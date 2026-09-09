#!/usr/bin/env python3
"""Fill in submission.submission_size for submissions that predate the column.

FormShare records the size of a submission as it stores it, but every
submission received before that was added carries 0. Anything reading the
column - a tenant's storage on the SaaS dashboard, for one - therefore
under-reports by everything that was already there, which on a real install is
almost all of it.

This recomputes those rows from the files on disk, using exactly the same
arithmetic as the live path in formshare/processes/odk/api.py: the submission's
media directory, plus the four serialisations beside it.

    submissions/<id>/                 media directory, recursively
    submissions/<id>.xml              the original from Collect
    submissions/<id>.original.json    the original JSON transformation
    submissions/<id>.ordered.json     the ordered JSON transformation
    submissions/<id>.json             the JSON transformation

Read-only unless given --apply, and by default it only touches rows sitting at
0, so it can be stopped and restarted without redoing work.

    python3 utilities/backfill_submission_size.py --ini /path/to/production.ini
    python3 utilities/backfill_submission_size.py --ini production.ini --apply

Worth running --verify first on an install that has some rows already filled in:
it recomputes those without writing and compares, which proves this agrees with
what FormShare itself recorded before trusting it with the rest.
"""

import argparse
import configparser
import os
import sys
import time

from sqlalchemy import create_engine, text


def get_directory_size(path):
    """Bytes under path, recursively. Same implementation the live path uses."""
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            entries = os.scandir(current)
        except OSError:
            continue
        with entries:
            for entry in entries:
                try:
                    # is_dir/is_file use the type readdir already returned, so
                    # they are free; only entry.stat() costs a syscall.
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    continue
    return total


# The order and the set of files here are not arbitrary - they mirror
# api.py:4065-4121. If the live calculation ever changes, this has to change
# with it, or a backfilled row and a freshly stored one stop meaning the same
# thing.
SERIALISATIONS = (".xml", ".original.json", ".ordered.json", ".json")


def submission_bytes(submissions_dir, submission_id):
    """What FormShare would have recorded for this submission."""
    total = get_directory_size(os.path.join(submissions_dir, submission_id))
    for suffix in SERIALISATIONS:
        path = os.path.join(submissions_dir, submission_id + suffix)
        try:
            total += os.stat(path).st_size
        except OSError:
            # Missing is normal: a form without a repository has no
            # .ordered.json, and older submissions may lack others.
            continue
    return total


def human(num):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1000 or unit == "TB":
            return "{:,.0f}{}".format(num, unit) if unit == "B" else "{:,.1f}{}".format(num, unit)
        num /= 1000.0


