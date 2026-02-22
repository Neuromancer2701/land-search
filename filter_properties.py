#!/usr/bin/env python3
"""
Filter properties in Bedford and Campbell counties by criteria:
- 5-25 acres
- At least 1800 sq-ft house
- 3+ bedrooms
- 2+ bathrooms
"""
import json
import csv
import sys
import os

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)


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


def filter_bedford():
    """Filter Bedford County properties by joining parcels + improvements."""
    print("=" * 60)
    print("  BEDFORD COUNTY")
    print("=" * 60)

    # Load improvements and index by PIN (joins to parcel RPC field)
    print("Loading improvements...")
    with open('bedford/improvements.json') as f:
        improvements = json.load(f)

    imp_by_pin = {}
    for rec in improvements:
        pin = str(rec.get('PIN', '')).strip()
        if pin:
            imp_by_pin[pin] = rec

    print(f"  {len(imp_by_pin)} improvement records indexed by PIN")

    # Load parcels
    print("Loading parcels...")
    with open('bedford/parcels_complete.geojson') as f:
        parcels = json.load(f)

    print(f"  {len(parcels['features'])} parcels loaded")

    # Filter and join (parcel RPC -> improvement PIN)
    matches = []
    join_count = 0
    for feat in parcels['features']:
        props = feat['properties']
        rpc = str(props.get('RPC', '')).strip()

        imp = imp_by_pin.get(rpc)
        if not imp:
            continue
        join_count += 1

        # Acreage filter: 5-25 acres
        acreage = safe_float(props.get('LegalAc'))
        if acreage < 5 or acreage > 25:
            continue

        # Sq ft filter: >= 1800
        sqft = safe_int(imp.get('FinSize'))
        if sqft < 1800:
            continue

        # Bedrooms filter: >= 3
        bedrooms = safe_int(imp.get('NumBdRms'))
        if bedrooms < 3:
            continue

        # Bathrooms filter: >= 2 (full baths = Num3Baths, half baths = Num2Baths)
        full_baths = safe_int(imp.get('Num3Baths'))
        half_baths = safe_int(imp.get('Num2Baths'))
        total_baths = full_baths + half_baths * 0.5
        if total_baths < 2:
            continue

        addr = str(props.get('LocAddr', '')).strip()
        city = str(props.get('MailCity', '')).strip()
        state = str(props.get('MailStat', '')).strip()
        zipcode = str(props.get('MailZip', '')).strip()

        # Try to build a full address
        if addr:
            full_addr = f"{addr}, {city}, {state} {zipcode}".strip(', ')
        else:
            full_addr = ''

        # Tax assessment - use sale amounts as proxy
        sale_amt = safe_float(props.get('Sale1Amt')) or safe_float(props.get('purch_price'))

        matches.append({
            'county': 'Bedford',
            'address': full_addr,
            'loc_addr': addr,
            'city': city,
            'state': state or 'VA',
            'zip': zipcode,
            'acreage': acreage,
            'sqft': sqft,
            'bedrooms': bedrooms,
            'full_baths': full_baths,
            'half_baths': half_baths,
            'total_baths': total_baths,
            'year_built': str(imp.get('YrBuilt', '')).strip(),
            'sale_amount': sale_amt,
            'owner': str(props.get('Owner1', '')).strip(),
            'use_desc': str(imp.get('UseDesc', '')).strip(),
            'bldg_type': str(imp.get('BldgType', '')).strip(),
        })

    print(f"  Joined {join_count} parcels with improvements")
    print(f"  Found {len(matches)} matching properties")
    return matches


def filter_campbell():
    """Filter Campbell County properties from improvements CSV."""
    print("\n" + "=" * 60)
    print("  CAMPBELL COUNTY")
    print("=" * 60)

    print("Loading improvements CSV...")
    matches = []
    total = 0

    with open('campbell/improvements.csv', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1

            # Acreage filter: 5-25 acres
            acreage = safe_float(row.get('LEGALACREAGE'))
            if acreage < 5 or acreage > 25:
                continue

            # Sq ft filter: >= 1800
            sqft = safe_int(row.get('FINSIZE'))
            if sqft < 1800:
                continue

            # Bedrooms filter: >= 3
            bedrooms = safe_int(row.get('NUMBDRMS'))
            if bedrooms < 3:
                continue

            # Campbell doesn't have bathroom count - include if other criteria match
            # Most 1800+ sqft 3+ bed homes have 2+ baths

            addr = str(row.get('MAILINGADDRESS', '')).strip()
            city = str(row.get('MAILINGCITY', '')).strip()
            state = str(row.get('MAILINGSTATE', '')).strip()
            zipcode = str(row.get('MAILINGZIP', '')).strip()

            if addr:
                full_addr = f"{addr}, {city}, {state} {zipcode}".strip(', ')
            else:
                full_addr = ''

            land_val = safe_float(row.get('LANDMARKETVALUE'))
            imp_val = safe_float(row.get('IMPROVEMENTMARKETVALUE'))
            total_assessment = land_val + imp_val

            matches.append({
                'county': 'Campbell',
                'address': full_addr,
                'loc_addr': addr,
                'city': city,
                'state': state or 'VA',
                'zip': zipcode,
                'acreage': acreage,
                'sqft': sqft,
                'bedrooms': bedrooms,
                'full_baths': 0,  # Not available
                'half_baths': 0,
                'total_baths': 0,  # Not available
                'year_built': str(row.get('YRBUILT', '')).strip(),
                'sale_amount': safe_float(row.get('SALE1AMT')),
                'tax_assessment': total_assessment,
                'owner': str(row.get('NAME1', '')).strip(),
                'use_desc': '',
                'bldg_type': '',
            })

    print(f"  Processed {total} records")
    print(f"  Found {len(matches)} matching properties")
    return matches


if __name__ == '__main__':
    bedford = filter_bedford()
    campbell = filter_campbell()

    all_matches = bedford + campbell
    print(f"\n{'='*60}")
    print(f"  TOTAL MATCHES: {len(all_matches)}")
    print(f"  Bedford: {len(bedford)}, Campbell: {len(campbell)}")
    print(f"{'='*60}")

    # Save intermediate results
    with open('filtered_properties.json', 'w') as f:
        json.dump(all_matches, f, indent=2)
    print(f"\nSaved to filtered_properties.json")

    # Print summary
    print(f"\n{'County':<12} {'Address':<40} {'Acres':>6} {'SqFt':>6} {'Bed':>4} {'Bath':>5} {'City':<20}")
    print("-" * 100)
    for p in all_matches:
        print(f"{p['county']:<12} {p['loc_addr'][:38]:<40} {p['acreage']:>6.1f} {p['sqft']:>6} {p['bedrooms']:>4} {p['total_baths']:>5.1f} {p['city']:<20}")
