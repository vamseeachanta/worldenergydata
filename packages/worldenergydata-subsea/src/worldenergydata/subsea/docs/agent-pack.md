# Subsea module knowledge pack

| Header | Value |
| --- | --- |
| Module | subsea |
| Repository | worldenergydata |
| Package path | `packages/worldenergydata-subsea/src/worldenergydata/subsea` |
| Pack revision | 2 |
| Code pin | `6149361d36373afe24fe1b0c1fe59886375d46b7` |
| Analysis family | EC; data pipeline; AQG r0 Python calculations gate set |
| Family review role | Calculations quality manager |
| Status | DRAFT |

## 1. Purpose and scope

The public API exposes `ManifoldSupplierLoader` and `ManifoldSupplierSchema`; the models subpackage exposes rigid-jumper and mooring-component schemas and CSV loaders. [packages/worldenergydata-subsea/src/worldenergydata/subsea/__init__.py:L3-L8] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/__init__.py:L3-L17]

The supplier loader reads UTF-8 CSV, validates rows and filters by role, tier, country and minimum water depth; the component loaders read CSV and construct Pydantic records. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L85] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L50-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L42-L55]

Scope includes every Python file in the package, including both subpackages; the implementing methods perform validation and selection rather than structural, pressure-containment or mooring-equilibrium analysis. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L70-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L25-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L24-L55] [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L93]

The module manifest labels subsea `stable`, while the distribution classifier labels it `Alpha`; these are declarations rather than independently established readiness (U2 in section 10). [module-manifest.yaml:L491-L504] [packages/worldenergydata-subsea/pyproject.toml:L15-L23]

### Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-16 | Initial package inventory, checks and open items. |
| 1 | 2026-10-16 | Add omitted silent paths, complete test references, distinguish issue drafts from filed issues and record executed CAD coverage. |
| 2 | 2026-10-16 | Include and link the ten issue drafts, distinguish downstream geometry from package validation and make CAD coverage conditional on its environment. |

## 2. Inputs and outputs

### Inputs

Ranges below describe implemented constraints; absence of a constraint is not an engineering acceptance criterion. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L131-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L13-L47] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L13-L39]

| Input | Unit or representation | Allowed range; default | Source and evidence |
| --- | --- | --- | --- |
| Supplier `csv_path` | filesystem path; UTF-8 CSV | optional; module data resolver plus `curated/manifold_suppliers.csv` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L22-L47] |
| Component `csv_path` | pandas CSV input | required; no default path | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L50-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L42-L55] |
| `COMPANY` | text | required; rejects null and whitespace-only text | [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L38-L41] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L70-L75] |
| `MANIFOLD_ROLE` | categorical text | `OEM`, `EPC`, `fabricator`, `subsystem_supplier`, `limited`; default `None` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L22-L29] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L49-L52] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L138-L145] |
| `ROLE_TIER` | categorical text | `tier_1`, `tier_2`, `niche`, `adjacency`; default `None` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L31-L32] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L49-L52] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L147-L152] |
| `MAX_WATER_DEPTH_M` | m, integer after coercion | inclusive 0 to 6000; default `None`; unknown and blank text become `None` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L54-L55] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L117-L136] |
| `TICKER`, `HQ_COUNTRY`, `HQ_CITY`, `PARENT_OR_JV`, `MARKET_POSITION`, `DATA_SOURCE_URL`, `COLLECTION_DATE`, `NOTES` | text; no date or URL parser | optional `None`; blank text becomes `None` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L43-L66] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L77-L94] |
| `PRODUCT_LINES`, `NOTABLE_PROJECTS`, `RECENT_DEVELOPMENTS`, `DATA_SOURCE_URLS` | lists of text or text separated by literal ` \| ` | default empty lists; strip elements and discard empty fragments | [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L19-L20] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L57-L61] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L96-L115] |
| Jumper identifiers, `manufacturer`, `material_grade`, `data_source` | required strings | no domain enumeration or nonempty-string validator | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L13-L47] |
| `od_in`, `wall_thickness_in` | inches at the downstream CAD boundary | required; each positive, but no relationship enforced between them | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L15-L16] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L25-L39] [src/worldenergydata/field_development/equipment_3d.py:L53-L76] |
| `length_ft` | feet at the downstream CAD boundary | required; no positivity validator | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L17-L47] [src/worldenergydata/field_development/equipment_3d.py:L53-L76] |
| `pressure_rating_psi`, `weight_air_kips` | unresolved metadata; U1 | pressure required and positive; weight defaults to `None` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L19-L20] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L41-L47] [data/catalog.yaml:L1785-L1800] |
| `connection_type`, jumper `notes` | text | optional `None` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L20-L23] |
| Mooring identifiers, `manufacturer`, `data_source` | required strings | no nonempty-string validator | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L13-L39] |
| `component_type` | categorical text | required; `chain`, `wire_rope`, `polyester_rope`, `anchor`, `connector` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L24-L31] |
| `size_mm`, `mbl_kn` | mm; kN | both required; only MBL has positivity validator | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L16-L17] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L33-L39] [data/catalog.yaml:L1730-L1737] |
| `weight_kg_per_m` | unresolved metadata; U1 | optional `None`; catalog labels it kg | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L18-L22] [data/catalog.yaml:L1738-L1741] |
| Mooring `material`, `grade`, `notes` | text | optional `None` | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L18-L22] |
| Query `role`, `tier`, `country`, `min_water_depth_m` | text; depth in m | all optional `None`; role and tier use exact equality; country uses case-insensitive substring; depth is inclusive minimum | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L59-L85] |
| `get(company)` | text substring | required; case-insensitive, first match | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L87-L93] |

### Outputs

| Output | Unit or representation | Behavior | Evidence |
| --- | --- | --- | --- |
| `all()` | list of supplier records | copy of cached list, with shared model objects | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L57] |
| `query()` | list of supplier records | retained matches; unknown country/depth can remove rows | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L68-L85] |
| `get()` | supplier record or `None` | first substring match or no match | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L87-L93] |
| `load_rigid_jumpers()` | list of `RigidJumperSpec` | lowercases column keys and omits missing cells | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L59-L63] |
| `load_mooring_components()` | list of `MooringComponentSpec` | lowercases column keys and omits missing cells | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L51-L55] |

