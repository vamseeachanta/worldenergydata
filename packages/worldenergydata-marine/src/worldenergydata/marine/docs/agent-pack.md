# Marine module knowledge pack

| Header | Value |
| --- | --- |
| Module | marine |
| Repository | worldenergydata |
| Package | `packages/worldenergydata-marine/src/worldenergydata/marine` |
| Pack revision | 0 |
| Code revision | `b1394197a66f95d78615425b4e1ad4ff78bd9de2` |
| Analysis family | EC; data pipeline under AQG r0 Python calculations |
| Quality role | Calculations quality manager; data quality role unassigned |
| Status | DRAFT |

## 1. Purpose and scope

`VesselGIS` copies an input DataFrame, filters records by spherical radius or polygon, and exports point features; `haversine_nm` is also exported publicly. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L106-L118] [packages/worldenergydata-marine/src/worldenergydata/marine/__init__.py:L3-L5]

The radius query sorts by `distance_nm`; the polygon test uses planar ray casting on longitude and latitude, without projection or geodesic edges. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L75-L98] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L179-L185]

Package metadata declares Alpha status; this is a metadata classification rather than an engineering qualification. [packages/worldenergydata-marine/pyproject.toml:L15-L23]

The implementation accepts in-memory tabular data and returns DataFrames or dictionaries; these methods contain no solver launch or persistent cache write. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L117-L247]

## 2. Inputs and outputs

| Input | Unit and convention | Allowed range / default | Source |
| --- | --- | --- | --- |
| `vessel_df` | `lat`, `lon` in decimal degrees; `vessel_id` for filtering | Empty permitted; nonempty table copied | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L106-L118] |
| `lat`, `lon` | Centre latitude then longitude, decimal degrees | No explicit bounds or finite-value validation | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L154-L185] |
| `radius_nm` | Nautical miles | Default 50.0; no positivity validation | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L124-L129] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L154-L185] |
| `field_name`, `bsee_fields_df` | Lookup key; upstream `field_name`, `lat`, `lon` | Query trimmed and uppercased; first match converted to float; built-in fallback | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L253-L284] |
| `polygon_coords` | `(lon, lat)` vertices; implicit closing edge | No vertex-count, datum or topology validation | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L75-L98] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L187-L209] |
| `vessel_ids` | Identifier list, dimensionless | `None`: all; filter applied only when identifier column exists | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L211-L231] |

| Output | Unit / form | Behaviour | Source |
| --- | --- | --- | --- |
| Radius result | DataFrame, `distance_nm` in nautical miles | Inclusive radius; ascending distance; index reset | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L179-L185] |
| Polygon result | DataFrame | Selected rows copied; index reset | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L205-L209] |
| Map data | FeatureCollection dictionary | Point coordinates `[lon, lat]`; remaining columns become properties | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L233-L247] |
| Unresolved / incomplete data | Empty DataFrame or empty feature list | Indistinguishable result shape from some legitimate empty queries | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L146-L149] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L172-L177] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L222-L231] |

UNVERIFIED: geographic datum, origin and signed-axis convention beyond the documented coordinate ordering are not established; issue pending (2). [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L43-L52] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L75-L85]

No phase convention or file-format reader is defined by the public query methods. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L124-L247]

## 3. Method and governing standards

| Method | Implementation and basis | Qualification limit |
| --- | --- | --- |
| Spherical distance | `haversine_nm`: degree-to-radian conversion; half-angle sines; `2*atan2(sqrt(a), sqrt(1-a))`; radius multiplication | Identical points short-circuit to zero; no clamping of `a` | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L42-L67] |
| Polygon membership | `_point_in_polygon`: toggle parity at horizontal ray crossings | Planar coordinate arithmetic; no boundary policy argument | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L75-L98] |
| Field selection | `_resolve_field_coords`: first external key match, then curated dictionary | External coordinate strings passed directly to `float` | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L270-L284] |
| Spatial selection | `query_vessels_by_coords` and `vessels_in_polygon` | Per-row evaluation; radius selection uses `<=` | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L179-L209] |
| Serialization | `get_vessel_map_data` | Copies properties without strict JSON encoding or finite-value checks | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L225-L247] |

