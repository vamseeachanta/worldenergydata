# Public HSE investigation refresh

The drilling analysis and intervention inventory share a configurable INCINV
workflow. The published counts describe investigation records. They are neither
a complete incident census nor exposure-normalized risk rates.

## Reproduce

Use Python 3.10 or newer and curl. No database, credentials or Python dependency
installation is needed for the builder. Set `HSE_DATA_DIR` to a new external data
folder before a refresh; raw files are retained there and are not committed.

```bash
python scripts/exploration/drilling_hse_patterns_analysis.py \
  --config config/hse/public_refresh.json --data-dir "$HSE_DATA_DIR" --fetch
```

The intervention entry point accepts the same arguments and runs the same
workflow. Either entry point regenerates both JSON outputs and the existing
interactive drilling HTML. `--output-dir` redirects every generated artifact.
Paths in the configuration resolve against its declared `base_dir`, relative to
the configuration file. The taxonomy directory points to the existing canonical
classifier, not a copied classification implementation.

A completed download is resumable: an existing manifest is verified and reused.
For a new public pull, choose a new data directory. Without `--fetch`, the builder
runs offline against the configured data directory and requires its manifest.
The download permits only the public INCINV endpoint and extracts only the known
text member. Archive bytes and extracted bytes each receive their own SHA-256,
byte count, source URL and UTC download timestamp. HTTP status is recorded too.
A failed request raises `BLOCKED-NETWORK`; no substitute data are generated.

## QA and outputs

Before classification, QA checks manifest evidence and every file digest and size,
CSV schema and row structure, nonempty row count, required composite keys,
duplicate keys, parseable dates within the configured range and download date,
and the quantity/unit contract `investigation records [count]`. The source has
no unique incident ID. Its composite key uses date, time, area/block and accident
type; lease numbers are optional, with missing leases counted separately.

A failed refresh writes `not_evaluated` with a reason, clears chart values and
replaces the public HTML with an unevaluated page. QA statistics remain available
in `incinv-qa.json`; they are not analysis headline numbers.

Generated files in the configured output directory:

- `incinv-manifest.json`: source evidence copied from the data directory.
- `incinv-qa.json`: QA status, observed row count, date range and key checks.
- `drilling-hse-patterns-2026-07-05.json`: source-dated aggregate headlines.
- `drilling-hse-patterns-2026-07-05.html`: the existing interactive report.
- `drilling-{phase,severity,year,area}-values.csv`: chart categories and counts,
  with quantity and unit in the header. All areas are exported.
- `intervention-hse-patterns-2026-05-18-explore.json`: public-source inventory,
  overlapping keyword counts and explicit unevaluated join status.

Historical output filenames remain stable; the download timestamp and occurrence
date range identify the current evidence. Outputs contain aggregate categories,
not raw narratives, operator identities or asset names. The analysis retains the
canonical classifier's precedence: direct accident-type mapping can take priority
over an intervention keyword. Severity labels are text-derived proxies, not
counts of individual injuries or fatalities. Intervention keyword hits are not
confirmed service types. The previous local database and well-activity inventory
is not comparable to this public-only inventory; no well join is inferred.

## Offline checks

`tests/unit/hse/fixtures/incinv_synthetic.csv` contains synthetic rows only.
The tests seal a temporary manifest, regenerate known headlines and exercise
individual QA failure modes, download resumption and both entry points.

```bash
uv run --no-project --with pytest --with pytest-cov python -m pytest \
  tests/unit/hse/test_public_refresh.py --noconftest -q -rA -p no:cacheprovider
```

For a constrained environment, direct coverage and pytest temporary output to an
external scratch directory. The broader repository suite is separate from these
stdlib workflow tests.
