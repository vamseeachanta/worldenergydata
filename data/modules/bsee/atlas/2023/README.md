# BSEE Atlas 2023

Source: [BSEE Atlas download page](https://www.data.bsee.gov/Main/GandG.aspx).
The manifest pins the retrieved archive, extracted database/workbook and three
CSV exports. Raw files remain outside Git; configure `BSEE_ATLAS_DATA_DIR` to an
external data directory. Install MDB Tools separately for the Access export.

```sh
uv run python scripts/bsee/fetch_sands_atlas.py
uv run python scripts/bsee/fetch_sands_atlas.py --reuse
```

The fetcher discovers the ZIP link, uses sequential requests, a descriptive
User-Agent, and at most one retry per transient request failure. HTTP refusal
stops downloading and records `refusal.json` plus a synthetic table-names-only
fixture; no engineering attribution is emitted in that case. Existing raw
outputs are preserved; a fresh directory is required for another fetch.

[Data dictionary](data_dictionary.html) documents the actual exported headers,
Access types, joins and criteria. `schema.json` is the loader contract.
`freshness.json` records dataset-specific snapshot freshness rather than changing
the older module-wide scorecard. Recorded fixtures contain five unmodified sand
rows and their lookup records (including a 1968 discovery date), with original export ordinals in fixture provenance.

`field_attribution.json` covers every null-play Gulf of Mexico roster entry.
Its counts describe **verified attribution**, **ambiguous candidates**, and
**unmatched fields**. An area-block association alone does not establish named
field identity. Candidates retain sand IDs, names, export row numbers, lookup
values and qualifiers. The sands table has no lease column; no lease association
is inferred. Canonical IDs resolve through `config/fields.yml`; unknown IDs stay
null. Multiple-play and shared-block candidates retain their qualifiers.

Remaining work: verify named-field to BOEM field-code crosswalks, backfill the
roster with reviewed attribution, regenerate the funnel, and investigate the
catalog-tail rows. The roster and funnel are unchanged by this ingest.