These records carry dimensions and classifications, with no coordinate arrays, origin, sign or phase transformation in the package; coordinate and phase conventions are therefore not applicable to these outputs. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L13-L23] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L13-L22] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L40-L66]

## 3. Method and governing standards

| Method family | Implementing definitions | Rule and evidence |
| --- | --- | --- |
| Supplier scalar validation | `ManifoldSupplierSchema._require_company`, `_empty_str_to_none`, `_validate_role`, `_validate_tier` | Required company, blank-to-null conversion and membership checks. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L70-L94] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L138-L152] |
| Supplier list normalization | `ManifoldSupplierSchema._split_list_fields` | Literal delimiter splitting; strips fragments and converts list/tuple elements to strings. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L96-L115] |
| Depth normalization and bounds | `ManifoldSupplierSchema._coerce_depth`, `_validate_depth` | String input uses `int(float(v))`; float input uses `int(v)`; subsequent inclusive bounds check. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L117-L136] |
| Supplier CSV ingestion and selection | `ManifoldSupplierLoader.__init__`, `_load`, `all`, `query`, `get` | Lazy CSV load into a per-instance cache; filters and first substring match. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L35-L93] |
| Jumper validation and ingestion | `RigidJumperSpec.od_positive`, `wall_thickness_positive`, `pressure_positive`; `load_rigid_jumpers` | Three scalar positivity criteria followed by pandas row construction; no geometric solver. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L25-L63] |
| Mooring validation and ingestion | `MooringComponentSpec.valid_type`, `mbl_positive`; `load_mooring_components` | Component-category membership and positive MBL; pandas row construction. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L24-L55] |

No governing engineering standard, edition, clause or standards-derived formula is declared by these implementations; no standards-derived numeric output or `Citation` sidecar is produced by them. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L1-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L1-L55] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L1-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L1-L93]

AQG r0, *Analysis QA gates*, revision 0, section 10, Python calculations, supplies the G0/G1/G2 gate set; sections 9 and 11 supply G5 and independent review requirements. (AQG r0, sections 9–11.)

## 4. Validated worked examples

Validated examples for this package: 0. One downstream analytical geometry example (V1) validates `field_development.equipment_3d.jumper_volume_mm3` against the annulus-volume formula; it does not validate a method in this package. The five regression examples below check parser expectations and repository-maintained data; physical catalogue accuracy remains UNVERIFIED under U3. [tests/unit/subsea/test_manifold_suppliers.py:L32-L70] [tests/unit/curated/test_csv_validation.py:L24-L110] [tests/modules/field_development/test_equipment_3d.py:L52-L61]

### Validated analytical geometry example

| ID | Synthetic input and independent reference | Expected volume (mm³) | Observed volume (mm³) | Criterion and existing test node ID | Baseline / final |
| --- | --- | --- | --- | --- | --- |
| V1 | OD 8.0 in, wall thickness 0.500 in, length 50.0 ft; reference is π × ((OD/2)² − ((OD − 2 × wall)/2)²) × length after conversion to mm | 115833329.7 | 115833329.7 | `math.isclose` relative tolerance `1e-3` (0.1%); observed relative difference 0.0%; `tests/modules/field_development/test_equipment_3d.py::test_volume_matches_hollow_pipe_formula` | NOT_RUN / PASS; the final isolated environment supplies CAD. [tests/modules/field_development/test_equipment_3d.py:L33-L42] [tests/modules/field_development/test_equipment_3d.py:L52-L61] |

Volumes are rounded to one decimal place after comparing unrounded values. This example qualifies the downstream geometry calculation for the stated synthetic case; U1 unit qualification and U3 catalogue accuracy remain open. [tests/modules/field_development/test_equipment_3d.py:L52-L61]

### Regression examples

Test paths in the node column are repository-relative; each PASS is an offline observation on 2026-10-16 at the header pin, for both the baseline and final runs. [tests/unit/subsea/test_manifold_suppliers.py:L32-L70] [tests/unit/curated/test_csv_validation.py:L24-L110]

| ID | Source and input | Expected value; tolerance and basis | Existing test node ID | Baseline / final |
| --- | --- | --- | --- | --- |
| E1 | Synthetic literal list, in test | 3 ordered items, exact equality; parser contract | `tests/unit/subsea/test_manifold_suppliers.py::test_schema_splits_delimited_lists` | PASS / PASS. [tests/unit/subsea/test_manifold_suppliers.py:L32-L38] |
| E2 | Synthetic unknown-depth token, in test | `None`; exact identity, schema contract | `tests/unit/subsea/test_manifold_suppliers.py::test_schema_coerces_unknown_depth_to_none` | PASS / PASS. [tests/unit/subsea/test_manifold_suppliers.py:L63-L65] |
| E3 | Synthetic jumper with nonpositive OD, in test | 1 validation exception at 0.0 inches; exact rejection | `tests/unit/curated/test_csv_validation.py::TestRigidJumperLoading::test_zero_od_raises_validation_error` | PASS / PASS. [tests/unit/curated/test_csv_validation.py:L58-L69] |
| E4 | Synthetic unrecognized component category, in test | 1 validation exception; exact rejection | `tests/unit/curated/test_csv_validation.py::TestMooringLoading::test_invalid_component_type_raises_validation_error` | PASS / PASS. [tests/unit/curated/test_csv_validation.py:L94-L103] |
| E5 | Curated jumper and mooring CSV paths constructed in test | Each list has more than 0 records; repository smoke criterion, no independent accuracy tolerance | `tests/unit/curated/test_csv_validation.py::TestMooringLoading::test_all_csv_rows_load_without_error` | PASS / PASS. [tests/unit/curated/test_csv_validation.py:L17-L21] [tests/unit/curated/test_csv_validation.py:L105-L110] |

