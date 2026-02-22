#!/usr/bin/env python3
"""
Download parcel data from Virginia county GIS services.
Uses only Python standard library (no external packages required).
"""
import json
import os
import sys
import urllib.request
import urllib.parse
import ssl
import time
from pathlib import Path


def query_service(query_url, params, retries=3, delay=5):
    """Make a query to an ArcGIS REST service with retries."""
    encoded = urllib.parse.urlencode(params)
    url = f"{query_url}?{encoded}"

    for attempt in range(retries):
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < retries - 1:
                print(f"  Retry {attempt + 1}/{retries} after error: {e}")
                time.sleep(delay)
            else:
                raise


def download_parcels(service_url, layer_id, output_dir, batch_size=1000):
    """
    Download all parcels from an ArcGIS REST service.

    Args:
        service_url: Base URL of the MapServer/FeatureServer
        layer_id: Layer ID to query
        output_dir: Directory to save output
        batch_size: Number of features per request
    """
    query_url = f"{service_url}/{layer_id}/query"

    # Get total count
    print(f"Getting total count from {service_url}...")
    count_data = query_service(query_url, {
        'where': '1=1',
        'returnCountOnly': 'true',
        'f': 'json'
    })
    total_count = count_data['count']
    print(f"Total features: {total_count}")

    # Download in batches
    all_features = []
    offset = 0

    while offset < total_count:
        print(f"Downloading features {offset} to {min(offset + batch_size, total_count)} of {total_count}...")

        data = query_service(query_url, {
            'where': '1=1',
            'outFields': '*',
            'f': 'geojson',
            'resultOffset': offset,
            'resultRecordCount': batch_size
        })

        features = data.get('features', [])

        if not features:
            print("  No more features returned, stopping.")
            break

        all_features.extend(features)
        offset += len(features)
        pct = (offset / total_count) * 100
        print(f"  Got {len(features)} features (total: {len(all_features)}, {pct:.1f}%)")

    # Build GeoJSON FeatureCollection
    geojson = {
        'type': 'FeatureCollection',
        'features': all_features
    }

    # Save to file
    output_path = Path(output_dir) / 'parcels_complete.geojson'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(geojson, f)

    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"Saved {len(all_features)} features to {output_path} ({file_size:.1f} MB)")
    return len(all_features)


if __name__ == '__main__':
    counties = {
        'campbell': {
            'url': 'https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer',
            'layer': 0
        },
        'bedford': {
            'url': 'https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer',
            'layer': 0
        }
    }

    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target and target in counties:
        targets = [(target, counties[target])]
    elif target:
        print(f"Unknown county: {target}")
        print(f"Available: {', '.join(counties.keys())}")
        sys.exit(1)
    else:
        targets = list(counties.items())

    for name, config in targets:
        print(f"\n{'=' * 60}")
        print(f"  {name.upper()} COUNTY")
        print(f"{'=' * 60}")
        try:
            download_parcels(config['url'], config['layer'], name)
        except Exception as e:
            print(f"ERROR downloading {name}: {e}")
            import traceback
            traceback.print_exc()

    print("\nAll downloads complete!")
