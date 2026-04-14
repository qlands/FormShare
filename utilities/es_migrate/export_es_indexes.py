#!/usr/bin/env python3
"""
Export all non-system Elasticsearch indexes to ndjson files.

Run this against the OLD ES 7.14.2 cluster before shutting it down.

Usage:
    python export_es_indexes.py [ES_HOST] [OUTPUT_DIR]

    ES_HOST    — Elasticsearch URL (default: http://localhost:9200)
    OUTPUT_DIR — directory to write ndjson + mapping files (default: ./es_export)

Each index produces two files:
    <index_name>.ndjson         — bulk-API-ready document data
    <index_name>_mapping.json   — index mapping and settings snapshot
"""

import json
import os
import sys

from elasticsearch import Elasticsearch

ES_HOST = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9200"
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "./es_export"


def main():
    es = Elasticsearch(ES_HOST)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    info = es.info()
    print("Connected to ES {} at {}".format(info["version"]["number"], ES_HOST))

    # Get all non-system indexes
    all_indexes = es.indices.get_alias(index="*")
    indexes = sorted(idx for idx in all_indexes if not idx.startswith("."))

    if not indexes:
        print("No indexes found.")
        return

    print("Found {} indexes: {}".format(len(indexes), ", ".join(indexes)))
    print()

    for index_name in indexes:
        print("Exporting {}...".format(index_name))

        # Save mapping + settings
        mapping = es.indices.get(index=index_name)[index_name]
        mapping_path = os.path.join(OUTPUT_DIR, "{}_mapping.json".format(index_name))
        with open(mapping_path, "w") as f:
            json.dump(mapping, f, indent=2)

        # Scroll through all documents
        out_path = os.path.join(OUTPUT_DIR, "{}.ndjson".format(index_name))
        count = 0

        with open(out_path, "w") as f:
            resp = es.search(
                index=index_name,
                scroll="5m",
                size=1000,
                body={"query": {"match_all": {}}},
            )
            scroll_id = resp["_scroll_id"]
            hits = resp["hits"]["hits"]

            while hits:
                for hit in hits:
                    action = {"index": {"_index": index_name, "_id": hit["_id"]}}
                    f.write(json.dumps(action) + "\n")
                    f.write(json.dumps(hit["_source"]) + "\n")
                    count += 1

                resp = es.scroll(scroll_id=scroll_id, scroll="5m")
                scroll_id = resp["_scroll_id"]
                hits = resp["hits"]["hits"]

            es.clear_scroll(scroll_id=scroll_id)

        print("  {} documents -> {}".format(count, out_path))

    print()
    print("Export complete. Files written to {}".format(OUTPUT_DIR))


if __name__ == "__main__":
    main()
