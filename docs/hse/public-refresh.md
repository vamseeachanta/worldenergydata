# Public HSE investigation refresh

The drilling analysis and intervention inventory share a configurable INCINV
workflow. The published counts describe investigation records. They are neither
a complete incident census nor exposure-normalized risk rates.

## Run a refresh

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
byte count, source URL and UTC download timestamp. HTTP status, ETag and
Last-Modified are recorded too (null if the server omits a header). Redirect
headers are discarded in favor of the final response headers. For the existing
snapshot, `response_metadata_observed_at` separates the later digest-matched
header observation from the original download timestamp.
A failed request raises `BLOCKED-NETWORK`; no substitute data are generated.

## Recorded snapshot limits

The checked-in aggregates describe the manifest's 2026-10-22 download: 2,027
investigation records, including 85 DRILL records (4.2%). The source endpoint is
mutable. The exact 35,938-byte archive and its 175,510-byte text member are not
retained at a durable referenced location. Digests identify bytes; they do not
make those bytes retrievable. A new download may therefore produce different
figures. Recalculating this snapshot requires the exact archived input matching
both recorded digests; neither the chart CSVs nor synthetic tests establish that
future downloads reproduce these headlines. The CSVs permit inspection of the
published chart values without rerunning classification.

## Classification assumptions

[BSEE offshore incident statistics](https://www.bsee.gov/stats-facts/offshore-incident-statistics)
identifies the reporting basis as 30 CFR 250.188 and points to
[BSEE NTL 2019-N05, Definitions](https://www.bsee.gov/sites/bsee.gov/files/notices-to-lessees-ntl/ntl-2019-n05.pdf).
The notice describes fatalities, injuries involving days away or restricted
work/job transfer, fire, explosion, loss of well control and damage reporting.
LTA is read here as lost-time accident and RW/JT as restricted work/job transfer.
The `$25k` substring matches a source damage-category label; it does not compute
losses, adjust money for inflation or apply a current reporting threshold.

The severity proxy uses the following **analyst-defined** first-match precedence,
retained for comparison with the earlier analysis. These ranks and group names
are not assigned by the regulation or validated as consequence measures.

| First matching terms (case insensitive) | Proxy label |
|---|---|
| fatality | fatality |
| blowout, explosion | major |
| lta, rw/jt, injury | injury_lost_time |
| fire, pollution, collision, $25k | serious |
| evacuation, muster, shutdown | evacuation_muster |
| no match | other |

Broad text terms such as pollution, evacuation, muster and shutdown are analyst
screening choices. Composite accident types receive only the first matching
label; no count of injured people or causal inference follows from the proxy.

`KEYWORDS` in `public_refresh.py` is an analyst-selected inventory list informed
by intervention and drilling terms in the canonical taxonomy
(`packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/activity_definitions.py`).
It uses overlapping literal substrings, including spelling variants, rather
than regulatory service categories or a validated intervention detector.

The configured lower date bound, 1995-01-01, is the start of the earliest year
observed in the sealed snapshot (first occurrence 1995-01-04). It is a snapshot
QA guard, not evidence that all earlier incidents are unavailable. Future dates
are bounded by the retrieval date. A deliberately wider historical source needs
an explicitly revised bound before it can qualify.

## QA and outputs

Before classification, QA checks manifest evidence and every file digest and size,
CSV schema and row structure, nonempty row count, required composite keys,
duplicate keys, parseable dates within the configured range and download date,
and the quantity/unit contract `investigation records [count]`. The source has
no unique incident ID. Its composite key uses date, time, area/block and accident
type; lease numbers are optional, with missing leases counted separately.

Offline analysis and download resumption use the same provenance checks. A public
manifest requires exactly one archive and one extracted text entry, HTTP 200 for
both, and the expected archive-member name. The extracted bytes must match that
member's size and SHA-256 as well as the manifest. Missing or invalid evidence
blocks qualification; explicitly synthetic fixtures retain their separate contract.

A failed refresh writes `not_evaluated` with a reason, clears chart values and
replaces the public HTML with an unevaluated page. QA statistics remain available
in `incinv-qa.json`; they are not analysis headline numbers. The copied output
manifest is also marked unevaluated, preventing stale provenance after failure.

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
The historical memo pins its inventory and exploration script to the pre-refresh
commit; its database and well-activity inputs are not supplied by this workflow.

Compared with the earlier drilling output, confidence buckets retain the original
0.90/0.70/0.50 boundaries. The percentage uses one decimal place; both the source
snapshot and its denominator have changed, so the earlier percentage is not a
rounding comparison. `drill_top_areas` now includes all area codes, preserving the
field name for consumers. Years are zero-filled from the earliest through latest
source occurrence year, including years outside the DRILL subset's nonzero
range. Zero means no classified DRILL record in this input, not complete incident
coverage. Raw accident-type distributions remain excluded because the source
text can identify facilities. Revision dates follow the source manifest rather
than the time the page is rendered.

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
