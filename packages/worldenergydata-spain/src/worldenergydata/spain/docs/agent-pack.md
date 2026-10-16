# Spain module knowledge pack

| Header | Value |
| --- | --- |
| Module | spain |
| Repository | worldenergydata |
| Package path | `packages/worldenergydata-spain/src/worldenergydata/spain` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` |
| Analysis family | EC; data pipeline; Python calculations gate set, AQG r0 |
| Quality role | Calculations quality manager; dedicated data role pending |
| Status | DRAFT; independent review pending |

## 1. Purpose and scope

`parse_cores_frame` converts monthly wide production frames into long oil or gas rows; `CoresLiveProductionLoader` merges the products and writes normalized CSVs. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L87-L113] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L91-L107]

`run_spain_reference_chain` connects unified production, FDAS conversion, sparse concept screening and pre-tax cashflow; its output explicitly labels screening as wiring-only and flags onshore model mismatch. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L22-L78]

`build_report` consumes normalized scheduler caches and can emit JSON and self-contained HTML; it evaluates economics only for curated metadata entries with positive oil volume. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L101-L175]

UNVERIFIED: Engineering valuation readiness, current external-source freshness and a registry maturity classification are not established; issue pending (1).

## 2. Inputs and outputs

| Input | Unit | Range / default | Route and evidence |
| --- | --- | --- | --- |
| `raw`, `product` | Oil tonnes; gas GWh | Product oil or gas; year positive; recognized Spanish or English month; numeric non-null field values | `parse_cores_frame`; annual totals and invalid months are removed. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L127-L159] |
| `oil_conversion_audit` | bbl/tonne | Required for oil; accepted source factor or explicit default opt-in | `_conversion_factor`, `build_oil_conversion_audit`. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L186-L198] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L243-L279] |
| `cache_root`, workbook selection | Path; worksheet / row index | Caller supplies cache; live default `Production`, header row index 5 | `CoresLiveProductionLoader`. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L60-L84] |
| Density factor record | API degrees; bbl/tonne | Accepted factor positive and between 5.0 and 9.5 bbl/tonne; formula agreement within 0.01 bbl/tonne | `validate_crude_density_factor`. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L135-L191] |
| `field_meta` | `water_depth_m` in m; categorical metadata | Onshore missing water depth becomes 0.0 m; region forced to spain | `spain_field_to_concept`. [packages/worldenergydata-spain/src/worldenergydata/spain/field_concept.py:L28-L38] |
| Oil / gas price deck | USD/bbl; USD/Mcf | Oil default 75.0 USD/bbl; gas deck optional, keyed by year-month | `run_spain_reference_chain`. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L22-L37] |

| Output | Unit / convention | Route and evidence |
| --- | --- | --- |
| Long production | `field_name`, integer `year`, integer `month`, `oil_bbl` or `gas_mcf` | Multiplication by resolved factor; no spatial coordinate frame is represented. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L162-L183] |
| Normalized CSV and density JSON | bbl, Mcf; sorted by field/year/month | `_write_normalized` and `_oil_density_sidecar_payload` retain coverage, factors and registry provenance. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L164-L193] |
| Download metadata | Byte count, SHA-256, source URL, HTTP status | `_workbook_metadata` records source units and relative raw path. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L250-L271] |
| Reference-chain metrics | Months; revenue, royalty, capital and net cashflow in USD | `_pre_tax_metrics` sums cashflows and carries the mismatch flag. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L102-L110] |
| Report payload | bbl, Mcf, USD; year-month strings | `_field_summaries`, `_monthly_series`, `_reference_chain_summary`; missing numeric products become zero in unified report rows. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L178-L231] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L276-L297] |

## 3. Method and governing standards

1. Frame parsing identifies year/month columns, removes aggregate columns, filters monthly rows, melts field columns and coerces numeric values; non-numeric production values are silently removed. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L127-L159]
2. Oil conversion multiplies tonnes by the audit's field-specific bbl/tonne factor; missing coverage becomes `CoresParseError`. Gas conversion uses the code's approximate 3290.0 Mcf/GWh factor. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L186-L198] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L32-L39]
3. `bbl_per_tonne_from_api` calculates specific gravity as `141.5 / (API + 131.5)` and returns `1 / (specific_gravity * 0.158987294928)`; this is a code equation, not an independently qualified physical reference. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L45-L48]
4. Density keys undergo Unicode decomposition, accent removal and lower-case alphanumeric normalization; source class, confidence, aliases and conversion eligibility are checked before registry use. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L38-L42] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L135-L191]
5. Source discovery requires both workbook links; download validation rejects HTTP errors, empty bytes and explicitly non-Excel MIME types, then writes atomically and records provenance. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L86-L114] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L232-L247] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L282-L285]
6. Report input validation compares scheduler and CSV row counts, requires successful scheduler status and workbook provenance; density audit validation checks factor links and coverage. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L234-L273] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_density_audit.py:L114-L124] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_density_audit.py:L268-L313]
7. The reference chain delegates economic calculations to FDAS rather than implementing a fiscal regime here; absent gas prices retain the oil-only route. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L22-L78]

UNVERIFIED: Independent qualification of conversion constants, governing-standard editions and calc-citation sidecar coverage is incomplete; issue pending (1).

## 4. Validated worked examples and regression examples

Validated examples: 0; independent published expected values have not been qualified, issue pending (1).

The following are regression examples with synthetic inputs, not engineering validation; expected values and assertions are defined by the cited tests. [tests/unit/spain/test_cores_loader.py:L159-L184] [tests/unit/spain/test_cores_density.py:L56-L58] [tests/unit/spain/test_synthetic_gas_reference_chain.py:L24-L54] [tests/unit/spain/test_synthetic_gas_reference_chain.py:L57-L63]

| ID | Source / input | Expected result and tolerance | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 | Synthetic in-memory oil frame and injected factor | 10 tonnes × 6.95 bbl/tonne = 69.5 bbl; pytest approximate equality, no explicit tolerance set | `tests/unit/spain/test_cores_loader.py::test_parse_oil_frame_uses_conversion_audit_factor` | BASE PASS; AFTER PASS |
| R2 | Synthetic API inputs | 36.0 degrees → 7.44554 bbl/tonne; 20.0 degrees → 6.73432 bbl/tonne; relative tolerance 1e-5 | `tests/unit/spain/test_cores_density.py::test_bbl_per_tonne_from_api_matches_reference_formula` | BASE PASS; AFTER PASS |
| R3 | Synthetic gas production and 3.0 USD/Mcf price deck | Gross revenue 29610.0 USD; royalty 3701.25 USD; net 25908.75 USD; exact assertions | `tests/unit/spain/test_synthetic_gas_reference_chain.py::test_synthetic_pure_gas_chain_uses_existing_volume_conversion` | BASE PASS; AFTER PASS |
| R4 | Synthetic gas production, no price deck | Gross revenue 0.0 USD; exact assertion | `tests/unit/spain/test_synthetic_gas_reference_chain.py::test_synthetic_pure_gas_chain_without_deck_retains_zero_revenue` | BASE PASS; AFTER PASS |

Execution record: BASE 109 passed, 0 failed, 0 skipped, 0 NOT_RUN; AFTER 109 passed, 0 failed, 0 skipped, 0 NOT_RUN; code revision is the header pin.

## 5. QA gates

The adopted family set is Python calculations in AQG r0 section 10; the following are executable acceptance criteria, not evidence of signed clearance.

| Gate | Applicability | Module-specific check and numeric pass criterion | Evidence route |
| --- | --- | --- | --- |
| G0 | Applicable: input units, citations | C0: missing oil audit produces exactly 1 `CoresParseError` per invalid invocation; 0 uncited accepted factors in malformed-registry test | `test_parse_oil_frame_requires_conversion_audit`, `test_density_registry_requires_citation_fields`; exception assertions. [tests/unit/spain/test_cores_loader.py:L113-L126] [tests/unit/spain/test_cores_density.py:L61-L69] |
| G1 | Applicable: import and tests | C1: 0 failed tests and 0 collection errors across the module, adapter and scheduler paths; imports occur through the production loader, reference chain and report test routes | Offline pytest results; no program input deck or solver load route is applicable. [tests/unit/spain/test_reference_chain.py:L49-L73] [tests/unit/spain/test_cores_field_development_report.py:L252-L259] |
| G2 | Applicable: arithmetic comparison | C2: R1 oil volume differs from 69.5 bbl by at most 0.0001 bbl; R3 gross revenue differs from 29610.0 USD by 0.0 USD | Hand multiplication of synthetic test inputs and the named regression assertions; physical conversion qualification remains open. [tests/unit/spain/test_cores_loader.py:L159-L184] [tests/unit/spain/test_synthetic_gas_reference_chain.py:L24-L54] |
| G3 | NOT_APPLICABLE | No offset-sweep response criterion: package route transforms production and delegates cashflow; 0 solver cases | `run_spain_reference_chain`. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L22-L78] |
| G4 | NOT_APPLICABLE | No mesh, buoyancy or displacement calculation in the documented package route; 0 mesh cases | `parse_cores_frame` and `build_report`. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L87-L113] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L101-L117] |
| G5 | Applicable: traceable evidence appendix | C5: 0 unmatched CSV row-count records and 0 missing required workbook provenance fields in the report-source test; a released report additionally requires 0 missing gate statuses, input fingerprints or independent signatures | Source-validation tests cover metadata; a generated signed AQG appendix is not established, issue pending (2). [tests/unit/spain/test_cores_field_development_report.py:L16-L80] |

C0, C1 and C2 are software checks; C5's metadata portion is executable now, while its signed-appendix criterion remains open rather than implicitly passing. [tests/unit/spain/test_cores_field_development_report.py:L16-L80]

## 6. Known failure modes and pitfalls

| Symptom / cause | Detection | Incident or follow-up |
| --- | --- | --- |
| Non-numeric production and unrecognized month rows disappear during filtering | No dedicated rejected-row-count detection check exists; add a count reconciliation criterion, issue pending (3) | `_monthly_rows` / `_melt_field_values`. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L143-L159] |
| Missing product values become zero in normalized report rows | C2 and sparse-product strict-JSON regression; zero-fill must not be interpreted as measured zero | `_to_unified`. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L276-L297] |
| Missing density coverage blocks strict oil conversion; explicit opt-in uses the approximate default | C0 and strict-coverage tests; 0 silently defaulted fields under strict mode | Conversion coverage work, issue 807; current source-gap follow-up, issue pending (1). [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L243-L279] |
| Earlier adapter expectations disagreed with accepted density provenance | C1; current adapter tests assert complete coverage and use the accepted registry factor | Historical defect issue 983; no claim of continuing failure without the offline result. [tests/unit/production/unified/test_spain_cores_adapter_loader.py:L194-L214] |
| Gas-only report economics remains deferred while the reference chain supports gas pricing | C2 and R3/R4 distinguish priced and unpriced routes; report selection still requires oil | Issue 808. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L151-L175] [tests/unit/spain/test_synthetic_gas_reference_chain.py:L24-L54] |
| Onshore concept and cashflow results are plumbing checks with sparse metadata | Reference-chain mismatch assertion and C1; 0 missing mismatch flags in that test | Issue 763; engineering-use qualification, issue pending (1). [tests/unit/spain/test_reference_chain.py:L56-L73] |
| Cached bytes may change while existing metadata is reused without recomputing its digest | No detection check exists for this tamper case; add digest equality with 0 byte-integrity mismatches | `_cached_metadata`, issue pending (4). [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L161-L176] |

Issue search covered the module keyword and conversion/validation keywords; the inventory's issue count is treated as a discovery lead rather than a defect count.

## 7. Lessons log

| Date | Record | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack | Preserve the distinction between strict density coverage, explicit default assumptions and physical validation | [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L243-L279] | Sections 2–6 separate those cases | Pending; issue pending (2) |

## 8. Ownership

- Proposed family quality role: calculations quality manager covering data pipelines; deputy: a maintainer-appointed independent reviewer.
- Producing role: module documentation contributor; independent clearance remains pending.
- Escalation: missing evidence, changed tolerances and ambiguous reference qualification go to the quality role; scope and publication decisions go to the maintainer.

These are pack governance assignments, not claims that a review or approval occurred.

## 9. Dependencies and implementation inventory

`worldenergydata-spain` declares core, FDAS, production, pandas and openpyxl dependencies; its reference chain additionally imports field-development recommendations. [packages/worldenergydata-spain/pyproject.toml:L25-L31] [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L10-L19]

| Relationship | Contract / inventory disposition | Evidence |
| --- | --- | --- |
| Upstream source | CORES oil tonnes and gas GWh workbook contracts; external freshness and rights not requalified | [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L30-L53] |
| Downstream production | Unified adapter standard-column normalization; default fixture and embedded fallback paths | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L47-L114] |
| Downstream economics | FDAS production conversion, assumptions and cashflow engine; field-development recommendation | [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L22-L78] |
| Scheduler | Refresh wrapper uses the module's live loader; deterministic source and density errors are non-retryable | [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/spain_cores_refresh.py:L36-L69] |
| Reporting script | CLI delegates to `build_report` | [scripts/spain/build_cores_field_development_report.py:L15-L25] |
| Cross-module inventory | Provider inventory rows for these dependencies are not qualified in this pack; issue pending (2) | [packages/worldenergydata-spain/pyproject.toml:L25-L31] |

### Implementation-map inventory

Map repository: digitalmodel; ref `origin/codex/implmap-work`; data revision `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; file `docs/registry/implementation-map.yaml`.

