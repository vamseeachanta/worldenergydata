"""Static audit tests; fixtures are source text, never imported legacy modules."""

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/analysis/legacy_symbol_inventory.py"
REPORT = ROOT / "docs/analysis/legacy-dead-code-report.md"


@pytest.fixture
def audit():
    spec = importlib.util.spec_from_file_location("legacy_symbol_inventory", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_never_executes_source(audit):
    """The raising statement must remain inert; only the class is inventoried."""
    source = 'raise RuntimeError("must not execute")\nclass Unused:\n    pass\n'
    assert audit.inventory(source) == [
        {
            "name": "Unused",
            "kind": "class",
            "start": 2,
            "end": 3,
            "loads": [],
            "exported": False,
            "origin": None,
        }
    ]


def test_nested_definitions_are_not_top_level(audit):
    """Only outer belongs to module scope; inner is part of its source span."""
    symbols = audit.inventory("def outer():\n    def inner():\n        pass\n")
    assert [item["name"] for item in symbols] == ["outer"]


def test_entry_point_and_callback_references_are_retained(audit):
    """Passing a callback and invoking it in the entry point both protect it."""
    source = (
        "def callback():\n    pass\n"
        "register(callback)\n"
        'if __name__ == "__main__":\n    callback()\n'
    )
    assert audit.inventory(source)[0]["loads"] == [3, 5]


def test_explicit_reexports_have_their_own_identity(audit):
    """An imported replacement and a local definition are distinct symbols."""
    source = (
        "from .replacement import Current as Migrated\n"
        "class Original:\n    pass\n"
        '__all__ = ["Migrated", "Original"]\n'
    )
    symbols = {item["name"]: item for item in audit.inventory(source)}
    assert symbols["Migrated"]["origin"] == ".replacement.Current"
    assert symbols["Migrated"]["kind"] == "reexport"
    assert symbols["Original"]["origin"] is None
    assert symbols["Original"]["exported"]
    assert symbols["Original"]["loads"] == []


def test_assignment_spans_and_decorators(audit):
    """All binding targets are retained; decorated source includes the decorator."""
    source = (
        "left, right = pair\n"
        "state: list = []\n"
        "@decorate\nasync def action():\n    return state\n"
    )
    symbols = {item["name"]: item for item in audit.inventory(source)}
    assert set(symbols) == {"left", "right", "state", "action"}
    assert symbols["action"]["start"] == 3
    assert symbols["state"]["loads"] == [5]


def test_incidental_imports_are_not_public_inventory(audit):
    """Imports without an explicit export are dependencies, not local definitions."""
    assert audit.inventory("import sqlite3\nfrom typing import Any\n") == []


def test_invalid_source_fails_instead_of_claiming_no_symbols(audit):
    with pytest.raises(SyntaxError):
        audit.inventory("def broken(:")


def test_dynamic_exports_fail_instead_of_silently_omitting_symbols(audit):
    with pytest.raises(ValueError, match="literal"):
        audit.inventory("__all__ = discover_exports()\n")


def test_source_line_union_does_not_double_count(audit):
    """Inclusive spans [2,4] and [4,5] cover {2,3,4,5}: four physical lines."""
    assert audit.covered_lines([{"start": 2, "end": 4}, {"start": 4, "end": 5}]) == 4


def test_cli_matches_inventory_and_report(audit, tmp_path):
    """Report rows cover every definition, binding and explicit public reexport."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(ROOT)],
        check=True,
        text=True,
        capture_output=True,
        cwd=tmp_path,
    )
    payload = json.loads(result.stdout)
    report = REPORT.read_text()
    for filename, evidence in payload.items():
        section = report.split(f"## `{filename}`\n", 1)[1].split("\n## ", 1)[0]
        rows = {}
        for line in section.splitlines():
            if line.startswith("| `"):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                rows[cells[0].strip("`")] = cells[1]
        assert set(rows) == {symbol["name"] for symbol in evidence["symbols"]}
        for symbol in evidence["symbols"]:
            expected = (
                "MIGRATED"
                if symbol["origin"]
                else ("LIVE" if symbol["loads"] else "DEAD")
            )
            assert rows[symbol["name"]] == expected
        dead = [
            symbol for symbol in evidence["symbols"] if rows[symbol["name"]] == "DEAD"
        ]
        assert all(not symbol["loads"] and not symbol["origin"] for symbol in dead)
        lines = audit.covered_lines(dead)
        percent = lines / evidence["physical_lines"] * 100
        expected_row = f"| `{filename}` | {lines} | {evidence['physical_lines']} | {percent:.1f}% |"
        assert expected_row in report


def test_migrated_symbols_resolve_to_actual_source_definitions(audit):
    """Every imported compatibility export must have a binding at its origin."""
    legacy = ROOT / audit.LEGACY
    source = (legacy / "wellpath3D.py").read_text()
    for symbol in audit.inventory(source):
        if symbol["origin"]:
            module, name = symbol["origin"].rsplit(".", 1)
            target = legacy / (module.rsplit(".", 1)[1] + ".py")
            assert name in {
                item["name"] for item in audit.inventory(target.read_text())
            }


def test_package_export_is_a_distinct_replacement(audit):
    """The package export targets the replacement, not the original class."""
    legacy = ROOT / audit.LEGACY
    tree = ast.parse((legacy / "__init__.py").read_text())
    origins = [
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and any(alias.name == "ONGFDComponents" for alias in node.names)
    ]
    assert origins == ["ong_fd_components_refactored"]


def test_no_tracked_python_imports_of_candidate_modules():
    """Independently recheck import sites, including relative and aliased imports.

    Text candidates come from every tracked Python file. Comments are not
    imports; literal dynamic module names are conservatively treated as uses.
    This cannot detect module names assembled at runtime.
    """
    names = {"ong_fd_components", "wellpath3D"}
    result = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "-z",
            "-I",
            "-w",
            "-e",
            "ong_fd_components",
            "-e",
            "wellpath3D",
            "--",
            "*.py",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode in (0, 1), "Tracked source search failed"
    excluded = {SCRIPT, Path(__file__).resolve()}
    excluded.update(
        ROOT
        / "packages/worldenergydata-core/src/worldenergydata/common/legacy"
        / (name + ".py")
        for name in names
    )
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = ROOT / raw_path.decode()
        if path in excluded:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported = [alias.name for alias in node.names]
                if isinstance(node, ast.ImportFrom):
                    imported.append(node.module or "")
                assert not any(
                    names.intersection(value.split(".")) for value in imported
                ), f"Unexpected legacy import: {path.relative_to(ROOT)}:{node.lineno}"
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not names.intersection(
                    node.value.split(".")
                ), f"Possible dynamic reference: {path.relative_to(ROOT)}:{node.lineno}"