UNVERIFIED: the source, datum and refresh date of the six curated coordinate entries are not established; issue pending (2). [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L21-L32]

UNVERIFIED: the documented Earth-radius constant has no published-source citation or citation sidecar beside its definition; issue pending (2). [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L34-L34]

No governing standard, edition or clause is named in either implementation file; no standards-derived acceptance value is asserted here. [packages/worldenergydata-marine/src/worldenergydata/marine/__init__.py:L1-L5] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L1-L284]

## 4. Validated worked examples and regression examples

Each listed node passed in both offline runs at the code revision in the header; BASE and AFTER results are recorded separately below.

| Case | Kind and independent basis | Inputs / expected value / tolerance | Existing test node | Offline result |
| --- | --- | --- | --- | --- |
| V1 | Validated; closed-form metric identity, coincident points | Fixture point repeated; distance exactly 0.0 nm; tolerance 0 nm | `tests/marine/test_vessel_gis.py::TestHaversineNm::test_haversine_zero_distance` | PASS, BASE and AFTER [tests/marine/test_vessel_gis.py:L47-L50] |
| V2 | Validated; same closed-form identity, separate smoke node | `(0, 0)` repeated; distance exactly 0.0 nm; tolerance 0 nm | `tests/unit/marine/test_smoke.py::test_trivial_public_api` | PASS, BASE and AFTER [tests/unit/marine/test_smoke.py:L13-L15] |
| R1 | Regression; synthetic record selection | Radius 50.0 nm; one fixture ID included and the other excluded; 0 incorrect selections | `tests/marine/test_vessel_gis.py::TestVesselGISQueryByCoords::test_query_by_coords_radius_filter` | PASS, BASE and AFTER [tests/marine/test_vessel_gis.py:L123-L129] |
| R2 | Regression; synthetic planar rectangle | Four fixture vertices; one ID inside, one outside; 0 incorrect selections | `tests/marine/test_vessel_gis.py::TestVesselGISVesselsInPolygon::test_vessels_in_polygon_filters_correctly` | PASS, BASE and AFTER [tests/marine/test_vessel_gis.py:L158-L165] |
| R3 | Regression; serialization of synthetic records | Every geometry Point; 2 coordinate components; 0 mismatches | `tests/marine/test_vessel_gis.py::TestVesselGISGetMapData::test_get_vessel_map_data_feature_geometry` | PASS, BASE and AFTER [tests/marine/test_vessel_gis.py:L183-L191] |
| R4 | Regression; unsourced interval assertion | Strictly 100.0 to 115.0 nm; tolerance basis unestablished, issue pending (4) | `tests/marine/test_vessel_gis.py::TestHaversineNm::test_haversine_known_distance` | PASS, BASE and AFTER [tests/marine/test_vessel_gis.py:L52-L57] |

The nonzero-distance interval assertion is retained as regression evidence only: it asserts a distance strictly between 100.0 and 115.0 nm without an independent source, and the prose tolerance differs from that interval; issue pending (4). [tests/marine/test_vessel_gis.py:L52-L57]

## 5. QA gates

Checks below are pack acceptance criteria; test references bind each executable check to the implementation quantities rather than claiming complete input qualification.