The earlier locked-extra attempt could not install `nlopt==2.10.0`. The current isolated environment satisfies the declared `cadquery>=2.8` requirement with CadQuery 2.8.0 and `nlopt==2.11.0`; all seven downstream CAD nodes now pass. Full locked-project resolution remains unverified. [tests/modules/field_development/test_equipment_3d.py:L12-L96] [pyproject.toml:L178-L184]

## 5. QA gates

Applicable gate selection follows AQG r0, *Analysis QA gates*, revision 0, sections 9–11, Python calculations; gate rows below define executable producer checks, with independent clearance still required. (AQG r0, sections 9–11.)

| Gate | Applicability and module route |
| --- | --- |
| G0 | Applicable: CSV-to-model constraints, null/list normalization, input provenance and units; C01–C03. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L70-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L25-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L24-L55] |
| G1 | Applicable: Python imports and offline pytest; no target-program file is emitted by this package; C04. [packages/worldenergydata-subsea/src/worldenergydata/subsea/__init__.py:L3-L8] [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L93] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L50-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L42-L55] |
| G2 | Applicable: independent literal reconstruction of list parsing, C05; physical catalogue accuracy remains outside that check. [tests/unit/subsea/test_manifold_suppliers.py:L32-L45] |
| G3 | NOT_APPLICABLE: package outputs are validated records, with no time integration. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L93] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L50-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L42-L55] |
| G4 | NOT_APPLICABLE: package does not construct diffraction meshes or hydrodynamic solutions. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L93] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L50-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L42-L55] |
| G5 | Applicable: C06 checks traceable example results and pinned citations; independent signature remains pending. (AQG r0, sections 9 and 11.) |

| Check | Executable definition | Numeric pass criterion and unit | Evidence and limit |
| --- | --- | --- | --- |
| C01 / G0 | Run `tests/unit/subsea/test_manifold_suppliers.py::test_schema_splits_delimited_lists`, `tests/unit/subsea/test_manifold_suppliers.py::test_schema_accepts_native_lists`, `tests/unit/subsea/test_manifold_suppliers.py::test_schema_requires_company`, `tests/unit/subsea/test_manifold_suppliers.py::test_schema_rejects_bad_role`, `tests/unit/subsea/test_manifold_suppliers.py::test_schema_rejects_bad_tier`, `tests/unit/subsea/test_manifold_suppliers.py::test_schema_coerces_unknown_depth_to_none`, `tests/unit/subsea/test_manifold_suppliers.py::test_schema_rejects_implausible_depth` | 7 passed tests; 0 failed tests (count) | Roles, tiers, company, lists and coarse depth rejection; no fractional-depth or locale case. [tests/unit/subsea/test_manifold_suppliers.py:L32-L70] |
| C02 / G0 | Run both classes of `tests/unit/curated/test_csv_validation.py` | 10 passed tests; 0 failed tests (count); loaded OD and MBL each strictly greater than 0 in declared field units | CSV/model smoke tests and selected rejections; not a finite-value or full geometry check. [tests/unit/curated/test_csv_validation.py:L24-L110] |
| C03 / G0 | Run `tests/unit/subsea/test_manifold_suppliers.py::test_database_has_all_key_players`, `tests/unit/subsea/test_manifold_suppliers.py::test_every_record_has_a_source_url`, `tests/unit/subsea/test_manifold_suppliers.py::test_every_record_is_classified`, `tests/unit/subsea/test_manifold_suppliers.py::test_depths_within_bounds` | 4 passed tests; 0 failed tests (count); catalogue depth strictly greater than 0 and at most 6000 m | 1 or more source-list items per loaded record; URL prefix only, not source truth or freshness. [tests/unit/subsea/test_manifold_suppliers.py:L76-L99] |
| C04 / G1 | Run the four discovered test files with the test form below, including the declared test and CAD requirements | 37 passed tests; 0 failed tests (count), plus 7 CAD nodes, which are `NOT_RUN` unless the environment of draft 6 is available | 3 query tests, 13 downstream integration tests and 7 CAD tests complement C01–C03; environment reproducibility remains a follow-up, issue pending (6). [tests/unit/subsea/test_manifold_suppliers.py:L105-L125] [tests/modules/field_development/test_integrations.py:L33-L142] [tests/modules/field_development/test_equipment_3d.py:L12-L96] |
| C05 / G2 | Hand-enumerate the three literal fragments and two native-list elements; compare `_split_list_fields` results using `tests/unit/subsea/test_manifold_suppliers.py::test_schema_splits_delimited_lists` and `tests/unit/subsea/test_manifold_suppliers.py::test_schema_accepts_native_lists` | 0 differing items (count); ordered equality, no tolerance | 2 passed test nodes; a parser check, with no physical benchmark claim. [tests/unit/subsea/test_manifold_suppliers.py:L32-L45] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L104-L115] |
| C06 / G5 | Resolve every bracket citation using `git show <code-pin>:<path>`; require `1 <= start <= end <= line_count`; inspect all E1–E5 results and section-10 issue references | 0 broken citations, 0 missing example results, 0 untracked open items (count) | Producer audit retained with the handoff; independent review and issue creation remain pending. (AQG r0, sections 9 and 11.) |

Current execution form: `uv run --no-project --no-compile-bytecode --active --python <environment>/bin/python --with pytest python -m pytest tests/unit/subsea/test_manifold_suppliers.py tests/unit/curated/test_csv_validation.py tests/modules/field_development/test_equipment_3d.py tests/modules/field_development/test_integrations.py -q -rA -p no:cacheprovider --basetemp=<scratch>` from a temporary test/data/configuration copy, importing worktree sources through `PYTHONPATH`. The isolated environment supplies the declared test and CAD requirements. Ordinary pytest configuration, including coverage, is retained without an addopts override or worker parallelism. [pyproject.toml:L143-L157] [pyproject.toml:L178-L184] [pyproject.toml:L392-L413]

## 6. Known failure modes and pitfalls

### Silent-failure sweep

