# Offshore Assets — Coverage Summary

Analytical roll-ups derived **from the offshore_assets curated tables themselves**
(`fields.csv` 2,149 rows, `production_facilities.csv` 836 rows). This is a new
derived artifact, not a copy: every number here is a count computed over the two
catalogs. The companion machine-readable file is `coverage_summary.csv`.

Corpus epic llm-wiki#767; worldenergydata issue #543.

## `coverage_summary.csv`

Long-form roll-up table, 135 rows.

| Column | Notes |
|---|---|
| CATEGORY | roll-up axis (see below) |
| DIMENSION | the bucket value within that axis |
| FIELDS_COUNT | count of rows in `fields.csv` for the bucket (blank where N/A) |
| FACILITIES_COUNT | count of rows in `production_facilities.csv` for the bucket (blank where N/A) |

CATEGORY values: `by_country`, `field_by_reserve_type`, `facility_by_duty`,
`field_by_status`, `facility_by_status`, `facility_by_host_type`,
`by_water_depth_band`, `by_region`, `total`.

## Highlights

### By country (fields / production facilities)
Top by combined count: United States (333 / 88), United Kingdom (308 / 124),
Norway (302 / 82), Australia (192 / 50), Brazil (98 / 58), Angola (75 / —),
Malaysia (65 / 48), Indonesia (62 / 30). Full list of 205 countries in the CSV.

### By reserve type (fields, 2,149)
Oil 624, Gas 583, n/a 540, Oil/Gas 402.

### By duty (production facilities, 836)
Oil 303, Oil/Gas 303, Gas 223, n/a 7.

### By field status (2,149)
Producing 645, Discovery (Drilled) 399, Bright Spot 319, Under Development 217,
Non-Commercial 179, Discovery (Appraised) 126, Producing - Under Dev. 103,
Appraisal Drilling 49, others smaller.

### By facility host type (836)
Fixed Platform 465, FPSO 152, Subsea Tieback 54, FSO/FSU 42, FPU/FPS 32,
Semisub 20, TLP 20, SPAR 19, FLNG 8, MOPU 8, Artificial Island 6, Mini-TLP 5,
others smaller.

### By water-depth band
| Band | Fields | Facilities |
|---|---|---|
| 0-100 m (shallow) | 526 | 351 |
| 100-500 m | 590 | 234 |
| 500-1000 m | 158 | 52 |
| 1000-1500 m (deepwater) | 217 | 56 |
| >=1500 m (ultra-deepwater) | 245 | 45 |
| Unknown (water depth absent in source) | 413 | 98 |

### US Gulf of Mexico vs rest of world
| Region | Fields | Facilities |
|---|---|---|
| US Gulf of Mexico (US_GOM_FLAG = Y) | 333 | 88 |
| Rest of world | 1,816 | 748 |
| **Total** | **2,149** | **836** |

## Notes

- Counts are exact over the curated tables on the date generated; re-run the
  roll-up after any refresh of `fields.csv` / `production_facilities.csv`.
- Water-depth bands are computed from `WATER_DEPTH_M`; rows with a blank or
  non-positive depth fall in the **Unknown** band.
- The US-GoM split uses the existing `US_GOM_FLAG` column; it is a name-based
  candidate flag for BSEE cross-reference, not an authoritative join.
- Facts-only: no source URLs, no third-party prose, no client tokens.
