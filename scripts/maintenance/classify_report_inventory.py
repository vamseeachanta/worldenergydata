#!/usr/bin/env python3
"""Classify every existing report HTML file recursively, including templates.

Rule order (first match wins), as defined by the architecture page:
1. Superseded: an explicit link with rel="successor-version" whose href resolves
   to an existing replacement file inside the repository.
2. Unverified: an explicit unverified report paragraph.
3. Current: a Pages input selection whose existence gates are present.
4. One-off: an unselected filename with a separate demo or test token, bounded
   by start, underscore or hyphen on the left and underscore, hyphen or dot on
   the right.
5. Undetermined: no decisive evidence under the preceding rules.

Only --write writes a file: the inventory CSV. Reports remain read-only.
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/build_pages.py"
INVENTORY = "docs/modules/report-inventory.csv"


def builder_functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def registered_builders(path):
    """Read the module-level DOMAINS registry that controls full builds."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    registry = next(
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "DOMAINS"
            for target in node.targets
        )
    )
    return {node.id for node in registry.values} | {"build_shared_assets"}


def literal_tables(function):
    """Read literal loop tables and dictionary/list assignments from source."""
    tables = []
    for node in ast.walk(function):
        value = node.iter if isinstance(node, ast.For) else None
        if isinstance(node, ast.Assign):
            value = node.value
        if isinstance(value, (ast.Tuple, ast.List, ast.Dict)) and all(
            isinstance(part, (ast.Tuple, ast.List, ast.Dict, ast.Constant, ast.Load))
            for part in ast.walk(value)
        ):
            tables.append(ast.literal_eval(value))
    return tables


def path_expression(node, values):
    if isinstance(node, ast.Name):
        return values.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        base = path_expression(node.left, values)
        if base is not None and isinstance(node.right, ast.Constant):
            return base / node.right.value
    return None


def direct_copy_sources(function):
    """Parse path assignments and direct copy arguments, without executing code."""
    values = {"REPORTS": Path("reports"), "SITE_ASSETS": Path("site_assets")}
    nodes = sorted(ast.walk(function), key=lambda node: getattr(node, "lineno", 0))
    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = path_expression(node.value, values)
            if isinstance(target, ast.Name) and value is not None:
                values[target.id] = value
    result = []
    for node in nodes:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("copy2", "copyfile"):
                value = path_expression(node.args[0], values)
                if value is not None and value.suffix == ".html":
                    result.append(value.as_posix())
    return result


def selection_rows(root, builder=BUILDER):
    """Mirror conditional publication in one place; read literal tables as data.

    Each row is (selection glob, all existence gates, builder evidence).
    Evidence ranges are derived from the parsed function, avoiding stale lines.
    """
    functions = builder_functions(builder)
    registered = registered_builders(builder)
    rows = []

    def add(function, pattern, *gates):
        if function not in registered:
            return
        node = functions[function]
        evidence = (
            f"scripts/build_pages.py:{node.lineno}-{node.end_lineno} ({function})"
        )
        rows.append((pattern, tuple(dict.fromkeys(gates or [pattern])), evidence))

    # build_shared_assets:389-406; prefer committed assets over report fallback.
    for name in literal_tables(functions["build_shared_assets"])[0]:
        if not (root / "site_assets" / name).exists():
            add("build_shared_assets", f"reports/bsee/{name}")

    # build_lower_tertiary:416-695; nested gates require the lifecycle index.
    base = "reports/lower_tertiary/lifecycle"
    gate = f"{base}/index.html"
    for pattern in ("*_lifecycle.html", "index.html"):
        add("build_lower_tertiary", f"{base}/{pattern}", gate)
    for sub, pattern, condition in (
        ("wells", "*_well.html", "wells/index.html"),
        ("wells", "index.html", "wells/index.html"),
        ("assets", "*_assets.html", "assets"),
        ("norms", "*.html", "norms"),
    ):
        add(
            "build_lower_tertiary",
            f"{base}/{sub}/{pattern}",
            gate,
            f"{base}/{condition}",
        )
    # build_lower_tertiary:416-695; direct copies gate on their own source.
    for path in direct_copy_sources(functions["build_lower_tertiary"]):
        if not path.startswith(base + "/"):
            add("build_lower_tertiary", path)

    # build_field_development:698-741; loop tables supply singles and whole trees.
    for table in literal_tables(functions["build_field_development"]):
        for source, destination in table:
            path = f"reports/field_development/{source}"
            pattern = path if path.endswith(".html") else f"{path}/**/*.html"
            add("build_field_development", pattern, path)

    # build_capabilities:744-781; index gate covers insights and the PDF tree.
    gate = "reports/capabilities/index.html"
    for path in direct_copy_sources(functions["build_capabilities"]):
        add("build_capabilities", path, gate, path)
    for sub in literal_tables(functions["build_capabilities"])[0]:
        path = f"reports/capabilities/{sub}"
        add("build_capabilities", f"{path}/**/*.html", gate, path)

    # build_completion:784-801, build_hse:826-838: early-return gates.
    for function, folder, condition in (
        ("build_completion", "completion", "completion/index.html"),
        ("build_hse", "hse", "hse"),
    ):
        add(function, f"reports/{folder}/*.html", f"reports/{condition}")
    # build_marine_safety:804-823; independent directory and single-file gates.
    add("build_marine_safety", "reports/marine_safety/*.html", "reports/marine_safety")
    for path in direct_copy_sources(functions["build_marine_safety"]):
        add("build_marine_safety", path)

    # build_field_atlas:841-864; index gate also controls the one-pager tree.
    gate = "reports/field-atlas/index.html"
    add("build_field_atlas", gate)
    add(
        "build_field_atlas",
        "reports/field-atlas/onepagers/**/*.html",
        gate,
        "reports/field-atlas/onepagers",
    )
    # build_pressure_atlas:867-875, build_field_benchmark:902-922: index gates.
    for function in ("build_pressure_atlas", "build_field_benchmark"):
        for path in direct_copy_sources(functions[function]):
            add(function, path)
    # build_decommissioning:878-899; pages dictionary supplies selected filenames.
    for name in literal_tables(functions["build_decommissioning"])[0]:
        add("build_decommissioning", f"reports/decommissioning/{name}")
    add("build_production_forecast", "reports/production_forecast/index.html")
    return rows