The following exact searches were run against every package Python file at the code pin; records below also include schema-default and unit inspection of the full files. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L1-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L1-L55] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L1-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L1-L93]

```sh
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|0\.05|5 ?%' packages/worldenergydata-subsea/src/worldenergydata/subsea --glob '*.py'
rg -n 'int\(|float\(|pd\.notna|if .* for |if .*strip|if r\.|_records|Optional|List\[|_in\b|_ft\b|_psi\b|_kips\b|_mm\b|_kn\b|_kg_per_m\b|DEPTH_M|read_csv|DictReader' packages/worldenergydata-subsea/src/worldenergydata/subsea --glob '*.py'
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|\b0\b|1970|%|int\(|float\(|cache|_records|page|offset|limit|step|range\(' packages/worldenergydata-subsea/src/worldenergydata/subsea --glob '*.py'
```

Sweep: 59 found

A row denotes a distinct inspected path or field. Expected missing-value behavior is retained alongside defects so that silent normalizations and exclusions remain visible. There are no `except` handlers, `continue` statements, epoch defaults, percentage defaults or zero-valued fallback defaults in these implementations. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L1-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L1-L55] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L1-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L1-L93]

| ID | Path or field; symptom and cause | Existing detection check; follow-up |
| --- | --- | --- |
| S01 | Missing CSV: warning followed by cached empty result; later file creation does not trigger reload. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L40-L44] | C03 detects fewer than 10 default-path records; no detection check exists for caller-supplied missing paths or reload behavior; issue pending (1). |
| S02 | Header-only CSV: empty row list is cached without a nonempty-data check. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L45-L53] | C03 detects fewer than 10 default-path records; no detection check exists for caller-supplied header-only paths; issue pending (1). |
| S03 | Cached records: source edits are not read again; all() copies the list but shares mutable models. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L40-L57] | no detection check exists; issue pending (1). |
| S04 | Role filter silently excludes nonmatching or unknown-role records. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L69-L70] | C04 checks selected positive matches, not exclusion accounting; issue pending (1). |
| S05 | Tier filter silently excludes nonmatching or unknown-tier records. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L71-L72] | C04 checks selected positive matches, not exclusion accounting; issue pending (1). |
| S06 | Country filter silently excludes missing country and nonmatching substrings. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L73-L77] | no detection check exists; issue pending (1). |
| S07 | Depth filter silently excludes missing depth and values below threshold. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L78-L84] | C04 checks returned lower bounds, not unknown-depth exclusions; issue pending (1). |
| S08 | get() returns None when no substring matches; multiple matches return the first. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L87-L93] | C04 checks a positive lookup; no detection check exists for misses or ambiguity; issue pending (1). |
| S09 | Blank optional scalar strings become None for every field in the validator list. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L77-L94] | no detection check exists; issue pending (4). |
| S10 | PRODUCT_LINES: omitted field defaults to an empty list. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L58-L58] | C03 checks populated source lists only; no detection check exists for this default; issue pending (4). |
| S11 | NOTABLE_PROJECTS: omitted field defaults to an empty list. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L59-L59] | C03 checks populated source lists only; no detection check exists for this default; issue pending (4). |
| S12 | RECENT_DEVELOPMENTS: omitted field defaults to an empty list. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L60-L60] | C03 checks populated source lists only; no detection check exists for this default; issue pending (4). |
| S13 | DATA_SOURCE_URLS: omitted field defaults to an empty list. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L61-L61] | C03 checks populated source lists only; no detection check exists for this default; issue pending (4). |
| S14 | Null list-valued input becomes []. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L104-L107] | no detection check exists; issue pending (4). |
| S15 | Blank list-valued text becomes []. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L108-L111] | no detection check exists; issue pending (4). |
| S16 | Delimited text drops whitespace-only fragments. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L108-L112] | C05 checks ordinary splitting; no detection check exists for dropped fragments; issue pending (4). |
| S17 | Native list/tuple drops blank stringified items; None becomes literal text. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L113-L115] | C05 checks ordinary native lists; no detection check exists for null elements; issue pending (4). |
| S18 | Null depth remains None. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L119-L121] | no detection check exists; issue pending (2). |
| S19 | Blank or case-insensitive unknown depth becomes None. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L122-L125] | C01 detects the unknown-token branch; blank branch has no detection check; issue pending (2). |
| S20 | External depth text uses int(float(v)): fractions truncate and localized separators raise validation errors. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L122-L126] | no detection check exists; issue pending (2). |
| S21 | Float depth uses int(v): fractional information is discarded. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L127-L129] | no detection check exists; issue pending (2). |
| S22 | Depth bounds permit 0 m, while catalogue test demands a strictly positive depth. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L131-L136] | C03 catches zero only in loaded catalogue records; issue pending (2). |
| S23 | Jumper row construction omits every pandas-missing cell before model defaults apply. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L59-L63] | C02 checks current rows; no detection check exists for missing-cell policy; issue pending (3). |
| S24 | Mooring row construction omits every pandas-missing cell before model defaults apply. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L51-L55] | C02 checks current rows; no detection check exists for missing-cell policy; issue pending (3). |
| S25 | weight_air_kips: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L20-L20] | no detection check exists for omitted-field completeness; issue pending (3). |
| S26 | connection_type: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L21-L21] | no detection check exists for omitted-field completeness; issue pending (3). |
| S27 | notes: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L23-L23] | no detection check exists for omitted-field completeness; issue pending (3). |
| S28 | weight_kg_per_m: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L18-L18] | no detection check exists for omitted-field completeness; issue pending (3). |
| S29 | material: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L19-L19] | no detection check exists for omitted-field completeness; issue pending (3). |
| S30 | grade: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L20-L20] | no detection check exists for omitted-field completeness; issue pending (3). |
| S31 | notes: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L22-L22] | no detection check exists for omitted-field completeness; issue pending (3). |
| S32 | TICKER: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L44-L44] | no detection check exists for omitted-field completeness; issue pending (4). |
| S33 | HQ_COUNTRY: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L45-L45] | no detection check exists for omitted-field completeness; issue pending (4). |
| S34 | HQ_CITY: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L46-L46] | no detection check exists for omitted-field completeness; issue pending (4). |
| S35 | PARENT_OR_JV: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L47-L47] | no detection check exists for omitted-field completeness; issue pending (4). |
| S36 | MANIFOLD_ROLE: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L50-L50] | no detection check exists for omitted-field completeness; issue pending (4). |
| S37 | ROLE_TIER: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L51-L51] | no detection check exists for omitted-field completeness; issue pending (4). |
| S38 | MARKET_POSITION: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L52-L52] | no detection check exists for omitted-field completeness; issue pending (4). |
| S39 | MAX_WATER_DEPTH_M: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L55-L55] | no detection check exists for omitted-field completeness; issue pending (4). |
| S40 | DATA_SOURCE_URL: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L64-L64] | no detection check exists for omitted-field completeness; issue pending (4). |
| S41 | COLLECTION_DATE: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L65-L65] | no detection check exists for omitted-field completeness; issue pending (4). |
| S42 | NOTES: optional default None leaves absence without a completeness error. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L66-L66] | no detection check exists for omitted-field completeness; issue pending (4). |
| S43 | od_in: numeric field has no conversion; downstream CAD explicitly assumes inches. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L15-L15] | no detection check exists for input unit qualification; issue pending (5). |
| S44 | wall_thickness_in: numeric field has no conversion; downstream CAD explicitly assumes inches. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L16-L16] | no detection check exists for input unit qualification; issue pending (5). |
| S45 | length_ft: numeric field has no conversion; downstream CAD explicitly assumes feet. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L17-L17] | no detection check exists for input unit qualification; issue pending (5). |
| S46 | pressure_rating_psi: field suffix is the only package unit indication; catalog unit is blank. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L19-L19] | no detection check exists for input unit qualification; issue pending (5). |
| S47 | weight_air_kips: catalog kg label conflicts with field suffix; no conversion. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L20-L20] | no detection check exists for input unit qualification; issue pending (5). |
| S48 | size_mm: catalog labels mm; model does not qualify input units. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L16-L16] | no detection check exists for input unit qualification; issue pending (5). |
| S49 | mbl_kn: catalog and field comment label kN; model does not qualify input units. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L17-L17] | no detection check exists for input unit qualification; issue pending (5). |
| S50 | weight_kg_per_m: catalog labels kg despite per-length field suffix; no conversion. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L18-L18] | no detection check exists for input unit qualification; issue pending (5). |
| S51 | MAX_WATER_DEPTH_M: range message assumes metres; no unit-tag validation. [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L131-L136] | no detection check exists for input unit qualification; issue pending (5). |
| S52 | OD: <= 0 rejects nonpositive finite values but lets NaN pass on direct construction; CSV NaN is dropped and fails as a missing required field. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L25-L31] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L59-L63] | no detection check exists for non-finite inputs; issue pending (3). |
| S53 | wall thickness: <= 0 rejects nonpositive finite values but lets NaN pass on direct construction; CSV NaN is dropped and fails as a missing required field. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L33-L39] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L59-L63] | no detection check exists for non-finite inputs; issue pending (3). |
| S54 | pressure: <= 0 rejects nonpositive finite values but lets NaN pass on direct construction; CSV NaN is dropped and fails as a missing required field. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L41-L47] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L59-L63] | no detection check exists for non-finite inputs; issue pending (3). |
| S55 | MBL: <= 0 rejects nonpositive finite values but lets NaN pass on direct construction; CSV NaN is dropped and fails as a missing required field. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L33-L39] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L51-L55] | no detection check exists for non-finite inputs; issue pending (3). |
| S56 | Positive infinity survives CSV loading and the <= 0 checks for OD, wall thickness, pressure and MBL. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L25-L47] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L59-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L33-L39] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L51-L55] | no detection check exists; issue pending (3). |
| S57 | Empty get query: the empty string is a substring of every company, so get("") returns the first record. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L87-L93] | no detection check exists; issue pending (1). |
| S58 | Negative weight_air_kips and weight_kg_per_m are accepted; neither optional weight has a sign check. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L20-L47] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L18-L39] | no detection check exists; issue pending (3). |
| S59 | Default pandas NA tokens (NA, N/A, null, None, nan and empty cells) erase literal optional text before pd.notna filtering; the model default None then applies. Required fields instead fail validation. [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L59-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L51-L55] | no detection check exists; issue pending (3). |