| Gate | Applicability | Checks / numeric pass criterion and unit | Evidence route |
| --- | --- | --- | --- |
| G0 | Applicable: inputs, units, citations | C01: `query_vessels_by_coords` fixture radius 50.0 nm produces 0 incorrect fixture-ID selections; C02: `get_vessel_map_data` emits exactly 2 coordinate components per Point | R1 and R3 nodes, cited in section 4 |
| G1 | Applicable: Python imports and tests | C03: `tests/unit/marine/test_smoke.py::test_package_imports` has 0 import failures; C04: marine suites have 0 test failures, unit: test cases | [tests/unit/marine/test_smoke.py:L5-L10] [tests/marine/test_vessel_gis.py:L46-L205] |
| G2 | Applicable: hand check | C05: `haversine_nm` coincident-point identity equals 0.0 nm with 0 nm tolerance; this does not establish nonzero-distance accuracy | V1 and V2 nodes, cited in section 4 |
| G3 | NOT_APPLICABLE | No dynamics integration or solver time history in this package | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L42-L284] |
| G4 | NOT_APPLICABLE | No diffraction mesh or hydrodynamic coefficient calculation in this package | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L42-L284] |
| G5 | Applicable: evidence traceability | C06: 100 percent of section-4 cases have an existing test node and an individual result, unit: cases; unresolved example results shall be 0 before clearance | Section-4 cases and their cited test assertions |

| Additional check | Gate | Numeric criterion and unit | Existing test node / detection limit |
| --- | --- | --- | --- |
| C07 | G0 | Unknown key returns exactly 0 records | `tests/marine/test_vessel_gis.py::TestVesselGISQueryByFieldArea::test_query_by_field_area_unknown_field_returns_empty` [tests/marine/test_vessel_gis.py:L91-L96] |
| C08 | G0 | Empty input emits exactly 0 features | `tests/marine/test_vessel_gis.py::TestVesselGISGetMapData::test_get_vessel_map_data_empty_vessels` [tests/marine/test_vessel_gis.py:L201-L205] |
| C09 | G2 | Reversing distance endpoints changes distance by less than 0.000001 nm | `tests/marine/test_vessel_gis.py::TestHaversineNm::test_haversine_symmetry` [tests/marine/test_vessel_gis.py:L59-L63] |
| C10 | G0 | Requested fixture-ID selection has 0 extra or missing IDs | `tests/marine/test_vessel_gis.py::TestVesselGISGetMapData::test_get_vessel_map_data_filter_by_ids` [tests/marine/test_vessel_gis.py:L193-L199] |
| C11 | G0 | Unmatched radius query returns exactly 0 records | `tests/marine/test_vessel_gis.py::TestVesselGISQueryByCoords::test_query_by_coords_empty_when_no_matches` [tests/marine/test_vessel_gis.py:L143-L147] |
| C12 | G0 | External field-table fixture returns the expected ID, 0 missing IDs | `tests/marine/test_vessel_gis.py::TestVesselGISQueryByFieldArea::test_query_with_bsee_fields_integration`; does not distinguish fallback from external-table precedence [tests/marine/test_vessel_gis.py:L98-L107] |

G0 has 7 checks, G1 has 2, G2 has 2 and G5 has 1; G3 and G4 have 0 applicable checks.

## 6. Known failure modes and pitfalls

sweep: 25 found

The sweep covers the entire package's two Python files; rows include intentional defaults and empty-result branches, so the count is an inventory rather than a defect count. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L1-L284] [packages/worldenergydata-marine/src/worldenergydata/marine/__init__.py:L1-L5]

```sh
rg -n 'except|continue|return None|return \[\]|return \{\}|return pd.DataFrame|features.*\[\]|= 0(\.0)?\b|1970|float\(|int\(|radius_nm|degrees|_EARTH_RADIUS' packages/worldenergydata-marine/src/worldenergydata/marine --glob '*.py'
rg -n 'fillna|setdefault|cache|json|dropna|isna|isfinite|pass|0\.05|5%' packages/worldenergydata-marine/src/worldenergydata/marine --glob '*.py'
```

