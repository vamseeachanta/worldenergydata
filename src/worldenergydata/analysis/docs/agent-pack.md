# Analysis module knowledge pack

| Header | Value |
| --- | --- |
| Module | `analysis` |
| Repository | `worldenergydata` |
| Package path | `src/worldenergydata/analysis` |
| Pack revision | 3, 2026-10-22 |
| Historical code revision | `3a5d87fba8d476ff2367e7256ef176fed5672492` |
| Analysis family | EC; data pipeline, using the Python calculations gate set of AQG r0 section 10 |
| Quality manager role | Calculations quality manager; independent-provider review required by AQG r0 section 11 |
| Status | DRAFT |

## 1. Purpose and scope

Pressure screening now requires finite positive depth and pressure before estimation or division. Invalid inputs and nonfinite computed estimates carry `NOT_EVALUATED` status and a reason, no gradient, no pressure tier and no near-vacuum flag. Usable-well selection excludes these observations.

### Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-16 | Initial inventory of implemented methods, regression evidence and qualification gaps. |
| 1 | 2026-10-16 | Add numbered issue drafts, the infinite-depth finding and numeric-flag consequences; complete check references and issue notation. |
| 2 | 2026-10-16 | Use explicit draft-number headings so pending references pass lint; update links to the renamed headings. |
| 3 | 2026-10-22 | Refuse nonfinite or nonpositive screen inputs before they produce misleading pressure tiers. |

### Current implementation update, revision 3

`estimate_bhp` applies `math.isfinite` and positivity checks before the gas-column exponential or pressure/depth ratio. Finite inputs that overflow the gas-column model are also refused. `screen_status` and `screen_reason` preserve the disposition on the observation; `pressure_tier` is explicitly `NOT_EVALUATED`. Direct classification also refuses nonfinite or nonpositive gradients.

| Finding | Current detection nodes |
| --- | --- |
| #1307 S52: infinite depth or invalid pressure yields a false tier | `tests/unit/analysis/test_screen_input_regressions.py::test_nonfinite_or_nonpositive_input_not_evaluated` |
| Independent normal-case arithmetic | `tests/unit/analysis/test_screen_input_regressions.py::test_normal_pressure_depth_hand_calculation`: measured 1200 psia divided by 5000 ft gives 0.24 psi/ft, as defined by historical C06 |
| Invalid direct classification or computed BHP | `tests/unit/analysis/test_screen_input_regressions.py::test_direct_classification_refuses_invalid_gradient`; `tests/unit/analysis/test_screen_input_regressions.py::test_overflow_in_bhp_estimate_not_evaluated` |

Remaining limits: the gas-column assumptions, configured tier thresholds, pressure datum, numeric flag parsing, missing metadata, earliest-observation proxy, field gates, output-before-gate behavior and rounding remain as recorded below. Invalid observations remain visible in the enriched frame but are excluded from usable-well rankings; no new invalid-row summary count is added.

### Historical inventory boundary

Sections 2–10 below retain the inventory, citations, execution records and open
limits at the historical code revision. Findings corrected by the current update
are historical evidence; the current contracts and detection nodes above supersede
those earlier behavior statements and test counts. Remaining limits are retained.


## 2. Inputs and outputs

### Inputs

| Name | Unit or type | Allowed range and default | Source and evidence |
| --- | --- | --- | --- |
| Input files | Parquet tables | One entry per configured source; empty sources allowed | `load_observations(inputs)` reads each entry's `path`. [src/worldenergydata/analysis/underpressured_screen/observations.py:L57-L82] |
| `well_key`, `state`, `field` | Identifiers; no physical unit | Required column names; values, nulls and uniqueness are not validated | `_validate_required_columns` checks presence only. [src/worldenergydata/analysis/underpressured_screen/observations.py:L10-L18] [src/worldenergydata/analysis/underpressured_screen/observations.py:L150-L160] |
| `test_year` | Year label | Required; no type, chronology or range validation | Required-column contract and earliest sorting. [src/worldenergydata/analysis/underpressured_screen/observations.py:L10-L18] [src/worldenergydata/analysis/underpressured_screen/screen.py:L86-L93] |
| `pressure_kind` | Categorical string | Required column; only exact `WHP_shut_in` triggers correction; missing or other kinds use reported pressure | `estimate_bhp`. [src/worldenergydata/analysis/underpressured_screen/screen.py:L54-L60] |
| `pressure_psia` | psia, as assumed by the code | Required; no range or gauge-to-absolute conversion in this package | Required columns and pressure arithmetic. [src/worldenergydata/analysis/underpressured_screen/observations.py:L10-L18] [src/worldenergydata/analysis/underpressured_screen/screen.py:L47-L64] |
| `reference_depth_ft` | ft, as assumed by the code | Required; gradient only for depth greater than 0 ft; no coordinate origin or TVD check | `estimate_bhp` uses supplied depth directly. [src/worldenergydata/analysis/underpressured_screen/screen.py:L47-L64] |
| `name`, `era`, optional `state` | Source and era labels | `name` and `era` replace existing columns; configured state fills missing state values | `normalize_observations`. [src/worldenergydata/analysis/underpressured_screen/observations.py:L44-L54] |
| `schema` | Schema ID | Default `screen_v1`; also `texas_rrc_pressure_v1`, `oklahoma_occ_completion_v1`, `colorado_ecmc_production_v1`; unsupported ID raises `ValueError` | Schema dispatch. [src/worldenergydata/analysis/underpressured_screen/observations.py:L30-L42] |
| `require_usable_proxy` | Boolean-like configuration | Absent disables the source-specific usable-row filter | Source adapter. [src/worldenergydata/analysis/underpressured_screen/observations.py:L95-L104] |
| `screen_observation_priority` | Dimensionless integer | Default 0; source earliest flags map to 0 for true and 1 otherwise | Priority injection and source adapters. [src/worldenergydata/analysis/underpressured_screen/observations.py:L51-L53] [src/worldenergydata/analysis/underpressured_screen/observations.py:L95-L103] [src/worldenergydata/analysis/underpressured_screen/observations.py:L124-L146] |
| `quality_path` | Optional JSON file | Omission gives no warnings; missing file gives a warning; absent `source_warnings` gives an empty list | `_read_source_warnings`. [src/worldenergydata/analysis/underpressured_screen/observations.py:L163-L170] |
| `gas_sg`, `z_avg`, `t_avg_rankine` | Dimensionless, dimensionless, degrees Rankine | Configuration values 0.65, 0.95 and 520.0; required keys, no positivity checks | Configuration and estimator. [config/underpressured_screen.yml:L39-L45] [src/worldenergydata/analysis/underpressured_screen/screen.py:L47-L53] |
| Tier thresholds | psi/ft; psia for vacuum flag | Configured boundaries 0.433 and 0.35 psi/ft; vacuum cutoff 50.0 psia; these are configuration assumptions | Configuration and comparisons. [config/underpressured_screen.yml:L47-L52] [src/worldenergydata/analysis/underpressured_screen/screen.py:L68-L82] |
| `min_wells_per_field` | Wells | Configuration 5 wells; no default in `rank_fields` | Group-size filter. [config/underpressured_screen.yml:L54-L55] [src/worldenergydata/analysis/underpressured_screen/screen.py:L96-L109] |
| Recovery and participation rules | Group IDs, tier and source-state IDs | Recovery considers first 10 ranked rows; participation defaults to no rules, then 1 well per configured state lacking `min_wells` | Gate functions. [src/worldenergydata/analysis/underpressured_screen/screen.py:L127-L156] [src/worldenergydata/analysis/underpressured_screen/screen.py:L194-L197] |

