#!/usr/bin/env python3
"""
Fetch Zillow Zestimates for all addresses in matching_properties_3800.csv.
Uses curl_cffi with Chrome impersonation to bypass PerimeterX bot detection.

Approach:
1. Use Zillow's autocomplete API (zillowstatic.com) to get zpid for each address
2. Fetch the property detail page using curl_cffi with browser impersonation
3. Parse __NEXT_DATA__ JSON from the HTML to extract Zestimate
4. Add Zestimate column to the CSV
"""

import csv
import json
import os
import re
import sys
import time
import random
from urllib.request import Request, urlopen

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
os.chdir('/home/count_zero/Repos/House_Search_GIS')

from curl_cffi import requests as cffi_requests

INPUT_CSV = 'matching_properties_3800.csv'
OUTPUT_CSV = 'matching_properties_3800.csv'
PROGRESS_FILE = 'zestimate_progress.json'


def get_zpid_from_autocomplete(address):
    """Use Zillow's autocomplete API to get zpid for an address."""
    clean = address.replace(",", "").replace("  ", " ").strip()
    q = clean.replace(" ", "+")
    url = f"https://www.zillowstatic.com/autocomplete/v3/suggestions?q={q}"
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("results", [])
        if results:
            meta = results[0].get("metaData", {})
            return meta.get("zpid")
    except Exception as e:
        pass
    return None


def get_zestimate_from_page(session, zpid):
    """Fetch property page and extract Zestimate from __NEXT_DATA__ JSON."""
    url = f"https://www.zillow.com/homedetails/{zpid}_zpid/"
    try:
        r = session.get(url, timeout=25)
        if r.status_code != 200:
            return None, None, f"HTTP {r.status_code}"

        nd_match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            r.text, re.DOTALL
        )
        if not nd_match:
            if "captcha" in r.text.lower()[:3000]:
                return None, None, "CAPTCHA"
            return None, None, "No __NEXT_DATA__"

        nd = json.loads(nd_match.group(1))
        comp = nd["props"]["pageProps"]["componentProps"]
        cache_str = comp.get("gdpClientCache", "")
        cache = json.loads(cache_str)

        for val in cache.values():
            if isinstance(val, dict) and "property" in val:
                prop = val["property"]
                zestimate = prop.get("zestimate")
                rent_zest = prop.get("rentZestimate")
                return zestimate, rent_zest, None

        return None, None, "No property in cache"

    except Exception as e:
        return None, None, str(e)


def load_progress():
    """Load previously fetched zestimates to allow resuming."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


if __name__ == '__main__':
    # Read CSV
    with open(INPUT_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Loaded {len(rows)} properties from {INPUT_CSV}")

    # Load any previous progress
    progress = load_progress()
    print(f"Resuming with {len(progress)} previously fetched zestimates")

    # Create session with browser impersonation
    session = cffi_requests.Session(impersonate="chrome")

    found = 0
    not_found = 0
    errors = 0

    for i, row in enumerate(rows):
        address = row['Address']

        # Check if already fetched
        if address in progress:
            found += 1 if progress[address].get('zestimate') else 0
            continue

        print(f"[{i+1}/{len(rows)}] {address}")

        # Step 1: Get zpid from autocomplete
        zpid = get_zpid_from_autocomplete(address)
        if not zpid:
            print(f"  -> No zpid found, skipping")
            progress[address] = {'zestimate': None, 'rent_zestimate': None, 'error': 'No zpid'}
            not_found += 1
            time.sleep(1)
            continue

        # Step 2: Fetch property page and extract zestimate
        zestimate, rent_zest, err = get_zestimate_from_page(session, zpid)

        if err == "CAPTCHA":
            print(f"  -> CAPTCHA detected! Pausing 60s and creating new session...")
            time.sleep(60)
            session = cffi_requests.Session(impersonate="chrome")
            # Retry once
            zestimate, rent_zest, err = get_zestimate_from_page(session, zpid)

        if err:
            print(f"  -> Error: {err}")
            progress[address] = {'zestimate': None, 'rent_zestimate': None, 'error': err}
            errors += 1
        elif zestimate:
            print(f"  -> Zestimate: ${zestimate:,}  Rent: ${rent_zest:,}" if rent_zest else f"  -> Zestimate: ${zestimate:,}")
            progress[address] = {'zestimate': zestimate, 'rent_zestimate': rent_zest, 'error': None}
            found += 1
        else:
            print(f"  -> No Zestimate available")
            progress[address] = {'zestimate': None, 'rent_zestimate': rent_zest, 'error': 'No zestimate'}
            not_found += 1

        # Save progress every 10 properties
        if (i + 1) % 10 == 0:
            save_progress(progress)
            print(f"  [Progress saved: {found} found, {not_found} not found, {errors} errors]")

        # Random delay 3-5 seconds between requests
        delay = 3 + random.random() * 2
        time.sleep(delay)

    # Final save
    save_progress(progress)

    print(f"\n{'='*60}")
    print(f"  RESULTS: {found} found, {not_found} not found, {errors} errors")
    print(f"{'='*60}")

    # Write updated CSV with Zestimate column
    out_fieldnames = list(fieldnames) + ['Zestimate', 'Rent Zestimate']

    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        for row in rows:
            address = row['Address']
            z = progress.get(address, {})
            row['Zestimate'] = z.get('zestimate', '')
            row['Rent Zestimate'] = z.get('rent_zestimate', '')
            writer.writerow(row)

    print(f"\nCSV updated: {OUTPUT_CSV} ({len(rows)} rows with Zestimate column)")
