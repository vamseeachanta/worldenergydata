# Drilling module knowledge pack

| Header | Value |
| --- | --- |
| Module | drilling |
| Repository | worldenergydata |
| Path | `packages/worldenergydata-drilling/src/worldenergydata/drilling` |
| Pack revision | 0, 2026-10-17 |
| Code revision | `b1394197a66f95d78615425b4e1ad4ff78bd9de2` |
| Analysis family | EC; Python calculations gate set, AQG r0 section 10 |
| Quality role | Calculations quality manager; data-pipeline coverage |
| Status | DRAFT; independent clearance pending |

## 1. Purpose and scope

The package exposes `BatchDrillingEconomics`, `BSEEBatchDetector`, `DrillCampaign` and `DrillingSite`. [packages/worldenergydata-drilling/src/worldenergydata/drilling/__init__.py:L6-L18]

The calculator evaluates power-law drilling durations, shared mobilization costs, a finite break-even search and campaign costs; the detector groups activity rows and fits a learning factor. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L62] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L68-L136] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L142-L228] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L38-L161]

The implementation is a stateless cost calculator and a DataFrame heuristic, rather than an optimization solver: cost methods count wells and sum position-based durations without searching schedules or consuming `ordered_wells()`. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L196] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L219-L228] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L62-L73]

The package metadata declares Alpha maturity and Python >=3.10; this declaration does not establish engineering validation. [packages/worldenergydata-drilling/pyproject.toml:L6-L22]

## 2. Inputs and outputs

### Inputs

| Input | Unit or convention | Enforced range; default | Evidence |
| --- | --- | --- | --- |
| `well_id`, `field_name`, `well_type` | Text identifiers/categories; no identities are reproduced here | Strings; required; no enum or uniqueness constraint | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L19-L36] |
| `location_coords` | Latitude, longitude in decimal degrees; datum, origin and sign validation are unspecified | Two floats; required; no bounds | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L21-L36] |
| `water_depth_ft`, `planned_md_ft` | ft; water depth and measured depth | Required floats; no positivity constraint | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L22-L36] |
| `bore_design`, `mpd_required` | Text, Boolean | `standard`, `False`; no design enum | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L25-L36] |
| `campaign_id`, `rig_name`, `wells`, `sequence` | Text IDs, site list, ordered ID list | IDs and wells required; sequence defaults to empty list; wells may be empty | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L54-L73] |
| `rig_day_rate_usd`, `mobilization_cost_usd` | USD/day, USD | Rate >0; mobilization >=0; required | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L45-L60] |
| `learning_curve_factor` | Dimensionless fraction | Campaign schema: >0 and <=1; default 0.85; direct calculator arguments lack that schema | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L50-L60] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L62] |
| `base_time_days`, `base_well_days`, `base_days_per_well`, `well_position` | days, one-based count | Required; direct calls do not enforce positive days or positive integer positions | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L62] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L96-L136] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L202-L228] |
| `mob_cost`, `n_wells_batch`, `n_wells_standalone` | USD, wells, wells | Batch denominator >0 checked; standalone denominator defaults to 1 but is unused | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L68-L90] |
| `discount_rate` | Annual fraction | Default 0.10; accepted but unused | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L23-L24] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L142-L196] |
| Activity DataFrame | `well_id`, `rig_name`, `field_name`, `spud_date`; dates parsed by pandas | Four columns required; window defaults to 12 months; no key/date null checks | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L22-L22] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L38-L75] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L167-L171] |
| Learning DataFrame | `well_position` (one-based), `days_to_drill` (days) | Cast to floats; retain positive pairs; substitute 0.85 for fewer than two usable pairs | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L122-L160] |

### Outputs

| Output | Unit, sign and meaning | Evidence |
| --- | --- | --- |
| `learning_curve_time` | days; first-position base or power-law duration | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L55-L62] |
| `mobilization_savings` | USD/well; allocated cost, not the difference from standalone | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L74-L90] |
| `break_even_n_wells` | wells; first strict cost reduction in 1..200; fallback 1 is ambiguous | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L122-L136] |
| `batch_npv`, `standalone_npv`, `batch_savings` | USD; cost totals without negation, savings = standalone minus batch; no discounting | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L196] |
| `campaign_total_cost` | USD; one mobilization plus sum of duration times rate | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L219-L228] |
| Detected batches | `batch_id`, grouping IDs, `well_ids`, `batch_size` (wells), start/end timestamps, `span_days` (integer days) | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L97-L120] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L173-L187] |
| Fitted factor | Dimensionless; clipped to [0.5,1.0], despite docstring's open lower bound | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L134-L160] |
| `ordered_wells` | Site list; empty sequence preserves insertion order, unknown IDs are omitted | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L62-L73] |