No vector coordinate system, sign convention or phase convention is implemented by this scalar pressure-screen path; the depth is used without conversion or reference-frame metadata validation. [src/worldenergydata/analysis/underpressured_screen/screen.py:L40-L65]

### Outputs

| Name | Unit or type | Meaning and evidence |
| --- | --- | --- |
| `bhp_psia_est`, `bhp_gradient_psi_ft`, `bhp_method` | psia, psi/ft, method label | Estimated or reported pressure, depth-normalized gradient, and method flag. [src/worldenergydata/analysis/underpressured_screen/screen.py:L54-L65] |
| `pressure_tier`, `near_vacuum` | Categorical label, Boolean | Gradient classification and shut-in-only vacuum comparison. [src/worldenergydata/analysis/underpressured_screen/screen.py:L68-L83] |
| `well_screen_earliest.parquet` | Table | Selected well records after optional metadata normalization. [src/worldenergydata/analysis/underpressured_screen/screen.py:L190-L204] |
| `underpressured_field_ranking.parquet` | Table | Well counts, median and percentile gradients in psi/ft, vacuum counts, earliest year, state/era labels and group tier. [src/worldenergydata/analysis/underpressured_screen/screen.py:L96-L124] [src/worldenergydata/analysis/underpressured_screen/screen.py:L205-L207] |
| `screen_summary.json` | JSON | Counts, median gradient, gates, era/source/state summaries and source warnings. [src/worldenergydata/analysis/underpressured_screen/screen.py:L159-L181] [src/worldenergydata/analysis/underpressured_screen/screen.py:L208-L210] |

All three output files are written before failed gates raise `RuntimeError`; file presence is therefore insufficient evidence of an accepted run. [src/worldenergydata/analysis/underpressured_screen/screen.py:L202-L215]

## 3. Method and governing standards

| Method family | Implementation and basis |
| --- | --- |
| Observation normalization | Four schema branches; two column-renaming maps; source/state/era annotation and required-column validation. [src/worldenergydata/analysis/underpressured_screen/observations.py:L10-L54] [src/worldenergydata/analysis/underpressured_screen/observations.py:L85-L160] |
| Gas-column estimate | `estimate_bhp`: `pressure_psia * exp(0.01875 * gas_sg * reference_depth_ft / (z_avg * t_avg_rankine))` for exact shut-in wellhead kind; other kinds retain reported pressure; estimated pressure divided by positive depth gives gradient. [src/worldenergydata/analysis/underpressured_screen/screen.py:L40-L65] |
| Tier classification | `classify_tiers` and `apply_field_tier` compare gradients to configured lower bounds, with the normal comparison first, then mild, then severe for a remaining non-null gradient; missing gradient yields no tier. [src/worldenergydata/analysis/underpressured_screen/screen.py:L68-L83] [src/worldenergydata/analysis/underpressured_screen/screen.py:L112-L124] |
| Observation selection | `earliest_per_well` removes null gradients, sorts by well key, year and optional priority, then uses `groupby(...).first()`; this selects first non-null values per column rather than guaranteeing one original record. [src/worldenergydata/analysis/underpressured_screen/screen.py:L86-L93] |
| Group ranking | `rank_fields` groups by `field`, replacing missing labels, computes unique-well count, median, 0.1 and 0.9 quantiles, and metadata summaries, removes groups below the configured minimum and sorts by count. [src/worldenergydata/analysis/underpressured_screen/screen.py:L96-L109] |
| Acceptance summaries | Recovery requires every configured group in the first 10 rows with the required tier; participation checks unique-well counts for configured states. [src/worldenergydata/analysis/underpressured_screen/screen.py:L127-L156] |
| Serialization | Optional object dates are parsed only when the non-null count is preserved; other object metadata becomes nullable text. [src/worldenergydata/analysis/underpressured_screen/screen.py:L235-L251] |

UNVERIFIED: independent physical derivation, calibration and applicability of the gas-column coefficient and pressure-tier assumptions have not been established; the estimator and configuration give arithmetic and assumptions but no governing standard, edition, clause or `Citation` sidecar. Issue pending (1). [src/worldenergydata/analysis/underpressured_screen/screen.py:L40-L65] [config/underpressured_screen.yml:L39-L52]
The existing correction test repeats the implementation's coefficient and expression, so its agreement is a regression check, not an independent physical reference. [tests/unit/analysis/test_underpressured_screen.py:L44-L58]
AQG r0 section 10 supplies G0, G1 and G2 for Python calculations, with G3 and G4 not applicable; G5 applies under AQG r0 section 9.

