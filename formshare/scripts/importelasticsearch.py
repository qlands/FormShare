"""
Import FormShare ElasticSearch indices from NDJSON.

This is the second half of the ElasticSearch migration tool. It reads the
NDJSON files produced by ``exportelasticsearch.py`` and bulk-loads them onto a
*new* ElasticSearch server (FormShare 3.x runs ES 9.2.x). The new server may be
completely empty: for any index that does not exist yet, the matching
``<index>.mapping.json`` sidecar written during export is used to recreate it
with the correct settings and mappings.

Document ``_id`` values are preserved, so re-running the import is idempotent
(documents are overwritten, not duplicated). The on-disk ``_source`` is byte
compatible between ES 7.x and 9.x for every FormShare index, so no
transformation is needed.

Index creation policy
---------------------
For every NDJSON file the target index name is taken from the embedded bulk
action lines (or ``--index`` / ``--rename`` overrides), then:

  * the index already exists  -> documents are loaded into it as-is. This is
    what happens when FormShare 3.x has already been started and created the
    indices with its *new* mappings; those new mappings win.
  * the index does not exist   -> it is created from the ``.mapping.json``
    sidecar (``--no-create`` disables this and relies on dynamic mapping).
  * ``--recreate``             -> the index is deleted first and rebuilt from
    the sidecar. Destructive; use only on a throw-away/empty target.

The script is self-contained and works with both the 7.x and 9.x
elasticsearch-py client (only the client constructor differs).

Examples
--------
Load a dump onto a new 9.x server with basic auth over https::

    import_elasticsearch --host es.new --port 9200 --scheme https \\
        --user elastic --password secret --input ./es_dump

Take the connection details straight from the new FormShare ini file::

    import_elasticsearch --ini /path/to/production.ini --input ./es_dump

Load one file into a renamed index::

    import_elasticsearch --ini new.ini --file ./es_dump/formshare_users.ndjson \\
        --index formshare_users_v3
"""

import argparse
import configparser
import glob
import json
import os
import sys

# Same group/name mapping used by the exporter, kept here so the importer stays
# self-contained.
INDEX_GROUPS = [
    ("user", "formshare_users"),
    ("partner", "formshare_partners"),
    ("repository", "formshare_datasets"),
    ("records", "formshare_records"),
]


