# Pipeline safety module knowledge pack

The module rejects incomplete assessment inputs and invalid geometry before returning a pressure or verdict. Original B31G now includes the sourced long-flaw rule. The modified-shape branch remains a disclosed historical screening variant. Import diagnostics preserve unknown consequences and expose parse errors, source-schema gaps and unit assumptions. These corrections address #1295; they do not qualify field data or establish code compliance.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-16 | Initial module inventory and regression evidence. |
| 1 | 2026-10-16 | Recorded the reviewed silent failures and missing coverage in #1294. |
| 2 | 2026-10-22 | Updated methods, regression nodes and remaining limits after the #1295 corrections. |

| Header | Value |
| --- | --- |
| Module | `pipeline_safety` |
| Package path | `packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety` |
| Analysis family | EC; Python calculations and data normalization |
| Status | DRAFT; independent engineering qualification remains open |
| Evidence basis | Source and tests delivered with this revision; historical review cited separately |

## 1. Purpose and scope

The Excel importer and the CSV assessment route are separate. PHMSA incident rows do not supply measured defect depth, length, wall, strength and MAOP; imported rows must not be assessed by inventing those values. The workflow requires all six numeric fields, while identifier/location aliases remain descriptive defaults. [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L228-L261] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L387-L428]

The engine router accepts CSV input, computes the entire assessment before output, and rejects empty batches. It writes a report, summary and narrative. [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/pipeline_safety.py:L37-L77] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L329-L353]

## 2. Input and output contract

| Object | Units and missing state | Evidence |
| --- | --- | --- |
| Assessment geometry | `depth_pct_wall`: percent wall; length, OD and thickness: mm; SMYS and MAOP: MPa. All required, finite; positive dimensions/strength/MAOP; positive pipe bore. Zero depth is retained. No conversion is implicit. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L108-L129] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L228-L261] |
| Criterion scope | Depth at most 80%, sourced from ORNL (2019), sections 2.1.1–2.1.2. Greater depth raises without a pressure sentinel. Material toughness and defect applicability remain caller qualification. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L108-L129] |
| Result | Pressures in MPa, supplied safety-factor divisor, method and flow-stress basis in notes. Remaining life is unknown without a qualified growth rate. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L38-L48] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L263-L323] |
| Report bundle | CSV includes method, notes and units; summary carries the units schema and flow-stress basis; narrative names the actual method. An empty input writes no bundle. Filesystem errors during later writes are not transactionally rolled back. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/pipeline_safety.py:L37-L77] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L370-L408] |
| Import values | Missing numeric/boolean cells remain unknown; malformed tokens raise and are counted by the import loop. Fractional integer counts raise. Missing columns emit a dedicated warning; `_normalize_row` collects names in output and import statistics. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L171-L181] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L161-L168] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L192-L201] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L230-L237] |
| Consequences | Persons; any absent component makes the total unknown. ORM columns are nullable without zero defaults. Existing historical zero rows cannot be reconstructed automatically. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L218-L227] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/database/models.py:L13-L106] |
| Source units | Diameter, CRS/datum, time zone and currency basis remain unverified and are labelled in `IMPORT_UNIT_ASSUMPTIONS`. BBLS fields retain barrels; gas MCF is an explicit assumption; LNG units are unknown. No source diameter is converted to assessment geometry. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L387-L428] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L603-L631] |

Source-schema and unit metadata are returned by normalization/import statistics; they are not additional persistent database columns. The schema's diameter unit is explicitly unknown. [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/database/models.py:L13-L106] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L680-L723]

## 3. Method and governing references

