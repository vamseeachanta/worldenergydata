# U.S. onshore source readiness

The [matrix](source-readiness-matrix.md) separates regulator data from land,
lease, mineral and county/title evidence for underwriting. Its
[catalog](../../../config/us_onshore_readiness.json) records reported inventory
and repository configuration; it does not certify current downloads or title.
The implementation addresses #911 under #909, with inventory acquisition
remaining in #910.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Establish source coverage and evidence boundaries before acquisition. |

## Scope and evidence

The baseline reports Texas RRC, Kansas KGS, Oklahoma OCC and Colorado ECMC as
`downloaded` because #909's **Current evidence snapshot** reports their data
directories. `pressure_screen` is `derived`: the same snapshot reports the
directory, while the existing analysis package establishes its derivative role.
These are reported observations, not an inspection of current data bytes.
The matrix's observation timestamps identify when the cited evidence was
reviewed; they are neither source vintage nor successful refresh timestamps.
No remote data roots are traversed and no private archives are imported.

The eight state landman endpoint groups (TX, NM, OK, ND, CO, WY, LA, UT), BLM
MLRS and county references come from
[landman configuration](../../../config/landman.yml). `configured-only` means
configuration exists while materialization is not established by this evidence.
County office reference code exists, but that is distinct from downloaded
recorder instruments. Mineral ownership and lease fields are configured data
models, not evidence of current interests. Arkansas remains `missing`, not
materialized in the reported inventory, with discovery required.

EIA is `partial/error`: #266 documents the runtime credential blocker and lack
of a proven scheduled write. Infrastructure is partial because the repository
has Texas metrics but broader materialization is unverified. HSE is partial
because existing offshore collection evidence cannot establish onshore coverage.
Neither label asserts a current endpoint failure. Individual sources can replace
these reported statuses through explicit inventory observations.

## Three implementation slices

- Catalog: source authority, state, domain, coverage, status, evidence scope,
  observation time, limitations, discovery requirement and linked issues.
- Report: validated per-source observations, JSON and Markdown output,
  preservation of previous evidence in JSON, and quarantine for private data.
- Acquisition guidance: the matrix, this worked example and regression tests.

No equations, physical constants, numerical acceptance thresholds or scoring
weights are used. Acquisition priorities are editorial recommendations, not
computed engineering acceptance limits.

## Status and qualification contract

The materialization vocabulary follows #910: `downloaded`, `derived`,
`configured-only`, `partial/error`, `missing`, `private/legacy`.
Discovery is a separate boolean so a missing source can explicitly require it.
An inventory observation changes only the named source; a failed observation
cannot silently reuse a reported downloaded status. JSON keeps that earlier row
under `prior_evidence`. Markdown displays the effective observation.

The [source refresh acceptance contract](../../data/source-refresh-acceptance-criteria.md),
**Freshness Status**, **Completeness Status** and the scheduler/static
acceptance rules (#462), defines the additional evidence needed to assess refresh
readiness. Materialization alone is insufficient. Every row therefore retains
`freshness: unknown`, `completeness: unknown` and
`qualification: NOT_EVALUATED`, including downloaded and derived sources.
Public ingestion is `NOT_EVALUATED`, or `quarantined` for private/legacy status.
No observation can assert ready, fresh, complete or approved public reuse.

## Worked example: incomplete regulator batch

Input: [readiness-example.json](readiness-example.json) is synthetic, explicitly
labelled as an example, and is not live inventory evidence. It reports a partial
Texas regulator batch against a baseline reported download.

Method: match `source_id`, validate its materialization status, nonempty evidence
and limitations, and an ISO timestamp with time zone; preserve the previous
observation, then replace that source's effective evidence. Reject unknown IDs,
duplicate IDs, duplicate JSON keys, unsupported fields and unsupported statuses.
Catalog and inventory envelopes contain exactly `sources` and `observations`,
respectively; each holds a list. Catalog rows have the fields visible in the
catalog. Inventory entries contain exactly the fields in the example.
Evidence locators are assertions supplied by the caller, not authenticated
manifests. Source discovery and acquisition are separate steps.

Run from the repository root with the package available on the Python path:

```bash
PYTHONPATH=src python -m worldenergydata.analysis.us_onshore_readiness
PYTHONPATH=src python -m worldenergydata.analysis.us_onshore_readiness \
  --inventory docs/data-sources/onshore/readiness-example.json --format json
```

Answer, by independent categorical reasoning:

| Source | Baseline | Example result | Reason |
| --- | --- | --- | --- |
| Texas RRC | downloaded, reported | partial/error | The named regulator observation overrides its reported download. |
| Texas landman endpoints | configured-only | configured-only | A regulator observation is not a land-record download. |
| County recorder/title | missing | missing | No recorder instruments were supplied. |
| All sources | qualification NOT_EVALUATED | qualification NOT_EVALUATED | Neither observation proves freshness, completeness, rights or title. |

The unit tests enumerate those expected results without calling the report to
calculate them. The committed matrix is also compared with the catalog output.
To regenerate the baseline matrix, omit `--inventory` and direct Markdown output
to `docs/data-sources/onshore/source-readiness-matrix.md`. Other computation
outputs belong outside the repository.

## First acquisition candidates and reuse

| Candidate | Why it matters | Next evidence required |
| --- | --- | --- |
| Arkansas regulator | Close the named state coverage gap for wells, permits and production. | Authority, endpoint, access terms and a qualified ingestion contract. |
| BLM MLRS | Federal lease status and legal descriptions constrain acreage interests. | Access/rights review, lease coverage and dated instrument evidence. |
| County recorder/title | Assignments, releases and encumbrances determine the title chain. | County scope, recording dates, fees, rights and instrument availability. |
| Lease and mineral records | Current interests and burdens require instrument-level reconciliation. | Legal descriptions, severance history, assignments and qualified review. |
| EIA | Production and market context require a successful existing scheduler path. | Resolve #266 and meet #462 successful-refresh evidence requirements. |

Reuse downloaded regulator work and #708 pressure-screen work before acquiring
overlapping wells or observations. #680 owns the broader production/reservoir
database and #681 the drilling/well database; this matrix creates neither.
#462 owns refresh acceptance and #266 EIA operationalization. #909 coordinates
landman coverage, and #910 supplies the broader bounded inventory. Each row
names relevant existing issues rather than opening duplicate acquisition work.

## Existing issue links

- [Pressure and state-regulator reuse: #708](../../../../../issues/708).
- [EIA scheduler operationalization: #266](../../../../../issues/266).
- [Production/reservoir database: #680](../../../../../issues/680).
- [Drilling/well database: #681](../../../../../issues/681).
- [Source refresh acceptance: #462](../../../../../issues/462).
- [Broader bounded inventory: #910](../../../../../issues/910).
- [Underwriting coverage coordination: #909](../../../../../issues/909).

## Limits and next work

Current artifact integrity, record counts, coverage, source vintage, successful
refresh, access rights, pressure semantics, title-chain completeness and mineral
interest fractions remain NOT_EVALUATED. A regulator lease label, a county office
entry, a federal patent or nearby infrastructure does not prove current title,
commercial access or underwriting suitability. Colorado candidate pressures
remain subject to the existing
[pressure-source qualification limits](state-well-databases/colorado-ecmc-pressure-source-discovery.md).

A verified inventory from #910 can supply per-source observations through
`--inventory`; this does not substitute for #462 source acceptance or title
review. Source-specific acquisitions and any underwriting diligence pack remain
later work under #909. No acquisition or external inventory was performed here.
