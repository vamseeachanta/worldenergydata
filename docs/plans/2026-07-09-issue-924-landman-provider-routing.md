# Plan for [#924](https://github.com/vamseeachanta/worldenergydata/issues/924): make Landman provider routing executable and prove the CLI smoke path

> **Status:** plan-approved
> **Complexity:** T3
> **Date:** 2026-07-09
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/924
> **Client:** N/A
> **Lane:** lane:codex
> **Execution mode:** parallel-worktree after explicit user approval; TDD implementation will serialize shared entry-point edits
> **Review artifacts:** r1 usable `scripts/review/results/2026-07-09-plan-924-r1b-{claude,codex}.md` and unavailable `scripts/review/results/2026-07-09-plan-924-{claude,codex,gemini}.md` | r2 usable `scripts/review/results/2026-07-09-plan-924-r2b-codex.md` and unavailable `scripts/review/results/2026-07-09-plan-924-r2-unavailable-{claude,gemini}.md` | r3 main-session resolution `scripts/review/results/2026-07-09-plan-924-r3-main.md`

---

## Resource Intelligence Summary

### Existing repo code

- `packages/worldenergydata-landman/src/worldenergydata/landman/landman.py:16-18,73-80,237-325` aliases `exceptions.ProviderError` as `LandmanProviderError`, advertises `county_records`, maps `auto` to it unconditionally, imports a missing module, resolves one provider before a multi-operation request, and converts per-operation exceptions into result fields.
- `landman.py` accepts `ownership`, `leases`, `title`, `deeds`, `mortgages`, `assignments`, and `all`. The CLI accepts a subset and currently defaults `--type` to `all` while always calling `search_ownership()`.
- `providers/county_reference.py` is embedded office-reference data; `providers/blm.py` exposes mining/fluid-mineral methods; `providers/state_gis.py` exposes well/permit methods. None implements generic ownership/title operations.
- `exceptions.py` is the runtime hierarchy used by providers and package exports. `errors.py` is a distinct legacy public hierarchy with different constructors/factories. This issue will extend the runtime hierarchy and preserve the legacy module unchanged; it will not alias incompatible classes.
- `MineralOwnershipRecord` in `models.py` is a dataclass, not a validating parser. A dedicated fixture parser must coerce and validate input before constructing it.
- `src/worldenergydata/cli/commands/landman.py` eagerly renders Rich output, reports failed searches as exit 0, and counts `auto`/nonexistent providers as available. Root `cli/main.py` eagerly imports every command family; that cross-cutting startup defect is now isolated in [#926](https://github.com/vamseeachanta/worldenergydata/issues/926).
- The nearest registry precedent is `packages/worldenergydata-production/src/worldenergydata/production/unified/router.py`: one registry, canonical keys, and deterministic adapter resolution.

### Standards and policy

- TDD is mandatory: failing tests will precede every behavior change.
- The controlling coding rule limits touched files to 400 lines and functions to 50 lines. Current `landman.py` is 537 lines and CLI `landman.py` is 1,051 lines, so both will be split while preserving their import/command surfaces.
- Fixture input is untrusted local input: regular-file, root, size, schema, enum/date/numeric, duplicate-ID, and no-network checks will fail closed.
- Secrets, private/client data, live provider calls, and legal/title conclusions are prohibited. `scripts/legal/legal-sanity-scan.sh` must pass.

### Documents consulted

- [#924](https://github.com/vamseeachanta/worldenergydata/issues/924) requires pinned reproduction, operation-aware routing, an offline fixture CLI, structured unsupported behavior, truthful status, focused tests, and legal/security scans.
- Parent [#909](https://github.com/vamseeachanta/worldenergydata/issues/909) plus [#913](https://github.com/vamseeachanta/worldenergydata/issues/913), [#914](https://github.com/vamseeachanta/worldenergydata/issues/914), [#915](https://github.com/vamseeachanta/worldenergydata/issues/915), and [#925](https://github.com/vamseeachanta/worldenergydata/issues/925) reserve live BLM, county portal, state join, and acreage work.
- [#926](https://github.com/vamseeachanta/worldenergydata/issues/926) owns lazy root command-family dispatch and installed `worldenergydata <family>` startup performance. This issue will prove the independently executable Landman module CLI.
- `config/landman.yml`, `module-manifest.yaml`, `MODULE_INDEX.md`, `data/freshness-scorecard.json`, and `docs/CLI.md` disagree on readiness. The first two call capabilities stable/configured while freshness records zero datasets and the CLI has no executable provider.
- `packages/worldenergydata-landman/pyproject.toml` already packages nested JSON resources, so a bundled sample can work outside a source checkout without a packaging-rule change.
- Drive-index query `worldenergydata landman provider routing county records` returned only unrelated documents; `master_document_index` was unreachable and two indexes were stale.

### Gaps identified

- No executable generic ownership provider, capability/status registry, atomic multi-operation preflight, fixture schema/parser, packaged sample, secure file reader, module CLI test, or stable JSON envelope exists.
- Provider instances are cached by name only, which is unsafe for successive fixture sources.
- No test preserves both exception hierarchies while extending the runtime one.
- Both touched public entry-point modules exceed the active size rule and require focused extraction.

### Evidence (embedded verification)

**Pinned state** (verified 2026-07-09T22:56:22-05:00):

```text
branch: chore/plan-924-landman-provider-routing
HEAD:   0c5393b18590cf787b3eb020a7d418f3f36fb0f7
issue:  OPEN, status:needs-plan, lane:codex
```

**File/size state**:

```text
EXISTS: providers/{base,blm,state_gis,county_reference}.py
MISSING: providers/{registry,county_records}.py
MISSING: tests/unit/cli/test_landman_cli.py
EXISTS: scripts/legal/legal-sanity-scan.sh
MISSING: scripts/workflow/{completeness_score,render_completeness_html}.py
537  packages/worldenergydata-landman/src/worldenergydata/landman/landman.py
1051 src/worldenergydata/cli/commands/landman.py
```

The repository also lacks `gate:completeness` and `status:completeness-verified` labels. This general governance defect is promoted to [workspace-hub #3426](https://github.com/vamseeachanta/workspace-hub/issues/3426) rather than being hidden inside the Landman implementation.

**Runtime alias and missing route**:

```python
from .exceptions import ProviderError as LandmanProviderError
...
if provider_name == "auto":
    provider_name = self._select_best_provider(cfg)
from .providers.county_records import CountyRecordsProvider
...
return "county_records"
```

**Reproduction 1 - provider resolution** (2026-07-09T22:55:40-05:00, exit 1):

```text
county_records
ModuleNotFoundError: No module named 'worldenergydata.landman.providers.county_records'
AttributeError: type object 'ProviderError' has no attribute 'unavailable'
```

**Reproduction 2 - focused Typer search** (2026-07-09T22:56:22-05:00):

```text
args: search --state TX --county MIDLAND --format json
exit_code=0; provider="auto"; total_records=0
errors=["Search failed: type object 'ProviderError' has no attribute 'unavailable'"]
```

**Reproduction 3 - status/providers**:

```text
status: exit 0, "Providers Available", "5 providers"
providers: [county_records, drillinginfo, txdir, ogorgs, auto]
```

A reused unsynchronized environment first failed root CLI import on `worldenergydata.kansas_kgs`. `uv run --all-packages` then reported `Installed 233 packages`; this is an environment-sync count, not a count of workspace packages. A direct `importlib.metadata` probe found 234 installed distributions, 39 of which have `worldenergydata*` distribution names. `worldenergydata landman --help` still timed out after 600 seconds and a second run timed out after 120 seconds. A 60-second direct `import worldenergydata.cli.main` dump showed eager BSEE -> common -> Pydantic plugin metadata -> Pandas/NumPy imports before Landman dispatch. This cross-cutting defect is filed as [#926](https://github.com/vamseeachanta/worldenergydata/issues/926); it is not a hidden fallback in this plan.

After synchronization, `.venv/bin/python -m worldenergydata.cli.commands.landman --help` completed in 18 seconds with exit 0 but no help output because the module has no `__main__` invocation. `uv run --no-sync python -m ...landman --help` then completed in 26 seconds with exit 0. This proves the bounded module path bypasses the root blocker and identifies the missing module invocation that this plan will add.

**Drive index** (2026-07-10T03:54:33Z): exit 0, no relevant result; one unreachable and two stale indexes.

Failure mode matches the issue: **YES**. Cold NumPy/Pandas import latency was variable but is not the correction target.

---

## Operation and Provider Contracts

Atomic router operations will be exactly: `ownership`, `leases`, `title`, `deeds`, `mortgages`, `assignments`. `all` will expand in that order. Unknown/case-variant aliases will be rejected.

`Landman.router()` will resolve every requested atomic operation before executing any. One unsupported operation will raise one structured error listing all unsupported operations, and no provider will run. Successful multi-operation requests may resolve different providers and will record `provider_by_operation`.

| Name | Implementation status | Router operations | Mode / requirement |
|---|---|---|---|
| `county_records` | implemented | ownership | fixture-only; exactly one of bundled sample or records file |
| `county_reference` | reference-only | none (`county_info` outside router) | embedded reference |
| `blm` | configured-only | none | live mining/fluid methods reserved for #913 |
| `state_gis` | configured-only | none | live well/permit methods reserved for #915 |
| `drillinginfo`, `txdir`, `ogorgs` | unavailable | none | subscription/unimplemented |

`auto` is a route mode, not a provider. Registry rows will have unique names and integer priority; resolution order will be `(priority, name)`. Static counts will be total 7, implemented 1, reference-only 1, configured-only 2, unavailable 3. Runtime requirement satisfaction will be a separate field, not folded into implementation status.

The shared source contract will be `source={"sample": bool, "records_file": str | null}` in router config and equivalent keyword arguments on `search_ownership()`. CLI `--sample`/`--records-file` will build that object; exactly one will be required for fixture ownership. Registry requirement checks and provider construction will receive the same immutable source value, not separate unconnected arguments.

`providers` and `status` JSON rows will use exact keys `name`, `implementation_status`, `router_operations`, `mode`, `requirements`, `requirements_satisfied`, `routable_now`, and `sample_available`. Both commands will accept `--operation` (default `ownership`) plus the source flags for contextual readiness; zero source flags will report unmet fixture requirements and both source flags will be rejected. `requirements_satisfied` will be evaluated against that command context; without `--sample` or `--records-file`, `county_records` will be implemented but not routable. `routable_now` will be true only when the implementation exists, the requested operation is advertised, and every runtime requirement is satisfied. `sample_available=true` will describe packaging only and will never silently select the sample. `auto` will be emitted in a separate `route_modes` list and excluded from provider counts.

Fixture ownership search semantics will be stable and tested: `state` and `county` will be required and compared exactly after trimming, uppercasing, collapsing whitespace, and stripping one terminal ` COUNTY` from county values. Optional `owner_name` and `legal_description` filters will collapse whitespace, casefold, and use substring matching. All supplied predicates will combine with AND. Results will be ordered by `record_id`; a valid no-match query will return an `ok` envelope with an empty records list rather than an error.

---

## Fixture and Output Contracts

The bundled resource `worldenergydata.landman.fixtures/county_records_v1.json` and custom files will use this closed schema:

- Root keys exactly: `schema_version`, `dataset_id`, `mode`, `records`; version must be integer `1`, mode `fixture-only`.
- Maximum 1 MiB and 1,000 records; `record_id` values unique.
- Required record keys: `record_id`, `state`, `county`, `legal_description`, `owner_name`.
- Optional keys: `interest_type`, `mineral_interest_percent`, `net_mineral_acres`, `gross_acres`, `effective_date`, `source_document`, `grantor`, `recorded_date`, `book`, `page`, `volume`, `instrument_number`, `notes`.
- Unknown keys will fail. JSON `NaN`, `Infinity`, and `-Infinity` will be rejected through `json.loads(parse_constant=reject_constant)`. Dates will be ISO `YYYY-MM-DD`; `interest_type` will map to the existing enum; state/county/legal/owner and numeric bounds will use existing validators before dataclass construction. Numeric fields will reject booleans and non-finite values before conversion. Provider/retrieval fields will be set by the adapter, not accepted from JSON.

Custom `--records-file` input will be restricted to a direct-child `.json` basename in the current working directory. Separators, empty/`.`/`..` names, absolute paths, and nested paths will be rejected before I/O. The reader will open the current directory as a descriptor, then call `os.open(name, dir_fd=root_fd, O_RDONLY|O_NOFOLLOW|O_CLOEXEC)`; because subdirectories are forbidden, there is no attacker-controlled intermediate component. It will `fstat` that opened descriptor, require a regular file no larger than 1 MiB, and read at most limit+1 bytes from the same descriptor. Platforms without `dir_fd`, directory-descriptor, or `O_NOFOLLOW` support will reject custom files but retain `--sample`. Errors will expose a stable code and basename only, never file content/full path. The provider will be constructed per request and never cached, so successive sources cannot bleed state.

Exception compatibility will remain explicit: `worldenergydata.landman.exceptions.ProviderError` will retain identity with package export `LandmanProviderError` and gain the new factories/subclass; `worldenergydata.landman.errors.LandmanProviderError` will remain a distinct unchanged legacy class; `landman.LandmanValidationError` will keep its import and constructor surface. Existing constructor keywords, attributes, subclass relationships, factories, string/serialization behavior, and package exports will be regression-tested.

JSON mode will write one parseable object to stdout and diagnostics to stderr:

```json
{"status":"ok","requested_provider":"auto","resolved_provider":"county_records","operation":"ownership","source_mode":"sample","records":[],"failures":[]}
{"status":"error","requested_provider":"auto","resolved_provider":null,"failures":[{"operation":"title","code":"LANDMAN_CAPABILITY_UNAVAILABLE","candidate_statuses":[{"name":"county_records","reason":"operation_not_advertised"}],"message":"..."}]}
```

Single-operation failures will use the same `failures` list with one entry. Atomic multi-operation failure will list every unsupported operation in canonical order, keep `resolved_provider=null` unless one provider resolves the entire request, and execute no provider. A mixed-provider success will use `provider_by_operation`; it will not invent one singular resolved provider.

---

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-09-issue-924-landman-provider-routing.md` |
| Runtime routing | `packages/worldenergydata-landman/src/worldenergydata/landman/routing.py` and `providers/registry.py` |
| Fixture parser/provider/sample | `packages/worldenergydata-landman/src/worldenergydata/landman/fixture_schema.py`, `providers/county_records.py`, `fixtures/county_records_v1.json` |
| CLI split | `src/worldenergydata/cli/commands/landman.py`, `landman_search.py`, `landman_reference.py`, `landman_status.py`, `landman_render.py` |
| Tests | `tests/unit/landman/`, `tests/unit/cli/test_landman_cli.py`, `tests/integration/cli/test_landman_module_cli.py` |
| Reviews | `scripts/review/results/2026-07-09-plan-924-r1b-{claude,codex}.md`, `2026-07-09-plan-924-{claude,codex,gemini}.md`, `2026-07-09-plan-924-r2b-codex.md`, `2026-07-09-plan-924-r2-unavailable-{claude,gemini}.md`, and `2026-07-09-plan-924-r3-main.md` |
| Completeness | `docs/reports/<completion-date>-924-completeness.html` |

---

## Deliverable

Landman will provide operation-complete, fail-atomic routing; one packaged/custom fixture-only ownership provider; structured capability/schema/path errors; and truthful provider/status JSON. The installed module entry point `python -m worldenergydata.cli.commands.landman` will return synthetic ownership data with `--sample` and no network access, while every unsupported operation will exit 1 with a stable error envelope. Root-family dispatch remains explicit follow-on [#926](https://github.com/vamseeachanta/worldenergydata/issues/926).

---

## Pseudocode

```text
normalize_operations(values): expand all; reject aliases/unknown; preserve canonical order
preflight(operations, requested, source): resolve each by registry priority; collect all failures
    if failures: return requested_provider, resolved_provider=null, and ordered failures[]
        before constructing/running providers
    return provider registration per operation
router(cfg): normalize + preflight; instantiate providers per request; execute; record provider_by_operation

load_fixture(source): choose sample xor records_file
    for custom file, reject non-basename input; descriptor-open CWD then direct child with O_NOFOLLOW
    fstat regular/size and bounded-read the same descriptor; parse closed JSON schema
    reject JSON constants, bool numerics, non-finite values, duplicates, and unknowns
    coerce enum/dates; run existing value validators; build dataclasses
search_ownership(criteria): normalize exact state/county and substring owner/legal filters
    combine filters with AND; sort by record_id; set provider/retrieved_at; make no network call

cli search: default type=ownership (matching prior effective behavior); dispatch declared operation
    JSON success/error uses one envelope; all explicitly preflights all six and fails atomically today
cli status/providers: accept operation and source context; emit exact readiness row keys/counts;
    show auto in route_modes; never auto-select packaged sample
module main: invoke app when executed with python -m; do not import root cli.main

subprocess_no_network_smoke(): create a temporary sitecustomize.py that records loading and
    raises on socket.connect/create_connection; prepend it to PYTHONPATH; execute the installed
    module CLI with --sample; require marker, exit 0, parseable JSON, and no network-attempt record

installed_wheel_smoke(): build root worldenergydata, worldenergydata-core, and landman wheels;
    create a temporary --system-site-packages venv outside the checkout and install those three
    wheels with --no-deps; change CWD to an empty directory; invoke python -m
    worldenergydata.cli.commands.landman ... --sample and require packaged resource lookup
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `docs/plans/2026-07-09-issue-924-landman-provider-routing.md` | Reviewed plan artifact |
| Create | `packages/worldenergydata-landman/src/worldenergydata/landman/routing.py`, `packages/worldenergydata-landman/src/worldenergydata/landman/providers/registry.py` | Complete operation normalization, atomic preflight, deterministic registration |
| Create | `packages/worldenergydata-landman/src/worldenergydata/landman/fixture_schema.py`, `packages/worldenergydata-landman/src/worldenergydata/landman/providers/county_records.py`, `packages/worldenergydata-landman/src/worldenergydata/landman/fixtures/county_records_v1.json` | Secure validated packaged/custom fixture path |
| Modify | `packages/worldenergydata-landman/src/worldenergydata/landman/landman.py`, `packages/worldenergydata-landman/src/worldenergydata/landman/exceptions.py`, `packages/worldenergydata-landman/src/worldenergydata/landman/__init__.py`, `packages/worldenergydata-landman/src/worldenergydata/landman/providers/__init__.py` | Delegate routing, add runtime factories/capability errors, preserve exports; leave `errors.py` unchanged |
| Split | `src/worldenergydata/cli/commands/landman.py` into four named helper modules | Preserve `landman.app`, add module `__main__` invocation, and bring touched files/functions under limits |
| Modify/Create | `tests/unit/landman/*`, `tests/unit/cli/test_landman_cli.py`, `tests/integration/cli/test_landman_module_cli.py` | TDD for every contract and installed module dispatch without root imports |
| Modify | `config/landman.yml`, `docs/CLI.md`, `module-manifest.yaml`, `MODULE_INDEX.md` | Align fixture-only/status/operation claims |
| Update | `docs/plans/README.md` | Index T3 draft/review state |
| Create | `docs/reports/<completion-date>-924-completeness.html` | Required evidence before owner close verification |

Every expanded path above will be named explicitly in the implementation commit; no glob will be used for staging.

---

## TDD Test List

| Test | Contract |
|---|---|
| `test_operation_vocabulary_and_all_order` | exact six atomic values; all expansion; aliases rejected |
| `test_router_preflight_is_atomic` | mixed supported/unsupported request executes nothing and lists all gaps |
| `test_atomic_error_envelope_lists_every_operation` | requested provider retained, unresolved provider null, ordered `failures[]`, no singular-provider fiction |
| `test_auto_priority_is_deterministic_with_two_candidates` | `(priority,name)` order, existing factory only |
| `test_registry_status_schema_counts_and_context` | exact row keys/categories/counts; auto separate; operation/source-context requirements; sample availability is not selection |
| `test_packaged_sample_survives_installed_wheels_outside_checkout` | root/core/landman wheels in an external venv and blank CWD find and parse the resource |
| `test_fixture_schema_valid_and_closed` | required/optional fields, enum/date coercion, unknowns/version rejected |
| `test_fixture_limits_duplicates_and_numeric_bounds` | 1 MiB/1,000 rows, IDs, percentages/acres, booleans, NaN/infinities fail closed |
| `test_custom_file_is_direct_child_descriptor_opened_and_bounded` | separators/traversal/symlink/device/dir rejected; CWD and child opened by descriptor; same-fd fstat/read |
| `test_two_sequential_sources_do_not_share_provider_state` | no cache/source bleed |
| `test_fixture_search_filter_contract` | normalized exact state/county; owner/legal substring; AND composition; record-id order; empty success |
| `test_fixture_search_never_opens_network` | in-process socket/httpx fail hooks remain untouched |
| `test_module_subprocess_loads_no_network_sitecustomize` | external `python -m` smoke loads the guard, succeeds, and records no socket attempt |
| `test_runtime_and_legacy_exception_contracts` | public imports, constructors, factories, subclass/attributes remain compatible and distinct |
| `test_search_default_is_ownership_and_reports_resolved_provider` | prior effective default explicit; no `auto` provenance |
| `test_each_unsupported_operation_and_all_exit_one` | leases/title/deeds/mortgages/assignments/all structured errors |
| `test_json_stdout_is_single_parseable_success_or_error_envelope` | no Rich contamination; diagnostics on stderr |
| `test_cli_command_option_and_output_compatibility` | search, lookup, county-info, providers, status; current option names; help; table/json/csv/file modes survive split |
| `test_status_and_providers_json_contract` | source flags, exact row keys/categories/counts/readiness fields and route-mode separation |
| `test_module_cli_does_not_import_root_or_unrelated_families` | `python -m` path bypasses `cli.main`, BSEE, Pandas, and NumPy |
| `test_installed_module_sample_smoke` | wheel-installed external-venv `python -m ...landman search --sample` succeeds offline |
| `test_touched_python_files_and_functions_meet_limits` | all touched Python files <=400 lines and functions <=50 |

---

## Acceptance Criteria

- [ ] RED evidence will capture current provider exception, exit-0 error, inflated status, router partial-success, and focused-vs-root CLI behavior before implementation.
- [ ] `uv run --no-sync pytest tests/unit/landman tests/unit/cli/test_landman_cli.py tests/integration/cli/test_landman_module_cli.py -q` will pass after the workspace sync preflight.
- [ ] Default search will be explicitly `ownership`; all six atomic operations plus explicit `all` will follow the operation contract above.
- [ ] Multi-operation router requests will preflight atomically and will never return `completed` with per-operation error strings.
- [ ] Atomic failures will retain `requested_provider`, use nullable `resolved_provider`, list every operation failure in canonical order, and execute no provider; mixed-provider success will use `provider_by_operation`.
- [ ] `uv run --no-sync python -m worldenergydata.cli.commands.landman search --state TX --county MIDLAND --type ownership --sample --format json` will exit 0 with one parseable JSON envelope, synthetic record(s), `requested_provider=auto`, `resolved_provider=county_records`, and zero network calls.
- [ ] State/county filters will use normalized exact matching; owner/legal filters will use normalized case-insensitive substring matching; predicates will combine with AND, results will sort by record ID, and a valid no-match query will return an empty success.
- [ ] Custom records files will be direct-child basenames opened relative to an already-open CWD descriptor with `O_NOFOLLOW`, then fstat/read from the same descriptor. The parser will reject JSON constants, booleans in numeric fields, and non-finite values; sequential files will not share provider state.
- [ ] Unsupported operations will exit 1 with `LANDMAN_CAPABILITY_UNAVAILABLE`; JSON stdout will remain parseable and contain no full local path/content.
- [ ] Provider/status output will match the exact row-key/table/count contract, evaluate requirements against explicit source flags, report sample availability without selecting it, and will not call `auto`, configured-only, reference-only, or unavailable sources executable.
- [ ] Search, lookup, county-info, providers, and status names, existing options, help output, and table/JSON/CSV/output-file modes will remain registered after the CLI split.
- [ ] A subprocess smoke will load a temporary `sitecustomize` socket guard through `PYTHONPATH`, prove the guard marker is active, and complete the sample query without a recorded network attempt.
- [ ] Root `worldenergydata`, `worldenergydata-core`, and `worldenergydata-landman` wheels will be installed with `--no-deps` into a temporary external `--system-site-packages` venv; from an empty CWD outside the checkout, the installed module sample query will succeed and prove packaged fixture lookup.
- [ ] Both exception modules' existing tests/imports/constructors will pass; only the runtime hierarchy will gain new capability behavior.
- [ ] Every touched Python file will be <=400 lines and every touched function <=50 lines; existing oversized untouched model/validator/legacy-error files are outside this issue.
- [ ] `docs/CLI.md`, config, manifest, index, and CLI JSON will agree on fixture-only readiness and operation coverage.
- [ ] `bash scripts/legal/legal-sanity-scan.sh`, the focused issue tests, and all pre-existing Landman package tests will pass; unrelated repo-wide failures, if any, will be reported rather than hidden.
- [ ] Implementation will remain blocked until the user applies `status:plan-approved`; the agent will never self-approve.
- [ ] Final review will route to Claude, Codex, and Gemini by default, record unavailable providers explicitly, and require at least two usable reviews with no MAJOR finding.
- [ ] Closeout will remain blocked on [workspace-hub #3426](https://github.com/vamseeachanta/workspace-hub/issues/3426), because this repo currently lacks the scorer, renderer, workflow, and completeness labels. Once that issue lands, #924 will derive the non-selectable code class from its changed paths, use a HEAD-bound `worldenergydata` package/test snapshot plus changed-code coverage and evidence-linked acceptance checks, persist the issue-bound record, render `docs/reports/<completion-date>-924-completeness.html`, and stop for owner-applied `status:completeness-verified`. If #3426 changes that contract materially, this plan will be revised and re-reviewed before closeout.

---

## Adversarial Review Summary

| Provider | Verdict | Key findings |
|---|---|---|
| Claude | MAJOR (fallback r1) | Root CLI assumption, default-all behavior, packaged fixture, source plumbing, priority, and evidence gaps |
| Codex | MAJOR (fallback r2) | Define filtering, atomic envelopes, descriptor-safe custom paths, strict numerics, subprocess network proof, CLI compatibility, readiness schema, and installed-wheel proof |
| Claude | UNAVAILABLE (r2) | Tool-enabled fallback timed out without a usable review artifact |
| Gemini | UNAVAILABLE (r1/r2) | No noninteractive Gemini credential; no review signal |
| Main session | RESOLVED (r3) | Patched every r2 finding inline under the required r3 loop-break rule; no additional provider dispatch was performed |

**Overall result:** r2 returned MAJOR and blocked advancement. The r3 main-session resolution will record each finding against revised text and local checks. The issue may move to `status:plan-review` only after the plan, review artifacts, and index are committed/pushed and a label-time evidence comment exists. Implementation will remain blocked pending explicit user approval.

R3 resolutions: exact normalized search filters; plural fail-atomic error envelope; direct-child descriptor-relative file policy; JSON constant/bool/non-finite rejection; active `sitecustomize` subprocess network guard; full CLI command/option/output compatibility inventory; source-context runtime-readiness schema; external root/core/landman wheel smoke; corrected environment-count evidence; revision-stamped review paths; and explicit closeout dependency [workspace-hub #3426](https://github.com/vamseeachanta/workspace-hub/issues/3426).

---

## Risks and Non-Goals

- Root CLI eagerly imports every command family and is empirically unusable within bounded startup time. [#926](https://github.com/vamseeachanta/worldenergydata/issues/926) owns that defect; this issue will neither claim nor test root-family dispatch.
- The default flag changes from declared `all` to `ownership`, matching actual prior dispatch but changing help text. Docs/tests will call this out.
- Secure custom-file reading is OS-sensitive. Unsupported descriptor-relative or `O_NOFOLLOW` platforms will fail closed for custom files while bundled sample remains usable.
- CLI splitting can drift command registration. Focused command/option/help/output-mode tests will preserve the Landman module surface; root-family startup remains [#926](https://github.com/vamseeachanta/worldenergydata/issues/926).
- This repo does not yet carry the mandatory completeness machinery. [workspace-hub #3426](https://github.com/vamseeachanta/workspace-hub/issues/3426) will block #924 closeout, but not its user-approved TDD implementation.
- Live BLM/MLRS acquisition ([#913](https://github.com/vamseeachanta/worldenergydata/issues/913)), county portals ([#914](https://github.com/vamseeachanta/worldenergydata/issues/914)), state joins ([#915](https://github.com/vamseeachanta/worldenergydata/issues/915)), and acreage reporting ([#925](https://github.com/vamseeachanta/worldenergydata/issues/925)) are non-goals.

---

## Complexity: T3

**T3** - this is a public router/CLI contract correction with secure input, packaged data, compatibility surfaces, atomic multi-operation behavior, root integration tests, and required decomposition of two oversized touched modules.
