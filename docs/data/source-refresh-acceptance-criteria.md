# Source Refresh Acceptance Criteria

This contract defines when a worldenergydata source can be treated as ready for periodic refresh work. It separates source-data vintage from local repository refresh evidence so agents do not mistake metadata timestamps, file modification times, or scheduler success timestamps for the newest date inside a dataset.

## Contract Artifacts

- Machine-readable contract: `data/source-refresh-acceptance-contract.json`
- Validator: `scripts/audit/validate_source_refresh_contract.py`
- Readiness summary skill: `.claude/skills/worldenergydata-source-readiness/SKILL.md`

Run the validator from the repository root:

```bash
python scripts/audit/validate_source_refresh_contract.py
```

## Required Row Fields

Each high-value source row must include:

| Field | Meaning |
|---|---|
| `module_id` | Canonical source group in the freshness contract. |
| `materialized_module_id` | Repo-local module directory that stores the data when different from `module_id`. |
| `aliases` | Known alternate module names agents may encounter. |
| `display_name` | Human-facing source group name. |
| `source_authority` | Primary public authority or maintainer. |
| `source_url_or_api` | Public source, API, or local source registry path. |
| `source_data_latest_date` | Newest accepted business/source-data date, or JSON `null` if not inspected. |
| `source_data_latest_date_basis` | How `source_data_latest_date` was proven. |
| `source_data_latest_date_unknown_reason` | Required reason when source-data date is `null`. |
| `last_successful_refresh` | Last known local refresh/proof timestamp. |
| `last_successful_refresh_basis` | Clock that produced `last_successful_refresh`. |
| `data_location` | Repo-local data path expected for the source. |
| `external_data_root_required` | Whether accepted data can exist only outside the repo. |
| `scheduler_job` | Scheduler job name or `none`. |
| `scheduler_output_dir` | Exact configured scheduler output directory. |
| `refresh_command` | Command agents should use when refresh is authorized. |
| `record_count` | Accepted row count when known. |
| `artifact_count` | Dataset/artifact count when known. |
| `refresh_cadence` | Expected refresh interval or `manual`/`reference`. |
| `freshness_grace_days` | Maximum allowed scheduler-manifest age for `fresh`. |
| `freshness_status` | Contract freshness lane. |
| `completeness_status` | Contract completeness lane. |
| `credential_requirement` | Credential, portal, or manual-download requirement. |
| `blocker_issue` | `none`, `#NNN`, or a GitHub issue URL. |
| `downstream_consumers` | Workflows or reports that depend on the source. |

## Freshness Status

Allowed `freshness_status` values:

- `fresh`: successful scheduler/source proof exists within cadence.
- `stale`: data exists but freshness proof is outside cadence or absent.
- `missing`: source is configured or expected but no accepted data/proof exists.
- `blocked`: refresh cannot pass until a named issue or external requirement is resolved.
- `unknown`: data exists but source-data vintage has not been proven.
- `reference_data`: static/reference asset where periodic refresh is not expected.
- `not_applicable`: infrastructure or non-data-product row.

## Completeness Status

Allowed `completeness_status` values:

- `full`
- `sample`
- `empty`
- `missing`
- `runtime_fetched`
- `reference_data`
- `blocked`
- `unknown`
- `not_applicable`

Completeness is not freshness. A source may be `full` and still have `freshness_status: "unknown"` until source vintage or scheduler proof is accepted.

## Scorecard Mapping

Current scorecard values are compatibility inputs, not the final acceptance vocabulary.

| Scorecard freshness | Scorecard catalog | Contract freshness | Contract completeness |
|---|---|---|---|
| `empty` | `empty` | `missing` | `empty` |
| `full` | `full` | `unknown` until source vintage or scheduler proof proves freshness | `full` |
| `missing` | `not_applicable` | `not_applicable` | `not_applicable` |
| `missing` | `runtime_fetched` | `missing` | `runtime_fetched` |
| `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` |
| `reference_data` | `reference_data` | `reference_data` | `reference_data` |
| `sample` | `sample` | `stale` until successful scheduler/source proof proves freshness | `sample` |
| `unknown` | `unknown` | `unknown` | `unknown` |
| `fresh` | any allowed value | `fresh` only if scheduler/source proof also passes | mapped from `catalog_status` |
| `stale` | any allowed value | `stale` | mapped from `catalog_status` |

Future non-wildcard scorecard pairs must be added to `scorecard_pair_mapping` before they can pass validation.

## Source-Date Rules

`source_data_latest_date` is the newest accepted date from the source dataset itself. It may use only these basis values when non-null:

- `dataset_field`
- `source_api_metadata`
- `source_publication_date`
- `source_version`

