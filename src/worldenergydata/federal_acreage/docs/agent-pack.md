# Federal acreage module knowledge pack

| Header | Value |
| --- | --- |
| Module | `federal_acreage` |
| Repository | `worldenergydata` |
| Package | `src/worldenergydata/federal_acreage` |
| Pack revision | 0 |
| Code revision | `dff1a33208ac2eb3771997cb6fffbf762cfd010d` |
| Analysis family | EC; data pipeline; AQG r0 Python calculations gate set |
| Review role | Calculations quality manager; independent provider |
| Status | DRAFT |

## 1. Purpose and scope

`FederalAcreage.router` reads a fixture, validates a tract, evaluates federal-record acreage evidence, writes JSON and HTML, and returns the configuration with output paths. [src/worldenergydata/federal_acreage/federal_acreage.py:L12-L33]

The geometry is a single-section quarter-quarter grid with exactly 40 acres per cell; lots, irregular surveys and multiple sections are excluded. [src/worldenergydata/federal_acreage/evidence.py:L1-L5] [src/worldenergydata/federal_acreage/models.py:L57-L86]

The output is screening evidence; `title_chain_gap` remains `not_evaluated` and explicitly disclaims title-chain evaluation. [src/worldenergydata/federal_acreage/models.py:L149-L170]

The implemented provider is fixture-only; `FederalLandRecordProvider` is a protocol for replacing acquisition, and the router rejects `data.source` other than `fixture`. [src/worldenergydata/federal_acreage/provider.py:L9-L41] [src/worldenergydata/federal_acreage/federal_acreage.py:L14-L23]

The registered workflow declares offline bundled-fixture execution; this is the maturity evidence used here rather than a production-readiness rating. [docs/registry/workflows.yaml:L243-L269]

## 2. Inputs and outputs

### Inputs

| Name | Unit / range | Default | Source and contract |
| --- | --- | --- | --- |
| `TractOfInterest` identifiers and section | Strings; section integer 1–36 | Required | Caller or fixture; no spatial coordinates are present in this contract. [src/worldenergydata/federal_acreage/models.py:L66-L75] |
| `aliquots`, `gross_area_acres` | Nonempty unique quarter-quarter codes; positive acres equal to 40 × cell count | Required | Exactly the combinations of `NE`, `NW`, `SE`, `SW`; exact equality, no tolerance. [src/worldenergydata/federal_acreage/models.py:L10-L10] [src/worldenergydata/federal_acreage/models.py:L57-L86] |
| `FederalLandRecord` | Type `lease`/`parcel`; status `active`/`expired`/`pending`/`unknown`; area nonnegative acres or hectares | Dates and public identity fields default to null; geometry required but nullable | Fixture records; dates reject reversed intervals, while geometry may be an empty list. [src/worldenergydata/federal_acreage/models.py:L89-L119] |
| `SourceRef` | Nonempty ID, dataset, licence note; timezone-aware retrieval datetime; kind `fixture`/`live` | URL null | Provider returns sources; unique nonreserved IDs and record-reference membership are checked by evaluation. [src/worldenergydata/federal_acreage/models.py:L21-L34] [src/worldenergydata/federal_acreage/evidence.py:L118-L154] [src/worldenergydata/federal_acreage/evidence.py:L197-L209] |
| Fixture JSON | UTF-8; schema `federal-acreage-fixture-v1` | No default | `FixtureData.model_validate_json`; all supplied sources must have kind `fixture`; requested section grid must match. [src/worldenergydata/federal_acreage/provider.py:L17-L41] |
| Router configuration | `Analysis.analysis_root_folder`, `Analysis.result_folder`, `data.file`, `data.source` | Tract from fixture if absent; label `federal_acreage_evidence` if absent | Root-relative fixture input; result folder supplied by configuration. [src/worldenergydata/federal_acreage/federal_acreage.py:L14-L28] |

Unknown fields and nonfinite numbers are forbidden by `Contract`; numerical zero is a valid known acreage, while unavailable or ambiguous values require null value/source and a nonempty note. [src/worldenergydata/federal_acreage/models.py:L17-L18] [src/worldenergydata/federal_acreage/models.py:L37-L54]

The grid uses legal-description keys rather than a coordinate reference system; no origin, signed axis or phase is used in intersection arithmetic, which operates on sets of aliquot strings. [src/worldenergydata/federal_acreage/provider.py:L38-L41] [src/worldenergydata/federal_acreage/evidence.py:L72-L80]

### Outputs

| Name | Unit / representation | Provenance / availability |
| --- | --- | --- |
| Five `AcreageRollup` metrics | Acres: gross, record coverage, leased, expired/nonleased, no-record | Each is a `SourcedValue`; no usable coverage makes all five unavailable, including gross area. [src/worldenergydata/federal_acreage/models.py:L141-L146] [src/worldenergydata/federal_acreage/evidence.py:L157-L189] |
| Record evidence and exceptions | Reported unit retained; converted/intersection values acres; optional exception acres | Sorted by serial; missing geometry, no intersection, unit ambiguity, stale status and overlaps are exposed. [src/worldenergydata/federal_acreage/evidence.py:L72-L115] [src/worldenergydata/federal_acreage/evidence.py:L207-L235] |
| `screening_status`, reasons, `data_as_of` | Complete / partial / blocked; string reasons; datetime | Retrieval minimum across sources, without a wall-clock lookup. [src/worldenergydata/federal_acreage/evidence.py:L128-L132] [src/worldenergydata/federal_acreage/evidence.py:L238-L276] |
| JSON twin | UTF-8; `federal-acreage-result-v1`; full precision model values | `<label>_result.json`; final newline. [src/worldenergydata/federal_acreage/models.py:L160-L172] [src/worldenergydata/federal_acreage/report.py:L158-L173] |
| HTML report | UTF-8; acreage text and bar widths to three decimal places | `<label>_report.html`; input echo, exceptions, title gap and provenance; escaped text. [src/worldenergydata/federal_acreage/report.py:L21-L34] [src/worldenergydata/federal_acreage/report.py:L48-L67] [src/worldenergydata/federal_acreage/report.py:L108-L173] |

