# Bandit enforcement triage

## Summary

Bandit 1.9.4 reports zero blocking findings and zero parse errors after five findings at BASE. The existing `src/` scan scope and medium severity/confidence thresholds are retained.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-23 | Five findings are resolved before failure suppression is removed. |

## 1. Basis

BASE: `2b98c7a6263ae2c04daa8265bdc16eb7906fc027`. Command: `uvx bandit==1.9.4 -r src/ -ll -ii -x tests/`. The scanner with these flags returned 1 before fixes; JSON reports were retained in scratch. No application module is imported by the scanner.

## 2. Dispositions

| Finding at BASE | Disposition and detection |
| --- | --- |
| `src/worldenergydata/field_development/dexpi.py:110`, B314 | The parser target rejects every DOCTYPE before expansion; two specific B314 annotations document this boundary. Empty and entity-bearing DTD regressions reject both inputs; existing round trips pass. |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:43`, B310 | The HTTP-only opener rejects other source and redirect schemes. |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:55`, B310 | The same HTTP-only opener is used; timeout and response behavior are retained. |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:32`, B310 | The same HTTP-only opener is used; existing download metadata tests pass. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:101`, B324 | MD5 is marked `usedforsecurity=False` for structural duplicate detection. A restricted-MD5 regression verifies both the flag and duplicate count. |

## 3. Acceptance

The command returns 0 for a clean fixture, 1 for an unsafe pickle fixture, and 2 for an invalid scanner option. Regression cases reject masking suffixes, unpinned versions, duplicate/missing steps, conditions and continue-on-error on the step or job. The workflow remains dispatch-only with the same jobs and PR policy.

## 4. Limits

Split packages remain outside this historical scan scope; broader coverage requires a separate change. Low-severity or low-confidence findings remain outside the existing threshold. HTTP(S) restrictions do not establish destination authorization or prevent private-network access. DTD rejection does not bound general XML document size. Existing metadata defaults and swallowed errors below remain unresolved. Hosted execution and independent review remain pending.

## 5. Checks

BASE compatibility: 159 passed. Before fixes, enforcement tests produced 12 passes and 4 expected failures; runtime regressions produced 3 failures and 7 missing-helper errors. After fixes: 186 passed, comprising 159 compatibility cases and 27 new cases. Commands use isolated pytest environments, no conftest, disabled cache and scratch output.

The focused files are `tests/workflows/test_bandit_enforcement.py`, `tests/workflows/test_bandit_triage.py`, `tests/workflows/test_ci_triggers.py`, `tests/ci/test_runner_routing.py`, `tests/ci/test_check_f821.py`, `tests/modules/field_development/test_dexpi.py`, `tests/modules/field_development/test_independent_topology.py`, and the three regulator pipeline/source-discovery test files. The download metadata checks are `test_download_source_writes_bytes_and_response_metadata` and `test_fetch_facility_detail_writes_html_and_metadata`.

## 6. Silent-failure review

The six changed source modules are swept with `rg -n 'except|continue|return None|return \[\]|return \{\}|= \[\]|= \{\}|\b0(\.0)?\b|1970|\b(int|float)\(|\.get\(|else pd.DataFrame' <changed-source-files>`. Each matched line is listed below, excluding the literal schema version. No new engineering-unit assumptions or empty-result caches are introduced. Existing manifest/parquet writes can retain empty results as noted below; provenance does not establish data readiness.

| Current file and line | Symptom and detection |
| --- | --- |
| `src/worldenergydata/field_development/dexpi.py:81` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:122` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:127` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:130` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:134` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:138` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:140` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:141` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:148` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:149` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:150` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/field_development/dexpi.py:151` | Absent XML attribute receives a default; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:32` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:42` | Byte counter starts at zero; download metadata tests in section 5. |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:57` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:58` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:69` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:72` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:76` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:77` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:78` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:79` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:80` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:81` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:82` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:83` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:98` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:133` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:135` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:136` | Non-production source is skipped; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:142` | No frames produces an empty table; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:29` | Configuration/count conversion; no separator normalization check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:54` | Byte counter starts at zero; download metadata tests in section 5. |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:70` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:71` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:85` | Configuration/count conversion; no separator normalization check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:86` | Absent count becomes zero; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:88` | Configuration/count conversion; no separator normalization check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:89` | Absent count becomes zero; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:104` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:109` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:114` | Configuration/count conversion; no separator normalization check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:115` | Configuration/count conversion; no separator normalization check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:120` | Configuration/count conversion; no separator normalization check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:121` | Configuration/count conversion; no separator normalization check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:122` | No frames produces an empty table; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:31` | Byte counter starts at zero; download metadata tests in section 5. |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:46` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:47` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:58` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:61` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:65` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:66` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:68` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:69` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:70` | Optional metadata or fallback; no detection check exists (issue pending). |
| `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:85` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:28` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:29` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:30` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:31` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:32` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:69` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:77` | Error is logged and swallowed; no detection check exists (issue pending). |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:82` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:114` | Error is logged and swallowed; no detection check exists (issue pending). |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:176` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:229` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:265` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:268` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:290` | Error is logged and swallowed; no detection check exists (issue pending). |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:305` | Error is logged and swallowed; no detection check exists (issue pending). |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:319` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:320` | Empty accumulator initialization; no error fallback. |
| `src/worldenergydata/testing/cleanup/test_analyzer.py:340` | Error is logged and swallowed; no detection check exists (issue pending). |
