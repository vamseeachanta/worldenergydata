# Drilling pressure management knowledge pack

| Header | Value |
| --- | --- |
| Module | `drilling_pressure_management` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management` |
| Pack revision | 2, 2026-10-22 |
| Code pin | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` |
| Analysis family | EC; Python calculations gate set for a data pipeline |
| Quality role | Calculations quality manager; data quality manager appointment pending |
| Status | DRAFT; second-provider clearance required |
| Evidence convention | Repository citations resolve at the code pin; execution observations are identified separately |

## 1. Purpose and scope

The analyzer now reports fractional ECD position and applies explicit caller policy to both window width and boundary margin. Annular loss is required. Known type queries include multi-mode candidates; catalog inclusion does not establish equipment suitability.

### Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-16 | Initial cited contracts, regression examples and open items |
| 1 | 2026-10-16 | Add missing failure modes, full test nodes and an ECD magnitude check; correct the Alpha citation and issue references |
| 2 | 2026-10-22 | Use ECD position in MPD assessment, require annular loss and policy, and include multi-mode candidates. |

### Current implementation update, revision 2

The position is `(ECD-pore)/(fracture-pore)`. MPD assessment is flagged if width is below the caller's `threshold_psi`, or position lies outside `[margin, 1-margin]`, where `minimum_window_margin_fraction` is a required caller input. Boundary equality is admissible. No universal threshold has been established by the reviewed sources; the removed implicit width threshold is not an engineering criterion. `analyze` requires finite physical inputs, positive depth/mud/window and nonnegative flow/loss. The returned `ecd_window_position` exposes the arithmetic.

The retained rounded hydrostatic conversion follows NIST SP 811 (2008), Appendix B.8 (pound, US gallon, foot and psi); the existing ECD convention and its rounding are unchanged. The analyzer uses supplied annular loss, not a flow-rate correlation.

| Finding | Current detection nodes |
| --- | --- |
| #1290 SF1: ECD position ignored | `tests/unit/drilling_pressure_management/test_pressure_regressions.py::test_mpd_depends_on_ecd_position`; `tests/unit/drilling_pressure_management/test_pressure_regressions.py::test_ecd_below_pore_requires_assessment`; `tests/unit/drilling_pressure_management/test_pressure_regressions.py::test_both_window_margin_boundaries` |
| #1290 SF2: multi-mode omitted | `tests/unit/drilling_pressure_management/test_pressure_regressions.py::test_multi_mode_in_every_known_type_query` |
| #1290 SF3: silent annular-loss default | `tests/unit/drilling_pressure_management/test_pressure_regressions.py::test_annular_loss_and_policy_required` |
| Invalid inputs or policy | `tests/unit/drilling_pressure_management/test_pressure_regressions.py::test_invalid_loss_refused`; `tests/unit/drilling_pressure_management/test_pressure_regressions.py::test_invalid_policy_refused` |

Remaining limits: the flag calls for assessment and does not prove MPD feasibility. Multi-mode entries are discovery candidates for each known type, not claims of qualification for every mode; `multi_mode` still has no single configuration definition. Stored capability currency, pressure datum, case-sensitive catalog queries, referential integrity, absent capability counts and package-data questions remain as recorded below.

Source: [NIST SP 811 (2008), Appendix B.8](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf). The fractional-position rule is explicit caller policy, not a sourced universal acceptance threshold.

### Historical inventory boundary

Sections 2–10 below retain the inventory, citations, execution records and open
limits at the historical code revision. Findings corrected by the current update
are historical evidence; the current contracts and detection nodes above supersede
those earlier behavior statements and test counts. Remaining limits are retained.


## 2. Inputs and outputs

### Inputs

| Input | Unit | Allowed range / default | Source and behavior |
| --- | --- | --- | --- |
| `depth_m` | m | Required float; no runtime range check | True vertical depth in `analyze`. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L214] |
| `pore_pressure_psi` | psi | Required float; no runtime range check | Formation pressure, subtracted from the fracture pressure. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L193-L214] |
| `fracture_gradient_psi` | psi, not psi per length | Required float; no runtime range check | Docstring calls it a pressure; subtraction uses it directly. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L193-L214] |
| `mud_weight_ppg` | pounds/gallon | Required float; no runtime range check | Multiplied by the conversion coefficient and depth. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L216-L233] |
| `flow_rate_gpm` | gallons/minute | Required float; unused | Accepted by `analyze`, absent from its calculation body. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L214] |
| `annular_pressure_drop_psi` | psi | 200.0 default in `analyze`; explicit in `ecd_pressure` | Added to hydrostatic pressure. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L233] |
| `threshold_psi` | psi | 200.0 default | Strict less-than comparison; equality returns false. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L235-L246] |
| `config_type`, `system_id` | dimensionless string | Exact keys; no default | Unknown keys raise `KeyError`. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L249-L261] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L164-L171] |
| `mpd_type`, `rig_type`, `contractor` | dimensionless string | Exact matching; no normalization | Filters return lists, including empty lists. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L174-L181] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L173-L175] |

