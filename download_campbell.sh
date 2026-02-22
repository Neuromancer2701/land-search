#!/bin/bash
# Download Campbell County parcels using curl batches, merge with Python
set -e

QUERY_URL="https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer/0/query"
BATCH_SIZE=2000
TOTAL=37826
OUTPUT_DIR="campbell"
TEMP_DIR="${OUTPUT_DIR}/batches"

mkdir -p "$TEMP_DIR"

offset=0
while [ $offset -lt $TOTAL ]; do
    echo "Downloading batch at offset $offset..."
    outfile="${TEMP_DIR}/batch_${offset}.json"

    if [ -f "$outfile" ] && [ -s "$outfile" ]; then
        echo "  Already exists, skipping."
    else
        curl -s --max-time 120 \
            "${QUERY_URL}?where=1%3D1&outFields=*&f=geojson&resultOffset=${offset}&resultRecordCount=${BATCH_SIZE}" \
            -o "$outfile"

        if [ ! -s "$outfile" ]; then
            echo "  ERROR: Empty file, retrying..."
            sleep 5
            curl -s --max-time 120 \
                "${QUERY_URL}?where=1%3D1&outFields=*&f=geojson&resultOffset=${offset}&resultRecordCount=${BATCH_SIZE}" \
                -o "$outfile"
        fi
    fi

    size=$(stat -c%s "$outfile" 2>/dev/null || echo 0)
    echo "  File size: ${size} bytes"
    offset=$((offset + BATCH_SIZE))
done

echo ""
echo "All batches downloaded. Merging with Python..."

python3 -c "
import json, glob, os

batch_dir = '${TEMP_DIR}'
output_file = '${OUTPUT_DIR}/parcels_complete.geojson'

all_features = []
for f in sorted(glob.glob(os.path.join(batch_dir, 'batch_*.json'))):
    print(f'  Reading {f}...')
    with open(f) as fh:
        data = json.load(fh)
        features = data.get('features', [])
        all_features.extend(features)
        print(f'    {len(features)} features (total: {len(all_features)})')

geojson = {'type': 'FeatureCollection', 'features': all_features}
with open(output_file, 'w') as fh:
    json.dump(geojson, fh)

size_mb = os.path.getsize(output_file) / (1024*1024)
print(f'\nSaved {len(all_features)} features to {output_file} ({size_mb:.1f} MB)')
"

echo "Cleaning up batch files..."
rm -rf "$TEMP_DIR"
echo "Done!"
