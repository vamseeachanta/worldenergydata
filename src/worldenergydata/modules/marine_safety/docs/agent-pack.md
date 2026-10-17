# Marine safety compatibility knowledge pack

| Header | Value |
| --- | --- |
| Module | `modules/marine_safety` |
| Repository | `worldenergydata` |
| Package path | `src/worldenergydata/modules/marine_safety` |
| Pack revision | 1, 2026-10-16 |
| Code revision | `72716499230d3457ce90a5bcd23a8a8367bc0bd3` |
| Analysis family | EC; compatibility interface for a data pipeline; AQG r0 section 10, Python calculations |
| Quality role | Calculations quality manager; data-pipeline quality manager as deputy when appointed |
| Status | DRAFT |

## 1. Purpose and scope

The package retains a wildcard re-export at its root and explicit re-exports for analysis, incident analysis, importers and processors; these files contain imports and export lists rather than incident-processing algorithms. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20]

Normal imports first encounter the shared redirect finder, installed by the namespace root; `marine_safety` is a registered moved package, and successful resolution aliases the old name to the canonical module object. [src/worldenergydata/__init__.py:L59-L65] [src/worldenergydata/_compat.py:L25-L44] [src/worldenergydata/_compat.py:L60-L73] [src/worldenergydata/_compat.py:L103-L123]

This pack covers that compatibility boundary, including all its subdirectories; the separate implementation package and its existing knowledge pack retain responsibility for incident ingestion, statistics, database operations and reporting. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs/agent-pack.md:L1-L13] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/__init__.py:L16-L30]

UNVERIFIED: U1 — no maturity classification or routing entry is established for this compatibility package; documentation and routing reconciliation is section 10, issue pending (1).

## 2. Inputs and outputs

### Inputs

| Name | Unit | Allowed range | Default | Source and evidence |
| --- | --- | --- | --- | --- |
| Import path | dotted Python identifier | Prefix `worldenergydata.modules.` followed by a registered moved name and optional suffix | No inferred alternative for an unregistered name | Shared finder extracts the suffix and checks registration. [src/worldenergydata/_compat.py:L85-L104] |
| Attribute name | Python identifier | Registered moved names for `from worldenergydata.modules import name` | Unknown attributes raise `AttributeError` | Shared namespace attribute route. [src/worldenergydata/modules/__init__.py:L21-L34] |
| Canonical package availability | importable module | `worldenergydata.marine_safety` and the requested suffix must resolve in the environment | Finder declines when the target cannot resolve | [src/worldenergydata/_compat.py:L106-L123] |

### Outputs

| Name | Unit | Range or representation | Default | Evidence |
| --- | --- | --- | --- | --- |
| Legacy imported module | Python module object | Same object as the canonical import on successful redirect | Canonical module namespace | [src/worldenergydata/_compat.py:L68-L73] |
| Deprecation warning | warning event | At most one emitted per old import name in the loader's warning set | Warning registered before canonical import | [src/worldenergydata/_compat.py:L46-L47] [src/worldenergydata/_compat.py:L60-L68] |
| Analysis exports declared in the compatibility file | Python objects | `CauseAnalysisReport`, `ReportFilters`, `CauseStatistics`, `CrossTabulation`, `FrequencyDistribution`, `StatisticalSummary`, `TemporalTrend`, `HatchMaloperationAnalyzer` | Explicit `__all__`; runtime target differs as section 6 records | [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] |
| Incident-analysis exports | Python class | `HatchMaloperationAnalyzer` | Explicit `__all__` | [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] |
| Importer exports declared in the compatibility file | Python classes | `BaseImporter`, `MISLEImporter` | Explicit `__all__` | [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] |
| Processor exports | Python classes | `BaseProcessor`, `DataCleaner`, `DataNormalizer` | Explicit `__all__` | [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20] |

These compatibility files define no physical coordinates, unit conversions, file readers, numeric defaults or serialization formats; such contracts belong to the implementations they import. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20]

## 3. Method and governing standards

| Method family | Implementation | Governing basis |
| --- | --- | --- |
| Legacy import dispatch | `_ModulesRedirectFinder.find_spec()` removes the legacy namespace component, resolves the canonical path and supplies `_RedirectLoader`; `exec_module()` registers object identity in `sys.modules` | Python import compatibility policy; no engineering equation is implemented here. [src/worldenergydata/_compat.py:L60-L73] [src/worldenergydata/_compat.py:L85-L123] |
| Wildcard export | Root compatibility file imports the canonical namespace with `*`; canonical `__all__` controls that direct file's export surface | Application export contract. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/__init__.py:L69-L94] |
| Explicit export | Four subordinate compatibility files bind named classes and define `__all__` | Application export contract; compare the declarations against the actual redirected module before relying on an export. [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20] |

No standards-derived formula or constant appears in the compatibility files, so a calculation-output citation sidecar has no object on this path; source references above describe the import contract. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20]

## 4. Validated worked examples

Validated numerical examples: 0; this package implements import and export contracts rather than a numerical calculation. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20]

