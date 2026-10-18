# Field-development module knowledge pack

| Header | Value |
| --- | --- |
| Module | `field_development` |
| Repository | `worldenergydata` |
| Path | `src/worldenergydata/field_development` (package scope) |
| Pack | `src/worldenergydata/field_development/docs/agent-pack.md` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `55991b0def0f90708b3e0c396c0f57d9d1b7f7fb` |
| Analysis family | EC (engineering calculations); data pipeline; AQG r0 section 10 Python calculations gate set |
| Quality manager role | Calculations quality manager, interim data-pipeline coverage |
| Status | DRAFT; independent clearance pending |

## 1. Purpose and scope

The main path constructs `FieldConcept`, returns cross-field sanity violations, ranks feasible concepts, maps a concept to a graph, and renders a schematic report. [src/worldenergydata/field_development/loader.py:L21-L44] [src/worldenergydata/field_development/recommendation.py:L401-L429] [src/worldenergydata/field_development/graph.py:L127-L157] [src/worldenergydata/field_development/fdp_report.py:L200-L246]

The recommendation is a deterministic heuristic shortlist; the report describes Concept Select fidelity rather than a sanctioned design. [src/worldenergydata/field_development/recommendation.py:L12-L24] [src/worldenergydata/field_development/fdp_report.py:L226-L228]

The flow-assurance path screens hydrate, wax, slugging and erosion hazards; it does not compute transient multiphase hydraulics or size insulation. [src/worldenergydata/field_development/flow_assurance.py:L7-L34]

This revision documents the screening and schematic main path in detail; catalog integration, reference queries, terrain, phase norms, economics and optional geometry are indexed for further coverage in section 10. [src/worldenergydata/field_development/__init__.py:L27-L175]

UNVERIFIED: U1 — conformity to the named engineering standards, their governing editions and clauses, and citation-sidecar completeness have not been established; #1322.

UNVERIFIED: U2 — independent engineering validation, comprehensive coverage of the supporting paths, and deployment suitability beyond the offline checks remain open; #1323.

Routing audit record: no `docs/registry/module-routing.yaml` exists at the code pin; no registry maturity is asserted.

## 2. Inputs and outputs

### Inputs

| Input | Unit | Allowed values and default | Entry and evidence |
| --- | --- | --- | --- |
| `name`, `operator`, `region`, `data_source` | text | `name` required and nonblank; other fields default to `None`; extra fields forbidden | [src/worldenergydata/field_development/models.py:L57-L68] [src/worldenergydata/field_development/models.py:L119-L129] |
| `water_depth_m`, host/shore/tieback distances | m; km | Nonnegative or `None`; default `None` | [src/worldenergydata/field_development/models.py:L86-L103] [src/worldenergydata/field_development/models.py:L131-L152] |
| Reserves, production rates, field life | MMboe; boe/day; years | Nonnegative or `None`; default `None` | [src/worldenergydata/field_development/models.py:L70-L83] [src/worldenergydata/field_development/models.py:L131-L152] |
| GOR; viscosity; API gravity | scf/stb; cP; API gravity | GOR/viscosity nonnegative; gravity strictly between 0 and 100; default `None` | [src/worldenergydata/field_development/models.py:L70-L77] [src/worldenergydata/field_development/models.py:L131-L160] |
| Counts and timeline years | count; year | Nonnegative integers or `None`; default `None` | [src/worldenergydata/field_development/models.py:L78-L83] [src/worldenergydata/field_development/models.py:L115-L184] |
| `discount_rate`; oil and gas prices | fraction; USD/bbl; USD/MMBtu | Rate in [0, 1); prices have no custom range validator; default `None` | [src/worldenergydata/field_development/models.py:L109-L113] [src/worldenergydata/field_development/models.py:L131-L184] |
| Fluid, architecture, metocean and reservoir categories | categorical | Enum values or `None` | [src/worldenergydata/field_development/enums.py:L20-L90] [src/worldenergydata/field_development/models.py:L70-L107] |
| Wax appearance temperature | C | Optional float, default `None`; no custom bound validator | [src/worldenergydata/field_development/models.py:L70-L77] [src/worldenergydata/field_development/models.py:L131-L184] |
| Sour, HPHT, injection and host-capacity flags | boolean | Optional; default `None` | [src/worldenergydata/field_development/models.py:L76-L93] |
| Flowline diameter and seabed terrain | in; text | Diameter nonnegative or `None`; terrain optional text; both default `None` | [src/worldenergydata/field_development/models.py:L86-L104] [src/worldenergydata/field_development/models.py:L131-L152] |
| `schema_version` | text | Default `1.0.0`; caller-provided string is accepted by the model definition | [src/worldenergydata/field_development/models.py:L47-L62] |
| JSON concept file | same units as model | UTF-8 JSON, passed directly to `FieldConcept` | [src/worldenergydata/field_development/loader.py:L26-L29] |
| Weights and thresholds | dimensionless; km; MMboe; count | Optional call overrides; dataclass defaults; recommendation weights are normalized at use | [src/worldenergydata/field_development/recommendation.py:L55-L75] [src/worldenergydata/field_development/recommendation.py:L129-L137] [src/worldenergydata/field_development/recommendation.py:L394-L429] |

### Outputs

| Output | Unit and convention | Limit and evidence |
| --- | --- | --- |
| `validate_concept` tuple | Model plus violation records | Single-field construction can raise; cross-field checks return records [src/worldenergydata/field_development/loader.py:L32-L44] |
| `recommend` list | Criterion and total scores dimensionless | Descending total, alphabetical concept tie-break; `top_n` slices results [src/worldenergydata/field_development/recommendation.py:L381-L429] |
| `FlowAssuranceAssessment` | Ordinal severity, metrics in C and ft/s, ratio dimensionless | Maximum hazard severity and deduplicated mitigations [src/worldenergydata/field_development/flow_assurance.py:L214-L229] [src/worldenergydata/field_development/flow_assurance.py:L410-L414] [src/worldenergydata/field_development/flow_assurance.py:L468-L499] |
| `GraphSpec` / dictionary | Typed nodes and edges, no spatial unit | Graph coordinates are assigned separately [src/worldenergydata/field_development/graph.py:L79-L104] [src/worldenergydata/field_development/graph.py:L127-L157] |
| Plan SVG / position mappings | Internal km, north +y; SVG px, y down | Manifolds centered at origin; host north; drawing scale in px/km [src/worldenergydata/field_development/layout.py:L65-L155] |
| Block SVG and HTML | SVG px and UTF-8 HTML text | Block diagram is logical; report embeds both renderers [src/worldenergydata/field_development/block.py:L76-L133] [src/worldenergydata/field_development/fdp_report.py:L214-L246] |
| DEXPI-aligned XML | Topology and labels, no geometric units | `PlantModel` equipment and piping; generic subsea attributes [src/worldenergydata/field_development/dexpi.py:L65-L105] |