| ID | Symptom / cause at pin | Detection check or missing coverage | Tracking |
| --- | --- | --- | --- |
| S01 | Empty constructor input loses even the input columns. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L117-L118] | C08 covers empty export only; no detection check exists for schema preservation | issue pending (1) |
| S02 | Unknown field returns an empty DataFrame after warning. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L146-L149] | C07; intentional fallback, no typed unresolved status | issue pending (1) |
| S03 | Empty radius-query input returns an empty DataFrame. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L172-L173] | no detection check exists | issue pending (1) |
| S04 | Missing coordinate columns return an empty radius result after warning. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L175-L177] | no detection check exists | issue pending (1) |
| S05 | Empty polygon-query input returns an empty DataFrame. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L198-L199] | no detection check exists | issue pending (1) |
| S06 | Missing coordinate columns return an empty polygon result after warning. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L201-L203] | no detection check exists | issue pending (1) |
| S07 | Empty map input returns an empty feature list. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L222-L223] | C08 | issue pending (1) |
| S08 | Missing map coordinate columns silently return an empty feature list. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L230-L231] | no detection check exists | issue pending (1) |
| S09 | Requested ID filter is omitted when identifier column is missing. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L227-L228] | C10 covers present column only; no detection check exists for missing column | issue pending (1) |
| S10 | Unavailable external key or schema silently falls back to curated coordinates. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L272-L282] | C12 cannot distinguish precedence; no detection check exists | issue pending (2) |
| S11 | Duplicate external keys use the first row without ambiguity reporting. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L275-L278] | no detection check exists | issue pending (2) |
| S12 | Two external coordinate cells use float conversion without separator or finite-value validation. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L278-L278] | no detection check exists | issue pending (2) |
| S13 | Unknown coordinate lookup returns None. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L280-L284] | C07 exercises caller result; no direct helper assertion | issue pending (1) |
| S14 | Field-area default radius silently selects a 50.0 nm search. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L128-L128] | no detection check exists for the default boundary | issue pending (2) |
| S15 | Coordinate-query default radius silently selects a 50.0 nm search. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L158-L158] | C01 covers explicit radius only; no detection check exists for default boundary | issue pending (2) |
| S16 | NaN distance fails the <= mask and silently drops a record; negative radius also selects no records. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L179-L185] | C11 covers ordinary no-match only; no detection check exists | issue pending (3) |
| S17 | Decimal-degree input and nautical-mile output are assumed without unit conversion metadata. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L43-L67] | C05 and C09; no detection check exists for input units | issue pending (2) |
| S18 | Hardcoded spherical radius is used without source metadata. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L34-L34] | no detection check exists for constant provenance | issue pending (2) |
| S19 | Empty or degenerate polygon starts false and may silently select no records. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L87-L98] | no detection check exists | issue pending (3) |
| S20 | Polygon arithmetic assumes a planar longitude/latitude frame without wrap or boundary contract. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L75-L98] | R2 covers an ordinary rectangle only; no detection check exists for boundaries | issue pending (3) |
| S21 | Exact-equality distance branch returns 0.0 before numeric validation. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L54-L55] | C05 covers valid coincident coordinates only | issue pending (3) |
| S22 | Feature accumulator begins empty and can remain empty after ID selection. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L225-L247] | C10 covers a present selected ID; no detection check exists for no selected IDs | issue pending (1) |
| S23 | Map properties and coordinates are exported without strict JSON or finite-value validation. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L233-L247] | C02 checks shape only; no detection check exists for serialization validity | issue pending (3) |
| S24 | Non-finite record coordinates can make polygon comparisons false and silently omit a record. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L87-L98] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L205-L209] | no detection check exists | issue pending (3) |
| S25 | Query keys are stripped but external key cells are only uppercased; surrounding whitespace can trigger fallback. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L270-L282] | C12 uses clean keys only; no detection check exists | issue pending (2) |

No swallowed `except`, record-skipping `continue`, integer conversion, epoch default or cache write appears in the complete implementation; all direct floating conversions are covered by S12. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L1-L284]

The square-root distance formula has no clamp for roundoff near antipodal inputs; no detection check exists for that condition; issue pending (3). [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L62-L67]