## 4. Validated worked examples

Validated physical examples: **0**; no independent expected-value source is established for the implemented pressure estimate (issue pending (1)). [tests/unit/analysis/test_underpressured_screen.py:L44-L58]

Regression examples: **4**; input values below are test fixtures rather than qualified observations. [tests/unit/analysis/test_underpressured_screen.py:L44-L104] [tests/unit/analysis/test_underpressured_screen.py:L426-L501]

| Case | Source and inputs | Expected value and tolerance basis | Test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 correction expression | In-test 100.0 psia, 2800.0 ft; test settings | `100 * exp(0.01875 * 0.65 * 2800 / (0.95 * 520))` psia; `pytest.approx` without explicit tolerance; repeated formula only | `tests/unit/analysis/test_underpressured_screen.py::TestEstimateBhp::test_whp_gets_static_column_correction` | PASS at BASE and AFTER. [tests/unit/analysis/test_underpressured_screen.py:L24-L24] [tests/unit/analysis/test_underpressured_screen.py:L44-L58] |
| R2 reported pressure | In-test measured pressure 1200.0 psia, depth 5000.0 ft | 1200.0 psia and `as_reported`; `pytest.approx` without explicit tolerance | `tests/unit/analysis/test_underpressured_screen.py::TestEstimateBhp::test_measured_bhp_passes_through` | PASS at BASE and AFTER. [tests/unit/analysis/test_underpressured_screen.py:L76-L90] |
| R3 absent gradient | In-test 100.0 psia, depth 0 ft | 1 null gradient per 1 well; exact `np.isnan` assertion | `tests/unit/analysis/test_underpressured_screen.py::TestEstimateBhp::test_no_gradient_without_depth` | PASS at BASE and AFTER. [tests/unit/analysis/test_underpressured_screen.py:L92-L104] |
| R4 output round trip | Two in-test Parquet inputs with mixed date metadata; temporary YAML and output folder | Exactly 2 selected rows; exactly 1 well in each of 2 state summaries; count tolerance 0 rows | `tests/unit/analysis/test_underpressured_screen.py::TestSummaryAndParticipationGate::test_screen_outputs_are_parquet_safe_with_mixed_optional_metadata` | PASS at BASE and AFTER. [tests/unit/analysis/test_underpressured_screen.py:L426-L501] |

Execution record: BASE at the code revision: 108 tests run, 108 passed, 0 failed, 1 collection skip and 0 NOT_RUN; 29 passed screening tests, 33 passed dashboard component tests and 46 passed contracts tests. AFTER produced the same outcomes: 108 run, 108 passed, 0 failed, 1 collection skip and 0 NOT_RUN. The 109 collected/result records match between runs, including the existing skip. The skipped compatibility test module is documented in section 6. The ordinary source-enabled `uv run --extra test python -m pytest` form is used with `-q -rA -p no:cacheprovider`, an external temporary base, retained coverage reports and JUnit output. The repository tree-preservation option records pre-existing documentation without changing test selection.

The reproducible test selection is shown below; `SCRATCH` denotes an external temporary output directory. BASE and AFTER differ only in output names. No source-resolution fallback or `addopts` override was used. All coverage formats were retained outside the repository.

```bash
uv run --extra test python -m pytest \
  tests/unit/analysis \
  tests/unit/well_production_dashboard/test_well_detail_views.py \
  tests/unit/well_production_dashboard/test_well_production_dashboard.py \
  tests/contracts -q -rA -p no:cacheprovider \
  --basetemp="$SCRATCH/bt-base" --allow-existing-tree-changes \
  --cov-report= --cov-report=term \
  --cov-report=html:"$SCRATCH/base-coverage-html" \
  --cov-report=xml:"$SCRATCH/base-coverage.xml" \
  --cov-report=json:"$SCRATCH/base-coverage.json" \
  --junitxml="$SCRATCH/base-results.xml"
```

Revision-1 local rerun: BASE 108 passed, 0 failed, 1 collection skip; AFTER 108 passed, 0 failed, 1 collection skip. Both runs had 29 screening, 33 dashboard and 46 contract passes, with matching test node outcomes. The selection above was run with `uv run --no-project --with pytest` and explicit dependency additions, including `pytest-cov`; repository and workspace-member source directories plus the sibling dependency source were supplied on `PYTHONPATH`. No dependency lock or source file changed. Coverage and JUnit reports stayed in the external scratch directory. The compatibility skip is unchanged; the test environment used binary distributions only.

## 5. QA gates

Applicable gate set: **G0, G1, G2, G5**; G3 and G4 are `NOT_APPLICABLE` because this path performs scalar Python calculations and table processing, with no dynamic simulation or diffraction model (AQG r0 sections 9–10). [src/worldenergydata/analysis/underpressured_screen/screen.py:L184-L216]

The following checks define module-specific acceptance criteria; a documented gap does not become a passed physical qualification check.

