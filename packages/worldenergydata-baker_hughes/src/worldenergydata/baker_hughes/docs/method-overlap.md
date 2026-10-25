# Proposed rig-count method coverage

Summary: issue #1337 proposes explicit family rows for the package loaders and
reporting, the independent workbook downloads, and their export caller. These
are proposed rows, not registered coverage. The external implementation registry
is unchanged. Counts below enumerate the explicit definitions in this page;
they do not count unrelated functions with similar names.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-25 | Proposed explicit method families and an executable inventory to separate package methods from the independent download and export path for #1337. |

## Inspection basis

- Map-proposal revision: **1**, introduced by the revision-history entry above.
- Inspected source revision: `5e6df17dfff3faffb66540e40b8683d1139e8395`.
- Boundary: `packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/`.
- Evidence: [loader source][loader], [report source][report],
  [collector source][collector] and [export caller][export] at that revision,
  read without importing collectors or executing downloads.

The [knowledge pack](agent-pack.md) retains the historical registry evidence in
section 9. This proposal does not refresh that external registry snapshot or
claim current registered-family counts.

## Proposed family rows

Each row proposes a distinct family with the qualified definition shown. The
classification describes delegation at the inspected revision, based on the
linked source bodies; the AST example establishes definition presence only.

| Proposed family | Boundary | Qualified symbol | Delegation classification and source |
| --- | --- | --- | --- |
| Pivot ingestion | Inside package | `worldenergydata.baker_hughes.loader.load_pivot_table` | Implementation: reads a supplied workbook, renames/coerces fields and filters rows; does not call the summary loader. [loader.py, definition at line 36][loader] |
| Summary ingestion | Inside package | `worldenergydata.baker_hughes.loader.load_summary` | Implementation: reads a supplied workbook and melts state/date columns; does not call the pivot loader. [loader.py, definition at line 75][loader-summary] |
| Ingestion reporting | Inside package | `worldenergydata.baker_hughes.report.generate_report` | Implementation: aggregates a supplied DataFrame and assesses date completeness; does not call a loader or download data. [report.py, definition at line 11][report] |
| North American workbook download | Outside package | `worldenergydata.vessel_fleet.collectors.baker_hughes_collector.BakerHughesCollector.download_na_rig_count` | Independent implementation: calls inherited `get_bytes` and its own `pd.read_excel`, without either package loader. [collector, definition at line 38][collector] |
| International workbook download | Outside package | `worldenergydata.vessel_fleet.collectors.baker_hughes_collector.BakerHughesCollector.download_international_rig_count` | Independent implementation: calls inherited `get_bytes` and its own `pd.read_excel`, without either package loader or the North American download method. [collector, definition at line 57][collector-international] |
| Rig-count export orchestration | Outside package | `scripts.vessel_fleet.enrich_from_government.main` | Caller: delegates downloads to the collector and nonempty-result storage to `ParquetStore.save`; no delegation to the package loaders or report. Only its rig-count branches are proposed here. [main, definition at line 28; branches at lines 44–69][export] |

The collector and export caller do **not** delegate to `load_pivot_table` or
`load_summary`. Sharing `pd.read_excel` establishes a common library dependency,
not delegation to a common rig-count implementation. The downloads return raw
parsed workbook frames rather than the standardized loader outputs.
`generate_report` hits elsewhere do not establish duplicate rig-count methods.

## Separate counts

These are hand enumerations of the qualified symbols in the table above and
are checked by the executable inventory and its test. Each proposed row has a
single named definition; the export row counts a caller, not another download
implementation. Package re-exports, collector construction and `collect` are
outside this explicit inventory.

| Boundary | Proposed families | Implementation definitions | Caller definitions | Total named definitions |
| --- | --- | --- | --- | --- |
| Inside package | 3 | 3 | 0 | 3 |
| Outside package | 3 | 2 | 1 | 3 |

Count basis: inside is two loaders plus one report; outside is two independent
downloads plus one export caller, as explicitly enumerated for #1337 above.
There is no combined registered-coverage total.

## Offline AST inventory

Run the following Python example from the repository root. It uses only the
standard library, reads the explicit source files, and never imports a package
or collector. It selects module functions and class-qualified methods by exact
name, requires a unique matching definition, and prints JSON containing the
qualified symbols, repository-relative paths, current line numbers and separate
boundary/role counts. It does not search for arbitrary report-name matches.

