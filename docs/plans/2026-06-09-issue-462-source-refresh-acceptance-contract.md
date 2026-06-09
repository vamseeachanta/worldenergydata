# Plan: Issue #462 — Source refresh acceptance criteria contract

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/462  
**Status:** plan-review  
**Tier:** T2 (contract document + machine-readable validation + skill update)  
**Client:** N/A  
**Project:** N/A

## Resource Intelligence Summary

### Execution mode

Planning will use `parallel-readonly` evidence gathering. Implementation will be `single-lane` unless review requires separate worktrees for the documentation and validator changes.

### Reproduction proofs

N/A — this is a governance/data-contract issue. It does not allege a failing runtime path; it defines the acceptance contract that later runtime checks will use.

### Evidence observed at planning time

- `.claude/skills/worldenergydata-source-readiness/SKILL.md` already reports source readiness, data locations, scheduler output directories, latest-known dates, and blocker inputs.
- `.claude/skills/worldenergydata-source-readiness/scripts/source_readiness_summary.py --format json` emits 31 module rows from `data/freshness-scorecard.json`, `data/modules/*/_metadata.json`, scheduler config, scheduler manifests, and `data/catalog.yaml`.
- `scripts/audit/data_freshness_scorecard.py` currently derives `freshness_status` from scheduler manifests, catalog status, dataset count, and module metadata.
- `tests/unit/audit/test_data_freshness_scorecard.py` covers a successful scheduler manifest, a non-success scheduler manifest, and output writing.
- `scripts/cron/scheduler-health.sh` already treats missing, non-success, unparseable, or stale scheduler manifests as stale scheduler health.
- `module-manifest.yaml` documents existing `catalog_status` values: `full`, `sample`, `empty`, `runtime_fetched`, `reference_data`, `not_applicable`, and `unknown`.
- `config/scheduler/scheduler_config.yml` defines seven enabled scheduler jobs: `bsee_refresh`, `sodir_refresh`, `eia_us_refresh`, `metocean_refresh`, `brazil_anp_refresh`, `ukcs_refresh`, and `lng_terminals_refresh`.

### Gaps this plan will close