## 3. Method and governing standards

| Method | Implementation and basis |
| --- | --- |
| Input schema | `valid_aliquots`, `TractOfInterest.validate_gross`, `FederalLandRecord.validate_date_interval`; explicit contract rules, rather than a cited surveying standard. [src/worldenergydata/federal_acreage/models.py:L57-L119] |
| Area conversion and consistency | `_inspect_record` multiplies hectares by `HECTARES_TO_ACRES = 2.4710538147`, otherwise by 1; `_check_area` marks differences greater than 0.5 acres from 40 × record-cell count ambiguous. [src/worldenergydata/federal_acreage/evidence.py:L22-L22] [src/worldenergydata/federal_acreage/evidence.py:L50-L80] |
| Intersection and overlap | Intersection is tract ∩ record cells; coverage is a set union; pairwise overlap emits 40 × shared-cell count acres. [src/worldenergydata/federal_acreage/evidence.py:L79-L97] [src/worldenergydata/federal_acreage/evidence.py:L202-L235] |
| Status resolution | `_stale_status` checks pending/unknown, active dates inconsistent with retrieval date, and expired dates at or after retrieval; unresolved records prevent a definite lease split. [src/worldenergydata/federal_acreage/evidence.py:L36-L47] [src/worldenergydata/federal_acreage/evidence.py:L98-L108] [src/worldenergydata/federal_acreage/evidence.py:L184-L188] |
| Lease split | Unresolved records are excluded from both buckets; otherwise active leases enter leased and every other record enters nonleased; intersecting buckets make both split outputs ambiguous. [src/worldenergydata/federal_acreage/evidence.py:L218-L224] [src/worldenergydata/federal_acreage/evidence.py:L184-L189] |
| Rollup and status | Acreage equals 40 × union cardinality; no-record acreage is gross minus coverage with a derived source; no coverage blocks, exceptions or uncovered acreage make partial, otherwise complete. [src/worldenergydata/federal_acreage/evidence.py:L157-L189] [src/worldenergydata/federal_acreage/evidence.py:L247-L276] |
| Provenance | `_provenance` sorts sources, takes the earliest retrieval, propagates fixture kind if any source is a fixture, and creates a combined source for multiple references. [src/worldenergydata/federal_acreage/evidence.py:L118-L154] |
| Export | `write_outputs` validates a filename slug and writes JSON followed by HTML from the same result; `render_html` escapes user text and appends sources and a title disclaimer. [src/worldenergydata/federal_acreage/report.py:L21-L45] [src/worldenergydata/federal_acreage/report.py:L108-L173] |

UNVERIFIED: an external authority for the hectare factor and the choice of 0.5-acre tolerance has not been established; both are implementation constants, not a verified surveying basis; issue pending (1). [src/worldenergydata/federal_acreage/evidence.py:L22-L22] [src/worldenergydata/federal_acreage/evidence.py:L58-L68]

No governing licensed standard or calculation-citation sidecar is declared by these methods; source references describe dataset provenance and do not authenticate the conversion constant. [src/worldenergydata/federal_acreage/evidence.py:L22-L23] [src/worldenergydata/federal_acreage/evidence.py:L118-L154] [src/worldenergydata/federal_acreage/models.py:L21-L34]

## 4. Validated worked examples and regression examples

The two validated cases below validate closed-form set arithmetic on the declared synthetic grid; they do not validate real survey geometry or live lease status. [examples/workflows/federal-acreage-evidence/fixture_records.json:L11-L21] [src/worldenergydata/federal_acreage/evidence.py:L1-L5]

All listed nodes ran offline at the header code revision: BASE and AFTER results are recorded per row; `tests/unit/federal_acreage/fixture_paths.py` locates the fixture independently of the working directory. [tests/unit/federal_acreage/fixture_paths.py:L3-L8]

