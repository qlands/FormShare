"""
Export FormShare ElasticSearch indices to NDJSON.

This is the first half of the ElasticSearch migration tool. It connects to an
*old* ElasticSearch server (the FormShare 2.x stack runs ES 7.14.x) and dumps
every requested index to disk as NDJSON, ready to be loaded onto a new server
(FormShare 3.x runs ES 9.2.x) with ``importelasticsearch.py``.

For each index three things are produced in the output directory:

  * ``<index>.ndjson``        -> the documents, in ElasticSearch *bulk* format
                                 (one action line + one source line per doc),
                                 the same shape FormShare already uses for its
                                 ``es_batch`` files. ``_id`` is preserved.
  * ``<index>.mapping.json``  -> the index settings + mappings, so an empty new
                                 server can recreate the index faithfully.
  * ``manifest.json``         -> a small summary of the dump (indices, counts,
                                 source, timestamp).

The four standard FormShare indices are exported by default
(formshare_users, formshare_partners, formshare_datasets, formshare_records),
but custom names can be given with ``--index`` (repeatable) or every non-system
index can be dumped with ``--all``.

The script is deliberately self-contained and works with both the 7.x and the
9.x elasticsearch-py client (only the client constructor differs between major
versions), so the very same file can run on the old box or the new box.

Examples
--------
Dump the four default indices from a local, unauthenticated 7.x server::

    export_elasticsearch --host localhost --port 9200 --output ./es_dump

Take the connection details straight from a FormShare ini file::

    export_elasticsearch --ini /path/to/production.ini --output ./es_dump

Dump a single custom index over https with basic auth::

    export_elasticsearch --host es.old --port 9200 --scheme https \\
        --user elastic --password secret --index my_index --output ./es_dump
"""

import argparse
import configparser
import json
import os
import sys
from datetime import datetime

# The four index "groups" FormShare configures, mapped to their default index
# names. Used both to derive names from an ini file and as the fall-back set.
INDEX_GROUPS = [
    ("user", "formshare_users"),
    ("partner", "formshare_partners"),
    ("repository", "formshare_datasets"),
    ("records", "formshare_records"),
]
DEFAULT_INDICES = [name for _, name in INDEX_GROUPS]

# Index-level settings that are safe (and meaningful) to copy when recreating an
# index. Everything else returned by get_settings (uuid, creation_date,
# version, provided_name, ...) is server-generated and must be dropped.
PORTABLE_SETTINGS = ("number_of_shards", "number_of_replicas", "analysis")


def read_ini_settings(ini_path):
    """Return the ``[app:formshare]`` settings of a Pyramid ini file as a dict.

    Interpolation is disabled so values containing ``%`` do not blow up.
    """
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ini_path)
    section = "app:formshare"
    if not parser.has_section(section):
        section = next((s for s in parser.sections() if s.startswith("app:")), None)
    if section is None:
        return {}
    return dict(parser.items(section))


def resolve_connection(args, settings):
    """Merge ini-file values and command-line flags into one connection dict.

    Command-line flags always win over the ini file. Authentication and scheme
    live under the ``elasticsearch.user.*`` keys in FormShare 3.x; on a 2.x /
    7.x server they are usually absent, which simply means "no auth / http".
    """
    group = args.ini_group

    def ini(key, default=None):
        return settings.get("elasticsearch.{}.{}".format(group, key), default)

    use_ssl = ini("use_ssl", "False") == "True"
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

    # FormShare uses the literal "empty" as a sentinel for "no credentials".
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


def build_client(
    conn, request_timeout=800, max_retries=10, verify_certs=True, ca_certs=None
):
    """Build an Elasticsearch client that works on both 7.x and 9.x clients.

    The only meaningful difference between the major versions is the
    constructor: 7.x takes ``http_auth`` / ``timeout`` while 8.x+ takes
    ``basic_auth`` / ``request_timeout``. Everything else used by this tool
    (``indices.exists``, ``helpers.scan``, ...) is call-compatible.
    """
    import elasticsearch
    from elasticsearch import Elasticsearch

    version = getattr(elasticsearch, "__version__", None)
    if isinstance(version, tuple):
        major = version[0]
    else:
        try:
            major = int(
                str(getattr(elasticsearch, "__versionstr__", "8")).split(".")[0]
            )
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


def list_all_indices(client):
    """Return every non-system index on the cluster (skips ``.``-prefixed)."""
    names = sorted(client.indices.get(index="*").keys())
    return [n for n in names if not n.startswith(".")]


def index_exists(client, index_name):
    return bool(client.indices.exists(index=index_name))


def dump_mapping(client, index_name, out_dir):
    """Write ``<index>.mapping.json`` with the portable settings + mappings."""
    raw_settings = client.indices.get_settings(index=index_name)
    raw_mapping = client.indices.get_mapping(index=index_name)

    index_settings = raw_settings[index_name]["settings"].get("index", {})
    portable = {
        key: index_settings[key] for key in PORTABLE_SETTINGS if key in index_settings
    }
    mapping_doc = {
        "settings": portable,
        "mappings": raw_mapping[index_name]["mappings"],
    }
    target = os.path.join(out_dir, index_name + ".mapping.json")
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(mapping_doc, handle, ensure_ascii=False, indent=2, default=str)
    return target