- There is no canonical contract that distinguishes `source_data_latest_date` from `last_successful_refresh`.
- There is no machine-readable list of required source-readiness fields per high-value data group.
- The current scorecard can report values such as `empty`, `sample`, and `full`, but the issue-level acceptance contract does not yet specify compatibility between catalog/completeness values and freshness values.
- The readiness skill has a drafting pattern, but it does not point agents to a repo-level acceptance contract.
- There is no validator that checks enum values, required data groups, scheduler-backed source mappings, or the "scheduler manifest required for green" rule without running downloads.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` |
| Plan index row | `docs/plans/README.md` |
| Contract document | `docs/data/source-refresh-acceptance-criteria.md` |
| Machine-readable contract | `data/source-refresh-acceptance-contract.json` |
| Validator | `scripts/audit/validate_source_refresh_contract.py` |
| Tests | `tests/unit/audit/test_source_refresh_contract.py` |
| Skill update | `.claude/skills/worldenergydata-source-readiness/SKILL.md` |
| Skill reference update | `.claude/skills/worldenergydata-source-readiness/references/readiness-fields.md` |
| Plan review r1 — schema | `scripts/review/results/2026-06-09-plan-462-schema-r1.md` |
| Plan review r1 — integration | `scripts/review/results/2026-06-09-plan-462-integration-r1.md` |
| Plan review r2 — schema | `scripts/review/results/2026-06-09-plan-462-schema-r2.md` |
| Plan review r2 — integration | `scripts/review/results/2026-06-09-plan-462-integration-r2.md` |
| Plan review r3 — mapping | `scripts/review/results/2026-06-09-plan-462-mapping-r3.md` |
| Plan review r3 — final readiness | `scripts/review/results/2026-06-09-plan-462-final-readiness-r3.md` |
| Plan review r4 — mapping | `scripts/review/results/2026-06-09-plan-462-mapping-r4.md` |
| Plan review r4 — final readiness | `scripts/review/results/2026-06-09-plan-462-final-readiness-r4.md` |

## Deliverable

The deliverable will define a source refresh acceptance contract that agents and humans can use to evaluate source readiness without running unbounded downloads. It will include a human-readable document, a JSON contract with required high-value data groups, a validator script, unit tests, and a skill update that routes agents to the contract.

## Plan

### Task 1 — Define the contract document

Create `docs/data/source-refresh-acceptance-criteria.md`.

The document will define:

- required fields per data group
- freshness status enum
- completeness status enum
- scorecard-to-contract mapping rules
- scheduler-backed source rule
- static/reference-data rule
- blocked-source rule
- distinction between source-data vintage and local refresh timestamp
- acceptance checklist for source summaries and downstream workflow readiness

The freshness enum will include `fresh`, `stale`, `missing`, `blocked`, `unknown`, `reference_data`, and `not_applicable`.

The completeness enum will include `full`, `sample`, `empty`, `missing`, `runtime_fetched`, `reference_data`, `blocked`, `unknown`, and `not_applicable`.

The contract will explicitly map current scorecard values into contract fields:

| Scorecard `freshness_status` | Scorecard `catalog_status` | Contract `freshness_status` | Contract `completeness_status` |
|---|---|---|---|
| `empty` | `empty` | `missing` | `empty` |
| `full` | `full` | `unknown` unless source vintage or scheduler success proves freshness | `full` |
| `missing` | `not_applicable` | `not_applicable` | `not_applicable` |
| `missing` | `runtime_fetched` | `missing` | `runtime_fetched` |
| `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` |
| `reference_data` | `reference_data` | `reference_data` | `reference_data` |
| `sample` | `sample` | `stale` unless a successful scheduler manifest proves freshness | `sample` |
| `unknown` | `unknown` | `unknown` | `unknown` |
| `fresh` | any allowed value | `fresh` only if scheduler/source proof also passes | mapped from `catalog_status` |
| `stale` | any allowed value | `stale` | mapped from `catalog_status` |

`completeness_status` will be deterministically mapped from scorecard `catalog_status`; it will not use "unchanged" fallback language. `freshness_status` will be deterministically mapped from scorecard `freshness_status` plus scheduler/source proof, with `catalog_status` used only to classify completeness and special `runtime_fetched` handling.

The implementation will include fixtures for each currently observed scorecard pair from `data/freshness-scorecard.json`: `empty|empty`, `full|full`, `missing|not_applicable`, `missing|runtime_fetched`, `not_applicable|not_applicable`, `reference_data|reference_data`, `sample|sample`, and `unknown|unknown`.

### Task 2 — Add the machine-readable contract

Create `data/source-refresh-acceptance-contract.json`.

The JSON will include:

- `schema_version`
- enum definitions
- required row fields
- high-value source rows for BSEE, EIA US, SODIR, UKCS, Brazil ANP, LNG terminals, metocean, HSE, marine safety, vessel fleet, vessel hull models, oil price, and wind
- scheduler job mapping for scheduler-backed sources
- blocker issue mappings where already known
- downstream consumer notes where known from issue context

Each source row will require these fields:

- `module_id`
- `materialized_module_id`
- `aliases`
- `display_name`
- `source_authority`
- `source_url_or_api`
- `source_data_latest_date`
- `source_data_latest_date_basis`
- `source_data_latest_date_unknown_reason`
- `last_successful_refresh`
- `last_successful_refresh_basis`
- `data_location`
- `external_data_root_required`
- `scheduler_job`
- `scheduler_output_dir`
- `refresh_command`
- `record_count`
- `artifact_count`
- `refresh_cadence`
- `freshness_grace_days`
- `freshness_status`
- `completeness_status`
- `credential_requirement`
- `blocker_issue`
- `downstream_consumers`

Unknown `source_data_latest_date` will be represented as JSON `null`, not an empty string, and must be paired with `source_data_latest_date_basis: "unknown"` plus a non-empty `source_data_latest_date_unknown_reason`. Allowed non-null source date basis values will be `dataset_field`, `source_api_metadata`, `source_publication_date`, and `source_version`. Prohibited source date basis values will include `metadata_refresh`, `newest_file_modified`, `scheduler_success`, `manifest_timestamp`, and `unknown` when the date is non-null. The contract will prohibit metadata refresh dates, file modification timestamps, or scheduler success timestamps from being copied into `source_data_latest_date` unless the implementation actually inspects a business/date field inside the dataset.

The EIA row will explicitly carry `module_id: "eia_us"`, `materialized_module_id: "eia"`, `aliases: ["eia"]`, `scheduler_job: "eia_us_refresh"`, `data_location: "data/modules/eia_us"`, and `scheduler_output_dir: "data/modules/eia"` so the existing scheduler output mismatch is visible instead of silently normalized away. Validator logic will require one of: existing `data_location`, `external_data_root_required: true`, or a declared `materialized_module_id`/`aliases` relationship whose scheduler output directory exists or is expected by scheduler config.

### Task 3 — Implement validator

Create `scripts/audit/validate_source_refresh_contract.py`.

The validator will:

- load `data/source-refresh-acceptance-contract.json`
- verify all required top-level keys exist
- verify every source row contains every field listed in `required_row_fields`
- verify freshness and completeness values belong to their declared enums
- verify the required high-value data groups are present
- verify scorecard-to-contract mapping is deterministic from scorecard `freshness_status` plus `catalog_status`, including `missing|runtime_fetched` and `missing|not_applicable`
- verify scheduler-backed sources name a job from `config/scheduler/scheduler_config.yml`
- verify scheduler-backed source `scheduler_output_dir` exactly matches the configured job `output_dir`
- verify scheduler-backed sources marked `fresh` have an existing `manifest.json` at the configured output directory, with `status: success`, parseable `last_success_ts`, and age within `freshness_grace_days`
- verify scheduler-backed sources with known blockers, missing manifests, failed manifests, or stale manifests are not marked `fresh`
- verify `source_data_latest_date` is either an ISO date/null and remains distinct from `last_successful_refresh`
- verify null `source_data_latest_date` rows carry `source_data_latest_date_basis: "unknown"` and an explicit unknown reason
- verify non-null `source_data_latest_date` rows use only allowed source-data basis values and reject prohibited basis values such as `metadata_refresh`, `newest_file_modified`, `scheduler_success`, and `manifest_timestamp`
- verify each source row has an existing `data_location`, `external_data_root_required: true`, or explicit `materialized_module_id`/`aliases` mapping
- verify every blocker issue value is either `none`, empty, or a GitHub issue URL / `#NNN` reference
- verify `.claude/skills/worldenergydata-source-readiness/SKILL.md` references the contract document

