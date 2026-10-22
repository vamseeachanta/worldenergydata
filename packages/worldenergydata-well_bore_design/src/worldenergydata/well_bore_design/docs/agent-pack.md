# Well bore design module knowledge pack

| Header | Value |
| --- | --- |
| Module | `well_bore_design` |
| Repository | `worldenergydata` |
| Path | `packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design` |
| Pack revision | 2, 2026-10-22 |
| Historical code revision | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` |
| Analysis family | EC; Python calculations gate set, AQG r0, section 10 |
| Quality role | Calculations quality manager; deputy assignment open |
| Status | DRAFT; independent clearance pending |

## 1. Purpose and scope

The current implementation estimates steady laminar Bingham annular loss using a sourced slot approximation, takes explicit mud rheology and geometry, and checks both pore and fracture bounds. Recommendation categories are normalized and every matrix envelope is checked. These are estimates with stated applicability limits, not design qualification.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-15 | Initial module knowledge pack; qualification gaps recorded. |
| 1 | 2026-10-16 | Failure inventory expanded after the hydraulic bound and selection checks exposed undocumented limitations. |
| 2 | 2026-10-22 | Replace the understated annular loss and implicit inputs; detect category and envelope failures. |

### Current implementation update, revision 2

- Method: the public 2025 annular-flow paper, Appendix A1, A29–A30, reduced to Bingham behavior with `N=1`, gives `v=G*h²/(12*mu)*(1-a)²*(1+a/2)`, where `a=2*tau_y/(G*h)` and `h=(D_h-D_p)/2`. A4/A6/A9 give the yield floor `YP/(3*(D_h-D_p))` psi/100 ft. Unit conversions use NIST SP 811 (2008), Appendix B.8.
- Inputs: rheology and a geometry mapping are required by `compare_bore_types`; `pressure_window_check` requires PV, YP, hole/pipe diameters and caller-selected `minimum_window_ppg`. It reports the rheology used and a laminar-model caveat. Missing inputs raise `TypeError`; invalid physical inputs raise `ValueError`. No implicit numerical basis replaces missing inputs.
- Selection: case, surrounding whitespace and completion separators are normalized. The preferred candidate is checked against depth, flow and well-type envelopes. An eligible alternative is selected when available; otherwise an explicit envelope caveat is returned. Unknown categories produce a named caveat and `evaluation_status="NOT_EVALUATED"`.

| Finding | Current detection nodes |
| --- | --- |
| #1288 SF1: loss below yield floor | `tests/unit/well_bore_design/test_hydraulic_regressions.py::test_annular_yield_floor`; `tests/unit/well_bore_design/test_hydraulic_regressions.py::test_laminar_bingham_worked_case`; `tests/unit/well_bore_design/test_hydraulic_regressions.py::test_newtonian_limit_without_yield` |
| #1288 SF2: fixed rheology | `tests/unit/well_bore_design/test_hydraulic_regressions.py::test_pressure_window_uses_actual_rheology`; `tests/unit/well_bore_design/test_selection_regressions.py::test_missing_rheology_or_geometry_is_required` |
| #1288 SF3: ignored envelopes | `tests/unit/well_bore_design/test_selection_regressions.py::test_selection_respects_all_matrix_envelopes` |
| #1288 SF4: category fall-through | `tests/unit/well_bore_design/test_selection_regressions.py::test_case_and_completion_separators_normalized`; `tests/unit/well_bore_design/test_selection_regressions.py::test_unknown_category_has_explicit_caveat` |
| Invalid loss inputs and missing pore-bound check | `tests/unit/well_bore_design/test_hydraulic_regressions.py::test_each_annular_input_must_be_finite`; `tests/unit/well_bore_design/test_hydraulic_regressions.py::test_invalid_pressure_loss_input_refused`; `tests/unit/well_bore_design/test_hydraulic_regressions.py::test_zero_flow_has_no_circulating_loss`; `tests/unit/well_bore_design/test_hydraulic_regressions.py::test_pressure_below_pore_is_incompatible` |

Remaining limits: the slot approximation assumes laminar flow, concentric stationary walls and no cuttings; turbulent loss and automatic regime selection are not evaluated. The single hydraulic depth must represent both length and TVD, limiting the window interface to a vertical uniform section. The selection matrix, cleaning heuristic, cost/risk thresholds, stored-profile consistency and empty-profile behavior remain unqualified. A declared compatible estimate does not settle those limitations. The schemas and profile calculations are unchanged.

Sources: [annular-flow paper (2025; corrected 2026), Appendix A](https://doi.org/10.1007/s13202-024-01919-z); [NIST SP 811 (2008), Appendix B.8](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf). The reproducible hand calculation and refusal example are in [the worked example](../../../../../../docs/examples/annular_pressure_screening.md).

### Historical inventory boundary

Sections 2–10 below retain the inventory, citations, execution records and open
limits at the historical code revision. Findings corrected by the current update
are historical evidence; the current contracts and detection nodes above supersede
those earlier behavior statements and test counts. Remaining limits are retained.


## 2. Inputs and outputs

### Inputs

| Surface / field | Unit | Allowed range / default | Source and evidence |
| --- | --- | --- | --- |
| `WellBoreDesign.well_id`, `bore_type` | identifier; enum | Required; no constructor cross-check against production bit size | Caller; use anonymous dataset IDs. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L41-L76] |
| `total_depth_m`, `water_depth_m`, `sections` | m; section records | Required depths; sections default empty; no range or continuity validator | Caller; sections hold casing, bit size in inches and depth endpoints in metres. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L51-L63] |
| Surface, intermediate, production bit sizes | in | Each defaults 0.0; classification helper uses <8.5 slim, >12.25 large, otherwise standard | Caller; enum thresholds are code conventions. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L27-L38] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L65-L68] |
| Mud weight, maximum and minimum weights | ppg | 9.0, 0.0 and 0.0 defaults respectively; 0.0 limit acts as unset in `pressure_window_ppg` | Caller. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L70-L82] |
| `formation_type`, `notes` | text | Defaults `mixed`, empty string; descriptive comments do not enforce categories | Caller. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L75-L76] |
| `EcdProfile` | m, ppg, gpm, ft/s | All arrays, weights, flow, minimum margin and bottleneck depth required; bottleneck may be `None`; notes default empty | Caller; lists and derived fields are stored without length or consistency checks. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L89-L120] |
| `annular_velocity_fps(Q, hole_od_in, pipe_od_in)` | gpm, in, in | Required; squared diameter difference must be >0; sign and finiteness otherwise unchecked | Caller. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L30-L48] |
| `pressure_loss_psi_per_100ft` | gpm, ppg, cP, lbf/100 ft², in, in | All required; hydraulic diameter must be >0; no positive-viscosity or finite-value validator | Caller. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L54-L100] |
| `ecd_ppg(mud_weight_ppg, annular_pressure_loss_psi, depth_ft)` | ppg, psi, ft | All required; depth must be >0; no nonnegative-loss guard | Caller. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L106-L120] |
| `hole_cleaning_index(annular_velocity_fps, mud_weight_ppg, cutting_density_ppg)` | ft/s, ppg, ppg | First two required; cutting density default 21.7 and must be >0 | Caller. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L126-L139] |
| `compare_bore_types` | gpm, ppg, ft; cP; lbf/100 ft² | Flow, weight, depth required; viscosity 20.0 and yield point 15.0 defaults | Caller; fixed hole/pipe OD pairs: 6.0/3.5, 8.5/5.0, 12.25/5.5 in. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L10-L15] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L145-L178] |
| `recommend` | type; m; ppg; bopd; degrees; category | First four required; deviation 0.0 and completion `simple` defaults; documented categories are not runtime validators | Caller; degrees from vertical. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L105-L146] |
| `pressure_window_check` | enum, ppg, ppg, ppg, gpm, ft | Bore type, mud weight, fracture gradient, pore pressure, flow and depth required | Caller; uses default rheology from comparison. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L178-L220] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L145-L152] |

Depths and diameters are scalars; these dataclasses and functions contain no coordinate transform, spatial origin or phase convention, and no file reader/writer is implemented in these paths. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L41-L120] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L30-L188] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L105-L294]

### Outputs

| Output | Unit / allowed result / default | Source and evidence |
| --- | --- | --- |
| `bore_type_from_bit_size` | One of three `BoreType` values; no output default | Strict outer inequalities leave both endpoints standard. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L27-L38] |
| `WellBoreDesign.pressure_window_ppg`, `is_offshore` | ppg; bool; computed | Maximum minus minimum, or 0.0 if either unset; offshore means water depth >0 m. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L78-L86] |
| `EcdProfile.is_safe_at_all_depths`, `safe_depth_fraction` | bool; fraction of points, unit 1 | Margins must be strictly >0; fraction is point-count weighted, with empty fraction 0.0; empty `all` is a pitfall in section 6. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L111-L120] |
| Hydraulic scalars | ft/s; psi/100 ft; ppg; cleaning index | Scalar returns; pressure loss clamped at 0.0; index formula retains velocity units because densities cancel. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L43-L48] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L89-L100] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L118-L139] |
| Comparison dictionary | Three bore keys, five fields each | `ecd_ppg` (ppg), `annular_velocity_fps` (ft/s), `pressure_loss_psi_per_100ft` (psi/100 ft), `hole_cleaning_index` (velocity-scaled index), `total_pressure_loss_psi` (psi). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L159-L188] |
| `BoreTypeRecommendation` | enum; text; bools; relative factor (unit 1); risk category; caveat list | `recommended`, `rationale`, compatibility, cleaning, cost and risk required; caveats default empty; factor is relative to standard. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L69-L80] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L168-L175] |
| Pressure-window dictionary | bool; ppg; category | Compatibility uses unrounded margins; `margin_ppg`, `ecd_ppg`, `available_window_ppg` rounded to four decimal places; `limiting_factor` is a string. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L197-L220] |

## 3. Method and governing standards

The following are implemented formulas and policies, rather than a claim of conformity to a governing standard; the hydraulic docstring names an author group without edition, page or equation, and the selection constants are local tables. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L63-L100] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L17-L65]

| Method | Implemented rule and reference boundary |
| --- | --- |
| Classification and schema metrics | `bore_type_from_bit_size` applies the two strict outer boundaries; `pressure_window_ppg` subtracts limits unless unset; profile safety uses strict positive margin and counts points. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L27-L38] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L78-L86] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L111-L120] |
| Annular velocity | `AV = 0.408 Q / (D_h² - D_p²)`; Q in gpm, diameters in inches, output labelled ft/s. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L30-L48] |
| Pressure loss | Let `D = hole_od_in - pipe_od_in`, `V = 60 AV` in ft/min, `PV = plastic_viscosity_cp`, `YP = yield_point_lbf_100ft2`, `MW = mud_weight_ppg`; `Re = 109 MW V D / (PV + 6 YP D / V)` for V>0, otherwise 0. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L74-L87] |
| Laminar branch | For `Re < 2100`, loss = `PV V / (300 D²) + YP / (225 D)`; the implementation uses V in ft/min, while the displayed docstring uses AV without specifying that conversion. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L63-L93] |
| Turbulent branch | For `Re >= 2100`, `f = 0.046 / Re**0.2`, loss = `f MW V² / (21.1 D 1000)`; returned loss is `max(loss, 0.0)`, labelled psi/100 ft. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L89-L100] |
| ECD and comparison | `ECD = MW + loss_psi / (0.052 depth_ft)`; comparison multiplies loss per 100 ft by `depth_ft / 100` before calling ECD. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L106-L120] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L159-L178] |
| Cleaning index | `HCI = AV MW / cutting_density_ppg`; docstring asserts adequate cleaning above 1.0; this is a velocity-scaled heuristic, with qualification open under U1. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L126-L139] |
| Candidate priority | First target rate >15000 bopd selects large; then exploration/appraisal window <1.5 ppg selects slim; then exploration/appraisal rate <3000 bopd selects slim; remaining rate >5000 bopd selects large; otherwise standard. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L226-L250] |
| Recommendation flags | Minimum available windows are 0.3/0.5/0.6 ppg for slim/standard/large; slim cleaning flag becomes false above 45° deviation; risk increments above 60° and for complex slim completions. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L53-L65] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L140-L175] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L252-L276] |
| Hydraulic pressure-window check | `margin = fracture - ECD`, `available = fracture - pore`; compatible requires margin >=0 and available >= minimum; limiting-factor priority is negative margin, insufficient available window, then ECD >1.05 times mud weight. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L192-L220] |

Provenance boundary: the scalar and dictionary return paths emit no `Citation` sidecar; hydraulic source qualification and reference metadata are open under U1. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L100-L139] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L180-L188] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L214-L220]

## 4. Validated worked examples

Validated examples: **0**; the numerical expected values below repeat the implementation's formulas, and the schema/selection cases assert local policy rather than an independent engineering source. [tests/unit/well_bore_design/test_hydraulics.py:L25-L30] [tests/unit/well_bore_design/test_hydraulics.py:L137-L140] [tests/unit/well_bore_design/test_hydraulics.py:L177-L180] [tests/unit/well_bore_design/test_schemas.py:L171-L177] [tests/unit/well_bore_design/test_decision_framework.py:L92-L100]

### Regression examples

| Case | Input source / expected result | Tolerance and basis | Existing test node ID | Last offline result |
| --- | --- | --- | --- | --- |
| R1 annular velocity | Inline Q=500 gpm, hole 8.5 in, pipe 5.0 in; `0.408*500/(8.5**2-5.0**2)` ft/s | Relative 1e-4, unit 1; test's arithmetic tolerance | `tests/unit/well_bore_design/test_hydraulics.py::TestAnnularVelocity::test_known_value` | PASS at BASE and AFTER. [tests/unit/well_bore_design/test_hydraulics.py:L25-L30] |
| R2 ECD | Inline mud 9.5 ppg, loss 100 psi, depth 5000 ft; `9.5+100/(0.052*5000)` ppg | Relative 1e-5, unit 1; test's arithmetic tolerance | `tests/unit/well_bore_design/test_hydraulics.py::TestEcdPpg::test_known_ecd_calculation` | PASS at BASE and AFTER. [tests/unit/well_bore_design/test_hydraulics.py:L137-L140] |
| R3 cleaning index | Inline velocity 2.0 ft/s, mud 10.0 ppg; `2*10/21.7` velocity-scaled index | Relative 1e-5, unit 1; test's arithmetic tolerance | `tests/unit/well_bore_design/test_hydraulics.py::TestHoleCleaningIndex::test_known_hci_calculation` | PASS at BASE and AFTER. [tests/unit/well_bore_design/test_hydraulics.py:L177-L180] |
| R4 stored pressure window | Inline maximum 14.0 ppg, minimum 10.0 ppg; 4.0 ppg | `pytest.approx(4.0)` as shipped; no module-specific tolerance supplied (ppg) | `tests/unit/well_bore_design/test_schemas.py::TestWellBoreDesign::test_pressure_window_ppg_is_positive` | PASS at BASE and AFTER. [tests/unit/well_bore_design/test_schemas.py:L171-L173] |
| R5 point safety fraction | Inline margins [1.0, -0.1, 0.5, -0.2] ppg; fraction 0.5, unit 1 | `pytest.approx(0.5)` as shipped; no module-specific tolerance supplied (unit 1) | `tests/unit/well_bore_design/test_schemas.py::TestEcdProfile::test_safe_depth_fraction_partial` | PASS at BASE and AFTER. [tests/unit/well_bore_design/test_schemas.py:L245-L247] |
| R6 recommendation | Inline exploration, depth 3000 m, window 0.8 ppg, production 500 bopd; slim enum | Exact enum equality; 0 mismatches | `tests/unit/well_bore_design/test_decision_framework.py::TestRecommendLogic::test_exploration_tight_margin_returns_slim_hole` | PASS at BASE and AFTER. [tests/unit/well_bore_design/test_decision_framework.py:L92-L100] |

Offline execution record, 2026-10-15: CPython 3.12.3; code pin `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746`; BASE and AFTER use the same unmodified Python/tests, with documentation added for AFTER.

```text
uv run python -m pytest tests/unit/well_bore_design --noconftest -q -rA
  -p no:cacheprovider --basetemp=<scratch>
  --cov-report= --cov-report=term-missing
  --cov-report=html:<scratch> --cov-report=xml:<scratch>
  --cov-report=json:<scratch>