| Case / class | Independent basis or regression basis | Input / expected / tolerance | Existing test node ID | BASE / AFTER |
| --- | --- | --- | --- | --- |
| V1 union and overlap; validated | Closed-form enumeration: eight tract cells; seven distinct covered cells; five active-lease cells; two expired cells; one repeated covered cell; multiply cardinalities by the declared 40 acres per cell. [examples/workflows/federal-acreage-evidence/fixture_records.json:L11-L21] [examples/workflows/federal-acreage-evidence/fixture_records.json:L24-L124] | Dataset `fixture-mlrs-synthetic`, fixture at code pin; gross 320, coverage 280, leased 200, nonleased 80, overlap 40 acres; exact integer arithmetic, tolerance 0 acres. [tests/unit/federal_acreage/test_evidence.py:L28-L38] | `tests/unit/federal_acreage/test_evidence.py::test_pilot_union_overlap_and_buckets` | PASS / PASS |
| V2 partial intersection; validated | Closed form: of two supplied record cells only one belongs to the eight-cell tract; intersection 1 × 40 and uncovered (8 − 1) × 40 acres. [examples/workflows/federal-acreage-evidence/fixture_records.json:L11-L21] [tests/unit/federal_acreage/test_evidence.py:L41-L44] | Input constructed in test; intersection 40, no-record 280 acres; tolerance 0 acres. [tests/unit/federal_acreage/test_evidence.py:L41-L44] | `tests/unit/federal_acreage/test_evidence.py::test_partial_intersection` | PASS / PASS |
| R1 hectare conversion; regression | Fixture expectation without an independently cited conversion authority. [tests/unit/federal_acreage/test_evidence.py:L59-L62] | 16.1874 hectares → approximately 40 acres; absolute tolerance 0.001 acres, as encoded by the test; no exception expected. [tests/unit/federal_acreage/test_evidence.py:L59-L62] | `tests/unit/federal_acreage/test_evidence.py::test_hectares_conversion` | PASS / PASS |
| R2 contract serialization; regression | Literal expected schema, metrics and sources, followed by model round trip. [tests/unit/federal_acreage/test_models.py:L36-L69] | Gross / coverage / leased / nonleased / no-record = 320 / 280 / 200 / 80 / 40 acres; exact equality, tolerance 0 acres. [tests/unit/federal_acreage/test_models.py:L43-L69] | `tests/unit/federal_acreage/test_models.py::test_schema_shape_round_trip` | PASS / PASS |
| R3 committed output identity; regression | Committed output bytes are generated snapshots, not independent acreage references. [tests/unit/federal_acreage/test_report.py:L100-L106] | Fixture and outputs under `examples/workflows/federal-acreage-evidence/`; regenerated JSON and HTML must differ by 0 bytes. [tests/unit/federal_acreage/test_report.py:L100-L106] | `tests/unit/federal_acreage/test_report.py::test_committed_outputs_match_fresh_render` | PASS / PASS |

## 5. QA gates and executable checks

Gate applicability follows AQG r0 §10, Python calculations, with G5 required by §9; the checks below are local pack checks rather than a signed clearance record (AQG r0 §11).

| Gate | Applicability | Module-specific route |
| --- | --- | --- |
| G0 | Applicable: inputs, units, provenance | G0-1 to G0-3 |
| G1 | Applicable: imports and tests | G1-1 and G1-2; Python API and CLI, no external solver format. [tests/unit/federal_acreage/test_provider.py:L40-L53] [tests/workflows/test_durable_workflows.py:L147-L162] |
| G2 | Applicable: independent hand check | G2-1 and G2-2 are closed-form checks; G2-3 to G2-5 are supporting regression checks. [tests/unit/federal_acreage/test_evidence.py:L28-L113] |
| G3 | NOT_APPLICABLE | No dynamic model; the evaluator performs set operations on records. [src/worldenergydata/federal_acreage/evidence.py:L192-L276] |
| G4 | NOT_APPLICABLE | No diffraction or mesh output; outputs are JSON and HTML. [src/worldenergydata/federal_acreage/report.py:L158-L173] |
| G5 | Applicable: evidence appendix | G5-1 to G5-3 check the twins and provenance; signed gate records and input fingerprints remain an open coverage item, issue pending (4). [src/worldenergydata/federal_acreage/report.py:L108-L173] |

Run the existing nodes named in each row through `uv run --extra test python -m pytest --noconftest <nodes> -q -rA -p no:cacheprovider --basetemp=<scratch>`; keep coverage output in scratch and use the same source revision for comparisons. [pyproject.toml:L142-L147] [AGENTS.md:L4-L4]