| Check | Gate | Executable route and numeric pass criterion | Evidence and status |
| --- | --- | --- | --- |
| C01 | G0 | Run `tests/unit/analysis/test_underpressured_observations.py::test_normalizes_texas_pressure_schema_to_screen_contract`; require exactly 1 normalized row retaining kind, key and provenance; 0 mismatched fields | PASS at BASE and AFTER; named test assertions. [tests/unit/analysis/test_underpressured_observations.py:L13-L46] |
| C02 | G0 | Run `tests/unit/analysis/test_underpressured_observations.py::test_filters_texas_unusable_rows_when_required`; require exactly 1 retained row from 2 fixture rows, with 0 unusable rows retained | PASS at BASE and AFTER; named filter test. [tests/unit/analysis/test_underpressured_observations.py:L49-L84] |
| C03 | G0 | Run R3; depth 0 ft shall yield exactly 1 null gradient per input well | PASS at BASE and AFTER; R3 result. [tests/unit/analysis/test_underpressured_screen.py:L92-L104] |
| C04 | G1 | Run the selected module and compatibility tests; require 0 failed or collection-error test cases, with every skip reason recorded | PASS: BASE and AFTER each 108 passed, 0 failed and 1 existing collection skip. Test sources and compatibility use. [tests/unit/analysis/test_underpressured_screen.py:L43-L104] [tests/unit/analysis/test_underpressured_observations.py:L13-L84] [tests/unit/well_production_dashboard/test_well_detail_views.py:L479-L493] |
| C05 | G1 | Import the legacy wrapper and canonical re-export in Python; require 0 identity differences for the 8 tested component classes, and 0 import exceptions | PASS: 8 class identities checked, 0 differences; diagnostic import record and wrapper delegation. [src/worldenergydata/analysis/dashboard/well_detail_views.py:L1-L8] [tests/unit/well_production_dashboard/test_well_detail_views.py:L19-L28] |
| C06 | G2 | Hand division on R2 inputs: `1200 / 5000 = 0.24` psi/ft; compare `estimate_bhp` gradient with absolute difference at most `1e-12` psi/ft | PASS: expected 0.24 psi/ft, absolute error 0 psi/ft; diagnostic arithmetic record; algebra check only, not gas-column qualification. [tests/unit/analysis/test_underpressured_screen.py:L76-L90] [src/worldenergydata/analysis/underpressured_screen/screen.py:L61-L64] |
| C07 | G2 | Independent gas-column benchmark: require at least 1 independently sourced pressure expected value, 0 missing coefficient/unit derivations, and a declared pressure tolerance in psia | NOT_RUN: no independent reference, issue pending (1); no independent-reference detection check exists in the shipped tests. [tests/unit/analysis/test_underpressured_screen.py:L44-L58] |
| C08 | G5 | Run `tests/unit/analysis/test_underpressured_observations.py::test_load_observations_collects_input_counts_and_quality_warnings`; require exactly 1 input row and 1 loaded row, with 1 source warning retained | PASS at BASE and AFTER; named loader test. [tests/unit/analysis/test_underpressured_observations.py:L183-L231] |
| C09 | G5 | Run R4; require 2 selected rows read back from Parquet and 0 state-count differences | PASS at BASE and AFTER; R4 result. [tests/unit/analysis/test_underpressured_screen.py:L426-L501] |
| C10 | G5 | Run `tests/unit/analysis/test_underpressured_screen.py::TestValidationGate::test_gate_passes_on_analog_recovery`, `tests/unit/analysis/test_underpressured_screen.py::TestValidationGate::test_gate_fails_on_wrong_tier`, `tests/unit/analysis/test_underpressured_screen.py::TestValidationGate::test_gate_fails_on_missing_field`, `tests/unit/analysis/test_underpressured_screen.py::TestSummaryAndParticipationGate::test_participation_gate_requires_state_well_count`, `tests/unit/analysis/test_underpressured_screen.py::TestSummaryAndParticipationGate::test_participation_gate_fails_when_state_missing`, `tests/unit/analysis/test_underpressured_screen.py::TestSummaryAndParticipationGate::test_participation_gate_tracks_colorado_state_entry`; require 0 wrong-tier or missing-required-group cases accepted and 0 absent-required-state cases accepted | PASS at BASE and AFTER; named gate tests; empty-rule coverage is excluded from this check and recorded below. [tests/unit/analysis/test_underpressured_screen.py:L282-L312] [tests/unit/analysis/test_underpressured_screen.py:L379-L424] |
| C11 | G5 | Before accepting any real screen output, read `screen_summary.json`; require exactly 2 true gate results, 0 unresolved source warnings and 0 missing input digests in the evidence bundle | NOT_RUN: qualified run evidence unavailable, issue pending (4); gate results and warning fields are emitted, but digests and a signed AQG appendix are not emitted by `run_screen`. [src/worldenergydata/analysis/underpressured_screen/screen.py:L167-L181] [src/worldenergydata/analysis/underpressured_screen/screen.py:L202-L216] |
| C12 | G0 | Run `tests/unit/analysis/test_underpressured_observations.py::test_load_observations_accepts_empty_warned_source_without_futurewarning`; require exactly 0 loaded rows for the empty source, 1 retained nonempty observation and 1 retained warning | PASS at BASE and AFTER; existing empty-source regression. [tests/unit/analysis/test_underpressured_observations.py:L234-L294] |

Executed checks: **10 PASS**, with **2 NOT_RUN** qualification checks (C07 and C11); these are separate from the pytest case counts.

Gate counts: G0 **4**, G1 **2**, G2 **2**, G3 **0**, G4 **0**, G5 **4**; total **12** defined checks.
No target-program load route applies to the pressure screen; its executable load route is Python import plus the offline tests in C04–C05. [src/worldenergydata/analysis/underpressured_screen/screen.py:L184-L216]

## 6. Known failure modes and pitfalls

Sweep scope: all six Python files under the package, including compatibility wrappers; the two implementation files contain the sites below. [src/worldenergydata/analysis/__init__.py:L1-L9] [src/worldenergydata/analysis/dashboard/__init__.py:L1-L10] [src/worldenergydata/analysis/dashboard/well_detail_views.py:L1-L8] [src/worldenergydata/analysis/underpressured_screen/__init__.py:L1-L9] [src/worldenergydata/analysis/underpressured_screen/screen.py:L1-L262] [src/worldenergydata/analysis/underpressured_screen/observations.py:L1-L176]

Re-run these exact searches at the code revision; the second search covers implicit coercion, unit and empty-output paths as well as explicit returns:

sweep: 52 found (S01–S52; findings and explicitly classified benign fallbacks).