The following are regression examples with application-defined expectations, not independently validated incident-analysis benchmarks. [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L83-L92] [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L375-L379] [tests/modules/marine_safety/analysis/test_cause_report.py:L388-L395]

| Case | Source and input | Expected value and tolerance | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1: legacy cause extraction | Synthetic five-row DataFrame; legacy import in test module | 5 output records, exact count; incident identifier, primary category and contributing-causes columns present | `tests/modules/marine_safety/analysis/test_cause_analyzer.py::TestIncidentCauseExtractor::test_extract_from_dataframe_basic` | PASS at BASE and AFTER. [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L14-L53] [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L83-L92] |
| R2: empty narrative | `None`, empty string and whitespace string | 0 returned causes for each of 3 inputs, exact count | `tests/modules/marine_safety/analysis/test_cause_analyzer.py::TestExtractCausesFromNarrative::test_extract_causes_empty` | PASS at BASE and AFTER. [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L375-L379] |
| R3: default report filters | `ReportFilters()` | 4 attributes equal `None`, exact identity | `tests/modules/marine_safety/analysis/test_cause_report.py::TestReportFilters::test_filters_initialization_default` | PASS at BASE and AFTER. [tests/modules/marine_safety/analysis/test_cause_report.py:L388-L395] |

Result record: BASE `72716499230d3457ce90a5bcd23a8a8367bc0bd3`; ordinary git-source resolution; `uv run --extra test python -m pytest tests/modules/marine_safety tests/unit/marine_safety tests/marine_safety tests/unit/test_modules_compat.py tests/integration/cli/test_marine_safety_cli.py -q -rA -p no:cacheprovider --basetemp=<scratch>`; 109 selected, 90 passed, 0 failed, 19 skipped, 0 NOT_RUN, with repository addopts preserved; outputs confined to a temporary source copy.

The unit-test directory argument does not establish unit coverage because the existing root hook excludes its descendants; explicit-file results and their limits are recorded separately in section 10. [tests/conftest.py:L662-L680]

## 5. QA gates

Assessment basis: AQG r0, section 10, Python calculations; G5 applies to every family. The checks below define executable acceptance criteria; recording a failed baseline check does not qualify the affected interface.

| Gate | Applicability | Module-specific check IDs |
| --- | --- | --- |
| G0 | Applicable: import identifiers, exported symbols and cited interface contracts | C0, C1 |
| G1 | Applicable: Python imports and offline tests; no program model is generated by the compatibility files | C2, C3, C4. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20] |
| G2 | Applicable: independent hand construction of canonical import paths and module-identity comparison; no engineering calculation exists here | C5. [src/worldenergydata/_compat.py:L95-L104] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] |
| G3 | NOT_APPLICABLE: the files contain no time integration or dynamic solver inputs | [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20] |
| G4 | NOT_APPLICABLE: no mesh, hydrostatic integration or hydrodynamic result is produced | [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] |
| G5 | Applicable: pinned sources, test evidence and limitations accompany this interface assessment | C6 |

| ID | Executable check | Numeric pass criterion and unit | Evidence and current result | Gate |
| --- | --- | --- | --- | --- |
| C0 | Parse all package `.py` files with `ast.parse`; count classes, functions, file I/O and numeric conversion calls independently of docstrings | 5 parseable files; 0 class/function definitions and 0 direct file I/O or numeric conversion calls, counts | Syntax-tree inventory; PASS. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20] | G0 |
| C1 | Extract each literal subordinate `__all__` with `ast.literal_eval`; use `hasattr(importlib.import_module(legacy_name), symbol)` for every declaration | 14 declarations checked; 0 missing symbols, counts | 14 checked, 2 missing: baseline FAIL, issue pending (1). [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L27-L36] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/__init__.py:L9-L56] | G0 |
| C2 | Run the section-4 pytest command with unchanged repository configuration | 0 failed nodes and 0 collection errors, counts; report all skips separately | BASE and AFTER: 90 PASS, 19 SKIP. [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L14-L22] [tests/modules/marine_safety/test_models.py:L73-L78] | G1 |
| C3 | Compare discovered `test_*.py` files under `tests/unit/marine_safety` with files represented in collected node IDs; target those files explicitly with importlib collection | 0 discovered files absent from collection, files; 0 collection errors, errors | Directory traversal excludes the unit tree; explicit files expose baseline collection and assertion failures; #1239 and #327. [tests/conftest.py:L662-L680] [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L11-L14] | G1 |
| C4 | Run R1, R2 and R3 through the full offline command | 3 passing example nodes; 0 failures, counts | BASE and AFTER: 3 PASS. [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L83-L92] [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L375-L379] [tests/modules/marine_safety/analysis/test_cause_report.py:L388-L395] | G1 |
| C5 | Hand-list suffixes: empty, `.analysis`, `.analysis.incidents`, `.importers`, `.processors`; for each compare `import_module('worldenergydata.modules.marine_safety'+suffix) is import_module('worldenergydata.marine_safety'+suffix)` | 5 successful imports and 5 identical object pairs; 0 mismatches, counts | BASE: 5/5 identical; PASS; source-derived oracle is the explicit legacy/canonical path pair, not an incident statistic. [src/worldenergydata/_compat.py:L68-L73] [src/worldenergydata/_compat.py:L95-L104] | G2 |
| C6 | Resolve every source citation at the header pin; match each example node to pytest output; retain all unresolved qualifications in section 10 | 0 invalid citation ranges, 0 examples without node results, 0 untracked qualifications, counts | Citation resolver and acceptance record; independent clearance pending | G5 |