| Check | Function / quantity / numeric pass criterion and unit | Executable evidence; result |
| --- | --- | --- |
| G0-1 | `TractOfInterest` rejects gross 319 acres and invalid cell codes; `FederalLandRecord` rejects reversed dates: 0 unexpectedly accepted cases. | `tests/unit/federal_acreage/test_models.py::test_tract_validation`; `tests/unit/federal_acreage/test_models.py::test_reversed_lease_dates_rejected`; PASS. [tests/unit/federal_acreage/test_models.py:L12-L21] [tests/unit/federal_acreage/test_models.py:L72-L85] |
| G0-2 | `SourcedValue` keeps unavailable/ambiguous values null and rejects unsupported known values: 0 accepted invalid marker states. | `tests/unit/federal_acreage/test_models.py::test_marker_states[unavailable]`; `tests/unit/federal_acreage/test_models.py::test_marker_states[ambiguous]`; PASS. [tests/unit/federal_acreage/test_models.py:L24-L33] |
| G0-3 | `FixtureRecordProvider` reads 6 records, fixture kind, and rejects a wrong schema: 0 count difference (records), 0 invalid-schema acceptances. | `tests/unit/federal_acreage/test_provider.py::test_fixture_and_version`; PASS. [tests/unit/federal_acreage/test_provider.py:L12-L22] |
| G1-1 | Import and execute the 25 module nodes and 2 workflow nodes: 27 passed, 0 failed, 0 skipped, 0 NOT_RUN (tests). | Full suite command below; BASE/AFTER PASS. [tests/unit/federal_acreage/test_evidence.py:L28-L113] [tests/unit/federal_acreage/test_models.py:L12-L85] [tests/unit/federal_acreage/test_provider.py:L12-L62] [tests/unit/federal_acreage/test_report.py:L59-L106] [tests/workflows/test_durable_workflows.py:L126-L162] |
| G1-2 | `FederalAcreage.router` returns completed and rejects live input; engine/CLI produce registered outputs: 0 assertion failures, CLI exit code 0. | `tests/unit/federal_acreage/test_provider.py::test_router`; `tests/workflows/test_durable_workflows.py::test_registry_workflow_outputs[federal-acreage-evidence]`; `tests/workflows/test_durable_workflows.py::test_module_yaml_invocation_exits_zero[federal-acreage-evidence]`; PASS. [tests/unit/federal_acreage/test_provider.py:L40-L53] [tests/workflows/test_durable_workflows.py:L126-L162] |
| G2-1 | `evaluate` union, lease split and overlap equal V1: absolute error 0 acres; exactly 3 exception kinds. | V1 node; PASS. [tests/unit/federal_acreage/test_evidence.py:L28-L38] |
| G2-2 | `evaluate` intersection and complement equal V2: absolute error 0 acres. | V2 node; PASS. [tests/unit/federal_acreage/test_evidence.py:L41-L44] |
| G2-3 | `_inspect_record` hectare regression equals 40 acres within 0.001 acres and 0 exceptions; independent conversion authority remains open. | R1 node; PASS as regression only. [tests/unit/federal_acreage/test_evidence.py:L59-L62] |
| G2-4 | `evaluate` missing geometry/nonintersection, unit ambiguity, unknown/pending status, expired active record and empty records: 0 wrong status assertions; empty records yield 5 unavailable metrics. | `tests/unit/federal_acreage/test_evidence.py::test_non_intersecting`; `tests/unit/federal_acreage/test_evidence.py::test_missing_geometry`; `tests/unit/federal_acreage/test_evidence.py::test_unit_ambiguous`; `tests/unit/federal_acreage/test_evidence.py::test_stale_status[unknown]`; `tests/unit/federal_acreage/test_evidence.py::test_stale_status[pending]`; `tests/unit/federal_acreage/test_evidence.py::test_expired_by_data_date`; `tests/unit/federal_acreage/test_evidence.py::test_empty_records_blocked`; PASS. [tests/unit/federal_acreage/test_evidence.py:L47-L89] |
| G2-5 | `evaluate` full coverage has no-record 0 acres; default fixture has 40 derived no-record acres and the expected source: absolute error 0 acres, 0 provenance assertion failures. | `tests/unit/federal_acreage/test_evidence.py::test_clean_full_coverage_and_determinism`; `tests/unit/federal_acreage/test_evidence.py::test_no_record_area_is_explicitly_derived`; PASS. [tests/unit/federal_acreage/test_evidence.py:L92-L113] |
| G5-1 | `write_outputs` JSON equals result; HTML table record count equals result count; unavailable rendering has 0 literal `None` cells; repeat writes differ by 0 bytes. | `tests/unit/federal_acreage/test_report.py::test_report_contract_and_determinism`; `tests/unit/federal_acreage/test_report.py::test_report_ambiguity_and_missing_values[100]`; `tests/unit/federal_acreage/test_report.py::test_report_ambiguity_and_missing_values[160]`; PASS. [tests/unit/federal_acreage/test_report.py:L42-L98] |
| G5-2 | Fresh output twins differ from committed snapshots by 0 bytes; round-trip schema differs in 0 fields. | R3 and R2 nodes; PASS. [tests/unit/federal_acreage/test_report.py:L100-L106] [tests/unit/federal_acreage/test_models.py:L36-L69] |
| G5-3 | Provider seam retains leased 200 acres, removes the fixture banner for all-live sources, and retains the fixture licence note: 0 failed assertions. | `tests/unit/federal_acreage/test_provider.py::test_live_provider_seam`; `tests/unit/federal_acreage/test_provider.py::test_fixture_uses_repository_licence`; PASS. [tests/unit/federal_acreage/test_provider.py:L25-L37] [tests/unit/federal_acreage/test_provider.py:L56-L62] |

Execution record: code pin `dff1a33208ac2eb3771997cb6fffbf762cfd010d`, BASE 27 passed / 0 failed / 0 skipped / 0 NOT_RUN; AFTER 27 passed / 0 failed / 0 skipped / 0 NOT_RUN; serial execution with the declared `test` extra and the AGENTS `--noconftest` form, no addopts override; coverage output destinations supplied on the command line. [AGENTS.md:L4-L4] [pyproject.toml:L142-L147]

Full suite arguments: `tests/unit/federal_acreage`, `tests/workflows/test_durable_workflows.py::test_registry_workflow_outputs[federal-acreage-evidence]`, and `tests/workflows/test_durable_workflows.py::test_module_yaml_invocation_exits_zero[federal-acreage-evidence]`; both workflow tests copy inputs and write results under pytest temporary storage. [tests/workflows/test_durable_workflows.py:L111-L162]

## 6. Known failure modes and silent-failure sweep

