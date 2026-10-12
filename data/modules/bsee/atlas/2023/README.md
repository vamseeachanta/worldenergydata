# BSEE Atlas 2023

Source: [BSEE Atlas download page](https://www.data.bsee.gov/Main/GandG.aspx).
The manifest pins the download and disclaimer pages, archive, extracted Access
database, three Atlas CSV exports and the public operator cross-reference export.
The small `2023plays.csv` and `2023chronozones.csv` lookups are committed and load
through `schema.json` without a fetch. The sands and cross-reference exports exceed
5 MB and remain fetch-only; raw packages remain outside Git. Configure
`BSEE_ATLAS_DATA_DIR` to an external data directory; supply MDB Tools separately.

```sh
uv run python scripts/bsee/fetch_sands_atlas.py
uv run python scripts/bsee/fetch_sands_atlas.py --reuse
uv run python scripts/bsee/fetch_sands_atlas.py --reuse --update-manifest
```

A run writes its manifest in the external data directory. By default it compares
file names, source URLs, SHA-256, sizes and row counts against the committed
manifest, prints differences, and exits non-zero on a difference. Retrieval times
are excluded from comparison. Only `--update-manifest` replaces the committed
manifest. `field_attribution.json` is a deterministic derived output for fixed
inputs and is written after manifest validation; offline reuse performs no fetch.
Unsupported workbook, relationship and export timestamp claims are omitted.

The fetcher makes three sequential requests with a descriptive User-Agent and
at most one retry per transient failure. Refusals (401/403/429), server errors
(5xx), and other client errors are recorded separately. Existing raw outputs are
preserved; a fresh directory is required. Access members above 64 MiB are rejected
before reading, compared with 36,438,016 bytes in the observed database.

[Data dictionary](data_dictionary.html) documents actual headers, types and joins.
Sand identifiers are digit strings. Recorded source fixtures include five sand
rows and a 1968 discovery date; a separate cross-reference fixture is synthetic.
`freshness.json` retains dataset-specific snapshot freshness. The scorecard
generator reads module-level catalog/metadata/scheduler summaries and has no
place for a dataset-level freshness entry; adding a catalog row would change
counts without representing this snapshot. The owner would need to authorize a
dataset-level generator/schema extension before that scorecard can represent Atlas.

`field_attribution.json` covers all 103 null-play Gulf of Mexico roster entries:
**0 attributed, 90 ambiguous, 13 unmatched**, under criteria version 2.
Attribution requires an exact `BOEM_FIELD` match plus public field-name agreement
or an independent public lease/block agreement, and a single consistent play.
A block equal to the join code is not a second confirmation; the three evidence
checks retain true/false/not-available and the source field used.

The retained `2023xref_oper-comp` table confirms independent lease/block evidence
for Buckskin, one of 90 candidates; its inconsistent lookup prevents attribution.
The other 89 candidate fields lack that confirmation in the inspected tables and
registry. Candidates retain all plays, chronozones, sand IDs and export-row
citations; multiple plays remain ambiguous. The sands table has no lease column.
Eight candidate fields carry `inconsistent_lookup`: a sand-row play code or
chronozone disagrees with the plays table; direct raw-row comparison confirms a
source-data discrepancy rather than a loader join problem.

Remaining work: verified crosswalk evidence where missing, reviewed roster
backfill, funnel regeneration, and catalog-tail attribution. The roster and
funnel remain unchanged.
