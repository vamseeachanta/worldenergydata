# International source-refresh reconciliation

The refresh contract describes accepted data evidence; completed country-chain
code does not establish persistent scheduler output. Brazil's resolved endpoint
blocker is removed, Spain's configured output is registered, and implementation,
scheduler and storage evidence are compared separately. No country data was
downloaded during this reconciliation. External storage is **NOT_EVALUATED**.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Separate implementation completion from data acceptance and correct stale refresh metadata. |

## Evidence and method

The dated issue states and repository capability paths are recorded in
[`international-source-reconciliation.json`](../../data/international-source-reconciliation.json).
Public issue bodies, closeout comments and states were read on the recorded
observation date. They are historical evidence, not live availability checks.
The public issue references remain in the register: #713, #716, #717, #718, #719,
#720, #721, #722, #753, #763, #806, #807, #809, #810 and #831.

The comparison reads the register, the
[`source-refresh-acceptance-contract.json`](../../data/source-refresh-acceptance-contract.json),
[`scheduler_config.yml`](../../config/scheduler/scheduler_config.yml) and the
explicitly listed capability files. It imports no country clients, executes no
scheduler jobs and makes no network requests. There are no physical equations,
conversion factors or new numeric acceptance limits in this change. Status
decisions follow the repository's
[source-refresh acceptance criteria](source-refresh-acceptance-criteria.md).

The external inventory reported in #909/#917 observed Spain's cache but did not
observe corresponding country directories for Norway, UK, Brazil, Canada, Mexico
or West Africa. Those observations are retained as historical claims, not
relabelled as current observations. The external root is unavailable here; #910
remains the broader inventory dependency. No remote filesystem was queried.
An absent directory in this checkout cannot establish absence on external storage.

## Country comparison

Paths below are relative to an explicitly selected data root, except for package
evidence, whose full repository-relative paths are listed in the register.

| Source | Issue evidence | Capability in this checkout | Scheduler / output | Interpretation |
| --- | --- | --- | --- | --- |
| Norway (`sodir`) | #716 closed | Loader-backed adapter and `sodir/reference_chain.py` | `sodir_refresh` / `modules/sodir` | Chain tests use injected inputs. The scheduled job writes blocks, wellbores and fields; it does not materialize the monthly-production loader cache. |
| UK (`ukcs`) | #717 closed | NSTA loader and `ukcs/reference_chain.py` | `ukcs_refresh` / `modules/ukcs` | Synthetic compatibility inputs remain. A successful reference-chain test does not run the refresh job or retain production downloads. |
| Brazil (`brazil_anp`) | #718 and #459 closed | Monthly official ZIP client and `brazil_anp/reference_chain.py` | `brazil_anp_refresh` / `modules/brazil_anp` | #459 was repaired through the monthly download path. Contract freshness is `missing`, with no active endpoint blocker; current accepted output/vintage is unproven. |
| Canada | #719 closed | Production-text parser and `canada/reference_chain.py`; default loader is a labeled synthetic fixture | No registered job / expected `modules/canada` | Code explicitly defers live PDF fetch/cache. Issue closure does not establish live ingestion; source redistribution restrictions remain relevant. |
| Mexico (`mexico_cnh`) | #720 open | Existing SIH scraper | No registered job / expected `modules/mexico_cnh` | Replacement direct-source loader and scheduled chain are not established by package existence. Continue under #720. |
| West Africa | #919 open | NUPRC and EITI clients | No registered job / expected `modules/west_africa` | Clients do not establish scheduled ingestion or a country chain. Continue under #919. |
| Spain (`spain_cores`) | #763, #806, #807, #809, #810 closed | Live workbook loader, reference chain and report | `spain_cores_refresh` / `spain/cores` | Historical cache and success evidence exists outside `data/modules`. Current strict config rejects missing accepted density factors; closure of #807 records that remaining limitation. |
| Australia | #721 closed | Metadata reference chain, explicitly screening-only | No registered job / expected `modules/australia` | Production is unavailable. #831 documents seed/real/screening distinctions; closure cannot be interpreted as production ingestion. |