No phase convention is used by the cost or date-grouping calculations; `location_coords` is stored by the model and is not read by these methods. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L29-L36] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L255] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L38-L120]

These entry points consume in-memory objects and return scalars, dictionaries, lists or DataFrames; their bodies contain no file reader, serializer or cache writer. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L255] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L38-L187] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L62-L73]

## 3. Method and governing standards

| Method | Implemented calculation and basis | Evidence |
| --- | --- | --- |
| Duration | `T(N)=T1*N**(log(LC)/log(2))`; N<=1 returns T1. The docstring attributes the law to Wright (1936) and calls it cumulative average, while callers sum it as individual durations. | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L44-L62] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L124-L128] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L224-L228] |
| Mobilization allocation | `mob_cost/n_wells_batch`; rejects nonpositive batch count | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L68-L90] |
| Break-even | First N with `mob + rate*sum(T(i)) < N*(mob+rate*T1)` over 1..200; returns 1 if none found | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L122-L136] |
| Cost comparison | Base duration from average depths; standalone = N*(mob+rate*base); batch = mob+rate*sum(T(i)); outputs are undiscounted | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L196] |
| Depth heuristic | `max(mean_MD/400 + mean_water_depth/2000 + 10, 30)` days; empty wells return 60 days; the prose instead describes a 20-day fixed term | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L234-L255] |
| Campaign total | One mobilization plus rate times sum of supplied-base power-law durations | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L202-L228] |
| Grouping | Sort by spud date, group by rig and field, anchor each next unassigned row, include rows within `months*30.44` days; singleton batches are allowed | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L45-L47] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L66-L120] |
| Learning fit | Least-squares slope of log(days) against log(position); return `2**slope` clipped to [0.5,1.0]; nonpositive pairs are filtered | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L138-L161] |

UNVERIFIED: the original Wright publication, individual-versus-cumulative-average interpretation, and empirical basis of the depth heuristic and default factors have not been independently established; issue pending (1). [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L44-L53] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L234-L255] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L134-L160]

No governing engineering standard or `Citation` sidecar is declared in these calculation/model definitions; standards-derived certification is not established by these methods. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L1-L255] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L1-L187] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L1-L73]

## 4. Validated worked examples

Validated examples: **0**; regression examples: **8** below. These tests use local fixture inputs and invariants rather than a cited independent engineering benchmark; the mobilization test derives its expected allocation from another call to the same method. [tests/drilling/test_batch_economics.py:L22-L43] [tests/drilling/test_batch_economics.py:L98-L105] [tests/drilling/test_batch_economics.py:L370-L380]