The opened public source is [ORNL/TM-2019/1192, May 2019, Review of Methods for Determining the Strength of Corroded Natural Gas Pipelines Based on Actual Remaining Wall Thickness](https://www.osti.gov/servlets/purl/1855701). Sections 2.1–2.4 give the derivation and identify the original basis as ASME B31G-1991 (reaffirmed 2004). The licensed standard was not accessed; the former ASME B31G-2012 attribution is not a verified edition comparison.

| Method | Equation basis and scope | Definition |
| --- | --- | --- |
| Original B31G burst pressure | Public report equations 2, 5, 6, 8: flow stress 1.1 SMYS; parabolic area ratio 2d/(3t) and M = sqrt(1 + 0.8z) for z = L²/(Dt) ≤ 20; rectangular reduction 1-d/t for z > 20. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L169-L191] |
| Modified-shape variant | Public report section 2.1.2 and equations 2, 10–11 supply area ratio 0.85d/t and modified M, switching at z = 50. The historical flow stress 0.9 SMYS is preserved from pack revision 1 SF2, **not** the published modified flow stress in section 2.2.2. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L145-L166] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L132-L142] |
| Safe pressure | Burst pressure divided by supplied factor. The default example 1.39 is sourced from section 2.4.1, p. 10 for operating stress at most 0.72 SMYS; universal applicability is not established. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L263-L323] |
| Verdict policy | Replace at the sourced depth boundary or burst pressure below MAOP; repair when safe pressure is below MAOP; otherwise accept as a pressure screen only. The unsourced monitoring threshold is removed; no monitoring interval is inferred. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L194-L212] |
| Remaining life | Not evaluated: the former fixed growth-rate assumption is removed. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/workflow.py:L263-L323] |
| Normalization and persistence | Code-defined era maps, category-prefixed incident key, complete consequence totals and per-file database commit. No engineering formula is implied by these operations. | [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L387-L428] [packages/worldenergydata-pipeline_safety/src/worldenergydata/pipeline_safety/importers/phmsa_importer.py:L288-L385] |

The [worked example](b31g-worked-example.md) compares two flaw lengths with independent hand calculations and documents the old-branch overstatements of 30.8% and 27.8% at z = 40 and 100. Published-modified flow stress is described for comparison, not silently substituted into the compatibility branch.

## 4. Execution evidence

All 369 module cases passed on the uncommitted tree: 179 input cases, 33 criterion cases, 25 import-integrity cases, 58 workflow cases, 69 importer-helper cases and 5 model cases. Ruff passes on every touched Python file using the repository's first-party import grouping. Expected pressure values come from the written hand calculations, never from a call to the implementation. The standalone synthetic example is exercised by `tests/unit/pipeline_safety/test_import_integrity.py::test_synthetic_example_module_runs`; its deepest synthetic flaw now uses the sourced boundary instead of an out-of-scope depth.

Historical probes loaded the reviewed workflow from the code pin recorded in revision 1: the complete reviewer record passed and both blank-cell cases failed the new rejection assertions. Loading BASE instead failed six omitted-field tests and six original-pressure hand checks. BASE already rejects explicit NaN cells; the historical probe establishes the original blank-cell regression separately.

Not exercised: the ten PHMSA workbooks are absent. Synthetic rows now exercise `import_data`, duplicate lookup and persistence (including an in-memory database), but do not validate real workbook mappings, full database ingestion or existing database migrations. The full engine/subprocess integration was not run; the registered CSV bundle was exercised directly through the shipped router with temporary outputs. No licensed program is involved.

## 5. QA gates and regression nodes