Norway, UK and Brazil jobs require an explicit output directory. Scheduler
configuration supplies one, but configuration alone does not show that a job
ran successfully. Runtime caches can also be caller-selected or temporary.
The code and issue evidence explain why completed reference chains need not
leave a directory at the canonical output path; they do not establish the
specific operational cause of any historical missing directory.

Spain's density qualification comes from
[`crude_density_factors.json`](../../packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/crude_density_factors.json),
whose `coverage_status` and `source_gap_fields` retain a source gap, and
`scheduler_config.yml`, whose `allow_default_density` is false. The contract's
`refresh_blocker_reason` records this external source requirement without
reopening the closed implementation issue. No new freshness grace period is
assumed: Spain's `freshness_grace_days` remains null. Counts, accepted refresh
time and source-data date also remain null until inspected evidence supports them.

## Offline comparison

From the repository root:

```bash
python scripts/audit/reconcile_international_sources.py
python scripts/audit/reconcile_international_sources.py --data-root "$DATA_ROOT"
python scripts/audit/validate_source_refresh_contract.py
```

`DATA_ROOT` must be an explicitly selected accessible data directory, containing
`modules/` and, where present, `spain/`. It is not the repository root. Without
it, or when it is unavailable, storage observations are `NOT_EVALUATED`.
The comparison returns a nonzero exit status for metadata discrepancies such as
a closed active blocker, a missing expected scheduler job, mismatched paths or
missing capability evidence. Missing storage alone is reported, not repaired.
Only the configured relative paths and manifest presence are inspected; no
recursive crawl, source parsing or file copying takes place. Symlinked observed
paths are reported as unavailable.

| Observation | Result | Meaning |
| --- | --- | --- |
| No accessible selected root | `NOT_EVALUATED` | No storage conclusion is possible. |
| Root accessible, country directory absent | `not_observed` | No directory at this selected path. |
| Country directory exists without a manifest | `directory_only` | Presence only; contents and provenance are unverified. |
| A manifest file exists | `manifest_present` | Presence only; success, age, source dates and data completeness are unverified. |
| Non-directory, inaccessible or symlinked country path | `unavailable` | Observation cannot be accepted. |

## Worked example

Inputs are synthetic and contain no country data: an accessible data root,
an empty `modules/brazil_anp` directory and the repository metadata. The register
says #459 is closed; the corrected contract has no Brazil endpoint blocker.

```python
import os
from pathlib import Path
from tempfile import mkdtemp
import sys

sys.path.insert(0, "scripts/audit")
from reconcile_international_sources import reconcile

data_root = Path(mkdtemp(dir=os.environ["TMPDIR"]))
(data_root / "modules/brazil_anp").mkdir(parents=True)
report = reconcile(Path.cwd(), data_root=data_root)
brazil = next(row for row in report["sources"]
              if row["module_id"] == "brazil_anp")
print(brazil["findings"])
print(brazil["materialization_status"])
print(brazil["freshness_status"])
```

Hand-derived answer: the closed issue is no longer an active blocker, so findings
are `[]`. Directory existence without a manifest gives `directory_only`.
Contract freshness stays `missing`: an empty directory proves neither a refresh
nor a source business date. The regression tests construct this truth table
independently; adding a failure manifest changes presence to `manifest_present`
and still cannot promote freshness.

## Follow-up

- Re-observe external storage through #910 and carry materialization badges
  through #918. Both issues remain open. Existing issues are reused; no duplicate
  issue is created by this reconciliation.
- Norway, UK and Brazil need separately authorized operational refresh and
  source-vintage acceptance if the canonical outputs remain absent. Reference
  chain completion alone does not close that gap.
- Canada needs the deferred live-fetch/cache path and source-rights qualification;
  Mexico remains under #720; scheduled West Africa ingestion remains under #919.
- #722 and #753 remain open source-characterization work. Their broader country
  candidates are not represented as implemented production chains here.
- Preserve Spain's source-rights and density qualifications. Historical success
  with an explicit default-factor assumption does not establish strict refresh
  readiness or permission to redistribute raw workbooks.
- #831 remains the benchmark-provenance reference. This reconciliation does not
  regenerate benchmarks or alter fiscal/economic assumptions.