| ID | Regression case | Inputs, expected value and tolerance | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 | Position 1 | 60 days, LC 0.85; expected 60 days; relative tolerance 1e-9 (test assertion) | `tests/drilling/test_batch_economics.py::TestLearningCurve::test_learning_curve_position_1_unchanged` | PASS at the code pin in both comparison runs; [tests/drilling/test_batch_economics.py:L65-L71] |
| R2 | No learning | 60 days, LC 1; positions 1..4 each 60 days; relative tolerance 1e-9 | `tests/drilling/test_batch_economics.py::TestLearningCurve::test_learning_curve_factor_1_no_improvement` | PASS at the code pin in both comparison runs; [tests/drilling/test_batch_economics.py:L79-L86] |
| R3 | Shared mobilization | 20,000,000 USD; 2 wells; expected standalone allocation /2 USD/well; relative tolerance 1e-9 | `tests/drilling/test_batch_economics.py::TestMobilizationSavings::test_mobilization_savings_2_wells` | PASS at the code pin in both comparison runs; [tests/drilling/test_batch_economics.py:L98-L105] |
| R4 | Break-even type | 20,000,000 USD mobilization; 350,000 USD/day; 60 days; expected integer >=1 well; no upper-bound oracle | `tests/drilling/test_batch_economics.py::TestBreakEven::test_break_even_positive_integer` | PASS at the code pin in both comparison runs; [tests/drilling/test_batch_economics.py:L160-L168] |
| R5 | Single-well comparison | Fixture campaign with 1 well; batch equals standalone USD cost; relative tolerance 1e-6 | `tests/drilling/test_batch_economics.py::TestBatchVsStandaloneNPV::test_single_well_no_mob_savings` | PASS at the code pin in both comparison runs; [tests/drilling/test_batch_economics.py:L198-L207] |
| R6 | Campaign total sign | Fixture campaign with 3 wells, base 60 days; expected >0 USD; no absolute-cost oracle | `tests/drilling/test_batch_economics.py::TestCampaignTotalCost::test_campaign_total_cost_positive` | PASS at the code pin in both comparison runs; [tests/drilling/test_batch_economics.py:L240-L244] |
| R7 | Learning fit range | Positions [1,2,3,4], durations [60,52,48,45] days; expected float >0.5 and <=1.0; no fitted-value oracle | `tests/drilling/test_batch_economics.py::TestBSEEBatchDetector::test_fit_learning_curve_returns_float` | PASS at the code pin in both comparison runs; [tests/drilling/test_batch_economics.py:L370-L380] |
| R8 | Separate grouping keys | Two rows with distinct rig IDs; every returned batch has 1 well; assertion permits empty output | `tests/drilling/test_batch_economics.py::TestBSEEBatchDetector::test_detect_batches_separate_rigs` | PASS at the code pin in both comparison runs; [tests/drilling/test_batch_economics.py:L302-L327] |

Offline observations on 2026-10-17, Python 3.11.15, at the header code pin: baseline 24 run / 24 passed / 0 failed / 0 skipped / 0 NOT_RUN; after 24 / 24 / 0 / 0 / 0; changed node outcomes 0. [tests/drilling/test_batch_economics.py:L51-L380] [tests/unit/drilling/test_smoke.py:L8-L19]

Both comparison commands used `uv run python -m pytest tests/drilling tests/unit/drilling -q -rA -p no:cacheprovider --allow-existing-tree-changes`, with separate scratch basetemp, coverage-data and coverage-report destinations; each exited 0 on the uncommitted tree. The documented preservation mode hashes existing changed files and rejects altered bytes or additional changes. [docs/development/index.md:L48-L61] [tests/conftest.py:L410-L450]

The initial ordinary invocation passed all 24 test nodes but exited 1 because the tree guard rejected this newly drafted pack; it is not counted as a successful comparison command. Test logs and input digests require durable review attachment before clearance, issue pending (7). [tests/conftest.py:L410-L450]

Inputs are constructed in the test file rather than an external input file; fixture identities are deliberately omitted here. [tests/drilling/test_batch_economics.py:L22-L43] [tests/drilling/test_batch_economics.py:L302-L319]

## 5. QA gates

Applicability follows AQG r0 section 10, Python calculations, with G5 from section 9; executable criteria below are pack checks, not a clearance signature.

| Gate | Applicability | Module-specific check IDs |
| --- | --- | --- |
| G0 | Applicable: schema, units and provenance | C0, C1 |
| G1 | Applicable: Python imports and offline tests; no solver load route | C2, C3 |
| G2 | Applicable: hand calculation against computed values | C4, C5 |
| G3 | NOT_APPLICABLE: no time-domain simulation in these methods | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L228] |
| G4 | NOT_APPLICABLE: no diffraction mesh or hydrodynamic calculation | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L228] |
| G5 | Applicable: evidence and limitations for any issued calculation | C6 |

