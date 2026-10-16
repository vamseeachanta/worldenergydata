# well_planning knowledge pack

| Header | Value |
|---|---|
| Module | `well_planning` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-well_planning/src/worldenergydata/well_planning` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `92b13dce6b3121cbe827f17327c6dde7fcd6dc5c` |
| Analysis family | EC; data pipeline, using AQG r0 Python calculations gates |
| Quality manager role | Calculations quality manager, interim data-pipeline coverage |
| Status | DRAFT; independent review pending |

## 1. Purpose and scope

The public API exposes risk enums, a risk dataclass, a built-in registry, an analyzer and calibration records/reports. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/__init__.py:L3-L27]
The analyzer filters risk records, sorts supplied scores, counts authority/category combinations and produces text and DataFrame summaries. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L38-L129]
The calibrator consumes an incident DataFrame, maps incident pairs to risk IDs, blends annual weighted frequencies with baseline probabilities, and returns copied registry entries. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L125-L258]
These are screening and reporting algorithms: the implemented operations are counts, filtering and probability arithmetic; the analyzer does not calculate physical drilling loads or equipment capacity. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L38-L129] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L176-L230]

Scope includes all five Python files in the package; calibration is included rather than treated as a separate sub-package. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/__init__.py:L3-L27]
The distribution declares version 0.1.0 and an Alpha classifier; neither establishes engineering qualification. [packages/worldenergydata-well_planning/pyproject.toml:L5-L24]
UNVERIFIED: an authoritative engineering-use maturity classification is not established by the inspected package metadata; resolve through #349. [packages/worldenergydata-well_planning/pyproject.toml:L5-L24]

## 2. Inputs and outputs

### Inputs

| Input | Unit / convention | Allowed range and default | Source and evidence |
|---|---|---|---|
| `risk_id`, `title`, `description` | Text | Required constructor arguments; no runtime validators in the dataclass | Caller; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L45-L66] |
| `category`, `authority`, `severity` | Enum; dimensionless | Seven categories, three authority tiers, severity integers 1–4 | Caller; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L12-L42] |
| `probability`, `risk_score` | Dimensionless | Probability comment states 0–1; score is supplied, not auto-computed; no enforcement | Caller; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L45-L66] |
| `mitigation_owner`, `mitigation_action`, `escalation_template`, `mpd_mitigation` | Role text, action text, template text, boolean | Required; flag filters records, without recalculating severity | Caller; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L62-L65] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L55-L57] |
| `related_wrk` | List of reference strings | New empty list per dataclass construction | Caller; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L66-L66] |
| Analyzer `risks` | List of risk records | `None` uses registry by reference; empty list is accepted | Caller / built-in registry; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L29-L32] [tests/unit/well_planning/test_risk_analyzer.py:L103-L112] |
| Filter thresholds | Dimensionless | Minimum severity is inclusive; score threshold defaults to 2.0 and is inclusive | Caller; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L46-L53] |
| `hse_df` | Rows of incidents | Nonempty data requires `incident_type` and `sub_type`; severity absent or unknown uses weight 1.0 | Caller DataFrame; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L141-L166] |
| Time columns | Calendar dates or numeric years | First usable column in `date`, `year`, `incident_date`; at least 1.0 year; unavailable/unparseable time falls back to 1.0 year | Caller DataFrame; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L351-L376] |
| Incident pair strings | Case-sensitive text | Whitespace stripped; unknown pair maps to no risks | Caller; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L344-L349] |
| Synthetic `n_incidents` | Rows | Default 150; random seed 42 | Test helper; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L277-L310] |

The supplied schema contains no coordinates, geometric origin, sign convention or phase convention; dates determine exposure duration rather than spatial position. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L54-L66] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L351-L376]
No input-file parser or output-file serializer is provided by the public methods; input/output objects are Python records, DataFrames and strings. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L80-L94] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L63-L129]

### Outputs

| Output | Unit | Contract / limit | Evidence |
|---|---|---|---|
| Filtered lists / priority list | Records | Exact enum filtering; priority scores descending | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L38-L57] |
| `risk_matrix()` | Risk count per cell | All enum authority rows and category columns, initialized to zero | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L63-L83] |
| `escalation_report()` | Text | Empty string for no matching risks; scores formatted to two decimals | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L85-L108] |
| `summary()` | DataFrame | Six columns for nonempty records, descending score; empty input returns columnless frame | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L110-L129] |
| `CalibrationRecord` | Weighted events/year; dimensionless probabilities | ID, category, annual rate, calibrated/baseline probability, confidence label, data-driven flag | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L58-L68] |
| `RiskCalibrationReport` | Years, risk-mapping count, percent | `total_incidents_used` counts each row-to-risk mapping; `coverage_pct` measures registry IDs meeting the count threshold | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L156-L166] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L219-L228] |
| `to_dataframe()` | Same record units | Seven record columns; report totals and exposure duration are not included | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L80-L94] |
| `risk_probability()` | Dimensionless float and bool | Unfitted returns baseline; unknown ID returns 0.5 and false | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L260-L271] |
| `calibrate_registry()` | Risk records | Shallow copies; probability and score rounded to four decimal places | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L240-L258] |

## 3. Method and governing standards

| Method family | Implementation and algorithm | Reference / qualification |
|---|---|---|
| Authority risk classification and score | `RiskAuthority`, `RiskCategory`, `RiskSeverity`, `WellPlanningRisk`: authority is supplied, not inferred; score convention is severity integer × probability, with caller-supplied score | Local convention; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L12-L66] |
| Risk selection and aggregation | `get_by_authority`, `get_by_category`, `get_by_severity`, `high_priority_risks`, `mpd_mitigable_risks`, `risk_matrix`: equality/inclusive comparisons, sorting and counts | Local algorithm; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L38-L83] |
| Incident-to-risk calibration | `calibrate`: look up ten incident pairs, accumulating severity weights per mapped risk; five raw mapped incidents qualify a risk for calibration | Local mapping/constants; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L22-L48] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L156-L185] |
| Exposure conversion | `_parse_years_covered`: numeric year span or elapsed whole days divided by 365.25; lower bound and fallback 1.0 year | Local convention, not well-year exposure normalization; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L351-L376] |
| Probability blend | Annual rate = weighted count / years; data probability = clip(rate / 5.0, 0.05, 0.95); result = clip(0.6 × data probability + 0.4 × baseline, 0.05, 0.95); sparse risks retain baseline | Implemented arithmetic; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L176-L205] |
| Confidence / coverage | At least 20 raw mapped incidents gives `high`; 5–19 gives `medium`; sparse gives `low`; coverage is calibrated-ID count / registry length × 100 | Count labels, not statistical confidence intervals; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L185-L228] |
| Synthetic incidents | `synthetic_hse_dataframe`: seeded category/severity/date sampling; this is generated test data rather than observed incidents | Local generator; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L277-L338] |

Severity weights are 2.0, 1.5, 1.0, 0.5 and 0.3 for the five named severity labels; an unknown label receives 1.0. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L38-L44] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L161-L162]
The calibration mapping, weights, clipping and blend are implemented without a named standard edition or clause in their defining code; they must be reviewed as local assumptions. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L22-L48] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L176-L205]
UNVERIFIED: empirical applicability of baseline probabilities, incident-to-risk associations, severity weights, normalization and blend coefficients is not established by the synthetic tests; independent calibration evidence is required, issue pending (1). [tests/unit/well_planning/test_risk_calibrator.py:L25-L32] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L22-L48]
No licensed-standard values are adopted in this pack; the registry's named training requirement is descriptive text, without edition or clause metadata. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L481-L503]
Citation sidecar adoption for standards-derived calculations is tracked by #361; this pack does not qualify these local calibration constants as standards-derived. (Repository issue #361, “Adopt calculation-output citation sidecars”, inspected 2026-10-15.)

## 4. Validated worked examples

Validated examples: **0**; the cases below use local test fixtures or registry expectations and are regression examples, not independently sourced validation. [tests/unit/well_planning/test_risk_model.py:L17-L33] [tests/unit/well_planning/test_risk_analyzer.py:L44-L85] [tests/unit/well_planning/test_risk_calibrator.py:L25-L32]

Execution observations below come from the retained offline logs; source citations identify the tests and their expectations.

All node IDs below are relative to `tests/unit/well_planning/`; each row is one existing test node, run offline at the header code revision with result PASS at BASE and PASS after the documentation addition. [tests/unit/well_planning/test_risk_model.py:L137-L139] [tests/unit/well_planning/test_risk_analyzer.py:L138-L140] [tests/unit/well_planning/test_risk_analyzer.py:L262-L264] [tests/unit/well_planning/test_risk_calibrator.py:L41-L43] [tests/unit/well_planning/test_risk_calibrator.py:L247-L257]

| Case | Source / input | Expected value and unit | Tolerance and basis | Test node ID | Offline result, BASE / after |
|---|---|---|---|---|---|
| R1 supplied score | Local `sample_risk`: severity 3, probability 0.6 | 1.8 dimensionless | Absolute error < 1e-9, test assertion | `test_risk_model.py::TestWellPlanningRisk::test_risk_score_equals_severity_times_probability` | PASS / PASS; [tests/unit/well_planning/test_risk_model.py:L17-L33] [tests/unit/well_planning/test_risk_model.py:L137-L139] |
| R2 authority selection | Local five-record `custom_risks` fixture | 2 strategic records | 0 records difference, exact assertion | `test_risk_analyzer.py::TestGetByAuthority::test_count_matches_custom_fixture` | PASS / PASS; [tests/unit/well_planning/test_risk_analyzer.py:L44-L85] [tests/unit/well_planning/test_risk_analyzer.py:L138-L140] |
| R3 matrix conservation | Built-in risk registry | Matrix sum equals registry size, 21 risks at the pin | 0 risks difference, exact assertion | `test_risk_analyzer.py::TestRiskMatrix::test_total_count_equals_registry_size` | PASS / PASS; [tests/unit/well_planning/test_risk_analyzer.py:L262-L264] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L15-L529] |
| R4 synthetic shape | Local seeded generator fixture | 150 incident rows | 0 rows difference, exact assertion | `test_risk_calibrator.py::TestSyntheticDataFrame::test_shape_default_rows` | PASS / PASS; [tests/unit/well_planning/test_risk_calibrator.py:L25-L27] [tests/unit/well_planning/test_risk_calibrator.py:L41-L43] |
| R5 copied-registry score consistency | Fitted synthetic-data fixture | severity × updated probability, dimensionless | `pytest.approx` with explicit absolute tolerance 1e-3; arithmetic consistency only | `test_risk_calibrator.py::TestCalibrateRegistry::test_risk_score_consistent_with_probability` | PASS / PASS; [tests/unit/well_planning/test_risk_calibrator.py:L247-L257] |

Test inventory / execution record (2026-10-15): 120 collected and passed, 0 failed, 0 skipped, 0 NOT_RUN before and after; four test files contain 34 model, 21 registry, 38 analyzer and 27 calibrator test definitions, respectively. [tests/unit/well_planning/test_risk_model.py:L40-L209] [tests/unit/well_planning/test_risk_registry.py:L14-L135] [tests/unit/well_planning/test_risk_analyzer.py:L103-L337] [tests/unit/well_planning/test_risk_calibrator.py:L40-L257]

Reproduction command, using the ordinary workspace source resolution and declared test extra:

```sh
uv run --extra test python -m pytest tests/unit/well_planning -q -rA \
  -p no:cacheprovider --basetemp="$TMPDIR/bt-<run>"