def read_ini_settings(ini_path):
    """Return the ``[app:formshare]`` settings of a Pyramid ini file as a dict."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ini_path)
    section = "app:formshare"
    if not parser.has_section(section):
        section = next(
            (s for s in parser.sections() if s.startswith("app:")), None
        )
    if section is None:
        return {}
    return dict(parser.items(section))


def resolve_connection(args, settings):
    """Merge ini-file values and command-line flags into one connection dict."""
    group = args.ini_group

    def ini(key, default=None):
        return settings.get("elasticsearch.{}.{}".format(group, key), default)

    use_ssl = (ini("use_ssl", "False") == "True")
    scheme_default = settings.get(
        "elasticsearch.user.scheme", "https" if use_ssl else "http"
    )

    host = args.host or ini("host", "localhost")
    port = args.port or ini("port", "9200")
    scheme = args.scheme or scheme_default
    url_prefix = args.url_prefix or ini("url_prefix") or None

    user = args.user
    if user is None:
        user = settings.get("elasticsearch.user.name")
    password = args.password
    if password is None:
        password = settings.get("elasticsearch.user.password")

    if user in (None, "", "empty"):
        user = None
        password = None

    return {
        "host": host,
        "port": int(port),
        "scheme": scheme,
        "url_prefix": url_prefix,
        "user": user,
        "password": password,
    }


def build_client(conn, request_timeout=800, max_retries=10, verify_certs=True,
                 ca_certs=None):
    """Build an Elasticsearch client that works on both 7.x and 9.x clients."""
    import elasticsearch
    from elasticsearch import Elasticsearch

    version = getattr(elasticsearch, "__version__", None)
    if isinstance(version, tuple):
        major = version[0]
    else:
        try:
            major = int(str(getattr(elasticsearch, "__versionstr__", "8")).split(".")[0])
        except (ValueError, AttributeError):
            major = 8

    url = "{scheme}://{host}:{port}".format(**conn)
    if conn["url_prefix"]:
        url = url + "/" + conn["url_prefix"].strip("/")

    auth = None
    if conn["user"]:
        auth = (conn["user"], conn["password"] or "")

    kwargs = {"max_retries": max_retries, "retry_on_timeout": True}
    if conn["scheme"] == "https":
        kwargs["verify_certs"] = verify_certs
        if ca_certs:
            kwargs["ca_certs"] = ca_certs

    if major <= 7:
        kwargs["timeout"] = request_timeout
        if auth:
            kwargs["http_auth"] = auth
        client = Elasticsearch([url], **kwargs)
    else:
        kwargs["request_timeout"] = request_timeout
        if auth:
            kwargs["basic_auth"] = auth
        client = Elasticsearch(url, **kwargs)

    return client, major


def index_exists(client, index_name):
    return bool(client.indices.exists(index=index_name))


def detect_index_name(ndjson_path):
    """Read the first bulk action line of a file to find its target index."""
    with open(ndjson_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            action = json.loads(line)
            meta = action[next(iter(action))]
            return meta.get("_index")
    return None


def sidecar_path(ndjson_path):
    """Return the ``.mapping.json`` path that matches an ``.ndjson`` file."""
    base = ndjson_path
    if base.endswith(".ndjson"):
        base = base[: -len(".ndjson")]
    return base + ".mapping.json"


def create_index_from_sidecar(client, index_name, ndjson_path, replicas=None):
    """Create ``index_name`` from its mapping sidecar. Returns True if created."""
    side = sidecar_path(ndjson_path)
    if not os.path.exists(side):
        print("    no mapping sidecar found ({}); relying on dynamic mapping".format(
            os.path.basename(side)))
        return False
    with open(side, "r", encoding="utf-8") as handle:
        mapping_doc = json.load(handle)

    settings = dict(mapping_doc.get("settings", {}))
    if replicas is not None:
        settings["number_of_replicas"] = replicas
    body = {"mappings": mapping_doc.get("mappings", {})}
    if settings:
        body["settings"] = {"index": settings}
    client.indices.create(index=index_name, body=body)
    print("    created index '{}' from mapping sidecar".format(index_name))
    return True


def iter_bulk_actions(ndjson_path, target_index):
    """Yield elasticsearch.helpers bulk actions from a bulk-format NDJSON file.

    The file alternates an action line ({"index": {"_index", "_id"}}) and a
    source line. We re-target every document at ``target_index`` and keep the
    original ``_id`` so the load is idempotent.
    """
    with open(ndjson_path, "r", encoding="utf-8") as handle:
        while True:
            action_line = handle.readline()
            if not action_line:
                break
            action_line = action_line.strip()
            if not action_line:
                continue
            action = json.loads(action_line)
            meta = action[next(iter(action))]

            source_line = handle.readline()
            if not source_line:
                break
            source = json.loads(source_line)

            doc = {
                "_op_type": "index",
                "_index": target_index,
                "_source": source,
            }
            doc_id = meta.get("_id")
            if doc_id is not None:
                doc["_id"] = doc_id
            yield doc


def load_file(client, ndjson_path, target_index, chunk_size, limit=None,
              progress_every=10000):
    """Bulk-load one NDJSON file. Returns (ok_count, fail_count, errors)."""
    from elasticsearch import helpers

    actions = iter_bulk_actions(ndjson_path, target_index)
    if limit is not None:
        actions = _take(actions, limit)

    ok_count = 0
    fail_count = 0
    errors = []
    for ok, info in helpers.streaming_bulk(
        client,
        actions,
        chunk_size=chunk_size,
        raise_on_error=False,
        raise_on_exception=False,
    ):
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            if len(errors) < 10:
                errors.append(info)
        processed = ok_count + fail_count
        if progress_every and processed % progress_every == 0:
            print("    ... {:,} documents".format(processed), flush=True)
    return ok_count, fail_count, errors


def _take(iterable, n):
    for i, item in enumerate(iterable):
        if i >= n:
            return
        yield item


def parse_rename(values):
    """Parse repeated ``old=new`` flags into a dict."""
    mapping = {}
    for value in values or []:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                "--rename expects old=new, got: {}".format(value))
        old, new = value.split("=", 1)
        mapping[old] = new
    return mapping


def main(raw_args=None):
    parser = argparse.ArgumentParser(
        description="Import FormShare ElasticSearch indices from NDJSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ini", help="FormShare ini file to read connection defaults from")
    parser.add_argument(
        "--ini-group",
        default="user",
        choices=[g for g, _ in INDEX_GROUPS],
        help="Which elasticsearch.<group>.* keys to read host/port from (default: user)",
    )
    parser.add_argument("--host", help="ElasticSearch host (overrides ini)")
    parser.add_argument("--port", help="ElasticSearch port (overrides ini)")
    parser.add_argument("--scheme", choices=["http", "https"], help="Connection scheme")
    parser.add_argument("--user", help="Basic-auth user (omit for no auth)")
    parser.add_argument("--password", help="Basic-auth password")
    parser.add_argument("--url-prefix", dest="url_prefix", help="URL prefix/path of the cluster")
    parser.add_argument("--no-verify-certs", dest="verify_certs", action="store_false",
                        help="Do not verify TLS certs (https only)")
    parser.add_argument("--ca-certs", dest="ca_certs", help="Path to a CA bundle (https only)")
    parser.add_argument("-i", "--input", default="es_dump",
                        help="Directory holding the dump (default: ./es_dump)")
    parser.add_argument("--file", dest="files", action="append",
                        help="Specific .ndjson file to load (repeatable). Overrides --input scan")
    parser.add_argument("--index", dest="force_index",
                        help="Force every loaded document into this index name")
    parser.add_argument("--rename", action="append",
                        help="Remap an index name as old=new (repeatable)")
    parser.add_argument("--chunk-size", type=int, default=500,
                        help="Documents per bulk request (default: 500)")
    parser.add_argument("--replicas", type=int,
                        help="Override number_of_replicas when creating indices")
    parser.add_argument("--no-create", dest="create", action="store_false",
                        help="Do not create missing indices (rely on dynamic mapping)")
    parser.add_argument("--recreate", action="store_true",
                        help="DELETE each target index before loading (destructive)")
    parser.add_argument("--refresh", action="store_true",
                        help="Refresh each index after loading it")
    parser.add_argument("--limit", type=int,
                        help="Stop after N documents per file (for testing)")
    args = parser.parse_args(raw_args)

    try:
        rename = parse_rename(args.rename)
    except argparse.ArgumentTypeError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 1

    settings = {}
    if args.ini:
        if not os.path.exists(args.ini):
            print("ERROR: ini file does not exist: {}".format(args.ini), file=sys.stderr)
            return 1
        settings = read_ini_settings(args.ini)

    conn = resolve_connection(args, settings)

    # Gather the NDJSON files to load.
    if args.files:
        files = args.files
    else:
        if not os.path.isdir(args.input):
            print("ERROR: input directory does not exist: {}".format(args.input),
                  file=sys.stderr)
            return 1
        files = sorted(glob.glob(os.path.join(args.input, "*.ndjson")))
    if not files:
        print("ERROR: no .ndjson files found to import.", file=sys.stderr)
        return 1

    try:
        client, major = build_client(
            conn,
            verify_certs=args.verify_certs,
            ca_certs=args.ca_certs,
        )
    except ImportError:
        print("ERROR: the 'elasticsearch' package is not installed in this "
              "environment.", file=sys.stderr)
        return 1

    if not client.ping():
        print("ERROR: cannot reach ElasticSearch at {scheme}://{host}:{port}".format(**conn),
              file=sys.stderr)
        return 1

    print("Connected to {scheme}://{host}:{port} (elasticsearch-py major {major})".format(
        major=major, **conn))

    total_ok = 0
    total_fail = 0
    for ndjson_path in files:
        if not os.path.exists(ndjson_path):
            print("  - {}: SKIPPED (file not found)".format(ndjson_path))
            continue

        # Decide the destination index name.
        target = args.force_index or detect_index_name(ndjson_path)
        if target is None:
            # Fall back to the file stem.
            target = os.path.splitext(os.path.basename(ndjson_path))[0]
        target = rename.get(target, target)

        print("  - {} -> index '{}'".format(os.path.basename(ndjson_path), target))

        if args.recreate and index_exists(client, target):
            client.indices.delete(index=target)
            print("    deleted existing index '{}' (--recreate)".format(target))

        if not index_exists(client, target):
            if args.create:
                created = create_index_from_sidecar(
                    client, target, ndjson_path, replicas=args.replicas
                )
                if not created:
                    print("    index will be auto-created on first write")
            else:
                print("    index missing and --no-create set; relying on dynamic mapping")
        else:
            print("    loading into existing index (its current mapping is kept)")

        ok_count, fail_count, errors = load_file(
            client,
            ndjson_path,
            target,
            chunk_size=args.chunk_size,
            limit=args.limit,
        )
        total_ok += ok_count
        total_fail += fail_count
        print("    loaded: {:,} ok, {:,} failed".format(ok_count, fail_count))
        for err in errors:
            print("      error: {}".format(json.dumps(err, default=str)[:500]))

        if args.refresh and index_exists(client, target):
            client.indices.refresh(index=target)

    try:
        client.close()
    except Exception:
        pass

    print("\nImport finished: {:,} documents loaded, {:,} failed.".format(
        total_ok, total_fail))
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