### Outputs and record schemas

| Output | Unit / contents | Source |
| --- | --- | --- |
| `PressureWindow` | Depth in m; pore, fracture, ECD and window pressures in psi; `mpd_required` boolean | Dataclass fields and construction. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L162-L171] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L204-L214] |
| `MPDConfiguration` | `config_type`, `full_name`, `description`, `pressure_control`; string lists of applications, equipment, advantages and limitations | No numeric unit fields. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L11-L22] |
| `MPDSystemEntry` | IDs/text, pressure rating in psi, flow rating in gpm, equipment and compatibility strings, reference strings, notes | No validation methods are declared on the record. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L13-L29] |
| `RigMPDCapability` | Identity strings, capability flags, optional system/manufacturer/year and notes | Optional values default only for notes; other fields are constructor arguments. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L14-L26] |
| `systems_summary()` | DataFrame: `system_id`, `manufacturer`, `product_name`, `mpd_type`, pressure/flow ratings, `rcd_type`, `integration_level` | One row per stored system; reference strings and compatibility lists are omitted. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L184-L199] |
| `fleet_mpd_summary()` | DataFrame: `contractor`, `total_rigs`, `mpd_capable_count`; counts in records | Group counts, sorted by contractor string. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L178-L201] |

The reviewed analyzer uses scalar true vertical depth and pressures, with no coordinate-frame, origin or phase argument and no external file reader/writer. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L246]
UNVERIFIED: the pressure datum, gallon convention and physical admissibility envelope are not established by an independent reference; issue pending (3).

## 3. Method and governing standards

| Method | Implementation and basis | Qualification |
| --- | --- | --- |
| Hydrostatic plus annular loss | `depth_ft = depth_m * 3.28084`; `ecd_psi = mud_weight_ppg * 0.052 * depth_ft + annular_pressure_drop_psi`. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L177-L178] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L216-L233] | Code coefficients, not values attributed to a licensed standard. Independent coefficient provenance remains open in item 3. |
| Available window | `fracture_gradient_psi - pore_pressure_psi`; `analyze` delegates the threshold decision to `mpd_required`. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L204-L214] | Arithmetic regression, not a verified well-control criterion. |
| Requirement flag | `pressure_window_psi < threshold_psi`; default threshold is 200.0 psi. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L235-L246] | Configurable software criterion; no governing standard is cited by this function. |
| Configuration taxonomy | Four records with types `CBHP`, `PMCD`, `dual_gradient`, `RFC`; index by `config_type`. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L25-L159] | Descriptive records rather than a configuration-selection algorithm. |
| System filtering | Index lookup, equality by type, membership by compatible rig type. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L161-L181] | Filters do not compare operating pressure or flow to ratings. |
| Capability aggregation | Filter a boolean, exact contractor match, count and tabulate. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L168-L201] | Counts describe the stored list, not complete current market coverage. |

No standard edition, clause reference or `Citation` sidecar is present in the analyzer implementation; the coefficient and threshold definitions have no attached provenance. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L174-L246]
UNVERIFIED: independent accuracy and engineering applicability of the coefficients and default threshold remain unestablished; issue pending (3).
Do not use this implementation as its own independent hand-check reference.

## 4. Validated worked examples

Validated examples: **0**. The following **5 regression examples** use expectations encoded by the repository tests; none is presented as independent engineering validation. [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L92-L100] [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L152-L168] [tests/unit/drilling_pressure_management/test_fleet_mpd.py:L145-L155] [tests/unit/drilling_pressure_management/test_mpd_systems.py:L163-L169]

Inputs are literals or the in-module stored lists, with no external input file. [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L92-L100] [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L152-L168] [tests/unit/drilling_pressure_management/test_fleet_mpd.py:L145-L155] [tests/unit/drilling_pressure_management/test_mpd_systems.py:L163-L165]

