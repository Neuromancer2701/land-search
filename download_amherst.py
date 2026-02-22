#!/usr/bin/env python3
"""Download Amherst County parcels with assessment data from ArcGIS FeatureServer."""

import json
import os
import sys
import subprocess
import time

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

BASE_URL = "https://services8.arcgis.com/TvqqWejphpVuqRec/arcgis/rest/services/Amherst_WL_P/FeatureServer/30/query"
OUT_DIR = "/home/count_zero/Repos/House_Search_GIS/amherst"
OUT_FILE = os.path.join(OUT_DIR, "parcels_with_assessment.geojson")
BATCH_SIZE = 2000

os.makedirs(OUT_DIR, exist_ok=True)

all_features = []
offset = 0
total = 26164

while offset < total:
    print(f"Downloading records {offset}-{offset+BATCH_SIZE}...")
    params = (
        f"where=1%3D1"
        f"&outFields=*"
        f"&outSR=4326"
        f"&returnGeometry=true"
        f"&resultOffset={offset}"
        f"&resultRecordCount={BATCH_SIZE}"
        f"&f=geojson"
    )
    url = f"{BASE_URL}?{params}"

    for attempt in range(3):
        try:
            result = subprocess.run(
                ["curl", "-s", "--connect-timeout", "30", "--max-time", "120", url],
                capture_output=True, text=True, timeout=150
            )
            data = json.loads(result.stdout)
            features = data.get("features", [])
            all_features.extend(features)
            print(f"  Got {len(features)} features (total: {len(all_features)})")
            break
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                print("  FATAL: giving up on this batch")

    offset += BATCH_SIZE
    time.sleep(0.5)  # Be polite

# Write GeoJSON
print(f"\nWriting {len(all_features)} features to {OUT_FILE}...")
geojson = {
    "type": "FeatureCollection",
    "features": all_features
}
with open(OUT_FILE, 'w') as f:
    json.dump(geojson, f)

file_size = os.path.getsize(OUT_FILE) / (1024 * 1024)
print(f"Done! File size: {file_size:.1f} MB")
