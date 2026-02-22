#!/usr/bin/env python3
"""Download improvement/assessment tables for Bedford and Campbell counties."""
import json
import subprocess
import sys
import os
import time
from urllib.parse import urlencode

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)


def fetch_with_curl(url, params, timeout=120):
    """Use curl for reliable downloading."""
    full_url = f"{url}?{urlencode(params)}"
    for attempt in range(3):
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', str(timeout), full_url],
                capture_output=True, text=True, timeout=timeout + 30
            )
            if result.returncode != 0:
                raise Exception(f"curl exit code {result.returncode}")
            return json.loads(result.stdout)
        except Exception as e:
            print(f"  Attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                raise


def download_table(query_url, output_file, batch_size=1000):
    """Download an ArcGIS table (no geometry)."""
    print(f"Getting count from {query_url}...")
    data = fetch_with_curl(query_url, {
        'where': '1=1', 'returnCountOnly': 'true', 'f': 'json'
    })
    total = data['count']
    print(f"Total records: {total}")

    all_records = []
    offset = 0
    while offset < total:
        pct = offset * 100 // total
        print(f"Downloading {offset}-{min(offset+batch_size, total)} of {total} ({pct}%)...")
        data = fetch_with_curl(query_url, {
            'where': '1=1',
            'outFields': '*',
            'returnGeometry': 'false',
            'f': 'json',
            'resultOffset': offset,
            'resultRecordCount': batch_size
        })
        features = data.get('features', [])
        if not features:
            break
        for f in features:
            all_records.append(f.get('attributes', {}))
        offset += len(features)
        print(f"  Got {len(features)} (total: {len(all_records)})")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(all_records, f)
    size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"Saved {len(all_records)} records to {output_file} ({size_mb:.1f} MB)")
    return all_records


# Bedford improvements
print("=" * 60)
print("  BEDFORD COUNTY - Real Estate Improvements")
print("=" * 60)
download_table(
    "https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer/6/query",
    "bedford/improvements.json"
)

print("\nDone!")