| Case | Expected value and tolerance basis | Existing test node | Last offline result |
| --- | --- | --- | --- |
| R1 window subtraction | 4500.0 − 4000.0 = 500.0 psi; `pytest.approx(500.0)`, implicit library tolerance; proposed pack comparison ≤ 0.0005 psi | `tests/unit/drilling_pressure_management/test_mpd_configurations.py::TestPressureWindowAnalyzer::test_pressure_window_equals_fracture_minus_pore` [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L92-L100] | BASE PASS; AFTER PASS |
| R2 preserved depth | 1500.0 m; `pytest.approx(1500.0)`, implicit library tolerance; proposed pack comparison ≤ 0.0015 m | `tests/unit/drilling_pressure_management/test_mpd_configurations.py::TestPressureWindowAnalyzer::test_analyze_preserves_depth_in_result` [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L152-L160] | BASE PASS; AFTER PASS |
| R3 threshold sides | 199.9 psi → true; 200.1 psi → false; 0 boolean mismatches | `tests/unit/drilling_pressure_management/test_mpd_configurations.py::TestPressureWindowAnalyzer::test_mpd_required_helper_boundary_at_200` [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L162-L164] | BASE PASS; AFTER PASS |
| R4 capability totals | Summary total equals stored list length; 0 records difference | `tests/unit/drilling_pressure_management/test_fleet_mpd.py::TestFleetMPDSummary::test_total_rigs_sum_matches_fleet` [tests/unit/drilling_pressure_management/test_fleet_mpd.py:L145-L147] | BASE PASS; AFTER PASS |
| R5 catalog rows | Summary rows equal catalog length; 0 rows difference | `tests/unit/drilling_pressure_management/test_mpd_systems.py::TestSystemsSummary::test_dataframe_row_count_matches_catalog` [tests/unit/drilling_pressure_management/test_mpd_systems.py:L163-L165] | BASE PASS; AFTER PASS |

Execution observation for this revision, with module code unchanged from the code pin: BASE 83 run / 83 passed / 0 failed / 0 skipped / 0 NOT_RUN; AFTER 83 run / 83 passed / 0 failed / 0 skipped / 0 NOT_RUN. All five node IDs above passed in both runs. No solver is required by these three test files. [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L1-L12] [tests/unit/drilling_pressure_management/test_fleet_mpd.py:L1-L12] [tests/unit/drilling_pressure_management/test_mpd_systems.py:L1-L13]

The source-enabled test command is `uv run --no-project --with pytest --with 'pandas>=2.3.3,<3' --with pytest-cov --with pytest-asyncio --with psutil --with plotly --with pyyaml --with 'pydantic>=2.13.4,<3' --with pydantic-settings python -m pytest tests/unit/drilling_pressure_management -q -rA -p no:cacheprovider --basetemp=<scratch> --cov-report= --cov-report=json:<scratch>/coverage.json`, with repository `addopts` retained and coverage data directed outside the checkout. `PYTHONPATH` includes `src`, `packages/worldenergydata-core/src`, `packages/worldenergydata-drilling_pressure_management/src` and the sibling utility source; `COVERAGE_FILE` is also directed to scratch. AFTER additionally uses `--allow-existing-tree-changes` to fingerprint the pre-existing pack and reject new undeclared writes, as documented by the repository. [docs/development/index.md:L56-L59]

## 5. QA gates

Apply AQG r0, section 10, Python calculations row and G5; section 11 requires independent clearance.

