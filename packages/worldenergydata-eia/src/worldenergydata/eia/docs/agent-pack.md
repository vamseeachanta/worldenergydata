# EIA module knowledge pack

| Header | Value |
| --- | --- |
| Module | `eia` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-eia/src/worldenergydata/eia` |
| Pack revision | 1, 2026-10-16 |
| Code revision | `bb9239b5160221ba2ade16214816abacd86b7639` |
| Analysis family | EC; data pipeline, assessed with AQG r0 Python calculations |
| Quality role | Calculations quality manager; deputy: calculations deputy quality manager |
| Status | DRAFT; independent-provider acceptance pending |

## 1. Purpose and scope

The package fetches weekly petroleum and gas-storage records from EIA API v2, appends JSONL, and retains a per-feed latest-period watermark. [packages/worldenergydata-eia/src/worldenergydata/eia/__init__.py:L1-L16] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L184-L252]

Domestic production analytics belong to the separate `eia_us` package; the scope here includes all four Python files under the header path and the CLI and scheduler interfaces that call them. [packages/worldenergydata-eia/src/worldenergydata/eia/__init__.py:L12-L16] [src/worldenergydata/cli/commands/eia.py:L74-L107] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L50-L61]

Package metadata declares development status Alpha; this is metadata rather than evidence of live-data qualification. [packages/worldenergydata-eia/pyproject.toml:L15-L23]

Open qualification items are tracked in section 10 by #266, #431 or a numbered draft in [ISSUES_DRAFT.md](ISSUES_DRAFT.md). Pending drafts are filing requests, not issued issue numbers; the maintainers file them and replace the linked pending references.

### Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-16 | Initial pack records weekly feed contracts, mocked regression evidence and qualification gaps. |
| 1 | 2026-10-16 | Link numbered issue drafts, record the offset-step risk and sweep count, and distinguish explicit decoding and total-type failures from silent loss. |

## 2. Inputs and outputs

### Inputs

| Input | Unit, range and convention | Default and source | Evidence |
| --- | --- | --- | --- |
| `api_key` | Opaque nonempty string; authentication is presence-checked | Explicit argument, then `EIA_API_KEY`; absent raises `EIAKeyError` | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L61-L75] |
| `base_url`, `timeout` | URL; timeout in seconds; no numeric range validation | EIA v2 base, 30 s | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L22-L31] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L61-L75] |
| HTTP parameters | Weekly frequency, ascending `period`, 5000 records/page, initial offset 0 records | `_get`; optional `start` forwarded unchanged | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L142-L181] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L204-L208] |
| Response `value`, `units` | `value` converted with Python `float`; unit text retained, never converted; missing/invalid numeric value becomes `None` | JSON `response.data`; missing data defaults to empty list | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L96-L119] |
| `period`, watermark | Expected ISO date string; comparisons are lexical, with no calendar validation | Missing feed watermark is `None` | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L63-L83] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L146-L180] |
| Output/state directories | Filesystem destinations; no spatial frame, origin, phase or sign transformation in the record-copy route | Output `data/eia`; state defaults to output | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L106-L115] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L106-L118] |

### Outputs

| Output | Unit and format | Default/schema | Evidence |
| --- | --- | --- | --- |
| Petroleum/gas records | Original fields and unit strings plus float-or-`None` value and `_feed` | Feed IDs `petroleum_weekly`, `gas_storage_weekly` | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L106-L118] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L208-L235] |
| JSONL | UTF-8, one JSON object per line; append mode; arbitrary unsupported objects become strings | `eia_petroleum_weekly.jsonl`, `eia_gas_storage_weekly.jsonl`; `_schema_version` is string `1` | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L24-L32] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L129-L140] |
| State | UTF-8 JSON feed-to-period mapping; overwritten on save | `eia_ingestion_state.json` | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L32-L32] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L48-L83] |
| Sync result | `records_written` in records, `latest_period` as date string or `None`, `feed` as identifier | One dictionary per feed; `run_all` returns petroleum then gas | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L213-L263] |
| Runner status | Integer exit code, dimensionless | 0 success, 1 missing configuration, 2 import/sync failure | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L45-L82] |

## 3. Method and governing standards

| Method family | Implementation and limits | Reference |
| --- | --- | --- |
| HTTP pagination | `_get` increments offset by 5000 and stops when offset reaches `total` or a page is empty; HTTP errors raise without retry | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L142-L184] |
| Response normalization | `parse_response` copies each record and applies `float` only to `value`; no unit conversion, locale parser or finite-value check | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L106-L119] |
| Incremental selection | `_filter_new_records` retains string periods greater than the saved watermark; `_latest_period` takes maximum string | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L160-L180] |
| Persistence | `write_jsonl` appends before each runner saves its latest period; file append and state update are separate operations | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L129-L140] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L198-L206] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L233-L241] |

No governing engineering standard, standards-derived equation or `Citation` sidecar is identified in these four source files; the inspected methods implement transport, conversion and persistence. [packages/worldenergydata-eia/src/worldenergydata/eia/__init__.py:L1-L28] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L96-L184] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L146-L263] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L45-L86]

UNVERIFIED: current live endpoint/schema compatibility and source-data freshness are not established by the mocked examples; tracked by #266. [tests/unit/eia/test_client.py:L1-L5]

## 4. Validated worked examples

Validated examples: **0**; the cases below are regression examples using synthetic mocked responses or local state, with no independently sourced production benchmark. [tests/unit/eia/test_client.py:L42-L135] [tests/unit/eia/test_client.py:L368-L372]

| Case | Source and input | Expected value, unit and tolerance | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 gas conversion | Pinned synthetic test fixture; no external input file | Two records; first value 3100.0 Bcf; exact equality (0.0 Bcf tolerance) [tests/unit/eia/test_client.py:L220-L228] | `tests/unit/eia/test_client.py::TestEIAFeedClientParsing::test_parse_gas_storage_response` | PASS at BASE and after |
| R2 empty response | Pinned synthetic test fixture; no external input file | 0 records; exact count [tests/unit/eia/test_client.py:L230-L236] | `tests/unit/eia/test_client.py::TestEIAFeedClientParsing::test_parse_empty_response_returns_empty_list` | PASS at BASE and after |
| R3 JSONL schema | Pinned synthetic test fixture; no external input file | 1 JSON object contains the schema constant; exact string equality [tests/unit/eia/test_client.py:L431-L445] | `tests/unit/eia/test_client.py::TestEIAIngestionSyncJsonl::test_write_jsonl_adds_schema_version` | PASS at BASE and after |
| R4 watermark selection | Pinned synthetic test fixture; no external input file | 3 input records minus 2 at/before watermark = 1 written record; exact count [tests/unit/eia/test_client.py:L588-L611] | `tests/unit/eia/test_client.py::TestEIAIngestionSyncIncremental::test_sync_skips_records_on_or_before_last_fetch` | PASS at BASE and after |
| R5 state round trip | Pinned synthetic test fixture; no external input file | Saved and loaded date strings equal; 0 differing characters [tests/unit/eia/test_client.py:L368-L372] | `tests/unit/eia/test_client.py::TestEIAIngestionState::test_state_load_returns_saved_date` | PASS at BASE and after |

UNVERIFIED: fidelity to current source-published values is not established; a revisioned independent benchmark is required before any regression example can be promoted to validated; [issue pending (5)](ISSUES_DRAFT.md#draft-5).

## 5. QA gates

AQG r0, section 10, Python calculations supplies G0, G1 and G2; section 9 supplies G5. G3 is NOT_APPLICABLE because these methods ingest records rather than integrate dynamics; G4 is NOT_APPLICABLE because no diffraction mesh or hydrostatic solver is used. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L142-L184] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L184-L263]

All criteria below are proposed acceptance checks; a passing fixture check establishes only the named fixture behavior. S35 has no multi-page completeness detection check; the required regression is specified in [issue pending (1)](ISSUES_DRAFT.md#draft-1). `T` in commands denotes `tests/unit/eia/test_client.py`.

| Check | Gate | Executable check and numeric pass criterion | Evidence |
| --- | --- | --- | --- |
| C01 | G0 | `tests/unit/eia/test_client.py::TestEIAFeedClientInit::test_client_raises_when_no_api_key`: exactly 1 `EIAKeyError` exception for absent authentication | [tests/unit/eia/test_client.py:L154-L159] |
| C02 | G0 | `tests/unit/eia/test_client.py::TestEIAFeedClientParsing::test_parse_petroleum_response_returns_list`: exactly 3 records | [tests/unit/eia/test_client.py:L195-L202] |
| C03 | G0 | `tests/unit/eia/test_client.py::TestEIAFeedClientParsing::test_parse_petroleum_value_is_float`: exactly 3 float values, 0 non-float values | [tests/unit/eia/test_client.py:L212-L218] |
| C04 | G0 | R3: exactly 1 schema field per output object; 0 differing characters against `JSONL_SCHEMA_VERSION` | [tests/unit/eia/test_client.py:L431-L445] |
| C05 | G1 | Import through the complete `tests/unit/eia` suite: 0 failed tests and 0 collection errors | [tests/unit/eia/test_client.py:L16-L26] |
| C06 | G1 | Run all five scheduler-adapter tests; 0 failed tests; adapter success fixture returns 15 updated records | [tests/unit/scheduler/test_eia_adapter.py:L17-L47] [tests/unit/scheduler/test_eia_adapter.py:L49-L146] |
| C07 | G2 | R1: first gas value equals the fixture decimal 3100.0 Bcf, absolute difference 0.0 Bcf; 2 output records | [tests/unit/eia/test_client.py:L220-L228] |
| C08 | G2 | R4: hand count of periods strictly greater than the watermark gives 3 - 2 = 1 record; output count differs by 0 records | [tests/unit/eia/test_client.py:L588-L611] |
| C09 | G5 | R5: state readback differs from saved period by 0 characters | [tests/unit/eia/test_client.py:L368-L372] |
| C10 | G5 | `tests/unit/eia/test_client.py::TestEIAIngestionSyncJsonl::test_write_jsonl_one_record_per_line`: 2 inputs produce exactly 2 JSONL lines | [tests/unit/eia/test_client.py:L416-L429] |
| C11 | G5 | Resolve every pack citation at the code pin; exactly 0 missing paths or out-of-range citations; read ten supporting ranges; exactly 0 mismatches | Pack self-check record retained separately; proposed check, no production QA appendix generator |
| C12 | G0 | `tests/unit/eia/test_client.py::TestEIAIngestionState::test_state_missing_feed_returns_none`: exactly 1 missing-feed lookup returns `None` | [tests/unit/eia/test_client.py:L374-L376] |
| C13 | G1 | `tests/unit/eia/test_client.py::TestEIAFeedClientFetch::test_fetch_raises_on_http_error` and `test_fetch_raises_on_rate_limit`: 2 HTTP status cases, 2 expected exceptions, 0 missing exceptions | [tests/unit/eia/test_client.py:L289-L305] |

G2 is a hand check of record selection and literal numeric conversion, not an independent source-data validation. G5 checks output/schema/state traceability; they do not constitute a signed production QA appendix; [issue pending (5)](ISSUES_DRAFT.md#draft-5). [tests/unit/eia/test_client.py:L220-L228] [tests/unit/eia/test_client.py:L588-L611]

## 6. Known failure modes and pitfalls

The table records silent-failure risks first, then explicit errors and benign defaults reviewed by the same sweep. A missing detection check is stated literally; no passing fixture is treated as evidence for an untested error path.

| ID | Symptom and cause at the pin | Existing detection check or gap | Tracking |
| --- | --- | --- | --- |
| S01 | Missing `response` or `data` becomes an empty successful result; an API error envelope can resemble no data. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L106-L106] | no detection check exists | [issue pending (1)](ISSUES_DRAFT.md#draft-1) |
| S02 | Missing or null `value` becomes `None`; missing and source-null are indistinguishable. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L110-L117] | Null fixture exists; no detection check exists for missing fields | [issue pending (2)](ISSUES_DRAFT.md#draft-2) |
| S03 | `float` converts external text; thousands commas or decimal commas raise and silently become `None`. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L114-L117] | no detection check exists | [issue pending (2)](ISSUES_DRAFT.md#draft-2) |
| S04 | Nonfinite numeric text can pass `float`; no finite-value constraint is applied. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L114-L118] | no detection check exists | [issue pending (2)](ISSUES_DRAFT.md#draft-2) |
| S05 | Missing `total` defaults to 0 records and silently terminates pagination after one page; a string `total` compared with the integer offset at line 181 raises `TypeError`, an explicit failure. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L179-L182] | no detection check exists | [issue pending (1)](ISSUES_DRAFT.md#draft-1) |
| S06 | Empty page ends pagination even when a declared total remains outstanding. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L175-L182] | C02 covers one populated page only; no detection check exists | [issue pending (1)](ISSUES_DRAFT.md#draft-1) |
| S07 | Corrupt or unreadable state is warned about and replaced by an empty mapping; a retry can append old history again. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L54-L61] | C09 covers valid state only; no detection check exists | [issue pending (3)](ISSUES_DRAFT.md#draft-3) |
| S08 | Without a truthy watermark all records pass through without validating period presence or type. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L160-L161] | no detection check exists | [issue pending (3)](ISSUES_DRAFT.md#draft-3) |
| S09 | With a watermark, missing or non-string period records are silently omitted. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L163-L167] | no detection check exists | [issue pending (3)](ISSUES_DRAFT.md#draft-3) |
| S10 | Equal/older dates are discarded, including later corrections or additional series arriving for a completed date. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L163-L167] | C08 detects intended exclusion, not correction loss; no detection check exists for corrections | #431 |
| S11 | Maximum-period selection drops non-string periods and returns `None` if none remain; written records can then lack a saved watermark. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L179-L180] | no detection check exists | [issue pending (3)](ISSUES_DRAFT.md#draft-3) |
| S12 | Lexical ordering assumes normalized ISO dates; malformed string dates can advance a watermark incorrectly. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L163-L180] | no detection check exists | #431 |
| S13 | Unsupported JSON values are silently stringified by `default=str`; schema types are not enforced. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L136-L140] | C10 checks line count only; no detection check exists | [issue pending (2)](ISSUES_DRAFT.md#draft-2) |
| S14 | Append and watermark save are not transactional; interruption or concurrent runs can duplicate output or race. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L198-L206] | C09 covers successful persistence only; no detection check exists | [issue pending (3)](ISSUES_DRAFT.md#draft-3) |
| S15 | Gas append and watermark save have the same interruption window. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L233-L241] | no detection check exists | [issue pending (3)](ISSUES_DRAFT.md#draft-3) |
| S16 | Unit text is retained without verification or conversion; response values can be combined in incompatible units by consumers. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L106-L118] | C07 asserts one fixture unit only; no detection check exists for incompatible units | [issue pending (2)](ISSUES_DRAFT.md#draft-2) |
| S17 | Empty JSONL write returns without creating output; no empty cache is written on this branch. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L129-L130] | no detection check exists | [issue pending (4)](ISSUES_DRAFT.md#draft-4) |
| S18 | Unknown feed name falls back to a generated filename instead of rejection. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L133-L134] | no detection check exists | [issue pending (4)](ISSUES_DRAFT.md#draft-4) |
| S19 | Unknown feed state returns `None`, a deliberate initial-history default. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L63-L72] | C12 | covered default |
| S20 | Initial empty state mapping is normal before load; malformed JSON object shape is not validated. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L48-L61] | C09 covers valid object only; no detection check exists for wrong shape | [issue pending (3)](ISSUES_DRAFT.md#draft-3) |
| S21 | Offset begins at 0 records in both params and loop variable; normal pagination initialization. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L142-L156] | C02 checks first-page record count only; no detection check exists for multi-page completeness | [issue pending (1)](ISSUES_DRAFT.md#draft-1) |
| S22 | Petroleum missing watermark forwards `None`; empty new-record result reports 0 and leaves state unchanged. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L198-L217] | no detection check exists for an empty sync | [issue pending (4)](ISSUES_DRAFT.md#draft-4) |
| S23 | Gas missing watermark forwards `None`; empty new-record result reports 0 and leaves state unchanged. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L233-L252] | no detection check exists for an empty sync | [issue pending (4)](ISSUES_DRAFT.md#draft-4) |
| S24 | Runner displays absent latest period as `N/A` and can return success with no fresh data. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L74-L82] | no detection check exists | #266 |
| S25 | Runner import exception is logged and returns code 2; explicit failure, not swallowed success. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L55-L60] | no detection check exists | [issue pending (4)](ISSUES_DRAFT.md#draft-4) |
| S26 | Runner configuration exception is logged and returns code 1. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L62-L66] | C01 tests client exception, not runner exit; no detection check exists | [issue pending (4)](ISSUES_DRAFT.md#draft-4) |
| S27 | Runner broad exception is logged with traceback and returns code 2; first feed can already have written before the second fails. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L68-L72] | no detection check exists | [issue pending (4)](ISSUES_DRAFT.md#draft-4) |
| S28 | Network exceptions are re-raised as `EIAFeedError`; HTTP 429/non-200 responses raise immediately without retry. `response.json()` at line 175 is outside the request `try` at lines 162–165: a non-JSON 200 body raises a decode error rather than `EIAFeedError`; it propagates to the runner, CLI and scheduler adapter, which catch `Exception`. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L162-L175] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L68-L72] [src/worldenergydata/cli/commands/eia.py:L108-L114] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L77-L85] | C13 covers rate-limit and HTTP errors; no detection check exists for network exception text or a non-JSON 200 body | #431 |
| S29 | Timeout defaults to 30 s without range checks; weekly frequency is fixed; no runtime schema qualification. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L61-L75] | C01 addresses authentication only; no detection check exists for timeout ranges | [issue pending (1)](ISSUES_DRAFT.md#draft-1) |
| S30 | Authentication falls back from a false explicit value to environment; query parameters contain the key. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L67-L75] | C01 detects absence; query-param fixture confirms current behavior; no detection check exists for log disclosure | #431 |
| S31 | `run_all` initializes an empty results list, then runs feeds sequentially; second-feed failure prevents a combined return. [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L254-L263] | C05 covers success only; no detection check exists for partial-feed failure | [issue pending (4)](ISSUES_DRAFT.md#draft-4) |
| S35 | `_get` advances `offset` by `DEFAULT_PAGE_SIZE` (5000 records), not `len(page_records)`. A short non-final page or a caller-supplied `length` below 5000 silently drops intervening records; a larger `length` can repeat records. Inspected lines 142–182 include the `extra_params` override at 152–153 and offset step at 180; package callers currently pass only `start`, so the override path is latent. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L142-L182] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L204-L208] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L228-L232] | no detection check exists | [issue pending (1)](ISSUES_DRAFT.md#draft-1) |

### Downstream interfaces and example handling

| ID | Symptom and cause at the pin | Existing detection check or gap | Tracking |
| --- | --- | --- | --- |
| S32 | Downstream Parquet conversion failures are warnings; ingestion can still return scheduler success. [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L60-L75] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L99-L111] | C06 covers a successful snapshot; no detection check exists for conversion failure | #266 |
| S33 | Downstream refresh-metadata write errors are warned about and not propagated; success can lack fresh metadata. [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/base.py:L105-L130] | no detection check exists | #266 |
| S34 | The quickstart example can disclose configured authentication material in output; it was inspected, not executed. [notebooks/quickstart_eia.py:L23-L32] | no detection check exists | [issue pending (10)](ISSUES_DRAFT.md#draft-10) |

Observation date for all rows: 2026-10-16; source revision is the header code pin. Interface/example rows S32–S34 come from the cited interface reads; the three package greps below account for the 32 package rows.

Additional issue evidence: #431 names retry, query-key and lexical-date weaknesses; at this pin absent `total` causes early termination, so the issue's historical absent-total looping description is not adopted. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L167-L182]

The operational issue #266 requires a real successful materialization; C01 detects missing authentication, while C06 uses a mocked sync and does not establish live readiness. [tests/unit/eia/test_client.py:L154-L159] [tests/unit/scheduler/test_eia_adapter.py:L17-L47]

### Reproducible silent-failure sweep

sweep: 35 found (32 package rows, 3 interface/example rows)

```bash
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|0\.05|float\(|int\(|units|default=str|\.get\(|if .*records|else None' packages/worldenergydata-eia/src/worldenergydata/eia --glob '*.py'
rg -n 'except|continue|return|default|units|period|cache|write|0\.0|1970|0\.05' packages/worldenergydata-eia/src/worldenergydata/eia --glob '*.py'
rg -n 'except|continue|\breturn\b *(None)?$|\[\]|\{\}|\b0(\.0)?\b|1970|%[^sd]|percent|\bint\(|\bfloat\(|units|timeout|DEFAULT_|length|offset|write|open\(|or None|else None|if not ' packages/worldenergydata-eia/src/worldenergydata/eia --glob '*.py'
```

Sweep classification: 27 narrow-search matching lines, 59 broad-search matching lines and 60 offset/default-search matching lines, reviewed into 32 package rows (S01–S31 and S35), with 3 additional interface/example rows (S32–S34); matching lines overlap and are not finding counts; all 6 exception handlers reviewed, 1 external-text `float` conversion, 0 external-text `int` conversions, 0 `continue` statements, 0 literal `return None`, 0 literal empty-list/dict returns, 0 epoch-year or percentage fallback constants. Empty-result and implicit-`None` branches, initial zero offsets, unit assumptions and state writes are covered above. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L106-L184] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L48-L83] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L119-L263] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L55-L82]

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-16 | Pack revision 0 | A fixture-only pass does not establish completeness or correction handling | [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L163-L180] [tests/unit/eia/test_client.py:L588-L611] | Risks S09–S12 distinguish intended filtering from untested loss | Not created; [issue pending (5)](ISSUES_DRAFT.md#draft-5) |

## 8. Ownership

Review assignment: calculations quality manager on a provider different from the producer; deputy assignment: calculations deputy quality manager. Proposed tolerance changes, ambiguous inputs and checks that cannot pass are referred to that quality role; cross-family priority decisions go to the maintainers. Reference: *Module agent lifecycle and module knowledge pack*, revision 0, sections 3–4; *AQG r0*, section 11.

## 9. Dependencies and implementation inventory

| Direction | Dependency/interface | Evidence |
| --- | --- | --- |
| Upstream | `requests` and `worldenergydata-core` are declared dependencies; the client imports `requests` | [packages/worldenergydata-eia/pyproject.toml:L29-L32] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L14-L18] |
| Upstream | Weekly endpoint paths `petroleum/sum/snd/w`, `natural-gas/stor/sum/dcu/nus/w`; record keys `period`, `value`, `units` | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L22-L31] [tests/unit/eia/test_client.py:L49-L76] [tests/unit/eia/test_client.py:L94-L118] |
| Downstream | CLI `sync` delegates to `EIAIngestionSync` | [src/worldenergydata/cli/commands/eia.py:L74-L107] |
| Downstream | Scheduler adapter delegates ingestion, converts JSONL to Parquet and writes refresh metadata | [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L50-L85] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L88-L111] |
| Launcher | Shell entry point invokes `worldenergydata.eia.ingestion_runner`; runner calls `run_all` | [scripts/eia_weekly_sync.sh:L48-L66] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L62-L72] |

### Map inventory and counted-family result

Map source: `digitalmodel`, `docs/registry/implementation-map.yaml`, branch `codex/implmap-work`; observed map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; declared data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`. This external map reference is separate from the owning code pin.

Inventory criterion: implementation-row `path` starts with the header package path plus `/`. Observed result: **0 in-package rows, 0 module map families, empty implementation inventory** among 13 map families. Counted-family ranking: empty. Counted-family grep: **NOT_APPLICABLE**, because no map family has an implementation row in this package. A8 inventory passes with the empty set; no assertion of completeness for unindexed methods is made. Reference: implementation map at the map commit above; prefix-count result retained in the self-check record.

Map follow-up, [issue pending (7)](ISSUES_DRAFT.md#draft-7): add the section-3 families HTTP pagination, response normalization, incremental selection and persistence before counted-family searches can apply to them. Their current implementations are `_get`, `parse_response`, `_filter_new_records`, `_latest_period`, `write_jsonl`, `save_last_fetch`, `run_petroleum_sync` and `run_gas_storage_sync`. [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L96-L184] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L74-L83] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L119-L252]

### Whole-repository search, including scripts

```bash
git grep -n -E 'EIAFeedClient|EIAIngestionSync|api\.eia\.gov|fetch_series|parse_series_response' bb9239b5160221ba2ade16214816abacd86b7639 -- '*.py' '*.sh'
rg -n 'eia|EIA' scripts --glob '*.py' --glob '*.sh'
```

`EIAApiClient.parse_series_response` is another numeric-normalization implementation outside this package; its `fetch_series` route is a separate series client with caching. These are map gaps, not counted-family misses. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L172-L201] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L205-L235]

`StateProductionLoader.load` is a further out-of-package date/number normalization and unit-conversion route for monthly production; its output contract differs from the weekly record-preserving client. It is included in the map follow-up, [issue pending (7)](ISSUES_DRAFT.md#draft-7). [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L53-L102]

The CLI, scheduler adapter and shell launcher delegate to listed ingestion definitions; they are helpers rather than further implementations of the package's selection algorithm. [src/worldenergydata/cli/commands/eia.py:L100-L107] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L55-L61] [scripts/eia_weekly_sync.sh:L60-L66]

## 10. Coverage and open items

### Reading coverage

All package Python files were read: `__init__.py`, `client.py`, `ingestion.py`, `ingestion_runner.py`; no sub-package is excluded from the header scope. [packages/worldenergydata-eia/src/worldenergydata/eia/__init__.py:L1-L28] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L1-L235] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion.py:L1-L263] [packages/worldenergydata-eia/src/worldenergydata/eia/ingestion_runner.py:L1-L86]

Package README and build metadata were read; tests read comprise all 41 client/ingestion tests and all 5 scheduler-adapter tests. The similarly named benchmark file exercises `eia_us` rather than this package. [packages/worldenergydata-eia/README.md:L1-L8] [packages/worldenergydata-eia/pyproject.toml:L1-L54] [tests/unit/eia/test_client.py:L1-L644] [tests/unit/scheduler/test_eia_adapter.py:L1-L146] [tests/benchmarks/test_eia_benchmarks.py:L13-L16]

The discovery index below records whole-word `eia` and `EIA` matches. Historical figures are excluded from the behavior and test-count basis; the cited implementation and executed test nodes govern this pack.

- [docs/CLI.md:L427-L429]
- [docs/adr/0001-domain-package-split.md:L41-L43]
- [docs/data-sources/bsee/data/drilling_data_rev1.md:L166-L168]
- [docs/data-sources/bsee/data/well/well_count.md:L5-L7]
- [docs/domains/field-development/gas-revenue.md:L39-L41]
- [docs/knowledge-base/bsee/data-dictionaries/common/unit-conversions.md:L109-L111]
- [docs/modules/bsee/analysis/production/FDAS_V30/PRICE_DECKS_SOURCE.md:L3-L5]
- [docs/modules/bsee/analysis/production/lt_v30_v50_code_reconciliation.md:L21-L23]
- [docs/modules/cost/REFRESH_PROCEDURE.md:L82-L84]
- [docs/modules/dashboard/implementation-guides/full-stack-guide.md:L392-L394]
- [docs/modules/data-procurement/api-catalog.md:L8-L10]
- [docs/modules/data-procurement/api-decision-matrix.md:L29-L31]
- [docs/modules/repository-architecture.md:L101-L103]
- [docs/plans/2026-04-26-issue-353-diagnose-uv-scheduler-noop-timeouts.md:L19-L21]
- [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L16-L18]
- [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L14-L16]
- [docs/plans/2026-05-03-issue-375-per-field-economics-10-lt-fields.md:L16-L18]
- [docs/plans/2026-05-04-issue-266-eia-scheduler-operationalize.md:L1-L2]
- [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L20-L22]
- [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L111-L113]
- [docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md:L107-L109]
- [docs/plans/README.md:L14-L16]
- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L17-L19]
- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L218-L220]
- [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L11-L13]
- [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml:L38-L40]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L20-L22]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L59-L61]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L133-L135]
- [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L31-L33]
- [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L85-L87]
- [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L15-L17]
- [docs/reports/2026-04-26-worldenergydata-scheduler-safe-probe-results.md:L58-L60]
- [docs/reports/2026-04-27-plan-354-adversarial-review.md:L8-L10]
- [docs/reports/cli-smoke-report-2026-05-11.md:L15-L17]
- [docs/research/bsee-fdas-integration-summary.md:L300-L302]