| ID | Execution and evidence | Numeric pass criterion and unit | Gate |
| --- | --- | --- | --- |
| C0 | Construct `DrillCampaign` with rate 0, mobilization -1 and factor 0 separately; require Pydantic rejection; repeat with valid inputs. Source constraints: [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L54-L60] | 3/3 invalid campaigns rejected; 1/1 valid campaign accepted (campaigns); observed PASS: 3 rejected and 1 accepted | G0 |
| C1 | Verify method-table units against schema/docstrings and recompute SHA-256 of the 5 package Python files from the code pin before each future use. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L19-L60] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L80-L86] | 0 unit-label mismatches; 5/5 input file digests match (files), observed PASS; unknown datum and coefficient basis remain disclosed | G0 |
| C2 | `tests/unit/drilling/test_smoke.py::test_package_imports` and `tests/unit/drilling/test_smoke.py::test_public_api_exported`; import through the installed member. [tests/unit/drilling/test_smoke.py:L5-L19] | 2/2 tests pass; 4/4 public exports resolve (symbols); observed PASS in both comparisons | G1 |
| C3 | Run `tests/drilling/` and `tests/unit/drilling/` in the project environment; keep node-level outcomes and compare before/after. [tests/drilling/test_batch_economics.py:L51-L380] [tests/unit/drilling/test_smoke.py:L8-L19] | 24/24 tests pass; 0 changed outcomes (tests); observed PASS in both comparisons | G1 |
| C4 | Independently calculate `20_000_000/2` then call `mobilization_savings(20_000_000,2)`; compare with 10,000,000 USD/well; retain the hand result and residual. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L68-L90] | Absolute difference <=0.01 USD/well; observed PASS against 10,000,000 USD/well | G2 |
| C5 | From the power law at N=2, compare `learning_curve_time(60,2,0.85)` against `60*0.85=51` days; retain residual. This checks the formula implementation, not its empirical interpretation. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L44-L62] | Absolute difference <=1e-9 days; observed PASS against 51 days | G2 |
| C6 | Resolve every pack source range at the pin, map all 8 examples to collected nodes, and attach before/after results plus the section-6 dispositions. | 0 broken ranges; 8/8 nodes resolve; 0 omitted sweep entries (entries); independent signature required before clearance under AQG r0 sections 9 and 11 | G5 |

C0, C4 and C5 are reproducible directly with public constructors and the explicit inputs above; their hand-check inputs do not contain operational records. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L54-L60] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L68-L90] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L62]

## 6. Known failure modes and pitfalls

sweep: 49 found

The inventory below includes benign bookkeeping/default sites as well as failure risks, so a match is not automatically a defect; each row is tied to its pinned code. The scan also found no `except` handler, `return None`, `return []`, `return {}`, epoch default or cache writer in the five package files. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L1-L255] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L1-L187] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L1-L73]

Commands run on the package Python files, with the package path from the header substituted for `$PACKAGE`:

```bash
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|0\.05|0\.85|0\.10|60\.0|30\.0|float\(|int\(|astype|30\.44|400|2000|groupby|return 1|default|cache' "$PACKAGE" --glob '*.py'
rg -n 'return|Field|log|polyfit|mask|sum|depth|days|usd|coords|sequence|well_map' "$PACKAGE" --glob '*.py'
```

