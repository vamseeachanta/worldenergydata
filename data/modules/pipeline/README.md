# Pipe dimension inputs

The distributed `api_5l_pipe_schedule.csv` is a header-only compatibility
template. All 43 previous data rows were removed because their only stated
sources were standards. No replacement engineering rows are supplied, and no
standard document was opened. Empty default lookups return no match.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-26 | Removed standards-sourced rows and required independent row provenance. |

## Caller input contract

Pass a directory to `PipelineSpecLookup(data_dir=...)` containing the CSV and
`sources.yml`. Keep the existing CSV column names. Supply nominal size,
outside diameter, wall thickness, schedule label and any optional mass,
grade or domain classifications from an independently usable source. The
legacy `standard` column is an optional caller classification label, never
permission to copy a standards table or a claim of compliance.

Each CSV data row requires one source record. `row: 1` identifies the first
data row after the header, rather than the physical file line. The manifest
has `version: 1` and a `rows` list. Each entry requires:

| Field | Meaning |
| --- | --- |
| `row` | Unique, one-based CSV data row number |
| `kind` | `manufacturer`, `public_paper` or `design_basis` |
| `title` | Exact source title |
| `publisher` | Source publisher |
| `url` or `catalogue_number` | Public HTTP(S) location or source catalogue identifier |
| `revision` | Source revision; explicitly state `unversioned` if applicable |
| `date` | Source publication or design-basis date in quoted `YYYY-MM-DD` form |

No record is included as an example engineering input. Tests generate invented
geometry and label its records `kind: synthetic`, with title, publisher and
catalogue identifier explicitly identifying test data. That kind requires
`allow_synthetic=True` and must never be used for a study.

All dimensions must be finite and positive; twice the wall thickness must be
less than outside diameter. Supplied inch and millimetre dimensions must agree
within 0.02 mm for rounding. Schedule labels cannot be empty. Mass may be
omitted; when present it must be finite and positive. Missing or inconsistent
provenance, duplicate row records or YAML keys, and standards-attributed source
labels are rejected before matching. Invalid inputs raise `ValueError`; a
missing CSV retains the existing empty-result behavior. Sources are included
in the matched result as `provenance`, alongside the existing result keys.

The source-label guard rejects common standards-body labels in the legacy
classification field and in source title, publisher, URL and catalogue number.
Use the independent document's own title and identifier. This conservative
label check cannot establish source rights or verify the contents of a caller's
document; the maintainer must review the original source before adding data.
It does not retrieve URLs or infer a source from remembered values.

## Plain geometry

Unit conversion is `inches = millimetres / 25.4`. Inner diameter can be computed
as `D - 2t`; annulus area is `pi * t * (D - t)`. With `D` and `t` in millimetres
and caller-supplied density in kg/m³, mass per metre is
`pi * t * (D - t) * 1e-6 * density`. These formulas do not determine nominal
size, schedule, grade, density or design suitability. The lookup validates
units but does not invent engineering rows or compute missing mass.

## Removal inventory

Every value in every original data row was removed: `nps_in`, `od_mm`, `od_in`,
`schedule`, `wt_mm`, `wt_in`, `weight_kgm`, `grade_range`, `standard` and
`domain_hint`. No original dimensional or material value is reproduced here.
The following identifiers refer only to original CSV file lines.

| Source key | Original stated source | Revision and date |
| --- | --- | --- |
| pipe | API 5L / ASME B36.10M | Not recorded |
| riser | API 5L / API STD 16F | Not recorded |

| Original CSV line | Source key | Disposition |
| --- | --- | --- |
| 2 | pipe | Removed in full |
| 3 | pipe | Removed in full |
| 4 | pipe | Removed in full |
| 5 | pipe | Removed in full |
| 6 | pipe | Removed in full |
| 7 | pipe | Removed in full |
| 8 | pipe | Removed in full |
| 9 | pipe | Removed in full |
| 10 | pipe | Removed in full |
| 11 | pipe | Removed in full |
| 12 | pipe | Removed in full |
| 13 | pipe | Removed in full |
| 14 | pipe | Removed in full |
| 15 | pipe | Removed in full |
| 16 | pipe | Removed in full |
| 17 | pipe | Removed in full |
| 18 | pipe | Removed in full |
| 19 | pipe | Removed in full |
| 20 | pipe | Removed in full |
| 21 | pipe | Removed in full |
| 22 | pipe | Removed in full |
| 23 | pipe | Removed in full |
| 24 | pipe | Removed in full |
| 25 | pipe | Removed in full |
| 26 | riser | Removed in full |
| 27 | riser | Removed in full |
| 28 | pipe | Removed in full |
| 29 | pipe | Removed in full |
| 30 | pipe | Removed in full |
| 31 | pipe | Removed in full |
| 32 | pipe | Removed in full |
| 33 | pipe | Removed in full |
| 34 | pipe | Removed in full |
| 35 | pipe | Removed in full |
| 36 | pipe | Removed in full |
| 37 | pipe | Removed in full |
| 38 | pipe | Removed in full |
| 39 | pipe | Removed in full |
| 40 | pipe | Removed in full |
| 41 | pipe | Removed in full |
| 42 | pipe | Removed in full |
| 43 | pipe | Removed in full |
| 44 | pipe | Removed in full |

Re-sourced rows: none. No independent public source has been verified for
these rows; future additions require exact citations and review. Historical
capability reports describe earlier snapshots and do not supply current inputs.
