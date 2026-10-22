# Public HSE investigation refresh

The drilling analysis and intervention inventory share a configurable INCINV
workflow. The published counts describe investigation records. They are neither
a complete incident census nor exposure-normalized risk rates.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| 1 | 2026-10-22 | The public refresh workflow, QA and chart exports are described. |
| 2 | 2026-10-22 | Historical evidence is pinned; source retention limits, classification choices and replay checks are made explicit. |

## Refresh and source retention

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
Last-Modified from the response supplying the archive are recorded too. A missing
validator is recorded as null; it is never invented. Validators supplement the
digests and do not replace byte verification.
A failed request raises `BLOCKED-NETWORK`; no substitute data are generated.

No durable source archive is supplied by this repository. The public endpoint
can change. Exact historical headline replay is established only when retained
archive and member bytes match both manifest digests. A fresh download can
generate a new analysis; it cannot establish the old counts merely by using the
same URL. The checked-in chart values support replotting, not independent
reclassification of the historical population. The source manifest identifies
the expected bytes; it is not itself a retained copy.

Issued revision records are retained in the configuration and copied to the
headline JSON. A revision's date is derived from its recorded source download
timestamp, or its original explicit issue date. Rendering a later source does
not rewrite those records. A new issue adds a revision record before publication.

For a retained copy, keep the archive, extracted member and manifest together in
the configured external directory. Offline analysis verifies local bytes and
does not require a second URL; the recorded URL remains the original source.

## QA and outputs

Before classification, QA checks manifest evidence and every file digest and size,
CSV schema and row structure, nonempty row count, required composite keys,
duplicate keys, parseable dates within the configured range and download date,
and the quantity/unit contract `investigation records [count]`. The source has
no unique incident ID. Its composite key uses date, time, area/block and accident
type; lease numbers are optional, with missing leases counted separately.

A failed refresh writes `not_evaluated` with a reason, clears chart values and
replaces the public HTML with an unevaluated page. QA statistics remain available
in `incinv-qa.json`; they are not analysis headline numbers. The public manifest
is also invalidated, so a failed refresh cannot present earlier source evidence
as the current accepted input.

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

The historical intervention memo pins its database inventory and exploration
script to an immutable repository revision. Its working JSON filename is now
used by the public inventory; the pinned artifacts, rather than that current
file, are the memo's evidence.

## Classification basis

The source accident-type vocabulary is the member
`IncInvRawData/mv_acc_investigations.txt` of the
[BSEE public archive](https://www.data.bsee.gov/Other/Files/IncInvRawData.zip).
`CLASSIFICATION_BASIS` in `public_refresh.py` records this source and the
distinction between observed vocabulary and analyst choices.

[30 CFR 250.188, 2025 edition](https://www.govinfo.gov/content/pkg/CFR-2025-title30-vol2/xml/CFR-2025-title30-vol2-sec250-188.xml),
*What incidents must I report to BSEE and when must I report them?*, provides
context for fatalities, losses of well control, fires, injuries, restricted work
or job transfer and other reporting categories. It does not prescribe the
report's severity ranking, define every historical acronym or establish a
historical coding dictionary. The source member supplies the literal vocabulary.

The severity proxy is analyst-defined: `_severity` selects the first matching
term group, in the order fatality, major, injury/lost-time, serious,
evacuation/muster, then other. `KEYWORDS` is an analyst-defined intervention
screening vocabulary. Hits can overlap and do not establish an intervention
service. The activity and subactivity classification continues to use the
canonical taxonomy with `source='bsee'`, including its direct-code precedence.

The lower date bound is the minimum parsed occurrence date in the pinned source
member. The configuration records the derivation rule and source SHA-256. This
is a coverage guard, not a regulatory commencement date. The upper bound remains
the earlier of the configured cutoff and source download date.

Classifier confidence buckets retain the historical thresholds. Scores are not
calibrated probabilities. Percentages now use one decimal place; `drill_top_areas`
and the area CSV include all observed DRILL area codes rather than a truncated
list. Year values now include every calendar year between the earliest and latest
screened occurrence, inclusive. A zero means no DRILL-classified investigation
record in this source, not zero incidents. `drill_year_range` continues to describe
the observed DRILL years. Raw accident-type strings remain excluded from exports.

## Offline checks

`tests/unit/hse/fixtures/incinv_synthetic.csv` contains synthetic rows only.
The tests seal a temporary manifest, regenerate known headlines and exercise
individual QA failure modes, download resumption and both entry points.
Literal hand counts assert areas, phases, leases, confidence buckets and HTML
KPIs as well as chart totals. Isolated Python execution is checked for both
entry points. CI routes refresh scripts, configuration and report changes to
the HSE tests, in addition to the existing package and unit-test routes.

```bash
uv run --no-project --with pytest --with pytest-cov python -m pytest \
  tests/unit/hse/test_public_refresh.py --noconftest -q -rA -p no:cacheprovider
```

For a constrained environment, direct coverage and pytest temporary output to an
external scratch directory. The broader repository suite is separate from these
stdlib workflow tests.

Set `HSE_REPLAY_DATA_DIR` to a retained archive/member/manifest directory to run
`test_pinned_public_headlines_replay`. The test verifies the two fixed source
digests before asserting the recorded population and drilling headlines. Without
matching retained inputs this test is skipped; that skip establishes no public
headline reproduction. CI's synthetic checks remain independent of network data.

## Report maintenance

Repository text is read as UTF-8 and written as UTF-8 with LF newlines; the raw
member alone retains its declared source encoding and original bytes. Numeric
claims require source provenance or an explicit `not_evaluated` disposition.
Source manifests identify inputs; generated reports do not cite one another as
independent evidence. Hand-worked literals in tests qualify the synthetic
example; agreement between generated JSON, CSV and HTML alone does not establish
correct classification. Missing retained bytes remain an explicit replay limit.