Check definitions: G0 = 2; G1 = 3; G2 = 1; G3 = 0; G4 = 0; G5 = 1; total = 7.

## 6. Known failure modes and pitfalls

sweep: 0 found

Sweep scope: all five `.py` files in the header package, including every subdirectory; their executable statements are imports and export declarations. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20]

Exact sweep command, followed by manual inspection of every package file for unit assumptions and empty-result cache writes:

```bash
rg --files src/worldenergydata/modules/marine_safety -g '*.py' -0 | xargs -0 rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|0\.05|\b(int|float)\(|cache|units?|degrees?|meters?|feet'
```

No local swallowing handler, skipped record, error-return sentinel, numeric default, external-text numeric conversion, unit assumption or empty-result cache write was found; shared-helper and test-infrastructure findings below are outside that five-file sweep. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20]

| Symptom | Cause at code pin | Detection check | Issue and date |
| --- | --- | --- | --- |
| An excluded test directory can leave the suite green without running its checks | Root collection hook returns `True` for descendants of `tests/unit/marine_safety` | C3; baseline finding, not coverage evidence | #1239, 2026-10-16. [tests/conftest.py:L662-L680] |
| Legacy analysis export declarations overstate the runtime namespace | Finder selects the canonical analysis initializer, which does not bind the two report symbols declared in the compatibility file | C1 detects 2 missing declarations; direct import from `worldenergydata.marine_safety.analysis.cause_report` is the tested route | issue pending (1), 2026-10-16. [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L16] [src/worldenergydata/_compat.py:L103-L123] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/__init__.py:L9-L56] [tests/modules/marine_safety/analysis/test_cause_report.py:L12-L15] |
| Finder can decline a target after an internal resolution error | Shared `find_spec()` catches `ModuleNotFoundError` and `ValueError`, substitutes `None`, then returns no spec; later import machinery decides the outcome | no detection check exists for the swallowed cause; C5 checks only available targets | issue pending (1), 2026-10-16. [src/worldenergydata/_compat.py:L106-L116] |
| A closed compatibility incident does not prove every old import surface works | #278's plan distinguishes healthy canonical marine-safety packages from deleted implementations in another domain | C5 covers the five package aliases; C1 covers declared symbols | #278, 2026-10-16. [docs/plans/2026-05-04-issue-278-compatibility-shims.md:L15-L19] [docs/plans/2026-05-04-issue-278-compatibility-shims.md:L30-L35] |
| Canonical-package tests fail, error or skip | Database fixtures, unavailable classifier inputs, logging assertions, a test-local matching oracle, and scraper/validator API expectations belong to the [canonical marine-safety pack](../../../../../packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs/agent-pack.md) (#1236), section 6 and section 10 C4–C10 | C2 and C3 record outcomes; no detection check exists for skipped assertions or unavailable model results | Tracked there: database skips / its draft 1; C4 / its draft 3; C5 / its draft 4; C6 / its draft 5; C9 / its draft 7 (including integration skips); C10 / its draft 8. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs/agent-pack.md:L198-L211] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs/agent-pack.md:L293-L299] |
| One hatch-analysis test imports a nonexistent fixture namespace | Test imports the historical fixture path; the fixture source is under the unit-test tree | C3 records collection errors; no module code correction is included | #327, 2026-10-16. [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L11-L14] [docs/plans/2026-05-04-issue-327-conftest-marine-safety-fix.md:L9-L17] |

## 7. Lessons log

| Date | Entry | Lesson | Evidence | Pack change | Shared-log reference |
| --- | --- | --- | --- | --- | --- |
| 2026-10-16 | Initial compatibility assessment | Inspect the active import finder before treating a surviving initializer's declarations as the runtime namespace | [src/worldenergydata/_compat.py:L103-L123] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/__init__.py:L9-L56] | C1 and section-6 export mismatch | issue pending (1) |
| 2026-10-16 | Initial compatibility assessment | Compare discovered files with collection; a green directory run can omit unit tests | [tests/conftest.py:L662-L680] | C3 and explicit-file evidence | #1239 |

## 8. Ownership

| Responsibility | Assigned role or route |
| --- | --- |
| Required family assessment | Calculations quality manager; data-pipeline specialization remains unassigned |
| Deputy | Data-pipeline quality manager when appointed |
| Production | Module documentation and implementation maintainers |
| Compatibility interpretation, tolerance changes or missing evidence | Family quality manager; cross-family conflicts go to the maintainers |
| Clearance | Independent provider; current status remains DRAFT |

These are the assessment responsibilities for this pack, not a record of completed review or approval.

## 9. Dependencies and implementation inventory

| Relationship | Interface or dependency | Evidence |
| --- | --- | --- |
| Upstream import machinery | Namespace extension and redirect installation in the root distribution | [src/worldenergydata/__init__.py:L59-L65] |
| Upstream canonical implementation | Workspace package `worldenergydata.marine_safety`; its distribution contributes the domain namespace | [packages/worldenergydata-marine_safety/pyproject.toml:L55-L67] |
| Export targets | Report filters, descriptive statistics, incident analyzer, importer and processor classes | [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L8-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L7-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L8-L20] |
| Downstream legacy callers | Cause extraction tests import the old analysis and constants names; model tests import the old database path | [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L14-L22] [tests/modules/marine_safety/test_models.py:L15-L23] |
| Detailed data and algorithm qualification | Separate canonical-package pack; this boundary has no direct dataset or solver-version setting | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs/agent-pack.md:L14-L26] [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] |

