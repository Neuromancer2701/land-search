#!/usr/bin/env python3
"""
Score properties from matching_properties_3800_zestimates.csv.

Scoring system:
  Sq Ft:    1800-2499 = 10 pts | 2500-2999 = 14 pts | 3000+ = 17 pts
  Commute:  <15 min = 15 pts | 15-25 min = 10 pts | >25 min = 5 pts  (applied to BOTH destinations)
  Acreage:  1 pt per acre (raw value)
  Zestimate: <$425k = 20 pts | $425k-$550k = 10 pts | >$550k = 0 pts

Outputs a scored CSV with a scoring key table to the right.
"""
import csv
import os
import sys

os.chdir('/home/count_zero/Repos/House_Search_GIS')

INPUT_CSV  = 'matching_properties_3800_zestimates.csv'
OUTPUT_CSV = 'matching_properties_scored.csv'

# ── Scoring thresholds (edit these to retune the model) ───────────────────────
# Higher-value-is-better tiers: ordered high→low; return pts when value >= threshold
SQFT_TIERS = [
    (3000, 17),   # >= 3000 sq ft
    (2500, 14),   # >= 2500 sq ft
    (1800, 10),   # >= 1800 sq ft
]
# Lower-value-is-better tiers: ordered low→high; return pts when value < threshold
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
ACRE_PTS_PER_ACRE = 1   # multiply by raw acreage
# ─────────────────────────────────────────────────────────────────────────────


def safe_float(val, default=0.0):
    try:
        return float(str(val).strip().replace(',', '').replace('$', ''))
    except (ValueError, TypeError):
        return default


def hi_tier_score(value, tiers):
    """Higher value = higher pts. Tiers ordered high→low; return pts when value >= threshold."""
    for threshold, pts in tiers:
        if value >= threshold:
            return pts
    return 0


def lo_tier_score(value, tiers):
    """Lower value = higher pts. Tiers ordered low→high; return pts when value < threshold."""
    for threshold, pts in tiers:
        if value < threshold:
            return pts
    return tiers[-1][1]


def score_row(row):
    sqft     = safe_float(row['Sq Ft'])
    commute1 = safe_float(row['Commute to 2424 Rivermont Ave (min)'])
    commute2 = safe_float(row['Commute to 122 Fleetwood Dr (min)'])
    acreage  = safe_float(row['Acreage'])
    zest     = safe_float(row['Zestimate'])

    s_sqft  = hi_tier_score(sqft, SQFT_TIERS)
    s_c1    = lo_tier_score(commute1, COMMUTE_TIERS) if commute1 > 0 else 0
    s_c2    = lo_tier_score(commute2, COMMUTE_TIERS) if commute2 > 0 else 0
    s_acres = round(acreage * ACRE_PTS_PER_ACRE, 1)
    s_zest  = lo_tier_score(zest, ZESTIMATE_TIERS) if zest > 0 else 0
    s_total = s_sqft + s_c1 + s_c2 + s_acres + s_zest

    return {
        'SqFt Score':              s_sqft,
        'Commute Rivermont Score': s_c1,
        'Commute Fleetwood Score': s_c2,
        'Acreage Score':           s_acres,
        'Zestimate Score':         s_zest,
        'TOTAL SCORE':             s_total,
    }


# ── Scoring key — displayed to the right of the data in the output CSV ────────
# Each entry is [Category, Threshold, Points, Note]
# Row 0 aligns with the header row; subsequent rows align with data rows 1, 2, …
KEY_ROWS = [
    # header row companion
    ['SCORING KEY', 'Category',          'Threshold',      'Points', 'Notes'],
    # data rows
    ['',            '── SQ FOOTAGE ──',  '',               '',       ''],
    ['',            'Sq Ft',             '1800 - 2499',    '10',     ''],
    ['',            'Sq Ft',             '2500 - 2999',    '14',     ''],
    ['',            'Sq Ft',             '3000+',          '17',     ''],
    ['',            '',                  '',               '',       ''],
    ['',            '── COMMUTE ──',     '',               '',       'Applied to BOTH destinations'],
    ['',            'Commute',           '< 15 min',       '15',     ''],
    ['',            'Commute',           '15 - 25 min',    '10',     ''],
    ['',            'Commute',           '> 25 min',       '5',      ''],
    ['',            '',                  '',               '',       ''],
    ['',            '── ACREAGE ──',     '',               '',       ''],
    ['',            'Acreage',           'per acre',       '1',      'Raw acreage value'],
    ['',            '',                  '',               '',       ''],
    ['',            '── ZESTIMATE ──',   '',               '',       ''],
    ['',            'Zestimate',         '< $425,000',     '20',     ''],
    ['',            'Zestimate',         '$425k - $550k',  '10',     ''],
    ['',            'Zestimate',         '> $550,000',     '0',      ''],
    ['',            '',                  '',               '',       ''],
    ['',            '── MAX SCORES ──',  '',               '',       ''],
    ['',            'Sq Ft max',         '3000+',          '17',     ''],
    ['',            'Commute max (×2)',  '< 15 min each',  '30',     ''],
    ['',            'Acreage max',       '25 acres',       '25',     ''],
    ['',            'Zestimate max',     '< $425k',        '20',     ''],
    ['',            'Theoretical max',   '',               '92',     '(17+30+25+20)'],
]

