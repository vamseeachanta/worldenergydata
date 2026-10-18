# Legacy BSEE module knowledge pack

sweep: 0 found

Candidate sweep: `rg -n 'except\s+(Exception|BaseException)|except\s*:' src/worldenergydata/modules/bsee --glob '*.py'`. The count records broad exception handlers for review; it does not establish a failure or qualify their behavior.

| Header | Value |
| --- | --- |
| Module | `modules/bsee` |
| Repository | `worldenergydata` |
| Path | `src/worldenergydata/modules/bsee` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `81e159ef57534f2ac4f324992ca3b5cff55d56ad` |
| Analysis family | EC; data pipeline; AQG r0 section 10, Python calculations |
| QM role | Calculations quality manager |
| Status | DRAFT |

## 1. Purpose and scope

The legacy package initializer re-exports `worldenergydata.bsee`; it contains no calculation of its own. [src/worldenergydata/modules/bsee/__init__.py:L1-L1]

Normal imports are intercepted by `_ModulesRedirectFinder`, which rewrites the legacy prefix, checks the canonical module exists and returns a redirect loader. [src/worldenergydata/_compat.py:L76-L123]

The loader imports the canonical module and binds the old name to that same module object; the namespace test explicitly checks legacy BSEE identity. [src/worldenergydata/_compat.py:L60-L73] [tests/unit/common/test_namespace_workspace.py:L122-L125]

Scope covers the legacy import surface and its offline regression checks; canonical processing, forecasting and reporting remain outside this package's implementation boundary. [src/worldenergydata/modules/bsee/__init__.py:L1-L1] [src/worldenergydata/_compat.py:L95-L123]

UNVERIFIED: routing maturity is not established because the routing registry is absent at the code pin; issue pending (1).

## 2. Inputs and outputs

### Inputs

| Name | Unit / representation | Range / default | Source |
| --- | --- | --- | --- |
| `fullname` | Python module name; dimensionless string | Prefix `worldenergydata.modules.` and registered top-level name required | `_ModulesRedirectFinder.find_spec`. [src/worldenergydata/_compat.py:L85-L104] |
| `name` | Attribute name; dimensionless string | Registered moved-module name; unknown names raise `AttributeError` | Namespace `__getattr__`. [src/worldenergydata/modules/__init__.py:L21-L33] |
| Canonical module specification | Python import specification; no physical units | Missing specification returns no redirect | Finder lookup. [src/worldenergydata/_compat.py:L106-L123] |

### Outputs

| Name | Unit / representation | Contract | Source |
| --- | --- | --- | --- |
| Legacy import | Module object; no physical units | `sys.modules[old_name]` becomes canonical module | Redirect loader. [src/worldenergydata/_compat.py:L68-L73] |
| Deprecation notice | Python warning; count | At most one warning per old name retained in `_warned` | Redirect loader. [src/worldenergydata/_compat.py:L46-L47] [src/worldenergydata/_compat.py:L60-L67] |
| Namespace directory | Sorted list of names; count | Sorted moved-module names | `__dir__`. [src/worldenergydata/modules/__init__.py:L36-L37] |

The import adapter defines no coordinate frame, origin, physical sign convention or physical file format; its operations manipulate module names, warnings and module objects. [src/worldenergydata/_compat.py:L60-L73] [src/worldenergydata/_compat.py:L87-L123]

## 3. Method and governing standards

| Method | Implementation and reference | Governing basis |
| --- | --- | --- |
| Prefix replacement | The suffix after the legacy prefix becomes `worldenergydata.<suffix>` | Import algorithm, no engineering equation. [src/worldenergydata/_compat.py:L85-L104] |
| Recursion protection | `_finding` guards lookup and is cleared in `finally` | Import algorithm. [src/worldenergydata/_compat.py:L87-L113] |
| Canonical object reuse | The loader updates attributes and registers the canonical object under the old name | Import algorithm. [src/worldenergydata/_compat.py:L68-L73] |
| Idempotent installation | Existing finder instance prevents another insertion | Import algorithm. [src/worldenergydata/_compat.py:L126-L132] |
| Legacy export declarations | Data-loader and source initializers import symbols and define export lists | Delegation, not independent data processing. [src/worldenergydata/modules/bsee/data/loaders/__init__.py:L9-L34] [src/worldenergydata/modules/bsee/data/sources/__init__.py:L8-L20] |