The searched issue leads do not establish a marine-GIS incident; inventory and packaging history are context rather than demonstrated calculation incidents. [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L15-L23] [packages/worldenergydata-marine/README.md:L1-L8]

## 7. Lessons log

| Date | Entry | Lesson | Evidence | Change / shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-17 | Initial pack | An empty spatial result cannot establish input readiness; missing columns also produce empty output | [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L172-L177] | Failure inventory added; shared-log entry unassigned, issue pending (1) |

## 8. Ownership

Designated review roles for this draft: calculations quality manager; deputy calculations reviewer; producing role: module documentation contributor; escalation: maintainer for scope and the quality manager for criteria or ambiguous input contracts.

This draft requires a second-provider review before the maintainer merges.

## 9. Dependencies and implementation inventory

The runtime imports pandas and standard-library logging, math and typing; the package declares pandas and the shared core distribution as dependencies. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L11-L19] [packages/worldenergydata-marine/pyproject.toml:L30-L33]

The upstream input is an in-memory record table with optional external field coordinates; the downstream output is a filtered table or a point-feature dictionary, with no specific solver version dependency. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L106-L118] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L124-L152] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L211-L247]

### Implementation-map inventory

Map source: `digitalmodel`, `docs/registry/implementation-map.yaml`, ref `origin/codex/implmap-work`, map-file commit `3256bab95f84da3d9fadce8d5dcf8458d66d1eb4`, data revision `270c8759c374b67a7f032953e7fcdb14e0224461`, schema 1.

A8 inventory: 0 map families contain an implementation row inside this pack's header package; consequently the implementation inventory is empty, counted families are empty, and the counted-family grep is `NOT_APPLICABLE` because no in-package map rows exist at that map revision.

Map follow-up: register spherical distance, planar point-in-polygon, radius/field spatial selection and point-feature serialization before these families can become counted; issue pending (5). [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L42-L98] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L124-L247]

### Repository-wide discovery

```sh
rg -n 'VesselGIS|haversine_nm|_point_in_polygon' --glob '*.py'
rg -n 'haversine|point_in_polygon|ray.casting|great.circle' src packages scripts --glob '*.py'
```

The in-package calculations are `haversine_nm` and `_point_in_polygon`; `query_vessels_by_field_area` delegates to the radius query, and the radius and polygon methods delegate to those functions. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L42-L98] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L146-L152] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L179-L209]

Further search results outside this package are map-follow-up candidates and do not change A8; the implementation map must classify those candidates before any canonicalization, issue pending (5).

| Outside-package definition | Output unit | Classification / evidence |
| --- | --- | --- |
| `packages/worldenergydata-metocean/src/worldenergydata/metocean/utils/coordinates.py`, `haversine_distance` | km | Computes its own spherical-distance formula; map gap, issue pending (5). [packages/worldenergydata-metocean/src/worldenergydata/metocean/utils/coordinates.py:L76-L100] |
| `packages/worldenergydata-metocean/src/worldenergydata/metocean/extrapolation/source_catalog.py`, `distance_km` | km | Computes its own spherical-distance formula; map gap, issue pending (5). [packages/worldenergydata-metocean/src/worldenergydata/metocean/extrapolation/source_catalog.py:L106-L127] |
| `packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_fusion.py`, `haversine_distance` | km | Computes its own spherical-distance formula; map gap, issue pending (5). [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_fusion.py:L803-L829] |
| `packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py`, `_haversine_km` | km | Computes its own spherical-distance formula; map gap, issue pending (5). [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L190-L205] |
| `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/spatial.py`, `haversine_miles` | miles | Computes its own spherical-distance formula; map gap, issue pending (5). [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/spatial.py:L39-L54] |
| `packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py`, `_haversine` | km | Computes its own spherical-distance formula; map gap, issue pending (5). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L357-L373] |
| `packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py`, `_haversine_distance` | km | Computes its own spherical-distance formula; map gap, issue pending (5). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L613-L643] |

