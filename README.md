# Virginia Property Search — House Search GIS

GIS-backed property search for **Bedford**, **Campbell**, and **Amherst** counties (Lynchburg, VA area). The pipeline downloads county parcel data, filters by lot/house criteria and commute time, enriches with Zillow estimates and owner-occupancy, then scores and ranks candidates.

## Current results

| Metric | Value |
|--------|--------|
| Shortlist size | ~295 properties |
| Counties | Bedford, Campbell, Amherst |
| Commute destinations | 2424 Rivermont Ave; 122 Fleetwood Dr (Lynchburg) |
| Max commute | ≤ 25 minutes to **both** destinations |
| Lot size | 5–25 acres |
| House | ≥ 1800 sq ft, ≥ 3 bedrooms, ≥ 2 baths (where baths available) |

**Primary scored output:** `matching_properties_scored.csv`  
**Per-county rankings:** `scored_by_county/<county>.csv`

---

## Pipeline overview

```
Download parcels / improvements
        │
        ▼
Filter by acreage, sq ft, beds, baths   (filter_properties.py, filter_amherst.py)
        │
        ▼
Commute filter via OSRM                 (commute_filter.py → matching_properties.csv)
        │
        ▼
Zillow Zestimate / rent estimate        (zillow_zestimate.py)
        │
        ▼
Mailing address + owner-occupied flag   (enrich_mailing_address.py)
        │
        ▼
Score & rank (overall + by county)      (score_properties.py)
```

### Typical file chain

| Stage | File |
|-------|------|
| After commute filter | `matching_properties.csv` (often renamed `matching_properties_3800.csv`) |
| After Zestimates | `matching_properties_3800_zestimates.csv` |
| After mailing enrich | `matching_properties_3800_zestimates_mailing.csv` |
| After scoring | `matching_properties_scored.csv` + `scored_by_county/*.csv` |

Checked-in deliverables usually start from the zestimate/mailing CSVs so you can re-score without re-scraping Zillow.

---

## Scoring

| Category | Rule | Points |
|----------|------|--------|
| Sq ft | 1800–2499 / 2500–2999 / 3000+ | 10 / 14 / 17 |
| Commute (each destination) | &lt;15 min / 15–25 / &gt;25 | 15 / 10 / 5 |
| Acreage | per acre | 1 × acres |
| Zestimate | &lt;$425k / $425k–$550k / &gt;$550k | 20 / 10 / 0 |
| Non-owner-occupied | mailing address ≠ situs (`Owner Occupied = N`) | **+50** (optional) |

Theoretical max with non-owner bonus: **142** (17 + 30 + 25 + 20 + 50).

### Known data caveats

- **Campbell:** bathroom counts are not in source data (bath filter skipped). Owner occupancy is **Unknown** (no separate situs vs mailing), so the non-owner bonus never applies there.
- **Bedford:** tax assessment is often blank in the shortlist; Zestimate is the price signal used in scoring.
- **Amherst:** parcels come from a public ArcGIS FeatureServer (see `DATA_SOURCES.md`).

---

## Scoring: usage

```bash
# Default: non-owner bonus ON, overall + per-county rankings
python3 score_properties.py

# Disable the +50 non-owner-occupied bonus
python3 score_properties.py --no-non-owner-bonus

# Custom paths
python3 score_properties.py \
  -i matching_properties_3800_zestimates_mailing.csv \
  -o matching_properties_scored.csv \
  --by-county-dir scored_by_county

# Overall ranking only (skip county split files)
python3 score_properties.py --no-by-county
```

### CLI flags

| Flag | Description |
|------|-------------|
| `-i` / `--input` | Input CSV (default: `matching_properties_3800_zestimates_mailing.csv`) |
| `-o` / `--output` | Overall ranked CSV (default: `matching_properties_scored.csv`) |
| `--no-non-owner-bonus` | Turn off the +50 non-owner-occupied points |
| `--by-county` | Write per-county ranked CSVs (default: **on**) |
| `--no-by-county` | Skip per-county files |
| `--by-county-dir` | Output directory for county files (default: `scored_by_county`) |

