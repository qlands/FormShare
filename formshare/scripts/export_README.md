# FormShare ElasticSearch migration (7.14.x → 9.2.x)

Two standalone scripts migrate FormShare's ElasticSearch data from an **old**
server (ES 7.14.x, the FormShare 2.x stack) to a **new** server (ES 9.2.x, the
FormShare 3.x stack) via NDJSON files on disk:

| Script | Role | Talks to | Client |
|--------|------|----------|--------|
| `exportelasticsearch.py` | dump indices → NDJSON | **old** ES 7.14.x | `elasticsearch==7.17.12` |
| `importelasticsearch.py` | NDJSON → load indices | **new** ES 9.2.x | `elasticsearch==9.2.0` |

The document `_source` shape is byte-compatible between the two ES versions for
every FormShare index, so documents migrate **1:1** with their original `_id`
preserved — no data transformation happens. Only the ElasticSearch *client*
constructor differs between major versions, and both scripts auto-detect the
installed client and adapt, so the same files run on either box.

> **The export is strictly read-only.** It only ever reads from the source and
> writes local NDJSON files. It never deletes or modifies the source index.
> The only destructive operation in the toolkit is `importelasticsearch.py`'s
> `--recreate` flag, which targets the **new** server only.

---

## Why two environments?

The ElasticSearch Python client is only supported against its own major
version (8.x/9.x also tolerate one major back). A 9.x client **cannot** talk to
a 7.14 server, and the 8.x/9.x clients refuse non-matching servers on connect.
So you cannot use a single client version for both ends — you need the 7.x
client where you export and the 9.x client where you import.

The two scripts share a version-aware connection helper, so you do **not** fork
the code; you just install the matching `elasticsearch` package in each place.
The NDJSON files are the version-neutral hand-off between them.

---

## Setup

Use two dedicated virtualenvs (the 7.x and 9.x clients cannot coexist in one):

```bash
# Old side (ES 7) — where you run the export
python3 -m venv venv-es7
./venv-es7/bin/pip install -r formshare/scripts/export_requirements.txt

# New side (ES 9) — where you run the import
python3 -m venv venv-es9
./venv-es9/bin/pip install -r formshare/scripts/import_requirements.txt
```

Run the scripts as **plain files** (`venv/bin/python …script.py`), not via the
`export_elasticsearch` / `import_elasticsearch` console entry points — the entry
points import `formshare/__init__.py` and pull in the whole app (gevent,
FastAPI…). As standalone files the scripts need nothing but `elasticsearch`.

---

## Quick start (end-to-end)

```bash
# 1. On the OLD box: dump the four FormShare indices + mappings + manifest
./venv-es7/bin/python formshare/scripts/exportelasticsearch.py \
    --host old-es.internal --port 9200 \
    --output ./es_dump

# 2. Copy ./es_dump to the new box (scp/rsync), then on the NEW box:
./venv-es9/bin/python formshare/scripts/importelasticsearch.py \
    --host new-es.internal --port 9200 --scheme https \
    --user elastic --password 'SECRET' \
    --input ./es_dump
```

That's it. By default the four standard indices are handled:
`formshare_users`, `formshare_partners`, `formshare_datasets`,
`formshare_records`.

---

## Export — `exportelasticsearch.py`

Connects to the old server, scrolls every requested index, and writes to the
output directory:

* `<index>.ndjson` — the documents in ElasticSearch **bulk** format (one action
  line + one source line per doc; the same shape FormShare's `es_batch` uses).
  `_id` is preserved.
* `<index>.mapping.json` — the index's portable settings + mappings, so an empty
  new server can recreate the index faithfully.
* `manifest.json` — summary of the dump (source, indices, document counts,
  timestamp).

### Options

| Flag | Description |
|------|-------------|
| `--ini PATH` | Read connection defaults from a FormShare ini file |
| `--ini-group {user,partner,repository,records}` | Which `elasticsearch.<group>.*` keys to read host/port from (default: `user`) |
| `--host`, `--port` | Server host/port (override the ini) |
| `--scheme {http,https}` | Connection scheme (default: `http`, or `https` if `use_ssl=True`) |
| `--user`, `--password` | Basic-auth credentials (omit for no auth — typical on old 7.x) |
| `--url-prefix PREFIX` | URL path prefix of the cluster |
| `--no-verify-certs`, `--ca-certs PATH` | TLS handling for `https` |
| `-o, --output DIR` | Output directory (default: `./es_dump`) |
| `--index NAME` | Index to export; repeatable; overrides the default/ini set |
| `--all` | Export every non-system index on the cluster |
| `--scroll-size N` | Documents per scroll batch (default: `1000`) |
| `--scroll-time T` | Scroll keep-alive (default: `5m`) |
| `--limit N` | Stop after N documents per index (for testing) |

### Examples

Dump the four default indices from a local, unauthenticated 7.x server:

```bash
./venv-es7/bin/python formshare/scripts/exportelasticsearch.py \
    --host localhost --port 9200 -o ./es_dump
```

Pull the connection straight from the old FormShare ini (host/port/credentials
read from `elasticsearch.user.*`; custom index names honored):

```bash
./venv-es7/bin/python formshare/scripts/exportelasticsearch.py \
    --ini /opt/formshare_2x/production.ini -o ./es_dump
```

Dump a single custom index over https with basic auth:

```bash
./venv-es7/bin/python formshare/scripts/exportelasticsearch.py \
    --host es.old --port 9200 --scheme https \
    --user elastic --password 'SECRET' \
    --index my_custom_index -o ./es_dump
```

Dump **every** non-system index on the cluster:

```bash
./venv-es7/bin/python formshare/scripts/exportelasticsearch.py \
    --host es.old --port 9200 --all -o ./es_dump
```

Quick smoke test — only the first 50 docs per index:

```bash
./venv-es7/bin/python formshare/scripts/exportelasticsearch.py \
    --host localhost --port 9200 --limit 50 -o ./es_dump_test
```

---

## Import — `importelasticsearch.py`

Reads the NDJSON files and bulk-loads them onto the new server, preserving
`_id`. The new server **may be completely empty** — missing indices are
recreated from their `.mapping.json` sidecars.

### Index creation policy

For each NDJSON file the target index name comes from the embedded bulk action
lines (or `--index` / `--rename` overrides). Then:

* **index already exists** → documents are loaded into it as-is. This is what
  happens when FormShare 3.x has already been started and created the indices
  with its **new** mappings; those new mappings win.
* **index does not exist** → it is created from the `<index>.mapping.json`
  sidecar. `--no-create` disables this and relies on ES dynamic mapping.
* **`--recreate`** → the index is **deleted** first, then rebuilt from the
  sidecar. Destructive; only for a throw-away/empty target.

### Options

| Flag | Description |
|------|-------------|
| `--ini PATH` | Read connection defaults from a FormShare ini file |
| `--ini-group {user,partner,repository,records}` | Which `elasticsearch.<group>.*` keys to read host/port from (default: `user`) |
| `--host`, `--port` | Server host/port (override the ini) |
| `--scheme {http,https}` | Connection scheme |
| `--user`, `--password` | Basic-auth credentials (the new 3.x server uses auth) |
| `--url-prefix PREFIX` | URL path prefix of the cluster |
| `--no-verify-certs`, `--ca-certs PATH` | TLS handling for `https` |
| `-i, --input DIR` | Directory holding the dump (default: `./es_dump`) |
| `--file PATH` | Specific `.ndjson` file to load; repeatable; overrides `--input` scan |
| `--index NAME` | Force every loaded document into this index name |
| `--rename OLD=NEW` | Remap an index name; repeatable |
| `--chunk-size N` | Documents per bulk request (default: `500`) |
| `--replicas N` | Override `number_of_replicas` when creating indices |
| `--no-create` | Do not create missing indices (rely on dynamic mapping) |
| `--recreate` | **DELETE** each target index before loading (destructive) |
| `--refresh` | Refresh each index after loading it |
| `--limit N` | Stop after N documents per file (for testing) |

### Examples

Load a dump onto the new 9.x server with basic auth over https:

```bash
./venv-es9/bin/python formshare/scripts/importelasticsearch.py \
    --host es.new --port 9200 --scheme https \
    --user elastic --password 'SECRET' \
    --input ./es_dump
```

Pull the connection straight from the new FormShare 3.x ini:

```bash
./venv-es9/bin/python formshare/scripts/importelasticsearch.py \
    --ini /opt/formshare_3x/production.ini --input ./es_dump
```

Load a single file into a renamed index:

```bash
./venv-es9/bin/python formshare/scripts/importelasticsearch.py \
    --ini new.ini \
    --file ./es_dump/formshare_users.ndjson \
    --index formshare_users_v3
```

Rebuild a throw-away target from scratch and refresh when done:

```bash
./venv-es9/bin/python formshare/scripts/importelasticsearch.py \
    --ini new.ini --input ./es_dump --recreate --refresh
```

Bulk-load creating indices with zero replicas first (faster), then bump
replicas afterwards in Kibana/ES:

```bash
./venv-es9/bin/python formshare/scripts/importelasticsearch.py \
    --ini new.ini --input ./es_dump --replicas 0 --chunk-size 1000
```

---

## Connection model

Both scripts resolve the connection the same way, with **CLI flags always
overriding the ini file**:

* Host/port/`use_ssl`/`url_prefix` come from `elasticsearch.<ini-group>.*`
  (default group `user`); all four FormShare index groups normally share one
  cluster.
* Auth and scheme come from `elasticsearch.user.name` / `elasticsearch.user.password`
  / `elasticsearch.user.scheme` (the FormShare 3.x keys). On an old 2.x server
  these are usually absent → no auth, `http`.
* The literal `empty` user (FormShare's "no credentials" sentinel) is treated as
  no auth.

> If a deployment splits indices across **different** clusters, run the scripts
> once per index with explicit `--host/--port` and a single `--index`.

---

## Verifying the migration

Compare the per-index counts in `es_dump/manifest.json` against the new server:

```bash
cat ./es_dump/manifest.json     # documents exported per index

# document count on the new server (adjust auth/scheme)
curl -s -u elastic:SECRET 'https://es.new:9200/formshare_records/_count'
```

The import also prints `loaded: N ok, M failed` per file and a final total; a
non-zero failure count makes the script exit non-zero. Re-running the import is
**idempotent** — documents are overwritten by `_id`, never duplicated — so it is
safe to re-run after fixing a transient error.

---

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `cannot reach ElasticSearch at …` | Wrong host/port/scheme, or auth required — check `--scheme https`, `--user/--password`. |
| `UnsupportedProductError` / product-check failures | Wrong client major for the server. Use the **es7** venv for export, **es9** venv for import. |
| TLS / certificate errors over https | Pass `--ca-certs /path/ca.pem`, or `--no-verify-certs` for self-signed (test only). |
| `ModuleNotFoundError: gevent` | You ran via the console entry point. Run the script as a file: `venv/bin/python …script.py`. |
| Import says `relying on dynamic mapping` | No `.mapping.json` sidecar next to the `.ndjson`. Keep the sidecars, or start FormShare 3.x first so it creates the indices. |
| Some docs `failed` on import | Inspect the printed error lines (first 10 per file). Fix and re-run — idempotent by `_id`. |
