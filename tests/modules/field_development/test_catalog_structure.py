"""Catalog helpers must remain within the repository's review size limits."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_catalog_module_and_function_sizes():
    paths = sorted(
        (ROOT / "src/worldenergydata/field_development").glob("catalog_*.py")
    ) + [
        ROOT / "scripts/field_atlas/catalog_extension.py",
        ROOT / "scripts/field_development/integrate_angola_catalog.py",
    ]
    violations = []
    for path in paths:
        source = path.read_text("utf-8")
        if len(source.splitlines()) > 400:
            violations.append(f"{path.name}: module exceeds 400 lines")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.end_lineno - node.lineno + 1 > 50:
                    violations.append(f"{path.name}:{node.name}: exceeds 50 lines")
    assert not violations, "\n".join(violations)
