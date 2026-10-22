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


def work_specifications():
    """Read literal work entries and their source spans without running the builder."""
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
    entries = {}
    for row in specification.elts:
        spec = {
            ast.literal_eval(key): ast.literal_eval(value)
            for key, value in zip(row.keys, row.values)
            if isinstance(key, ast.Constant) and key.value in {"id", "kind", "std"}
        }
        if spec["kind"] == "work":
            entries[spec["id"]] = (spec, ast.get_source_segment(source_text, row))
    return entries


def provenance_rows():
    """Select only the capability inventory table."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    section = text.split("## Capability inventory and provenance\n")[1].split("\n## ")[
        0
    ]
    return re.findall(r"^\| (\w+) \| (.*?) \| (.*?) \|$", section, re.MULTILINE)


def row_work_ids(identifiers, specs):
    """Expand the shared economics dimension without embedding field names."""
    if identifiers == "`economics-` prefix (seven work IDs)":
        return [
            identifier for identifier in specs if identifier.startswith("economics-")
        ]
    return re.findall(r"`([^`]+)`", identifiers)


def test_work_specs_have_one_provenance_row_and_drawn_node():
    """Every cited SPECS span contains its work ID and maps once to a drawn node."""
    specs = work_specifications()
    text = ARCHITECTURE.read_text(encoding="utf-8")
    observed = []
    economics_nodes = set()
    for node, identifiers, provenance in provenance_rows():
        ids = row_work_ids(identifiers, specs)
        assert ids
        assert re.search(rf'^\s+{node}\["', text, re.MULTILINE), node
        locator = re.search(
            r"`scripts/capabilities/build_onepagers\.py::SPECS"
            r'\[(id|id_prefix)="([^"]+)"\]`',
            provenance,
        )
        assert locator is not None, node
        selector, value = locator.groups()
        selected = (
            [value]
            if selector == "id"
            else [identifier for identifier in specs if identifier.startswith(value)]
        )
        assert Counter(selected) == Counter(ids), node
        for identifier in ids:
            assert identifier in specs, identifier
            _, span = specs[identifier]
            assert f"'id': '{identifier}'" in span, identifier
        observed.extend(ids)
        if any(identifier.startswith("economics-") for identifier in ids):
            economics_nodes.add(node)
    assert Counter(observed) == Counter(specs.keys())
    assert economics_nodes == {"economics"}


def test_provenance_descriptions_match_current_specification_basis():
    """A stale source, vintage or qualification in any std description is rejected."""
    specs = work_specifications()
    for node, identifiers, provenance in provenance_rows():
        for identifier in row_work_ids(identifiers, specs):
            spec, _ = specs[identifier]
            assert provenance.startswith(spec["std"] + "; `"), (node, identifier)


def test_publication_table_uses_existing_builder_symbols():
    """Table 4 locators survive line shifts and identify real builder functions."""
    source = ROOT / "scripts/build_pages.py"
    functions = {
        node.name
        for node in ast.parse(source.read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef)
    }
    text = ARCHITECTURE.read_text(encoding="utf-8")
    table = text.split("| Repository-relative selection glob |")[1].split("\n\n")[0]
    rows = re.findall(r"^\| `.*?` \| .*? \| (.*?) \|$", table, re.MULTILINE)
    assert rows
    for locator in rows:
        match = re.fullmatch(r"`scripts/build_pages\.py::(build_\w+)`", locator)
        assert match is not None, locator
        assert match.group(1) in functions, locator
