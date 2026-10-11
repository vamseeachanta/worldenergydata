# Public BSEE borehole status snapshot

Refs [issue 960](https://github.com/vamseeachanta/worldenergydata/issues/960).

[snapshot.html](snapshot.html) contains the counts and limitations;
[data_dictionary.html](data_dictionary.html) defines the observed positional layout.
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
