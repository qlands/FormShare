#!/usr/bin/env python3
"""
Import ndjson files into Elasticsearch.

Run this against the NEW ES 9.2.1 cluster after it is started.

Usage:
    python import_es_indexes.py [ES_HOST] [INPUT_DIR]

    ES_HOST   — Elasticsearch URL (default: http://localhost:9200)
    INPUT_DIR — directory containing ndjson + mapping files (default: ./es_export)

Expects files produced by export_es_indexes.py:
    <index_name>.ndjson         — bulk-API-ready document data
    <index_name>_mapping.json   — index mapping snapshot
"""

import json
import os
import sys

from elasticsearch import Elasticsearch

ES_HOST = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9200"
INPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "./es_export"

# Number of action+source line pairs per bulk request (2500 docs)
BATCH_SIZE = 5000


def clean_mapping(mapping):
    """Extract only the mappings block, stripping version-specific settings.

    ES 9.x removed _type and has different default settings than 7.x,
    so we only keep the field mappings to avoid compatibility errors.
    """
    body = {}

    if "mappings" in mapping:
        mappings = mapping["mappings"]
        # ES 7.x may still have a _type wrapper — unwrap it
        if isinstance(mappings, dict):
            keys = list(mappings.keys())
            if len(keys) == 1 and keys[0] not in (
                "properties",
                "dynamic",
                "_source",
                "_meta",
            ):
                # Single type name wrapping the actual mapping
                mappings = mappings[keys[0]]
        body["mappings"] = mappings

    return body


def main():
    es = Elasticsearch(ES_HOST)

    info = es.info()
    print("Connected to ES {} at {}".format(info["version"]["number"], ES_HOST))

    if not os.path.isdir(INPUT_DIR):
        print("ERROR: Input directory does not exist: {}".format(INPUT_DIR))
        sys.exit(1)

    # Find all ndjson files
    ndjson_files = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".ndjson"))

    if not ndjson_files:
        print("No .ndjson files found in {}".format(INPUT_DIR))
        return

    print("Found {} indexes to import".format(len(ndjson_files)))
    print()

    total_docs = 0
    total_errors = 0

    for ndjson_file in ndjson_files:
        index_name = ndjson_file.replace(".ndjson", "")
        mapping_file = os.path.join(INPUT_DIR, "{}_mapping.json".format(index_name))
        ndjson_path = os.path.join(INPUT_DIR, ndjson_file)

        # Create index with mapping
        if os.path.exists(mapping_file):
            with open(mapping_file) as f:
                raw_mapping = json.load(f)
            body = clean_mapping(raw_mapping)
        else:
            body = {}

        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name, body=body)
            print("Created index: {}".format(index_name))
        else:
            print("Index already exists: {} (skipping creation)".format(index_name))

        # Check for empty export
        file_size = os.path.getsize(ndjson_path)
        if file_size == 0:
            print("  {} documents (empty file)".format(0))
            continue

        # Bulk import in batches
        count = 0
        errors = 0
        batch = []

        with open(ndjson_path) as f:
            for line in f:
                batch.append(line)
                if len(batch) >= BATCH_SIZE:
                    err = _send_batch(es, batch)
                    count += len(batch) // 2
                    errors += err
                    batch = []

            if batch:
                err = _send_batch(es, batch)
                count += len(batch) // 2
                errors += err

        status = "  {} documents imported".format(count)
        if errors:
            status += " ({} errors)".format(errors)
        print(status)

        total_docs += count
        total_errors += errors

    print()
    print(
        "Import complete. {} documents imported, {} errors.".format(
            total_docs, total_errors
        )
    )


def _send_batch(es, batch):
    """Send a bulk request and return the number of errors."""
    resp = es.bulk(body="".join(batch))
    error_count = 0
    if resp.get("errors"):
        for item in resp.get("items", []):
            index_result = item.get("index", {})
            if "error" in index_result:
                error_count += 1
                print(
                    "    Error on doc {}: {}".format(
                        index_result.get("_id", "?"),
                        index_result["error"].get("reason", index_result["error"]),
                    )
                )
    return error_count


if __name__ == "__main__":
    main()
