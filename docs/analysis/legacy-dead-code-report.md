# Legacy caller analysis

## Summary

The original component class has no tracked caller. The wellpath module retains
its executable GUI entry point and compatibility exports. These findings identify
candidates for a compatibility review; no runtime code is removed.
The inventory covers 58 symbols: 6 DEAD candidates, 40 MIGRATED exports and
12 LIVE bindings, using the repository-scoped definitions below.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Record static caller evidence before considering legacy deletion. |

## Scope and evidence basis

Refs #1108. Source revision: `648d6de46081ad98a06504a25ec8a222acbd41b1`.
The current source lives in
`packages/worldenergydata-core/src/worldenergydata/common/legacy/`, rather than
in the old root-package location named by the issue. The report lives under
`docs/analysis/` because `specs/` is absent from the permitted roots in
[the repository structure contract](../../config/repo_structure.yml).

The inventory covers direct module-level classes, functions, data assignments,
and imports explicitly listed in literal `__all__`. Dependency imports and the
`__all__` metadata binding are excluded. Methods and nested callbacks belong to
their containing class/function span. Bindings inside the guarded entry point
are executable entry-point state, not direct module-body declarations.

Classification is repository-scoped:

- **DEAD**: a local definition or data binding with no observed consumer of that
  binding in the tracked repository. This is a deletion candidate, not a claim
  about external installations, plugins, or dynamic access.
- **MIGRATED**: an explicit public reexport whose import origin is a separate
  source module. A same-named replacement class does not make the old class a
  reexport.
- **LIVE**: a local name read by code in the source, including callbacks,
  annotations and the guarded entry point. This is conservative syntactic use,
  not proof that every branch executes. Uses confined to a DEAD class are stated
  separately.

The inventory parses source with `ast`; it never imports the legacy modules,
opens databases or starts the GUI. Name loads deliberately overestimate liveness:
they do not resolve lexical shadowing or perform whole-program reachability.
External caller evidence comes from the separate tracked-text sweep below;
absence of local loads alone does not prove DEAD.

## `ong_fd_components.py`

Source: [original component module](../../packages/worldenergydata-core/src/worldenergydata/common/legacy/ong_fd_components.py).

| Symbol | Status | Definition lines | Evidence |
| --- | --- | --- | --- |
| `logger` | LIVE | 19 | Read only inside the candidate class: 127, 131, 161, 224, 248, 1443. |
| `dtu` | LIVE | 21 | Read only inside the candidate class: 259. |
| `ONGFDComponents` | DEAD | 24-1656 | No tracked caller; the package exports a distinct replacement. |

## `wellpath3D.py`

Source: [wellpath compatibility and GUI module](../../packages/worldenergydata-core/src/worldenergydata/common/legacy/wellpath3D.py).
For MIGRATED rows the final column gives the defining module; import spans are
shown, not the length of the imported implementation. All such origins remain
under the same legacy package and are checked against actual source bindings.

