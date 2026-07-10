#!/usr/bin/env python3
"""
Score properties from the enriched mailing/zestimate CSV.

Scoring system:
  Sq Ft:    1800-2499 = 10 pts | 2500-2999 = 14 pts | 3000+ = 17 pts
  Commute:  <15 min = 15 pts | 15-25 min = 10 pts | >25 min = 5 pts  (both destinations)
  Acreage:  1 pt per acre (raw value)
  Zestimate: <$425k = 20 pts | $425k-$550k = 10 pts | >$550k = 0 pts
  Non-owner-occupied: +50 pts when mailing address ≠ property address
                      (disable with --no-non-owner-bonus)

Outputs:
  - Overall ranked CSV (default: matching_properties_scored.csv)
  - Per-county ranked CSVs (default: scored_by_county/<county>.csv)
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

INPUT_CSV = 'matching_properties_3800_zestimates_mailing.csv'
OUTPUT_CSV = 'matching_properties_scored.csv'
BY_COUNTY_DIR = 'scored_by_county'

# ── Scoring thresholds (edit these to retune the model) ───────────────────────
SQFT_TIERS = [
    (3000, 17),   # >= 3000 sq ft
    (2500, 14),   # >= 2500 sq ft
    (1800, 10),   # >= 1800 sq ft
]
COMMUTE_TIERS = [
    (15,  15),    # < 15 min  → 15 pts
    (25,  10),    # < 25 min  → 10 pts
    (999,  5),    # anything else → 5 pts
]
ZESTIMATE_TIERS = [
    (425_000, 20),   # < $425k
    (550_000, 10),   # < $550k
    (999_999_999, 0),
]
ACRE_PTS_PER_ACRE = 1
NON_OWNER_OCCUPIED_PTS = 50
# ─────────────────────────────────────────────────────────────────────────────

SCORE_FIELDS = [
    'Rank',
    'SqFt Score',
    'Commute Rivermont Score',
    'Commute Fleetwood Score',
    'Acreage Score',
    'Zestimate Score',
    'Non-Owner-Occupied Score',
    'TOTAL SCORE',
]
KEY_FIELDS = ['', 'KEY Category', 'KEY Threshold', 'KEY Points', 'KEY Notes']
EMPTY_KEY = ['', '', '', '', '']


def safe_float(val, default=0.0):
    try:
        return float(str(val).strip().replace(',', '').replace('$', ''))
    except (ValueError, TypeError):
        return default


def hi_tier_score(value, tiers):
    """Higher value = higher pts. Tiers ordered high→low."""
    for threshold, pts in tiers:
        if value >= threshold:
            return pts
    return 0


def lo_tier_score(value, tiers):
    """Lower value = higher pts. Tiers ordered low→high."""
    for threshold, pts in tiers:
        if value < threshold:
            return pts
    return tiers[-1][1]


def score_row(row, non_owner_bonus: bool):
    sqft = safe_float(row['Sq Ft'])
    commute1 = safe_float(row['Commute to 2424 Rivermont Ave (min)'])
    commute2 = safe_float(row['Commute to 122 Fleetwood Dr (min)'])
    acreage = safe_float(row['Acreage'])
    zest = safe_float(row['Zestimate'])
    occupied = (row.get('Owner Occupied') or '').strip().upper()

    s_sqft = hi_tier_score(sqft, SQFT_TIERS)
    s_c1 = lo_tier_score(commute1, COMMUTE_TIERS) if commute1 > 0 else 0
    s_c2 = lo_tier_score(commute2, COMMUTE_TIERS) if commute2 > 0 else 0
    s_acres = round(acreage * ACRE_PTS_PER_ACRE, 1)
    s_zest = lo_tier_score(zest, ZESTIMATE_TIERS) if zest > 0 else 0
    s_occ = (NON_OWNER_OCCUPIED_PTS if occupied == 'N' else 0) if non_owner_bonus else 0
    s_total = s_sqft + s_c1 + s_c2 + s_acres + s_zest + s_occ

    return {
        'SqFt Score': s_sqft,
        'Commute Rivermont Score': s_c1,
        'Commute Fleetwood Score': s_c2,
        'Acreage Score': s_acres,
        'Zestimate Score': s_zest,
        'Non-Owner-Occupied Score': s_occ,
        'TOTAL SCORE': s_total,
    }


def build_key_rows(non_owner_bonus: bool):
    """Scoring key table embedded to the right of data rows."""
    non_owner_pts = str(NON_OWNER_OCCUPIED_PTS) if non_owner_bonus else '0'
    non_owner_note = (
        'Owner Occupied = N'
        if non_owner_bonus
        else 'DISABLED (--no-non-owner-bonus)'
    )
    theoretical = 17 + 30 + 25 + 20 + (NON_OWNER_OCCUPIED_PTS if non_owner_bonus else 0)
    theoretical_parts = (
        f'(17+30+25+20+{NON_OWNER_OCCUPIED_PTS})'
        if non_owner_bonus
        else '(17+30+25+20)'
    )

    return [
        ['SCORING KEY', 'Category', 'Threshold', 'Points', 'Notes'],
        ['', '── SQ FOOTAGE ──', '', '', ''],
        ['', 'Sq Ft', '1800 - 2499', '10', ''],
        ['', 'Sq Ft', '2500 - 2999', '14', ''],
        ['', 'Sq Ft', '3000+', '17', ''],
        ['', '', '', '', ''],
        ['', '── COMMUTE ──', '', '', 'Applied to BOTH destinations'],
        ['', 'Commute', '< 15 min', '15', ''],
        ['', 'Commute', '15 - 25 min', '10', ''],
        ['', 'Commute', '> 25 min', '5', ''],
        ['', '', '', '', ''],
        ['', '── ACREAGE ──', '', '', ''],
        ['', 'Acreage', 'per acre', '1', 'Raw acreage value'],
        ['', '', '', '', ''],
        ['', '── ZESTIMATE ──', '', '', ''],
        ['', 'Zestimate', '< $425,000', '20', ''],
        ['', 'Zestimate', '$425k - $550k', '10', ''],
        ['', 'Zestimate', '> $550,000', '0', ''],
        ['', '', '', '', ''],
        ['', '── OCCUPANCY ──', '', '', 'Bedford & Amherst only; Campbell = Unknown'],
        ['', 'Non-owner-occupied', 'mailing ≠ situs', non_owner_pts, non_owner_note],
        ['', 'Owner-occupied', 'mailing = situs', '0', 'Owner Occupied = Y'],
        ['', 'Unknown occupancy', '', '0', 'Campbell or unmatched'],
        ['', '', '', '', ''],
        ['', '── MAX SCORES ──', '', '', ''],
        ['', 'Sq Ft max', '3000+', '17', ''],
        ['', 'Commute max (×2)', '< 15 min each', '30', ''],
        ['', 'Acreage max', '25 acres', '25', ''],
        ['', 'Zestimate max', '< $425k', '20', ''],
        ['', 'Non-owner max', 'mailing ≠ situs', non_owner_pts, non_owner_note],
        ['', 'Theoretical max', '', str(theoretical), theoretical_parts],
    ]


def slugify_county(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', (name or 'unknown').strip().lower())
    return slug.strip('_') or 'unknown'


def write_scored_csv(path: Path, src_fieldnames, scored_rows, key_rows):
    """Write ranked rows with scoring key columns; patch key headers."""
    out_fieldnames = list(src_fieldnames) + SCORE_FIELDS + KEY_FIELDS
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames, extrasaction='ignore')
        writer.writeheader()
        for i, (row, scores) in enumerate(scored_rows):
            out_row = dict(row)
            out_row.update(scores)
            out_row['Rank'] = i + 1
            key = key_rows[i + 1] if (i + 1) < len(key_rows) else EMPTY_KEY
            out_row[''] = key[0]
            out_row['KEY Category'] = key[1]
            out_row['KEY Threshold'] = key[2]
            out_row['KEY Points'] = key[3]
            out_row['KEY Notes'] = key[4]
            writer.writerow(out_row)

    # Patch last 5 header labels to human-readable key titles
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    if not lines:
        return
    hdr_parts = lines[0].rstrip('\r\n').split(',')
    key_header = key_rows[0]
    hdr_parts[-5:] = key_header
    lines[0] = ','.join(hdr_parts) + '\n'
    path.write_text(''.join(lines), encoding='utf-8')


def print_top(scored_rows, label: str, n: int = 10):
    print(f"\n{label} — top {min(n, len(scored_rows))}:")
    print(f"{'Rank':>4}  {'Score':>6}  {'Address':<45} {'County':<10} {'SqFt':>6} {'Acres':>6} {'Zestimate':>10}")
    print("-" * 100)
    for i, (row, scores) in enumerate(scored_rows[:n], start=1):
        zest = safe_float(row.get('Zestimate'))
        zest_str = f"${zest:,.0f}" if zest else "N/A"
        acres = safe_float(row.get('Acreage'))
        print(
            f"  {i:>3}  {scores['TOTAL SCORE']:>5.1f}  {row.get('Address', '')[:43]:<45} "
            f"{row.get('County', ''):<10} {row.get('Sq Ft', ''):>6} {acres:>6.1f} {zest_str:>10}"
        )


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description='Score filtered Virginia properties and rank overall + by county.'
    )
    p.add_argument(
        '-i', '--input',
        default=INPUT_CSV,
        help=f'Input CSV (default: {INPUT_CSV})',
    )
    p.add_argument(
        '-o', '--output',
        default=OUTPUT_CSV,
        help=f'Overall ranked output CSV (default: {OUTPUT_CSV})',
    )
    p.add_argument(
        '--no-non-owner-bonus',
        action='store_true',
        help='Disable the +50 non-owner-occupied bonus (Owner Occupied = N).',
    )
    p.add_argument(
        '--by-county',
        action='store_true',
        default=True,
        help='Write per-county ranked CSVs (default: on).',
    )
    p.add_argument(
        '--no-by-county',
        action='store_false',
        dest='by_county',
        help='Skip per-county ranked CSV outputs.',
    )
    p.add_argument(
        '--by-county-dir',
        default=BY_COUNTY_DIR,
        help=f'Directory for per-county CSVs (default: {BY_COUNTY_DIR})',
    )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    non_owner_bonus = not args.no_non_owner_bonus
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    by_county_dir = Path(args.by_county_dir)
    if not by_county_dir.is_absolute():
        by_county_dir = ROOT / by_county_dir

    if not input_path.exists():
        print(f'ERROR: input not found: {input_path}', file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        src_fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    key_rows = build_key_rows(non_owner_bonus)
    scored_rows = [(row, score_row(row, non_owner_bonus)) for row in rows]
    scored_rows.sort(key=lambda x: x[1]['TOTAL SCORE'], reverse=True)

    write_scored_csv(output_path, src_fieldnames, scored_rows, key_rows)

    bonus_label = 'ON' if non_owner_bonus else 'OFF'
    print(f"Scored {len(scored_rows)} properties → {output_path}")
    print(f"Non-owner-occupied bonus: {bonus_label}"
          f"{f' (+{NON_OWNER_OCCUPIED_PTS} pts)' if non_owner_bonus else ''}")
    print_top(scored_rows, 'Overall ranking')

    if args.by_county:
        by_county: dict[str, list] = defaultdict(list)
        for item in scored_rows:
            county = (item[0].get('County') or 'Unknown').strip() or 'Unknown'
            by_county[county].append(item)

        print(f"\nPer-county rankings → {by_county_dir}/")
        for county in sorted(by_county.keys()):
            county_rows = by_county[county]
            # Already sorted globally; re-sort for safety within county
            county_rows = sorted(
                county_rows, key=lambda x: x[1]['TOTAL SCORE'], reverse=True
            )
            out = by_county_dir / f'{slugify_county(county)}.csv'
            write_scored_csv(out, src_fieldnames, county_rows, key_rows)
            print(f"  {county}: {len(county_rows)} properties → {out.name}")
            print_top(county_rows, f'{county} ranking', n=5)


if __name__ == '__main__':
    main()