| # | Symptom or sweep site | Cause or disposition | Existing detection | Tracking and date | Pinned source |
| --- | --- | --- | --- | --- | --- |
| 1 | Empty activity input returns schema-only output | `detect_batches` returns `_empty_result()` after column validation; empty is not proof of no campaigns | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L61-L64] |
| 2 | Spud date interpretation depends on pandas parsing | No format, timezone or missing-date validation is supplied | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L66-L68] |
| 3 | Month boundary differs from calendar months | Each month is assumed to be 30.44 days; nonpositive window is not rejected | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L70-L70] |
| 4 | Rows with null rig or field can disappear | `groupby` uses its default missing-key behavior; no input/output reconciliation | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L75-L76] |
| 5 | Missing spud dates can be omitted | Comparison of NaT with window end admits no members; index still advances | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L85-L97] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L115-L118] |
| 6 | Assigned-row continue | Already-assigned rows are skipped; this is intended de-duplication, not an error handler | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L81-L83] |
| 7 | No emitted batches looks like an empty source | Second empty-result branch carries no rejection reason | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L117-L118] |
| 8 | Fitted value replaced with assumed factor | Empty or one-row fit logs a warning and returns 0.85 | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L138-L140] |
| 9 | External position strings are cast directly | `astype(float)` has no locale/thousands normalization | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L142-L142] |
| 10 | External duration strings are cast directly | `astype(float)` has no locale/thousands normalization | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L143-L143] |
| 11 | Nonpositive training records disappear | Mask excludes position<=0 or time<=0 without reporting excluded count | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L145-L146] |
| 12 | Filtered fit substitutes 0.85 silently | Fewer than two retained pairs return a default without the first branch warning | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L147-L148] |
| 13 | Out-of-range fitted trend becomes a boundary factor | `2**slope` is clipped to [0.5,1.0]; lower bound conflicts with documented (0.5,1.0] | C3/R7 checks range only; no detection check exists for clipping | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L134-L160] [tests/drilling/test_batch_economics.py:L370-L380] |
| 14 | Nonfinite or repeated training positions are not rejected | Positive mask and polyfit have no finite/distinct-position preflight | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L142-L160] |
| 15 | Zero batch counter | Counter initializes to 0 then increments before ID emission; bookkeeping, not an assumed measurement | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L72-L74] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L97-L104] |
| 16 | Zero row index | Index initializes to 0 and advances even without members; bookkeeping | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L79-L83] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L115-L115] |
| 17 | Implicit bore-design default | `standard` is accepted without an enum or qualification | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L29-L36] |
| 18 | Implicit pressure-management default | `mpd_required=False` can conceal missing source classification | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L29-L36] |
| 19 | Default empty sequence | Model supplies an empty list, and ordered_wells falls back to insertion order | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L59-L73] |
| 20 | Duplicate well IDs overwrite earlier entries | Dictionary construction retains only the last site for a repeated ID | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L72-L73] |
| 21 | Unknown or incomplete sequence omits wells | Comprehension filters unknown IDs and does not enforce permutation completeness | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L72-L73] |
| 22 | Unqualified campaign factor | Model default is 0.85 without evidence of campaign-specific calibration | C0 validates boundaries only; no detection check exists for calibration | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L50-L60] |
| 23 | Unbounded site dimensions/coordinates | Floats lack positivity, finite-value and geographic bounds | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L29-L36] |
| 24 | Invalid positions treated as the first well | Position<=1, including nonpositive values, returns base days | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L58-L62] |
| 25 | Float coercion of base duration | `float(base_time_days)` accepts a convertible numeric input without unit metadata; this is not a text parser | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L58-L59] |
| 26 | Float coercion of duration result | Derived arithmetic is cast to float, with no finite-value check; not external-text conversion | C5 covers one valid value only; no detection check exists for nonfinite outputs | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L61-L62] |
| 27 | Calculator default factor in duration | Default 0.85 is applied without campaign-specific evidence | C5 checks arithmetic only; no detection check exists for calibration | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L62] |
| 28 | Calculator default factor in break-even | Default 0.85 is applied without campaign-specific evidence | no detection check exists | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L96-L102] |
| 29 | Standalone denominator ignored | `n_wells_standalone=1` is accepted but never used | C3/R3 covers batch division only; no detection check exists for the unused argument | issue pending (4); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L68-L90] |
| 30 | Break-even sentinel resembles success | After 200 candidates, fallback 1 does not distinguish no solution from a result | C3/R4 checks positivity only; no detection check exists for the sentinel | issue pending (4); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L122-L136] [tests/drilling/test_batch_economics.py:L160-L168] |
| 31 | Discount rate ignored | Default 0.10 and any supplied rate have no role in the returned costs | no detection check exists | issue pending (4); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L23-L24] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L142-L196] |
| 32 | Unnegated totals contradict negative-cash-flow prose | Returned NPV keys contain cost totals with no discount schedule | C3/R5 checks equality only; no detection check exists for sign/basis | issue pending (4); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L147-L168] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L180-L196] |
| 33 | Empty campaign still incurs mobilization in comparison | N=0 gives standalone zero and batch=mob, after a default base-duration lookup | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L195] |
| 34 | Empty campaign still incurs mobilization in total cost | Empty duration sum is zero; return is mobilization | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L219-L228] |
| 35 | Empty campaign base duration is assumed | `_estimate_base_well_days` returns 60.0 days | no detection check exists | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L247-L248] |
| 36 | Measured-depth conversion is an empirical assumption | Average measured depth divided by 400 ft/day | no detection check exists | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L250-L254] |
| 37 | Water-depth conversion is an empirical assumption | Average water depth divided by 2000 ft/day | no detection check exists | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L251-L254] |
| 38 | Fixed duration differs from prose | Calculation adds 10 days; docstring describes 20 days | no detection check exists | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L237-L239] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L253-L254] |
| 39 | Low estimated duration is silently floored | `max(estimated,30.0)` forces at least 30 days | no detection check exists | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L254-L255] |
| 40 | Cumulative-average versus individual-time ambiguity | A cumulative-average formula is summed as per-well values | C5 tests formula only; no aggregation-reference check exists | issue pending (1); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L44-L56] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L224-L228] |
| 41 | Invalid direct calculator inputs bypass campaign schema | Batch count has a guard, but rate, duration and LC arguments are otherwise unconstrained | C0 covers model only; no detection check exists for direct-call validation | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L62] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L68-L90] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L96-L136] |
| 42 | Cost methods ignore sequence | They use well count and average depths rather than ordered wells | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L188] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L219-L228] |
| 43 | Break-even tests have misleading prose and weak oracles | One test permits any positive count despite its equality narrative; another gives both costs without an independent economic reference | C3/R4; no detection check exists against a reference value | issue pending (4); 2026-10-17 | [tests/drilling/test_batch_economics.py:L133-L168] |
| 44 | Fractional-day batch spans are truncated | Timestamp difference is reported with .days, so sub-day spans become integer days | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L109-L111] |
| 45 | Repeated activity rows count as additional wells | batch_size=len(members) and well_ids retains every row; no well-ID de-duplication | no detection check exists | issue pending (2); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L97-L111] |
| 46 | Currency labels are assumed rather than converted | Methods accept plain numbers documented as USD and USD/day; no currency metadata accompanies them | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L80-L90] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L45-L60] |
| 47 | Duration labels are assumed rather than converted | Base durations are plain floats documented in days, without a unit conversion boundary | C5 checks one day-based input only; no detection check exists for unit mismatch | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L49-L62] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L212-L228] |
| 48 | Geometry labels are assumed rather than converted | Site depths are documented as feet and coordinates as degrees, without datum or unit-tag validation | no detection check exists | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L19-L36] |
| 49 | Financial input finiteness is unqualified | Campaign financial fields declare lower bounds but no finite-value constraint | C0 covers lower bounds only; no detection check exists for finiteness | issue pending (3); 2026-10-17 | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L54-L60] |

