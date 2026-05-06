#!/usr/bin/env python3
"""
Enrich matching_properties_3800_zestimates.csv with mailing address +
owner-occupancy flag.

Outputs: matching_properties_3800_zestimates_mailing.csv (adds columns
'Mailing Address' and 'Owner Occupied').

Owner Occupied values:
  Y       — property address matches mailing address
  N       — property address differs from mailing address
  Unknown — Campbell County (no separate situs address in source data)
            or address could not be matched
"""
import csv
import json
import os
import re

os.chdir('/home/count_zero/Repos/House_Search_GIS')

INPUT_CSV  = 'matching_properties_3800_zestimates.csv'
OUTPUT_CSV = 'matching_properties_3800_zestimates_mailing.csv'

STREET_ABBR = {
    'STREET': 'ST',  'ROAD': 'RD',     'AVENUE': 'AVE',  'BOULEVARD': 'BLVD',
    'DRIVE': 'DR',   'LANE': 'LN',     'COURT': 'CT',    'CIRCLE': 'CIR',
    'HIGHWAY': 'HWY','PARKWAY': 'PKWY','PLACE': 'PL',    'TERRACE': 'TER',
    'TRAIL': 'TRL',  'SQUARE': 'SQ',
    'NORTH': 'N', 'SOUTH': 'S', 'EAST': 'E', 'WEST': 'W',
}


def norm_street(s):
    """Normalize a street/address: uppercase, strip punctuation, collapse
    whitespace, normalize common abbreviations."""
    if not s:
        return ''
    s = s.upper()
    s = re.sub(r'[.,#]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    parts = [STREET_ABBR.get(p, p) for p in s.split(' ')]
    return ' '.join(parts)


def first_line_only(addr):
    """Drop city/state/zip suffix; keep just the leading street portion."""
    if not addr:
        return ''
    return addr.split(',', 1)[0].strip()


def addresses_match(prop_addr, mail_addr):
    """True if normalized street portions match (or one contains the other)."""
    a = norm_street(first_line_only(prop_addr))
    b = norm_street(first_line_only(mail_addr))
    if not a or not b:
        return None  # unknown
    return a == b or a in b or b in a


def build_bedford_lookup():
    """Return dict: normalized LocAddr -> mailing address string."""
    print('Loading Bedford parcels…')
    with open('bedford/parcels_complete.geojson') as f:
        d = json.load(f)
    out = {}
    for feat in d['features']:
        p = feat['properties']
        loc = (p.get('LocAddr') or '').strip()
        mail = (p.get('MailAddr') or '').strip()
        if not loc or not mail:
            continue
        key = norm_street(loc)
        if not key:
            continue
        city = (p.get('MailCity') or '').strip()
        state = (p.get('MailStat') or '').strip()
        zipc = (p.get('MailZip') or '').strip()
        full_mail = ', '.join(x for x in [mail, city, f"{state} {zipc}".strip()] if x)
        out[key] = full_mail
    print(f'  indexed {len(out)} Bedford parcels by normalized LocAddr')
    return out


def build_amherst_lookup():
    """Return dict: normalized ParcelAddress1 -> mailing address string."""
    print('Loading Amherst parcels…')
    with open('amherst/parcels_with_assessment.geojson') as f:
        d = json.load(f)
    out = {}
    for feat in d['features']:
        p = feat['properties']
        parc = (p.get('ParcelAddress1') or '').strip()
        own1 = (p.get('OwnerAddress1') or '').strip()
        own2 = (p.get('OwnerAddress2') or '').strip()
        if not parc or not own1:
            continue
        key = norm_street(parc)
        if not key:
            continue
        full_mail = ', '.join(x for x in [own1, own2] if x)
        out[key] = full_mail
    print(f'  indexed {len(out)} Amherst parcels by normalized ParcelAddress1')
    return out


def main():
    bedford = build_bedford_lookup()
    amherst = build_amherst_lookup()

    with open(INPUT_CSV, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames + ['Mailing Address', 'Owner Occupied']
        rows = list(reader)

    counts = {'Y': 0, 'N': 0, 'Unknown': 0}
    out_rows = []
    for row in rows:
        county = row.get('County', '').strip()
        prop_addr = row.get('Address', '').strip()
        key = norm_street(first_line_only(prop_addr))

        mail_addr = ''
        if county == 'Bedford':
            mail_addr = bedford.get(key, '')
        elif county == 'Amherst':
            mail_addr = amherst.get(key, '')
        # Campbell: no situs address available → leave blank, mark Unknown

        if county == 'Campbell':
            occupied = 'Unknown'
        elif not mail_addr:
            occupied = 'Unknown'
        else:
            match = addresses_match(prop_addr, mail_addr)
            occupied = 'Y' if match else 'N'

        row['Mailing Address'] = mail_addr
        row['Owner Occupied'] = occupied
        counts[occupied] += 1
        out_rows.append(row)

    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f'\nWrote {len(out_rows)} rows → {OUTPUT_CSV}')
    print(f"  Owner-occupied (Y):     {counts['Y']}")
    print(f"  Non-owner-occupied (N): {counts['N']}")
    print(f"  Unknown:                {counts['Unknown']}")


if __name__ == '__main__':
    main()