```python
import ast
import json
from pathlib import Path

PACKAGE = "packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes"
SOURCES = (
    (
        "inside-package",
        "worldenergydata.baker_hughes.loader",
        f"{PACKAGE}/loader.py",
        (("load_pivot_table", "implementation"), ("load_summary", "implementation")),
    ),
    (
        "inside-package",
        "worldenergydata.baker_hughes.report",
        f"{PACKAGE}/report.py",
        (("generate_report", "implementation"),),
    ),
    (
        "outside-package",
        "worldenergydata.vessel_fleet.collectors.baker_hughes_collector",
        "packages/worldenergydata-vessel_fleet/src/worldenergydata/"
        "vessel_fleet/collectors/baker_hughes_collector.py",
        (
            ("BakerHughesCollector.download_na_rig_count", "implementation"),
            ("BakerHughesCollector.download_international_rig_count", "implementation"),
        ),
    ),
    (
        "outside-package",
        "scripts.vessel_fleet.enrich_from_government",
        "scripts/vessel_fleet/enrich_from_government.py",
        (("main", "caller"),),
    ),
)


def definitions(body, parents=()):
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield ".".join((*parents, node.name)), node
        elif isinstance(node, ast.ClassDef):
            yield from definitions(node.body, (*parents, node.name))


# Zero initializes direct enumeration; each proposed symbol must occur once.
counts = {
    boundary: {"implementation": 0, "caller": 0}
    for boundary in ("inside-package", "outside-package")
}
rows = []
for boundary, module, path, targets in SOURCES:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    found = list(definitions(tree.body))
    for target, role in targets:
        matches = [node for name, node in found if name == target]
        if len(matches) != 1:
            raise ValueError(f"{module}.{target}: expected one definition")
        (node,) = matches
        rows.append(
            {
                "symbol": f"{module}.{target}",
                "path": path,
                "line": node.lineno,
                "boundary": boundary,
                "role": role,
            }
        )
        counts[boundary][role] += 1

print(json.dumps({"definitions": rows, "counts": counts}, indent=2))
```

To execute that exact block without maintaining a separate script:

```bash
python - <<'PY'
import re
from pathlib import Path

page = Path(
    "packages/worldenergydata-baker_hughes/src/worldenergydata/"
    "baker_hughes/docs/method-overlap.md"
)
(example,) = re.findall(r"```python\n(.*?)\n```", page.read_text(encoding="utf-8"), re.S)
exec(compile(example, "method-overlap example", "exec"))
PY
```

The regression test at `tests/unit/baker_hughes/test_method_inventory.py`
extracts and executes that exact Python block with isolated Python and site
packages disabled. Its expected symbols come from #1337 and the explicit table,
and its expected counts use the hand enumeration above. It also adds an
unrelated `generate_report` in a temporary source tree to demonstrate that such
a hit neither changes the inventory nor replaces a missing named definition.

## Retained limitations

- **Collector empty-on-error is retained, not fixed.** Both download methods
  catch `Exception`, log a warning and return an empty DataFrame. Download and
  parsing failures therefore have the same return shape as a valid empty
  workbook. See [North American error handling][collector-error] and
  [international error handling][collector-international-error].
- **Export-skips-empty is retained, not fixed.** The rig-count branches of
  `main` save only when the returned frame is nonempty. A failed download that
  returns empty produces no new export and no structured failure result;
  existing exports are not cleared. Exceptions are logged and `main` still
  returns success. See [export branches and return][export-branches].
- This documents the inspected call relationships. The AST inventory checks
  definition existence, qualification and counts, not runtime behavior, workbook
  validity, network availability or equivalence between implementations.
- Registry integration remains a separate maintainer action. No production,
  download, cache or external registry behavior changes here.

[loader]: ../loader.py#L36
[loader-summary]: ../loader.py#L75
[report]: ../report.py#L11
[collector]: ../../../../../../packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/baker_hughes_collector.py#L38
[collector-international]: ../../../../../../packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/baker_hughes_collector.py#L57
[collector-error]: ../../../../../../packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/baker_hughes_collector.py#L53
[collector-international-error]: ../../../../../../packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/baker_hughes_collector.py#L72
[export]: ../../../../../../scripts/vessel_fleet/enrich_from_government.py#L28
[export-branches]: ../../../../../../scripts/vessel_fleet/enrich_from_government.py#L44