### Implementation-map audit record

| Audit field | Value |
| --- | --- |
| Map repository | `digitalmodel` |
| Map file and branch | `docs/registry/implementation-map.yaml`, `codex/implmap-work` |
| Map commit read | `3256bab95f84da3d9fadce8d5dcf8458d66d1eb4` |
| Data revision named by the map | `270c8759c374b67a7f032953e7fcdb14e0224461` |
| Package prefix tested | `src/worldenergydata/modules/marine_safety/` |
| In-package implementation rows | 0 |
| Module map families and inventory | Empty; 0 families, 0 implementations |
| Counted families | 0; ranking and signal selection have no members |
| A8 inventory result | PASS, empty inventory |
| A8 counted-family grep | NOT_APPLICABLE: no map family has an implementation row in the header package |
| Further second implementations counted | 0 |
| Map follow-up | Legacy import dispatch, wildcard export and explicit export, the method families of section 3; issue pending (4) |

The audit above records a map revision from a separate repository, not an implementation census of the canonical data pipeline. Reproduction: parse that pinned YAML, select families having at least one implementation `path` below the header package, retain every implementation row for those families, and rank by in-package row count with map order as the tie-breaker; the empty selection requires no `search_signals` grep.

Repository-wide discovery for the same interface uses `rg -n --glob '*.py' 'worldenergydata\.modules\.marine_safety|worldenergydata\.marine_safety' src packages scripts tests`; the compatibility files delegate to the canonical modules, and the shared finder and attribute shim implement the dispatch rather than a second incident algorithm. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/_compat.py:L60-L73] [src/worldenergydata/modules/__init__.py:L21-L34]

## 10. Coverage and open items

### Coverage record

The two compatibility-specific drafts are committed in [ISSUES_DRAFT.md](ISSUES_DRAFT.md); their numbers remain 1 and 4 to preserve existing references. Canonical-package defects are tracked in its own pack and must not create additional drafts here.

All five package Python files were read in full, including the incident-analysis subdirectory; no subordinate compatibility source is excluded from this pack. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L1-L36] [src/worldenergydata/modules/marine_safety/analysis/incidents/__init__.py:L1-L14] [src/worldenergydata/modules/marine_safety/importers/__init__.py:L1-L13] [src/worldenergydata/modules/marine_safety/processors/__init__.py:L1-L20]

Supporting sources read: the shared redirect and attribute shim, canonical export initializers, canonical package metadata, the existing canonical knowledge pack, the compatibility and fixture-repair plans, and the example test assertions cited above. [src/worldenergydata/_compat.py:L1-L142] [src/worldenergydata/modules/__init__.py:L1-L37] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/__init__.py:L1-L56] [docs/plans/2026-05-04-issue-278-compatibility-shims.md:L13-L35] [docs/plans/2026-05-04-issue-327-conftest-marine-safety-fix.md:L7-L46]

| Open item | Required resolution | Responsible role | Tracking |
| --- | --- | --- | --- |
| U1: maturity and compatibility contract | Reconcile declared versus active exports, define compatibility maturity and document the missing-target diagnostic contract | Module maintainer | issue pending (1) |
| U2: wider documentation claims | Reconcile discovered documentation with the separate canonical-package assessment; excerpts establish discovery only, not capability or data qualification | Module maintainer | issue pending (1) |
| Unit-test collection gap | Restore complete discovery and resolve the historical fixture imports; the old repair issue is closed, not evidence of current coverage | Test maintainer | #1239; #327 |
| Canonical-package test outcomes | Resolve database/model fixtures, unconditional skips and assertion/API mismatches in the canonical pack; retain this pack's outcome inventory as evidence | Canonical-package test maintainers | [canonical marine-safety pack](../../../../../packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs/agent-pack.md) (#1236), section 6 and C4–C10; its drafts 1, 3, 4, 5, 7 and 8 |
| Implementation-map follow-up | Register the three section-3 compatibility method families with in-package rows before counting them in a later A8 audit | Registry maintainer | issue pending (4) |

UNVERIFIED: U2 — capability, completeness, worked-example counts and validation claims in the discovered documentation are not accepted as evidence for the compatibility boundary; reconciliation remains issue pending (1).

### Discovered documentation

Discovery command: `rg -l -i 'marine[_-]safety|modules/marine_safety' docs`; matching passages were inspected, and full cross-domain reconciliation remains U2. The following 63 entries record the first matching line at the code pin.

