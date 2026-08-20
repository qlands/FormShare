# Downscaling Elasticsearch in production

Taking an existing FormShare deployment from five shards and a replica across
several nodes to one shard, no replica, on one node.

**Audience:** whoever runs the migration on a live server.

**Status.** The reasoning is backed by measurement (§1); the procedures in §3
and §4 are written from the code and the Elasticsearch APIs but have **not been
rehearsed against a production dataset**. Do §2 first, and read §5 before
retiring any node — that is where data actually gets lost.

---

## 1. Why

FormShare asks Elasticsearch for very little. Of the six indices, five are not
search at all: `formshare_records` is a `_id` lookup returning a schema and
table name, user and partner "search" is a leading-wildcard substring match, and
the feeds indices are not really implemented. Only `formshare_datasets` uses a
genuine capability — the `geotile_grid` + `geo_centroid` the map plugin uses to
cluster GPS points.

Measured on one shard on one node with a 512 MB heap:

| | |
|---|---|
| 10,000,000 GPS points | 1.88 GB, one segment |
| Heaviest map query (all points scanned, 10,000 clusters) | 79 ms |
| 100 concurrent users, viewports of 290–46,690 points | 693 refreshes/s, p50 135 ms, **zero errors** |
| 500 concurrent users | 659 refreshes/s, p50 562 ms, **zero errors, zero rejections, zero breaker trips** |
| Peak resident memory, idle → 500 users | 2,108 MB → 2,110 MB |

Load moved memory by two megabytes. Throughput plateaus rather than failing:
the search thread pool queues 34,000 deep, and circuit breakers shed work before
the heap is exhausted. A single node is not the constraint.

Against that, a five-shard index holding a few megabytes is all overhead — a
shard is a whole Lucene index with its own segments, memory and cluster-state
entry. And two nodes is the worst count available: a two-node cluster has a
quorum of two, so losing either leaves the survivor without a master and the
cluster read-only. Twice the failure surface, no fault tolerance. That begins at
three.

**Before you start, know what you are giving up.** With no replica there is one
copy of every index, and FormShare has **no rebuild-from-MySQL path** —
`export_elasticsearch`/`import_elasticsearch` are a 2.x→3.x migration tool, not
a reindexer. Everything in these indices is derivable from the database in
principle, but nothing derives it today. Until that exists, treat the dump in §3
as your only safety net.

## 2. The half that needs no migration

`number_of_replicas` is mutable on a live index. `number_of_shards` is not.

So do this first, on its own. It halves the shard count immediately, costs
nothing, and is reversible:

```bash
curl -XPUT -u elastic:PASS "$ES/formshare_*/_settings" \
     -H 'Content-Type: application/json' \
     -d '{"index":{"number_of_replicas":0}}'

curl -s -u elastic:PASS "$ES/_cat/indices?v&h=index,health,pri,rep,docs.count"
```

Every index should read `rep 0` and stay green. If you stop here you have
already removed half the shards and made the second node optional.

Reducing the shard count needs one of the two options below.

---

## 3. Option A — dump to NDJSON, delete, reload

Uses the tooling already in the repository. Best when you are also moving to a
different server, since the dump is portable.

### The trap

`import_elasticsearch` recreates a missing index from the `.mapping.json`
sidecar written at export time, and `create_index_from_sidecar` copies those
settings **verbatim** — including `number_of_shards: 5`. There is a `--replicas`
override; there is no `--shards`. A straight round trip faithfully rebuilds
exactly what you are trying to remove.

### The way around it

Do not let the importer create the indices. FormShare creates any that are
missing at startup (`formshare/config/config_indexes.py`), using the defaults in
`formshare/processes/elasticsearch/*_index.py` — now one shard and no replica —
and the correct mappings. Then load into what it made, with `--no-create`.

```bash
# 1. Stop FormShare and its celery workers, so nothing indexes mid-dump.

# 2. Dump every index, and keep it somewhere that is not this server.
export_elasticsearch --ini /path/to/production.ini --all \
                     --output /backup/es-$(date +%F)

# 3. Verify the dump BEFORE destroying anything.
cat /backup/es-*/manifest.json
wc -l /backup/es-*/*.ndjson
#    Each .ndjson holds two lines per document (an action line and a source
#    line), so the line count should be twice the document count in the
#    manifest. If it is not, stop.

# 4. Drop the indices.
curl -XDELETE -u elastic:PASS \
  "$ES/formshare_datasets,formshare_records,formshare_users,formshare_partners"

# 5. Start FormShare. It recreates all four on boot.

# 6. Confirm the new geometry before loading a single document.
curl -s -u elastic:PASS "$ES/_cat/indices?v&h=index,pri,rep,docs.count"
#    Expect pri 1, rep 0, docs.count 0.

# 7. Load the documents into the indices FormShare just created.
import_elasticsearch --ini /path/to/production.ini \
                     --input /backup/es-$(date +%F)/ --no-create

# 8. Compare counts against the manifest from step 3.
curl -s -u elastic:PASS "$ES/_cat/indices?v&h=index,pri,rep,docs.count"
```

`_id` is preserved on both sides. That matters more than it looks:
`formshare_records` is looked up **by `_id`** (the rowuuid) to find which schema
and table a record lives in, so an import that reassigned ids would silently
break API cleaning while looking like it worked.