The validator will not download data or call external APIs.

### Task 4 — Add tests first, then implementation

Add `tests/unit/audit/test_source_refresh_contract.py`.

Tests will cover:

- valid minimal contract passes validation
- source row missing any required row field fails validation
- invalid freshness enum fails validation
- invalid completeness enum fails validation
- missing required high-value source fails validation
- scheduler-backed source with an unknown job fails validation
- scheduler-backed source with the wrong output directory fails validation
- scheduler-backed source marked `fresh` without a successful in-cadence manifest fails validation
- scorecard `freshness_status` plus `catalog_status` pairs `empty|empty`, `full|full`, `missing|not_applicable`, `missing|runtime_fetched`, `not_applicable|not_applicable`, `reference_data|reference_data`, `sample|sample`, and `unknown|unknown` map to contract freshness/completeness without leaking invalid values into the freshness enum
- source rows keep `source_data_latest_date` and `last_successful_refresh` as distinct fields
- null source-data latest dates require `source_data_latest_date_basis: "unknown"` and an unknown reason
- non-null source-data latest dates reject prohibited basis values from metadata/file/scheduler clocks
- EIA alias/materialization mapping validates `module_id: eia_us` to `materialized_module_id: eia`
- fixtures cover one source in each lane: fresh, stale, missing, blocked, sample, and reference/static
- skill file must reference the contract path

### Task 5 — Update source-readiness skill

Update `.claude/skills/worldenergydata-source-readiness/SKILL.md` and `references/readiness-fields.md` so agents:

- run the readiness summary for current evidence
- use the contract document for pass/fail acceptance decisions
- avoid treating metadata refresh dates as source-data vintage
- report data location and scheduler output location together when both exist

### Task 6 — Verify

Run focused verification:

```bash
set -euo pipefail
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/unit/audit/test_source_refresh_contract.py tests/unit/audit/test_data_freshness_scorecard.py -q
python scripts/audit/validate_source_refresh_contract.py
python .claude/skills/worldenergydata-source-readiness/scripts/source_readiness_summary.py --format json
```