The schematic origin and north direction are synthetic placement conventions; no geodetic location is assigned by `compute_positions`. [src/worldenergydata/field_development/layout.py:L65-L123]

## 3. Method and governing standards

| Method or reference | Implementation and traceability |
| --- | --- |
| Feasibility and ranking | `feasible_concepts` filters host depth envelopes and host reachability; `_weighted_total` divides the weighted sum by the weight sum, using a denominator fallback for a zero sum; `recommend` sorts the results. [src/worldenergydata/field_development/recommendation.py:L200-L245] [src/worldenergydata/field_development/recommendation.py:L394-L429] |
| Depth and regional priors | `_depth_fit` is flat inside the preferred band and decays linearly outside; unknown depth is neutral; `region_fit` is neutral for an unmapped region. [src/worldenergydata/field_development/recommendation.py:L114-L125] [src/worldenergydata/field_development/basin.py:L146-L163] |
| Graph and layout | Wet-tree nodes route through manifolds; dry wellheads connect to the host; the plan renderer uses trigonometric rings and linear pixel scaling. [src/worldenergydata/field_development/graph.py:L160-L196] [src/worldenergydata/field_development/layout.py:L126-L155] |
| Hazard screening | Temperature is a linear depth envelope with a floor; hazard driver counts set ordinal tiers; bulk velocity is volumetric rate divided by circular bore area with unit conversions. [src/worldenergydata/field_development/flow_assurance.py:L58-L62] [src/worldenergydata/field_development/flow_assurance.py:L82-L99] [src/worldenergydata/field_development/flow_assurance.py:L169-L183] [src/worldenergydata/field_development/flow_assurance.py:L384-L392] |
| API RP 14E and API RP 14J | `screen_erosion_risk` compares bulk velocity with an overridable fixed threshold; the code explicitly does not calculate a mixture-density-dependent limit; editions, publication titles and clause identifiers are absent from this reference block. Clause text not checked against the licensed copy; U1, #1322. [src/worldenergydata/field_development/flow_assurance.py:L38-L45] [src/worldenergydata/field_development/flow_assurance.py:L395-L451] |
| ISO 15926 | The XML adapter explicitly disclaims full ISO-15926 conformance; the briefing calls DEXPI ISO-15926-rooted; neither supplies a governing edition or clause here. Clause text not checked against the licensed copy; U1, #1322. [src/worldenergydata/field_development/dexpi.py:L15-L26] [docs/domains/field-development/concept-selection-and-ai-cad-briefing.md:L245-L250] |
| ANSI/ISA-5.1 | The symbol docstring describes style guidance only; the briefing names ANSI/ISA-5.1-2024 but supplies no clause. This is an edition-detail omission in code, rather than evidence of contradictory editions. Clause text not checked against the licensed copy; U1, #1322. [src/worldenergydata/field_development/symbols/__init__.py:L7-L22] [docs/domains/field-development/concept-selection-and-ai-cad-briefing.md:L181-L184] |
| Calibration basis | The depth-prior comments disclose hand-set in-sample decision boundaries and no train/test holdout; backtesting removes `concept_type` and `operator` from the probe. [src/worldenergydata/field_development/recommendation.py:L79-L100] [src/worldenergydata/field_development/calibration.py:L80-L96] |

No standards-derived tabulated value is reproduced here; the erosion implementation should be treated as a configurable screening heuristic while its provenance is resolved. [src/worldenergydata/field_development/flow_assurance.py:L38-L45]

## 4. Validated worked examples

Offline record date: 2026-10-15; code pin as in header; BASE results below, repeated AFTER without module-code changes.

### Closed-form validation

| ID | Source and inputs | Independent expectation, tolerance and basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| V1 | Synthetic in-test concept: one manifold, 12 km tieback, 50 px/km | Linear distance scaling: 12 × 50 = 600 px; absolute error 0 px, exact equality of the axis-aligned geometry; validates drawing scale only | `tests/modules/field_development/test_layout.py::test_host_to_manifold_pixel_distance_equals_tieback_times_scale` | PASS at BASE and AFTER [tests/modules/field_development/test_layout.py:L26-L37] |

### Regression examples

| ID | Fixture and expected behavior | Tolerance and basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 | Synthetic near-host concept ranks `subsea_tieback` first | 0 categorical mismatches; heuristic expectation, not independent engineering truth | `tests/modules/field_development/test_recommendation.py::test_marginal_near_host_field_recommends_tieback` | PASS at BASE and AFTER [tests/modules/field_development/test_recommendation.py:L49-L60] |
| R2 | Concept without depth returns LOW hydrate severity and a nonempty note | 0 missing notes; policy regression, not a safety clearance | `tests/modules/field_development/test_flow_assurance.py::test_hydrate_unknown_depth_is_low_and_noted` | PASS at BASE and AFTER [tests/modules/field_development/test_flow_assurance.py:L75-L78] |
| R3 | Graph XML round-trip preserves nodes and edges | 0 differing node attributes or edge tuples; self-round-trip regression | `tests/modules/field_development/test_dexpi.py::test_roundtrip_preserves_nodes_and_edges` | PASS at BASE and AFTER [tests/modules/field_development/test_dexpi.py:L75-L89] |

The geometry case establishes scale arithmetic only; the hazard tests explicitly check heuristic direction rather than precise physical predictions. [tests/modules/field_development/test_layout.py:L26-L37] [tests/modules/field_development/test_flow_assurance.py:L5-L9]

## 5. QA gates

Gate selection: AQG r0, section 10, Python calculations; section 9, evidence appendix. The criteria below are proposed repeatable checks, not quality-manager signatures.

| Gate | Applicability | Module-specific route |
| --- | --- | --- |
| G0 | Applicable: inputs, units, citations | `FieldConcept`, `sanity_check`, JSON schema and provenance review [src/worldenergydata/field_development/models.py:L131-L184] [src/worldenergydata/field_development/loader.py:L32-L44] |
| G1 | Applicable: imports and offline tests | Python/pytest; XML parsed by ElementTree and SVG checked by renderer tests; no external-program load claim [tests/modules/field_development/test_dexpi.py:L34-L41] [tests/modules/field_development/test_layout.py:L70-L76] |
| G2 | Applicable: independent hand or published check | V1 closed-form scale check; engineering-screen validation remains U2 [tests/modules/field_development/test_layout.py:L26-L37] |
| G3 | NOT_APPLICABLE | AQG r0 section 10 excludes short dynamics for Python calculations. |
| G4 | NOT_APPLICABLE | AQG r0 section 10 excludes diffraction QA for Python calculations. |
| G5 | Applicable: traceable evidence appendix | Record tests, pin, input hashes and outstanding items; the report builder itself ends with source prose and embeds diagrams, without an AQG signature record [src/worldenergydata/field_development/fdp_report.py:L200-L246] |

