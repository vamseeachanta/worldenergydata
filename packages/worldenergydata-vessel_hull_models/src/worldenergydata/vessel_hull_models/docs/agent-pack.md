# vessel_hull_models knowledge pack

| Header | Value |
| --- | --- |
| Module | `vessel_hull_models` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models` |
| Pack revision | 0 |
| Code revision | `13f3b70aa7a87045631b737406c881e4cb5bcfd0` |
| Analysis family | EC; data pipeline, using AQG r0 Python calculations gates |
| Quality manager role | Calculations quality manager |
| Status | DRAFT; second-provider review pending |

## 1. Purpose and scope

The implemented paths parse OBJ/GDF geometry, write OBJ/MSH files, render Plotly figures and PNG previews, and enrich curated rig records with hull forms and dimension estimates. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/__init__.py:L10-L47] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/__init__.py:L10-L33] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_loader.py:L54-L70]

Acquisition and report namespaces expose empty export lists; their descriptive docstrings do not establish working acquisition clients or report generators. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/acquisition/__init__.py:L4-L11] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/reports/__init__.py:L4-L10]

The distribution declares Alpha status; this is packaging metadata, not an engineering qualification. [packages/worldenergydata-vessel_hull_models/pyproject.toml:L16-L24]

The loader returns an empty frame when its curated dataset is absent; an empty query is therefore not evidence of a complete dataset. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_loader.py:L59-L63]

## 2. Inputs and outputs

| Input | Unit | Range / default | Route and evidence |
| --- | --- | --- | --- |
| OBJ vertices and faces | Coordinates interpreted as m by presentation; indices dimensionless | At least one vertex and face; vertices float32, faces int32 | `OBJParser.parse`; suffix must be `.obj`. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L133-L178] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L175-L179] |
| Expected OBJ dimensions | m | Optional; tolerance default 0.05, dimensionless | `validate_obj_file` compares relative errors; nonzero expected values are needed by its divisions. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L312-L318] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L348-L368] |
| GDF header | `unit_length`, `gravity` retained as input scalars | Description, unit length, gravity, X/Y symmetry, panel count required | `parse_gdf_header`; no scale multiplication is applied in the mesh construction route. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L42-L75] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L258-L308] |
| Curated records | `LOA_M`, `BEAM_M`, `DRAFT_M`: m; water-depth rating: ft | Missing dimension columns inserted; estimates fill only rows missing all three dimensions | `populate_estimated_dimensions`. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L171-L220] |
| Hull metadata | Dimensions m; displacement tonnes; counts dimensionless; file size bytes | Length and beam required and ≥0; depth/draft default 0; units default `meters` | `VesselHullModel`; creation/update schemas do not repeat its nonnegative constraints. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/data/models.py:L77-L100] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/data/models.py:L128-L165] |
| Storage settings | bytes for maximum size | 500 × 1024 × 1024 bytes; paths supplied by data resolver | `StorageConfig`; paths expanded and resolved. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/config.py:L19-L57] |

| Output | Unit / convention | Default and evidence |
| --- | --- | --- |
| `OBJMesh` | X length, Y width, Z height; zero-based triangle indices | Extrema difference defines dimensions; bbox midpoint defines center. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L28-L31] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L52-L83] |
| Converted OBJ | Input coordinate units; one-based connectivity | Coordinates written with six decimal places. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L384-L405] |
| MSH | Input coordinate units; one-based nodes; triangle element type 2 | ASCII version 2.2; optional physical name. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L35-L72] |
| Plotly figure / HTML | Axes labelled m; waterline Z defaults 0 m | 1000 × 700 pixels; standalone HTML includes Plotly by default. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L36-L60] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L252-L285] |
| PNG | Axis labels m; image size inches and resolution dots/inch | `export_hull_png`: 12 × 9 inches, 150 dots/inch. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/png_exporter.py:L41-L68] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/png_exporter.py:L123-L125] |
| Enriched frame / coverage | Dimensions m; displacement tonnes; coverage counts records | Confidence strings `measured`, `estimated`, `generic`; missing data summary `{}`. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L18-L26] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L223-L248] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_loader.py:L110-L139] |

The OBJ parser preserves coordinate values rather than translating the origin; the GDF symmetry routine mirrors about X=0 and Y=0 and reverses face winding. A waterline display is not a hydrostatic datum qualification. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L215-L225] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L334-L368] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L127-L159]

UNVERIFIED: external coordinate origin, handedness, phase convention and physical unit provenance are not established by the parser; require dataset-specific qualification before analysis (issue pending (1)).

## 3. Method and governing standards

| Method | Implementing definition and basis | Limits |
| --- | --- | --- |
| Bounding dimensions | `OBJMesh.dimensions`: componentwise max minus min; center is half the sum of extrema. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L52-L83] | Geometric extent only, not wetted geometry. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L67-L83] |
| OBJ triangulation | `OBJParser._parse_face`: quads split along first-to-third vertex; larger polygons use a fan; negative indices are relative to vertices read so far. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L250-L295] | Face references are converted without an explicit bounds check in this routine. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L265-L295] |
| GDF panel interpretation | `_detect_vertices_per_panel`: ratio ≥3.5 selects quads; `_add_vertex_to_map` rounds coordinates to six decimal places; `_create_faces_from_panel` splits quads. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L78-L92] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L130-L136] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L177-L201] | Header unit length/gravity do not enter returned coordinate arrays. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L258-L308] |
| Hull classification | `map_hull_form` normalizes text then uses the operational-to-hydrodynamic mapping; non-vessel/unknown types return `None`. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_form_mapper.py:L18-L58] | Existing nonempty forms are preserved. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_form_mapper.py:L73-L95] |
| Hull reference | `_make_hull_library_ref` rounds positive LOA to a 10 m bucket; missing LOA produces a generic reference. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_form_mapper.py:L121-L136] | Custom references are preserved. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_form_mapper.py:L98-L118] |
| Dimension estimation | `estimate_hull` selects depth brackets for two forms, otherwise defaults; ratings beyond the final bracket reuse it. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L139-L168] | Table comments identify general sources without editions, records or equations. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L29-L31] |
| Rendering | `create_hull_figure` uses triangle arrays and coordinate intensity; PNG routes construct polygon collections. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L64-L105] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/png_exporter.py:L82-L100] | These routes render geometry, rather than solve fluid or structural response. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L161-L179] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/png_exporter.py:L155-L160] |

No governing engineering standard is identified in these method implementations; the mesh writer names a format version rather than a design code. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L22-L38] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L29-L31]

UNVERIFIED: independent provenance and applicability of the dimension tables are not established; no table value is offered as a hand-check reference (issue pending (2)).

## 4. Validated worked examples

Validated examples: 0. The cases below are regression examples using local synthetic fixtures or implementation tables, without independently sourced physical benchmark data. [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L26-L60] [tests/unit/vessel_hull_models/rig_hulls/test_hull_estimator.py:L138-L151]

| Case | Input / expected value / tolerance basis | Existing test node ID | Last offline result |
| --- | --- | --- | --- |
| R1 triangle | Inline unit-coordinate triangle; 3 vertices, 1 face; exact integer equality. [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L26-L32] [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L140-L145] | `tests/unit/vessel_hull_models/geometry/test_obj_parser.py::TestOBJParserParse::test_triangle` | PASS at BASE and after |
| R2 quad | Inline unit-coordinate square; 4 vertices, 2 faces; exact integer equality. [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L34-L40] [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L147-L152] | `tests/unit/vessel_hull_models/geometry/test_obj_parser.py::TestOBJParserParse::test_quad_triangulated` | PASS at BASE and after |
| R3 dimensions | Inline extrema (0,0,0) and (10,5,3); extents 10, 5, 3 coordinate units; `pytest.approx` defaults, no physical validation tolerance. [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L83-L90] | `tests/unit/vessel_hull_models/geometry/test_obj_parser.py::TestOBJMesh::test_dimensions` | PASS at BASE and after |
| R4 sparse dimensions | Inline frame lacks 3 dimension columns; all 3 columns created and populated for 2 rows; exact count/non-null checks. [tests/unit/vessel_hull_models/rig_hulls/test_hull_estimator.py:L231-L255] | `tests/unit/vessel_hull_models/rig_hulls/test_hull_estimator.py::TestPopulateEstimatedDimensions::test_sparse_input_missing_dimension_columns_does_not_crash` | PASS at BASE and after |

## 5. QA gates

Gate selection: AQG r0 §10, Python calculations; G5 applies to every family (AQG r0 §§9–10). These are acceptance checks, not a claim of solver qualification. C0/C1/C2 passed in the module suite; standalone C3/C4 checks also passed with zero extent error and zero missing fields. G5 report signature and downstream evidence transfer remain pending with issue pending (4).

| Gate | Applicability and module-specific check | Numeric pass criterion and unit | Evidence / execution |
| --- | --- | --- | --- |
| G0 | Applicable: C0, `validate_obj_file` on `_FULL_OBJ` at expected LOA 10 m | 0 dimension warnings (count), relative error ≤0.05 (dimensionless) | `TestValidateObjFile::test_dimension_check_within_tolerance`; source defines fixture and assertion. [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L42-L60] [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L314-L318] |
| G0 | Applicable: C1, sparse-frame enrichment | 3 dimension columns, 2 non-null entries per column (counts) | R4 test node and assertions. [tests/unit/vessel_hull_models/rig_hulls/test_hull_estimator.py:L231-L255] |
| G1 | Applicable: C2, Python imports and complete offline module test collection | 0 failed tests, 0 collection errors (counts) | Run `uv run python -m pytest tests/unit/vessel_hull_models -q -rA -p no:cacheprovider --basetemp=<scratch>`; test imports exercise Python entry points. [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L9-L15] [tests/unit/vessel_hull_models/test_plotly_3d.py:L3-L12] |
| G2 | Applicable: C3, `OBJMesh.dimensions` versus direct subtraction of supplied extrema | Max absolute difference 0 coordinate units for the exactly representable fixture (also 0 m if supplied in m) | R3; independently subtract endpoints, without calling another module calculation. [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L83-L90] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L67-L78] |
| G3 | NOT_APPLICABLE: no time-domain response is calculated by the geometry/record paths | NOT_APPLICABLE | Geometry returns meshes and loader returns a frame. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L301-L308] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_loader.py:L65-L70] |
| G4 | NOT_APPLICABLE to the Python calculations family; mesh export alone does not qualify a diffraction analysis | NOT_APPLICABLE | Export writes nodes and triangles only. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L35-L72] |
| G5 | Applicable: C4, preserve `get_stats` dimension/count fields in the evidence record and compare to fixture | 0 missing fields (count); vertex_count 3, face_count 1, extents 1,1,0 coordinate units | `TestOBJMesh::test_get_stats`; retain pin, command, result and input digest with downstream use. [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L98-L116] |

C2 covers Python only. Loading exported meshes in OrcaWave, OpenFOAM or Gmsh is NOT_RUN: target programs and their version-specific import acceptance are outside this offline check; no compatibility pass is inferred from the writer. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L5-L8] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L4-L8]

## 6. Known failure modes and pitfalls

| Symptom / cause | Detection | Evidence and disposition |
| --- | --- | --- |
| Missing curated data silently becomes empty output after a warning | `TestHullDataLoader::test_missing_data_dir`; require nonempty expected inventory separately | Loader fallback and test establish behavior, not dataset completeness; issue pending (2). [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_loader.py:L59-L63] [tests/unit/vessel_hull_models/rig_hulls/test_hull_loader.py:L90-L92] |
| Dimension mismatch is a warning while `valid` stays true | C0 plus `TestValidateObjFile::test_dimension_check_outside_tolerance`; downstream acceptance must inspect warnings | Warning append does not reset `valid`; issue pending (1). [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L335-L368] [tests/unit/vessel_hull_models/geometry/test_obj_parser.py:L320-L325] |
| Historical sparse-frame crash | C1 / R4 | [Issue 408](https://github.com/vamseeachanta/worldenergydata/issues/408); guard is present at this pin. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L185-L188] [tests/unit/vessel_hull_models/rig_hulls/test_hull_estimator.py:L231-L255] |
| Migration script inserted logging imports within open parentheses | C2 detects import failure; syntax parsing provides earlier detection | [Issue 275](https://github.com/vamseeachanta/worldenergydata/issues/275); historical mechanism recorded by issue; no dedicated module detection test exists. |
| CLI compare supplies keywords absent from the comparison function signature | No detection check exists in the module suite; compare call keywords against signature | Issue pending (3); static signature mismatch. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/cli.py:L332-L335] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L288-L293] |
| GDF scaling and malformed panel acceptance are not engineering validation | No detection check exists for unit scaling/panel integrity; require fixture-based checks | Issue pending (1); header is read but vertices are passed through; malformed coordinate lines return `None`. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L95-L111] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L285-L308] |

Issue searches also returned data/catalog/packaging work; these are scope context rather than confirmed module incidents: [349](https://github.com/vamseeachanta/worldenergydata/issues/349), [529](https://github.com/vamseeachanta/worldenergydata/issues/529), [1215](https://github.com/vamseeachanta/worldenergydata/issues/1215). No additional incident is inferred from an issue mention.

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Pack revision 0 | Separate estimated dimensions from independently qualified measurements | Confidence flags and default-table selection. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L139-L168] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L193-L235] | Not assigned; issue pending (2) |

## 8. Ownership

Review assignment: calculations quality manager; deputy calculations quality manager. Production responsibility: module maintainer. Escalation: unresolved criteria, missing independent sources and tolerance changes go to the calculations quality manager; cross-family changes go to the maintainer. This is the proposed ownership for this DRAFT pack, not evidence of completed review.

## 9. Dependencies and implementation inventory

Upstream Python dependencies include the shared core, curated-record package, NumPy, pandas, PyArrow, Plotly, Pydantic settings, Typer and Rich; the loader resolves curated Parquet from the installed upstream package and allows an injected directory. [packages/worldenergydata-vessel_hull_models/pyproject.toml:L34-L46] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_loader.py:L24-L51]

Matplotlib is guarded at import and raises `VisualizationError` when unavailable; geometry wrappers delegate rather than launch a solver. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/png_exporter.py:L14-L38] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L93-L108] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L127-L142]

### Solver and format names: complete textual inventory

| Name | Every source occurrence, grouped by definition | Interpretation |
| --- | --- | --- |
| OrcaWave | `ModelSource` enum and GDF parser module comments/docstring | Metadata/format naming only. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/data/models.py:L36-L46] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L1-L8] |
| OpenFOAM | MSH exporter module docstring | Intended downstream consumer; compatibility not tested. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L4-L8] |
| Gmsh | MSH exporter module comments/docstring, `export_to_msh` docstring and format/connectivity comments, `convert_obj_to_msh`, `convert_gdf_to_msh`, `validate_msh_file`; CLI `convert_gdf` and `batch_convert` option help | MSH 2.2 ASCII is written directly; no program invocation. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L1-L8] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L17-L23] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L55-L67] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L77-L88] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L111-L122] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L145-L153] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/cli.py:L398-L407] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/cli.py:L587-L599] |

Implementation-map inspection record (cross-repository metadata, outside the code pin): `digitalmodel`, branch `codex/implmap-work`, ref commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; embedded data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `docs/registry/implementation-map.yaml`. The inventory has 0 rows inside this package, hence 0 module map families and an empty section-9 mapped implementation inventory (inspection recorded 2026-10-15). Counted-family grep: NOT_APPLICABLE, because there is no in-package family. Map membership does not establish absence of duplicate code outside this repository.

Map follow-up: register OBJ triangulation/dimension checking, GDF parsing/symmetry, MSH serialization, hull-form classification/reference bucketing, dimension estimation and geometry visualization before counted-family evaluation (issue pending (4)); these are the section-3 method families. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/obj_parser.py:L250-L295] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L271-L308] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L17-L74] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_form_mapper.py:L45-L58] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L139-L168] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L36-L60]

Repository-wide discovery included `scripts/`: record-population scripts delegate to the listed mapper/estimator; module CLI and conversion wrappers delegate to listed parsers/writers rather than supply independent algorithms. [scripts/vessel_fleet/populate_hull_forms.py:L22-L23] [scripts/vessel_fleet/fuse_and_deduplicate.py:L23-L24] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/msh_exporter.py:L93-L108] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/cli.py:L429-L454]

## 10. Coverage and open items

Coverage: all 23 package Python files, the package README/packaging metadata, and all 9 module test files were inspected; the test files define 169 test functions. Test execution results are recorded below. No curated geometry or private reference dataset was qualified.

Test record: BASE and after each collected and passed 169 tests, with 0 failed, 0 skipped and 0 NOT_RUN. Contract tests additionally passed 46 cases, with 0 failed and 0 skipped. Code pin: `13f3b70aa7a87045631b737406c881e4cb5bcfd0`. Commands use ordinary `uv run python -m pytest`, module directory, `-q -rA -p no:cacheprovider` and separate scratch `--basetemp` directories. The after-run and contract run used the same pytest configuration with a scratch working directory, `uv run --project <checkout>` and `--allow-existing-tree-changes`; this preserves and compares the already-written pack while retaining the tree guard. Coverage output remained in scratch for those runs. No solver was started.

| Open item | Responsibility | Tracking |
| --- | --- | --- |
| Coordinate origin, handedness, phase and physical-unit provenance remain UNVERIFIED; add GDF/OBJ/MSH geometry-integrity fixtures and independent expected geometry | Module maintainer | issue pending (1); affected code reads header and returns unscaled vertices. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/geometry/gdf_parser.py:L293-L308] |
| Dimension-table independent source records/applicability remain UNVERIFIED; no validated physical example; qualify missing-data completeness separately and assign shared-log entry | Module maintainer | issue pending (2); table comments are not record-level citations. [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py:L29-L31] |
| CLI comparison keyword mismatch needs regression coverage and correction | Module maintainer | issue pending (3). [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/cli.py:L332-L335] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/visualization/plotly_3d.py:L288-L293] |
| Implementation-map families, independent examples and downstream G5 signed evidence require registration/qualification | Module maintainer | issue pending (4); method inventory is section 3 |
| Nested Markdown package-data glob includes the proposed pack; wheel exclusion is not established without a packaging change | Module maintainer | issue pending (5). [packages/worldenergydata-vessel_hull_models/pyproject.toml:L75-L76] |
| Historical capability/catalog statements need reconciliation with current package layout; routing registry is absent at the pin | Module maintainer | [Issue 349](https://github.com/vamseeachanta/worldenergydata/issues/349); historical source locations and CLI state are listed in the readiness matrix. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L492-L504] |

### Documentation discovery

Documentation discovery (historical claims; not current acceptance evidence):

- Module mention in `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml`. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L292-L292]
- Module mention in `docs/reports/data-freshness-scorecard-2026-06-08.md`. [docs/reports/data-freshness-scorecard-2026-06-08.md:L33-L33]
- Module mention in `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md`. [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L69-L69]
- Module mention in `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L16-L16]
- Module mention in `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L70-L70]
- Module mention in `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L492-L492]
- Module mention in `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md`. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L14-L14]
- Module mention in `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md`. [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L112-L112]
- Module mention in `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`. [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21]
- Module mention in `docs/adr/0001-domain-package-split.md`. [docs/adr/0001-domain-package-split.md:L48-L48]
- Module mention in `docs/modules/repository-architecture.md`. [docs/modules/repository-architecture.md:L121-L121]
The package README describes shared-root geometry and upstream curated-record dependencies. [packages/worldenergydata-vessel_hull_models/README.md:L6-L21]

No private sidecar value is included. External scientific references and licensed clause texts were not used to qualify a physical benchmark. Open items above require resolution or explicit review disposition before clearance.