sweep: 35 found

The count is 35 reviewed behavior sites below, including deliberate sentinels and repeated unit assumptions; it is not a count of confirmed defects or raw textual matches. [src/worldenergydata/federal_acreage/models.py:L21-L172] [src/worldenergydata/federal_acreage/evidence.py:L22-L276] [src/worldenergydata/federal_acreage/report.py:L21-L173] [src/worldenergydata/federal_acreage/federal_acreage.py:L14-L33]

Exact package sweep commands (Python files only):

```sh
rg -n 'except|\bcontinue\b|return None|return \[\]|return \{\}|=\s*0(\.0)?\b|1970|0\.05|\b(int|float)\(' src/worldenergydata/federal_acreage --glob '*.py'
rg -n 'None|or \[\]|else|\.get\(|40|0\.5|HECTARES|unit|cache|write_text|\[\]|\{\}' src/worldenergydata/federal_acreage --glob '*.py'
```

No swallowed `except`, record-skipping `continue`, external-text `int()`/`float()` call, empty error return, zero/year/percentage fallback default or cache write exists in the package; `Field(ge=0)` is an acceptance bound, and initialized collections accumulate results rather than absorb an error. [src/worldenergydata/federal_acreage/models.py:L17-L172] [src/worldenergydata/federal_acreage/evidence.py:L26-L276] [src/worldenergydata/federal_acreage/provider.py:L24-L41] [src/worldenergydata/federal_acreage/report.py:L21-L173] [src/worldenergydata/federal_acreage/federal_acreage.py:L12-L33]

Review date: 2026-10-18; issue #925 is the fixture-workflow context, #913 the acquisition gap, and #914 the separate title-chain gap; the rows with no existing detection identify a numbered draft.