```

AFTER adds the documented `--allow-existing-tree-changes` mode: it fingerprints the existing pack and fails on new or changed content; BASE started clean. [docs/development/index.md:L56-L59] [tests/conftest.py:L412-L460]
The initial AFTER and contract invocations passed all 120 and 46 test nodes respectively, but exited 1 because the default guard reported the pre-existing untracked pack; the final repeats with the documented mode both exited 0. [tests/conftest.py:L434-L460]
Contract check: `uv run --extra test python -m pytest tests/contracts -q -rA -p no:cacheprovider --basetemp="$TMPDIR/bt-contracts" --allow-existing-tree-changes`, on the uncommitted documentation tree at the header pin, collected and passed 46 tests, with 0 failed, 0 skipped and 0 NOT_RUN. This checks upstream API/register contracts rather than a routing registry.

Retain the configured pytest addopts; save stdout/stderr and before/after ignored-file inventories outside the repository, and remove generated coverage files by explicit path after the run.

## 5. QA gates

Gate applicability follows AQG r0, section 10, “Python calculations”, with G5 from section 9. (AQG r0, revision 0, sections 9–10.)
The following are pack check definitions, not an engineering qualification or a quality-manager signature.

| Gate | Applicability | Module-specific check / numeric pass criterion | Evidence to retain |
|---|---|---|---|
| G0 | Applicable: records, units and assumptions | G0-01: for every registry record, finite probability in [0, 1] dimensionless and absolute score error < 1e-9 dimensionless; 0 violations. G0-02: for the five-row calibration fixture, 0 missing required columns, 0 null incident-pair cells and an explicitly declared 1-year interval; compare exact pair strings with the mapping | Input table, assumption list and violation count; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L54-L66] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L141-L166] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L344-L376] |
| G1 | Applicable: Python imports and tests | G1-01: import through `worldenergydata.well_planning` and run the section-4 command; 120 tests passed, 0 failures, 0 collection errors, 0 skipped tests | Interpreter/dependency versions, full node outcomes and test log; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/__init__.py:L3-L27] [tests/unit/well_planning/test_risk_calibrator.py:L11-L18] |
| G2 | Applicable: hand arithmetic | G2-01: five recordable `kick` / `pressure_control` incidents in one declared year; for OP-002 compute `min(0.95, max(0.05, 5 / 5))`, blend with baseline 0.55, obtaining 0.79 dimensionless; absolute error ≤ 1e-12 dimensionless; flag true. Use scalar decimal arithmetic outside the calibrator | Hand calculation, input digest and returned tuple; this checks implementation arithmetic, not empirical validity; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L24-L24] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L36-L48] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L176-L205] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L44-L54] |
| G3 | NOT_APPLICABLE | No dynamic state integration in these functions; operations are filtering, counting and probability blending | Reason retained; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L38-L83] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L176-L230] |
| G4 | NOT_APPLICABLE | No diffraction body, mesh or hydrostatic computation in the supplied input/output schema | Reason retained; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L54-L66] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L58-L94] |
| G5 | Applicable: evidence appendix | G5-01: retain input SHA-256, code pin, gate outcomes and report export; report record count = updated-registry count = 21 records; matrix total = 21 risks; exported versus returned probability absolute discrepancy ≤ 5e-5 dimensionless, allowing four-decimal rounding; 0 missing required evidence records | Generated evidence JSON plus report DataFrame and test log; obtain independent signature before report release; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L207-L228] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L240-L258] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L63-L83] (AQG r0, revision 0, section 9.) |

Five checks are defined: G0 two, G1 one, G2 one, G5 one; G3 and G4 have no applicable check.
G0-01, G0-02, G2-01 and G5-01 were exercised on the controlled five-row fixture; G1-01 is supported by the complete module test runs; independent gate signatures remain pending.
For reproducibility, build the G2 fixture as five rows with columns `incident_type`, `sub_type`, `severity`, `year` and values `kick`, `pressure_control`, `recordable`, `2020`; retain the exact CSV bytes and SHA-256 beside the evidence.

## 6. Known failure modes and pitfalls

| Symptom | Cause and detection recipe | Reference / tracking |
|---|---|---|
| Invalid or missing time silently gives one year; unknown incident pairs disappear; unknown severity is accepted with weight 1.0 | G0-02 preflight: require 0 unparseable exposure inputs, 0 unknown incident pairs, 0 unknown severities for supplied data; the module does not enforce these extra acceptance conditions | issue pending (2); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L161-L162] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L344-L376] |
| Sparse or unfitted calibration returns baseline, while an unknown risk ID returns 0.5 and false | Inspect `data_driven` per risk; compare with the count threshold, never treat a float alone as calibrated evidence | issue pending (1); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L185-L203] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L260-L271] |
| `total_incidents_used` exceeds distinct input rows | The counter increments per mapped risk, not per incident; five matching kick rows produce ten mappings; detection: compare input row count with independently summed pair multiplicities before using totals | issue pending (3); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L156-L166] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L223-L227] |
| A copied risk shares its mutable reference list with the original | `copy.copy` preserves `related_wrk` list identity; detection: `updated[0].related_wrk is WELL_PLANNING_RISKS[0].related_wrk`; expected independence requires 0 shared list identities | issue pending (5); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L249-L257] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L66-L66] |
| Synthetic outputs contain identifying organization labels | Generator embeds a five-label vocabulary; detection: inspect the `operator` column against a permitted dataset-ID vocabulary; expected 0 identifying labels | issue pending (4); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L325-L338] |
| Calibration mappings can assign an incident to a semantically different risk | Compare each incident pair with the target risk description, rather than trusting the mapping comment; require independent disposition for every pair before qualification | issue pending (1); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L24-L33] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L67-L88] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L138-L160] |
| Caller supplies inconsistent score or out-of-range probability | Dataclass has no validation; G0-01 must be applied to supplied records as well as registry defaults | issue pending (2); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L45-L66] |
| Empty summaries have no declared columns | Empty record comprehension becomes an empty DataFrame; check row count before selecting columns | Existing regression detection: `test_risk_analyzer.py::TestSummary::test_empty_risks_returns_empty_dataframe`; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L115-L129] [tests/unit/well_planning/test_risk_analyzer.py:L329-L333] |
| Registry documentation says 22 risks but the current list contains 21 | Count constructor calls at the pin; compare the 7 operational, 6 tactical and 8 strategic records rather than repeating the introductory count | #349; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L1-L3] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L15-L529] |

The issue search found inventory and packaging work (#349, #529) and general citation adoption (#361); no module-specific incident was supplied, and the newly identified gaps above are tracked by drafts rather than attributed to an undocumented incident. (Repository issues #349, #529 and #361, inspected 2026-10-15.)

## 7. Lessons log

Append entries; do not rewrite earlier lessons.

| Date | Reference | Lesson | Evidence | Pack change | Shared-log entry |
|---|---|---|---|---|---|
| 2026-10-15 | Initial pack | Retain the data-driven flag with every probability; a fallback float alone is not calibration evidence | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L260-L271] | Sections 2 and 6 distinguish fallback behavior | Pending, issue pending (1) |
| 2026-10-15 | Initial pack | Count incident rows separately from mapped associations before reporting totals | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L156-L166] | Sections 2, 5 and 6 distinguish quantities | Pending, issue pending (3) |

## 8. Ownership

Review assignment: calculations quality manager for interim data-pipeline coverage; deputy role: calculations deputy quality manager; producing role: module maintainer.
Engineering ambiguities, reference evidence and check failures go to the quality manager; cross-domain changes and unassigned responsibilities go to the maintainers.
Review status remains DRAFT until an independent provider reviews this pack; no clearance or signature is asserted.

## 9. Dependencies

| Dependency / consumer | Relationship | Evidence |
|---|---|---|
| `numpy`, `pandas`, `worldenergydata-core` | Declared package dependencies; runtime numerical clipping, random sampling and DataFrames | [packages/worldenergydata-well_planning/pyproject.toml:L26-L33] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L185-L190] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L277-L338] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L63-L83] |
| Built-in registry | Default source of risk records and baseline probabilities | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L29-L32] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L172-L180] |
| Caller-provided incident table | Upstream data boundary; no automatic incident download in `calibrate` | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L125-L166] |
| Caller-provided risk collection | Alternative upstream records for analysis | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L29-L32] |
| Summary/report consumers | Downstream Python callers receive DataFrames, strings and calibrated risk records | [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L85-L129] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L80-L94] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L240-L271] |

Inventory relationships are described from package metadata and imports; no upstream incident-loader adapter or downstream application integration is claimed by this pack. [packages/worldenergydata-well_planning/pyproject.toml:L26-L33] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/__init__.py:L3-L27]

### Implementation inventory and counted-family search

Inspected source: `digitalmodel`, `docs/registry/implementation-map.yaml`, branch `codex/implmap-work`, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; the map's own searched-code revision is `947fa50ff9a9e210de7e8f90e01b37add85c5954`. (Implementation map, schema version 1, header `revision` and `families` / `implementations` at that map commit.)

Inventory result: **0 module map families, 0 in-package implementation rows, 0 counted families**; the complete in-package map inventory is empty. The map holds 13 families for another repository and no implementation path within the header package. (Implementation map, schema version 1, `families` / `implementations`, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`.)
Counted-family grep: **NOT_APPLICABLE**, because no family has an in-package implementation row; therefore there is no ranked family or signal to apply or exclude. Inventory acceptance passes with an empty inventory; no engineering-method completeness is implied. (Implementation map, schema version 1, `families` / `implementations`, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`.)

Map follow-up, issue pending (6): add the section-3 families—authority classification/scoring, risk filtering/counting/reporting, incident-frequency calibration (including duration conversion, confidence and coverage), and synthetic incident generation—before counting them in a later map revision. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L12-L66] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L38-L129] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L125-L376]
The copied registry score computation belongs in the scoring inventory as well as the dataclass's score convention; it is listed here and in section 3 rather than hidden as a copy helper. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L249-L256] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L45-L61]

Additional repository search at the code pin included every tracked Python file, including `scripts/` and tests, for public class names, mapping keys, calibration accumulators and severity/probability multiplication; matched definitions were separated from test fixtures and namespace metadata. This is an auxiliary discovery search; no uncounted search changes the empty-inventory acceptance result.

## 10. Coverage and open items

### Read inventory

| Material read | Coverage / finding | Tracking |
|---|---|---|
| Package `__init__.py`, `risk_model.py`, `risk_registry.py`, `risk_analyzer.py`, `risk_calibrator.py` | All five Python files; includes synthetic helper and private duration/pair helpers | Complete; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/__init__.py:L3-L27] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L12-L66] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L15-L529] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L19-L129] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L22-L376] |
| Package README and package metadata | Packaging description and declared dependencies; metadata is not a qualification decision | [packages/worldenergydata-well_planning/README.md:L1-L8] [packages/worldenergydata-well_planning/pyproject.toml:L5-L33] |
| `tests/unit/well_planning/test_risk_model.py`, `test_risk_registry.py`, `test_risk_analyzer.py`, `test_risk_calibrator.py`, and empty test `__init__.py` | Entire module test directory; no separate package-local test directory found; all 120 tests recorded in section 4 | Complete; [tests/unit/well_planning/test_risk_model.py:L1-L209] [tests/unit/well_planning/test_risk_registry.py:L1-L135] [tests/unit/well_planning/test_risk_analyzer.py:L1-L337] [tests/unit/well_planning/test_risk_calibrator.py:L1-L257] |
| `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` | Historical inventory plan, not evidence of current module calculations | #349; [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L13-L24] |
| `docs/adr/0001-domain-package-split.md` | Historical package-split rationale; current package metadata takes precedence for dependencies | #529; [docs/adr/0001-domain-package-split.md:L30-L51] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` | Historical row names subdirectories not present in the current package; do not use as an algorithm inventory | #349; [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L185-L193] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml` | Historical module row and four-test-file count; current test count re-derived | #349; [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L848-L859] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` | Historical off-manifest discovery row; no present calibration-data provenance established by this row | #349; [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L73-L79] |

Read-inventory observations: no package docs existed at the pin; the five repository documents above were found by the module-name search under `docs/`; no routing registry exists at `docs/registry/module-routing.yaml` at the pin, so no registry entry is created.
Supporting guidance read: AQG r0 sections 9–10, module knowledge-pack lifecycle template and calculation-output citation contract; no named licensed standard was opened or adopted.

### Open items

The maintainer coordinates all items; the calculations quality manager decides qualification and check criteria.

| Item | Required follow-up / limitation | Issue |
|---|---|---|
| U1 | Engineering-use maturity remains unverified; reconcile current package metadata and historical discovery records; correct the registry introductory count | #349; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L1-L3] [packages/worldenergydata-well_planning/pyproject.toml:L5-L24] |
| U2 | Empirical calibration remains unverified; independently justify risk associations, baseline probabilities, weights, clipping, blending and exposure normalization; add a published or independently curated example with dataset revision, expected probability and tolerance; retain calibration evidence and shared-log entry | issue pending (1); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L22-L48] [tests/unit/well_planning/test_risk_calibrator.py:L25-L32] |
| Input quality | Add explicit exposure/pair/severity diagnostics and record validation before calibration or risk ranking | issue pending (2); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L141-L166] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L344-L376] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L45-L66] |
| Incident totals | Distinguish source incidents from mapped-risk associations and complete the lesson linkage | issue pending (3); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L156-L166] |
| Identifier hygiene | Replace the five identifying synthetic labels with neutral dataset identifiers; no identifying names are reproduced in this pack | issue pending (4); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L325-L338] |
| Copy isolation | Make mutable reference lists independent between original and calibrated records | issue pending (5); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L249-L257] |
| Map coverage | Add all section-3 method families to the implementation map before counting them in acceptance searches | issue pending (6); [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_model.py:L12-L66] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_analyzer.py:L38-L129] [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L125-L376] |
| Distribution boundary | Existing `**/*.md` package-data glob matches this pack; excluding documentation from wheels requires separate packaging work, without modifying the package configuration here | #529; [packages/worldenergydata-well_planning/pyproject.toml:L49-L55] |
| Calculation provenance | Apply citation sidecars when a future calculation adopts a standards-derived constant or formula; no standard-derived sidecar is asserted for this local heuristic | #361; [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_calibrator.py:L22-L48] (Repository issue #361, calculation-output citation adoption, inspected 2026-10-15.) |

No client-derived data, solver outputs or private sidecar values are included; the reproducible arithmetic fixture uses neutral incident categories and risk IDs only.