| Symbol | Status | Definition or import lines | Evidence or origin |
| --- | --- | --- | --- |
| `calculate_geographic_position` | MIGRATED | 34-38 | `wellpath_coordinates` |
| `east2lon` | MIGRATED | 34-38 | `wellpath_coordinates` |
| `north2lat` | MIGRATED | 34-38 | `wellpath_coordinates` |
| `delete_stratigraphy_point` | MIGRATED | 41-59 | `wellpath_database` |
| `delete_survey_point` | MIGRATED | 41-59 | `wellpath_database` |
| `delete_well` | MIGRATED | 41-59 | `wellpath_database` |
| `first_start` | MIGRATED | 41-59 | `wellpath_database` |
| `get_formation_color` | MIGRATED | 41-59 | `wellpath_database` |
| `get_well_surface_data` | MIGRATED | 41-59 | `wellpath_database` |
| `import_csv_survey` | MIGRATED | 41-59 | `wellpath_database` |
| `load_all_wells` | MIGRATED | 41-59 | `wellpath_database` |
| `load_formation_list` | MIGRATED | 41-59 | `wellpath_database` |
| `load_stratigraphy_data` | MIGRATED | 41-59 | `wellpath_database` |
| `load_stratigraphy_dataframe` | MIGRATED | 41-59 | `wellpath_database` |
| `load_survey_data` | MIGRATED | 41-59 | `wellpath_database` |
| `load_survey_dataframe` | MIGRATED | 41-59 | `wellpath_database` |
| `load_well_names` | MIGRATED | 41-59 | `wellpath_database` |
| `write_stratigraphy_point` | MIGRATED | 41-59 | `wellpath_database` |
| `write_survey_point` | MIGRATED | 41-59 | `wellpath_database` |
| `write_wellmap_point` | MIGRATED | 41-59 | `wellpath_database` |
| `NewWell` | MIGRATED | 62-69 | `wellpath_models` |
| `StratigraphyMarker` | MIGRATED | 62-69 | `wellpath_models` |
| `SurveyData` | MIGRATED | 62-69 | `wellpath_models` |
| `Well` | MIGRATED | 62-69 | `wellpath_models` |
| `WellMap` | MIGRATED | 62-69 | `wellpath_models` |
| `WellSurface` | MIGRATED | 62-69 | `wellpath_models` |
| `SurveyPoint` | MIGRATED | 72-80 | `wellpath_trajectory` |
| `TrajectoryResult` | MIGRATED | 72-80 | `wellpath_trajectory` |
| `calculate_dogleg` | MIGRATED | 72-80 | `wellpath_trajectory` |
| `calculate_dogleg_severity` | MIGRATED | 72-80 | `wellpath_trajectory` |
| `calculate_minimum_curvature` | MIGRATED | 72-80 | `wellpath_trajectory` |
| `calculate_ratio_factor` | MIGRATED | 72-80 | `wellpath_trajectory` |
| `interpolate_survey_point` | MIGRATED | 72-80 | `wellpath_trajectory` |
| `COLOR_PALETTE` | MIGRATED | 83-91 | `wellpath_visualization` |
| `DEFAULT_COLOR` | MIGRATED | 83-91 | `wellpath_visualization` |
| `create_formation_plane` | MIGRATED | 83-91 | `wellpath_visualization` |
| `create_wellsite_polygon` | MIGRATED | 83-91 | `wellpath_visualization` |
| `get_color_from_index` | MIGRATED | 83-91 | `wellpath_visualization` |
| `plot_multiple_wells` | MIGRATED | 83-91 | `wellpath_visualization` |
| `plot_single_well` | MIGRATED | 83-91 | `wellpath_visualization` |
| `logger` | LIVE | 94 | Local reads: 1249. |
| `instantTab` | DEAD | 98-100 | No executable read; retained in the public export list. |
| `base` | LIVE | 104 | Local reads: 418, 959, 963, 1037, 1041. |
| `wellnames_given` | LIVE | 105 | Local reads: 120, 129. |
| `wellactual` | LIVE | 106 | Local reads: 313, 378, 428, 431, 466, 469, 522, 525, 659, 663, 956, 1001, 1004, 1015, 1018, 1099, 1102. |
| `wells_plot` | DEAD | 107 | No executable read; retained in the public export list. |
| `fmtop` | DEAD | 108 | No executable read; retained in the public export list. |
| `wellnamelist` | DEAD | 109 | No executable read; retained in the public export list. |
| `wells_selected` | DEAD | 110 | No executable read; retained in the public export list. |
| `well_objects` | LIVE | 111 | Local reads: 820, 824, 828. |
| `firstStart` | LIVE | 114-120 | Local reads: 1243. |
| `newwell` | LIVE | 124-129 | Local reads: 235. |
| `well` | LIVE | 132-135 | Local reads: 311. |
| `wellmap` | LIVE | 138-141 | Local reads: 823. |
| `myApplication` | LIVE | 144-1172 | Local reads: 1246. |

## Caller sweep and false-positive checks

The following searches cover all tracked, non-binary repository text, including
Python, configuration, notebooks, documentation and test-generation metadata.
They do not depend on a hard-coded source-directory list. The two audited source
files are excluded only from the module-name search, to expose external sites.
The new audit script, tests and this report are evidence rather than consumers.

```sh
git grep -n -I -w -e ong_fd_components -e wellpath3D -- \
  ':!packages/worldenergydata-core/src/worldenergydata/common/legacy/ong_fd_components.py' \
  ':!packages/worldenergydata-core/src/worldenergydata/common/legacy/wellpath3D.py' \
  ':!scripts/analysis/legacy_symbol_inventory.py' \
  ':!tests/analysis/test_legacy_symbol_inventory.py' \
  ':!docs/analysis/legacy-dead-code-report.md'
git grep -n -I -w -e ONGFDComponents -e instantTab -e wells_plot \
  -e fmtop -e wellnamelist -e wells_selected -- \
  ':!scripts/analysis/legacy_symbol_inventory.py' \
  ':!tests/analysis/test_legacy_symbol_inventory.py' \
  ':!docs/analysis/legacy-dead-code-report.md'
```

Every external match was inspected:

| Matching source | Interpretation |
| --- | --- |
| `common/legacy/__init__.py`:7,63 | Imports and exports the class from `ong_fd_components_refactored`, not the original file. |
| `common/legacy/ong_fd_components_refactored.py`:3,59,71 | Documentation and declaration of the distinct replacement. |
| `bsee/analysis/war_rig_days.py`:361,404,433 | Docstrings describing ported behavior; no import of the original class. |
| `bsee/analysis/production_api10.py`:33 | Comment describing a ported production loop. |
| `tests/unit/bsee/analysis/test_war_rig_days_phases.py`:1 | Test docstring describing ported behavior. |
| `common/legacy/wellpath_database.py`:85,91,93 | Function-local `wellnamelist`, distinct from the unused wellpath module global. |
| `tests/ai_test_generation/strategies/ong_fd_components_strategy.json`:2,7 | Planned module/class test metadata; no runnable caller. |
| `tests/ai_test_generation/strategies/wellpath3D_strategy.json`:2,249,254 | Planned module/function test metadata, including `instantTab`; not a caller. |
| `tests/ai_test_generation/report.txt`:17,19 | Historical source-file inventory. |
| `docs/ci/flake8-inventory-2026-04-23.md`:92,96 | Historical lint inventory. |
| `docs/data-sources/bsee/analysis/survey/survey.md`:12 | Historical source link. |
| `docs/plans/2026-05-04-issue-326-prepare-production-data-missing.md`:57 | Comment in an example of the production port. |
| `drilling_pressure_management/docs/agent-pack.md`:180 | Source citation for a legacy calculation. |
| `well_bore_design/docs/agent-pack.md`:284 | Source citations comparing related legacy calculations. |

Package-relative source names in this table abbreviate the corresponding
`packages/worldenergydata-<domain>/src/worldenergydata/` prefix. The package
initializer and replacement class were read directly: resolving a name through
`common.legacy` does not resolve to the original component class.

Within wellpath, the guarded entry point calls `firstStart` and `myApplication`
at lines 1243 and 1246. GUI code instantiates `newwell`, `well` and `wellmap` at
lines 235, 311 and 823. Those wrappers are LIVE even though their underlying model
classes are MIGRATED. The unused exported names are candidates only; their public
export listing and test-generation metadata must be considered before removal.

## Candidate deletion estimate

The arithmetic is defined here and implemented in `covered_lines`: take the union
of inclusive physical source spans of DEAD local symbols, divide its size by the
file's physical line count, and express as a percentage. Blank lines outside the
spans, dependency imports, reexport imports and export-list entries are excluded.
The whole candidate class includes its methods; those methods are not counted
again. This is a source-size estimate, not an approved deletion amount.

| File | Candidate lines | Physical lines | Candidate percentage |
| --- | --- | --- | --- |
| `ong_fd_components.py` | 1633 | 1656 | 98.6% |
| `wellpath3D.py` | 7 | 1249 | 0.6% |

Independent arithmetic: the class spans lines 24 through 1656 inclusive, so its
size is 1656 minus 24 plus 1 = 1633 lines. The unused wellpath function spans
98 through 100 inclusive, contributing 3 lines, and the four unused global
assignments contribute one line each: 3 + 4 = 7. Percentages are rounded to one
decimal place. Denominators are measured from the source files, not the issue's
historical line counts. No engineering constants or acceptance limits are used.

## Reproduction and tests

```sh
uv run --no-project python scripts/analysis/legacy_symbol_inventory.py
uv run --no-project --with pytest python -m pytest \
  tests/analysis/test_legacy_symbol_inventory.py --noconftest -c /dev/null \
  -q -rA -p no:cacheprovider
```

Direct the test temporary directory and tool caches to a writable scratch folder.
All 13 isolated tests pass; they require only pytest and the standard library.
They exercise
inert parsing, module-scope boundaries, callback/entry-point references, distinct
reexport identity, explicit export validation, decorators and source-span union.
They also resolve migrated exports to actual source bindings and compare every
report row and percentage with the current source. An independent tracked-Python
search guards against new direct, relative or aliased legacy-module imports and
literal dynamic module references. Expected fixture line numbers
come from the literal source strings in the tests; the union example is worked
out independently in its test docstring. Runtime legacy modules are unchanged.

## Later slices and limits

- A compatibility review is warranted for the original component class: its
  candidate share exceeds the follow-up threshold stated in #1108. Confirm
  external consumers and decide whether a deprecation or forwarding shim is
  required. The package replacement's import alone does not prove behavioral
  equivalence, and its behavior has not been compared here.
- Separately review the unused wellpath exports. Preserve the GUI entry point,
  callbacks and all migrated exports unless their public compatibility contract
  is intentionally changed.
- Deletion implementation and new tracking issues are deferred. No issue is
  created by this change. The linked well-design discussion supplies no caller
  evidence; the historical split reference did not resolve to a separate issue
  in the repository issue search.
- Dynamic import strings assembled at runtime, untracked local scripts and
  external consumers are NOT_EVALUATED. Explicit reexports are protected even
  when no in-repository direct caller uses them. A repository text sweep cannot
  establish global deadness.