## 10. Coverage and open items

### Read scope

The package contains two implementation files, both read in full: `__init__.py` and `vessel_gis.py`; there are no implementation subpackages to exclude. [packages/worldenergydata-marine/src/worldenergydata/marine/__init__.py:L1-L5] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L1-L284]

Package documentation and configuration read: `packages/worldenergydata-marine/README.md` and `packages/worldenergydata-marine/pyproject.toml`. [packages/worldenergydata-marine/README.md:L1-L8] [packages/worldenergydata-marine/pyproject.toml:L1-L55]

Repository documentation found by exact module/import/path search and read:

- `docs/adr/0001-domain-package-split.md`; historical isolation classification, not current qualification. [docs/adr/0001-domain-package-split.md:L43-L49]
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`; historical inventory lead. [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L15-L23]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`; historical zero-test/module-layout claims are superseded by the test inventory below. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L184-L190]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml`; historical off-manifest note. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L780-L795]

### Test inventory

The implementation suite defines 20 tests and the import/API smoke file defines 2, giving 22 test cases rather than relying on an inventory estimate. [tests/marine/test_vessel_gis.py:L46-L205] [tests/unit/marine/test_smoke.py:L9-L15]

All nodes below are in `tests/marine/test_vessel_gis.py`, except the two fully qualified smoke nodes:

- `tests/marine/test_vessel_gis.py::TestHaversineNm::test_haversine_zero_distance`. [tests/marine/test_vessel_gis.py:L47-L50]
- `tests/marine/test_vessel_gis.py::TestHaversineNm::test_haversine_known_distance`. [tests/marine/test_vessel_gis.py:L52-L57]
- `tests/marine/test_vessel_gis.py::TestHaversineNm::test_haversine_symmetry`. [tests/marine/test_vessel_gis.py:L59-L63]
- `tests/marine/test_vessel_gis.py::TestHaversineNm::test_haversine_positive`. [tests/marine/test_vessel_gis.py:L65-L68]
- `tests/marine/test_vessel_gis.py::TestVesselGISQueryByFieldArea::test_query_by_field_area_returns_df`. [tests/marine/test_vessel_gis.py:L77-L81]
- `tests/marine/test_vessel_gis.py::TestVesselGISQueryByFieldArea::test_query_by_field_area_gom_builtin`. [tests/marine/test_vessel_gis.py:L83-L89]
- `tests/marine/test_vessel_gis.py::TestVesselGISQueryByFieldArea::test_query_by_field_area_unknown_field_returns_empty`. [tests/marine/test_vessel_gis.py:L91-L96]
- `tests/marine/test_vessel_gis.py::TestVesselGISQueryByFieldArea::test_query_with_bsee_fields_integration`. [tests/marine/test_vessel_gis.py:L98-L107]
- One additional node has an identifying label; its spelling is omitted pending neutral codenaming, issue pending (7). [tests/marine/test_vessel_gis.py:L109-L119]
- `tests/marine/test_vessel_gis.py::TestVesselGISQueryByCoords::test_query_by_coords_radius_filter`. [tests/marine/test_vessel_gis.py:L123-L129]
- `tests/marine/test_vessel_gis.py::TestVesselGISQueryByCoords::test_query_by_coords_returns_df`. [tests/marine/test_vessel_gis.py:L131-L135]
- `tests/marine/test_vessel_gis.py::TestVesselGISQueryByCoords::test_query_by_coords_distance_column`. [tests/marine/test_vessel_gis.py:L137-L141]
- `tests/marine/test_vessel_gis.py::TestVesselGISQueryByCoords::test_query_by_coords_empty_when_no_matches`. [tests/marine/test_vessel_gis.py:L143-L147]
- `tests/marine/test_vessel_gis.py::TestVesselGISVesselsInPolygon::test_vessels_in_polygon_returns_df`. [tests/marine/test_vessel_gis.py:L151-L156]
- `tests/marine/test_vessel_gis.py::TestVesselGISVesselsInPolygon::test_vessels_in_polygon_filters_correctly`. [tests/marine/test_vessel_gis.py:L158-L165]
- `tests/marine/test_vessel_gis.py::TestVesselGISGetMapData::test_get_vessel_map_data_structure`. [tests/marine/test_vessel_gis.py:L169-L175]
- `tests/marine/test_vessel_gis.py::TestVesselGISGetMapData::test_get_vessel_map_data_features_list`. [tests/marine/test_vessel_gis.py:L177-L181]
- `tests/marine/test_vessel_gis.py::TestVesselGISGetMapData::test_get_vessel_map_data_feature_geometry`. [tests/marine/test_vessel_gis.py:L183-L191]
- `tests/marine/test_vessel_gis.py::TestVesselGISGetMapData::test_get_vessel_map_data_filter_by_ids`. [tests/marine/test_vessel_gis.py:L193-L199]
- `tests/marine/test_vessel_gis.py::TestVesselGISGetMapData::test_get_vessel_map_data_empty_vessels`. [tests/marine/test_vessel_gis.py:L201-L206]
- `tests/unit/marine/test_smoke.py::test_package_imports`. [tests/unit/marine/test_smoke.py:L9-L10]
- `tests/unit/marine/test_smoke.py::test_trivial_public_api`. [tests/unit/marine/test_smoke.py:L13-L15]

### Open-item register

| Item | Responsible role | Tracking / disposition |
| --- | --- | --- |
| Empty results and schema loss; missing-ID filter; explicit failure diagnostics | Marine maintainer | issue pending (1); S01–S09, S13, S22 |
| Datum/sign convention; curated-coordinate provenance; radius source; parsing, duplicate keys and fallback semantics | Marine maintainer | issue pending (2); three unresolved claims from sections 2–3; S10–S12, S14–S18, S25 |
| Numerical domain, degenerate/boundary geometry and strict JSON | Marine maintainer | issue pending (3); S16, S19–S21, S23–S24 |
| Independent nonzero-distance benchmark and inconsistent regression tolerance prose | Calculations quality manager | issue pending (4); current validated examples cover only zero distance |
| Map families and repository-wide candidate classification | Registry maintainer | issue pending (5); no counted families at named map revision |
| Recursive Markdown package-data glob can ship the pack | Packaging maintainer | issue pending (6); configuration is unchanged [packages/worldenergydata-marine/pyproject.toml:L54-L55] |
| One identifying test-node label and fixture labels | Marine maintainer | issue pending (7); identifying spellings omitted [tests/marine/test_vessel_gis.py:L14-L37] [tests/marine/test_vessel_gis.py:L109-L119] |
| Historical readiness inventory says no module-level tests | Documentation maintainer | #349; current 22-case inventory above replaces that historical count [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L184-L190] |

No module-routing registry is present at the code pin, so no routing entry is added; the index remains a maintainer follow-up under issue pending (5).

### Offline execution record

| Run | Command form | Revision | Run / passed / failed / skipped / NOT_RUN |
| --- | --- | --- | --- |
| BASE | `uv run python -m pytest tests/marine tests/unit/marine --noconftest -q -rA -p no:cacheprovider` | `b1394197a66f95d78615425b4e1ad4ff78bd9de2` | 22 / 22 / 0 / 0 / 0 |
| AFTER | Same form and paths; documentation-only working tree | Same code revision | 22 / 22 / 0 / 0 / 0 |
| Contracts | `uv run python -m pytest tests/contracts --noconftest -q -rA -p no:cacheprovider` | Same code revision | 46 / 46 / 0 / 0 / 0 |

The documented `--noconftest` form was used, ordinary source resolution succeeded, no addopts override was used, and coverage reports and base temporary directories were directed to scratch storage.

The citation audit and second-provider clearance remain distinct records; this pack remains DRAFT until review.