| Check ID | Operation and executable evidence | Numeric pass criterion and unit | Gate |
| --- | --- | --- | --- |
| FD-G0-1 | `tests/modules/field_development/test_field_concept.py::test_negative_water_depth_rejected`: construct `FieldConcept` with negative depth | 1 `ValidationError` raised, count [tests/modules/field_development/test_field_concept.py:L70-L72] | G0 |
| FD-G0-2 | `tests/modules/field_development/test_field_concept.py::test_committed_json_schema_matches_model`: compare committed JSON schema with `build_schema()` | 0 differing schema values, count [tests/modules/field_development/test_field_concept.py:L190-L197] | G0 |
| FD-G1-1 | Run both module test directories and the discovered consumer/contract tests | 0 failed tests and 0 collection errors, count; retain all skip reasons [tests/modules/field_development/test_field_concept.py:L172-L174] | G1 |
| FD-G1-2 | R3: `dexpi_to_graph(graph_to_dexpi(graph))` compared with the original graph | 0 differing node attributes and 0 differing edge tuples, count [tests/modules/field_development/test_dexpi.py:L75-L89] | G1 |
| FD-G2-1 | V1: `compute_pixel_positions`, measure host-to-manifold Euclidean distance against distance × scale | 600 px expected, absolute error 0 px [tests/modules/field_development/test_layout.py:L26-L37] | G2 |
| FD-G2-2 | Diagnostic: construct `FieldConcept(name="synthetic", water_depth_m=1500.0, num_wells=6, discount_rate=0.0)` and read `estimate_economics(concept).discount_rate`; script `evidence/probe-zero.py` retained outside the repository | Returned rate = 0.0, fraction; observed 0.1 at BASE and AFTER: FAIL, known defect, #1324 [src/worldenergydata/field_development/models.py:L162-L168] [src/worldenergydata/field_development/integrations.py:L138-L146] | G2 |
| FD-G5-1 | `tests/modules/field_development/test_fdp_report.py::test_embeds_both_visualizations`: inspect `build_fdp_html` output | At least 2 inline SVG elements, count; this checks composition, not signed clearance [tests/modules/field_development/test_fdp_report.py:L48-L52] | G5 |
| FD-G5-2 | Proposed evidence-assembly check: resolve every citation at the pin, associate V1/R1–R3 with run records, and hash the pack and evidence inputs; retained records listed in section 10 | 0 unresolved citations and 0 unmatched example nodes, count; 1 SHA-256 per evidence input, digest count | G5 |

## 6. Known failure modes and pitfalls

sweep: 94 found — candidate matching lines, not confirmed defects, at commit `71955f077f3da2667e8b5341cf136bf50dc4eea5`.

Silent-failure sweep command: `git grep -n -E 'except|return None|or mgr.get|RiskSeverity.LOW' 71955f077f3da2667e8b5341cf136bf50dc4eea5 -- 'src/worldenergydata/field_development/*.py'`. The matches include exception handlers, absent-data returns, LOW defaults and the known zero-discount fallback; section 6 records confirmed pitfalls. This lexical sweep does not establish that every match is a defect or that unmatched paths are verified; detailed supporting-path review remains U2.

| Symptom | Cause and detection | Incident or follow-up | Observed |
| --- | --- | --- | --- |
| Missing inputs can appear LOW | Hydrate, wax and erosion return LOW plus a note when inputs are unavailable; inspect notes as well as severity; R2 detects the missing-depth policy. [src/worldenergydata/field_development/flow_assurance.py:L201-L206] [src/worldenergydata/field_development/flow_assurance.py:L264-L272] [src/worldenergydata/field_development/flow_assurance.py:L399-L408] | #642; provenance/coverage follow-up: #1323 | 2026-10-15 |
| Explicit zero discount silently becomes the assumption default | `FieldConcept` accepts zero but `estimate_economics` selects with boolean `or`; detection: FD-G2-2 requires returned rate = 0.0 (fraction) for an explicit 0.0 input; the offline diagnostic returns 0.1 at BASE and AFTER, so the criterion FAILS; no dedicated repository regression exists. [src/worldenergydata/field_development/models.py:L162-L168] [src/worldenergydata/field_development/integrations.py:L138-L146] | #1324 | 2026-10-15 |
| Sparse concepts can pass sanity without engineering completeness | Checks run only when dependent fields are populated; graph construction draws one tree when well count is absent or zero; report construction substitutes four wells for a false-valued count; no detection check exists for engineering completeness or rejection of substituted counts. [src/worldenergydata/field_development/sanity.py:L69-L86] [src/worldenergydata/field_development/graph.py:L120-L124] [src/worldenergydata/field_development/fdp_report.py:L204-L215] | #568; coverage follow-up: #1323 | 2026-10-15 |
| Unavailable integration can look like a successful workflow | Imports and queries can return `None`, empty picks or notes; integration tests deliberately accept some degraded results; FD-G1-1 alone does not establish populated economics or installation suitability; no detection check exists that requires populated economics, installation and hardware results. [src/worldenergydata/field_development/integrations.py:L106-L135] [src/worldenergydata/field_development/integrations.py:L179-L206] [tests/modules/field_development/test_integrations.py:L62-L77] | #575; #1323 | 2026-10-15 |
| Calibration fit mistaken for predictive accuracy | Thresholds use the scored catalog; no holdout; no held-out detection check exists; require a held-out evaluation before predictive claims. [docs/domains/field-development/calibration-v2.md:L85-L100] | #640 | 2026-10-15 |
| Erosion threshold presented as verified code compliance | Fixed configured threshold, no mixture-density calculation, edition or clause trace; no licensed-copy detection check exists; review provenance before use. [src/worldenergydata/field_development/flow_assurance.py:L38-L45] | #1322 | 2026-10-15 |

## 7. Lessons log

Append-only initial entry; record ID `initial-pack`; date 2026-10-15; shared-log entry: pending.

Preserve the distinction between a heuristic regression, a closed-form geometry check and independent engineering validation; sections 4–6 record those boundaries. [tests/modules/field_development/test_flow_assurance.py:L5-L9] [tests/modules/field_development/test_layout.py:L26-L37]