Sweep inventory: 59 rows, including 2 empty-result cache paths, 4 explicit `return None` sites, 2 explicit `return []` sites, 4 list defaults, 18 scalar model defaults, 9 unit assumptions, 4 NaN-sensitive positivity validators and the 4 additional paths S56–S59; overlapping categories are counted once per row above. [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L93] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L43-L136] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L13-L47] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L13-L39]

### Additional confirmed gaps and issue context

| Finding | Evidence | Detection / disposition |
| --- | --- | --- |
| Infinite external depth text raises raw OverflowError at int(float(v)); this is an explicit failure rather than a silent path | [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L122-L126] | no detection check exists; issue pending (2). |
| Jumper negative length and wall greater than radius are accepted by the data model; downstream CAD rejects a nonpositive bore | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L13-L47] [src/worldenergydata/field_development/equipment_3d.py:L66-L76] | no detection check exists in the model tests; issue pending (3). |
| Mooring size lacks positivity validation; supplier unknown columns are ignored by default model configuration | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L13-L39] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L35-L66] | no detection check exists; issue pending (3) for component validation, issue pending (4) for supplier schema policy. |
| Catalogue unit labels disagree with dimensional field suffixes | [data/catalog.yaml:L1730-L1741] [data/catalog.yaml:L1785-L1800] | no detection check exists; issue pending (5); do not use these labels as a conversion reference. |
| Readiness matrix says there is no subsea source or test coverage | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L91-L91] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L822-L835] | Contradicted by C04 and package code; existing #349 covers the inventory drift. |
| Packaging includes recursive Markdown globs | [packages/worldenergydata-subsea/pyproject.toml:L49-L55] | no wheel exclusion check exists; issue pending (9). |

