# Marine safety collection and baseline results

Summary: directory collection now visits all dedicated test files. Established
assertion/API mismatches remain unfixed and visible as strict xfails. Optional
classifier dependencies skip explicitly; no classifier result is qualified.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-22 | Record independent collection counts, raw outcomes and per-node causes for #1351 and #1239. |

## Sources and scope

- Source base: `a814fe13149465d1daeb8a06ca2f024b60a335a1`, equal to `origin/main` at start.
- Historical pack: revision 1, 2026-10-15, sections 6 and 10; it reports 35 FAIL and 28 ERROR with optional model dependencies installed. Those counts are historical evidence, not expected outcomes for another environment.
- Audit issues: #1351 defects 1–5 and #1239. No engineering equation, coefficient or acceptance tolerance is introduced.
- Collection oracle: disk enumeration compared with file-level pytest reports by `tests/unit/test_marine_safety_collection.py`. The comparison includes module skips.
- Failure oracle: assertions and API/schema definitions read on `origin/main`; no production method is changed.
- Attribution of each remaining defect: [ISSUES_DRAFT.md](ISSUES_DRAFT.md), with exact node/exception entries in `tests/unit/marine_safety/baseline_failures.json`.

## Collection worked example

| Inventory | Before | After | Evidence |
| --- | --- | --- | --- |
| Unit files | 0/52 | 52/52 | Root hook exclusion, then collection set comparison |
| Dedicated trees including module and API files | 4/56 | 56/56 | Regression red/green runs, with 55 successful and 1 module-skip file report after restoration |
| Separate CLI integration file | Outside that inventory | Tested separately | Explains the historical 57-file total in the packs |

The before hook could not visit the hatch-analysis file. Its historical fixture
namespace and two lazy fixture imports are corrected to allow collection.
No hatch-analysis assertion or production method is changed.

## Outcome ledger

| Run | Passed | Failed | Setup errors | Skipped | Strict xfail | Collection errors |
| --- | --- | --- | --- | --- | --- | --- |
| First exposed run, before optional dependency handling | 2,061 | 33 | 26 | 40 | 0 | 0 |
| Raw run with test dependencies available and explicit optional skips (`--runxfail`) | 2,062 | 30 | 0 | 68 | 0 | 0 |
| Ordinary run, same marine-safety and compatibility scope | 2,062 | 0 | 0 | 68 | 30 | 0 |
| Expanded checks, latest result per node including corrected tree-fixture run | 2,248 | 0 | 0 | 70 | 30 | 0 |

The first run lacked `PyPDF2` and the sibling utility source on the import path.
Providing those test dependencies resolves the API-envelope failure and exposes
the PDF method mismatch. The absent optional classifier dependencies account
for the first run’s setup errors and two additional call failures; these become
reasoned skips. The remaining raw failures are not fixed or excluded.
The expanded run includes the new collection/documentation regressions, CLI,
existing pack-lint and tree-preservation tests. Four tree-fixture checks initially
failed because inherited `COVERAGE_FILE` redirected their expected data file;
configuring coverage only for the parent resolves them (28 PASS, 2 optional SKIP).
No assertion was changed. The expanded ledger uses the latest result per node.

## Reproduction

Provide the dependencies declared by the marine-safety package, the sibling
utility source, pytest and its coverage/mock/asyncio plugins, plus the test
fixtures’ `faker` and `PyPDF2` dependencies. The audit uses the repository source
roots on `PYTHONPATH`. The optional classifier packages are absent.

```bash
python -m pytest tests/unit/marine_safety tests/modules/marine_safety \
  tests/marine_safety tests/unit/test_modules_compat.py \
  -q -rA --runxfail --import-mode=importlib --allow-existing-tree-changes \
  -p no:cacheprovider --basetemp="$TMPDIR/raw-tests" \
  --cov-report=term --cov-report=html:"$TMPDIR/htmlcov" \
  --cov-report=xml:"$TMPDIR/coverage.xml" \
  --cov-report=json:"$TMPDIR/coverage.json"
```

Coverage data also uses `COVERAGE_FILE` in scratch. Remove `--runxfail` for the
ordinary strict-xfail run. A passing xfailed assertion is an error; an exception
outside its recorded class is also an error. No file is excluded for a known
failure. No optional model data is downloaded or assumed present.

## Per-node baseline and dependency ledger

Each row was observed in the first exposed run; raw established failures were
confirmed again with dependencies available. The exception-class restriction
guards unrelated failures; resolving a mismatch requires removing its marker.

| Test node | First exposed outcome | Current classification and established cause |
| --- | --- | --- |
| `tests/unit/marine_safety/analysis/test_cause_statistics.py::TestStatisticalSummary::test_print_report` | FAIL (call) | Strict XFAIL (AssertionError), canonical draft 8: The test expects stdout while print_report uses logging. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_custom_model_path` | FAIL (call) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classify_hatch_maloperation_positive` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classify_hatch_maloperation_negative` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_confidence_scores_returned` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_batch_classification` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classification_determinism` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_hatch_not_closed` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_opening_maloperation` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_engine_room_access_failure` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_watertight_door_issue` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_negative_case_no_hatch_incident` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_empty_text_handling` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_none_value_handling` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_whitespace_only_handling` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_very_long_text_handling` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_multilingual_text` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_special_characters_handling` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_numeric_only_text` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_batch_processing_faster_than_individual` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_classification_within_time_limit` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_batch_throughput` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_positive_case_accuracy` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_negative_case_accuracy` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_confidence_calibration` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_f1_score_calculation` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_concurrent_classification` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_error_recovery` | ERROR (setup) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_repeated_initialization` | FAIL (call) | SKIP: optional transformers/torch dependencies unavailable; no model fixture result. Canonical draft 7. |
| `tests/unit/marine_safety/test_correlation.py::TestIncidentMatcherConfidence::test_find_matches_returns_above_threshold` | FAIL (call) | Strict XFAIL (AssertionError), canonical draft 5: The test-local weighted matcher finds no qualifying pair. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_success` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_timeout` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_connection_error` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_retry_on_failure` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_max_retries_exceeded` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_html` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_empty_html` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_malformed_html` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_scrape_incidents_date_range` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_download_pdf_success` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_extract_pdf_text` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. First run was blocked by absent optional PyPDF2; the raw run confirms the absent public method. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_parse_pdf_metadata` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_http_500_error` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_invalid_ssl_certificate` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_network_timeout_recovery` | FAIL (call) | Strict XFAIL (AttributeError), canonical draft 3: Scraper tests call public methods absent from the implementation. |
| `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_valid_incident_data` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_missing_required_fields` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_casualties_validation` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_negative_casualties` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_severity_type_consistency` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_location_validation` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_valid_vessel_data` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_vessel_name_required` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_gross_tonnage_positive` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_year_built_range` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_pollution_environmental_impact` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_critical_severity_requires_investigation` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_vessel_incident_consistency` | FAIL (call) | Strict XFAIL (ValidationError), canonical draft 4: Empty Pydantic model construction fails before the validator assertions. |
| `tests/marine_safety/test_api_on_base.py::test_marine_safety_query_envelope` | FAIL (call) | PASS after including the declared sibling utility source on the import path; environment omission, no code change. |

## Limits and follow-up

The historical 35 FAIL / 28 ERROR cannot be reproduced without the historical
environment and supplied model inputs. The current counts are measured outcomes,
not calibrated incident-analysis benchmarks. Database and integration skips in
existing tests remain visible and are not counted as passed. Canonical drafts
1–9 retain the work for the maintainer to file; no new issue is created.
