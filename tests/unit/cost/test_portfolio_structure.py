"""Structural limits for the portfolio cost-map implementation."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "packages/worldenergydata-cost/src/worldenergydata/cost/timeseries"


def _portfolio_python_paths() -> tuple[Path, ...]:
    production = tuple(PACKAGE.glob("portfolio_*.py"))
    tests = tuple((ROOT / "tests/unit/cost").glob("test_portfolio_*.py"))
    builder = ROOT / "scripts/cost/build_portfolio_asset_award_coverage.py"
    entrypoints = (builder,) if builder.exists() else ()
    return tuple(sorted((*production, *tests, *entrypoints)))


def test_portfolio_python_structure() -> None:
    violations: list[str] = []
    for path in _portfolio_python_paths():
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > 400:
            violations.append(f"{path.relative_to(ROOT)}: {len(lines)} lines")
        tree = ast.parse("\n".join(lines), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                if span > 50:
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno} "
                        f"{node.name}: {span} lines"
                    )
    assert not violations, "\n".join(violations)
