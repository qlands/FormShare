#!/usr/bin/env python3
"""Back up a FormShare server, and restore what was backed up.

What a backup holds:

- **Every schema of the MySQL server** but MySQL's own: formshare, the
  repositories (FS_), and what plugins keep there -- the analytics plugin's
  FU_ schemas, where each user keeps tables of their own, Superset's
  metadata (superset), FormAtlas's FA_ repositories. One gzipped mysqldump
  file each, without CREATE DATABASE, so that any of them can be restored
  alone, under its own name or beside the live one.
- **Every MySQL account** but MySQL's own, the cloud's and the one that runs
  the backup, with its password hash and its grants (users.sql). Plugins
  create accounts that read the repositories: FU_ for analytics and
  Superset, fa_ for FormAtlas. A dump of the schemas alone loses them.
- **The repository directory** (repository.path: submissions, media, each
  form's create.xml), and any other path given, as tar.gz.
- A copy of the ini, and manifest.json: what is where, with checksums, the
  server's version and Alembic's revision.

Each dump is consistent within its schema (--single-transaction), not
across schemas: stop FormShare and its Celery workers, and Superset, before
a backup that has to be consistent as a whole.

It needs Python 3, the mysql and mysqldump clients and tar, and nothing of
FormShare, so the container of any FormShare version can run it: back up
with the old one before an upgrade. The connection is the one FormShare
uses: the file the ini names as mysql.cnf, or else mysql.host, mysql.port,
mysql.user and mysql.password. --defaults-file takes another. The options
of mysqldump are the ones Azure's managed MySQL needs.

    formshare_backup.py backup <ini> <directory> [--schema GLOB ...]
        [--exclude-schema GLOB ...] [--path PATH ...] [--no-files] [--jobs N]
    formshare_backup.py verify <backup>
    formshare_backup.py restore <ini> <backup> (--schema NAME ... | --all-schemas)
        [--suffix TEXT] [--drop-existing] [--strip-definers]
        [--users [--account GLOB ...]]

A restore checks the files against the manifest first. It refuses a schema
that exists, unless --drop-existing; --suffix restores beside it instead
(FS_x as FS_x_check), to look at a backup without touching the live data.
A view, trigger, routine or event is restored with its definer. A server that
refuses another definer (Azure: no SET_USER_ID) needs --strip-definers:
views and routines then run with the caller's rights (SQL SECURITY
INVOKER), and a trigger or an event with the rights of the account that
restored it. The manifest names the definers of each schema.
"""

import argparse
import datetime
import fnmatch
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

TOOL_VERSION = 1
SYSTEM_SCHEMAS = {"mysql", "information_schema", "performance_schema", "sys"}
# Accounts the server or the cloud manages, by user name: recreating them is
# neither needed nor allowed
SYSTEM_ACCOUNTS = ("mysql.*", "mariadb.sys", "debian-sys-maint", "azure_*")
MYSQLDUMP_OPTIONS = [
    "--single-transaction",
    "--set-gtid-purged=OFF",
    "--no-tablespaces",
    "--column-statistics=0",
    "--routines",
    "--triggers",
    "--events",
    "--hex-blob",
    "--default-character-set=utf8mb4",
]
CHUNK = 1 << 20
DUMP_COMPLETED = b"-- Dump completed"
DEFINER = re.compile(rb"DEFINER=`(?:[^`]|``)*`@`(?:[^`]|``)*`")


class BackupError(Exception):
    pass


def say(message):
    print(message, flush=True)


# --- Settings and the connection ---------------------------------------------


def read_settings(ini, section):
    """The ini's settings, with %(here)s resolved as PasteDeploy resolves it.
    Nothing else is interpolated: a value may hold a %."""
    import configparser

    parser = configparser.RawConfigParser(strict=False)
    with open(ini, encoding="utf-8") as a_file:
        parser.read_file(a_file)
    if not parser.has_section(section):
        raise BackupError("{} has no [{}] section".format(ini, section))
    here = os.path.dirname(os.path.abspath(ini))
    return {
        key: value.replace("%(here)s", here).replace(
            "%(__file__)s", os.path.abspath(ini)
        )
        for key, value in parser.items(section)
    }