BASE: 105 run / 105 passed / 0 failed / 0 skipped / 0 NOT_RUN
AFTER: 105 run / 105 passed / 0 failed / 0 skipped / 0 NOT_RUN
```

The documented `--noconftest` form is used with the normal project sources and unchanged `addopts`; coverage destinations and the environment are redirected to scratch, with no solver dependency in the module tests. [AGENTS.md:L1-L12] [tests/unit/well_bore_design/test_hydraulics.py:L1-L11] [tests/unit/well_bore_design/test_schemas.py:L1-L13] [tests/unit/well_bore_design/test_decision_framework.py:L1-L15]

Fix-up execution record, 2026-10-16: BASE `1e40a4ccad4c313ce9dea2d9e8079988e7dd0b2a`; AFTER is the uncommitted documentation tree. The package source is unchanged from the code pin. The focused suite ran with the isolated pytest tool, package source on `PYTHONPATH`, `--no-project --with pytest`, `--noconftest -o addopts='' -p no:cacheprovider` and scratch `--basetemp`: **105 passed / 0 failed / 0 skipped** at both BASE and AFTER. This directly runs the module tests without the unrelated repository coverage configuration. C06–C08 arithmetic passed; C09 and C11 reproduce existing failures rather than clear them.

## 5. QA gates

Gate applicability: G0 inputs/units/citations, G1 imports/tests and G2 hand or published check apply; G3 and G4 are `NOT_APPLICABLE` for Python calculations; G5 evidence applies to every family. (AQG r0, sections 9–10.)

These are executable acceptance criteria, with the recorded results below; a passing regression check does not clear the independent-reference gap U1 or U2. [tests/unit/well_bore_design/test_hydraulics.py:L25-L30] [tests/unit/well_bore_design/test_hydraulics.py:L137-L140] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L17-L65]

| Gate / check | Module-specific action | Numeric pass criterion and unit | Evidence / recorded result |
| --- | --- | --- | --- |
| G0 / C01 | Run bit-classification boundary tests for 8.5 and 12.25 in | 0 unexpected enum results (count) | Boundary assertions; PASS in both test runs. [tests/unit/well_bore_design/test_schemas.py:L71-L97] |
| G0 / C02 | Run invalid-annulus, nonpositive-depth and zero-cutting-density guards in `WellBoreHydraulics` | 6 specified calls raise `ValueError`; 0 missing exceptions (count) | Six existing nodes; PASS in both runs. [tests/unit/well_bore_design/test_hydraulics.py:L43-L49] [tests/unit/well_bore_design/test_hydraulics.py:L96-L98] [tests/unit/well_bore_design/test_hydraulics.py:L142-L148] [tests/unit/well_bore_design/test_hydraulics.py:L187-L189] |
| G0 / C03 | Construct the empty `EcdProfile` shown in section 6 and inspect both safety methods | 0 empty profiles reported safe (count); fraction 0.0, unit 1 | Diagnostic confirmed safety true / fraction 0.0; baseline FAIL, issue pending (2). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L111-L120] |
| G0 / C04 | Call `pressure_window_check(STANDARD, 8, 12, 10, 1, 8000)` and compare returned ECD with pore bound | 0 compatible results with ECD <10.0 ppg (count) | Diagnostic confirmed compatible with ECD below pore; baseline FAIL, issue pending (3). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L192-L220] |
| G1 / C05 | Import `worldenergydata.well_bore_design` through the normal workspace and run all three module test files | 105 passed tests; 0 errors, failures or skips (count) | Node outcomes and counts in section 4; PASS in both test runs. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/__init__.py:L3-L34] [tests/unit/well_bore_design/test_hydraulics.py:L1-L11] [tests/unit/well_bore_design/test_schemas.py:L1-L13] [tests/unit/well_bore_design/test_decision_framework.py:L1-L15] |
| G2 / C06 | Re-evaluate R1 independently of the function using rational arithmetic `204/(189/4)` ft/s | Relative residual <=1e-4, unit 1 | Arithmetic diagnostic PASS; consistency only. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L30-L48] [tests/unit/well_bore_design/test_hydraulics.py:L25-L30] |
| G2 / C07 | Re-evaluate R2 as `19/2+5/13` ppg and compare `ecd_ppg` | Relative residual <=1e-5, unit 1 | Arithmetic diagnostic PASS; source qualification remains open. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L106-L120] [tests/unit/well_bore_design/test_hydraulics.py:L137-L140] |
| G2 / C08 | Re-evaluate R3 as `200/217` and compare `hole_cleaning_index` | Relative residual <=1e-5, unit 1 | Arithmetic diagnostic PASS; this does not validate cleaning adequacy. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L126-L139] [tests/unit/well_bore_design/test_hydraulics.py:L177-L180] |
| G2 / C09 | Compare `recommend('exploration', 10000, 0.8, 500)`, `recommend('exploration', 3000, 1.0, 12000)` and `recommend('exploration', 3000, 2.0, 20000)` with the entire selected matrix row | 0 selections outside depth, flow or well-type sets without a caveat (count) | FAIL at BASE and AFTER: 3 silent violations, respectively depth, flow and well type; #1288. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L17-L48] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L226-L250] |
| G3 | `NOT_APPLICABLE`: no time-domain simulation in the calculation interface | Not a dynamic analysis | Python calculations family row. (AQG r0, section 10.) |
| G4 | `NOT_APPLICABLE`: no diffraction-body or mesh computation in this interface | Not a diffraction analysis | Python calculations family row. (AQG r0, section 10.) |
| G5 / C10 | Retain a calculation record with input units, code/input SHA-256, R1–R6 node outcomes, diagnostic results and explicit U1/U2 dispositions | 6 of 6 regression node results linked; 0 missing input units, hashes or unresolved dispositions presented as cleared (count) | Pack evidence below; DRAFT disposition; independent signature pending. (AQG r0, sections 9, 11 and 13.) |

### Yield-stress force-balance check (C11)

C11 supplements C06–C08: for every positive-flow case below, loss per 100 ft shall be at least `YP/(3*(D_h-D_p))`; the criterion is 0 violations (count). BASE and AFTER: **4 violations**, unchanged code; #1288. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L74-L100]

For a steady annular force balance, `dP/dL = 4*tau_wall/(D_h-D_p)`. A flowing Bingham fluid requires `tau_wall >= YP`. Converting the inch gap to feet, multiplying by 100 ft and converting lbf/ft² to psi gives `4*(YP/100)*12*100/(144*(D_h-D_p)) = YP/(3*(D_h-D_p))` psi/100 ft. This is a lower bound, not a replacement hydraulic correlation. The calculation imports the pinned function for loss and evaluates this bound separately.

| Geometry (in); flow (gpm); mud (ppg); PV (cP); YP (lbf/100 ft²) | Re; branch | Module loss (psi/100 ft) | Floor (psi/100 ft) | Floor / loss (1) | Module / floor-only ECD (ppg), 10000 ft |
| --- | --- | --- | --- | --- | --- |
| 8.5/5.0; 500; 10; 20; 15 | 46581; turbulent | 0.0487 | 1.4286 | 29.3 | 10.0094 / 10.2747 |
| 8.5/5.0; 100; 9; 10; 10 | 12658; turbulent | 0.0023 | 0.9524 | 418.6 | 9.0004 / 9.1832 |
| 8.5/5.0; 100; 9; 40; 10 | 4038; turbulent | 0.0029 | 0.9524 | 333.1 | 9.0005 / 9.1832 |
| 6.0/3.5; 500; 10; 20; 15 | 68719; turbulent | 0.2497 | 2.0000 | 8.0 | 10.0480 / 10.3846 |

Table C11. Independently evaluated floor compared with the imported implementation; ratios use unrounded losses. The review's whole-number range is 8 to 419 times.

`pressure_window_check(STANDARD, 10, 10.2, 9.5, 500, 10000)` returns `compatible=True`, `limiting_factor="none"` and ECD 10.0094 ppg. The floor alone requires at least 10.2747 ppg, exceeding the fracture gradient 10.2 ppg; the compatible result is NON-CONSERVATIVE. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L192-L220]

G5 input fingerprint procedure: for each calculation, sort `relative input path + space + file SHA-256` lines, hash the joined manifest and retain outputs with the same fingerprint; inline test inputs use the three pinned test-file digests as the input manifest. (AQG r0, sections 2 and 13.)

Input-manifest record (SHA-256 over the sorted relative-path/file-digest lines, each ending in LF):

| Inline-input source | SHA-256 at the code pin |
| --- | --- |
| `tests/unit/well_bore_design/test_decision_framework.py` | `423a7a2f0bf32b1371144bbf4810d6b84aa5a741c8efce44b0c0a76469695900` |
| `tests/unit/well_bore_design/test_hydraulics.py` | `ff6b2acce3b189ed00bfc263e6494e63864d4b84708acffda111bcce74945ce2` |
| `tests/unit/well_bore_design/test_schemas.py` | `02a98d1ad220c8525edc9f7615f1f9c2365ebf5638d774e3eab71f5c26e97947` |

Combined input fingerprint: `c515d9f25ddd02d573fc57bee08d3cc3a0483895b49413f0cdc938596394ceee`.

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom | Cause / detection | Tracking and date |
| --- | --- | --- |
| SF1: NON-CONSERVATIVE annular loss; optimistic ECD and `compatible` | C11: flowing losses are 8 to 419 times below the yield-stress floor; 4 violations. Magnitude, not only notation, is in question | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L79-L100] |
| SF2: Caller rheology cannot be supplied or read back | PV 20 cP / YP 15 lbf/100 ft² are silently used by `pressure_window_check`; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L192-L196] |
| SF4: Unknown or mis-cased categories silently fall through | `Exploration` selects standard instead of slim; `gravel pack` bypasses the slim caveat and risk step; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L134-L166] |
| S1: Measured depth also used as TVD | Comparison uses one depth for friction length and ECD denominator; a deviated trajectory understates the ECD increment when MD is passed; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L161-L177] |
| S2: Recommendation window flag is not hydraulic | `pressure_window_compatible` tests window width only; neither ECD nor the mud is evaluated despite the class docstring; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L90-L92] |
| S3: Zero bit-size defaults classify as slim | Three bit sizes default 0.0; passing one to the classifier returns slim without warning or bore-type cross-check; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L27-L76] |
| S4: Clamp hides negative flow and incomplete scalar validation | Non-positive velocity sets Re to zero and the loss clamp can return 0.0 for negative flow; signs, finiteness and rheology are not validated; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L74-L100] |
| Unqualified fixed defaults silently supply engineering basis | Mud 9.0 ppg, cutting density 21.7 ppg, comparison PV/YP defaults, vertical deviation 0.0 and simple completion are assumed when omitted; 1.05 ECD warning and selection/risk/cost constants lack independent qualification; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L17-L65] |
| Empty sections and inconsistent stored profiles are accepted | Empty section default and unmatched arrays/minimum/bottleneck fields have no consistency validation; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L51-L120] |
| Units and preset geometry are caller assumptions | Metres versus feet, inches, gpm versus bopd and density units are not converted or tagged at runtime; fixed comparison geometry ignores supplied sections; no detection check exists | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L145-L188] |
| Empty profile reports safe | `all` over an empty margin list returns true, while the fraction method returns zero; C03 detects the disagreement | issue pending (2), 2026-10-15; no existing empty-profile detection test. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L111-L120] [tests/unit/well_bore_design/test_schemas.py:L208-L251] |
| Compatible flag without a pore-pressure lower-bound check | C04: the upper margin and available-window width can both pass with ECD below pore pressure; do not treat `compatible` as a complete well-control check | issue pending (3), 2026-10-15. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L199-L220] |
| SF3: Depth, flow and well-type envelopes silently bypassed | C09: all three selected matrix envelopes are ignored; 3 silent violations | #1288, 2026-10-16. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L17-L48] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L226-L250] |
| Comparison preset conflicts with classifier boundary | Large comparison geometry uses 12.25 in, while the helper classifies exactly 12.25 in as standard; C01 proves the boundary only, not agreement with the preset | issue pending (1), 2026-10-15; no preset/classifier agreement check exists. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L10-L15] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L27-L38] |
| Formula notation can obscure velocity conversion | Docstring laminar expression uses AV, implementation uses `av_fpm = 60*av`; C06–C08 establish arithmetic only, not the physical source | issue pending (1), 2026-10-15; no independent published-value detection check exists. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L63-L98] |
| Profile safety omits lower bound and weighting by depth interval | Stored margin is fracture minus ECD; `safe_depth_fraction` counts points rather than interval lengths; C03 covers empty data only | issue pending (2), related issue pending (3), 2026-10-15; no lower-bound or interval-weighting detection check exists. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L91-L120] |
| Completion caveat does not change selection | Slim complex-completion requests get a caveat after selection; cleaning flag is a deviation rule, not a call to the hydraulic index | issue pending (1), 2026-10-15; C09 qualifies selection limits. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L134-L166] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L252-L276] |
| Test described as laminar exercises the turbulent branch | At Q=100 gpm in the viscosity test, both viscosity settings give Re >2100 using the implemented formula; C06–C08 do not qualify either loss branch independently | issue pending (1), 2026-10-15; no independent laminar expected-value check exists. [tests/unit/well_bore_design/test_hydraulics.py:L100-L112] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L78-L98] |
| A named negative-margin test does not assert negative margin or incompatibility | Existing test asserts presence/non-None fields; its name alone is not branch coverage evidence | issue pending (3), 2026-10-15; C04 supplies a concrete lower-bound detection case. [tests/unit/well_bore_design/test_decision_framework.py:L225-L237] |
| Stored zero limits hide missing design basis | `pressure_window_ppg` returns zero if either limit is zero; no automatic calculation of profile minima or bottleneck | issue pending (2), 2026-10-15; no missing-basis detection check exists. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L78-L82] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L97-L120] |

Silent-failure sweep, 2026-10-16, all four package Python files at the code pin: 20 distinct section-6 rows (the 10 original rows, SF3 widened, plus 10 new rows). No swallowed exception, skipped-record `continue`, error-path `None`/empty return, external-text numeric conversion, date default or cache write exists. Empty list/dict initialisers are covered as schema defaults, caveats or comparison accumulation, rather than error returns. Zero limits, empty profile return and all fixed defaults/units are covered above. Empty notes are descriptive metadata, not calculation fallbacks.

```text
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|float\(|int\(|default|0\.05|1\.05|0\.052|0\.408|21\.7|20\.0|15\.0' <package>/*.py
rg -n 'return|field\(|: float =|: str =|open\(|write|cache|ppg|gpm|bopd|ft|metre|inch' <package>/*.py
```

The sweep includes manual inspection of every matched definition, including the 9.0 ppg mud default and heuristic thresholds not matched by the first expression. SF2/SF4 and S1–S4 have no shipped detection check; their reproduced observations do not imply a passing gate.

Diagnostic reproduction, using only the public API and an anonymous dataset ID:

```python
from worldenergydata.well_bore_design import (
    BoreType, BoreTypeDecision, EcdProfile,
)
p = EcdProfile('DATASET-001', BoreType.STANDARD, [], [], 9.5,
               450, [], [], None, 0.0)
print(p.is_safe_at_all_depths(), p.safe_depth_fraction())
print(BoreTypeDecision().pressure_window_check(
    BoreType.STANDARD, 8.0, 12.0, 10.0, 1.0, 8000.0))
print(BoreTypeDecision().recommend('exploration', 10000.0, 0.8, 500.0))
```

Recorded observations: empty safety `True`, fraction 0.0; lower-bound case `compatible=True` with ECD below 10.0 ppg; depth case slim at 10000 m against the stored slim maximum of 6000 m. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L111-L120] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L199-L220] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L17-L27] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L226-L250]

## 7. Lessons log

| Date | Record ID | Lesson / evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial knowledge record | A passing arithmetic test does not establish an independent hydraulic reference. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L63-L100] [tests/unit/well_bore_design/test_hydraulics.py:L25-L30] | Sections 3–5 separate formulas, regression evidence and source gaps | Pending, issue pending (7) |
| 2026-10-15 | Initial boundary record | Empty lists and matrix metadata need explicit handling before safety or applicability is inferred. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L111-L120] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L226-L250] | Section 6 records C03/C04/C09 and their reproduction inputs | Pending, issue pending (7) |

Append future lessons with evidence and tracking; retain these initial entries. (Module agent lifecycle, revision 0, section 3, lessons-log template.)

## 8. Ownership

| Responsibility | Role / disposition |
| --- | --- |
| Family quality manager | Calculations quality manager, covering EC data pipelines under the Python calculations gate set |
| Deputy quality manager | Unassigned; maintainer to nominate, issue pending (7) |
| Production and maintenance | Module maintainer; future calculation changes update the affected citations and examples |
| Escalation | Calculation/reference ambiguity goes to the calculations quality manager; unresolved cross-family scope goes to the maintainer |
| Clearance | Independent provider reviews the acceptance items; this pack remains DRAFT |

Role and clearance basis: Module agent lifecycle, revision 0, sections 3–4 and 6; AQG r0, sections 10–11.

## 9. Dependencies

| Dependency / consumer | Interface and evidence |
| --- | --- |
| Python runtime and standard library | Member requires Python >=3.10; schemas use dataclasses, enum and typing; decision code uses dataclasses. [packages/worldenergydata-well_bore_design/pyproject.toml:L5-L10] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L6-L10] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L6-L11] |
| `worldenergydata-core` | Declared member dependency; no core import appears in the four module files | [packages/worldenergydata-well_bore_design/pyproject.toml:L26-L32] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/__init__.py:L1-L34] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L6-L10] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L6-L8] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L6-L11] |
| Internal calculation route | Recommendation imports the hydraulics class; hydraulics imports the bore enum; public API re-exports them | [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L8-L11] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L8-L15] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/__init__.py:L3-L34] |
| Offline consumer | Tests construct data and invoke public functions with inline inputs, without stored well records | [tests/unit/well_bore_design/test_schemas.py:L105-L120] [tests/unit/well_bore_design/test_hydraulics.py:L19-L30] [tests/unit/well_bore_design/test_decision_framework.py:L52-L64] |

### Implementation-map inventory

Read-only map evidence record:

```text
Repository: digitalmodel
Ref: origin/codex/implmap-work
Map: docs/registry/implementation-map.yaml
Map commit: b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407
Map data revision: 947fa50ff9a9e210de7e8f90e01b37add85c5954
Map families examined: 13
Families with an implementation path inside this package: 0
Inventory rows for this module's map families: 0
Counted families: 0
Counted-family exact Python-re grep: NOT_APPLICABLE
Reason: no map family has an implementation row inside the package.
Inventory outcome: empty inventory; no counted-family miss total applicable.
```

Map follow-up, issue pending (6): add the section-3 families **annular velocity/pressure loss/ECD/cleaning**, **bore classification/design margins/profile safety**, and **bore recommendation/pressure-window feasibility**, with the implementations listed in section 3. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L30-L188] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L27-L38] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L78-L120] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L105-L276]

### Supplemental whole-repository search

Search record: all 2997 tracked Python files at the code pin, including hidden directories and `scripts/`; case-sensitive Python regex `0\.408|0\.052|Bingham|annular.velocity|equivalent.circulating.density|def .*ecd|def .*pressure_window|capital_cost_factor|bore_type_from_bit_size`; 116 matching lines in 14 files, assigned to their enclosing AST function/class or module-level definition. This search supplies map follow-up findings independently of the empty counted-family inventory.

| Definition outside the package | Classification / reason |
| --- | --- |
| `calculate_ecd` in the drilling-calculation template | Further independent ECD formula, adding temperature correction; map gap outside the package. [.claude/agent-library/worldenergydata/drilling-expert/templates/drilling_calculations.py:L18-L37] |
| `annular_pressure_loss` in the same template | Further independent annular velocity/friction/loss algorithm; map gap, not a delegate to this module. [.claude/agent-library/worldenergydata/drilling-expert/templates/drilling_calculations.py:L40-L82] |
| `PressureWindowAnalyzer.ecd_pressure`, `analyze` | Related independent pressure/window calculations; pressure output is psi rather than this module's ppg density. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L233] |
| Legacy `calculate_drilling_completion_summary`, `get_drilling_completion_summary` | Hydrostatic reservoir-pressure estimates share the 0.052 conversion but omit circulating annular pressure loss; related expressions, not another implementation of this ECD result. [packages/worldenergydata-core/src/worldenergydata/common/legacy/ong_fd_summary.py:L92-L104] [packages/worldenergydata-core/src/worldenergydata/common/legacy/ong_fd_components.py:L1186-L1198] |
| Template `surge_swab_pressure`, `kick_calculations`, `maasp_calculation` | Other pressure quantities using the conversion constant, rather than the same ECD or steady annular-loss result. [.claude/agent-library/worldenergydata/drilling-expert/templates/drilling_calculations.py:L157-L167] [.claude/agent-library/worldenergydata/drilling-expert/templates/drilling_calculations.py:L385-L430] |
| Risk-register text, test definitions and exports | Text/data, test assertions or delegation, rather than independent implementation. [packages/worldenergydata-well_planning/src/worldenergydata/well_planning/risk_registry.py:L54-L60] [tests/unit/well_bore_design/test_hydraulics.py:L25-L30] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/__init__.py:L3-L34] |

These outside-package findings belong in the map follow-up, issue pending (6); no counted-family acceptance result is changed by this supplemental search. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L30-L139] [.claude/agent-library/worldenergydata/drilling-expert/templates/drilling_calculations.py:L18-L82]

## 10. Coverage and open items

### Reading and execution inventory

| Coverage | Pinned evidence / disposition |
| --- | --- |
| Entire module | `__init__.py` (34 lines), `schemas.py` (120), `hydraulics.py` (188), `decision_framework.py` (294); no excluded subpackage | [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/__init__.py:L1-L34] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L1-L120] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L1-L188] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L1-L294] |
| Member documentation/configuration | README and member metadata; README describes namespace installation, not an engineering benchmark | [packages/worldenergydata-well_bore_design/README.md:L1-L8] [packages/worldenergydata-well_bore_design/pyproject.toml:L26-L53] |
| Documentation discovery: 4 files under `docs/` | `docs/adr/0001-domain-package-split.md`, `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`, `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`, `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`; their module mentions are historical inventory context, not current validation | [docs/adr/0001-domain-package-split.md:L45-L48] [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L18-L24] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L88-L94] [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L75-L79] |
| Entire module test suite | `test_schemas.py`: 42 test functions; `test_hydraulics.py`: 29; `test_decision_framework.py`: 34; no parametrized expansion; 105 collected/passed at BASE | [tests/unit/well_bore_design/test_schemas.py:L20-L251] [tests/unit/well_bore_design/test_hydraulics.py:L19-L249] [tests/unit/well_bore_design/test_decision_framework.py:L23-L274] |
| Citation contract | Calculation-output citation contract read; output provenance remains open under U1; current numeric outputs carry no sidecar | [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L100-L139] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L180-L188] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L214-L220] |

Repository inspection record at the code pin: `docs/registry/module-routing.yaml` is absent; there are no routing fields to update and no routing-domain contract change. Repository issue searches for module name, hydraulics, pressure-window checking and profiles found no matching specific defect issue; issue 349 is historical inventory context, and issue 529 is package-split context, rather than incident evidence for C03/C04/C09.

The SF1–SF4 and S1–S4 limitations remain present in the pinned implementation; #1288 tracks them. No calculation is corrected by this documentation revision.

### Open-item register

| Item | Missing evidence / next action | Responsible role / tracking |
| --- | --- | --- |
| U1 | Independently sourced hydraulic/cleaning formulas, edition/equation metadata, laminar/turbulent reference cases, velocity-notation reconciliation, loss-magnitude correction against C11, caller-rheology disclosure and provenance sidecars (#1288); 0 independently validated examples currently claimed | Maintainer; issue pending (1). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L63-L100] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L126-L139] |
| U2 | Evidence and applicability for selection/risk/cost heuristics, completion policy and the comparison-preset/classifier boundary disagreement | Maintainer; issue pending (1). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L17-L65] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L226-L276] |
| U3 | Explicit metre/foot depth datum, TVD versus MD basis and conversion contract | Maintainer; issue pending (1). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L51-L63] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L106-L120] |
| O1 | Define empty/inconsistent profile handling and missing-limit status; detect invalid geometry/array data, zero bit-size classification, negative flow, non-finite scalars and clamp-hidden invalid inputs before safety evaluation (#1288) | Maintainer; issue pending (2). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L51-L82] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L89-L120] |
| O2 | Define pore-pressure lower-bound compatibility and strengthen the existing branch assertions | Maintainer; issue pending (3). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L199-L220] [tests/unit/well_bore_design/test_decision_framework.py:L225-L237] |
| O3 | Enforce matrix depth/flow/well-type applicability and category validation or identify unsupported inputs explicitly (#1288) | Maintainer; issue pending (4). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L17-L48] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L226-L250] |
| O4 | Exclude the pack from wheel data; the existing `**/*.md` pattern matches nested Markdown, so exclusion is not established and no wheel was built here | Maintainer; issue pending (5), related issue 529. [packages/worldenergydata-well_bore_design/pyproject.toml:L47-L53] |
| O5 | Add every section-3 method family and section-9 supplemental finding to the implementation map before those families become counted | Maintainer; issue pending (6). [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L30-L188] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L27-L38] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L78-L120] [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L105-L276] |
| O6 | Assign deputy, record independent clearance/shared lessons, link the maintained index and replace all pending issue references | Maintainer; issue pending (7), related issue 349; Module agent lifecycle, revision 0, sections 3–4 |

Pending references identify issue drafts for filing; independent acceptance and final issue-number linkage remain open.