Issue #518 records supplier-database requirements, #575 catalog integration, #580 downstream CAD and #529 domain packaging; these are feature/context records, not confirmed incident reports for the silent paths above. (Repository issues #518, #575, #580 and #529, bodies inspected 2026-10-16.)

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Pack change / shared entry |
| --- | --- | --- | --- | --- |
| 2026-10-16 | Initial pack | Missing supplier data is indistinguishable from an empty cached database through the return value alone | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L53] | S01–S03; issue pending (1). Shared-entry follow-up: issue pending (7). |
| 2026-10-16 | Initial pack | Data-model positivity checks do not establish usable component geometry or finite values | [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L13-L47] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L13-L39] | Section 6; issue pending (3). Shared-entry follow-up: issue pending (7). |
| 2026-10-16 | Initial pack | Unit metadata must be resolved before dimensional reuse | [data/catalog.yaml:L1738-L1741] [data/catalog.yaml:L1789-L1796] | U1 and unit sweep rows; issue pending (5). Shared-entry follow-up: issue pending (7). |

## 8. Ownership

Review assignment for this draft: calculations family quality manager; deputy nomination remains open, issue pending (10). Independent gate clearance is required before a status of CLEARED can be assigned. (AQG r0, *Analysis QA gates*, revision 0, section 11.)

Producing responsibility: maintain the package evidence, example results and failure inventory; escalate ambiguous units, acceptance criteria and evidence gaps to the calculations quality manager, with cross-family decisions reserved for the maintainers. (AQG r0, sections 10–11.)

## 9. Dependencies and implementation inventory

### Data and package dependencies

| Dependency | Direction and use | Evidence |
| --- | --- | --- |
| `worldenergydata-core` | Upstream; resolves the module data location, including safe fallback when data directories are missing | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L22-L29] [packages/worldenergydata-core/src/worldenergydata/common/data_resolver.py:L100-L124] |
| pandas and Pydantic | Upstream; CSV component parsing and all record validation; declared ranges are pandas `>=2.3.3,<3.0`, Pydantic `>=2.13.4,<3.0` | [packages/worldenergydata-subsea/pyproject.toml:L29-L33] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L6-L7] |
| Dataset `manifold_suppliers` | Supplier-loader default CSV | [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L29-L47] |
| Datasets `rigid_jumper_specs`, `mooring_components` | Explicit-path component inputs | [tests/unit/curated/test_csv_validation.py:L17-L21] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L50-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L42-L55] |
| `field_development.integrations` | Downstream catalog selection via loaders; wraps failures as missing selections | [src/worldenergydata/field_development/integrations.py:L211-L252] |
| `field_development.equipment_3d` | Downstream optional CAD geometry; consumes jumper specs and performs dimensional conversion | [src/worldenergydata/field_development/equipment_3d.py:L27-L37] [src/worldenergydata/field_development/equipment_3d.py:L53-L76] |
| Supplier builder and report renderer | Upstream CSV/Parquet writer delegates validation to the schema; downstream renderer reads the loader | [scripts/build_manifold_suppliers_db.py:L489-L526] [scripts/generate_manifold_market_report.py:L33-L46] |

The manifest inventories the subsea domain and its three dataset types; no solver or solver version is a dependency of the package implementations. [module-manifest.yaml:L491-L504] [packages/worldenergydata-subsea/pyproject.toml:L29-L33]

### Implementation-map audit