```bash
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|0\.05|5 ?%|int\(|float\(' src/worldenergydata/analysis --glob '*.py'
rg -n 'fillna|dropna|coerce|\.get\(|groupby|value_counts|nunique|to_parquet|write_text|psi|rankine|depth|exp\(' src/worldenergydata/analysis --glob '*.py'
```

No exception handler, epoch fallback, 5-percent default or numeric-separator normalization is present in these implementation files; integer row counts, Boolean-priority casts and the median float conversion operate on computed values, while the configurable participation minimum is converted with `int()`. [src/worldenergydata/analysis/underpressured_screen/screen.py:L1-L262] [src/worldenergydata/analysis/underpressured_screen/observations.py:L1-L176]

Each row below is a sweep finding or an explicitly classified benign fallback. Discovery date: 2026-10-16. A check ID covers only the behavior its cited test asserts; other conditions are explicitly without a detection check.

| ID | Site at code revision | Symptom or fallback | Detection and tracking |
| --- | --- | --- | --- |
| S01 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L32-L42] | Missing schema selects `screen_v1`; accidental schema omission can avoid the intended adapter. | no detection check exists; issue pending (2). |
| S02 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L44-L45] | Source and era labels overwrite input columns; conflicting source provenance is not compared. | no detection check exists; issue pending (2). |
| S03 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L46-L50] | Configured state supplies a missing column or fills null state values without checking contradictory non-null values. | no detection check exists; issue pending (2). |
| S04 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L51-L53] | Absent observation priority becomes 0; the source priority distinction is then unavailable. | no detection check exists; issue pending (2). |
| S05 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L65-L72] | Repeated source names overwrite row-count and warning dictionary entries. | no detection check exists; issue pending (2). |
| S06 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L70-L72] | Omitted quality path contributes no source warnings to the summary. | no detection check exists; issue pending (2). |
| S07 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L74-L76] | Empty source frames are omitted before concatenation; counts and supplied warnings remain the only evidence of the empty source. | C12 covers one empty source alongside one nonempty source; no detection check exists for all-empty inputs; issue pending (2). |
| S08 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L77-L82] | All-empty or absent inputs return an empty schema frame, with no explicit nonempty-input gate. | no detection check exists; issue pending (2). |
| S09 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L94-L97] | Key conversion assumes string-compatible identifiers; unrecognized or missing earliest flags become lower priority. | no detection check exists; issue pending (2). |
| S10 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L98-L104] | Absent or false `require_usable_proxy` disables filtering; when enabled, false-like values discard records; float-typed `1.0` flags become false and can remove every source row with no error, visible only in loaded-row counts. | C02 covers the enabled Boolean case only; no detection check exists for float-typed or malformed flags; issue pending (2). |
| S11 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L117-L123] | Absent field column uses formation label; an existing but null field column is not filled from formation. | no detection check exists; issue pending (2). |
| S12 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L123-L126] | Key casting and earliest-flag conversion do not validate missing identifiers or unexpected flag text. | no detection check exists; issue pending (2). |
| S13 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L143-L146] | The production-schema key and earliest flags receive the same unchecked conversion. | no detection check exists; issue pending (2). |
| S14 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L150-L160] | Column presence alone accepts nulls, invalid numeric types, nonfinite values and inconsistent pressure/depth units. | no detection check exists; issue pending (1). |
| S15 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L164-L165] | No quality path returns an empty warning list, not an unavailable-quality status. | no detection check exists; issue pending (2). |
| S16 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L166-L168] | Missing quality file returns a warning instead of stopping; downstream acceptance must inspect it. | no detection check exists; issue pending (2). |
| S17 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L169-L170] | Absent warning key returns an empty list; warning payload shape is not checked. | no detection check exists; issue pending (2). |
| S18 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L173-L175] | Missing Boolean flag becomes false. | no detection check exists; issue pending (2). |
| S19 | [src/worldenergydata/analysis/underpressured_screen/observations.py:L176-L176] | Missing textual flag becomes empty text; only `1`, `true`, `yes` are recognized, without trimming. Float-typed `1.0` becomes `"1.0"` and false, as does text `"NA"`; usable filtering can remove a whole source and earliest flags can all become priority 1. | no detection check exists; issue pending (2). |
| S20 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L35-L37] | YAML is safely loaded but mapping shape, duplicate keys, ranges and cross-field constraints are not validated. | no detection check exists; issue pending (1). |
| S21 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L47-L53] | Fixed gas-column coefficient assumes compatible psia/ft/Rankine settings; zero divisors, overflow and invalid settings have no explicit rejection. | no detection check exists; issue pending (1). |
| S22 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L54-L60] | Null pressure kind becomes empty text and unknown kinds use reported pressure rather than being rejected. | no detection check exists for null or unknown kinds; issue pending (1). |
| S23 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L61-L64] | Depth at or below 0 ft or null depth yields a null gradient; later selection can silently remove the record. | C03 covers 0 ft only; no detection check exists for negative or null depth; issue pending (1). |
| S24 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L71-L79] | Null gradient receives `None` tier; nonfinite gradients and reversed thresholds are not rejected. | no detection check exists; issue pending (1). |
| S25 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L80-L82] | Vacuum flag assumes absolute pressure and exact shut-in kind; unknown kinds cannot raise that flag. | no detection check exists for wrong units or unknown kind; issue pending (1). |
| S26 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L88-L88] | Null-gradient observations are removed without an exclusion-count output. | no detection check exists; issue pending (3). |
| S27 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L89-L93] | Missing years sort after known years; exact sort ties lack a stable observation ID; null well keys disappear during grouping. | no detection check exists; issue pending (3). |
| S28 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L93-L93] | `groupby.first()` can combine non-null cells from different observations into a synthetic selected record. | no detection check exists; issue pending (3). |
| S29 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L97-L97] | Missing group labels share `(unmatched)`; equal labels across states are grouped together. | no detection check exists; issue pending (3). |
| S30 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L98-L104] | Unique counts and median/quantile/sum statistics use library missing-value semantics without an explicit completeness criterion; 0.1/0.9 are percentile definitions, not error defaults. | no detection check exists for incomplete groups; issue pending (3). |
| S31 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L105-L105] | Null state metadata is discarded from aggregated state labels. | no detection check exists; issue pending (3). |
| S32 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L106-L106] | Null era metadata is discarded from aggregated era labels. | no detection check exists; issue pending (3). |
| S33 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L108-L109] | Groups below minimum well count disappear without an exclusion-count output; equal counts have no secondary ranking key. | no detection check exists for exclusion accounting or tied ordering; issue pending (3). |
| S34 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L115-L123] | Null group median receives `None` tier; threshold order and finiteness are unchecked. | no detection check exists; issue pending (1). |
| S35 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L130-L138] | Empty required-group list passes `all()`; the top-10 slice is a configurable-data acceptance assumption, not physical validation. | C10 covers wrong-tier and missing-group rules only; no detection check exists for empty requirements; issue pending (4). |
| S36 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L144-L144] | Missing `required_states` becomes an empty rule dictionary. | no detection check exists; issue pending (4). |
| S37 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L146-L146] | Missing minimum becomes 1 well; `int()` may truncate a fractional YAML number and does not parse separator-formatted external text. | no detection check exists; issue pending (1). |
| S38 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L147-L155] | Unique-well count omits null keys; an empty state-rule dictionary passes `all()`. | C10 covers an absent required state only; no detection check exists for empty rules or null keys; issue pending (4). |
| S39 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L166-L170] | Tier counts omit missing labels; vacuum sum uses library null handling without reporting missing flag counts. | no detection check exists; issue pending (3). |
| S40 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L178-L178] | Absent input counts become an empty dictionary. | no detection check exists; issue pending (4). |
| S41 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L179-L179] | Absent loaded counts become an empty dictionary. | no detection check exists; issue pending (4). |
| S42 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L180-L180] | Absent source warnings become an empty dictionary. | no detection check exists; issue pending (4). |
| S43 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L194-L197] | Omitted participation gate becomes an empty configuration and can pass without participants. | no detection check exists; issue pending (4). |
| S44 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L202-L215] | Outputs are created before gate failures raise; empty or failed-run artifacts have no transactional acceptance marker or input digest. | no detection check exists; issue pending (4). |
| S45 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L219-L221] | Summary counts remove null state/source labels. | no detection check exists; issue pending (3). |
| S46 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L224-L227] | Missing median returns `None`; JSON null is distinct from a zero gradient. | no detection check exists; issue pending (3). |
| S47 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L228-L228] | Median is rounded to four decimal places before summary output; float conversion is internal numeric conversion, not parsing of external text. | no detection check exists for rounding bounds; issue pending (3). |
| S48 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L231-L232] | Null era values disappear from the unique-value list. | no detection check exists; issue pending (3). |
| S49 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L239-L242] | Object date parsing uses coercion; any non-null parse failure prevents conversion of the entire column, which then becomes text. | no detection check exists for invalid-date fidelity; issue pending (5). |
| S50 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L241-L244] | `continue` follows successful whole-column date conversion; it skips text conversion, not a record. Count casts operate on computed values. | C09 covers valid mixed optional dates; issue pending (5) for invalid-date fidelity. |
| S51 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L248-L251] | Missing object metadata returns `None`; nonmissing values are stringified, losing original object type. | no detection check exists for general object-type preservation; issue pending (5). |
| S52 | [src/worldenergydata/analysis/underpressured_screen/screen.py:L47-L64] [src/worldenergydata/analysis/underpressured_screen/screen.py:L71-L88] | Positive infinite depth passes `> 0`: non-shut-in pressure divided by infinity yields 0.0 psi/ft and a false severe tier; shut-in estimation overflows to a nonfinite gradient that selection drops. Negative pressure can classify severe and set the shut-in vacuum flag; positive infinite pressure can classify normal. | no detection check exists; issue pending (1), with numeric-flag acceptance in issue pending (2). |