| Gate | Applicability | Module-specific executable check and numeric pass criterion | Evidence / disposition |
| --- | --- | --- | --- |
| G0 | Applicable | C0a: run `tests/unit/drilling_pressure_management/test_mpd_systems.py::TestMPDSystemsCatalog::test_all_max_pressure_ratings_positive` and `tests/unit/drilling_pressure_management/test_mpd_systems.py::TestMPDSystemsCatalog::test_all_max_flow_rates_positive`; 0 records at or below 0 psi or 0 gpm. [tests/unit/drilling_pressure_management/test_mpd_systems.py:L43-L53] | Test results; data consistency only. |
| G0 | Applicable | C0b: audit `analyze` and `PressureWindow`: 0 mismatches between seven numeric inputs' documented units and their use (m, psi, pounds/gallon, gpm); explicitly record the unused flow argument. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L214] | Unit audit; physical input validation remains item 1. |
| G1 | Applicable | C1: import through the tests and run all three test files; 83 passed tests, 0 failures, 0 skipped tests, 0 collection errors. [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L5-L12] [tests/unit/drilling_pressure_management/test_fleet_mpd.py:L6-L12] [tests/unit/drilling_pressure_management/test_mpd_systems.py:L6-L13] | Python import/test route; no program deck is written. |
| G2 | Applicable | C2a: calculate 4500.0 − 4000.0 independently with decimal arithmetic and compare `analyze(...).pressure_window_psi`; absolute difference ≤ 0.0005 psi. [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L92-L100] | Arithmetic check only; coefficient qualification remains item 3. |
| G2 | Applicable | C2b: call `mpd_required` at 199.9, 200.0 and 200.1 psi with a 200.0 psi threshold; expected true, false, false; 0 boolean mismatches. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L235-L246] | Boundary check; equality supplements R3. |
| G2 | Applicable | C2c: execute `PressureWindowAnalyzer().ecd_pressure(10.0, 3000.0, 300.0)`; compare with 5418.11 psi, calculated as 10.0 × 0.052 × 9842.52 + 300.0; absolute difference ≤ 0.01 psi. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L177-L178] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L216-L233] | Coefficient visibility and arithmetic consistency only; independent provenance remains item 3. |
| G3 | NOT_APPLICABLE | No transient integration or dynamics model is implemented by the analyzer. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L246] | No short dynamics run. |
| G4 | NOT_APPLICABLE | No diffraction mesh, hydrostatics or radiation calculation is implemented by the analyzer. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L246] | No diffraction evidence. |
| G5 | Applicable | C5: reconcile R1–R5 node IDs and results with both test logs at the pin; 5 of 5 cases traced, 0 missing results or pin mismatches. [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L92-L100] [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L152-L164] [tests/unit/drilling_pressure_management/test_fleet_mpd.py:L145-L147] [tests/unit/drilling_pressure_management/test_mpd_systems.py:L163-L165] | Pack evidence table; quality-manager clearance remains required. |

Checks defined: G0 = 2, G1 = 1, G2 = 3, G3 = 0, G4 = 0, G5 = 1; total = 7.
Execution observation: C0a, C0b, C1, C2a, C2b, C2c and C5 passed their stated consistency criteria; decimal subtraction differed by 0.0 psi, the threshold probe had 0 boolean mismatches, and ECD was within 0.01 psi of 5418.11 psi. A passed consistency or arithmetic check does not close the provenance gaps in section 10.

C2c can be run in the same source-enabled environment:

```python
from worldenergydata.drilling_pressure_management import PressureWindowAnalyzer

assert abs(PressureWindowAnalyzer().ecd_pressure(10.0, 3000.0, 300.0) - 5418.11) <= 0.01
```

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom / cause | Detection and disposition | Reference at the code pin |
| --- | --- | --- |
| Changing `flow_rate_gpm` does not change results; the supplied annular loss controls the friction term | C0b records the unused argument; no detection check exists for flow sensitivity; issue pending (1) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L214] |
| Negative or nonfinite inputs are not rejected; `fracture_gradient_psi` expects a pressure, so supplying a gradient can create an inverted window and a true flag | C0b audits units only; no detection check exists for finite/range rejection or the naming trap; issue pending (1) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L193-L246] |
| Stored capability and rating assertions can pass without proving current equipment capability | C0a checks positive ratings only; no detection check exists for source accuracy or currency; issue pending (2) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L13-L29] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L14-L26] |
| Metres, pounds/gallon and psi are assumed; 0.052 and 3.28084 lack independent qualification, while existing ECD tests check positivity and monotonicity | C2c checks magnitude against the written expression; C0b audits declared units; no detection check exists for pressure datum, gallon convention or independent coefficient accuracy; issue pending (3) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L177-L178] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L216-L233] [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L122-L150] |
| Recursive Markdown package-data selection matches the documentation location | No detection check exists for built-wheel exclusion; issue pending (4) | [packages/worldenergydata-drilling_pressure_management/pyproject.toml:L48-L54] |
| SF1: `mpd_required` uses only window width; ECD outside the pore/fracture bounds can accompany a false flag | No detection check exists for ECD position versus the flag; #1290; issue pending (1) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L204-L214] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L235-L246] |
| SF2: the stored `multi_mode` system is absent from all four configuration-type queries; its type is not a configuration key | No detection check exists for catalog-to-configuration type coverage; #1290; issue pending (1) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L33-L46] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L174-L176] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L249-L261] |
| SF3: omitted `annular_pressure_drop_psi` silently adds 200.0 psi, even for static or unknown-friction input; the result does not expose the default used | No detection check exists for omitted loss or default disclosure; R1 and R2 inherit it; #1290; issue pending (1) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L214] |
| Exact-match queries given case or spelling variants for contractor, system type or rig type return empty lists, indistinguishable from a valid query with no matches | No detection check exists for normalization or query validation; issue pending (2) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L173-L175] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L174-L181] |
| Rig `mpd_system` references and rig-type compatibility can drift without a referential integrity test | No detection check exists for catalog-id resolution and membership in `compatible_rig_types`; issue pending (2) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L14-L26] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L13-L29] |
| Zero-default integer count dictionaries treat an absent capable count as zero; truth-value filtering trusts stored capability flags | R4 reconciles total records only; no detection check exists for absent versus false capability data; issue pending (2) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L168-L170] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L178-L201] |
| The 200.0 psi threshold default is a configurable software boundary without independent engineering qualification | C2b checks strict comparison only; no detection check exists for the physical threshold basis; issue pending (3) | [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L187-L188] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L235-L246] |