- [docs/AI_USAGE_GUIDELINES.md:L83-L83]

- [docs/CLI.md:L138-L138]

- [docs/IMO_GISIS_DOWNLOAD_SETUP.md:L179-L179]

- [docs/MIGRATION_GUIDE.md:L57-L57]

- [docs/adr/0001-domain-package-split.md:L42-L42]

- [docs/ci/flake8-inventory-2026-04-23.md:L20-L20]

- [docs/data-sources/AVAILABLE_DATA_SOURCES.md:L46-L46]

- [docs/data-sources/DATA_ACQUISITION_GUIDE.md:L42-L42]

- [docs/data-sources/DOWNLOAD_INSTRUCTIONS.md:L35-L35]

- [docs/data-sources/FINAL_DATA_ACQUISITION_SUMMARY.md:L171-L171]

- [docs/data-sources/IMPORT_DEMONSTRATION.md:L186-L186]

- [docs/data-sources/MANUAL_DOWNLOAD_GUIDE.md:L32-L32]

- [docs/data-sources/MANUAL_DOWNLOAD_REQUIRED.md:L38-L38]

- [docs/data-sources/MARINE_SAFETY_IMPORT_STATUS.md:L4-L4]

- [docs/data-sources/PHASE_2_IMPORT_COMPLETE.md:L146-L146]

- [docs/examples/cause_statistics_example.py:L13-L13]

- [docs/examples/hatch_maloperation_analysis_example.py:L9-L9]

- [docs/guides/QUICK_START.md:L60-L60]

- [docs/guides/QUICK_START_MARINE_REPORTS.md:L7-L7]

- [docs/guides/user_prompt.md:L41-L41]

- [docs/marine-safety-data-sources-comprehensive.md:L993-L993]

- [docs/modules/marine_safety/CAUSE_REPORT_MODULE.md:L68-L68]

- [docs/modules/marine_safety/COMMAND_LINE_ANALYSIS.md:L10-L10]

- [docs/modules/marine_safety/COMMAND_LINE_REPORT_SYSTEM_COMPLETE.md:L15-L15]

- [docs/modules/marine_safety/INCIDENT_CAUSE_ANALYSIS_MODULE.md:L87-L87]

- [docs/modules/marine_safety/LLM_DOCUMENTATION_SUMMARY.md:L16-L16]

- [docs/modules/marine_safety/LLM_INTEGRATION_COMPLETE.md:L15-L15]

- [docs/modules/marine_safety/LLM_INTEGRATION_GUIDE.md:L63-L63]

- [docs/modules/marine_safety/analysis/IMPLEMENTATION_SUMMARY.md:L4-L4]

- [docs/modules/marine_safety/analysis/cause_report_summary.md:L17-L17]

- [docs/modules/marine_safety/cause_mapping_reference.md:L481-L481]

- [docs/modules/marine_safety/hatch_maloperation_analysis.md:L138-L138]

- [docs/modules/marine_safety/incident_cause_research.md:L29-L29]

- [docs/modules/report-inventory.csv:L290-L290]

- [docs/modules/repository-architecture.md:L110-L110]

- [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L14-L14]

- [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L14-L14]

- [docs/plans/2026-05-03-issue-376-cross-field-analytics-lt.md:L16-L16]

- [docs/plans/2026-05-04-issue-153-uscg-misle-dataset.md:L6-L6]

- [docs/plans/2026-05-04-issue-278-compatibility-shims.md:L1-L1]

- [docs/plans/2026-05-04-issue-327-conftest-marine-safety-fix.md:L1-L1]

- [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21]

- [docs/plans/2026-05-04-issue-352-cli-smoke-verification.md:L26-L26]

- [docs/plans/2026-05-04-issue-363-hse-query-api.md:L5-L5]

- [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L92-L92]

- [docs/plans/2026-05-12-issue-403-hurricane-mooring-risk-infographic.md:L14-L14]

- [docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md:L18-L18]

- [docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md:L18-L18]

- [docs/plans/README.md:L32-L32]

- [docs/registry/workflows.yaml:L152-L152]

- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L13-L13]

- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L282-L282]

- [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L12]

- [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml:L61-L61]

- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L14-L14]

- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L13-L13]

- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L193-L193]

- [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L68-L68]

- [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L88-L88]

- [docs/reports/cli-smoke-report-2026-05-11.json:L69-L69]

- [docs/reports/cli-smoke-report-2026-05-11.md:L17-L17]

- [docs/reports/data-freshness-scorecard-2026-06-08.md:L15-L15]

- [docs/research/marine_safety_data_sources_verification_report.md:L4-L4]


### Offline test evidence — canonical-package test outcomes, tracked in the canonical pack