At that map revision, 0 implementation rows have paths inside this pack's package; inventory: empty; counted families: 0; A8 grep: `NOT_APPLICABLE`, because no map family has an in-package row.

The map follow-up will add monthly production normalization, crude density conversion/auditing, workbook cache provenance, report assembly and reference-chain orchestration from section 3 before those families can count; issue pending (2).

### Whole-repository supplementary discovery

Searches for `parse_cores_frame`, `bbl_per_tonne_from_api`, `GWH_TO_MCF`, `CoresWorkbookSource` and `run_spain_reference_chain` include package sources, root sources, tests and `scripts/`; these are supplementary findings and do not change the empty-map A8 result.

The unified adapter's `_merge_product_frames` also outer-merges product frames, and its embedded fallback holds its own sample rows and conversion metadata; the scheduler and CLI delegate to the listed loader/report routes. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L47-L114] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L131-L160] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/spain_cores_refresh.py:L36-L69] [scripts/spain/build_cores_field_development_report.py:L15-L25]

These outside-package implementations are map follow-up candidates rather than additional counted in-package misses; issue pending (2).

## 10. Coverage and open items

### Read inventory

Package source coverage includes `field_concept.py`, `reference_chain.py`, `production/cores_loader.py`, `production/cores_density.py`, `production/cores_live.py`, `production/cores_source.py`, `reports/cores_field_development.py`, `reports/cores_density_audit.py`, `reports/cores_html.py`, and the root, production and reports initializer files; detailed inventory and remaining documentation qualification are tracked by issue pending (2).