Sweep: 12 documented failure modes and pitfalls, including SF1–SF3 in #1290. All four package Python files were read at the code pin. The sweep found 0 swallowed exceptions, 0 record-skipping `continue` statements, 0 `return None` or literal empty-result returns on error paths, 0 external-text numeric conversions, 0 date defaults and 0 cache writes. Empty filter results, zero-default aggregation, numeric defaults and unit assumptions are covered above. Unknown index keys raise `KeyError`, rather than returning an empty result. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L249-L256] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L164-L171]

The exact discovery commands, run from the repository root, were:

```sh
package=packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|int\(|float\(|0\.052|3\.28084|200\.0|cache|default|units' "$package" --glob '*.py'
rg -n 'except|continue|return|default|float\(|int\(|psi|gpm|ppg|_m\b' "$package" --glob '*.py'
```

#1290 tracks the three confirmed analyzer/catalog failures. The other rows identify limitations and missing evidence; issue pending (1)–(5) remain drafts in section 10.

## 7. Lessons log

| Date | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-16 | Keep supplied annular loss distinct from flow-rate-driven hydraulics | `analyze` calls `ecd_pressure` without flow rate. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L204-L214] | Sections 1–3 and 6 distinguish arithmetic from hydraulics | Proposed; issue pending (1) |

## 8. Ownership

Proposed review route: calculations quality manager; deputy: data quality manager when appointed. Escalate unresolved engineering criteria to the family quality manager and cross-family ownership to the maintainer. Apply AQG r0 section 11 independence; clearance shall come from a provider different from the producer.
No clearance is asserted by this DRAFT pack.

## 9. Dependencies and implementation inventory

The package declares `worldenergydata-core` and `pandas>=2.3.3,<3.0`; the summaries use pandas DataFrames. [packages/worldenergydata-drilling_pressure_management/pyproject.toml:L29-L32] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L184-L199] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L178-L201]
The package initializer re-exports the three module APIs. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/__init__.py:L3-L48]