All commands use `python -m pytest -q -rA -p no:cacheprovider --basetemp=<scratch>` through ordinary `uv run`, with the existing addopts unchanged, one process and temporary source copies. Source pin for BASE and the uncommitted AFTER tree: `72716499230d3457ce90a5bcd23a8a8367bc0bd3`. Classifier runs install the declared `test` and `llm` extras and set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`; no model download is attempted.

| Command | BASE | AFTER | Limits |
| --- | --- | --- | --- |
| Section-4 command, `--extra test` | 90 passed, 0 failed, 19 skipped, 0 errors | 90 passed, 0 failed, 19 skipped, 0 errors | 109 selected nodes; NOT_RUN 0 selected nodes; unit-directory traversal excluded |
| Explicit unit-file arguments, `--extra test --extra llm`, `--import-mode=importlib --continue-on-collection-errors` | 1958 passed, 35 failed, 18 skipped, 27 errors | 1958 passed, 35 failed, 18 skipped, 27 errors | 2036 selected nodes; 26 setup errors and 1 collection error; NOT_RUN 1 uncollectable file |
| Same explicit unit files, additionally `--runslow --with-llm` | 1958 passed, 35 failed, 17 skipped, 28 errors | 1958 passed, 35 failed, 17 skipped, 28 errors | 2036 selected nodes; 27 setup errors and 1 collection error; NOT_RUN 1 uncollectable file |

Explicit-file argument expansion: `$(rg --files tests/unit/marine_safety -g 'test_*.py' | sort)`. Existing ignore hooks, marks and assertions are retained. `--continue-on-collection-errors` keeps the collection error in the failing result while allowing the remaining nodes to execute. The unavailable model error ends: “We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.” The uncollectable file reports `ModuleNotFoundError: No module named 'tests.modules.marine_safety.fixtures'`.

The explicit-run skip counts include one module-level skip report in addition to skipped test nodes; the collection error is also a file-level report, separate from the 2036 selected test nodes. The recorded failures originate in unchanged source or test files at the pin; source bytes were compared with `origin/main`. No solver is involved in these commands. Model setup errors provide no classification result; database and unconditional integration skips provide no validation result.

### Nonpassing baseline nodes — canonical-package test outcomes, tracked in the canonical pack

The following records preserve every assertion failure and setup/collection error from the original enabled explicit-file command at the code pin. These are canonical-package test outcomes, tracked in the canonical pack, not additional compatibility drafts. Existing skip groups follow the table.

| Outcome | Node or file | Tracking and pinned test definition |
| --- | --- | --- |
| ERROR | `tests/unit/marine_safety/test_hatch_maloperation_analysis.py` | #327. [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L11-L14] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classify_hatch_maloperation_positive` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L144-L153] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classify_hatch_maloperation_negative` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L155-L164] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_confidence_scores_returned` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L166-L173] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_batch_classification` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L175-L188] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classification_determinism` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L190-L199] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_hatch_not_closed` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L214-L228] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_opening_maloperation` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L230-L244] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_engine_room_access_failure` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L246-L260] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_watertight_door_issue` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L262-L276] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_negative_case_no_hatch_incident` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L278-L286] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_empty_text_handling` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L301-L308] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_none_value_handling` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L310-L318] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_whitespace_only_handling` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L320-L325] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_very_long_text_handling` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L327-L333] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_multilingual_text` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L335-L346] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_special_characters_handling` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L348-L358] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_numeric_only_text` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L360-L365] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_batch_processing_faster_than_individual` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L380-L398] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_classification_within_time_limit` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L400-L410] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_batch_throughput` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L412-L424] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_memory_usage_stability` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L427-L452] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_positive_case_accuracy` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L467-L478] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_negative_case_accuracy` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L480-L491] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_confidence_calibration` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L493-L506] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_f1_score_calculation` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L508-L553] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_concurrent_classification` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L568-L579] |
| ERROR | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_error_recovery` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L581-L601] |
| FAILED | `tests/unit/marine_safety/analysis/test_cause_statistics.py::TestStatisticalSummary::test_print_report` | Canonical pack C10 / its draft 8. [tests/unit/marine_safety/analysis/test_cause_statistics.py:L195-L201] |
| FAILED | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_llm_classifier_initialization` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L51-L68] |
| FAILED | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_model_loading_with_cache` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L70-L92] |
| FAILED | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_fallback_on_model_load_failure` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L94-L118] |
| FAILED | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_custom_model_path` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L120-L129] |
| FAILED | `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_repeated_initialization` | Canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_llm_classifier.py:L603-L617] |
| FAILED | `tests/unit/marine_safety/test_correlation.py::TestIncidentMatcherConfidence::test_find_matches_returns_above_threshold` | Canonical pack C6 / its draft 5. [tests/unit/marine_safety/test_correlation.py:L764-L803] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_success` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L78-L86] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_timeout` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L90-L95] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_connection_error` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L99-L104] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_retry_on_failure` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L108-L120] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_max_retries_exceeded` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L124-L132] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_html` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L135-L143] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_empty_html` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L146-L151] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_malformed_html` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L154-L160] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_scrape_incidents_date_range` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L164-L177] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_download_pdf_success` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L185-L195] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_extract_pdf_text` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L210-L221] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_parse_pdf_metadata` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L224-L239] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_http_500_error` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L247-L255] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_invalid_ssl_certificate` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L259-L264] |
| FAILED | `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_network_timeout_recovery` | Canonical pack C4 / its draft 3. [tests/unit/marine_safety/test_uscg_scraper.py:L274-L281] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_valid_incident_data` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L25-L42] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_missing_required_fields` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L45-L57] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_casualties_validation` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L60-L72] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_negative_casualties` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L75-L82] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_severity_type_consistency` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L85-L97] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_location_validation` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L100-L116] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_valid_vessel_data` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L123-L137] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_vessel_name_required` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L140-L147] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_gross_tonnage_positive` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L150-L157] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_year_built_range` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L160-L174] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_pollution_environmental_impact` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L181-L196] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_critical_severity_requires_investigation` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L199-L211] |
| FAILED | `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_vessel_incident_consistency` | Canonical pack C5 / its draft 4. [tests/unit/marine_safety/test_validators.py:L214-L223] |