No standards-derived coefficient is emitted by these import operations; a calculation citation sidecar is not applicable to this adapter. [src/worldenergydata/modules/bsee/__init__.py:L1-L1] [src/worldenergydata/_compat.py:L87-L123]

## 4. Validated worked examples

Validated examples: 0; the cases below exercise import contracts and synthetic expectations, rather than an independently qualified engineering dataset. [tests/unit/common/test_namespace_workspace.py:L75-L125] [tests/unit/test_modules_compat.py:L8-L36]

| Regression case | Input / expected value / tolerance | Test node ID | Offline result |
| --- | --- | --- | --- |
| R1 canonical identity | Legacy and canonical BSEE imports; 1 identical object; 0 identity mismatches | `tests/unit/common/test_namespace_workspace.py::test_move_is_import_transparent` | BASE PASS; AFTER PASS. [tests/unit/common/test_namespace_workspace.py:L75-L125] |
| R2 unknown attribute | `nonexistent_module_xyz_12345`; 1 `AttributeError`; exact exception match | `tests/unit/test_modules_compat.py::TestModulesCompat::test_getattr_unknown_raises` | BASE PASS; AFTER PASS. [tests/unit/test_modules_compat.py:L32-L36] |
| R3 sorted exports | `dir(modules)`; 0 ordering mismatches against `sorted(names)` | `tests/unit/test_modules_compat.py::TestModulesCompat::test_dir_returns_moved_modules` | BASE PASS; AFTER PASS. [tests/unit/test_modules_compat.py:L9-L14] |

## 5. QA gates

Family set: AQG r0 section 10, Python calculations; G0, G1, G2 and G5 apply, while G3 and G4 are not applicable (AQG r0, sections 9–10).

| Gate | Check ID | Module-specific pass criterion and unit | Evidence |
| --- | --- | --- | --- |
| G0 applicable | C0 | Hand-derive `worldenergydata.bsee` from `worldenergydata.modules.bsee`; 0 string mismatches, dimensionless count | Prefix and suffix operations. [src/worldenergydata/_compat.py:L85-L104] |
| G1 applicable | C1 | Import both names in the namespace test; 1 shared object and 0 import exceptions, dimensionless count | R1; offline Python route, no target solver. [tests/unit/common/test_namespace_workspace.py:L122-L125] |
| G1 applicable | C2 | Unknown attribute raises exactly 1 `AttributeError`, dimensionless count | R2. [tests/unit/test_modules_compat.py:L32-L36] |
| G2 applicable | C3 | Hand-sort the namespace export list; 0 mismatches, dimensionless count | Independent ordering operation compared with `__dir__`; this checks the adapter, not reservoir physics. [src/worldenergydata/modules/__init__.py:L36-L37] [tests/unit/test_modules_compat.py:L9-L14] |
| G3 NOT_APPLICABLE | none | No dynamics performed by the import adapter | Import operations only. [src/worldenergydata/_compat.py:L60-L73] |
| G4 NOT_APPLICABLE | none | No diffraction model or mesh produced by the import adapter | Import operations only. [src/worldenergydata/_compat.py:L60-L73] |
| G5 applicable | C5 | 3 of 3 listed regression cases have node IDs and paired offline results; 0 unaccounted cases, dimensionless count | R1–R3 evidence contract; no engineering clearance follows from import identity alone. [tests/unit/common/test_namespace_workspace.py:L122-L125] [tests/unit/test_modules_compat.py:L9-L14] [tests/unit/test_modules_compat.py:L32-L36] |

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom / cause | Detection | Evidence and disposition |
| --- | --- | --- |
| Missing canonical module: finder returns no redirect when canonical lookup fails | C1; failed import is not analytical validation | Historical issue 278 documents missing type-curve implementations; present detection is import identity plus explicit type-curve tests. [docs/plans/2026-05-04-issue-278-compatibility-shims.md:L15-L20] [src/worldenergydata/_compat.py:L106-L116] [tests/modules/bsee/analysis/test_type_curves.py:L9-L22] |
| Reading a legacy initializer as an independent computation overstates implementation coverage | C0; inspect imports before counting an implementation | The type-curve initializer exports imported symbols, as do the data-loader and source initializers. [src/worldenergydata/modules/bsee/analysis/type_curves/__init__.py:L3-L34] [src/worldenergydata/modules/bsee/data/loaders/block/__init__.py:L6-L12] [src/worldenergydata/modules/bsee/data/loaders/lease/__init__.py:L6-L11] [src/worldenergydata/modules/bsee/data/sources/zip/__init__.py:L6-L11] |
| A warning is suppressed after first use of an old name | No dedicated warning-count detection check exists in the listed regression cases; issue pending (1) | `_warned` gates warning emission; the current attribute-access test only checks a module is returned. [src/worldenergydata/_compat.py:L60-L67] [tests/unit/test_modules_compat.py:L16-L30] |
| Documentation test command points outside the present paleowell test directory | Compare documented test location with the collected canonical tests; no dedicated documentation-link detection check exists | The documented command uses the legacy test directory; current tests are under the unit-test tree; issue pending (3). [docs/domains/bsee/paleowells-readme.md:L128-L134] [tests/unit/bsee/paleowells/test_field_era.py:L1-L16] |
| Historical type-curve collection failure can be confused with current adapter failure | Run the explicit type-curve test file, alongside C1 | Existing issue 313 records the infrastructure follow-up; the import node remains explicit. [docs/plans/2026-05-04-issue-313-test-infra-cleanup.md:L7-L11] [tests/modules/bsee/analysis/test_type_curves.py:L9-L22] |

