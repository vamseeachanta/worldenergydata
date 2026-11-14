# Facility reference data availability

Seven asset-specific reference tables are held privately pending redistribution-terms review.
Their legacy workbook source has no established independent provenance or
redistribution clearance. Notices replace the FPSO, semisubmersible, spar and
TLP particulars and riser tables. Related to #543.

## Comparison basis

The reference tables at revision `b258d0e1` were compared with the withheld
host-facility catalog at merge base `d700998b`. Names were trimmed and
case-folded; attributes were compared as trimmed strings, with every compared
cell required to be non-blank. Where host names repeat, any same-name row can
match. No numeric conversion or fuzzy matching was used.

| Table group | Rows per table | Names in host catalog | Matching non-blank attributes |
|---|---:|---:|---|
| FPSO particulars and risers | 147 | 144 | 80 classification/construction pairs; 90 drafts; 49 total-riser/umbilical pairs |
| Semisubmersible particulars and risers | 53 | 52 | 48 classifications; 42 drafts; no construction, total-riser or quarters matches |
| Spar particulars and risers | 20 | 20 | No classification matches; riser columns have no host-catalog counterpart |
| TLP particulars | 25 | 23 | No classification matches |

These counts show overlap, not upstream provenance. A lack of matching
attributes does not clear the other tables from the same workbook collection.
All seven asset-specific tables are therefore withheld together. Blank cells
were excluded from matching counts and are not evidence of shared values.

## Retained generic matrix

`curated/mooring_facility_matrix.csv` remains unchanged: 21 rows of generic
mooring-system and facility-type feasibility, with no named asset rows. The
schema describes only this retained table. Retention does not establish rights
for the withheld asset-specific tables.

The matrix is in tidy long form: `MOORING_SYSTEM`, `MOORING_SUBTYPE`,
`MOORING_VARIANT`, `CONNECTION_MODE`, `FACILITY_TYPE` and `FEASIBILITY`.

## Limits

Earlier Git objects and previously published external copies are not removed.
History and external-copy disposition remain maintainer decisions. Withheld
record totals are unavailable, not zero; metadata counts describe retained
public files only.
