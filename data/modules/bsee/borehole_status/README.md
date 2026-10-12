# Public BSEE borehole status snapshot

Refs [issue 960](https://github.com/vamseeachanta/worldenergydata/issues/960).

`summary.json` contains per-field counts, status totals and the selected play.
`schema.json` defines the headerless 29-cell layout, utf-8-sig encoding, status
meanings and retained numeric masks. Registry lease lists determine coverage;
lease membership does not establish reservoir targeting or current ownership.
Raw downloads and full unmatched rows remain in external data storage. Every
source file has URL, UTC retrieval, terms, size and SHA-256 in source_manifest.json.
extract_manifest.json pins curated and retained outputs and the canonical registry.

Use a new external directory for each source retrieval. Set
`BSEE_BOREHOLE_RAW_DIR` to that directory; no storage location is hard-coded.
With the project environment and BSEE/core packages installed:

```sh
uv run python scripts/bsee/fetch_borehole_status.py \
  --output-dir data/modules/bsee/borehole_status_snapshot \
  --registry config/fields.yml
```

For offline regeneration from retained files, add `--reuse-manifest` and choose a
new output directory. Existing sources are never overwritten. Source masks and
unknown statuses remain explicit. Counts identify API12 boreholes on registered
bottom leases, not independent wells or quantified P&A liability.

Offline tests: `tests/unit/bsee/data/test_borehole_status*.py`.
Cost basis, underwriting wiring, and reconciliation with the independently dated
lease ingest remain downstream work. No shared metadata or registry is changed.

`BoreholeDataAcquirer.acquire_borehole_dataframe` handles the sibling
BoreholeRawData.zip headered file with network/cache behavior and DataFrame
normalization. `load_boreholes` validates headerless 5010.txt plain rows without
network/cache behavior. Use the former for DataFrame acquisition and the latter
for this digest-bound status snapshot; their source and validation contracts
prevent straightforward reuse. Convergence remains downstream work.

The default `--play-filter "lower tertiary"` can select another registry play.
`--request-delay` sets seconds between consecutive downloads (default 1).
`unmatched_summary.json` records counts and distinct leases by reason plus the
20 largest lease/reason groups, with deterministic lease tie-breaking.
The full per-lease rollup and unmatched CSV remain in external raw storage.
To regenerate the full rollup offline, retain the four source files and manifest
in a writable external directory and run with `--reuse-manifest` and a new
curated output directory; `unmatched_by_lease.json` is written beside the raw inputs.