Sweep inventory: **52 rows**; wrapper exports are helpers, not local calculation implementations. [src/worldenergydata/analysis/dashboard/well_detail_views.py:L1-L8]
The empty-source regression checks exactly 0 loaded rows for an empty warned source and retains its warning; it does not assert rejection of all-empty inputs. [tests/unit/analysis/test_underpressured_observations.py:L234-L294]

No incident issue is specified for this package. Historical implementation context is recorded in issues #710, #732, #740 and #745 by the tracked source documentation; it does not independently establish present physical validation. [docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md:L3-L19]
The dashboard test module has an unconditional skip citing absent legacy modules, although a compatibility namespace and wrapper are present; issue pending (6). [tests/unit/well_production_dashboard/test_well_production_dashboard.py:L1-L15] [src/worldenergydata/analysis/dashboard/__init__.py:L1-L10]
Legacy verification documentation advertises `worldenergydata.analysis.verification`, while the actual compatibility wrapper imports verification from the BSEE package; route reconciliation remains open, issue pending (6). [docs/modules/bsee/well_data_verification/cli_reference.md:L16-L34] [src/worldenergydata/analysis/dashboard/well_detail_views.py:L3-L6]

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-16 | Initial pack revision | Repeated estimator arithmetic is regression evidence; field recovery is a configured-data gate, not independent physical validation | [tests/unit/analysis/test_underpressured_screen.py:L44-L58] [src/worldenergydata/analysis/underpressured_screen/screen.py:L127-L138] | Reference limitation in sections 3–5 | Not assigned; issue pending (7) |

## 8. Ownership

Required review role: calculations quality manager, independent from the producer under AQG r0 section 11.
Requested deputy role: calculations quality-manager deputy; appointment and pack-index entry remain open with the maintainer, issue pending (7).
Escalation route for method, unit, tolerance and reference-source disagreements: the reviewing quality manager; unresolved acceptance requires a maintainer disposition, consistent with AQG r0 section 11.
No clearance is asserted by this DRAFT pack.

