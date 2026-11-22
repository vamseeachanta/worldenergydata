# Curated fleet merge readiness assessment

The stored vendor-only inputs cannot replace the curated drilling fleet without
losing named records. All stored raw sources retain the named baseline, but
unnamed records prevent a complete coverage assessment. These are observations
of the repository snapshot, without a website refresh or curated write.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Add a reproducible coverage assessment before curated replacement. |

## Scope and method

Refs #407; parent #127; sparse-dimension fix #408 and merged PR #409.
The later issue comments and merged change supersede the original proposal to
fix the parser before attempting any assessment. Current stored field presence
must still be measured rather than inferred from those comments.

Slice 1 adds `quality/merge_readiness.py`: a pure comparison of baseline and
candidate normalized names, plus caller-selected field-presence checks.
Slice 2 adds its read-only command: discover raw parquet sources recursively,
apply the existing fleet deduplicator, select drilling records and compare with
the curated CSV. Slice 3 records the current snapshot findings and limitations.

For baseline names B and candidate names C, retained names are B intersect C,
added names are C minus B, and removed names are B minus C. The definitions come
from [Discrete Mathematics: An Open Introduction, third edition (2019),
section 0.3, Sets](https://discrete.openmathbooks.org/dmoi3/sec_intro-sets.html).
The replacement criterion follows the coverage-loss disclosure in PR #409:
any known removed name blocks replacement; no loss tolerance is assumed.
The normalization is the existing `dedup/normalizer.py` implementation.

Missing or empty inputs, unnamed rows and duplicate normalized names give
`NOT_EVALUATED` unless a nonempty candidate already demonstrates named-record
loss. An empty candidate remains `NOT_EVALUATED` because there is no replacement
to assess. Field presence is independent: callers select the required fields;
nulls, blank strings and nonfinite numbers count as missing, while zero counts
as present. Missing cells block that selected presence check. Without selected
fields, presence is `NOT_EVALUATED`. These are data checks without engineering
coefficients or acceptance limits.

## Snapshot findings

All paths in this section are relative to
`packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/_data/`.
Counts are enumerations of those committed inputs at the baseline revision,
`648d6de46081ad98a06504a25ec8a222acbd41b1`.

| Observation | Count | Evidence |
| --- | ---: | --- |
| Baseline rows | 2,268 | `curated/drilling_rigs.csv` |
| Baseline distinct nonempty normalized names | 2,263 | Same CSV; normalization described above |
| Baseline unnamed rows | 5 | Same CSV |
| Vendor-only rows | 48 | `raw/spec_details/*.parquet`; source counts 31 + 17 |
| Vendor-only retained baseline names | 48 | Intersection with baseline names |
| Vendor-only removed baseline names | 2,215 | Set difference; 2,263 minus 48 |
| Vendor-only missing design cells | 17 | `RIG_DESIGN` in vendor-only inputs |
| Vendor-only missing water-depth rating cells | 17 | `WATER_DEPTH_RATING_FT` in vendor-only inputs |
| Vendor-only missing source-link cells | 0 | `DATA_SOURCE_URL` in vendor-only inputs |
| All raw rows | 2,568 | All `raw/*/**/*.parquet` inputs |
| All-source deduplicated drilling rows | 2,398 | Existing deduplicator, then drilling-category selection |
| All-source distinct named drilling records | 2,394 | Same candidate; normalization described above |
| All-source retained baseline names | 2,263 | Intersection with baseline names |
| All-source added names | 131 | 2,394 minus 2,263 |
| All-source removed baseline names | 0 | Set difference |
| All-source unnamed drilling rows | 4 | Same candidate |
| All-source missing design cells | 2,177 | `RIG_DESIGN` in candidate |
| All-source missing water-depth rating cells | 2,073 | `WATER_DEPTH_RATING_FT` in candidate |
| All-source missing source-link cells | 2,172 | `DATA_SOURCE_URL` in candidate |

The vendor-only coverage and selected field-presence checks are `BLOCKED`.
All-source name coverage is `NOT_EVALUATED` because unnamed rows remain; the
selected field-presence check is `BLOCKED`. Missing fields across historical
records are a completeness observation, not a newly imposed engineering limit.
No physical identity, design suitability or estimate is established.

## Reproduce

Run from the repository root with the package dependencies installed:

```sh
PYTHONPATH=packages/worldenergydata-vessel_fleet/src:src \
python -m worldenergydata.vessel_fleet.quality.merge_readiness \
  --data-dir packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/_data \
  --required-field RIG_DESIGN \
  --required-field WATER_DEPTH_RATING_FT \
  --required-field DATA_SOURCE_URL
```

The command prints JSON to standard output and never writes to its input tree.
The source inventory gives row counts by raw relative path. For a vendor-only
comparison, load `raw/spec_details/*.parquet`, concatenate their records and
call `assess_merge_readiness` with the CSV records and the same selected fields;
do not overwrite the curated files or move raw inputs to simulate this subset.

Command exit codes are interface choices: `0` means the explicit coverage and
presence checks passed, `2` means blocked or unreadable input, and `3` means a
check was not evaluated. Engineering validity always stays `NOT_EVALUATED`.
A nonzero exit for the stored snapshot is an expected assessment result.

## Verification and limits

Synthetic tests enumerate name intersections and differences independently in
their docstrings. They cover equal-size replacements that lose a name, case and
spacing normalization, missing or empty inputs, unnamed rows, duplicate names,
null and nonfinite cells, sparse columns, zero values, nested sources, missing
baseline files, unreadable inputs, category selection and deduplication. A byte
comparison before and after command execution proves input files are unchanged
and no files are created by the command.

This assessment ends before hull estimation, schema validation and persistence.
It uses the curated CSV as the baseline and does not establish CSV/parquet
agreement, stable physical identity, field-value preservation, provenance,
freshness, units, source rights or engineering validity. Name matches alone
cannot prove that two records describe the same physical unit. The existing
fusion script is unchanged and does not enforce this assessment automatically.

Later slices: reconcile unnamed records; establish stable-identity and field
preservation checks; qualify required specs and source freshness; add a guarded
publication step after review. A parser change or refreshed vendor capture
requires separate evidence of the source structure and independently expected
field values.