| Site | Symptom / cause at the pin | Existing detection / tracking |
| --- | --- | --- |
| S01 | Fixed hectare conversion coefficient has no cited unit authority. [src/worldenergydata/federal_acreage/evidence.py:L22-L22] | G2-3 checks regression, not authority; issue pending (1). |
| S02 | Area disagreement only above 0.5 acres sets ambiguity; boundary and tolerance basis are untested. [src/worldenergydata/federal_acreage/evidence.py:L58-L68] | G2-4 detects a large mismatch; no detection check exists for the boundary; issue pending (1). |
| S03 | Acres bypass conversion with multiplier 1; unknown units are rejected by the model. [src/worldenergydata/federal_acreage/evidence.py:L76-L78] [src/worldenergydata/federal_acreage/models.py:L89-L91] | G2-1/G2-3 exercise accepted units; no detection check exists for invalid-unit rejection; issue pending (3). |
| S04 | `record.aliquots or []` turns null and empty geometry into empty intersection. [src/worldenergydata/federal_acreage/evidence.py:L79-L80] | G2-4 checks null geometry; no detection check exists for empty-list distinction; issue pending (3). |
| S05 | Intersection cardinality × 40 creates a known zero for disjoint geometry. [src/worldenergydata/federal_acreage/evidence.py:L80-L80] | G2-2/G2-4; #925. |
| S06 | Null geometry overwrites intersection with an unavailable marker and emits an exception. [src/worldenergydata/federal_acreage/evidence.py:L82-L97] | G2-4; #925. |
| S07 | Disjoint supplied geometry emits `non_intersecting`; zero coverage later blocks. [src/worldenergydata/federal_acreage/evidence.py:L88-L97] [src/worldenergydata/federal_acreage/evidence.py:L259-L260] | G2-4; #925. |
| S08 | Missing effective/expiration dates bypass date comparisons; an active or expired record can be accepted without dated status support. [src/worldenergydata/federal_acreage/evidence.py:L36-L47] | G2-4 detects supplied stale dates; no detection check exists for missing-date uncertainty; issue pending (3). |
| S09 | Pending/unknown or date-conflicting status makes the split uncertain. [src/worldenergydata/federal_acreage/evidence.py:L98-L108] | G2-4; no detection check exists for future-effective active or future-expiring expired branches; issue pending (3). |
| S10 | Minimum retrieval is a data date, without a freshness-age check against current time. [src/worldenergydata/federal_acreage/evidence.py:L128-L132] [src/worldenergydata/federal_acreage/evidence.py:L241-L245] | no detection check exists for stale source age; #913. |
| S11 | Any fixture source makes aggregate provenance fixture; mixed kinds and multiple-source rollup are not covered by the seam test. [src/worldenergydata/federal_acreage/evidence.py:L130-L154] | G5-3 checks all-live only; no detection check exists for mixed or multiple-source cases; issue pending (3). |
| S12 | No coverage makes all five metrics unavailable, even known tract gross. [src/worldenergydata/federal_acreage/evidence.py:L165-L168] | G2-4 asserts all markers; #925. |
| S13 | Coverage union cardinality is multiplied by 40 acres. [src/worldenergydata/federal_acreage/evidence.py:L171-L171] | G2-1, tolerance 0 acres; #925. |
| S14 | Leased union cardinality is multiplied by 40 acres. [src/worldenergydata/federal_acreage/evidence.py:L172-L172] | G2-1, tolerance 0 acres; #925. |
| S15 | Nonleased union cardinality is multiplied by 40 acres. [src/worldenergydata/federal_acreage/evidence.py:L173-L173] | G2-1, tolerance 0 acres; #925. |
| S16 | No-record acreage subtracts 40 × coverage count, including a genuine zero for full coverage. [src/worldenergydata/federal_acreage/evidence.py:L174-L182] | G2-5; #925. |
| S17 | Uncertain or overlapping lease/nonlease buckets replace both totals with ambiguous markers. [src/worldenergydata/federal_acreage/evidence.py:L184-L188] | G2-4 tests uncertainty; no detection check exists for conflicting-bucket overlap; issue pending (3). |
| S18 | Every resolved record other than an active lease goes to the nonleased bucket, including active parcels. [src/worldenergydata/federal_acreage/evidence.py:L218-L224] | G2-1 checks expired leases; no detection check exists for an intersecting active parcel; issue pending (3). |
| S19 | Pairwise overlap acreage assumes 40 acres per shared cell; coverage counts the union once. [src/worldenergydata/federal_acreage/evidence.py:L225-L234] | G2-1, tolerance 0 acres; #925. |
| S20 | A falsy numeric no-record value is treated as complete if exceptions are absent; this relies on nonnegative known acreage. [src/worldenergydata/federal_acreage/evidence.py:L257-L266] [src/worldenergydata/federal_acreage/models.py:L43-L54] | G2-5 checks exact zero; #925. |
| S21 | Null record geometry passes through `validate_aliquots` as null rather than an error. [src/worldenergydata/federal_acreage/models.py:L106-L109] | G2-4, unavailable geometry marker; #925. |
| S22 | `effective_date` defaults to null; missing lower date bound is accepted. [src/worldenergydata/federal_acreage/models.py:L98-L98] | no detection check exists for a required-date policy; issue pending (3). |
| S23 | `expiration_date` defaults to null; missing upper date bound is accepted. [src/worldenergydata/federal_acreage/models.py:L99-L99] | no detection check exists for a required-date policy; issue pending (3). |
| S24 | `public_lessee` defaults to null; absence is not identity evidence. [src/worldenergydata/federal_acreage/models.py:L101-L101] | G5-1 tests readable missing cells; #925. |
| S25 | `public_operator` defaults to null; absence is not operator evidence. [src/worldenergydata/federal_acreage/models.py:L102-L102] | G5-1 tests readable missing cells; #925. |
| S26 | `SourceRef.url` defaults to null and imposes no locator format validation. [src/worldenergydata/federal_acreage/models.py:L21-L34] | G5-3 checks licence text, not locator quality; no detection check exists for source-locator completeness; #913. |
| S27 | `SourcedValue.note` defaults to null for available values, while unavailable values require a note. [src/worldenergydata/federal_acreage/models.py:L37-L54] | G0-2/G2-5; #925. |
| S28 | `AcreageException.acres` defaults to null for exceptions without computed area. [src/worldenergydata/federal_acreage/models.py:L128-L138] | G5-1 checks missing display cells; #925. |
| S29 | `text(None)` displays `not stated`, rather than numerical zero. [src/worldenergydata/federal_acreage/report.py:L21-L28] | G5-1; #925. |
| S30 | `_sourced_area` preserves unknown markers; bars omit null quantities and otherwise divide by positive tract gross. [src/worldenergydata/federal_acreage/report.py:L31-L34] [src/worldenergydata/federal_acreage/report.py:L48-L67] | G5-1 checks missing values; no detection check exists for omitted-bar count; issue pending (3). |
| S31 | Fixture banner becomes an empty string for all-live source references. [src/worldenergydata/federal_acreage/report.py:L108-L113] | G5-3; #925. |
| S32 | Router silently selects fixture tract if configuration omits `tract`. [src/worldenergydata/federal_acreage/federal_acreage.py:L18-L22] | G1-2 tests fallback; no detection check exists for an explicit tract on another grid; issue pending (3). |
| S33 | Router defaults the output label when metadata omits it; an existing empty label is rejected by the exporter. [src/worldenergydata/federal_acreage/federal_acreage.py:L24-L28] [src/worldenergydata/federal_acreage/report.py:L161-L162] | no detection check exists for omitted/invalid label branches; issue pending (3). |
| S34 | Tract gross must exactly equal 40 acres per cell; HTML repeats that geometry assumption. [src/worldenergydata/federal_acreage/models.py:L82-L86] [src/worldenergydata/federal_acreage/report.py:L150-L153] | G0-1 checks mismatch; #925. |
| S35 | Output writes are sequential and overwrite existing paths; an HTML write error can leave the JSON twin without a corresponding new report. [src/worldenergydata/federal_acreage/report.py:L163-L173] | G5-1 checks successful repeat writes; no detection check exists for partial export on I/O failure; issue pending (5). |

Additional guard coverage: `evaluate` raises for empty/duplicate/reserved source IDs, duplicate serials and unknown source references; the shipped tests do not assert these rejection branches, so no detection check exists for their regression; issue pending (3). [src/worldenergydata/federal_acreage/evidence.py:L121-L127] [src/worldenergydata/federal_acreage/evidence.py:L197-L209]

## 7. Lessons log