### What this does not cover

`formshare_feeds` and `formshare_network` belong to elasticfeeds, not to
FormShare's index modules, so nothing recreates them at startup. `--all` dumps
them; if you delete them, recreate them yourself or let elasticfeeds do it, and
check their shard count afterwards.

## 4. Option B — reindex in place *(recommended when staying on the same cluster)*

Option A makes you delete your only copy and trust a file. `_reindex` never
does: the old index stays untouched until you choose to remove it.

Per index — `formshare_datasets` shown, repeat for `records`, `users`,
`partners`:

```bash
# 1. Capture the current mappings. Keep them; you are reusing them exactly.
curl -s -u elastic:PASS "$ES/formshare_datasets/_mapping" > ds-mapping.json

# 2. Create the replacement with the geometry you want and those mappings.
curl -XPUT -u elastic:PASS "$ES/formshare_datasets_v2" \
     -H 'Content-Type: application/json' -d '{
       "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
       "mappings": <the "mappings" object from step 1>
     }'

# 3. Copy. _id is preserved.
curl -XPOST -u elastic:PASS "$ES/_reindex?wait_for_completion=true" \
     -H 'Content-Type: application/json' -d '{
       "source": {"index": "formshare_datasets"},
       "dest":   {"index": "formshare_datasets_v2"}
     }'

# 4. Compare counts. Do not proceed until they match.
curl -s -u elastic:PASS "$ES/_cat/indices?v&h=index,pri,rep,docs.count"

# 5. Swap. FormShare addresses the index by the name in its ini, and a
#    single-index alias accepts writes, so an alias is transparent to it.
curl -XDELETE -u elastic:PASS "$ES/formshare_datasets"
curl -XPOST -u elastic:PASS "$ES/_aliases" -H 'Content-Type: application/json' \
     -d '{"actions":[{"add":{"index":"formshare_datasets_v2",
                             "alias":"formshare_datasets"}}]}'
```

Stop FormShare for steps 3–5 so nothing is written to the old index after the
copy begins. At FormShare's volumes the whole thing takes seconds.

If you would rather not live with an alias, reindex `_v2` back into a freshly
created `formshare_datasets` afterwards and drop `_v2`. Two hops, no aliases,
same result.

### `_shrink`, and why it is not the first suggestion

`_shrink` exists for precisely this and 5 → 1 is legal, since the target must
divide the source. But it requires the index to be made read-only and every
primary shard relocated onto one node first. That is more moving parts than
`_reindex` for a few megabytes of data.

## 5. Only then: three nodes down to one

This is the step that loses data if it is done out of order. With no replica
there is no second copy, so a node that still holds a shard when you stop it
takes that shard with it.

```bash
# 1. Replicas already at 0 (§2), shard counts already reduced (§3 or §4).

# 2. Tell the cluster to move everything off the nodes you are retiring.
curl -XPUT -u elastic:PASS "$ES/_cluster/settings" \
     -H 'Content-Type: application/json' \
     -d '{"persistent":{"cluster.routing.allocation.exclude._name":"es02,es03"}}'

# 3. WAIT. Green, and nothing relocating or initialising.
watch -n 5 "curl -s -u elastic:PASS '$ES/_cat/health?v'"

# 4. Prove no shard is left on them before stopping anything.
curl -s -u elastic:PASS "$ES/_cat/shards?v&h=index,shard,prirep,state,node"
#    Every row must name the surviving node.

# 5. Now stop es02 and es03, and switch to the single-node compose file.

# 6. Clear the exclusion so the surviving node is not excluded from itself
#    if you ever rename it.
curl -XPUT -u elastic:PASS "$ES/_cluster/settings" \
     -H 'Content-Type: application/json' \
     -d '{"persistent":{"cluster.routing.allocation.exclude._name":null}}'
```

Going to `discovery.type: single-node` also drops the transport TLS requirement,
because there is no longer any node-to-node traffic to encrypt. `docker_compose/servers.yml`
has the details, including the startup warning that is expected and not a fault.

## 6. Checks that mean something afterwards

Counts matching is necessary, not sufficient. These exercise the three things
that would break quietly:

```bash
# geometry is what you asked for
curl -s -u elastic:PASS "$ES/_cat/indices?v&h=index,health,pri,rep,docs.count"

# the records index still answers by _id -- take a rowuuid from a repository
curl -s -u elastic:PASS "$ES/formshare_records/_doc/<a-real-rowuuid>"
#   must return schema and table
```

Then, in FormShare itself: open a project map and confirm points and clusters
still draw (the `geo_point` mapping survived), and search for a user by a
fragment of their name (the `all_data` copy_to field and the email analyser
survived). A reindex or import that lost a custom analyser will still report the
right document count.

## 7. Still worth building

A **rebuild-from-MySQL command**. Every document in these four indices is
derivable: datasets and records from the repository tables, users and partners
from their tables. With it, this whole procedure becomes "drop and regenerate",
replicas become a convenience rather than the only copy, and a corrupted index
stops being an incident. Without it, a single node means a single copy of
something nothing can reproduce.

Also small, if Option A is going to be used more than once: add a `--shards`
flag to `import_elasticsearch` beside the existing `--replicas`, so
`create_index_from_sidecar` can override the exported shard count instead of
relying on FormShare having created the index first.