Tests read: the eight `tests/unit/spain/test_*.py` files, `tests/unit/production/unified/test_spain_cores_adapter_loader.py`, and `tests/unit/scheduler/test_spain_cores_refresh.py`; the execution record below supersedes the inventory's unverified count, issue pending (2).

Documentation discovery: `packages/worldenergydata-spain/README.md`; the four Spain implementation plans for issues 806, 807, 809 and 810; `docs/plans/README.md`; `docs/domains/field-development/gas-revenue.md`; `docs/modules/repository-architecture.md`; incidental references to generic processor cores are excluded from module scope, issue pending (2).

No `docs/registry/module-routing.yaml` exists at the code pin; no registry edit is supplied, issue pending (2).

### Open-item register

| Item | Disposition / responsible role | Tracking |
| --- | --- | --- |
| Engineering valuation readiness, external-source freshness and registry maturity are not established | Unqualified; calculations quality role; no engineering acceptance claimed | issue pending (1) |
| Independent conversion qualification, governing-standard editions and calc-citation sidecar coverage are incomplete | Unqualified; calculations quality role; 0 validated examples | issue pending (1) |
| Remaining density source gap and original publisher evidence | Requalify sources before physical use; no identifying records or client values copied | issue pending (1) |
| Generated AQG evidence appendix, signatures, dependency inventory rows, map enrollment, index and shared log | Maintainer and quality role; do not equate metadata tests with signed clearance | issue pending (2) |
| Source/read inventory and documentation qualification | Maintainer; complete independent review and reconcile any stale plan claims against code | issue pending (2) |
| Identifying discovery content (1 file with an identifying name) | Maintainer; codenaming follow-up; source contents are not reproduced | issue pending (2) |
| Rejected-row accounting | Module maintainer; add explicit filtered-input counts and a numeric reconciliation test | issue pending (3) |
| Cached-byte integrity | Module maintainer; verify current bytes against retained digest before metadata reuse | issue pending (4) |
| Report gas-only economics | Module maintainer; distinguish enabled reference-chain gas pricing from report selection | issue 808 |

### Offline execution record

BASE: 109 passed, 0 failed, 0 skipped, 0 NOT_RUN at the header pin; AFTER 109 passed, 0 failed, 0 skipped, 0 NOT_RUN.

Command form: `uv run python -m pytest tests/unit/spain tests/unit/production/unified/test_spain_cores_adapter_loader.py tests/unit/scheduler/test_spain_cores_refresh.py -q -rA -p no:cacheprovider --basetemp=<scratch> --allow-existing-tree-changes`, with coverage data and HTML/XML/JSON destinations in scratch; repository addopts retained, ordinary source resolution, no extra installation or solver use.

The first execution passed all 109 cases but failed the tree-preservation check because the pack was created during the run; the clean-tree repeated baseline passed, and existing-work digest verification remains enabled for the after run.

Additional contract-domain check: 46 passed, 0 failed, 0 skipped, 0 NOT_RUN using `uv run python -m pytest tests/contracts` with the same offline options and scratch destinations; no module code changed.