## 8. Ownership

Proposed responsibility: calculations quality manager for interim data-pipeline review; deputy: a maintainer-designated independent calculations reviewer; producing role: module documentation contributor; escalation: the maintainer for unresolved provenance, missing reference data or changes to acceptance criteria. Reference: AQG r0, sections 10–11.

## 9. Dependencies and alternative implementations

`FieldConcept` uses Pydantic; JSON loading uses the Python standard library; graph generation and SVG placement use internal types and trigonometry. [src/worldenergydata/field_development/models.py:L31-L62] [src/worldenergydata/field_development/loader.py:L13-L29] [src/worldenergydata/field_development/layout.py:L25-L39] [src/worldenergydata/field_development/layout.py:L126-L155]

Optional enrichment delegates to project_economics for classification/NPV, construction capability data for installation screening and curated subsea components for representative hardware picks; missing dependencies can degrade results. [src/worldenergydata/field_development/integrations.py:L106-L173] [src/worldenergydata/field_development/integrations.py:L179-L251]

Implementation-map inventory (A8 r1): digitalmodel, *Implementation map*, revision `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, `docs/registry/implementation-map.yaml` and its index. This is a digitalmodel artefact with 13 families and 0 worldenergydata implementation rows; the inventory of map implementations for this package is empty, with 0 rows to add. The counted-family grep is `NOT_APPLICABLE`: no map family has an implementation row in this package. Source: digitalmodel, *Implementation map*, cited revision, `repository` and `families` entries.

Map follow-up (U2, #1323): add the following section-3 method families with implementations in this package; they count only from the first map revision that contains such rows. Source: digitalmodel, *Implementation map*, cited revision, `families` inventory.

- Feasibility and weighted ranking, including depth and regional priors. [src/worldenergydata/field_development/recommendation.py:L200-L245] [src/worldenergydata/field_development/recommendation.py:L394-L429] [src/worldenergydata/field_development/recommendation.py:L114-L125] [src/worldenergydata/field_development/basin.py:L146-L163]
- Graph and plan-layout placement. [src/worldenergydata/field_development/graph.py:L160-L196] [src/worldenergydata/field_development/layout.py:L126-L155]
- Hazard-tier screening, including the bulk-velocity erosion screen. [src/worldenergydata/field_development/flow_assurance.py:L169-L183] [src/worldenergydata/field_development/flow_assurance.py:L384-L451]
- DEXPI-aligned XML export. [src/worldenergydata/field_development/dexpi.py:L65-L105]
- Symbol library. [src/worldenergydata/field_development/symbols/__init__.py:L7-L22]
- Calibration backtesting. [src/worldenergydata/field_development/calibration.py:L80-L96]

Repository search record: searched tracked Python under `src/`, `packages/` and `scripts/` for the ranking/temperature/velocity functions, cost assumption keys, depth classifiers, NPV functions and layout methods. The following are distinct routes requiring attention; helpers that call a method are identified as consumers.

| Quantity or route | Implementation relationship and evidence |
| --- | --- |
| Concept scoring versus analog scoring | `recommend` ranks candidate architectures; `find_analogs` weights matches to reference records; these are distinct scores, not interchangeable validation references [src/worldenergydata/field_development/recommendation.py:L394-L429] [src/worldenergydata/field_development/analogs.py:L391-L425] [src/worldenergydata/field_development/analogs.py:L484-L538] |
| Depth classification | `past_projects.classify_water_depth` classifies feet; `water_depth_band_from_ft` converts feet then delegates to the BSEE metre classifier; project_economics classifies a different development-system vocabulary [src/worldenergydata/field_development/past_projects.py:L100-L113] [src/worldenergydata/field_development/well_economics.py:L117-L119] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/cost/models.py:L92-L97] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/config.py:L85-L112] |
| CAPEX estimates | Field-level host plus per-well assumptions in `estimate_economics`; per-concept adjustment in `estimate_per_concept_costs`; separate drilling/SURF/host allocation in the financial reproducer [src/worldenergydata/field_development/integrations.py:L137-L146] [src/worldenergydata/field_development/cost_estimator.py:L224-L292] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L172-L198] |
| Graph placement versus layout search | `compute_positions` draws synthetic rings; `optimize_layout` clusters supplied coordinates with Lloyd iterations and sums jumper/flowline lengths; `naive_layout` calls the same optimizer with one manifold [src/worldenergydata/field_development/layout.py:L65-L136] [src/worldenergydata/field_development/layout_optimization.py:L81-L150] |
| Consumers | `build_fdp_html`, `backtest_fields` and recommendation-grid generation call the ranking method; they are workflow coverage, not independent implementations [src/worldenergydata/field_development/fdp_report.py:L200-L215] [src/worldenergydata/field_development/calibration.py:L80-L96] [src/worldenergydata/field_development/interactive_grid.py:L139-L152] |

Detailed economics implementation parity and the remaining upstream/downstream inventory rows remain within U2, #1323.

## 10. Coverage and open items

### Open items

| Item | Scope, evidence and completion criterion | Responsible role | Tracking |
| --- | --- | --- | --- |
| U1 | Establish standards editions, publication titles, clauses and citation-sidecar applicability; reconcile the fixed erosion heuristic with its stated references without copying licensed values [src/worldenergydata/field_development/flow_assurance.py:L38-L45] [src/worldenergydata/field_development/dexpi.py:L15-L26] [src/worldenergydata/field_development/symbols/__init__.py:L15-L18] | Maintainer | #1322 |
| U2 | Extend method-by-method coverage of catalog publication, analogs/reference data, terrain/bathymetry, economics/norms, optional CAD, launch scripts and consumer adapters; add independent engineering examples, populated-dependency checks and generated QA evidence; retain missing-package/fixture results [src/worldenergydata/field_development/catalog_integration.py:L54-L100] [src/worldenergydata/field_development/fdp_report.py:L200-L246] [tests/modules/field_development/test_integrations.py:L62-L77] | Maintainer | #1323 |
| Defect | Preserve explicit zero discount in `estimate_economics`; add a regression that checks returned zero and undiscounted arithmetic [src/worldenergydata/field_development/integrations.py:L138-L146] [src/worldenergydata/field_development/models.py:L162-L168] | Maintainer | #1324 |
| Calibration | Independent evaluation and non-circular concept discrimination; do not quote in-sample fit as unseen-data accuracy [docs/domains/field-development/calibration-v2.md:L85-L111] | Maintainer | #640 |

### Reading coverage

The main-path citations identify the behavior reviewed; the remaining files below were inventoried and text-read for structure and dependencies, with detailed method coverage tracked by U2.

| Module file | Reading evidence |
| --- | --- |
| `__init__.py` | [src/worldenergydata/field_development/__init__.py:L1-L241] |
| `analogs.py` | [src/worldenergydata/field_development/analogs.py:L1-L538] |
| `analogs_weights.yml` | [src/worldenergydata/field_development/analogs_weights.yml:L1-L36] |
| `assembly_3d.py` | [src/worldenergydata/field_development/assembly_3d.py:L1-L201] |
| `basin.py` | [src/worldenergydata/field_development/basin.py:L1-L163] |
| `bathymetry.py` | [src/worldenergydata/field_development/bathymetry.py:L1-L249] |
| `bathymetry_grid.py` | [src/worldenergydata/field_development/bathymetry_grid.py:L1-L245] |
| `bathymetry_manifest.json` | [src/worldenergydata/field_development/bathymetry_manifest.json:L1-L204] |
| `block.py` | [src/worldenergydata/field_development/block.py:L1-L183] |
| `calibration.py` | [src/worldenergydata/field_development/calibration.py:L1-L121] |
| `catalog_build_common.py` | [src/worldenergydata/field_development/catalog_build_common.py:L1-L104] |
| `catalog_build_crosswalk.py` | [src/worldenergydata/field_development/catalog_build_crosswalk.py:L1-L150] |
| `catalog_build_eligibility.py` | [src/worldenergydata/field_development/catalog_build_eligibility.py:L1-L81] |
| `catalog_build_links.py` | [src/worldenergydata/field_development/catalog_build_links.py:L1-L116] |
| `catalog_build_registry.py` | [src/worldenergydata/field_development/catalog_build_registry.py:L1-L135] |
| `catalog_export.py` | [src/worldenergydata/field_development/catalog_export.py:L1-L154] |
| `catalog_inputs.py` | [src/worldenergydata/field_development/catalog_inputs.py:L1-L182] |
| `catalog_integration.py` | [src/worldenergydata/field_development/catalog_integration.py:L1-L100] |
| `catalog_storage.py` | [src/worldenergydata/field_development/catalog_storage.py:L1-L233] |
| `catalog_validation.py` | [src/worldenergydata/field_development/catalog_validation.py:L1-L209] |
| `catalog_validation_common.py` | [src/worldenergydata/field_development/catalog_validation_common.py:L1-L64] |
| `catalog_validation_crosswalk.py` | [src/worldenergydata/field_development/catalog_validation_crosswalk.py:L1-L164] |
| `catalog_validation_evidence.py` | [src/worldenergydata/field_development/catalog_validation_evidence.py:L1-L159] |
| `catalog_validation_links.py` | [src/worldenergydata/field_development/catalog_validation_links.py:L1-L114] |
| `concept.py` | [src/worldenergydata/field_development/concept.py:L1-L57] |
| `cost_estimator.py` | [src/worldenergydata/field_development/cost_estimator.py:L1-L318] |
| `data_dictionary.md` | [src/worldenergydata/field_development/data_dictionary.md:L1-L102] |
| `decommission_risk.py` | [src/worldenergydata/field_development/decommission_risk.py:L1-L51] |
| `dexpi.py` | [src/worldenergydata/field_development/dexpi.py:L1-L144] |
| `enums.py` | [src/worldenergydata/field_development/enums.py:L1-L90] |
| `equipment_3d.py` | [src/worldenergydata/field_development/equipment_3d.py:L1-L199] |
| `fdp_report.py` | [src/worldenergydata/field_development/fdp_report.py:L1-L246] |
| `flow_assurance.py` | [src/worldenergydata/field_development/flow_assurance.py:L1-L499] |
| `graph.py` | [src/worldenergydata/field_development/graph.py:L1-L196] |
| `host_enrichment.py` | [src/worldenergydata/field_development/host_enrichment.py:L1-L261] |
| `host_text_classifier.py` | [src/worldenergydata/field_development/host_text_classifier.py:L1-L77] |
| `hpht_risk.py` | [src/worldenergydata/field_development/hpht_risk.py:L1-L87] |
| `integrations.py` | [src/worldenergydata/field_development/integrations.py:L1-L283] |
| `interactive_grid.py` | [src/worldenergydata/field_development/interactive_grid.py:L1-L264] |
| `landman.py` | [src/worldenergydata/field_development/landman.py:L1-L81] |
| `layout.py` | [src/worldenergydata/field_development/layout.py:L1-L254] |
| `layout_optimization.py` | [src/worldenergydata/field_development/layout_optimization.py:L1-L150] |
| `llm_completion.py` | [src/worldenergydata/field_development/llm_completion.py:L1-L144] |
| `loader.py` | [src/worldenergydata/field_development/loader.py:L1-L44] |
| `models.py` | [src/worldenergydata/field_development/models.py:L1-L184] |
| `past_projects.py` | [src/worldenergydata/field_development/past_projects.py:L1-L309] |
| `past_projects.yml` | [src/worldenergydata/field_development/past_projects.yml:L1-L220] |
| `phase_norms.py` | [src/worldenergydata/field_development/phase_norms.py:L1-L569] |
| `portfolio_concepts.py` | [src/worldenergydata/field_development/portfolio_concepts.py:L1-L166] |
| `portfolio_matched.py` | [src/worldenergydata/field_development/portfolio_matched.py:L1-L205] |
| `recommendation.py` | [src/worldenergydata/field_development/recommendation.py:L1-L429] |
| `sanity.py` | [src/worldenergydata/field_development/sanity.py:L1-L174] |
| `schema/export_schema.py` | [src/worldenergydata/field_development/schema/export_schema.py:L1-L38] |
| `schema/field_concept.schema.json` | [src/worldenergydata/field_development/schema/field_concept.schema.json:L1-L589] |
| `showcase.py` | [src/worldenergydata/field_development/showcase.py:L1-L344] |
| `subseaiq.py` | [src/worldenergydata/field_development/subseaiq.py:L1-L300] |
| `symbols/__init__.py` | [src/worldenergydata/field_development/symbols/__init__.py:L1-L284] |
| `symbols/compliant_tower.svg` | [src/worldenergydata/field_development/symbols/compliant_tower.svg:L1-L1] |
| `symbols/dry_tree.svg` | [src/worldenergydata/field_development/symbols/dry_tree.svg:L1-L1] |
| `symbols/existing_host.svg` | [src/worldenergydata/field_development/symbols/existing_host.svg:L1-L1] |
| `symbols/export.svg` | [src/worldenergydata/field_development/symbols/export.svg:L1-L1] |
| `symbols/export_symbols.py` | [src/worldenergydata/field_development/symbols/export_symbols.py:L1-L57] |
| `symbols/fixed_jacket.svg` | [src/worldenergydata/field_development/symbols/fixed_jacket.svg:L1-L1] |
| `symbols/flng.svg` | [src/worldenergydata/field_development/symbols/flng.svg:L1-L1] |
| `symbols/fpso.svg` | [src/worldenergydata/field_development/symbols/fpso.svg:L1-L1] |
| `symbols/manifest.json` | [src/worldenergydata/field_development/symbols/manifest.json:L1-L21] |
| `symbols/manifold.svg` | [src/worldenergydata/field_development/symbols/manifold.svg:L1-L1] |
| `symbols/nui.svg` | [src/worldenergydata/field_development/symbols/nui.svg:L1-L1] |
| `symbols/onshore_terminal.svg` | [src/worldenergydata/field_development/symbols/onshore_terminal.svg:L1-L1] |
| `symbols/plet.svg` | [src/worldenergydata/field_development/symbols/plet.svg:L1-L1] |
| `symbols/semisub_fps.svg` | [src/worldenergydata/field_development/symbols/semisub_fps.svg:L1-L1] |
| `symbols/spar.svg` | [src/worldenergydata/field_development/symbols/spar.svg:L1-L1] |
| `symbols/subsea_tree.svg` | [src/worldenergydata/field_development/symbols/subsea_tree.svg:L1-L1] |
| `symbols/tlp.svg` | [src/worldenergydata/field_development/symbols/tlp.svg:L1-L1] |
| `terrain.py` | [src/worldenergydata/field_development/terrain.py:L1-L226] |
| `terrain_sources.yml` | [src/worldenergydata/field_development/terrain_sources.yml:L1-L140] |
| `well_economics.py` | [src/worldenergydata/field_development/well_economics.py:L1-L359] |

| Documentation search hit | Reading evidence; incidental references do not establish module behavior |
| --- | --- |
| `docs/adr/0001-domain-package-split.md` | [docs/adr/0001-domain-package-split.md:L1-L273] |
| `docs/analysis-guides/index.md` | [docs/analysis-guides/index.md:L1-L192] |
| `docs/data-sources/bsee/analysis/well-identifier-grain.md` | [docs/data-sources/bsee/analysis/well-identifier-grain.md:L1-L121] |
| `docs/data-sources/bsee/data/clean_up/data_for_analysis.md` | [docs/data-sources/bsee/data/clean_up/data_for_analysis.md:L1-L171] |
| `docs/data-sources/bsee/data/local_field_development_sources.md` | [docs/data-sources/bsee/data/local_field_development_sources.md:L1-L196] |
| `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md` | [docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md:L1-L155] |
| `docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md` | [docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md:L1-L75] |
| `docs/data-sources/onshore/texas-rrc/field-architecture-portfolio.md` | [docs/data-sources/onshore/texas-rrc/field-architecture-portfolio.md:L1-L104] |
| `docs/data-sources/onshore/texas-rrc/field-atlas-reports.md` | [docs/data-sources/onshore/texas-rrc/field-atlas-reports.md:L1-L57] |
| `docs/data-sources/onshore/texas-rrc/field-development-metrics.md` | [docs/data-sources/onshore/texas-rrc/field-development-metrics.md:L1-L113] |
| `docs/data-sources/onshore/texas-rrc/field-opportunity-ranking.md` | [docs/data-sources/onshore/texas-rrc/field-opportunity-ranking.md:L1-L123] |
| `docs/data-sources/onshore/texas-rrc/infrastructure-access-metrics.md` | [docs/data-sources/onshore/texas-rrc/infrastructure-access-metrics.md:L1-L116] |
| `docs/data-sources/onshore/texas-rrc/production-field-atlas.md` | [docs/data-sources/onshore/texas-rrc/production-field-atlas.md:L1-L80] |
| `docs/data-sources/onshore/texas-rrc/source-catalog.md` | [docs/data-sources/onshore/texas-rrc/source-catalog.md:L1-L54] |
| `docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md` | [docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md:L1-L116] |
| `docs/data-sources/terrain/bathymetry-fetch.md` | [docs/data-sources/terrain/bathymetry-fetch.md:L1-L94] |
| `docs/data-sources/terrain/source-catalog.md` | [docs/data-sources/terrain/source-catalog.md:L1-L66] |
| `docs/domains/field-development/README.md` | [docs/domains/field-development/README.md:L1-L74] |
| `docs/domains/field-development/calibration-v2.md` | [docs/domains/field-development/calibration-v2.md:L1-L111] |
| `docs/domains/field-development/concept-selection-and-ai-cad-briefing.md` | [docs/domains/field-development/concept-selection-and-ai-cad-briefing.md:L1-L338] |
| `docs/modules/cost/research/2026-07-14-contract-award-asset-registry-tranche1.md` | [docs/modules/cost/research/2026-07-14-contract-award-asset-registry-tranche1.md:L1-L179] |
| `docs/modules/cost/research/2026-07-15-e1-project-expansion-research-record.md` | [docs/modules/cost/research/2026-07-15-e1-project-expansion-research-record.md:L1-L154] |
| `docs/modules/cost/research/2026-07-15-e3-award-tranche2-record.md` | [docs/modules/cost/research/2026-07-15-e3-award-tranche2-record.md:L1-L174] |
| `docs/modules/project_economics/country-adapter-checklist.md` | [docs/modules/project_economics/country-adapter-checklist.md:L1-L69] |
| `docs/modules/repository-architecture.md` | [docs/modules/repository-architecture.md:L1-L295] |
| `docs/plans/2026-05-08-issue-394-repo-structure-normalization.md` | [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L1-L220] |
| `docs/plans/2026-06-30-issue-662-texas-rrc-well-lifecycle-spine.md` | [docs/plans/2026-06-30-issue-662-texas-rrc-well-lifecycle-spine.md:L1-L386] |
| `docs/plans/2026-06-30-issue-663-texas-rrc-production-field-atlas.md` | [docs/plans/2026-06-30-issue-663-texas-rrc-production-field-atlas.md:L1-L134] |
| `docs/plans/2026-07-01-issue-664-texas-rrc-field-development-metrics.md` | [docs/plans/2026-07-01-issue-664-texas-rrc-field-development-metrics.md:L1-L408] |
| `docs/plans/2026-07-01-issue-665-texas-rrc-pipeline-gis-infrastructure-access.md` | [docs/plans/2026-07-01-issue-665-texas-rrc-pipeline-gis-infrastructure-access.md:L1-L369] |
| `docs/plans/2026-07-01-issue-666-texas-rrc-onshore-field-atlas-reports.md` | [docs/plans/2026-07-01-issue-666-texas-rrc-onshore-field-atlas-reports.md:L1-L473] |
| `docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md` | [docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md:L1-L493] |
| `docs/plans/2026-07-02-issue-702-texas-rrc-field-architecture-dossiers.md` | [docs/plans/2026-07-02-issue-702-texas-rrc-field-architecture-dossiers.md:L1-L851] |
| `docs/plans/2026-07-02-issue-707-texas-rrc-field-architecture-portfolio.md` | [docs/plans/2026-07-02-issue-707-texas-rrc-field-architecture-portfolio.md:L1-L598] |
| `docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md` | [docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md:L1-L431] |
| `docs/plans/2026-07-04-issue-715-adapter-contract.md` | [docs/plans/2026-07-04-issue-715-adapter-contract.md:L1-L30] |
| `docs/plans/2026-07-04-issue-716-norway-sodir-reference-chain.md` | [docs/plans/2026-07-04-issue-716-norway-sodir-reference-chain.md:L1-L67] |
| `docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md` | [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L1-L290] |
| `docs/plans/2026-07-04-issue-806-spain-live-cores-xlsx.md` | [docs/plans/2026-07-04-issue-806-spain-live-cores-xlsx.md:L1-L252] |
| `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md` | [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L1-L405] |
| `docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md` | [docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md:L1-L508] |
| `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md` | [docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md:L1-L800] |
| `docs/plans/2026-07-06-issue-847-boem-reserves-discovery-ingest.md` | [docs/plans/2026-07-06-issue-847-boem-reserves-discovery-ingest.md:L1-L136] |
| `docs/plans/2026-07-16-issue-1040-required-assets-award-coverage.md` | [docs/plans/2026-07-16-issue-1040-required-assets-award-coverage.md:L1-L108] |
| `docs/plans/2026-07-16-issue-1043-correlated-capex-estimator.md` | [docs/plans/2026-07-16-issue-1043-correlated-capex-estimator.md:L1-L110] |
| `docs/plans/README.md` | [docs/plans/README.md:L1-L117] |
| `docs/reference/petroleum-domain/reserves-classification.md` | [docs/reference/petroleum-domain/reserves-classification.md:L1-L119] |

| Test files in the module directories | Reading evidence |
| --- | --- |
| `tests/modules/field_development/catalog_test_support.py` | [tests/modules/field_development/catalog_test_support.py:L1-L174] |
| `tests/modules/field_development/test_analogs.py` | [tests/modules/field_development/test_analogs.py:L1-L434] |
| `tests/modules/field_development/test_assembly_3d.py` | [tests/modules/field_development/test_assembly_3d.py:L1-L165] |
| `tests/modules/field_development/test_basin.py` | [tests/modules/field_development/test_basin.py:L1-L62] |
| `tests/modules/field_development/test_block.py` | [tests/modules/field_development/test_block.py:L1-L117] |
| `tests/modules/field_development/test_calibration.py` | [tests/modules/field_development/test_calibration.py:L1-L107] |
| `tests/modules/field_development/test_catalog_cli.py` | [tests/modules/field_development/test_catalog_cli.py:L1-L73] |
| `tests/modules/field_development/test_catalog_decision_binding.py` | [tests/modules/field_development/test_catalog_decision_binding.py:L1-L208] |
| `tests/modules/field_development/test_catalog_input_contract.py` | [tests/modules/field_development/test_catalog_input_contract.py:L1-L244] |
| `tests/modules/field_development/test_catalog_integration.py` | [tests/modules/field_development/test_catalog_integration.py:L1-L348] |
| `tests/modules/field_development/test_catalog_integrity.py` | [tests/modules/field_development/test_catalog_integrity.py:L1-L156] |
| `tests/modules/field_development/test_catalog_publication.py` | [tests/modules/field_development/test_catalog_publication.py:L1-L311] |
| `tests/modules/field_development/test_catalog_schema_contract.py` | [tests/modules/field_development/test_catalog_schema_contract.py:L1-L815] |
| `tests/modules/field_development/test_catalog_structure.py` | [tests/modules/field_development/test_catalog_structure.py:L1-L23] |
| `tests/modules/field_development/test_cost_estimator.py` | [tests/modules/field_development/test_cost_estimator.py:L1-L224] |
| `tests/modules/field_development/test_dexpi.py` | [tests/modules/field_development/test_dexpi.py:L1-L116] |
| `tests/modules/field_development/test_equipment_3d.py` | [tests/modules/field_development/test_equipment_3d.py:L1-L96] |
| `tests/modules/field_development/test_fdp_report.py` | [tests/modules/field_development/test_fdp_report.py:L1-L83] |
| `tests/modules/field_development/test_field_concept.py` | [tests/modules/field_development/test_field_concept.py:L1-L197] |
| `tests/modules/field_development/test_flow_assurance.py` | [tests/modules/field_development/test_flow_assurance.py:L1-L260] |
| `tests/modules/field_development/test_graph.py` | [tests/modules/field_development/test_graph.py:L1-L181] |
| `tests/modules/field_development/test_host_enrichment.py` | [tests/modules/field_development/test_host_enrichment.py:L1-L161] |
| `tests/modules/field_development/test_integrations.py` | [tests/modules/field_development/test_integrations.py:L1-L142] |
| `tests/modules/field_development/test_interactive_grid.py` | [tests/modules/field_development/test_interactive_grid.py:L1-L257] |
| `tests/modules/field_development/test_layout.py` | [tests/modules/field_development/test_layout.py:L1-L119] |
| `tests/modules/field_development/test_layout_optimization.py` | [tests/modules/field_development/test_layout_optimization.py:L1-L120] |
| `tests/modules/field_development/test_llm_completion.py` | [tests/modules/field_development/test_llm_completion.py:L1-L114] |
| `tests/modules/field_development/test_past_projects.py` | [tests/modules/field_development/test_past_projects.py:L1-L290] |
| `tests/modules/field_development/test_portfolio_matched.py` | [tests/modules/field_development/test_portfolio_matched.py:L1-L184] |
| `tests/modules/field_development/test_recommendation.py` | [tests/modules/field_development/test_recommendation.py:L1-L221] |
| `tests/modules/field_development/test_showcase.py` | [tests/modules/field_development/test_showcase.py:L1-L104] |
| `tests/modules/field_development/test_subseaiq.py` | [tests/modules/field_development/test_subseaiq.py:L1-L148] |
| `tests/modules/field_development/test_symbols.py` | [tests/modules/field_development/test_symbols.py:L1-L76] |
| `tests/modules/field_development/test_terrain.py` | [tests/modules/field_development/test_terrain.py:L1-L196] |
| `tests/unit/field_development/test_bathymetry.py` | [tests/unit/field_development/test_bathymetry.py:L1-L332] |
| `tests/unit/field_development/test_bathymetry_readers.py` | [tests/unit/field_development/test_bathymetry_readers.py:L1-L270] |
| `tests/unit/field_development/test_concept.py` | [tests/unit/field_development/test_concept.py:L1-L49] |
| `tests/unit/field_development/test_host_text_classifier.py` | [tests/unit/field_development/test_host_text_classifier.py:L1-L71] |
| `tests/unit/field_development/test_landman.py` | [tests/unit/field_development/test_landman.py:L1-L72] |
| `tests/unit/field_development/test_lt_reserves_discovery.py` | [tests/unit/field_development/test_lt_reserves_discovery.py:L1-L264] |
| `tests/unit/field_development/test_phase_norms.py` | [tests/unit/field_development/test_phase_norms.py:L1-L331] |
| `tests/unit/field_development/test_risk_classifiers.py` | [tests/unit/field_development/test_risk_classifiers.py:L1-L89] |
| `tests/unit/field_development/test_well_economics.py` | [tests/unit/field_development/test_well_economics.py:L1-L375] |

Offline run records (2026-10-15): code pin remains `55991b0def0f90708b3e0c396c0f57d9d1b7f7fb`; BASE is `9ef993445433456593fbf854f98cdb10a9a891ce`, whose only difference from the code pin is this pack. AFTER runs use the uncommitted documentation tree on that BASE; no module code or test changes.

| Run scope | BASE passed / failed / skipped | AFTER passed / failed / skipped | NOT_RUN exclusions |
| --- | --- | --- | --- |
| Both module test directories | 578 / 0 / 5 | 578 / 0 / 5 | 5 skip records: 2 collection records and 3 individual test nodes, detailed below |
| Consumer and contract scope listed below | 70 / 0 / 0 | 70 / 0 / 0 | 0 |

Successful test form, identical at BASE and AFTER: `PYTHONPATH=<package source>:<dependency source> uv run --with rasterio --with netCDF4 --no-build-package rasterio --no-build-package netCDF4 python -m pytest --noconftest <scope> -q -rA -p no:cacheprovider --basetemp=<scratch>`; the environment was resolved with ordinary project sources. Repository addopts were retained; HTML/XML/JSON coverage destinations were redirected to scratch with `--cov-report`. No tests or markers were changed. The two real reader nodes now PASS at BASE and AFTER: `tests/unit/field_development/test_bathymetry_readers.py::test_real_tiny_geotiff` and `tests/unit/field_development/test_bathymetry_readers.py::test_real_tiny_netcdf_preserves_directory`. [tests/unit/field_development/test_bathymetry_readers.py:L184-L217] [tests/unit/field_development/test_bathymetry_readers.py:L220-L245]

Dependency attempt at BASE and AFTER: `uv run --extra cad --with rasterio --with netCDF4 --no-build-package cadquery --no-build-package cadquery-ocp --no-build-package vtk --no-build-package rasterio --no-build-package netCDF4 python -m pytest ...` cannot resolve `nlopt==2.10.0`: "can't be installed because it doesn't have a source distribution or wheel for the current platform" (Linux aarch64). No long source build was attempted. An earlier blanket `--no-build` attempt stopped at the git-sourced `assetutilities` package; package-specific binary restrictions allowed that source package to build. The declared `cad` extra requests CadQuery for Python >= 3.11. [pyproject.toml:L178-L184]

### Remaining offline exclusions

| Node or collection | Offline result and reason | Tracking and evidence |
| --- | --- | --- |
| `tests/modules/field_development/test_assembly_3d.py`; `tests/modules/field_development/test_equipment_3d.py` | NOT_RUN: 2 collection skips, `No module named 'cadquery'`; the declared CAD extra cannot install because `nlopt==2.10.0` has no compatible distribution | U2, #1323; [tests/modules/field_development/test_assembly_3d.py:L12-L14] [tests/modules/field_development/test_equipment_3d.py:L12-L14] |
| `tests/unit/field_development/test_lt_reserves_discovery.py::test_bridge_codes_resolve_in_deepqual` | NOT_RUN: `deepqual bin not materialized (LFS stub / CI)`; LFS objects were not fetched for this offline run | U2, #1323; [tests/unit/field_development/test_lt_reserves_discovery.py:L54-L65] |
| `tests/unit/field_development/test_lt_reserves_discovery.py::test_known_answer_real_2023_vintage` | NOT_RUN: `fieldreserves_tables bin not materialized (LFS stub / CI)`; LFS objects were not fetched for this offline run | U2, #1323; [tests/unit/field_development/test_lt_reserves_discovery.py:L252-L264] |
| `tests/modules/field_development/test_terrain.py::test_fetch_dem_live_smoke` | NOT_RUN in offline scope: the test fetches a live DEM endpoint and requires `WED_LIVE_NETWORK_TESTS=1`; network availability and live data are outside a reproducible offline run | U2, #1323; [tests/modules/field_development/test_terrain.py:L187-L196] |

Consumer/contract run scope: `tests/unit/australia/test_field_concept_opt_in.py`, `tests/unit/brazil_anp/test_brazil_field_concept.py`, `tests/unit/brazil_anp/test_reference_chain.py`, `tests/unit/project_economics/adapters/test_field_concept_normalizer.py`, `tests/unit/sodir/test_norway_716.py`, `tests/integration/site/test_architecture_panel.py`, `tests/integration/site/test_public_link_graph.py`, and `tests/contracts`.

### Retained evidence for FD-G5-2

The supplemental review-artifact directory `evidence/` is retained outside the repository: `input-sha256.json` lists one SHA-256 for each of 181 pinned source inputs (all cited files, package files, module tests and the consumer/contract scope); `run-record.json` lists the BASE/AFTER outcomes and SHA-256 for each retained log and diagnostic script. Local-path and source-address headers in retained logs are replaced; result values are unchanged. `pack.sha256` fingerprints the final pack separately to avoid a self-referential digest. These records document the offline checks; they do not supply independent engineering validation or clearance (U2, #1323).

| Retained record | SHA-256 |
| --- | --- |
| `evidence/input-sha256.json` | `53f8196662af80a83d02ed3c0e4a3b6822d9448d88cd452b819fc800bec6c682` |
| `evidence/run-record.json` | `081e67d13e742c25ae885dcfe4959b1ffd49798d1585a37e3d264b6d25ed5cb8` |