EMPTY_KEY = ['', '', '', '', '']
# ─────────────────────────────────────────────────────────────────────────────


def main():
    with open(INPUT_CSV, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        src_fieldnames = reader.fieldnames
        rows = list(reader)

    score_fields = [
        'SqFt Score',
        'Commute Rivermont Score',
        'Commute Fleetwood Score',
        'Acreage Score',
        'Zestimate Score',
        'TOTAL SCORE',
    ]
    key_fields = ['', 'KEY Category', 'KEY Threshold', 'KEY Points', 'KEY Notes']

    out_fieldnames = src_fieldnames + score_fields + key_fields

    # Sort data rows by total score descending
    scored_rows = []
    for row in rows:
        scores = score_row(row)
        scored_rows.append((row, scores))

    scored_rows.sort(key=lambda x: x[1]['TOTAL SCORE'], reverse=True)

    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()

        # Write key header alongside the column header (already done above by DictWriter)
        # We need to inject the KEY_ROWS[0] into the header — DictWriter can't do that,
        # so re-open and patch if needed.  Simpler: embed key from data row 0 onward.

        for i, (row, scores) in enumerate(scored_rows):
            out_row = dict(row)
            out_row.update(scores)

            # key_fields row: KEY_ROWS[0] aligns with header (handled separately below)
            # KEY_ROWS[1] onward aligns with data rows 0, 1, 2, ...
            key_idx = i + 1          # data row i → KEY_ROWS[i+1]
            key = KEY_ROWS[key_idx] if key_idx < len(KEY_ROWS) else EMPTY_KEY
            out_row['']            = key[0]
            out_row['KEY Category']  = key[1]
            out_row['KEY Threshold'] = key[2]
            out_row['KEY Points']    = key[3]
            out_row['KEY Notes']     = key[4]

            writer.writerow(out_row)

    # Now patch the header row to include the key header (KEY_ROWS[0])
    # Read back, inject, rewrite
    with open(OUTPUT_CSV, 'r', newline='') as f:
        content = f.read()

    # The DictWriter wrote blank strings for '' and 'KEY *' field names in the header.
    # Replace the tail of the header line with the actual key titles.
    lines = content.splitlines(keepends=True)
    hdr_parts = lines[0].rstrip('\r\n').split(',')
    # Last 5 fields are the key columns — replace their header labels
    key_header_labels = KEY_ROWS[0]   # ['SCORING KEY','Category','Threshold','Points','Notes']
    hdr_parts[-5] = key_header_labels[0]
    hdr_parts[-4] = key_header_labels[1]
    hdr_parts[-3] = key_header_labels[2]
    hdr_parts[-2] = key_header_labels[3]
    hdr_parts[-1] = key_header_labels[4]
    lines[0] = ','.join(hdr_parts) + '\n'

    with open(OUTPUT_CSV, 'w') as f:
        f.writelines(lines)

    print(f"Scored {len(scored_rows)} properties → {OUTPUT_CSV}")
    print(f"\nTop 10 by score:")
    print(f"{'Score':>6}  {'Address':<45} {'County':<10} {'SqFt':>6} {'Acres':>6} {'Zestimate':>10}")
    print("-" * 90)
    for row, scores in scored_rows[:10]:
        zest = safe_float(row['Zestimate'])
        zest_str = f"${zest:,.0f}" if zest else "N/A"
        print(f"  {scores['TOTAL SCORE']:>4.1f}  {row['Address'][:43]:<45} "
              f"{row['County']:<10} {row['Sq Ft']:>6} {float(row['Acreage']):>6.1f} {zest_str:>10}")


if __name__ == '__main__':
    main()