## 9. Dependencies and implementation inventory

| Dependency | Relationship and evidence |
| --- | --- |
| pandas, NumPy, PyYAML | Table arithmetic and configuration imports, exercised through the estimator and loader. [src/worldenergydata/analysis/underpressured_screen/screen.py:L22-L28] [src/worldenergydata/analysis/underpressured_screen/screen.py:L35-L65] [src/worldenergydata/analysis/underpressured_screen/observations.py:L57-L82] |
| Parquet backend | Parquet read/write boundaries; the root dependency specifies `pyarrow`. [src/worldenergydata/analysis/underpressured_screen/observations.py:L65-L69] [src/worldenergydata/analysis/underpressured_screen/screen.py:L202-L207] [pyproject.toml:L119-L121] |
| Source observation contracts | Four configured input schema IDs and source/era labels; paths and identifying values are intentionally omitted here. [config/underpressured_screen.yml:L7-L34] |
| Dashboard implementation | Canonical component algorithms are owned by `worldenergydata.well_production_dashboard`, outside this package. [src/worldenergydata/analysis/dashboard/well_detail_views.py:L1-L8] [packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/well_detail_views.py:L7-L39] |
| Verification compatibility export | Delegates to `worldenergydata.bsee.analysis.well_data_verification`. [src/worldenergydata/analysis/dashboard/well_detail_views.py:L3-L5] |

