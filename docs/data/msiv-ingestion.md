# MSIV particulars ingestion

The ingestion command reads a local specifications matrix, maps public
particulars into the construction schema, and merges them with curated records.
Raw source documents and commercial analysis stay outside the repository.
No engineering coefficients or estimated vessel specifications are introduced.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Document the table contract and validation needed for reproducible ingestion. |

## Source contract

Supply a directory containing `vessel-specifications-matrix.md`. The command's
`--msiv-dir` option overrides the collector's configured environment directory.
An unset or missing source produces no records and logs a warning.

The first matching Markdown table must have a separator row and these complete
column headings, in any order:

- `Vessel Name`
- `Type`
- `LOA (m)`
- `Beam (m)`
- `Draft (m)`
- `Main Crane (MT)`

Heading case and repeated whitespace are normalized. Duplicate headings are
rejected. Unit labels are required; no unit conversion is inferred.

Optional fields are `IMO Number` (or `IMO`), `Aux Crane (MT)`, `DP Class`,
`Accommodation`, `Deck Area (m2)` (also `m²`), `Deck Load Capacity (MT)` and
`Source URL`. Deck load capacity means total tonnes, not tonnes per square metre.
Only the explicit particulars fields are mapped. Unrecognized columns and
unrelated tables are excluded.

The destination field names and sign/identifier rules come from
`ConstructionVesselSchema` and `BaseVesselSchema` in the package's `schemas/`
directory. All dimensioned values map directly in their labelled units. Existing
source conventions retain the first transit/operating draft and the per-crane
capacity after a multiplicity prefix. They are parsing conventions, not an
assessment of operating draft or combined lifting capability.

## Validation and provenance

Missing cells remain unknown. Malformed numeric values, non-finite or negative
particulars, fractional accommodation, malformed DP labels, empty normalized
names and invalid identifier formats reject the row. Other rows continue to be
processed. Warnings identify row positions or
column-count problems without echoing source values.

Source references must be plain HTTP(S) URLs without credentials, queries or
fragments; local paths and Markdown link syntax are rejected. Only public
brochure URLs should be supplied. This syntax check does not verify publication
rights or fetch the URL.

Each accepted source row carries the existing source tag, optional brochure URL
and any supplied identifier. Identifiers are format checked, not registry
verified. DP labels are parsed, but equipment-class compliance remains
NOT_EVALUATED without a cited classification source. Deduplication uses the
existing IMO/normalized-name rules and source
priorities. Conflicting identifiers produce the existing reconciliation warning.
The merge retains one record-level source tag and URL; it does not provide
field-level lineage or establish that either identifier is registry-correct.

## Run and inspect

Use an explicit output directory when preparing a review copy. It must already
contain `curated/construction_vessels.csv` as the starting records.

```sh
uv run python scripts/vessel_fleet/ingest_offrepo_construction_vessels.py \
  --msiv-dir <source-directory> --data-dir <output-directory> --dry-run
uv run python scripts/vessel_fleet/ingest_offrepo_construction_vessels.py \
  --msiv-dir <source-directory> --data-dir <output-directory>
```

A dry run reads and validates without writing. A normal run writes curated CSV
and Parquet. The default output location is the package's bundled `_data/`
directory. The command also reads any separately configured construction source.
Review warnings, identifier conflicts, source URLs and both outputs before
promoting a dataset.

## Evidence and remaining work

`tests/unit/vessel_fleet/test_msiv_ingestion.py` uses synthetic inputs with
identity mappings and a hand-calculated merge count. It checks table boundaries,
validation, private-column exclusion, provenance, identifier/name deduplication,
CSV/Parquet output, repeatability and dry-run preservation.

The off-repo brochure dataset was unavailable during implementation. No curated
records were regenerated and no real particulars were asserted. Dataset-level
coverage and identifier reconciliation remain NOT_EVALUATED until the source
is supplied and its public provenance is reviewed.
