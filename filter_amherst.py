#!/usr/bin/env python3
"""
Filter Amherst County properties and append matching results to matching_properties.csv.
Criteria: 5-25 acres, 1800+ sqft, 3+ beds, 2+ baths, <=25 min commute to both Lynchburg locations.
"""
import json
import csv
import sys
import os
import time
import math
from urllib.request import Request, urlopen
from urllib.parse import quote
import ssl

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

os.chdir('/home/count_zero/Repos/House_Search_GIS')

DEST1 = "2424 Rivermont Ave, Lynchburg, VA 24503"
DEST2 = "122 Fleetwood Dr, Lynchburg, VA 24501"
MAX_COMMUTE_MIN = 25
MAX_DISTANCE_MILES = 25

# Pre-geocoded destinations (from previous runs)
D1_LAT, D1_LON = 37.4365294, -79.1681415
D2_LAT, D2_LON = 37.3955192, -79.2061156


def safe_float(val, default=0):
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def get_drive_time(origin_lat, origin_lon, dest_lat, dest_lon):
    """Get driving time in minutes using OSRM."""
    url = f"http://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"
    req = Request(url, headers={'User-Agent': 'PropertySearch/1.0'})
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if data.get('code') == 'Ok' and data.get('routes'):
            return data['routes'][0]['duration'] / 60
    except Exception:
        pass
    return None


def polygon_centroid(coords):
    ring = coords[0] if coords else []
    if not ring:
        return None, None
    n = len(ring)
    return sum(p[1] for p in ring) / n, sum(p[0] for p in ring) / n


def filter_amherst():
    """Filter Amherst County parcels by property criteria and distance."""
    print("=== AMHERST COUNTY ===")
    print("  Loading parcels with assessment data...")

    with open('amherst/parcels_with_assessment.geojson') as f:
        data = json.load(f)

    print(f"  Total parcels: {len(data['features'])}")

    candidates = []
    skipped = {'no_acreage': 0, 'acreage': 0, 'sqft': 0, 'beds': 0, 'baths': 0,
               'no_geom': 0, 'distance': 0, 'no_addr': 0, 'commercial': 0}

    for feat in data['features']:
        p = feat['properties']

        # Filter acreage
        acreage = safe_float(p.get('MACRE_'))
        if acreage == 0:
            skipped['no_acreage'] += 1
            continue
        if acreage < 5 or acreage > 25:
            skipped['acreage'] += 1
            continue

        # Filter sqft
        sqft = safe_int(p.get('CNS_AREA_LIVING'))
        if sqft < 1800:
            skipped['sqft'] += 1
            continue

        # Filter bedrooms
        bedrooms = safe_int(p.get('M_BR'))
        if bedrooms < 3:
            skipped['beds'] += 1
            continue

        # Filter too many bedrooms (likely commercial)
        if bedrooms > 8:
            skipped['commercial'] += 1
            continue

        # Filter bathrooms (M_FBTH = full, M_HBTH = half)
        full_baths = safe_int(p.get('M_FBTH'))
        half_baths = safe_int(p.get('M_HBTH'))
        total_baths = full_baths + half_baths * 0.5
        if total_baths < 2:
            skipped['baths'] += 1
            continue

        # Get centroid
        geom = feat.get('geometry')
        if not geom or not geom.get('coordinates'):
            skipped['no_geom'] += 1
            continue
        if geom['type'] == 'Polygon':
            lat, lon = polygon_centroid(geom['coordinates'])
        elif geom['type'] == 'MultiPolygon':
            lat, lon = polygon_centroid(geom['coordinates'][0])
        else:
            skipped['no_geom'] += 1
            continue
        if not lat or not lon:
            skipped['no_geom'] += 1
            continue

        # Distance pre-filter
        d1 = haversine_miles(lat, lon, D1_LAT, D1_LON)
        d2 = haversine_miles(lat, lon, D2_LAT, D2_LON)
        if d1 > MAX_DISTANCE_MILES or d2 > MAX_DISTANCE_MILES:
            skipped['distance'] += 1
            continue

        # Address
        addr1 = str(p.get('ParcelAddress1', '')).strip()
        addr2 = str(p.get('ParcelAddress2', '')).strip()
        if not addr1:
            skipped['no_addr'] += 1
            continue

        # Skip PO Box addresses
        if 'PO BOX' in addr1.upper() or 'P.O. BOX' in addr1.upper():
            skipped['no_addr'] += 1
            continue

        full_addr = f"{addr1}, {addr2}" if addr2 else addr1

        # Owner name
        owner_last = str(p.get('MLNAM', '')).strip()
        owner_first = str(p.get('MFNAM', '')).strip()
        owner = f"{owner_last} {owner_first}".strip()

        # Tax assessment - use REVAL_Total_Market_Value or MTOTPR
        tax_val = safe_float(p.get('REVAL_Total_Market_Value'))
        if tax_val == 0:
            tax_val = safe_float(p.get('MTOTPR'))

        year_built = str(safe_int(p.get('MYRBLT'))) if safe_int(p.get('MYRBLT')) > 0 else ''

        candidates.append({
            'county': 'Amherst',
            'address': full_addr,
            'loc_addr': addr1,
            'lat': lat, 'lon': lon,
            'acreage': acreage,
            'sqft': sqft,
            'bedrooms': bedrooms,
            'total_baths': total_baths,
            'year_built': year_built,
            'tax_assessment': tax_val if tax_val > 0 else '',
            'owner': owner,
        })

    print(f"\n  Filter results:")
    for reason, count in skipped.items():
        if count > 0:
            print(f"    Skipped ({reason}): {count}")
    print(f"  Candidates within {MAX_DISTANCE_MILES} miles: {len(candidates)}")
    return candidates