## 7. Lessons log

No historical lesson is imported as a new event; the current boundary separates a redirect from a second implementation, because the loader reuses the canonical object. [src/worldenergydata/_compat.py:L68-L73]

| Date | Change reference | Lesson | Evidence | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack revision | Check canonical identity before treating legacy source directories as executable duplicates | [tests/unit/common/test_namespace_workspace.py:L122-L125] | issue pending (1) |

## 8. Ownership

Calculations quality manager; deputy data-pipeline quality manager when appointed; producing role: module maintainer; unresolved classifications go to the family quality manager (AQG r0, sections 10–11).

## 9. Dependencies

The root package installs the redirect finder during initialization; the finder imports canonical BSEE and its deeper subpackages on demand. [src/worldenergydata/__init__.py:L62-L65] [src/worldenergydata/_compat.py:L95-L123]

Attribute access through the old namespace also delegates to the canonical module. [src/worldenergydata/modules/__init__.py:L21-L33]

The namespace regression checks that canonical BSEE resolves from its workspace member, while legacy BSEE is the same object. [tests/unit/common/test_namespace_workspace.py:L98-L104] [tests/unit/common/test_namespace_workspace.py:L122-L125]

### Implementation inventory and second implementations

Map source: `digitalmodel`, `docs/registry/implementation-map.yaml`, data revision `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; embedded source-code revision `947fa50ff9a9e210de7e8f90e01b37add85c5954` (digitalmodel, Implementation map, named data revision, `repository`, `revision` and `families` fields).

The inventory is empty: 0 families have an implementation row inside `src/worldenergydata/modules/bsee`; therefore 0 families are counted and the counted-family grep is `NOT_APPLICABLE` (digitalmodel, Implementation map, named data revision, `families[].implementations[].path`).

A separate package inspection finds export imports rather than formulas or solver launches in the legacy initializers. [src/worldenergydata/modules/bsee/__init__.py:L1-L1] [src/worldenergydata/modules/bsee/paleowells/__init__.py:L8-L11] [src/worldenergydata/modules/bsee/analysis/type_curves/__init__.py:L3-L34] [src/worldenergydata/modules/bsee/data/loaders/__init__.py:L9-L34] [src/worldenergydata/modules/bsee/data/sources/__init__.py:L8-L20]

Repository-wide dependency search includes `scripts/`; the actual prefix rewrite and aliasing algorithms are outside this package, in the compatibility layer, and are map follow-up candidates rather than package misses. [src/worldenergydata/_compat.py:L60-L73] [src/worldenergydata/_compat.py:L85-L123] [src/worldenergydata/modules/__init__.py:L21-L37]

Map follow-up: prefix rewriting, module-object aliasing, idempotent finder installation and export forwarding are the section-3 method families; record their exclusion or registration before a later map revision counts them; issue pending (2). [src/worldenergydata/_compat.py:L95-L123] [src/worldenergydata/_compat.py:L126-L132] [src/worldenergydata/modules/bsee/__init__.py:L1-L1]

## 10. Coverage and open items

| Item | Evidence / boundary | Tracking |
| --- | --- | --- |
| U1 UNVERIFIED: routing maturity and routing index availability | The adapter export does not establish analytical maturity. [src/worldenergydata/modules/bsee/__init__.py:L1-L1] | issue pending (1) |
| U2 UNVERIFIED: complete canonical analytical validation | Import identity provides no independent engineering expected value; validated examples remain 0. [tests/unit/common/test_namespace_workspace.py:L122-L125] | issue pending (1) |
| Warning-count detection, canonical test coverage and shared lesson indexing | The known-module test asserts only a non-null module. [tests/unit/test_modules_compat.py:L16-L30] | issue pending (1) |
| Implementation-map follow-up | Prefix replacement, aliasing and installation reside outside the package. [src/worldenergydata/_compat.py:L95-L132] | issue pending (2) |
| Stale paleowell test command | The documentation still names the legacy test directory. [docs/domains/bsee/paleowells-readme.md:L128-L134] | issue pending (3) |
| Historical compatibility incident | The historical plan records lost type-curve implementations; current results must be read separately. [docs/plans/2026-05-04-issue-278-compatibility-shims.md:L15-L20] | Existing issues 278 and 313 |

### Files read and tests listed

All nine package Python files are inspected: the root initializer; empty analysis initializer; type-curve and paleowell initializers; loader, block-loader and lease-loader initializers; source and ZIP-source initializers. [src/worldenergydata/modules/bsee/__init__.py:L1-L1] [src/worldenergydata/modules/bsee/analysis/type_curves/__init__.py:L1-L34] [src/worldenergydata/modules/bsee/paleowells/__init__.py:L1-L11] [src/worldenergydata/modules/bsee/data/loaders/__init__.py:L1-L34] [src/worldenergydata/modules/bsee/data/loaders/block/__init__.py:L1-L12] [src/worldenergydata/modules/bsee/data/loaders/lease/__init__.py:L1-L11] [src/worldenergydata/modules/bsee/data/sources/__init__.py:L1-L20] [src/worldenergydata/modules/bsee/data/sources/zip/__init__.py:L1-L11]

Read supporting files: `_compat.py`, namespace initializer, root initializer, namespace and compatibility tests, type-curve tests, paleowell tests, historical compatibility plan and paleowell documentation. [src/worldenergydata/_compat.py:L1-L16] [src/worldenergydata/modules/__init__.py:L1-L11] [tests/unit/common/test_namespace_workspace.py:L1-L15] [docs/domains/bsee/paleowells-readme.md:L1-L22]

The paleowell documentation describes a processing implementation, while this legacy initializer only imports two classes; that documentation is not used to infer processing behaviour inside the adapter. [docs/domains/bsee/paleowells-readme.md:L7-L22] [src/worldenergydata/modules/bsee/paleowells/__init__.py:L8-L11]

Tests selected for the adapter main path: `tests/unit/test_modules_compat.py`, `tests/unit/common/test_namespace_workspace.py`, `tests/modules/bsee/analysis/test_type_curves.py`, and `tests/unit/bsee/paleowells/`; canonical data-pipeline clearance remains issue pending (1). [tests/unit/test_modules_compat.py:L8-L36] [tests/unit/common/test_namespace_workspace.py:L75-L125] [tests/modules/bsee/analysis/test_type_curves.py:L9-L22] [tests/unit/bsee/paleowells/test_field_era.py:L1-L16]

### Documentation discovery requiring canonical coverage follow-up

The following discovery files require separate canonical review; discovery does not establish that their claims are current; issue pending (1).

- `docs/knowledge-base/bsee/integration/codebase-mapping.md`
- `docs/hse/URL_REFRESH_INTEGRATION.md`
- `docs/intervention-db/data-quality.md`
- `docs/data/TWO_TIER_DATA.md`
- `docs/PHASE_2_TIER_1_COVERAGE_EXPANSION.md`
- `docs/data/DATA_INVENTORY_ANALYSIS.md`
- `docs/data/LOCAL_DATA_PATTERN.md`
- `docs/knowledge-base/bsee/data-sources/raw-data-downloads.md`
- `docs/data/DATA_MAP.md`
- `docs/domains/bsee/infrastructure_data_catalog.md`
- `docs/domains/bsee/paleowells-readme.md`
- `docs/knowledge-base/bsee/README.md`
- `docs/domains/field-development/README.md`
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`
- `docs/research/project_economics-code-comparison.md`
- `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md`
- `docs/research/bsee-project_economics-integration-summary.md`
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`
- `docs/research/project_economics-implementation-plan.md`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
- `docs/plans/2026-05-04-issue-339-legacy-npv-test-resolution.md`
- `docs/plans/2026-05-04-issue-271-scheduler-output-dir.md`
- `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md`
- `docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md`
- `docs/research/docs/research/project_economics-integration-index.md`
- `docs/plans/2026-05-04-issue-365-bsee-binary-ingest.md`
- `docs/plans/2026-05-18-issue-424-decommissioning-market-outlook.md`
- `docs/plans/2026-05-04-issue-313-test-infra-cleanup.md`
- `docs/plans/2026-07-16-issue-1038-cost-map-program.md`
- `docs/plans/2026-05-04-issue-278-compatibility-shims.md`
- `docs/plans/2026-05-15-issue-411-bsee-war-bridge.md`
- `docs/plans/2026-07-06-issue-847-boem-reserves-discovery-ingest.md`
- `docs/plans/2026-05-04-issue-267-bsee-scheduler-compat.md`
- `docs/plans/2026-05-04-issue-367-api12-npv-migration.md`
- `docs/plans/2026-05-04-issue-325-xfail-bugs.md`
- `docs/plans/2026-05-18-issue-426-drilling-hse-patterns.md`
- `docs/plans/2026-07-18-issue-1039-manifest-lineage-hotfix.md`
- `docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md`
- `docs/plans/2026-05-04-issue-341-npv-suite-drift.md`
- `docs/modules/bsee/chunk_refresh_mechanism.md`
- `docs/modules/bsee/PRODUCTION_DATA_RETRIEVAL_GUIDE.md`
- `docs/modules/bsee/well_data_verification/bsee_integration.md`
- `docs/modules/bsee/comprehensive-report-system/README.md`
- `docs/modules/bsee/data-refresh-architecture/web-scraping-libraries.md`
- `docs/modules/bsee/well_data_verification/troubleshooting.md`
- `docs/modules/bsee/data-refresh-architecture/module-documentation.md`
- `docs/development/development_history.md`
- `docs/modules/bsee/data-refresh-architecture/data-flow-diagram.md`
- `docs/modules/bsee/data-refresh-architecture/README.md`
- `docs/modules/bsee/analysis/production/project_economics_V30/README_PRODUCTION_RETRIEVAL.md`
- `docs/modules/bsee/analysis/production/project_economics_V30/QUICKSTART.md`
- `docs/data-sources/bsee/analysis/rig_days/day_basis_comparison.md`
- `docs/modules/project_economics/USER-GUIDE.md`
- `docs/data-sources/bsee/data/WELL_ACTIVITY_CD/publication_status.md`
- `docs/ci/flake8-inventory-2026-04-23.md`
- `docs/data-sources/bsee/data/local_field_development_sources.md`
- `docs/data-sources/bsee/data/data_rev1.md`
- `docs/data-sources/bsee/data/drilling_data_rev1.md`
- `docs/data-sources/bsee/analysis/well-identifier-grain.md`
- `docs/data-sources/bsee/data/field_infrastructure_bundle_contract.md`
- `docs/data-sources/bsee/data/well/well_count.md`
- `docs/data-sources/bsee/data/clean_up/data_for_analysis.md`
- `docs/data-sources/bsee/analysis/economics/NPV/NPV_REFACTORING_SUMMARY.md`

2 discovery files with identifying names and 1 discovery file with restricted path wording are omitted from this public inventory; codenaming remains issue pending (1).

### Offline execution record

Selected baseline: 60 passed, 0 failed, 0 skipped, 0 NOT_RUN at the header code pin; AFTER: 60 passed, 0 failed, 0 skipped, 0 NOT_RUN at the same code pin. The selection is an adapter main-path check, not the complete canonical BSEE test suite. [tests/unit/common/test_namespace_workspace.py:L75-L125] [tests/modules/bsee/analysis/test_type_curves.py:L9-L22]

The inventory estimate is not used as an execution count: the selected namespace test checks import identity, while type-curve tests exercise a canonical implementation through its legacy spelling; complete canonical collection and count reconciliation remain issue pending (1). [tests/unit/common/test_namespace_workspace.py:L122-L125] [tests/modules/bsee/analysis/test_type_curves.py:L9-L22]

The ordinary `uv run python -m pytest` form is used, with `-q -rA -p no:cacheprovider` and a separate scratch basetemp per run; the after-check uses the existing-tree preservation option to verify the uncommitted pack is unchanged by tests. No source-resolution fallback or addopts override is used. [tests/conftest.py:L394-L421] [tests/conftest.py:L425-L449]