It must not use local evidence clocks:

- `metadata_refresh`
- `newest_file_modified`
- `scheduler_success`
- `manifest_timestamp`

If the source-data latest date is unknown, use JSON `null`, `source_data_latest_date_basis: "unknown"`, and a non-empty `source_data_latest_date_unknown_reason`.

## Scheduler Rule

Scheduler-backed sources must name a job from `config/scheduler/scheduler_config.yml`, and `scheduler_output_dir` must exactly match the configured job `output_dir`.

A scheduler-backed source may be marked `fresh` only when:

- `manifest.json` exists at the configured output directory.
- `status` is `success`.
- `last_success_ts` is parseable.
- Manifest age is within `freshness_grace_days`.

Missing, failed, or stale manifests must not be represented as `fresh`.

A non-scheduler source may be marked `fresh` only when it has an accepted source-data date, a documented refresh/proof timestamp, and that proof is within `freshness_grace_days`.

## Static And Blocked Sources

Use `reference_data` only for static reference assets where periodic refresh is not expected. Use `blocked` when a source has a known issue, external portal requirement, endpoint failure, or manual step that prevents normal periodic refresh. Blocked rows must carry `blocker_issue` when the blocker is tracked.

## International Chain Reconciliation

Completed reference-chain implementation is separate from materialized data and
accepted source vintage. The dated
[international reconciliation](international-source-reconciliation.md) compares
country capabilities, issue states, scheduler configuration and storage evidence.
Its register is `data/international-source-reconciliation.json`; the offline
comparison is `scripts/audit/reconcile_international_sources.py`.

Directory or manifest presence alone does not establish freshness. Historical
external-cache observations stay historical until explicitly re-observed. A
closed endpoint repair must not remain an active blocker, and a closed chain
issue must not be treated as proof that a scheduled refresh ran. External source
requirements without an open implementation issue may use `blocker_issue: none`
with a documented `refresh_blocker_reason`.

## Acceptance Checklist

A source summary is acceptable when:

- It includes every required row field.
- It reports data location and scheduler output location together.
- It distinguishes source-data vintage from refresh/proof timestamps.
- It maps scorecard freshness/completeness through the contract mapping.
- It does not mark scheduler-backed data `fresh` without a successful in-cadence manifest.
- It names blockers instead of collapsing them into `missing`.

## Deterministic Generator Input Integrity

A generator that emits input-hash manifests shall enumerate its complete input
set before the first semantic read. `worldenergydata.common.input_snapshot.freeze_inputs`
shall capture those paths, freeze their bytes, and calculate SHA-256 fingerprints
before rendering begins. Input identities and paths are supplied by the caller;
files added outside that frozen set are not discovered during rendering.

Every semantic read shall use the returned immutable byte mapping. External
binary fingerprints shall be supplied through `expected_sha256` and validated
before extraction or rendering. Unknown fingerprint identities and mismatched
fingerprints fail before the context yields any input bytes.

All outputs shall be rendered within the context. On successful exit, every
captured input is read in 1 MiB chunks and hashed again. Changed or unavailable
inputs fail the build. Publication shall occur only after successful exit; manifest input hashes
shall come from the initial frozen snapshot. Two equal endpoint hashes do not
establish that a live file remained unchanged throughout rendering; frozen bytes
keep the rendered input basis fixed even if a file changes and is restored.

Inputs are held in memory for the length of the block; peak memory is about
once the total input size plus one closing-read chunk. Present candidates are
text sources and one workbook; entry capture is not intended to stream large
binary inputs. The closing check runs only when the body finishes normally.
The result exposes read-only `bytes`, `sha256` and `size` mappings; `size` records
the frozen byte length, and `algorithm` is `"sha256"`.

Integrity failures raise `InputIntegrityError`, a `ValueError` subclass carrying
`reason` and `identity`. Reason codes are `unreadable`, `unknown-identity`,
`pin-mismatch`, `changed` and `unavailable`. Pins shall contain exactly 64
hexadecimal characters, without whitespace or a prefix. Upper and mixed case
are accepted; returned digests remain lower-case. Malformed pins fail with
`pin-mismatch`.

The helper does not provide private output staging, output-mutation detection,
canonical-output preservation or atomic publication. Those controls require
separate integration and validation before canonical output paths are touched.

The producer-identity policy is not settled by this slice. Snapshot hashes establish
input identity, not authenticated producer provenance. A hash dictionary controlled
by the same pull request is not producer provenance. Durable producer ancestry,
exact executable Git blobs, shallow-checkout history hydration, squash merges,
rebases and source-branch deletion remain subject to a separate policy and tests.
