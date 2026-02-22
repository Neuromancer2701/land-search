#!/usr/bin/env python3
"""Download Campbell County parcels using curl subprocess for reliability."""
import json
import subprocess
import sys
import os
import time

QUERY_URL = "https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer/0/query"
BATCH_SIZE = 2000
OUTPUT_FILE = "campbell/parcels_complete.geojson"

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

def fetch_with_curl(params, timeout=300):
    """Use curl subprocess for more reliable downloading."""
    from urllib.parse import urlencode
    url = f"{QUERY_URL}?{urlencode(params)}"

    for attempt in range(3):
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', str(timeout), url],
                capture_output=True, text=True, timeout=timeout + 30
            )
            if result.returncode != 0:
                raise Exception(f"curl exit code {result.returncode}")
            return json.loads(result.stdout)
        except Exception as e:
            print(f"  Attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(10)
            else:
                raise

# Get count
print("Getting total count...")
data = fetch_with_curl({'where': '1=1', 'returnCountOnly': 'true', 'f': 'json'}, timeout=60)
total = data['count']
print(f"Total parcels: {total}")

# Download batches
all_features = []
offset = 0

while offset < total:
    remaining = total - offset
    batch = min(BATCH_SIZE, remaining)
    pct = offset * 100 // total
    print(f"Downloading {offset}-{offset+batch} of {total} ({pct}%)...")

    start = time.time()
    data = fetch_with_curl({
        'where': '1=1',
        'outFields': '*',
        'f': 'geojson',
        'resultOffset': offset,
        'resultRecordCount': batch
    })
    elapsed = time.time() - start

    features = data.get('features', [])
    if not features:
        print("  No features returned, stopping.")
        break

    all_features.extend(features)
    offset += len(features)
    print(f"  Got {len(features)} features in {elapsed:.0f}s (total: {len(all_features)})")

# Save
print(f"\nSaving {len(all_features)} features...")
os.makedirs("campbell", exist_ok=True)
geojson = {'type': 'FeatureCollection', 'features': all_features}

with open(OUTPUT_FILE, 'w') as f:
    json.dump(geojson, f)

size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
print(f"Done! Saved to {OUTPUT_FILE} ({size_mb:.1f} MB)")