class SuccessorLinks(HTMLParser):
    """Collect only explicit successor-version links."""

    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if (
            tag == "link"
            and "successor-version" in (attributes.get("rel") or "").split()
        ):
            if attributes.get("href"):
                self.hrefs.append(attributes["href"])


def replacement_evidence(path, root):
    parser = SuccessorLinks()
    parser.feed(path.read_text(encoding="utf-8"))
    for href in parser.hrefs:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        replacement = (path.parent / unquote(parsed.path)).resolve()
        if replacement != path.resolve() and replacement.is_relative_to(root.resolve()):
            if replacement.is_file():
                return (
                    "successor-version: "
                    + replacement.relative_to(root.resolve()).as_posix()
                )
    return None


def classify_tree(root, builder=BUILDER):
    selected = {}
    for pattern, gates, evidence in selection_rows(root, builder):
        if all((root / gate).exists() for gate in gates):
            for path in sorted(root.glob(pattern)):
                if path.is_file():
                    selected.setdefault(path.relative_to(root).as_posix(), evidence)
    rows = []
    for path in sorted((root / "reports").rglob("*.html")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        replacement = replacement_evidence(path, root)
        if replacement:
            classification, evidence = "superseded", replacement
        elif '<p class="unverified">' in path.read_text(encoding="utf-8"):
            classification = "unverified"
            evidence = "explicit unverified notice; source-data reproduction not established"
        elif relative in selected:
            classification, evidence = "current", selected[relative]
        elif re.search(r"(^|[_-])(demo|test)(?=[_.-])", path.name):
            classification = "one-off"
            evidence = "filename demo/test marker; not selected by Pages"
        else:
            classification = "undetermined"
            evidence = (
                "no decisive publication or replacement evidence under these rules"
            )
        rows.append(
            dict(path=relative, classification=classification, evidence=evidence)
        )
    return rows


def inventory_bytes(root, builder=BUILDER):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=["path", "classification", "evidence"], lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(classify_tree(root, builder))
    return output.getvalue().encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    output = inventory_bytes(ROOT, BUILDER)
    target = ROOT / INVENTORY
    if args.write:
        target.write_bytes(output)
    elif args.check:
        if not target.is_file() or target.read_bytes() != output:
            print("Report inventory differs; run with --write to regenerate.")
            return 1
        print("Report inventory: OK")
    else:
        counts = Counter(row["classification"] for row in classify_tree(ROOT, BUILDER))
        print("| Classification | HTML files |\n| --- | --- |")
        for classification in ("current", "superseded", "unverified", "one-off", "undetermined"):
            print(f"| {classification} | {counts[classification]} |")
        print(
            "\n| Repository-relative selection glob | Existence gates | "
            "Builder function and lines |"
        )
        print("| --- | --- | --- |")
        for pattern, gates, evidence in selection_rows(ROOT, BUILDER):
            print(
                f"| `{pattern}` | "
                + ", ".join(f"`{g}`" for g in gates)
                + f" | `{evidence}` |"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