Each output includes a **Rank** column (1 = best within that file), component scores, **TOTAL SCORE**, and a scoring-key table on the right-hand columns.

---

## Counties & data

| County | Parcels (approx.) | Source | Local data |
|--------|-------------------|--------|------------|
| Bedford | ~50,688 | [Open Data portal](https://geohub-bedfordvagis.opendata.arcgis.com/) | `bedford/parcels_complete.geojson`, `bedford/improvements.json` |
| Campbell | ~37,826 | [GIS Hub](https://data1-campbellva.hub.arcgis.com/) | `campbell/parcels_complete.geojson`, `campbell/improvements.csv` |
| Amherst | ~26,000+ | ArcGIS FeatureServer (Timmons / county) | `amherst/parcels_complete.geojson`, `amherst/parcels_with_assessment.geojson` |

Large GeoJSON files use **Git LFS**. Details and REST endpoints: [`DATA_SOURCES.md`](DATA_SOURCES.md).

### Refresh downloads

```bash
./download_parcels.sh bedford    # or campbell, or no arg for both
python3 download_improvements.py # Bedford improvements table
python3 download_campbell.py     # Campbell parcels (Python path)
python3 download_amherst.py      # Amherst parcels + assessment fields
```

---

## Full regenerate (when needed)

Dependencies: Python 3, `curl`; for Zestimates only: `pip install curl_cffi`.

```bash
# 1. Filter Bedford + Campbell (acreage / house criteria)
python3 filter_properties.py          # → filtered_properties.json

# 2. Commute filter (OSRM + Nominatim)
python3 commute_filter.py             # → matching_properties.csv

# 3. Append Amherst (same criteria + commute)
python3 filter_amherst.py             # appends to matching_properties.csv

# 4. Zestimates (slow; uses browser impersonation)
#    Point INPUT_CSV at your matching file first if needed
python3 zillow_zestimate.py

# 5. Mailing / owner-occupied
python3 enrich_mailing_address.py

# 6. Score
python3 score_properties.py
python3 score_properties.py --no-non-owner-bonus -o matching_properties_scored_no_nonowner.csv
```

Commute uses the public OSRM demo server and OpenStreetMap Nominatim—be polite with rate limits if re-running at scale.

---

## Project layout

```
House_Search_GIS/
├── README.md
├── DATA_SOURCES.md
├── download_parcels.sh / download_parcels.py
├── download_campbell.py / download_campbell.sh
├── download_amherst.py
├── download_improvements.py
├── filter_properties.py          # Bedford + Campbell criteria
├── commute_filter.py             # Drive-time filter → matching_properties.csv
├── filter_amherst.py             # Amherst criteria + commute, appends CSV
├── zillow_zestimate.py
├── enrich_mailing_address.py
├── score_properties.py           # Rank overall + by county
├── bedford/  campbell/  amherst/ # Parcel / improvement source data
├── matching_properties_3800_zestimates.csv
├── matching_properties_3800_zestimates_mailing.csv
├── matching_properties_scored.csv
└── scored_by_county/             # e.g. bedford.csv, campbell.csv, amherst.csv
```

---

## View parcels in QGIS / Python

```bash
# Reproject to WGS84 if needed (source CRS is often EPSG:2284)
ogr2ogr -t_srs EPSG:4326 out.geojson bedford/parcels_complete.geojson
```

```python
import geopandas as gpd
bedford = gpd.read_file('bedford/parcels_complete.geojson')
```

---

## Contacts (county GIS)

- **Bedford:** gis@bedfordcountyva.gov · (540) 587-5678  
- **Campbell:** gisweb@campbellcountyva.gov  
- **Amherst:** Planning & Zoning · (434) 946-9303  

---

*Documentation updated: July 2026*
