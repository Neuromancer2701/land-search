#!/usr/bin/env python3
"""
Filter properties by commute time to two Lynchburg locations.
Uses OSRM (free routing) for drive time estimates.
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

DEST1 = "2424 Rivermont Ave, Lynchburg, VA 24503"
DEST2 = "122 Fleetwood Dr, Lynchburg, VA 24501"
MAX_COMMUTE_MIN = 25
MAX_DISTANCE_MILES = 25


def safe_float(val, default=0):
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default


def geocode(address):
    """Geocode an address using Nominatim."""
    ctx = ssl.create_default_context()
    url = f"https://nominatim.openstreetmap.org/search?q={quote(address)}&format=json&limit=1"
    req = Request(url, headers={'User-Agent': 'PropertySearch/1.0'})
    with urlopen(req, context=ctx, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if data:
        return float(data[0]['lat']), float(data[0]['lon'])
    return None, None


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
    except Exception as e:
        pass
    return None


def polygon_centroid(coords):
    ring = coords[0] if coords else []
    if not ring:
        return None, None
    n = len(ring)
    return sum(p[1] for p in ring) / n, sum(p[0] for p in ring) / n


def build_coord_index(geojson_path, key_field):
    """Build a dict of key -> (lat, lon) from GeoJSON parcel data."""
    print(f"  Loading {geojson_path}...")
    with open(geojson_path) as f:
        data = json.load(f)
    coords = {}
    for feat in data['features']:
        props = feat['properties']
        key = str(props.get(key_field, '')).strip()
        geom = feat.get('geometry')
        if not key or not geom or not geom.get('coordinates'):
            continue
        if geom['type'] == 'Polygon':
            lat, lon = polygon_centroid(geom['coordinates'])
        elif geom['type'] == 'MultiPolygon':
            lat, lon = polygon_centroid(geom['coordinates'][0])
        else:
            continue
        if lat and lon:
            coords[key] = (lat, lon)
    print(f"    {len(coords)} entries indexed")
    return coords


def filter_and_geocode_bedford(dest1_coords, dest2_coords):
    """Filter Bedford: join parcels+improvements, get coords, pre-filter by distance."""
    print("\n=== BEDFORD COUNTY ===")

    # Load improvements indexed by PIN (joins to parcel RPC)
    print("  Loading improvements...")
    with open('bedford/improvements.json') as f:
        imps = json.load(f)
    imp_by_pin = {}
    for rec in imps:
        pin = str(rec.get('PIN', '')).strip()
        if pin:
            imp_by_pin[pin] = rec

    # Load parcels with coords
    print("  Loading parcels...")
    with open('bedford/parcels_complete.geojson') as f:
        parcels = json.load(f)

    candidates = []
    for feat in parcels['features']:
        props = feat['properties']
        rpc = str(props.get('RPC', '')).strip()
        imp = imp_by_pin.get(rpc)
        if not imp:
            continue

        acreage = safe_float(props.get('LegalAc'))
        if acreage < 5 or acreage > 25:
            continue

        sqft = safe_int(imp.get('FinSize'))
        if sqft < 1800:
            continue

        bedrooms = safe_int(imp.get('NumBdRms'))
        if bedrooms < 3:
            continue

        full_baths = safe_int(imp.get('Num3Baths'))
        half_baths = safe_int(imp.get('Num2Baths'))
        total_baths = full_baths + half_baths * 0.5
        if total_baths < 2:
            continue

        # Get centroid
        geom = feat.get('geometry')
        if not geom or not geom.get('coordinates'):
            continue
        if geom['type'] == 'Polygon':
            lat, lon = polygon_centroid(geom['coordinates'])
        elif geom['type'] == 'MultiPolygon':
            lat, lon = polygon_centroid(geom['coordinates'][0])
        else:
            continue
        if not lat or not lon:
            continue

        # Distance pre-filter
        d1 = haversine_miles(lat, lon, dest1_coords[0], dest1_coords[1])
        d2 = haversine_miles(lat, lon, dest2_coords[0], dest2_coords[1])
        if d1 > MAX_DISTANCE_MILES or d2 > MAX_DISTANCE_MILES:
            continue

        addr = str(props.get('LocAddr', '')).strip()
        city = str(props.get('MailCity', '')).strip()
        state = str(props.get('MailStat', '')).strip() or 'VA'
        zipcode = str(props.get('MailZip', '')).strip()
        full_addr = f"{addr}, {city}, {state} {zipcode}".strip(', ')

        candidates.append({
            'county': 'Bedford',
            'address': full_addr,
            'loc_addr': addr,
            'city': city,
            'state': state,
            'zip': zipcode,
            'lat': lat, 'lon': lon,
            'acreage': acreage,
            'sqft': sqft,
            'bedrooms': bedrooms,
            'total_baths': total_baths,
            'year_built': str(imp.get('YrBuilt', '')).strip(),
            'tax_assessment': '',  # Not available in current data
            'owner': str(props.get('Owner1', '')).strip(),
        })

    print(f"  {len(candidates)} candidates within {MAX_DISTANCE_MILES} miles")
    return candidates


def filter_and_geocode_campbell(dest1_coords, dest2_coords):
    """Filter Campbell: use improvements CSV + parcel coords."""
    print("\n=== CAMPBELL COUNTY ===")

    # Build coord index from parcels (key=ACCOUNT)
    coord_index = build_coord_index('campbell/parcels_complete.geojson', 'ACCOUNT')

    # Read improvements CSV and filter
    print("  Loading improvements CSV...")
    candidates = []
    with open('campbell/improvements.csv', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            acreage = safe_float(row.get('LEGALACREAGE'))
            if acreage < 5 or acreage > 25:
                continue

            sqft = safe_int(row.get('FINSIZE'))
            if sqft < 1800:
                continue

            bedrooms = safe_int(row.get('NUMBDRMS'))
            if bedrooms < 3:
                continue

            # Get coords from parcel geometry
            pin = str(row.get('PIN', '')).strip()
            if pin not in coord_index:
                continue
            lat, lon = coord_index[pin]

            # Distance pre-filter
            d1 = haversine_miles(lat, lon, dest1_coords[0], dest1_coords[1])
            d2 = haversine_miles(lat, lon, dest2_coords[0], dest2_coords[1])
            if d1 > MAX_DISTANCE_MILES or d2 > MAX_DISTANCE_MILES:
                continue

            addr = str(row.get('MAILINGADDRESS', '')).strip()
            city = str(row.get('MAILINGCITY', '')).strip()
            state = str(row.get('MAILINGSTATE', '')).strip() or 'VA'
            zipcode = str(row.get('MAILINGZIP', '')).strip()
            full_addr = f"{addr}, {city}, {state} {zipcode}".strip(', ')

            land_val = safe_float(row.get('LANDMARKETVALUE'))
            imp_val = safe_float(row.get('IMPROVEMENTMARKETVALUE'))

            candidates.append({
                'county': 'Campbell',
                'address': full_addr,
                'loc_addr': addr,
                'city': city,
                'state': state,
                'zip': zipcode,
                'lat': lat, 'lon': lon,
                'acreage': acreage,
                'sqft': sqft,
                'bedrooms': bedrooms,
                'total_baths': 0,  # Not available
                'year_built': str(row.get('YRBUILT', '')).strip(),
                'tax_assessment': land_val + imp_val,
                'owner': str(row.get('NAME1', '')).strip(),
            })

    print(f"  {len(candidates)} candidates within {MAX_DISTANCE_MILES} miles")
    return candidates


if __name__ == '__main__':
    # Geocode destinations
    print("Geocoding destinations...")
    d1_lat, d1_lon = geocode(DEST1)
    time.sleep(1.1)
    d2_lat, d2_lon = geocode(DEST2)

    print(f"  {DEST1}")
    print(f"    -> ({d1_lat}, {d1_lon})")
    print(f"  {DEST2}")
    print(f"    -> ({d2_lat}, {d2_lon})")

    if not d1_lat or not d2_lat:
        print("ERROR: Could not geocode destinations!")
        sys.exit(1)

    dest1 = (d1_lat, d1_lon)
    dest2 = (d2_lat, d2_lon)

    # Filter both counties
    bedford_cands = filter_and_geocode_bedford(dest1, dest2)
    campbell_cands = filter_and_geocode_campbell(dest1, dest2)

    all_candidates = bedford_cands + campbell_cands
    print(f"\n{'='*60}")
    print(f"  Total distance-filtered candidates: {len(all_candidates)}")
    print(f"  Checking drive times via OSRM...")
    print(f"{'='*60}")

    # Check drive times
    final_matches = []
    for i, prop in enumerate(all_candidates):
        if i % 20 == 0:
            print(f"  Progress: {i+1}/{len(all_candidates)}...")

        t1 = get_drive_time(prop['lat'], prop['lon'], d1_lat, d1_lon)
        time.sleep(0.1)
        t2 = get_drive_time(prop['lat'], prop['lon'], d2_lat, d2_lon)
        time.sleep(0.1)

        if t1 is not None and t2 is not None:
            prop['commute_rivermont'] = round(t1, 1)
            prop['commute_fleetwood'] = round(t2, 1)

            if t1 <= MAX_COMMUTE_MIN and t2 <= MAX_COMMUTE_MIN:
                final_matches.append(prop)
                print(f"    MATCH: {prop['loc_addr']}, {prop['city']} - "
                      f"{t1:.0f}/{t2:.0f} min | {prop['sqft']}sqft {prop['bedrooms']}bd "
                      f"{prop['acreage']}ac")

    print(f"\n{'='*60}")
    print(f"  FINAL MATCHES: {len(final_matches)}")
    print(f"{'='*60}")

    # Generate CSV
    with open('matching_properties.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Address', 'Sq Ft', 'Tax Assessment',
            'Commute to 2424 Rivermont Ave (min)',
            'Commute to 122 Fleetwood Dr (min)',
            'County', 'Acreage', 'Bedrooms', 'Baths', 'Year Built', 'Owner'
        ])
        for p in sorted(final_matches, key=lambda x: max(x['commute_rivermont'], x['commute_fleetwood'])):
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

    print(f"CSV saved to matching_properties.csv")
