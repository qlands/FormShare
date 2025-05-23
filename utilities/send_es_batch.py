import os
import requests
import datetime

ES_HOST = "http://localhost:9200"
NDJSON_DIR = "/opt/formshare/repository/es_batch/dataset_index"
MAX_MB = 10
MAX_BYTES = MAX_MB * 1024 * 1024


def send_bulk_to_es(payload, bulk_number):
    print("Sending bulk to ES of {} elements".format(bulk_number))
    headers = {"Content-Type": "application/x-ndjson"}
    response = requests.post(f"{ES_HOST}/_bulk", headers=headers, data=payload)
    if response.status_code != 200 or response.json().get("errors"):
        print("❌ Error in bulk {} request: {}".format(bulk_number, response.text))
        exit(1)
    else:
        print("✅ Bulk {} indexed successfully".format(bulk_number))


def process_directory():
    start_time = datetime.datetime.now()
    current_batch = []
    current_size = 0
    bulk_number = 0
    for filename in sorted(os.listdir(NDJSON_DIR)):
        bulk_number = bulk_number + 1
        if not filename.endswith(".ndjson"):
            continue
        path = os.path.join(NDJSON_DIR, filename)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        size = len(content.encode("utf-8"))

        # Check if adding this file would exceed the limit
        if current_size + size > MAX_BYTES and current_batch:
            payload = "".join(current_batch)
            send_bulk_to_es(payload, bulk_number)
            current_batch = []
            current_size = 0

        current_batch.append(content)
        current_size += size

    # Send last batch if any
    if current_batch:
        payload = "".join(current_batch)
        send_bulk_to_es(payload, bulk_number)

    end_time = datetime.datetime.now()
    time_delta = end_time - start_time
    total_seconds = time_delta.total_seconds()
    minutes = total_seconds / 60
    print("Finished in {} minutes".format(minutes))


if __name__ == "__main__":
    process_directory()