def read_ini(path):
    cfg = configparser.ConfigParser()
    if not cfg.read(path):
        sys.exit("Could not read {}".format(path))
    section = "app:formshare" if cfg.has_section("app:formshare") else "app:main"
    return cfg.get(section, "sqlalchemy.url"), cfg.get(section, "repository.path")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ini", required=True)
    parser.add_argument(
        "--apply", action="store_true", help="write the sizes (default: report only)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="recompute every submission, not only those sitting at 0",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="recompute rows that already have a size and compare, writing nothing",
    )
    parser.add_argument("--project", help="limit to one project id")
    parser.add_argument("--limit", type=int, help="stop after this many submissions")
    parser.add_argument(
        "--batch", type=int, default=500, help="rows per UPDATE batch (default 500)"
    )
    args = parser.parse_args()

    db_url, repo_path = read_ini(args.ini)
    odk_forms = os.path.join(repo_path, "odk", "forms")
    if not os.path.isdir(odk_forms):
        sys.exit("{} does not exist - is repository.path right?".format(odk_forms))

    engine = create_engine(db_url)
    connection = engine.connect()

    where = []
    params = {}
    if args.verify:
        where.append("s.submission_size > 0")
    elif not args.all:
        where.append("(s.submission_size IS NULL OR s.submission_size = 0)")
    if args.project:
        where.append("s.project_id = :project")
        params["project"] = args.project
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    sql = (
        "SELECT s.project_id, s.form_id, s.submission_id, "
        "       COALESCE(s.submission_size, 0), f.form_directory "
        "FROM submission s "
        "JOIN odkform f ON f.project_id = s.project_id AND f.form_id = s.form_id "
        "{} ORDER BY f.form_directory, s.submission_id".format(clause)
    )
    rows = connection.execute(text(sql), params).fetchall()
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        print("Nothing to do.")
        return

    print("{} submission(s) to {}".format(
        len(rows), "verify" if args.verify else "measure"))
    print("repository: {}\n".format(repo_path))

    started = time.perf_counter()
    updates = []
    measured = empty = unchanged = mismatched = 0
    grew = shrank = gone = 0
    total_bytes = 0
    missing_dirs = set()
    worst = []

    for index, (project_id, form_id, submission_id, stored, form_directory) in enumerate(rows, 1):
        if not form_directory:
            missing_dirs.add((project_id, form_id))
            continue
        submissions_dir = os.path.join(odk_forms, form_directory, "submissions")
        if not os.path.isdir(submissions_dir):
            missing_dirs.add((project_id, form_id))
            continue
        size = submission_bytes(submissions_dir, submission_id)
        measured += 1
        total_bytes += size
        if size == 0:
            empty += 1
        if args.verify:
            if size == stored:
                unchanged += 1
            else:
                mismatched += 1
                if len(worst) < 10:
                    worst.append((submission_id, stored, size))
                if size == 0:
                    gone += 1
                elif size > stored:
                    grew += 1
                else:
                    shrank += 1
        elif size != stored:
            updates.append({"size": size, "pid": project_id, "fid": form_id,
                            "sid": submission_id})
        if index % 2000 == 0:
            sys.stderr.write("\r  {}/{} ...".format(index, len(rows)))
            sys.stderr.flush()
    sys.stderr.write("\r\033[K")
    elapsed = time.perf_counter() - started

    print("measured {} submission(s) in {:.1f}s, {} total".format(
        measured, elapsed, human(total_bytes)))
    if empty:
        print("  {} measured as 0 - their files are not on disk".format(empty))
    if missing_dirs:
        print("  {} form(s) skipped: no directory on disk".format(len(missing_dirs)))

    if args.verify:
        print("\n--- verify ---")
        print("  {} agree exactly with what FormShare recorded".format(unchanged))
        print("  {} differ: {} larger, {} smaller, {} with no files left".format(
            mismatched, grew, shrank, gone))
        for sid, stored, size in worst:
            print("    {}  stored {:>14,}  measured {:>14,}  delta {:>+14,}".format(
                sid[:36], stored, size, size - stored))
        if mismatched:
            print()
            print("  A difference does not necessarily mean this disagrees with api.py.")
            print("  submission_size is written once when the submission arrives and")
            print("  never revisited, so it goes stale as soon as the files change:")
            print()
            print("    larger  - the submission was edited. Data cleaning writes a")
            print("              diffs/ directory inside the media directory, and on")
            print("              this install one of those held a 306 KB HTML diff.")
            print("    smaller - files were removed since.")
            print("    no files- the submission's directory is gone entirely while its")
            print("              row survives.")
            print()
            print("  Measured is the current truth in every one of those cases. Only a")
            print("  difference you cannot explain that way is a bug in this script.")
        return

    print("\n{} row(s) would change".format(len(updates)))
    if not updates:
        return
    if not args.apply:
        for u in updates[:10]:
            print("  {}  -> {:>14,} bytes".format(u["sid"][:36], u["size"]))
        if len(updates) > 10:
            print("  ... and {} more".format(len(updates) - 10))
        print("\nRead-only. Re-run with --apply to write.")
        return

    print("applying...")
    written = 0
    update_sql = text(
        "UPDATE submission SET submission_size = :size "
        "WHERE project_id = :pid AND form_id = :fid AND submission_id = :sid"
    )
    try:
        for start in range(0, len(updates), args.batch):
            chunk = updates[start:start + args.batch]
            transaction = connection.begin()
            connection.execute(update_sql, chunk)
            transaction.commit()
            written += len(chunk)
            sys.stderr.write("\r  {}/{} written".format(written, len(updates)))
            sys.stderr.flush()
        sys.stderr.write("\r\033[K")
        print("done: {} row(s) updated, {} accounted for".format(
            written, human(total_bytes)))
    except Exception as e:
        sys.exit("\nstopped after {} row(s): {}\nRe-running resumes where it "
                 "left off, since only rows at 0 are selected.".format(written, e))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