| Date | Entry ID | Lesson and evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-18 | FA-001 | Synthetic grid arithmetic and byte-identical exports establish different kinds of evidence; snapshot identity does not independently validate acreage. [tests/unit/federal_acreage/test_evidence.py:L28-L44] [tests/unit/federal_acreage/test_report.py:L100-L106] | Section 4 separates closed-form checks from regression cases. | Not assigned; issue pending (4). |
| 2026-10-18 | FA-002 | Known zero and missing evidence require different representations; blocked evidence makes every rollup metric unavailable. [src/worldenergydata/federal_acreage/evidence.py:L165-L188] [tests/unit/federal_acreage/test_evidence.py:L84-L98] | Sections 2, 5 and 6 retain the marker and zero distinction. | Not assigned; issue pending (4). |

## 8. Ownership

Required review role: calculations quality manager, using the Python calculations gate set for this data pipeline; deputy review role: alternate calculations quality manager; independent-provider clearance is required (AQG r0 §§10–11).

Required producing role: module maintainer or contributing implementation agent; unresolved unit basis, status policy or gate evidence is referred to the calculations quality manager; cross-family scope is referred to the maintainers (AQG r0 §11).

UNVERIFIED: appointment of a deputy, a signed clearance record and a shared-log identifier are not evidenced by the module's output contract; issue pending (4). [src/worldenergydata/federal_acreage/models.py:L160-L172]

## 9. Dependencies and implementation inventory

| Dependency / direction | Observed boundary |
| --- | --- |
| Pydantic / upstream | `BaseModel`, fields and validators implement the input and result contracts; the root dependency constraint is Pydantic 2.13.4 or later below 3. [src/worldenergydata/federal_acreage/models.py:L8-L18] [pyproject.toml:L95-L96] |
| Fixture / upstream | Dataset ID `fixture-mlrs-synthetic`, schema `federal-acreage-fixture-v1`, six synthetic records, retrieval date and licence note are embedded in the example. [examples/workflows/federal-acreage-evidence/fixture_records.json:L2-L2] [examples/workflows/federal-acreage-evidence/fixture_records.json:L23-L135] [tests/unit/federal_acreage/test_provider.py:L12-L16] |
| Configuration / upstream | Example input selects fixture source and tract; base configuration sets the basename and overwrite behavior. [examples/workflows/federal-acreage-evidence/input.yml:L1-L23] [src/worldenergydata/base_configs/modules/federal_acreage/federal_acreage.yml:L1-L7] |
| Engine / caller | Engine dispatch imports `FederalAcreage` for its basename and calls the router. [src/worldenergydata/engine.py:L177-L181] |
| Export / downstream | `write_outputs` consumes the result contract; registered workflow assertions inspect its JSON and expect the HTML twin. [src/worldenergydata/federal_acreage/report.py:L158-L173] [docs/registry/workflows.yaml:L243-L269] |
| Live acquisition / future | Provider protocol and fixture adapter form the replacement boundary; live-source work remains #913. [src/worldenergydata/federal_acreage/provider.py:L1-L41] |

Implementation-map audit source: `digitalmodel`, `docs/registry/implementation-map.yaml`, data revision `3256bab95f84da3d9fadce8d5dcf8458d66d1eb4` on `codex/implmap-work`, `families` inventory: 13 families, 0 implementation rows under `src/worldenergydata/federal_acreage/`, hence 0 module map families (implementation map, cited data revision, `families[*].implementations[*].path`).

Inventory of map families for this package: empty; counted families: 0; prescribed signal grep: `NOT_APPLICABLE` because no family has an in-package implementation row; A8 inventory passes with no counted grep (implementation map, cited data revision, `families[*].implementations[*].path`).

Map follow-up: add the method families represented by section 3—input-contract validation, hectare conversion and consistency, quarter-quarter intersection/union and overlap, dated lease-status partitioning, sourced rollup/provenance, and result export; issue pending (2). [src/worldenergydata/federal_acreage/models.py:L57-L119] [src/worldenergydata/federal_acreage/evidence.py:L36-L276] [src/worldenergydata/federal_acreage/report.py:L108-L173]

Additional repository search, including `scripts/`, used `rg -n 'acreage|aliquot|HECTARES_TO_ACRES|federal-record-rollup' --glob '*.py' .`; related definitions found outside the package are listed below as findings, without changing the empty counted-family result. [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L407-L434] [src/worldenergydata/engine.py:L177-L181]

| Definition | Classification / reason |
| --- | --- |
| `evidence._check_area`, `_inspect_record`, `_stale_status`, `_rollup`, `_summarize_records`, `_provenance`, `evaluate` | In-package calculation and aggregation inventory; all are described in section 3. [src/worldenergydata/federal_acreage/evidence.py:L36-L276] |
| `models.valid_aliquots`, `TractOfInterest.validate_gross`, `FederalLandRecord.validate_date_interval` | In-package criteria; all are described in section 3. [src/worldenergydata/federal_acreage/models.py:L57-L119] |
| `FederalAcreage.router`, `FixtureRecordProvider.records_for_tract` | Routing and data-provider helpers, delegating evaluation rather than computing a second acreage union. [src/worldenergydata/federal_acreage/federal_acreage.py:L12-L33] [src/worldenergydata/federal_acreage/provider.py:L35-L41] |
| `report._acreage`, `_records`, `render_html`, `write_outputs` | Export helpers; bar widths and display precision are presentation calculations on existing result values. [src/worldenergydata/federal_acreage/report.py:L48-L173] |
| `LandmanDataValidator.validate_acreage` | Outside-package positive-value/range validation, not a second quarter-quarter union; related map coverage belongs in the follow-up. [packages/worldenergydata-landman/src/worldenergydata/landman/validators.py:L407-L434] |
| Engine federal-acreage branch | Delegates to the router; no independent geometry method. [src/worldenergydata/engine.py:L177-L181] |