Map source: `digitalmodel`, `docs/registry/implementation-map.yaml`, schema 1; ref commit `21f0a121ffacbd63b97af00f873e8089effa6c3b`, data revision `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; all 13 family entries were inspected for implementation paths inside this pack's header package. (Implementation map, schema 1, named data revision, `families` collection.)

| Inventory item | Result |
| --- | --- |
| Map families with at least one row inside the package | 0; empty inventory. (Implementation map, named data revision, `families[*].implementations[*].path`.) |
| Counted families | 0; no ranked family or path-vocabulary exclusion applies. (Implementation map, named data revision, implementation paths.) |
| Counted-family signal grep | NOT_APPLICABLE: the map inventories digitalmodel only; no map family has an implementation row in this package. (Implementation map, named data revision, implementation paths.) |
| Further second implementations counted for A8 | 0; empty counted-family set. (Implementation map, named data revision, implementation paths.) |
| A8 producer result | PASS for empty inventory; map follow-up below remains required. (Implementation map, named data revision, implementation paths.) |

Map follow-up: add the six section-3 families (supplier scalar validation, supplier list normalization, depth normalization and bounds, supplier CSV ingestion and selection, jumper validation and ingestion, mooring validation and ingestion) with this package's rows before counting them; issue pending (7). [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L70-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L35-L93] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L25-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L24-L55]

### Repository-wide further search

```sh
rg -n 'MANIFOLD_ROLES|class ManifoldSupplierSchema|load_rigid_jumpers|load_mooring_components|manifold_suppliers\.csv|rigid_jumper_specs\.csv|mooring_components\.csv' --glob '*.py' .
rg -n 'int\(float\(v\)\)|_split_list_fields|_coerce_int' --glob '*.py' .
rg -n 'subsea|manifold|jumper|mooring' scripts --glob '*.py'
```

| Definition outside the package | Classification and map follow-up |
| --- | --- |
| Supplier builder `build`, `_pack` | Delegating schema user and list serializer; helper, not an independent supplier validator. [scripts/build_manifold_suppliers_db.py:L489-L526] |
| Market report `render` | Loader consumer and presentation logic; helper, not a separate CSV loader. [scripts/generate_manifold_market_report.py:L33-L46] |
| Integration `_pick_jumper`, `_pick_mooring` | Delegating loaders plus independent representative ranking; outside-package selection map gap, issue pending (7). [src/worldenergydata/field_development/integrations.py:L227-L252] |
| Demo `pick_chain_component` | Separate CSV reader and maximum-MBL chain selection; outside-package map gap, issue pending (7); inspected only, not executed. [scripts/demo/_mooring_live.py:L44-L50] |
| Emerging-basin schema `_coerce_int` | Separate `int(float(v))` normalization with its own unknown-token policy; outside-package map gap, issue pending (7). [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discovery_schema.py:L97-L109] |
| CAD `build_jumper_solid`, `build_jumper_from_catalog` | Geometry implementation and delegating catalog selection; not an additional in-package data validator; downstream environment reproducibility follow-up, issue pending (6). [src/worldenergydata/field_development/equipment_3d.py:L53-L106] |

Further-search findings do not change the empty counted-family A8 result. (Implementation map, schema 1, named data revision, implementation paths.)

## 10. Coverage and open items

### Files and tests read

The complete package Python inventory is seven files; no Python subpackage is excluded from this pack. [packages/worldenergydata-subsea/src/worldenergydata/subsea/__init__.py:L1-L8] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/__init__.py:L1-L17] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L1-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L1-L55] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/__init__.py:L1-L7] [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L1-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L1-L93]

| Reading | Scope and evidence |
| --- | --- |
| Package README and packaging metadata | Namespace and declared dependencies; [packages/worldenergydata-subsea/README.md:L1-L8] [packages/worldenergydata-subsea/pyproject.toml:L29-L55] |
| `module-manifest.yaml` subsea entry | Dataset and API registration; [module-manifest.yaml:L491-L506] |
| `data/catalog.yaml` subsea entry | Dimensional metadata; [data/catalog.yaml:L1710-L1810] |
| Architecture decision | Independent domain artifacts and subsea leaf classification; [docs/adr/0001-domain-package-split.md:L20-L22] [docs/adr/0001-domain-package-split.md:L43-L48] |
| Readiness matrix and YAML companion | Historical no-source/no-test claim; [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L91-L91] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L822-L835] |
| Completeness scorecard and YAML companion | Historical subsea data-readiness entries; [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L73-L77] [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L136-L138] [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L358-L369] |
| Freshness scorecard | Historic unknown refresh status; [docs/reports/data-freshness-scorecard-2026-06-08.md:L25-L27] |
| Supplier test file | 14 direct tests; [tests/unit/subsea/test_manifold_suppliers.py:L32-L125] |
| Curated CSV test file | 10 component-loader tests; [tests/unit/curated/test_csv_validation.py:L24-L110] |
| Downstream CAD test file | 7 functions, module-level CadQuery import guard; [tests/modules/field_development/test_equipment_3d.py:L12-L96] |
| Downstream integration test file | 13 functions, including 3 hardware-selection tests; [tests/modules/field_development/test_integrations.py:L33-L142] |
| Catalog consumers and generators | Inspected definitions listed in section 9; [scripts/build_manifold_suppliers_db.py:L489-L526] [scripts/generate_manifold_market_report.py:L33-L46] [scripts/demo/_mooring_live.py:L44-L50] |

Discovery used `rg --files` under the package and `rg -n` over `docs`, `tests`, `packages`, `src` and `scripts` for `worldenergydata[./]subsea`, the three public schema names, loader names and dataset file stems; generic engineering uses of the word subsea were separated from package/API references. [packages/worldenergydata-subsea/src/worldenergydata/subsea/__init__.py:L1-L8] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/__init__.py:L3-L17] [tests/unit/curated/test_csv_validation.py:L8-L21]

The code inventory contains 31 directly relevant test functions (14 supplier, 10 component and 7 downstream CAD), plus 13 downstream integration tests. When CAD is unavailable, the module guard counts as one pytest collection skip; the current final run executes all 44 functions. [tests/unit/subsea/test_manifold_suppliers.py:L32-L125] [tests/unit/curated/test_csv_validation.py:L24-L110] [tests/modules/field_development/test_equipment_3d.py:L12-L96] [tests/modules/field_development/test_integrations.py:L33-L142]

### Recorded offline results

All runs use code pin `6149361d36373afe24fe1b0c1fe59886375d46b7`. Revision 0 observations are preserved in the first table; current revision 1 results follow it. Runtime code and test inputs remain unchanged, and checks run on the uncommitted documentation tree. [tests/unit/subsea/test_manifold_suppliers.py:L32-L125] [tests/unit/curated/test_csv_validation.py:L24-L110] [tests/modules/field_development/test_equipment_3d.py:L12-L96]

| Revision 0 command scope | Baseline | Final | Interpretation |
| --- | --- | --- | --- |
| Direct supplier/component tests plus CAD file | 24 passed, 0 failed, 1 module skip | 24 passed, 0 failed, 1 module skip | 24 executed nodes; the CAD guard skips collection. [tests/modules/field_development/test_equipment_3d.py:L12-L14] |
| Same paths plus downstream integration file | 37 passed, 0 failed, 1 module skip | 37 passed, 0 failed, 1 module skip | 37 executed nodes; CAD remains unavailable. [tests/modules/field_development/test_integrations.py:L33-L142] |
| Declared test/CAD extra attempt | pytest NOT_RUN; resolver exit 2 | Same availability limitation, not retried | `nlopt==2.10.0` has no source distribution or compatible wheel; dependency setup stops before collection. [pyproject.toml:L178-L184] |

| Revision 1 command scope | Result | Interpretation |
| --- | --- | --- |
| Same four test files, initial minimal environment | 36 passed, 1 failed, 1 collection skip | The first project_economics import fails because `numpy-financial` is missing; a direct import probe confirms the missing declared dependency. It is installed before the final run. CAD is initially absent. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L13-L16] [packages/worldenergydata-project_economics/pyproject.toml:L41-L45] |
| Same four test files, complete focused environment | 44 passed, 0 failed, 0 skipped | Includes all seven CAD nodes and the recovered integration case; V1 also passes. [tests/modules/field_development/test_equipment_3d.py:L12-L96] [tests/modules/field_development/test_integrations.py:L33-L142] |

The current isolated environment uses Python 3.11.15, pytest 9.1.1, pandas 2.3.3, Pydantic 2.14.1, CadQuery 2.8.0, nlopt 2.11.0 and numpy-financial 1.0.0. These are observed test-environment versions; reproducibility in the locked project and other supported environments remains a follow-up, issue pending (6). [pyproject.toml:L143-L157] [pyproject.toml:L178-L184] [packages/worldenergydata-project_economics/pyproject.toml:L41-L45]

The seven individual downstream CAD nodes below all pass in the current final run. The historical collection skips above represent unavailable CAD collection, rather than executed nodes. [tests/modules/field_development/test_equipment_3d.py:L12-L96]

| Existing test node ID | Result |
| --- | --- |
| `tests/modules/field_development/test_equipment_3d.py::test_builds_a_valid_solid` | PASS. [tests/modules/field_development/test_equipment_3d.py:L46-L49] |
| `tests/modules/field_development/test_equipment_3d.py::test_volume_matches_hollow_pipe_formula` | PASS. [tests/modules/field_development/test_equipment_3d.py:L52-L61] |
| `tests/modules/field_development/test_equipment_3d.py::test_is_hollow_less_than_solid_cylinder` | PASS. [tests/modules/field_development/test_equipment_3d.py:L64-L68] |
| `tests/modules/field_development/test_equipment_3d.py::test_wall_too_thick_raises` | PASS. [tests/modules/field_development/test_equipment_3d.py:L71-L73] |
| `tests/modules/field_development/test_equipment_3d.py::test_export_writes_step_file` | PASS. [tests/modules/field_development/test_equipment_3d.py:L76-L80] |
| `tests/modules/field_development/test_equipment_3d.py::test_build_from_catalog` | PASS. [tests/modules/field_development/test_equipment_3d.py:L86-L91] |
| `tests/modules/field_development/test_equipment_3d.py::test_unknown_component_raises_keyerror` | PASS. [tests/modules/field_development/test_equipment_3d.py:L94-L96] |

### Unverified claims

| ID | Claim and limit | Responsible role / tracking |
| --- | --- | --- |
| U1 | UNVERIFIED: Complete physical unit qualification of CSV numeric fields; conflicting weight labels and blank unit metadata remain unresolved. [data/catalog.yaml:L1730-L1741] [data/catalog.yaml:L1773-L1796] | Maintainer; issue pending (5). |
| U2 | UNVERIFIED: Operational readiness beyond the manifest's `stable` declaration and the distribution's Alpha classifier. [module-manifest.yaml:L491-L504] [packages/worldenergydata-subsea/pyproject.toml:L15-L23] | Maintainer; #349. |
| U3 | UNVERIFIED: Independent catalogue accuracy, provenance rights and current supplier-market facts; existing tests check presence and prefix rather than external-source content. [tests/unit/subsea/test_manifold_suppliers.py:L76-L99] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L13-L23] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L13-L22] | Maintainer; issue pending (8). |
| U4 | UNVERIFIED: Exclusion of this pack from the built wheel; existing recursive Markdown package-data globs match its location and no wheel was built. [packages/worldenergydata-subsea/pyproject.toml:L49-L55] | Maintainer; issue pending (9). |
| U5 | UNVERIFIED: Appointment of a deputy for independent review; review assignment is provisional pending maintainers' nomination. (AQG r0, revision 0, section 11.) | Maintainer; issue pending (10). |

### Open items

Numbered issue-pending markers identify drafts, not filed issues. The accompanying [issue-draft list](ISSUES_DRAFT.md) contains Draft 1 through Draft 10; the maintainers will create the issues and replace the corresponding markers before merging. Existing #349 remains the filed readiness follow-up.

| Item | Required follow-up and responsibility | Tracking |
| --- | --- | --- |
| Missing/empty data, caches and query omissions | Maintainer: define unavailable versus empty state, reload/mutation policy and omission-accounting tests; S01–S08 | issue pending (1). [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L39-L93] |
| Depth coercion | Maintainer: define fractional, localized-text and zero-depth policy; regression coverage for S18–S22 | issue pending (2). [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L117-L136] |
| Component validation and missing cells | Maintainer: finite-value, geometry, completeness and missing-cell policies | issue pending (3). [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L13-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L13-L55] |
| Supplier normalization and provenance completeness | Maintainer: absent/blank/null list and scalar cases, source/date formats and unknown-key policy | issue pending (4). [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L38-L152] |
| Unit qualification | Maintainer: resolve U1 before dimensional reuse | issue pending (5). [data/catalog.yaml:L1730-L1741] [data/catalog.yaml:L1789-L1796] |
| CAD environment reproducibility | Maintainer: preserve the working declared-extra versions and make seven-node CAD coverage reproducible; the current final run passes all seven nodes | issue pending (6); context #580. [tests/modules/field_development/test_equipment_3d.py:L12-L96] |
| Historical readiness claims | Maintainer: reconcile U2 and obsolete source/test inventory | #349. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L822-L835] |
| Map and shared index follow-up | Maintainer: add all six section-3 method families, register outside-package search findings and index this pack | issue pending (7). [packages/worldenergydata-subsea/src/worldenergydata/subsea/schemas/manifold_supplier.py:L70-L152] [packages/worldenergydata-subsea/src/worldenergydata/subsea/suppliers.py:L35-L93] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/rigid_jumper.py:L25-L63] [packages/worldenergydata-subsea/src/worldenergydata/subsea/models/mooring.py:L24-L55] |
| Independent catalogue example and source basis | Maintainer: establish U3 and an independent data-validation benchmark; V1 validates synthetic geometry only | issue pending (8). [tests/unit/subsea/test_manifold_suppliers.py:L32-L99] [tests/modules/field_development/test_equipment_3d.py:L52-L61] |
| Distribution and deputy | Maintainer: resolve U4 and U5 before relying on exclusion or review assignment | issue pending (9), issue pending (10). [packages/worldenergydata-subsea/pyproject.toml:L49-L55] (AQG r0, section 11.) |

No module-routing registry is present at the code pin, so no registry file is changed; package registration remains in the existing module manifest. [module-manifest.yaml:L491-L506]
