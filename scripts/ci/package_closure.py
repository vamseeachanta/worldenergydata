#!/usr/bin/env python3
"""Report static reverse dependencies between workspace distributions.

AST semantics: Python language reference, Import statement; repository source is
the graph's evidence. All syntactic imports count, including conditional imports.
Dynamic imports and runtime plugin discovery are outside this static inventory.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def dependents(package: str, imports: dict[str, list[str]]) -> list[str]:
    """Pure reverse reachability: return direct and transitive importers, excluding self.

    Input edges run importer -> provider; repeatedly visit reverse neighbours
    until no unseen vertex remains. No filesystem reads or application imports.
    """
    if package not in imports:
        raise KeyError(package)
    visited = {package}
    pending = [package]
    while pending:
        provider = pending.pop()
        for importer, providers in imports.items():
            if provider in providers and importer not in visited:
                visited.add(importer)
                pending.append(importer)
    return sorted(visited - {package})


def _imports(tree: ast.AST, module: str, is_init: bool):
    """Resolve relative ImportFrom nodes without importing their modules."""
    current = module.split(".") if is_init else module.split(".")[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # Import statement reference: level=1 is the current package.
                if node.level > len(current):
                    continue
                base = current[: len(current) - node.level + 1]
            else:
                base = []
            if node.module:
                base += node.module.split(".")
            prefix = ".".join(base)
            if prefix:
                yield prefix
            for alias in node.names:
                if alias.name != "*":
                    yield ".".join([*base, alias.name])


def scan(root: Path) -> dict:
    """Parse all member source files, resolving ownership by longest module prefix."""
    members = sorted(
        p for p in (root / "packages").glob("worldenergydata-*") if p.is_dir()
    )
    edges = {p.name: set() for p in members}
    ownership: dict[str, set[str]] = {}
    files = []
    sources = {p.name: [] for p in members}
    problems = []
    for member in members:
        base = member / "src"
        for path in sorted(base.rglob("*.py")):
            relative = path.relative_to(base).with_suffix("")
            parts = list(relative.parts)
            is_init = parts[-1] == "__init__"
            if is_init:
                parts.pop()
            module = ".".join(parts)
            # Namespace ancestors may be shared. Never assign one arbitrarily.
            for end in range(1, len(parts) + 1):
                ownership.setdefault(".".join(parts[:end]), set()).add(member.name)
            files.append((member.name, path, module, is_init))
            sources[member.name].append(path.relative_to(root).as_posix())
    for member, path, module, is_init in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeError) as error:
            problems.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "line": getattr(error, "lineno", None),
                    "reason": type(error).__name__,
                }
            )
            continue
        for imported in _imports(tree, module, is_init):
            parts = imported.split(".")
            while parts:
                providers = ownership.get(".".join(parts))
                if providers:
                    if len(providers) == 1:
                        edges[member].update(providers - {member})
                    # Shared namespaces are not evidence of a specific dependency.
                    break
                parts.pop()
    return {
        "imports": {p: sorted(e) for p, e in edges.items()},
        "sources": sources,
        "not_evaluated": problems,
    }


def report(graph: dict) -> dict:
    imports = graph["imports"]
    return {
        "packages": {
            package: {
                "direct": sorted(
                    p for p, providers in imports.items() if package in providers
                ),
                "transitive": dependents(package, imports),
            }
            for package in imports
        },
        "not_evaluated": graph["not_evaluated"],
    }


def selector_gaps(root: Path, graph: dict, selector) -> list[dict]:
    """Compare real source-only diffs with dependent test homes; report missing homes too."""
    gaps = []
    for provider, paths in graph["sources"].items():
        required = set()
        absent = []
        for dependent in dependents(provider, graph["imports"]):
            namespace = root / "packages" / dependent / "src/worldenergydata"
            homes = (
                [f"tests/unit/{p.name}" for p in namespace.iterdir() if p.is_dir()]
                if namespace.is_dir()
                else []
            )
            homes.append(f"packages/{dependent}/tests")
            existing = [h for h in homes if (root / h).is_dir()]
            if not existing:
                absent.append(dependent)
            required.update(existing)
        for path in paths:
            result = selector.select([path], root)
            if result["scope"] == "full":
                continue
            targets = result["xdist"] + result["seq"]
            missing = sorted(
                h
                for h in required
                if not any(h == t or h.startswith(t + "/") for t in targets)
            )
            if missing or absent:
                gaps.append(
                    {
                        "path": path,
                        "missing_targets": missing,
                        "dependents_without_test_home": sorted(absent),
                    }
                )
    return gaps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    args = parser.parse_args(argv)
    print(json.dumps(report(scan(args.root)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