def dump_documents(
    client,
    index_name,
    out_dir,
    scroll_size,
    scroll_time,
    limit=None,
    progress_every=10000,
):
    """Scroll every document of ``index_name`` into ``<index>.ndjson``.

    Returns the number of documents written.
    """
    from elasticsearch import helpers

    target = os.path.join(out_dir, index_name + ".ndjson")
    written = 0
    scanner = helpers.scan(
        client,
        index=index_name,
        query={"query": {"match_all": {}}},
        size=scroll_size,
        scroll=scroll_time,
        preserve_order=False,
        raise_on_error=True,
    )
    with open(target, "w", encoding="utf-8") as handle:
        for hit in scanner:
            action = {"index": {"_index": index_name, "_id": hit["_id"]}}
            source = hit.get("_source", {})
            handle.write(json.dumps(action, ensure_ascii=False, default=str) + "\n")
            handle.write(json.dumps(source, ensure_ascii=False, default=str) + "\n")
            written += 1
            if progress_every and written % progress_every == 0:
                print("    ... {:,} documents".format(written), flush=True)
            if limit is not None and written >= limit:
                break
    return target, written


def main(raw_args=None):
    parser = argparse.ArgumentParser(
        description="Export FormShare ElasticSearch indices to NDJSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ini", help="FormShare ini file to read connection defaults from"
    )
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
    parser.add_argument(
        "--url-prefix", dest="url_prefix", help="URL prefix/path of the cluster"
    )
    parser.add_argument(
        "--no-verify-certs",
        dest="verify_certs",
        action="store_false",
        help="Do not verify TLS certs (https only)",
    )
    parser.add_argument(
        "--ca-certs", dest="ca_certs", help="Path to a CA bundle (https only)"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="es_dump",
        help="Output directory for the dump (default: ./es_dump)",
    )
    parser.add_argument(
        "--index",
        dest="indices",
        action="append",
        help="Index to export (repeatable). Overrides the default/ini set",
    )
    parser.add_argument(
        "--all",
        dest="dump_all",
        action="store_true",
        help="Export every non-system index on the cluster",
    )
    parser.add_argument(
        "--scroll-size",
        type=int,
        default=1000,
        help="Documents per scroll batch (default: 1000)",
    )
    parser.add_argument(
        "--scroll-time", default="5m", help="Scroll context keep-alive (default: 5m)"
    )
    parser.add_argument(
        "--limit", type=int, help="Stop after N documents per index (for testing)"
    )
    args = parser.parse_args(raw_args)

    settings = {}
    if args.ini:
        if not os.path.exists(args.ini):
            print(
                "ERROR: ini file does not exist: {}".format(args.ini), file=sys.stderr
            )
            return 1
        settings = read_ini_settings(args.ini)

    conn = resolve_connection(args, settings)

    try:
        client, major = build_client(
            conn,
            verify_certs=args.verify_certs,
            ca_certs=args.ca_certs,
        )
    except ImportError:
        print(
            "ERROR: the 'elasticsearch' package is not installed in this "
            "environment.",
            file=sys.stderr,
        )
        return 1

    if not client.ping():
        print(
            "ERROR: cannot reach ElasticSearch at {scheme}://{host}:{port}".format(
                **conn
            ),
            file=sys.stderr,
        )
        return 1

    print(
        "Connected to {scheme}://{host}:{port} (elasticsearch-py major {major})".format(
            major=major, **conn
        )
    )

    # Work out which indices to export.
    if args.indices:
        indices = args.indices
    elif args.dump_all:
        indices = list_all_indices(client)
    elif settings:
        indices = [
            settings.get("elasticsearch.{}.index_name".format(group), default)
            for group, default in INDEX_GROUPS
        ]
    else:
        indices = list(DEFAULT_INDICES)

    os.makedirs(args.output, exist_ok=True)

    manifest = {
        "created": datetime.now().isoformat(),
        "source": "{scheme}://{host}:{port}".format(**conn),
        "client_major": major,
        "indices": [],
    }
    total = 0
    missing = []
    for index_name in indices:
        if not index_exists(client, index_name):
            print("  - {}: SKIPPED (does not exist on source)".format(index_name))
            missing.append(index_name)
            continue
        print("  - {}: exporting ...".format(index_name))
        dump_mapping(client, index_name, args.output)
        _, written = dump_documents(
            client,
            index_name,
            args.output,
            scroll_size=args.scroll_size,
            scroll_time=args.scroll_time,
            limit=args.limit,
        )
        print("    done: {:,} documents".format(written))
        manifest["indices"].append({"index": index_name, "documents": written})
        total += written

    with open(
        os.path.join(args.output, "manifest.json"), "w", encoding="utf-8"
    ) as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    try:
        client.close()
    except Exception:
        pass

    print(
        "\nExport finished: {:,} documents across {} index(es) -> {}".format(
            total, len(manifest["indices"]), os.path.abspath(args.output)
        )
    )
    if missing:
        print("Indices not found on source (skipped): {}".format(", ".join(missing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