The rows above identify code paths and coverage limitations; no historical incident is attributed. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L1-L255] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L1-L187] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L1-L73]

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-17 | Initial pack revision | Preserve undiscounted-cost semantics and distinguish regression from independent qualification | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L196] | Sections 3–6 | Pending maintainer registration; issue pending (7) |

## 8. Ownership

The calculations quality manager will review the data-pipeline pack, with a calculations deputy to be appointed; the producing role is module documentation, and unresolved engineering criteria go to the quality manager while scope goes to the maintainer, under AQG r0 sections 10–11. Appointment and independent clearance remain pending; issue pending (7).

## 9. Dependencies and implementation inventory

### Runtime and consumers

| Dependency or interface | Inventory and limits | Evidence |
| --- | --- | --- |
| NumPy, pandas, Pydantic, core namespace | Declared member dependencies; no solver version or binary is declared | [packages/worldenergydata-drilling/pyproject.toml:L30-L35] |
| Public API consumers | The package root and batch subpackage re-export the same four objects; tests import the public and implementation paths | [packages/worldenergydata-drilling/src/worldenergydata/drilling/__init__.py:L6-L18] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/__init__.py:L6-L17] [tests/drilling/test_batch_economics.py:L11-L15] [tests/unit/drilling/test_smoke.py:L5-L19] |
| Activity source | Detector takes an already-normalized in-memory DataFrame; it does not download BSEE data or join upstream records | [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L38-L75] |
| Historical data and solver datasets | No operational dataset is qualified by the local fixture tests; external record provenance is not tested | [tests/drilling/test_batch_economics.py:L22-L43] [tests/drilling/test_batch_economics.py:L261-L300] |

### Implementation map

Map source: `digitalmodel`, `docs/registry/implementation-map.yaml`, branch `codex/implmap-work`, map-file commit `3256bab95f84da3d9fadce8d5dcf8458d66d1eb4`; its embedded data revision is `270c8759c374b67a7f032953e7fcdb14e0224461`.

Inventory at that map-file commit: **0 in-package implementation rows; 0 module map families; 0 counted families**. No path in the map lies under the package in this header. A8 inventory is empty; counted-family grep is `NOT_APPLICABLE` because the map has no in-package rows. Further second implementations counted for A8: 0; this is not a claim that all methods are mapped.