def option_value(value):
    """A value for a MySQL option file: quoted, so that a # or a quote in a
    password is the password's, with its backslashes escaped."""
    return '"' + value.replace("\\", "\\\\") + '"'


def sql_string(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_name(value):
    return "`" + value.replace("`", "``") + "`"


def unescape(field):
    """A field of mysql --batch, which escapes NUL, tab, newline and \\."""
    if field == "NULL":
        return None
    return re.sub(
        r"\\(.)",
        lambda m: {"0": "\0", "t": "\t", "n": "\n"}.get(m.group(1), m.group(1)),
        field,
    )


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as a_file:
        for chunk in iter(lambda: a_file.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MySQL:
    """The mysql and mysqldump clients, connected as FormShare connects."""

    def __init__(self, settings, defaults_file=None):
        self._temporary = None
        if defaults_file:
            self.defaults = defaults_file
        elif settings.get("mysql.cnf") and os.path.isfile(settings["mysql.cnf"]):
            self.defaults = settings["mysql.cnf"]
        else:
            self.defaults = self._write_defaults(settings)

    def _write_defaults(self, settings):
        missing = [
            key
            for key in ("mysql.host", "mysql.user", "mysql.password")
            if not settings.get(key)
        ]
        if missing:
            raise BackupError(
                "The ini names no mysql.cnf, and lacks {}".format(", ".join(missing))
            )
        handle, path = tempfile.mkstemp(prefix="formshare_backup_", suffix=".cnf")
        with os.fdopen(handle, "w") as a_file:
            a_file.write("[client]\n")
            a_file.write("host={}\n".format(option_value(settings["mysql.host"])))
            a_file.write("port={}\n".format(settings.get("mysql.port") or "3306"))
            a_file.write("user={}\n".format(option_value(settings["mysql.user"])))
            a_file.write(
                "password={}\n".format(option_value(settings["mysql.password"]))
            )
        self._temporary = path
        return path

    def close(self):
        if self._temporary and os.path.exists(self._temporary):
            os.remove(self._temporary)

    def command(self, program):
        # --defaults-file has to come first
        return [program, "--defaults-file=" + self.defaults]

    def query(self, sql, database=None):
        """The rows of what the statements return, each a list of strings."""
        args = self.command("mysql") + [
            "--batch",
            "--skip-column-names",
            "--default-character-set=utf8mb4",
            "-e",
            sql,
        ]
        if database:
            args.append(database)
        process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode != 0:
            raise BackupError(
                "mysql: " + process.stderr.decode("utf-8", "replace").strip()
            )
        return [
            [unescape(field) for field in line.split("\t")]
            for line in process.stdout.decode("utf-8").split("\n")
            if line
        ]

    def scalar(self, sql, database=None):
        rows = self.query(sql, database)
        return rows[0][0] if rows else None


# --- Backup ------------------------------------------------------------------


class HashingWriter:
    """A file that keeps the SHA-256 and the size of what is written to it."""

    def __init__(self, a_file):
        self.file = a_file
        self.digest = hashlib.sha256()
        self.size = 0

    def write(self, data):
        self.digest.update(data)
        self.size += len(data)
        return self.file.write(data)

    def flush(self):
        self.file.flush()


def matches(name, globs):
    return any(fnmatch.fnmatch(name.lower(), glob.lower()) for glob in globs)


def list_schemas(db, include, exclude):
    tables = {
        row[0]: int(row[1])
        for row in db.query(
            "SELECT TABLE_SCHEMA, COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE' GROUP BY TABLE_SCHEMA"
        )
    }
    definers = {}
    for schema, definer in db.query(
        "SELECT TRIGGER_SCHEMA, DEFINER FROM information_schema.TRIGGERS "
        "UNION SELECT TABLE_SCHEMA, DEFINER FROM information_schema.VIEWS "
        "UNION SELECT ROUTINE_SCHEMA, DEFINER FROM information_schema.ROUTINES "
        "UNION SELECT EVENT_SCHEMA, DEFINER FROM information_schema.EVENTS"
    ):
        definers.setdefault(schema, set()).add(definer)
    schemas = []
    for name, charset, collation in db.query(
        "SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
        "FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME"
    ):
        if name.lower() in SYSTEM_SCHEMAS:
            continue
        if include and not matches(name, include):
            continue
        if exclude and matches(name, exclude):
            continue
        schemas.append(
            {
                "name": name,
                "charset": charset,
                "collation": collation,
                "tables": tables.get(name, 0),
                "definers": sorted(definers.get(name, ())),
            }
        )
    return schemas


def dump_schema(db, schema, backup):
    """One schema into schemas/<name>.sql.gz. A dump that does not end as
    mysqldump ends a complete one is an error."""
    relative = os.path.join("schemas", schema["name"] + ".sql.gz")
    target = os.path.join(backup, relative)
    partial = target + ".partial"
    errors = tempfile.TemporaryFile()
    args = db.command("mysqldump") + MYSQLDUMP_OPTIONS + [schema["name"]]
    tail = b""
    with open(partial, "wb") as raw:
        writer = HashingWriter(raw)
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=errors) as process:
            with gzip.GzipFile(fileobj=writer, mode="wb", mtime=0) as compressed:
                for chunk in iter(lambda: process.stdout.read(CHUNK), b""):
                    compressed.write(chunk)
                    tail = (tail + chunk)[-4096:]
            returncode = process.wait()
    errors.seek(0)
    message = errors.read().decode("utf-8", "replace").strip()
    errors.close()
    if returncode != 0 or DUMP_COMPLETED not in tail:
        os.remove(partial)
        raise BackupError(
            "mysqldump of {} failed ({}): {}".format(
                schema["name"], returncode, message or "the dump is not complete"
            )
        )
    os.chmod(partial, 0o600)
    os.replace(partial, target)
    return dict(
        schema, file=relative, bytes=writer.size, sha256=writer.digest.hexdigest()
    )


def system_account(user, host, me):
    return (
        (user, host) == me
        or matches(user, SYSTEM_ACCOUNTS)
        or (user == "root" and host == "localhost")
    )


def dump_accounts(db, backup):
    """users.sql: every account but the system's and the one running this,
    created only if it does not exist, with the password it has, then the
    grants, then the default roles. Each statement follows a line naming its
    account, which is how a restore picks some."""
    current = db.scalar("SELECT CURRENT_USER()")
    me = tuple(current.rsplit("@", 1))
    try:
        db.query("SET SESSION print_identified_with_as_hex = ON")
        as_hex = "SET SESSION print_identified_with_as_hex = ON; "
    except BackupError:
        # Before MySQL 8.0.17 a hash is printed as it is, and a binary one
        # (caching_sha2_password) may not load again
        as_hex = ""
    accounts, skipped = [], []
    for user, host in db.query("SELECT User, Host FROM mysql.user ORDER BY User, Host"):
        if system_account(user, host, me):
            skipped.append("{}@{}".format(user, host))
        else:
            accounts.append((user, host))
    creates, grants, roles = [], [], []
    for user, host in accounts:
        account = "{}@{}".format(sql_string(user), sql_string(host))
        label = "-- account: {}@{}".format(user, host)
        rows = db.query(
            as_hex + "SHOW CREATE USER {0}; SHOW GRANTS FOR {0};".format(account)
        )
        create = re.sub(r"^CREATE USER ", "CREATE USER IF NOT EXISTS ", rows[0][0])
        # The roles an account starts with exist only once every account
        # does: they are set at the end
        default_role = re.search(
            r" DEFAULT ROLE (.+?)(?= REQUIRE | PASSWORD | ACCOUNT | COMMENT | ATTRIBUTE |$)",
            create,
        )
        if default_role:
            create = create.replace(" DEFAULT ROLE " + default_role.group(1), "", 1)
            roles.append(
                (
                    label,
                    "ALTER USER {} DEFAULT ROLE {};".format(
                        account, default_role.group(1)
                    ),
                )
            )
        creates.append((label, create + ";"))
        grants.extend((label, row[0] + ";") for row in rows[1:])
    path = os.path.join(backup, "users.sql")
    with open(path, "w", encoding="utf-8") as a_file:
        a_file.write(
            "-- The MySQL accounts and their grants, by formshare_backup.py on {}.\n"
            "-- Every account but MySQL's own, the cloud's and {} (which made the\n"
            "-- backup, and which a restore needs anyway). An account is created\n"
            "-- only if it does not exist, with the password it had; grants add to\n"
            "-- what an account has. Restore: formshare_backup.py restore --users.\n\n".format(
                datetime.datetime.now().isoformat(timespec="seconds"), current
            )
        )
        for section in (creates, grants, roles):
            for label, statement in section:
                a_file.write(label + "\n" + statement + "\n")
            a_file.write("\n")
    os.chmod(path, 0o600)
    return {
        "file": "users.sql",
        "sha256": sha256_of(path),
        "accounts": ["{}@{}".format(user, host) for user, host in accounts],
        "skipped": skipped,
        "made_by": current,
        "hashes_as_hex": bool(as_hex),
    }


def archive(source, backup, name):
    """A file or a directory into files/<name>.tar.gz. GNU tar says 1 when a
    file changed while it was read: a warning, written in the manifest."""
    source = os.path.abspath(source.rstrip("/") or "/")
    relative = os.path.join("files", name + ".tar.gz")
    target = os.path.join(backup, relative)
    process = subprocess.run(
        [
            "tar",
            "-czf",
            target,
            "-C",
            os.path.dirname(source),
            os.path.basename(source),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    message = process.stderr.decode("utf-8", "replace").strip()
    if process.returncode not in (0, 1):
        if os.path.exists(target):
            os.remove(target)
        raise BackupError("tar of {} failed: {}".format(source, message))
    os.chmod(target, 0o600)
    entry = {
        "source": source,
        "file": relative,
        "bytes": os.path.getsize(target),
        "sha256": sha256_of(target),
    }
    if process.returncode == 1:
        entry["warning"] = message
    return entry


def backup(args):
    settings = read_settings(args.ini, args.section)
    db = MySQL(settings, args.defaults_file)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = os.path.join(args.directory, "formshare-backup-" + stamp)
    os.makedirs(os.path.join(target, "schemas"))
    os.makedirs(os.path.join(target, "files"))
    os.makedirs(os.path.join(target, "config"))
    os.chmod(target, 0o700)
    manifest = {
        "tool_version": TOOL_VERSION,
        "status": "incomplete",
        "started": datetime.datetime.now().isoformat(timespec="seconds"),
        "ini": os.path.abspath(args.ini),
        "server_version": None,
        "formshare_schema": None,
        "alembic_version": None,
        "mysqldump": None,
        "schemas": [],
        "users": None,
        "files": [],
        "config": [],
    }
    try:
        manifest["server_version"] = db.scalar("SELECT VERSION()")
        manifest["mysqldump"] = (
            subprocess.run(["mysqldump", "--version"], stdout=subprocess.PIPE)
            .stdout.decode()
            .strip()
        )
        url = settings.get("sqlalchemy.url", "")
        formshare_schema = url.rsplit("/", 1)[-1].split("?")[0] if url else None
        manifest["formshare_schema"] = formshare_schema
        if formshare_schema:
            try:
                manifest["alembic_version"] = db.scalar(
                    "SELECT version_num FROM {}.alembic_version".format(
                        sql_name(formshare_schema)
                    )
                )
            except BackupError:
                pass
        say("Server {} -- backup in {}".format(manifest["server_version"], target))

        # The paths are checked before anything is dumped
        paths = (
            [] if args.no_files else [("repository", settings.get("repository.path"))]
        )
        paths += [(None, path) for path in args.path]
        archives, used = [], set()
        for name, path in paths:
            if not path:
                raise BackupError(
                    "The ini names no repository.path (or use --no-files)"
                )
            if not os.path.exists(path):
                raise BackupError("{} does not exist".format(path))
            source = os.path.realpath(path)
            if os.path.commonpath([source, os.path.realpath(target)]) == source:
                raise BackupError(
                    "{} holds the backup itself: write the backup elsewhere".format(
                        path
                    )
                )
            name = name or (
                re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.basename(path.rstrip("/")))
                or "root"
            )
            while name in used:
                name += "_"
            used.add(name)
            archives.append((name, path))

        schemas = list_schemas(db, args.schema, args.exclude_schema)
        if not schemas:
            raise BackupError("No schema to back up")
        say("Accounts and grants")
        manifest["users"] = dump_accounts(db, target)
        say(
            "  {} account(s); left out: {}".format(
                len(manifest["users"]["accounts"]),
                ", ".join(manifest["users"]["skipped"]) or "none",
            )
        )
        say("{} schema(s)".format(len(schemas)))
        done = []
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            futures = [
                pool.submit(dump_schema, db, schema, target) for schema in schemas
            ]
            for future in futures:
                entry = future.result()
                done.append(entry)
                say(
                    "  [{}/{}] {} ({} tables, {:.1f} MB)".format(
                        len(done),
                        len(schemas),
                        entry["name"],
                        entry["tables"],
                        entry["bytes"] / 1048576,
                    )
                )
        manifest["schemas"] = done

        for name, path in archives:
            say("Archiving {}".format(path))
            manifest["files"].append(archive(path, target, name))

        copy = os.path.join(target, "config", os.path.basename(args.ini))
        shutil.copy2(args.ini, copy)
        os.chmod(copy, 0o600)
        manifest["config"].append(
            {
                "source": os.path.abspath(args.ini),
                "file": os.path.relpath(copy, target),
                "sha256": sha256_of(copy),
            }
        )
        manifest["status"] = "complete"
    except BaseException as e:
        manifest["error"] = str(e) or e.__class__.__name__
        raise
    finally:
        manifest["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
        path = os.path.join(target, "manifest.json")
        with open(path, "w") as a_file:
            json.dump(manifest, a_file, indent=1)
        os.chmod(path, 0o600)
        db.close()
    total = sum(entry["bytes"] for entry in manifest["schemas"] + manifest["files"])
    say(
        "Done: {} schema(s), {} account(s), {} archive(s), {:.1f} MB in {}".format(
            len(manifest["schemas"]),
            len(manifest["users"]["accounts"]),
            len(manifest["files"]),
            total / 1048576,
            target,
        )
    )
    return target


# --- Verify ------------------------------------------------------------------


def load_manifest(backup):
    path = os.path.join(backup, "manifest.json")
    if not os.path.exists(path):
        raise BackupError("{} is not a backup: it has no manifest.json".format(backup))
    with open(path) as a_file:
        manifest = json.load(a_file)
    if manifest.get("status") != "complete":
        raise BackupError(
            "The backup in {} did not complete: {}".format(
                backup, manifest.get("error", "no reason recorded")
            )
        )
    return manifest


def check_file(backup, entry):
    path = os.path.join(backup, entry["file"])
    if not os.path.exists(path):
        return "{} is missing".format(entry["file"])
    if sha256_of(path) != entry["sha256"]:
        return "{} does not match its checksum".format(entry["file"])
    return None


def check_dump(backup, entry):
    """A dump's file, its checksum, and that it decompresses to a complete
    mysqldump output."""
    problem = check_file(backup, entry)
    if problem:
        return problem
    tail = b""
    try:
        with gzip.open(os.path.join(backup, entry["file"]), "rb") as a_file:
            for chunk in iter(lambda: a_file.read(CHUNK), b""):
                tail = (tail + chunk)[-4096:]
    except (OSError, EOFError) as e:
        return "{} does not decompress: {}".format(entry["file"], e)
    if DUMP_COMPLETED not in tail:
        return "{} is not a complete dump".format(entry["file"])
    return None


def verify(args):
    manifest = load_manifest(args.backup)
    problems = []
    for entry in manifest["schemas"]:
        problem = check_dump(args.backup, entry)
        if problem:
            problems.append(problem)
    for entry in [manifest["users"]] + manifest["files"] + manifest["config"]:
        problem = check_file(args.backup, entry)
        if problem:
            problems.append(problem)
    for problem in problems:
        say("PROBLEM: " + problem)
    say(
        "{}: {} schema(s), {} account(s), {} archive(s), alembic {}".format(
            "Not sound" if problems else "Sound",
            len(manifest["schemas"]),
            len(manifest["users"]["accounts"]),
            len(manifest["files"]),
            manifest.get("alembic_version"),
        )
    )
    return not problems


# --- Restore -----------------------------------------------------------------


def stream_dump(path, strip_definers):
    """The SQL of a dump, chunk by chunk, its definers removed if asked."""
    with gzip.open(path, "rb") as a_file:
        if not strip_definers:
            for chunk in iter(lambda: a_file.read(CHUNK), b""):
                yield chunk
            return
        # mysqldump writes each definer on the line of the CREATE it belongs to
        for line in a_file:
            if b"DEFINER" in line:
                line = DEFINER.sub(b"", line).replace(
                    b"SQL SECURITY DEFINER", b"SQL SECURITY INVOKER"
                )
            yield line


def run_sql(db, chunks, database=None):
    args = db.command("mysql") + ["--default-character-set=utf8mb4"]
    if database:
        args.append(database)
    errors = tempfile.TemporaryFile()
    with subprocess.Popen(args, stdin=subprocess.PIPE, stderr=errors) as process:
        try:
            for chunk in chunks:
                process.stdin.write(chunk)
        except BrokenPipeError:
            pass
        process.stdin.close()
        returncode = process.wait()
    errors.seek(0)
    message = errors.read().decode("utf-8", "replace").strip()
    errors.close()
    if returncode != 0:
        raise BackupError(message or "mysql exited with {}".format(returncode))


def account_statements(path, globs):
    """The statements of users.sql for the accounts whose user name matches."""
    selected, account = [], None
    with open(path, encoding="utf-8") as a_file:
        for line in a_file:
            if line.startswith("-- account: "):
                account = line[len("-- account: ") :].strip()
            elif line.strip() and not line.startswith("--"):
                user = account.rsplit("@", 1)[0] if account else ""
                if not globs or matches(user, globs):
                    selected.append(line)
    return selected


def restore(args):
    manifest = load_manifest(args.backup)
    settings = read_settings(args.ini, args.section)
    db = MySQL(settings, args.defaults_file)
    try:
        by_name = {entry["name"].lower(): entry for entry in manifest["schemas"]}
        if args.all_schemas:
            selected = list(manifest["schemas"])
        else:
            missing = [name for name in args.schema if name.lower() not in by_name]
            if missing:
                raise BackupError("Not in the backup: " + ", ".join(missing))
            selected = [by_name[name.lower()] for name in args.schema]
        if not selected and not args.users:
            raise BackupError(
                "Nothing to restore: name --schema, --all-schemas or --users"
            )

        problems = [check_dump(args.backup, entry) for entry in selected]
        if args.users:
            problems.append(check_file(args.backup, manifest["users"]))
        problems = [problem for problem in problems if problem]
        if problems:
            raise BackupError("The backup is not sound: " + "; ".join(problems))

        existing = {
            row[0].lower()
            for row in db.query("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA")
        }
        targets = [(entry, entry["name"] + args.suffix) for entry in selected]
        clashes = [target for _, target in targets if target.lower() in existing]
        if clashes and not args.drop_existing:
            raise BackupError(
                "These schemas exist: {}. Use --drop-existing to replace them, "
                "or --suffix to restore beside them".format(", ".join(clashes))
            )
        for count, (entry, target) in enumerate(targets, 1):
            if target.lower() in existing:
                # Another schema's foreign keys may point at it: a follow-up's
                # at the repository its cases come from
                db.query(
                    "SET FOREIGN_KEY_CHECKS = 0; DROP DATABASE {}".format(
                        sql_name(target)
                    )
                )
            db.query(
                "CREATE DATABASE {} CHARACTER SET {} COLLATE {}".format(
                    sql_name(target), entry["charset"], entry["collation"]
                )
            )
            try:
                run_sql(
                    db,
                    stream_dump(
                        os.path.join(args.backup, entry["file"]), args.strip_definers
                    ),
                    target,
                )
            except BackupError as e:
                raise BackupError(
                    "Restoring {} into {}: {}{}".format(
                        entry["name"],
                        target,
                        e,
                        (
                            ""
                            if args.strip_definers
                            else " (if MySQL refused a definer, use --strip-definers)"
                        ),
                    )
                )
            tables = int(
                db.scalar(
                    "SELECT COUNT(*) FROM information_schema.TABLES WHERE "
                    "TABLE_SCHEMA = {} AND TABLE_TYPE = 'BASE TABLE'".format(
                        sql_string(target)
                    )
                )
            )
            if tables != entry["tables"]:
                raise BackupError(
                    "{} has {} tables after the restore, and the backup {}".format(
                        target, tables, entry["tables"]
                    )
                )
            say(
                "  [{}/{}] {} -> {} ({} tables)".format(
                    count, len(targets), entry["name"], target, tables
                )
            )
        if args.users:
            statements = account_statements(
                os.path.join(args.backup, manifest["users"]["file"]), args.account
            )
            run_sql(db, (statement.encode("utf-8") for statement in statements))
            say("Accounts restored: {} statement(s)".format(len(statements)))
    finally:
        db.close()
    return True


# --- Command line ------------------------------------------------------------


def parse(raw_args):
    parser = argparse.ArgumentParser(
        description="Back up a FormShare server's MySQL schemas, its MySQL "
        "accounts and grants, and its repository directory; verify a backup; "
        "restore one."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    def connection(sub):
        sub.add_argument("--section", default="app:formshare", help="the ini's section")
        sub.add_argument(
            "--defaults-file",
            help="a MySQL option file to connect with, instead of the ini's",
        )

    sub = commands.add_parser("backup", help="make a backup")
    sub.add_argument("ini", help="FormShare's ini (development.ini)")
    sub.add_argument("directory", help="where to create formshare-backup-<time>")
    sub.add_argument(
        "--schema",
        action="append",
        default=[],
        metavar="GLOB",
        help="back up only the schemas that match (default: every one but MySQL's)",
    )
    sub.add_argument(
        "--exclude-schema",
        action="append",
        default=[],
        metavar="GLOB",
        help="leave out the schemas that match",
    )
    sub.add_argument(
        "--path",
        action="append",
        default=[],
        help="another file or directory to archive (the plugins, say)",
    )
    sub.add_argument(
        "--no-files", action="store_true", help="leave the repository directory out"
    )
    sub.add_argument("--jobs", type=int, default=2, help="mysqldumps at once (2)")
    connection(sub)

    sub = commands.add_parser("verify", help="check a backup's files")
    sub.add_argument("backup", help="a formshare-backup-<time> directory")

    sub = commands.add_parser("restore", help="restore schemas and accounts")
    sub.add_argument("ini", help="FormShare's ini, for the connection")
    sub.add_argument("backup", help="a formshare-backup-<time> directory")
    sub.add_argument(
        "--schema",
        action="append",
        default=[],
        metavar="NAME",
        help="a schema to restore",
    )
    sub.add_argument(
        "--all-schemas", action="store_true", help="restore every schema of the backup"
    )
    sub.add_argument(
        "--suffix",
        default="",
        help="restore each schema under its name and this (beside the live one)",
    )
    sub.add_argument(
        "--drop-existing",
        action="store_true",
        help="drop a schema that exists before restoring it",
    )
    sub.add_argument(
        "--strip-definers",
        action="store_true",
        help="for a server that refuses another definer (no SET_USER_ID)",
    )
    sub.add_argument(
        "--users", action="store_true", help="restore the accounts and their grants"
    )
    sub.add_argument(
        "--account",
        action="append",
        default=[],
        metavar="GLOB",
        help="with --users, only the accounts whose user name matches",
    )
    connection(sub)
    return parser.parse_args(raw_args)


def main(raw_args=None):
    args = parse(raw_args)
    try:
        if args.command == "backup":
            backup(args)
            return 0
        if args.command == "verify":
            return 0 if verify(args) else 1
        restore(args)
        return 0
    except BackupError as e:
        say("ERROR: {}".format(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
