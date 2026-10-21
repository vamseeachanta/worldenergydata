"""Architecture observations checked against independently inspected source data.

Counts are enumerations, not engineering acceptance limits. Expected coverage is
the HTML file set, the CSV category tally and the literal work-specification set;
none is obtained by calling the inventory classifier or a report generator.
"""

import ast
import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = ROOT / "docs/modules/repository-architecture.md"


def test_report_observation_matches_tree_and_csv():
    """Hand tally: one CSV row per HTML path; category totals sum to that set."""
    with (ROOT / "docs/modules/report-inventory.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    paths = {p.relative_to(ROOT).as_posix() for p in (ROOT / "reports").rglob("*.html")}
    assert len(rows) == len(paths)
    assert {row["path"] for row in rows} == paths
    counts = Counter(row["classification"] for row in rows)
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert f"**{len(paths)} report HTML files" in text
    table = dict(
        re.findall(
            r"^\| (current|superseded|unverified|one-off|undetermined) \| (\d+) \|$",
            text,
            re.MULTILINE,
        )
    )
    assert {key: int(value) for key, value in table.items()} == {
        key: counts[key]
        for key in ("current", "superseded", "unverified", "one-off", "undetermined")
    }


def test_readme_embeds_canonical_mermaid():
    """The README and detailed page shall show the same repository drawing."""
    pattern = r"```mermaid\n(flowchart TB\n.*?)\n```"
    drawing = re.search(pattern, ARCHITECTURE.read_text(encoding="utf-8"), re.DOTALL)
    assert drawing is not None
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert drawing.group(0) in readme
    for label in ("BSEE", "IMO GISIS", "Texas RRC", "WED_DATA_ROOT", "LFS"):
        assert label in drawing.group(1)


def test_work_specs_have_one_provenance_row_and_drawn_node():
    """Each literal work ID maps once to a node; economics uses one shared node."""
    source = ROOT / "scripts/capabilities/build_onepagers.py"
    source_text = source.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    specification = next(
        node.value
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "SPECS"
    )
    specs = [
        {
            ast.literal_eval(key): ast.literal_eval(value)
            for key, value in zip(row.keys, row.values)
            if isinstance(key, ast.Constant) and key.value in {"id", "kind", "std"}
        }
        for row in specification.elts
    ]
    expected = {spec["id"] for spec in specs if spec["kind"] == "work"}
    work_specs = {
        spec["id"]: (spec, row)
        for spec, row in zip(specs, specification.elts)
        if spec["kind"] == "work"
    }
    text = ARCHITECTURE.read_text(encoding="utf-8")
    section = text.split("## Capability inventory and provenance\n")[1].split("\n## ")[
        0
    ]
    observed = []
    economics_nodes = set()
    for node, identifiers, provenance in re.findall(
        r"^\| (\w+) \| (.*?) \| (.*?) \|$", section, re.MULTILINE
    ):
        ids = re.findall(r"`([^`]+)`", identifiers)
        assert ids
        assert re.search(rf'^\s+{node}\["', text, re.MULTILINE), node
        evidence = re.findall(r"`([^`]+)`", provenance)
        assert evidence, node
        assert len(evidence) == len(ids), node
        for identifier, locator in zip(ids, evidence):
            assert locator == (
                'scripts/capabilities/build_onepagers.py:SPECS[id="' + identifier + '"]'
            ), locator
            spec, row = work_specs[identifier]
            # Resolve the symbol to its AST span, then verify that span's ID.
            span = ast.get_source_segment(source_text, row)
            assert f"'id': '{identifier}'" in span, locator
            assert provenance.split("; `", 1)[0] == spec["std"], identifier
        observed.extend(ids)
        if any(identifier.startswith("economics-") for identifier in ids):
            economics_nodes.add(node)
    assert Counter(observed) == Counter(expected)
    assert economics_nodes == {"economics"}


def test_pages_selection_locators_resolve_to_function_symbols():
    """Publication locators survive line shifts and identify real builders."""
    tree = ast.parse((ROOT / "scripts/build_pages.py").read_text(encoding="utf-8"))
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    text = ARCHITECTURE.read_text(encoding="utf-8")
    table = text.split("| Repository-relative selection glob |", 1)[1].split(
        "\nTable 4.", 1
    )[0]
    rows = re.findall(r"^\| `reports/.*? \| .*? \| `([^`]+)` \|$", table, re.MULTILINE)
    assert rows
    for locator in rows:
        path, symbol = locator.split(":", 1)
        assert path == "scripts/build_pages.py"
        assert symbol in functions, locator