Map follow-up, issue pending (5): add the duration law, mobilization allocation, break-even comparison, campaign cost comparison/total, anchored time-window grouping and log-space learning fit before they can become counted families. The implementations in this package are already described in section 3. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L228] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L38-L161]

### Whole-repository duplicate discovery

At the code pin, tracked Python files across the whole repository, including `scripts/`, were searched with the following separate queries; retained results were the package definitions, re-exports and local tests, with no further computational definition for these named methods. This search is narrower than a proof of algorithmic uniqueness; new candidates require semantic classification. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L38-L228] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L38-L161] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L15-L73]

```bash
git grep -n -E 'def (learning_curve_time|mobilization_savings|break_even_n_wells|batch_vs_standalone_npv|campaign_total_cost|detect_batches|fit_learning_curve)|class (DrillCampaign|DrillingSite)|Wright|log\(lc_factor\)' "$PIN" -- '*.py'
git grep -l -i -E 'learning_curve|learning.?rate|mobilization_savings|batch_cost' "$PIN" -- '*.py'
```

## 10. Coverage and open items

### Read coverage

| Files read at the code pin | Coverage |
| --- | --- |
| `__init__.py` and `batch_economics/__init__.py` within the header package | All exports [packages/worldenergydata-drilling/src/worldenergydata/drilling/__init__.py:L1-L18] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/__init__.py:L1-L17] |
| `batch_economics/models.py` | Complete [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L1-L73] |
| `batch_economics/economics.py` | Complete [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L1-L255] |
| `batch_economics/bsee_batch_detector.py` | Complete [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L1-L187] |
| Member README and package metadata | Complete README and packaging/dependency definitions [packages/worldenergydata-drilling/README.md:L1-L8] [packages/worldenergydata-drilling/pyproject.toml:L1-L57] |
| `tests/drilling/test_batch_economics.py`, `tests/drilling/__init__.py`, `tests/unit/drilling/test_smoke.py`, `tests/unit/drilling/__init__.py` | Both test directories; 22 economics/detector cases plus 2 smoke cases [tests/drilling/test_batch_economics.py:L51-L380] [tests/unit/drilling/test_smoke.py:L8-L19] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` and its YAML companion | Discovery documents identify a historical empty package and a separate historical planning path; their old counts are not used here [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L84-L93] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L736-L752] |

Discovery used `rg` for the package/import spelling and `batch_economics` across documentation and tests; the historical planning references occur in the two readiness files. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L93-L93] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L845-L854]

There is no `docs/registry/module-routing.yaml` at the code pin, so no registry edit is included; the implementation and header path above are the pack's scope rather than a new routing domain.

### Tracked gaps

| Item | Evidence and limit | Responsible role and tracking |
| --- | --- | --- |
| Method provenance and independent validation | Section-3 UNVERIFIED claim; no independent section-4 reference; depth terms disagree with prose | Maintainer; issue pending (1) [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L44-L62] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L234-L255] |
| Data loss, fit defaults and parser contracts | Section-6 detector rows; no rejected-record accounting or locale contract | Maintainer; issue pending (2) [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/bsee_batch_detector.py:L61-L160] |
| Input, sequence and empty-campaign contracts | Section-6 model/direct-call rows; no completeness or uniqueness checks | Maintainer; issue pending (3) [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L29-L73] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L170-L228] |
| Cost and break-even semantics | Unused discount/standalone arguments, fallback 1 and weak break-even test oracles | Maintainer; issue pending (4) [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L68-L196] [tests/drilling/test_batch_economics.py:L133-L168] |
| Map coverage | No in-package map rows at the section-9 map pin; all section-3 method families need enrollment | Maintainer; issue pending (5) |
| Documentation and distribution | Historical readiness text describes an empty domain; the existing nested-Markdown package-data glob matches the new pack, so wheel exclusion is not established; packaging is unchanged | Maintainer; issue pending (6) [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L84-L84] [packages/worldenergydata-drilling/pyproject.toml:L56-L57] |
| Clearance and evidence retention | A different-provider clearance, deputy appointment, durable test-evidence attachment and shared-log registration remain outstanding under AQG r0 sections 9–11 | Maintainer; issue pending (7) |

The calc-citation contract was read as procedural guidance; no licensed standard text or operational source records are reproduced. Standards provenance remains the section-3 limitation. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L44-L53] [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/models.py:L19-L36]
