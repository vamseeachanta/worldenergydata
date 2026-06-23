# Facility Specs — Floating-Facility & Mooring Reference Tables

Public-safe reference tables converted from legacy "Posters Data" engineering
reference workbooks (read with openpyxl). Covers per-facility-type particulars
(FPSO, Spar, Semisubmersible, TLP), riser configuration references, and a
mooring-system × facility-type feasibility matrix.

Corpus epic llm-wiki#767; worldenergydata issue #543 (Part B).

## Facts-only policy

Discrete factual attributes only. No URLs, no source-site names, no
client/project-confidential annotations. Vessel/field/operator names are
retained as factual asset attributes. Canonical (de-duplicated) copy of each
workbook was used — the Posters Data trees are duplicated 3–4× across the
corpus; one copy under `my-drive/Posters Data` was taken as canonical.

## Tables (`curated/`)

| File | Rows | Content |
|---|---|---|
| `fpso_basic_info.csv` | 147 | FPSO particulars: classification, max operating draft (m), construction type, leased/owned, operating water depth, location, owner, operator |
| `fpso_riser_info.csv` | 147 | FPSO riser counts: total / production / water-injection / gas-injection / gas-lift / import-export / other / umbilicals |
| `spar_basic_info.csv` | 20 | Spar particulars: location, operating water depth (m), reserves (MBOE), operator, classification society, estimated field life |
| `spar_riser_info.csv` | 20 | Spar production-riser barriers, sizes, tensioning method, riser system (air cans) |
| `semisub_basic_info.csv` | 53 | Semisubmersible particulars: status, type, operator, owner, water depth, max operating draft, classification, conversion/newbuild |
| `semisub_riser_info.csv` | 53 | Semisub riser system: total risers, prod/injection type & size, oil-export, gas-export, quarters capacity, installed power (kW) |
| `tlp_basic_info.csv` | 25 | TLP/TLWP particulars: type, status, operator, water depth (m), location, classification org, hull class, CVA scope, rig type & contracting |
| `mooring_facility_matrix.csv` | 21 | Mooring-system × facility-type feasibility (tidy long form) |

### `mooring_facility_matrix.csv`

The source was a 2-D poster matrix (mooring systems down the rows, offshore
facility types across the columns, cell = "Proven" / "Not Proven"). It has been
unpivoted to tidy long form:

| Column | Notes |
|---|---|
| MOORING_SYSTEM | Spread Mooring, Tendons & AP, Single Point Mooring |
| MOORING_SUBTYPE | e.g. Turret, CALM, SALM |
| MOORING_VARIANT | e.g. Catenary, Taut, Tension, Internal |
| CONNECTION_MODE | Permanent / Disconnectable / both |
| FACILITY_TYPE | offshore structure type (Semisubmersible, TLP, Spar, Buoy, …) |
| FEASIBILITY | Proven / Not Proven |

## Notes

- Headers in the legacy workbooks were preserved where clean; multi-row poster
  headers (TLP, Spar/Semisub riser, mooring matrix) were flattened into single
  normalized column names.
- Blank cells indicate the attribute was absent in the source.
- `NaKika` field workbook was **skipped**: its content was almost entirely
  source-reference URLs plus an internal annotation, with very few discrete
  factual cells — not convertible to a clean facts-only table.
