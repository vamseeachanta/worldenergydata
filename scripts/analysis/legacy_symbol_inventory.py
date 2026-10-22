"""Inventory legacy definitions and explicit exports without importing them.

This is evidence for a manual caller audit, not a reachability or deletion tool.
Name loads include annotations, callbacks and guarded entry points. They do not
resolve scope, dynamic lookup or callers outside the inspected source.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

LEGACY = Path("packages/worldenergydata-core/src/worldenergydata/common/legacy")
TARGETS = ("ong_fd_components.py", "wellpath3D.py")


def _bindings(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [name for item in node.elts for name in _bindings(item)]
    return []


def inventory(source: str) -> list[dict]:
    """Return direct module definitions, data bindings and literal public imports.

    Incidental dependency imports and the export-list metadata are excluded.
    Reexports are identified by import origin, never by matching symbol names.
    """
    tree = ast.parse(source)
    exports: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any("__all__" in _bindings(target) for target in targets):
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, TypeError) as error:
                    raise ValueError("__all__ must be a literal string list") from error
                if not isinstance(value, (list, tuple)) or not all(
                    isinstance(item, str) for item in value
                ):
                    raise ValueError("__all__ must be a literal string list")
                exports.update(value)

    loads: dict[str, set[int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loads.setdefault(node.id, set()).add(node.lineno)

    symbols = []

    def record(name: str, kind: str, node: ast.AST, origin: str | None = None):
        decorators = getattr(node, "decorator_list", [])
        symbols.append(
            {
                "name": name,
                "kind": kind,
                "start": min([node.lineno] + [item.lineno for item in decorators]),
                "end": node.end_lineno,
                "loads": sorted(loads.get(name, [])),
                "exported": name in exports,
                "origin": origin,
            }
        )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            record(
                node.name,
                "class" if isinstance(node, ast.ClassDef) else "function",
                node,
            )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in _bindings(target):
                    if name != "__all__":
                        record(name, "data", node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if name in exports:
                    prefix = (
                        "." * node.level + (node.module or "")
                        if isinstance(node, ast.ImportFrom)
                        else ""
                    )
                    origin = f"{prefix}.{alias.name}" if prefix else alias.name
                    record(name, "reexport", node, origin)
    return symbols


def covered_lines(symbols: list[dict]) -> int:
    """Count the union of inclusive source spans, including decorators.

    Definition: each physical line in [start, end] contributes once. This is
    source accounting, not an engineering coefficient or acceptance limit.
    """
    return len(
        {
            line
            for symbol in symbols
            for line in range(symbol["start"], symbol["end"] + 1)
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    args = parser.parse_args()
    result = {}
    for filename in TARGETS:
        source = (args.root / LEGACY / filename).read_text(encoding="utf-8")
        result[filename] = {
            "physical_lines": len(source.splitlines()),
            "symbols": inventory(source),
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