Implementation-map observation: map repository `digitalmodel`, branch `codex/implmap-work`, read at data commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; its header names searched code revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`.
Inventory: 13 map families inspected, 0 implementation rows inside this package, 0 module map families, 0 counted families, empty implementation inventory. A8 inventory passes with an empty inventory; counted-family grep is `NOT_APPLICABLE` because no map family has an in-package row.
Map follow-up, issue pending (5): add the section-3 method families (hydrostatic-plus-annular-loss pressure, pressure-window subtraction, threshold classification, configuration taxonomy, system filtering and capability aggregation) before counting them in a later map revision.

Additional discovery at the code pin searched all tracked Python files across the repository, including `scripts/`, with `PressureWindowAnalyzer|def ecd_pressure|def mpd_required|pressure_window_psi|0\.052.*3\.28084|FLEET_MPD_DATA`: 34 line hits, confined to this package and its tests. The calculation definitions are `PressureWindowAnalyzer.analyze`, `.ecd_pressure` and `.mpd_required`; the initializer is a re-export and tests are regression consumers. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L180-L246] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/__init__.py:L10-L17] [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L78-L168]
This supplementary search is a symbol/formula search, not proof of absence of differently named implementations; it does not alter A8.

A broader supplementary search used `0\.052|pressure_window|hydrostatic.*pressure|mud_weight_ppg|annular_pressure_drop` across tracked Python source and scripts: 69 matching lines in eight files. The following outside-package methods compute related results and belong in the map follow-up, issue pending (5); none is an in-package A8 miss.

| Outside-package definition | Classification and evidence |
| --- | --- |
| `WellBoreHydraulics.ecd_ppg` | Related ECD calculation returning ppg rather than pressure; computes its own expression. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/hydraulics.py:L106-L120] |
| `BoreTypeDecision.pressure_window_check` | Delegates hydraulics but computes its own available-window and compatibility criteria in ppg. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L178-L220] |
| `WellBoreDesign.pressure_window_ppg` | Computes max-minus-min mud-weight window, with a zero sentinel. [packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L78-L82] |
| `ONGFDComponents.get_drilling_completion_summary` | Computes its own hydrostatic-style reservoir-pressure estimate with an offset and overbalance term. [packages/worldenergydata-core/src/worldenergydata/common/legacy/ong_fd_components.py:L1186-L1198] |
| `calculate_drilling_completion_summary` | Separate implementation of that reservoir-pressure estimate. [packages/worldenergydata-core/src/worldenergydata/common/legacy/ong_fd_summary.py:L92-L104] |

The two matched timeline scripts consume or display stored mud-weight values rather than compute hydrostatic pressure. [scripts/lower_tertiary/build_wells_facts.py:L87-L107] [scripts/lower_tertiary/build_well_timelines.py:L150-L165]

## 10. Coverage and open items

### Reading inventory

All four package Python files were read: `__init__.py`, `mpd_configurations.py`, `mpd_systems.py`, `fleet_mpd.py`; all three module test files and the empty test initializer were read. [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/__init__.py:L1-L48] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_configurations.py:L1-L261] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/mpd_systems.py:L1-L199] [packages/worldenergydata-drilling_pressure_management/src/worldenergydata/drilling_pressure_management/fleet_mpd.py:L1-L201] [tests/unit/drilling_pressure_management/test_mpd_configurations.py:L1-L168] [tests/unit/drilling_pressure_management/test_mpd_systems.py:L1-L169] [tests/unit/drilling_pressure_management/test_fleet_mpd.py:L1-L155]
The package README describes the namespace-package split and core dependency. [packages/worldenergydata-drilling_pressure_management/README.md:L1-L8]

Discovery documents read for module references:

- `docs/adr/0001-domain-package-split.md`. [docs/adr/0001-domain-package-split.md:L43-L49]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L180-L188]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L751-L759]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L74-L79]
- `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md`. [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L13-L19]
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`. [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L17-L23]

Historical readiness documents count three test files, not executed test cases. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L751-L759]
Execution counts are recorded in section 4; no maturity or validation figure from the historical reports is adopted.
Registry observation at the code pin: `docs/registry/module-routing.yaml` does not exist; no registry edit is proposed.

### Open-item register

| Item | Missing evidence / action | Responsibility | Tracking |
| --- | --- | --- | --- |
| 1 | Define invalid-input handling and the unused flow-rate contract; add ECD-position, type-coverage and omitted-loss detection tests for #1290; retain current module code in this documentation change | Calculation maintainer | issue pending (1) |
| 2 | UNVERIFIED: real-world accuracy, currency and source rights of stored catalog/capability assertions; qualify sources and codenaming before publishing record identities or using records as engineering input; add referential integrity tests for every non-null `mpd_system` and membership of the rig type in `compatible_rig_types`; define exact-match query and missing-capability behavior | Data maintainer | issue pending (2) |
| 3 | Resolve both earlier UNVERIFIED claims: pressure datum, gallon convention, admissibility envelope, coefficient provenance and independent threshold basis; add independent ECD examples and determine whether a standards-derived Citation sidecar is required | Calculation maintainer | issue pending (3) |
| 4 | Establish documentation exclusion from wheel data; existing recursive Markdown glob conflicts with the intended documentation-only delivery; wheel contents have not been built or inspected | Package maintainer | issue pending (4) |
| 5 | Add method families and package rows to the implementation map; retain A8 empty-inventory treatment until then | Map maintainer | issue pending (5) |
| 6 | Reconcile historical readiness/index coverage with the package path and executed test count | Documentation maintainer | #349 |

The distribution split remains tracked by #529; it is context, not a confirmed analyzer incident.