Run the official workspace-hub legal/security scanner against the current worktree by passing a relative path from the workspace-hub checkout to this checkout:

```bash
set -euo pipefail
export WORKSPACE_HUB="${WORKSPACE_HUB:?set path to workspace-hub checkout}"
REL_FROM_HUB="$(python - <<'PY'
import os
from pathlib import Path
print(os.path.relpath(Path.cwd().resolve(), Path(os.environ["WORKSPACE_HUB"]).resolve()))
PY
)"
test -n "$REL_FROM_HUB"
test "$REL_FROM_HUB" != "."
(cd "$WORKSPACE_HUB" && bash scripts/legal/legal-sanity-scan.sh --repo="$REL_FROM_HUB" --diff-only)
```

Because `scripts/review/results/` is ignored by a broad `.gitignore` rule while historical review files are tracked, stage issue #462 review artifacts explicitly with `git add -f scripts/review/results/2026-06-09-plan-462-*.md`.

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `docs/data/source-refresh-acceptance-criteria.md` | Canonical human-readable source refresh contract |
| Create | `data/source-refresh-acceptance-contract.json` | Machine-readable contract used by validator and agents |
| Create | `scripts/audit/validate_source_refresh_contract.py` | No-download validator for enum, required source, scheduler mapping, and skill-reference checks |
| Create | `tests/unit/audit/test_source_refresh_contract.py` | TDD coverage for contract validation |
| Update | `.claude/skills/worldenergydata-source-readiness/SKILL.md` | Route agents from readiness summary to acceptance contract |
| Update | `.claude/skills/worldenergydata-source-readiness/references/readiness-fields.md` | Document contract-backed interpretation rules |
| Update | `docs/plans/README.md` | Index this plan |

## TDD Test List

| Test | What it verifies |
|---|---|
| `test_valid_minimal_contract_passes` | A valid fixture with required groups and enum values validates |
| `test_source_row_missing_required_field_fails` | Every row must contain every `required_row_fields` entry |
| `test_invalid_freshness_status_fails` | Unknown freshness values are rejected |
| `test_invalid_completeness_status_fails` | Unknown completeness values are rejected |
| `test_required_high_value_sources_present` | Required source rows cannot be omitted |
| `test_scheduler_source_requires_known_job` | Scheduler-backed rows must name a configured job |
| `test_scheduler_source_requires_exact_configured_output_dir` | Scheduler-backed rows must match the configured job output path exactly |
| `test_fresh_scheduler_source_requires_success_manifest` | Scheduler-backed sources cannot be marked fresh without an in-cadence success manifest |
| `test_observed_scorecard_pairs_map_to_contract_statuses` | Observed scorecard pairs, including `missing|runtime_fetched` and `missing|not_applicable`, map deterministically |
| `test_source_date_and_refresh_date_are_distinct_fields` | Contract rows must keep source data vintage separate from local refresh timestamp |
| `test_unknown_source_date_requires_basis_and_reason` | Null source-data latest dates require basis `unknown` and an explicit unknown reason |
| `test_non_null_source_date_rejects_metadata_file_scheduler_basis` | Metadata refresh, file mtime, and scheduler success bases cannot populate source-data vintage |
| `test_eia_us_alias_materialization_mapping_is_explicit` | EIA US row preserves `module_id` while declaring the existing `eia` materialization path |
| `test_contract_fixture_covers_required_lanes` | Fixtures cover fresh, stale, missing, blocked, sample, and reference/static lanes |
| `test_skill_references_contract` | Agent-facing skill routes to the canonical contract document |

## Acceptance Criteria