Skip inventory: the initial directory command skips every test in the four model classes listed below; the enabled explicit-file command skips the entire unit model file and every node in the integration file because those files declare unconditional skips. The initial explicit-file command additionally skips the marked memory test; the enabled command attempts it and records its model setup error. [tests/modules/marine_safety/test_models.py:L73-L78] [tests/modules/marine_safety/test_models.py:L231-L235] [tests/modules/marine_safety/test_models.py:L327-L331] [tests/modules/marine_safety/test_models.py:L387-L390] [tests/unit/marine_safety/test_models.py:L9-L14] [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L554-L558] [tests/unit/marine_safety/analysis/test_llm_classifier.py:L426-L442]

- SKIP: `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_create_incident_minimal`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L81-L97]

- SKIP: `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_create_incident_full`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L100-L125]

- SKIP: `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_incident_date_required`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L128-L139]

- SKIP: `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_vessel_relationship`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L142-L157]

- SKIP: `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_latitude_constraint_valid`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L160-L173]

- SKIP: `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_longitude_constraint_valid`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L176-L189]

- SKIP: `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_created_at_auto_generated`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L192-L206]

- SKIP: `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_updated_at_auto_updated`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L209-L228]

- SKIP: `tests/modules/marine_safety/test_models.py::TestVesselModel::test_create_vessel_minimal`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L239-L249]

- SKIP: `tests/modules/marine_safety/test_models.py::TestVesselModel::test_vessel_company_relationship`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L252-L262]

- SKIP: `tests/modules/marine_safety/test_models.py::TestVesselModel::test_vessel_incidents_relationship`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L265-L286]

- SKIP: `tests/modules/marine_safety/test_models.py::TestVesselModel::test_imo_number_unique`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L289-L310]

- SKIP: `tests/modules/marine_safety/test_models.py::TestVesselModel::test_gross_tonnage_positive`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L313-L324]

- SKIP: `tests/modules/marine_safety/test_models.py::TestCompanyModel::test_create_company_minimal`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L335-L344]

- SKIP: `tests/modules/marine_safety/test_models.py::TestCompanyModel::test_company_vessels_relationship`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L347-L360]

- SKIP: `tests/modules/marine_safety/test_models.py::TestCompanyModel::test_imo_number_unique_company`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L363-L374]

- SKIP: `tests/modules/marine_safety/test_models.py::TestCompanyModel::test_company_active_default`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L377-L384]

- SKIP: `tests/modules/marine_safety/test_models.py::TestEnums::test_incident_type_enum`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L394-L400]