| Check | Full test node and acceptance criterion | Basis |
| --- | --- | --- |
| Input rejection | `tests/unit/pipeline_safety/test_input_validation.py::test_blank_csv_numeric_cell_raises`; `tests/unit/pipeline_safety/test_input_validation.py::test_explicit_invalid_numeric_input_raises`; `tests/unit/pipeline_safety/test_input_validation.py::test_omitted_numeric_input_raises`; `tests/unit/pipeline_safety/test_input_validation.py::test_direct_defect_cannot_bypass_validation`: every invalid case raises. | Missing data cannot establish a pressure or verdict (#1295). |
| Reviewer cases | `tests/unit/pipeline_safety/test_input_validation.py::test_reviewer_complete_record_and_blank_cells`: complete record repairs; either blank raises. | Independent hand calculation in docstring and historical review SF1. |
| Original pressure | `tests/unit/pipeline_safety/test_criteria.py::test_original_hand_calculation`: short, exact-boundary and long cases match the independent calculation. | ORNL equations 2, 5, 6, 8. |
| Modified pressure | `tests/unit/pipeline_safety/test_criteria.py::test_modified_variant_hand_calculation`: both modified-M branches and their boundary match the independent calculation. | ORNL equations 2, 10–11; disclosed historical flow stress. |
| Ratio confirmation | `tests/unit/pipeline_safety/test_criteria.py::test_review_ratios_against_confirmed_original`: old/new ratios agree with independent equations. | Original 1991 basis confirmed from public report. |
| Invalid geometry | `tests/unit/pipeline_safety/test_criteria.py::test_invalid_geometry_has_no_pressure_or_verdict`: nonphysical or out-of-scope geometry raises. | Positive dimensions and public depth limit. |
| Parse/schema diagnostics | `tests/unit/pipeline_safety/test_import_integrity.py::test_malformed_is_not_missing`; `tests/unit/pipeline_safety/test_import_integrity.py::test_missing_source_column_is_reported`; `tests/unit/pipeline_safety/test_import_integrity.py::test_import_loop_counts_parse_error_and_reports_schema`: malformed values counted, missing column names and unit assumptions exposed. | #1295 SF4 and SF6. |
| Unknown counts | `tests/unit/pipeline_safety/test_import_integrity.py::test_partial_consequence_sum_is_unknown`; `tests/unit/pipeline_safety/test_import_integrity.py::test_persistence_preserves_unknown_counts`; `tests/unit/pipeline_safety/test_import_integrity.py::test_unknown_consequences_and_units_in_normalized_output`: unknown is distinct from zero through persistence. | #1295 SF5. |
| Output integrity | `tests/unit/pipeline_safety/test_import_integrity.py::test_empty_csv_leaves_no_output_bundle`; `tests/unit/pipeline_safety/test_import_integrity.py::test_summary_cannot_hide_unknown_verdicts`; `tests/unit/pipeline_safety/test_input_validation.py::test_csv_router_rejects_batch_before_writing_outputs`: no partial bundle for empty/invalid input and no dropped unknown verdicts. | #1295 SF8. |
| Method/units | `tests/unit/pipeline_safety/test_criteria.py::test_flow_stress_disclosed_in_report`; `tests/unit/pipeline_safety/test_import_integrity.py::test_registered_example_bundle`: serialized outputs disclose the variant and schema; fixture expectations match. | #1295 SF2/SF7. |

The suite supplies input and algebra regressions. Engineering release still requires qualified measurements, material/temperature applicability, a justified safety factor and a traceable QA evidence record. No signed evidence sidecar or input fingerprint is implemented (#361, #364).

## 6. Known failure modes and remaining limits

| Finding | Current disposition and detection | Remaining limit |
| --- | --- | --- |
| SF1: blank cells previously produced mild verdicts | Corrected; input rejection and reviewer-case nodes in section 5. | No historical assessment is retroactively corrected. |
| SF2: original branch overstated long-flaw pressure | Corrected and independently hand-checked; original and modified M are separate. | Compatibility variant still uses historical flow stress; field applicability and licensed-edition review remain open. |
| SF3: absent geometry silently defaulted | Corrected; all six numeric fields required. Zero depth is preserved; zero dimensions and MAOP rejected. | Descriptive identifier/location aliases, category fallback and fixed `phmsa` source label remain; origin is not authenticated. |
| SF4: parse errors silently became null | Corrected; coercion raises and import loop records errors. | Formatting such as thousands separators and currency symbols is rejected rather than normalized. |
| SF5: unknown consequences became zero | Corrected; complete-component sums and nullable persistence. | Previously stored zero rows require source re-import to distinguish unknowns. |
| SF6: missing source columns were silent | Corrected with warnings and returned column inventory; unknown category/era rejected. | Real workbook schema coverage is not established; optional mappings and alternate-column provenance need review. |
| SF7: unit and growth assumptions undisclosed | Unit schema/assumptions and flow-stress basis emitted; unsupported monitoring/growth assumptions removed. | CSV unit names are a caller contract; source CRS, time, currency, diameter and LNG units remain unqualified. |
| SF8: empty CSV left a partial report | Corrected; empty/invalid input raises before output, unknown verdict labels raise. | Later filesystem failures are not a multi-file atomic transaction. |
| SF9: invalid geometry used a zero-pressure sentinel | Corrected; helpers raise on invalid or out-of-scope geometry. | High-toughness/blunt-corrosion applicability is not established from incident categories. |
| Import completeness | Synthetic import loop is tested. | Missing/read-error files remain logged/skipped without file-error counters; supplemental revision policy, repeated-call counters and per-row SELECT scaling remain open (#431). |
| Release aggregation | Partial component total is now unknown; LNG unit not guessed. | Intentional/unintentional split is still collapsed (#431). |
| Compliance evidence | Sourced equations and hand checks added. | No signed QA evidence, fingerprint, field-data validation, interacting-defect/crack analysis or independent material qualification (#361, #364). |
| Documentation/packaging | Current pack refreshed. | Historical source counts/readiness claims remain unqualified (#349, #364); wheel exclusion of Markdown, documentation indexing and independent reviewer appointment remain open. |

## 7. Lessons log

| Date | Lesson | Evidence |
| --- | --- | --- |
| 2026-10-16 | Synthetic demonstrations and implementation algebra do not establish independent standards validation. | Historical pack revisions 0–1. |
| 2026-10-16 | Import completion needs file coverage and supplemental-update context. | Historical pack revisions 0–1. |
| 2026-10-22 | Test missing states at parsing, direct calculation, aggregation and serialization boundaries. | Section 5 regression nodes. |

## 8. Review responsibility

The maintainer requires an independent calculations review before engineering use. A deputy reviewer, evidence-signature contract and material/temperature applicability review remain to be established. Regression success is not engineering release approval.

## 9. Dependencies and sibling sweep

Dependencies are pandas, SQLAlchemy and the shared core package; the engine also depends on assetutilities. The importer manifest is not a live completeness guarantee. No method-routing registry or independent solver interface is introduced.

Read-only sweep scope: `bsee/pipeline_screening*.py`, `well_bore_design` schemas/hydraulics/decision framework, `analysis/underpressured_screen` and the parallel `safety_analysis.risk_index.data_assembler` loader. Searches covered `fillna`, coercion, missing/finite checks, pressure comparisons and verdict branches; relevant definitions were read in full.

| Sibling | Finding and disposition |
| --- | --- |
| `packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L258-L265`, `L516-L523` | Missing release/consequence values become zero. This can lower assembled risk inputs; no pipeline-pressure verdict is produced here. Follow-up needs a complete risk missing-data contract, so no change is included. |
| `packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/schemas.py:L78-L82`, `L111-L119` | Absent mud-weight window uses zero; an empty pressure profile passes `all(...)` vacuously while its safe-depth fraction is zero. Follow-up requires consistent profile completeness policy. |
| `packages/worldenergydata-well_bore_design/src/worldenergydata/well_bore_design/decision_framework.py:L199-L218` | NaN fracture margin yields incompatible but can fall through to limiting factor `none`; misleading diagnostic, not an affirmative compatibility verdict. Follow-up needs validation across both decision entry points. |
| `src/worldenergydata/analysis/underpressured_screen/screen.py:L68-L83`, `L112-L124` | NaN gradients retain a null tier; no blank-to-normal-tier match found. Infinity is not explicitly rejected; follow-up finite-value audit remains. |
| `packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline_screening_io.py:L21-L42` | Export QA rejects non-finite values and requires null/UNKNOWN provenance agreement. No pressure acceptance verdict is issued by this inventory. |

No sibling code is modified. This bounded read-only sweep does not certify the entire repository.

## 10. Follow-up

- Qualify real source schemas/units and re-import historical consequence data where possible (#364).
- Review the original edition directly and qualify material, temperature, toughness, interacting defects and safety factors before engineering use.
- Decide whether to introduce a separately named published-modified method; the existing variant is explicitly disclosed for compatibility.
- Supply measured corrosion growth and a sourced monitoring policy before returning life or scheduling advice.
- Complete import file-error accounting, supplemental updates, query scaling and release provenance (#431).
- Add output fingerprints and signed QA evidence (#361); establish independent review and documentation indexing; assess Markdown wheel packaging.
- Address sibling unknown-to-zero aggregation and empty/NaN diagnostic findings with their own input contracts and tests.