## 10. Coverage and open items

Coverage record: every package Python file was read—`__init__.py`, `models.py`, `evidence.py`, `provider.py`, `report.py`, `federal_acreage.py`; section 3 describes the calculation path and sections 2 and 6 its input, export and error boundaries. [src/worldenergydata/federal_acreage/__init__.py:L1-L13] [src/worldenergydata/federal_acreage/models.py:L1-L172] [src/worldenergydata/federal_acreage/evidence.py:L1-L276] [src/worldenergydata/federal_acreage/provider.py:L1-L41] [src/worldenergydata/federal_acreage/report.py:L1-L173] [src/worldenergydata/federal_acreage/federal_acreage.py:L1-L33]

Test coverage read: all four `tests/unit/federal_acreage/test_*.py` files and `fixture_paths.py`; the two module-specific durable-workflow nodes are included in the execution record. [tests/unit/federal_acreage/test_evidence.py:L1-L113] [tests/unit/federal_acreage/test_models.py:L1-L85] [tests/unit/federal_acreage/test_provider.py:L1-L62] [tests/unit/federal_acreage/test_report.py:L1-L106] [tests/unit/federal_acreage/fixture_paths.py:L1-L8] [tests/workflows/test_durable_workflows.py:L111-L162]

Documentation discovery used `rg -l -i 'federal[_ -]acreage' docs examples src/worldenergydata/federal_acreage --glob '*.md' --glob '*.yaml' --glob '*.yml' --glob '!**/agent-pack.md'`; excluding this pack, the documentation found was `examples/workflows/federal-acreage-evidence/README.md`, `docs/registry/workflows.yaml`, and the example YAML configuration; the base YAML configuration was also read separately; no pre-existing package README or package documentation was found. [examples/workflows/federal-acreage-evidence/README.md:L1-L34] [docs/registry/workflows.yaml:L243-L269] [examples/workflows/federal-acreage-evidence/input.yml:L1-L23] [src/worldenergydata/base_configs/modules/federal_acreage/federal_acreage.yml:L1-L7]

Issue searches covered the module name, federal acreage, conversion/tolerance, implementation map, validation/branch coverage, QA fingerprints and partial export; existing #913, #914 and #925 provide acquisition, title and fixture context, while the focused gaps below require separate drafts (#913, acquisition acceptance criteria; #914, title feasibility acceptance criteria; #925, fixture-workflow acceptance criteria).

| Open item | Responsible role | Tracking / completion criterion |
| --- | --- | --- |
| External authority for hectare factor and rationale/boundaries for 0.5-acre tolerance; the unverified claim of section 3 | Calculation maintainer | issue pending (1); supply a reference-backed conversion and boundary checks. [src/worldenergydata/federal_acreage/evidence.py:L22-L22] [src/worldenergydata/federal_acreage/evidence.py:L58-L68] |
| Implementation-map method inventory | Map maintainer | issue pending (2); register section-3 methods and signals before they enter counted-family review. [src/worldenergydata/federal_acreage/evidence.py:L36-L276] |
| Missing-date policy and uncovered guard/status/provenance/display branches listed in section 6 | Module maintainer | issue pending (3); add synthetic branch assertions and explicit missing-date policy. [src/worldenergydata/federal_acreage/models.py:L94-L119] [src/worldenergydata/federal_acreage/evidence.py:L36-L47] [src/worldenergydata/federal_acreage/evidence.py:L118-L235] |
| Reproducible signed QA evidence, input fingerprints, deputy appointment and shared-log assignment; the unverified claim of section 8 | Calculations quality manager and module maintainer | issue pending (4); independently reviewed evidence bound to input bytes and code pin, with alternate review role recorded. [src/worldenergydata/federal_acreage/models.py:L160-L172] [src/worldenergydata/federal_acreage/report.py:L108-L173] |
| Output-pair consistency on I/O failure | Module maintainer | issue pending (5); detect and prevent partially replaced twins. [src/worldenergydata/federal_acreage/report.py:L163-L173] |
| Live acquisition, independently qualified source age and real geometry beyond the synthetic single-section model | Acquisition maintainer | #913; qualify normalized records and input geometry before replacing fixtures; no live-data validation is claimed. [src/worldenergydata/federal_acreage/provider.py:L1-L41] [src/worldenergydata/federal_acreage/evidence.py:L1-L5] |
| County title-chain evidence | Data maintainer | #914; maintain the separately visible unevaluated gap until evidence is supplied. [src/worldenergydata/federal_acreage/models.py:L149-L170] |

All source-read requirements for this package are covered; there are no deferred package subfolders, licensed-solver cases or private-reference-data cases in the selected suite. [src/worldenergydata/federal_acreage/__init__.py:L1-L13] [tests/unit/federal_acreage/test_evidence.py:L1-L113] [tests/unit/federal_acreage/test_models.py:L1-L85] [tests/unit/federal_acreage/test_provider.py:L1-L62] [tests/unit/federal_acreage/test_report.py:L1-L106]