- SKIP: `tests/modules/marine_safety/test_models.py::TestEnums::test_severity_level_enum`; canonical pack section 6 / its draft 1. [tests/modules/marine_safety/test_models.py:L403-L408]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_hatch_analyzer_with_llm_enabled`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L52-L73]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_hatch_analyzer_llm_vs_regex_comparison`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L75-L102]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_hybrid_detection_fallback`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L104-L140]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_llm_confidence_threshold`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L142-L168]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_batch_processing_consistency`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L170-L194]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMPerformanceIntegration::test_large_dataset_processing_time`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L226-L242]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMPerformanceIntegration::test_memory_efficiency_large_dataset`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L244-L270]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMErrorHandling::test_graceful_handling_of_null_narratives`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L301-L317]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMErrorHandling::test_handling_of_malformed_data`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L319-L341]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMErrorHandling::test_partial_llm_failure_handling`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L343-L370]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestAnalysisReportGeneration::test_generate_analysis_report_with_confidence`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L427-L443]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestAnalysisReportGeneration::test_confidence_distribution_in_report`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L445-L457]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestAnalysisReportGeneration::test_temporal_analysis_with_llm_results`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L459-L469]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestConfigurationOptions::test_custom_model_configuration`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L492-L503]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestConfigurationOptions::test_disable_llm_configuration`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L505-L519]

- SKIP: `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestConfigurationOptions::test_batch_size_configuration`; canonical pack C9 / its draft 7. [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L521-L538]

### Discovered test files — canonical-package test outcomes, tracked in the canonical pack

Inventory: 58 test files across the target directories and shared compatibility test; 52 are under the canonical unit-test tree. The directory command selects 109 nodes from the remaining paths; explicit unit-file execution selects 2036 nodes and exposes the collection error separately. Counts are execution and discovery records, not claims of validation.

- [tests/integration/cli/test_marine_safety_cli.py:L1-L1]
- [tests/marine_safety/test_api_on_base.py:L1-L1]
- [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L1-L1]
- [tests/modules/marine_safety/analysis/test_cause_report.py:L1-L1]
- [tests/modules/marine_safety/test_models.py:L1-L1]
- [tests/unit/marine_safety/analysis/incidents/test_hatch_analysis.py:L1-L1]
- [tests/unit/marine_safety/analysis/incidents/test_hatch_patterns.py:L1-L1]
- [tests/unit/marine_safety/analysis/incidents/test_incident_taxonomy.py:L1-L1]
- [tests/unit/marine_safety/analysis/incidents/test_maib_loader.py:L1-L1]
- [tests/unit/marine_safety/analysis/incidents/test_ntsb_marine_loader.py:L1-L1]
- [tests/unit/marine_safety/analysis/test_cause_analyzer.py:L1-L1]
- [tests/unit/marine_safety/analysis/test_cause_report.py:L1-L1]
- [tests/unit/marine_safety/analysis/test_cause_statistics.py:L1-L1]
- [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L1-L1]
- [tests/unit/marine_safety/analysis/test_llm_classifier.py:L1-L1]
- [tests/unit/marine_safety/importers/test_atsb_importer.py:L1-L1]
- [tests/unit/marine_safety/importers/test_boating_importer.py:L1-L1]
- [tests/unit/marine_safety/importers/test_emsa_importer.py:L1-L1]
- [tests/unit/marine_safety/importers/test_imo_importer.py:L1-L1]
- [tests/unit/marine_safety/importers/test_imo_normalizers.py:L1-L1]
- [tests/unit/marine_safety/importers/test_imo_parser.py:L1-L1]
- [tests/unit/marine_safety/importers/test_imo_validators.py:L1-L1]
- [tests/unit/marine_safety/importers/test_maib_importer.py:L1-L1]
- [tests/unit/marine_safety/importers/test_noaa_importer.py:L1-L1]
- [tests/unit/marine_safety/importers/test_ntsb_importer.py:L1-L1]
- [tests/unit/marine_safety/importers/test_tsb_importer.py:L1-L1]
- [tests/unit/marine_safety/processors/test_base_processor.py:L1-L1]
- [tests/unit/marine_safety/processors/test_data_cleaner.py:L1-L1]
- [tests/unit/marine_safety/processors/test_data_normalizer.py:L1-L1]
- [tests/unit/marine_safety/reports/test_quality_dashboard.py:L1-L1]
- [tests/unit/marine_safety/scrapers/test_atsb_checkpoint.py:L1-L1]
- [tests/unit/marine_safety/scrapers/test_atsb_constants.py:L1-L1]
- [tests/unit/marine_safety/scrapers/test_atsb_exceptions.py:L1-L1]
- [tests/unit/marine_safety/scrapers/test_atsb_extractor.py:L1-L1]
- [tests/unit/marine_safety/scrapers/test_atsb_parser.py:L1-L1]
- [tests/unit/marine_safety/scrapers/test_atsb_transformer.py:L1-L1]
- [tests/unit/marine_safety/scrapers/test_atsb_validator.py:L1-L1]
- [tests/unit/marine_safety/scrapers/test_ntsb_scraper.py:L1-L1]
- [tests/unit/marine_safety/test_atsb_importer.py:L1-L1]
- [tests/unit/marine_safety/test_cause_statistics.py:L1-L1]
- [tests/unit/marine_safety/test_cause_visualizations.py:L1-L1]
- [tests/unit/marine_safety/test_cli_commands.py:L1-L1]
- [tests/unit/marine_safety/test_cli_utils.py:L1-L1]
- [tests/unit/marine_safety/test_constants.py:L1-L1]
- [tests/unit/marine_safety/test_correlation.py:L1-L1]
- [tests/unit/marine_safety/test_cross_database.py:L1-L1]
- [tests/unit/marine_safety/test_cross_database_live.py:L1-L1]
- [tests/unit/marine_safety/test_exceptions.py:L1-L1]
- [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L1-L1]
- [tests/unit/marine_safety/test_imo_importer.py:L1-L1]
- [tests/unit/marine_safety/test_models.py:L1-L1]
- [tests/unit/marine_safety/test_ntsb_importer.py:L1-L1]
- [tests/unit/marine_safety/test_refresh_cli.py:L1-L1]
- [tests/unit/marine_safety/test_report_verification.py:L1-L1]
- [tests/unit/marine_safety/test_uscg_scraper.py:L1-L1]
- [tests/unit/marine_safety/test_validators.py:L1-L1]
- [tests/unit/marine_safety/utils/test_validators.py:L1-L1]
- [tests/unit/test_modules_compat.py:L1-L1]


Supplemental dependency-contract check: `uv run --extra test --extra llm python -m pytest tests/contracts -q -rA -p no:cacheprovider --basetemp=<scratch>` on the uncommitted tree at the same source pin; 46 passed, 0 failed, 0 skipped, 0 errors, NOT_RUN 0. No routing registry exists at the requested path, so no routing entry is added.