Implementation-map evidence: `digitalmodel`, `docs/registry/implementation-map.yaml`, map commit `21f0a121ffacbd63b97af00f873e8089effa6c3b`, source data revision `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; the map identifies its source repository and revision. [digitalmodel@21f0a121ffacbd63b97af00f873e8089effa6c3b:docs/registry/implementation-map.yaml:L1-L4]

Map inventory for this package: **0 families, 0 rows** across the inspected 13 families; no row path lies below the header package path. The counted-family grep is **NOT_APPLICABLE**, because no map family has an implementation row in this package. This empty-inventory result does not qualify unmapped methods. [digitalmodel@21f0a121ffacbd63b97af00f873e8089effa6c3b:docs/registry/implementation-map.yaml:L339-L26478]

Map follow-up, issue pending (8): register observation normalization, static gas-column BHP estimation, gradient tier classification, earliest-observation selection, group ranking, recovery/participation gates and metadata serialization, with the section-3 implementations as candidate rows. [src/worldenergydata/analysis/underpressured_screen/observations.py:L30-L176] [src/worldenergydata/analysis/underpressured_screen/screen.py:L40-L251]

A separate whole-repository search, including `scripts/` and workspace member packages, used the following command at the pin; it found the pressure implementation in `screen.py`, normalization in `observations.py`, and repeated correction arithmetic in the regression test, without another matching formula implementation outside the package. This signal-bounded finding does not establish mathematical uniqueness. [src/worldenergydata/analysis/underpressured_screen/screen.py:L40-L65] [src/worldenergydata/analysis/underpressured_screen/observations.py:L30-L54] [tests/unit/analysis/test_underpressured_screen.py:L55-L58]

```bash
git grep -n -E '0\.01875|static_gas_column_avg_zt|def (estimate_bhp|earliest_per_well|rank_fields|normalize_observations|classify_tiers|run_validation_gate)' 3a5d87fba8d476ff2367e7256ef176fed5672492 -- '*.py'
```

## 10. Coverage and open items

### Files and tests examined

All six package Python files are covered: root `__init__.py`; dashboard `__init__.py` and `well_detail_views.py`; pressure-screen `__init__.py`, `observations.py` and `screen.py`. [src/worldenergydata/analysis/__init__.py:L1-L9] [src/worldenergydata/analysis/dashboard/__init__.py:L1-L10] [src/worldenergydata/analysis/dashboard/well_detail_views.py:L1-L8] [src/worldenergydata/analysis/underpressured_screen/__init__.py:L1-L9] [src/worldenergydata/analysis/underpressured_screen/observations.py:L1-L176] [src/worldenergydata/analysis/underpressured_screen/screen.py:L1-L262]
The module tests are `tests/unit/analysis/test_underpressured_screen.py` and `tests/unit/analysis/test_underpressured_observations.py`; the two compatibility-related test files and `tests/contracts` are additional executed coverage. [tests/unit/analysis/test_underpressured_screen.py:L1-L22] [tests/unit/analysis/test_underpressured_observations.py:L1-L10] [tests/unit/well_production_dashboard/test_well_detail_views.py:L19-L28] [tests/unit/well_production_dashboard/test_well_production_dashboard.py:L1-L15] [tests/contracts/test_assetutilities_engine_contract.py:L13-L31]

Documentation discovery used `rg -l 'worldenergydata\.analysis|analysis/underpressured_screen|analysis/dashboard' docs --glob '*.md' --glob '*.rst'`. The current screen document and configuration were read; the discovered plans and legacy guides are reference context rather than verified execution instructions. [docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md:L21-L60] [config/underpressured_screen.yml:L1-L71]

| Discovered document | Coverage and supporting lines |
| --- | --- |
| `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md` | Method and caveats read; historic numerical results not requalified. [docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md:L21-L155] |
| `docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md` | Historical integration plan; executable-route reconciliation pending (6). [docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md:L1-L10] |
| `docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md` | Historical source adapter plan; route reconciliation pending (6). [docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md:L1-L10] |
| `docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md` | Historical production-source plan; reference context only, pending (6). [docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md:L1-L10] |
| `docs/plans/2026-07-04-issue-751-colorado-ecmc-form5a-ingest.md` | Historical initial-test-source plan; reference context only, pending (6). [docs/plans/2026-07-04-issue-751-colorado-ecmc-form5a-ingest.md:L1-L10] |
| `docs/modules/python-ds-engineer/SS_spec_priority_guide.md` | Legacy module priorities; no maturity/count claims adopted, pending (6). [docs/modules/python-ds-engineer/SS_spec_priority_guide.md:L65-L100] |
| `docs/modules/bsee/well_data_verification/api_reference.md` | Legacy verification import references; full-route audit pending (6). [docs/modules/bsee/well_data_verification/api_reference.md:L16-L24] |
| `docs/modules/bsee/well_data_verification/bsee_integration.md` | Legacy verification import references; full-route audit pending (6). [docs/modules/bsee/well_data_verification/bsee_integration.md:L64-L72] |
| `docs/modules/bsee/well_data_verification/cli_reference.md` | Legacy verification command references; full-route audit pending (6). [docs/modules/bsee/well_data_verification/cli_reference.md:L16-L34] |
| `docs/modules/bsee/well_data_verification/configuration_guide.md` | Legacy verification import references; full-route audit pending (6). [docs/modules/bsee/well_data_verification/configuration_guide.md:L29-L37] |
| `docs/modules/bsee/well_data_verification/troubleshooting.md` | Legacy import-error guidance; full-route audit pending (6). [docs/modules/bsee/well_data_verification/troubleshooting.md:L15-L23] |
| `docs/modules/bsee/well_data_verification/user_guide.md` | Legacy verification command references; full-route audit pending (6). [docs/modules/bsee/well_data_verification/user_guide.md:L86-L109] |
| `docs/modules/bsee/well_data_verification/workflow_tutorial.md` | Legacy verification commands; full-route audit pending (6). [docs/modules/bsee/well_data_verification/workflow_tutorial.md:L62-L70] |

### Open-item register

Every item below is assigned to the maintainer for issue filing and to the reviewing quality manager for acceptance; pending numbers refer to the numbered [issue drafts](ISSUES_DRAFT.md), each with a title, problem and acceptance criteria. These are drafts, not filed issues.

| Item | Remaining work and evidence | Tracking |
| --- | --- | --- |
| O1 | Establish independently sourced gas-column coefficient, units, calibration, tier applicability and numeric validation; reject nonfinite or non-positive depth and pressure with counted exclusions and regressions for S52; the unresolved physical basis remains as stated in section 3. [src/worldenergydata/analysis/underpressured_screen/screen.py:L35-L82] | [issue pending (1)](ISSUES_DRAFT.md#draft-1-validate-pressure-inputs-and-establish-an-independent-benchmark) |
| O2 | Add explicit normalization, Boolean and numeric 1/0 flag, identifier, empty-source and quality-metadata completeness checks for S01–S19. [src/worldenergydata/analysis/underpressured_screen/observations.py:L30-L176] | [issue pending (2)](ISSUES_DRAFT.md#draft-2-validate-normalization-numeric-flags-and-source-completeness) |
| O3 | Preserve actual selected-record identity, missing-data counts, deterministic ties and group identity across sources; audit S26–S33 and S39, S45–S48. [src/worldenergydata/analysis/underpressured_screen/screen.py:L86-L124] [src/worldenergydata/analysis/underpressured_screen/screen.py:L219-L232] | [issue pending (3)](ISSUES_DRAFT.md#draft-3-preserve-selected-record-identity-and-complete-ranking-counts) |
| O4 | Reject vacuous gates; publish outputs transactionally; retain input digests and signed QA evidence; implement C11 and missing S35–S44 checks. [src/worldenergydata/analysis/underpressured_screen/screen.py:L127-L215] | [issue pending (4)](ISSUES_DRAFT.md#draft-4-reject-vacuous-gates-and-publish-accepted-outputs-transactionally) |
| O5 | Add invalid-date, null-object and general metadata round-trip fidelity coverage; the existing R4 asserts selected row counts only. [src/worldenergydata/analysis/underpressured_screen/screen.py:L235-L251] [tests/unit/analysis/test_underpressured_screen.py:L494-L501] | [issue pending (5)](ISSUES_DRAFT.md#draft-5-test-metadata-and-invalid-date-round-trip-fidelity) |
| O6 | Reconcile legacy guides, test skip and dashboard delegate ownership; complete the broader downstream algorithm/documentation audit before claiming dashboard-method qualification. [tests/unit/well_production_dashboard/test_well_production_dashboard.py:L1-L15] [packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/well_detail_views.py:L7-L39] | [issue pending (6)](ISSUES_DRAFT.md#draft-6-reconcile-compatibility-routes-and-the-dashboard-test-skip) |
| O7 | UNVERIFIED: historic run totals and current source-dataset readiness are not established from the offline fixtures; obtain versioned input manifests, source identities, units, digests and native readback before adopting historic results; appoint the deputy and record the pack/shared-log index. [docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md:L62-L90] [src/worldenergydata/analysis/underpressured_screen/observations.py:L65-L82] | [issue pending (7)](ISSUES_DRAFT.md#draft-7-qualify-source-readiness-and-record-pack-ownership) |
| O8 | Add the section-3 method families to the implementation map before future counted-family searches apply. [src/worldenergydata/analysis/underpressured_screen/screen.py:L40-L156] [src/worldenergydata/analysis/underpressured_screen/observations.py:L30-L176] | [issue pending (8)](ISSUES_DRAFT.md#draft-8-register-the-analysis-method-families-in-the-implementation-map) |
| O9 | Replace identifying data labels in tests and documentation with approved dataset IDs before reusing their text in new public artifacts; values are not reproduced here by name. [tests/unit/analysis/test_underpressured_screen.py:L32-L40] [tests/unit/analysis/test_underpressured_observations.py:L13-L27] | [issue pending (9)](ISSUES_DRAFT.md#draft-9-replace-identifying-labels-with-neutral-dataset-ids) |

No routing registry is supplied with this change; the pack remains at the package's documented knowledge-pack location rather than creating a new registry schema.
The calculation-citation contract was readable; no standards-derived constant or module code is introduced by this documentation change, and the unresolved coefficient source remains O1.