Codenaming follow-up: 1 discovery file with identifying names is omitted from the public reading index; [issue pending (8)](ISSUES_DRAFT.md#draft-8).

Routing metadata: NOT_APPLICABLE; *Module agent lifecycle and module knowledge pack*, revision 0, section 2 specifies a knowledge-index row for this repository in place of a routing-registry entry.

### Revision 0 offline execution record

Both runs exercised code revision `bb9239b5160221ba2ade16214816abacd86b7639`; module source digests remain unchanged. Ordinary `uv run python -m pytest` form was used, retaining root addopts, with `-q -rA -p no:cacheprovider`, scratch basetemp and `--cov-report= --cov-report=json:<scratch>`. The after run adds the documented `--allow-existing-tree-changes` option for the existing pack.

| Run | Paths | Run | Passed | Failed | Skipped | NOT_RUN |
| --- | --- | --- | --- | --- | --- | --- |
| BASE, before editing | `tests/unit/eia tests/unit/scheduler/test_eia_adapter.py` | 46 | 46 | 0 | 0 | 0 |
| After, uncommitted tree | Same paths plus `tests/contracts` | 92 | 92 | 0 | 0 | 0 |

The same 46 module/adapter node IDs pass in both runs; the additional 46 contract nodes also pass. Every section-4 node appears as PASS in both logs. Evidence records are retained separately; there are no failed, skipped or NOT_RUN node IDs.

The root pytest defaults include coverage; JSON evidence is directed to external scratch while collection rules remain unchanged. The defaults also generate local HTML/XML reports, which are removed by exact path after the runs. The after run enables existing-tree comparison through the documented `--allow-existing-tree-changes` option. [pyproject.toml:L392-L413] [tests/conftest.py:L480-L490]

### Revision 1 offline execution record

The documentation-only update leaves all four package source files byte-identical to the code pin. BASE and after each ran `tests/unit/eia tests/unit/scheduler/test_eia_adapter.py` with `uv run --no-project --with pytest python -m pytest`, `-q -rA -p no:cacheprovider`, external scratch basetemp, coverage and JUnit destinations, and the declared import dependencies supplied to the isolated environment. The after run used `--allow-existing-tree-changes` to compare the pre-existing documentation edits; the tree-preservation check passed. Checks requested after committing were performed on the uncommitted tree.

| Run | Tests | Passed | Failed | Skipped | NOT_RUN |
| --- | --- | --- | --- | --- | --- |
| BASE, before revision 1 edits | 46 | 46 | 0 | 0 | 0 |
| After revision 1 edits, uncommitted tree | 46 | 46 | 0 | 0 | 0 |

Both runs passed the same 46 node IDs, including all five section-4 examples. The revision-0 contract-suite figures above are historical; that suite is not included in the revision-1 counts. The documentation self-check resolves all citations at the code pin and checks all numbered-draft links. Seven targeted documentation assertions failed before the edits and pass afterward; they check draft resolution, all 13 open-item trackers, sweep/S35 presence, S05 and S28 wording, check ordering and issue-reference format.

### Open items and qualification limits

| Item | Disposition / required evidence | Responsible role | Tracking |
| --- | --- | --- | --- |
| Missing response envelope / pagination totals | Add malformed-envelope and multiple-page completion regressions; S01, S05, S06, S21, S29, S35 | Maintainer | [issue pending (1)](ISSUES_DRAFT.md#draft-1) |
| Numeric/schema/unit integrity | Separate null, invalid, locale-formatted and nonfinite inputs; reject unintended JSON stringification and incompatible units; S02–S04, S13, S16 | Maintainer | [issue pending (2)](ISSUES_DRAFT.md#draft-2) |
| State integrity and revision handling | Validate state object/date types; define correction replay and concurrent/partial-write recovery; S07–S12, S14–S15, S20 | Maintainer | [issue pending (3)](ISSUES_DRAFT.md#draft-3), #431 |
| Runner and empty-result coverage | Cover S17–S18, S22–S27 and S31, including empty feeds, partial success and the downstream warning-only paths S32–S33 | Maintainer | [issue pending (4)](ISSUES_DRAFT.md#draft-4), #266 |
| UNVERIFIED live compatibility and freshness | Obtain a real successful materialization with source-vintage evidence; mocked tests do not establish it | Maintainer | #266 |
| UNVERIFIED independent source-value validation | Add an openly sourced revisioned reference, then reconsider validated examples; record independent QA evidence and shared lessons | Maintainer | [issue pending (5)](ISSUES_DRAFT.md#draft-5) |
| Markdown packaging | Existing `**/*.md` package-data glob includes nested documentation; exclusion from built distributions is not established and requires a packaging change outside this pack | Maintainer | [issue pending (6)](ISSUES_DRAFT.md#draft-6) [packages/worldenergydata-eia/pyproject.toml:L53-L54] |
| Implementation-map coverage | Index all four section-3 families and outside-package normalization route | Maintainer | [issue pending (7)](ISSUES_DRAFT.md#draft-7) |
| Identifying discovery names | Assign neutral identifiers before publishing the omitted reading locator | Maintainer | [issue pending (8)](ISSUES_DRAFT.md#draft-8) |
| CLI documentation drift | `docs/CLI.md` shows `eia fetch`, while command implementation documents and implements `sync`; retain code route as the usage basis | Maintainer | [issue pending (9)](ISSUES_DRAFT.md#draft-9) [docs/CLI.md:L428-L442] [src/worldenergydata/cli/commands/eia.py:L38-L72] |
| HTTP retry/key handling | Resolve lack of retry and query-key exposure without copying credential values into evidence | Maintainer | #431 [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L142-L173] |
| Quickstart redaction | Prevent disclosure of configured authentication material in the example; S34 | Maintainer | [issue pending (10)](ISSUES_DRAFT.md#draft-10) |
| Independent acceptance | File the ten linked numbered drafts, replace pending references with issue numbers, and obtain a second-provider A1–A8 decision before clearance | Maintainer | [issue pending (5)](ISSUES_DRAFT.md#draft-5) |