- [ ] `docs/data/source-refresh-acceptance-criteria.md` defines required fields, freshness enum, completeness enum, and pass/fail interpretation rules.
- [ ] `data/source-refresh-acceptance-contract.json` includes initial rows for BSEE, EIA US, SODIR, UKCS, Brazil ANP, LNG terminals, metocean, HSE, marine safety, vessel fleet, vessel hull models, oil price, and wind.
- [ ] Every source row contains every field listed in `required_row_fields`; the validator rejects missing row fields.
- [ ] Scheduler-backed rows include configured scheduler job names and output directories.
- [ ] Scheduler-backed row output directories exactly match scheduler config output directories, including the existing `eia_us_refresh` to `data/modules/eia` mapping.
- [ ] The contract distinguishes `source_data_latest_date` from `last_successful_refresh`.
- [ ] Unknown source-data latest dates use JSON `null` plus an explicit unknown reason.
- [ ] Null source-data latest dates require `source_data_latest_date_basis: "unknown"`; non-null source-data latest dates reject metadata/file/scheduler clock bases.
- [ ] Metadata refresh dates, file modification dates, and scheduler success dates are not allowed to populate `source_data_latest_date` unless a dataset business/date field is inspected.
- [ ] The validator rejects invalid enum values and missing required high-value sources.
- [ ] The validator rejects scheduler-backed rows that do not map to configured scheduler jobs.
- [ ] The validator rejects scheduler-backed rows marked `fresh` when the success manifest is missing, failed, stale, or unparseable.
- [ ] Observed scorecard pairs, including `missing|runtime_fetched` and `missing|not_applicable`, are explicitly mapped into contract freshness/completeness statuses.
- [ ] EIA US explicitly records `materialized_module_id: eia` or equivalent alias metadata so `eia_us_refresh` output drift is visible and validated.
- [ ] Tests cover fresh, stale, missing, blocked, sample, and reference/static lanes.
- [ ] The source-readiness skill references the contract and tells agents to use it for acceptance decisions.
- [ ] Focused tests pass.
- [ ] The legal/security diff scan passes.

## Risks and Open Questions

- **Risk:** Existing scorecard `freshness_status` values include `empty`, `sample`, and `full` for current pipeline behavior. Implementation will preserve compatibility through an explicit scorecard-to-contract mapping layer unless a separate reviewed issue changes the scorecard schema.
- **Risk:** Some high-value rows will initially have unknown source-data latest dates. Unknown is acceptable only as JSON `null` with `source_data_latest_date_basis: "unknown"` and a non-empty unknown reason; it must not be backfilled from metadata refresh timestamps.
- **Risk:** The contract could become a static checklist that drifts from scheduler config. The validator must read scheduler config at runtime to reduce this drift.
- **Risk:** The workspace-hub legal scanner cannot scan arbitrary worktrees by simple `--repo=worldenergydata` when this branch lives outside the workspace-hub root. Verification will use the relative-path command in Task 6 and must record the exact command in the PR body.
- **Open:** Should `data/source-refresh-acceptance-contract.json` become the future source of truth for `module-manifest.yaml` `catalog_status`, or should it remain a validation overlay until source-specific issues close?

## Adversarial Review Summary

Rounds 1, 2, and 3 returned MAJOR findings. Round 4 returned APPROVE from both reviewers after the mapping, artifact, and status fixes. This plan is ready for user approval only after the committed/pushed artifacts are posted to the issue.

| Reviewer | Verdict | Key findings addressed in this revision |
|---|---|---|
| Schema/contract r1 | MAJOR | Required row schema missing; scorecard enum compatibility underspecified; scheduler `fresh` not manifest-gated; source-data date semantics ambiguous; EIA identity/output drift not explicit; lane tests incomplete. |
| Repo integration/testability r1 | MAJOR | Verification command used missing `.venv`; workspace-hub legal scan command was not reproducible for this worktree; scheduler output exact-match validation missing; scorecard enum mapping underspecified. |
| Schema/contract r2 | MAJOR | Required row fields not validator-enforced; mapping not deterministic over scorecard `freshness_status` plus `catalog_status`; date-basis validation incomplete; EIA alias/materialization not contract-safe. |
| Repo integration/testability r2 | MAJOR | Legal scan snippet still lacked exported `WORKSPACE_HUB` and non-empty relative path validation; ignored review artifacts needed force-add handling; `runtime_fetched` needed explicit mapping test coverage. |
| Mapping r3 | MAJOR | Mapping still mishandled live `missing|runtime_fetched` rows. |
| Final-readiness r3 | MAJOR | Mapping needed total observed-pair coverage; r3 review artifacts and plan status needed reconciliation. |
| Mapping r4 | APPROVE | No findings; observed scorecard pairs and artifact hygiene verified. |
| Final-readiness r4 | APPROVE | No findings; plan/index/review artifacts and verification command shape verified. |

Implementation must not start until plan review is complete and the user applies `status:plan-approved`.