if __name__ == '__main__':
    candidates = filter_amherst()

    if not candidates:
        print("\nNo Amherst candidates found within distance filter.")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"  Checking drive times for {len(candidates)} candidates via OSRM...")
    print(f"{'='*60}")

    amherst_matches = []
    for i, prop in enumerate(candidates):
        if i % 10 == 0:
            print(f"  Progress: {i+1}/{len(candidates)}...")

        t1 = get_drive_time(prop['lat'], prop['lon'], D1_LAT, D1_LON)
        time.sleep(0.1)
        t2 = get_drive_time(prop['lat'], prop['lon'], D2_LAT, D2_LON)
        time.sleep(0.1)

        if t1 is not None and t2 is not None:
            prop['commute_rivermont'] = round(t1, 1)
            prop['commute_fleetwood'] = round(t2, 1)

            if t1 <= MAX_COMMUTE_MIN and t2 <= MAX_COMMUTE_MIN:
                amherst_matches.append(prop)
                print(f"    MATCH: {prop['loc_addr']} - "
                      f"{t1:.0f}/{t2:.0f} min | {prop['sqft']}sqft {prop['bedrooms']}bd "
                      f"{prop['total_baths']}ba {prop['acreage']}ac")

    print(f"\n{'='*60}")
    print(f"  AMHERST MATCHES: {len(amherst_matches)}")
    print(f"{'='*60}")

    if not amherst_matches:
        print("\nNo Amherst properties met all criteria.")
        sys.exit(0)

    # Deduplicate by address
    seen = set()
    unique_matches = []
    for m in amherst_matches:
        addr_key = m['address'].upper().strip()
        if addr_key not in seen:
            seen.add(addr_key)
            unique_matches.append(m)
    amherst_matches = unique_matches
    print(f"  After dedup: {len(amherst_matches)}")

    # Read existing CSV and append Amherst results
    existing_rows = []
    with open('matching_properties.csv', 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            existing_rows.append(row)

    print(f"\n  Existing properties in CSV: {len(existing_rows)}")
    print(f"  Adding {len(amherst_matches)} Amherst properties...")

    with open('matching_properties.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in existing_rows:
            writer.writerow(row)
        for p in sorted(amherst_matches, key=lambda x: max(x['commute_rivermont'], x['commute_fleetwood'])):
            writer.writerow([
                p['address'],
                p['sqft'],
                p.get('tax_assessment', ''),
                p['commute_rivermont'],
                p['commute_fleetwood'],
                p['county'],
                p['acreage'],
                p['bedrooms'],
                p['total_baths'],
                p['year_built'],
                p['owner'],
            ])

    total = len(existing_rows) + len(amherst_matches)
    print(f"\n  CSV updated: {total} total properties in matching_properties.csv")
