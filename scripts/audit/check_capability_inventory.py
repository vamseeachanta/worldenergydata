#!/usr/bin/env python3
"""Inventory capability presence without importing or qualifying domain code."""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import yaml

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*\Z")


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently losing evidence."""


def _mapping(loader, node):
    pairs = loader.construct_pairs(node)
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate YAML key")
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def build_inventory(project_root):
    """Return deterministic, relative evidence; unknown optional evidence is null."""
    root = Path(project_root).resolve()
    inputs, exclusions = {}, {}

    def relative(path):
        return path.relative_to(root).as_posix()

    def safe(path):
        part = root
        for name in path.relative_to(root).parts:
            part = part / name
            if part.is_symlink():
                exclusions[relative(part)] = "symlink"
                return False
        return True

    def read(name, required=True):
        path = root / name
        if not safe(path) or not path.is_file():
            if required:
                raise ValueError(f"missing or unsafe input: {name}")
            return None
        content = path.read_bytes()
        inputs[name] = hashlib.sha256(content).hexdigest()
        return content.decode("utf-8")

    def load(name):
        try:
            loader = UniqueLoader(read(name))
            try:
                value = loader.get_single_data()
            finally:
                loader.dispose()
            if not isinstance(value, dict) or "modules" not in value:
                raise ValueError("missing modules")
            return value["modules"]
        except (yaml.YAMLError, ValueError, TypeError):
            raise ValueError(f"invalid input: {name}") from None

    def walk_error(error):
        raise error

    def files(path):
        found = []
        if safe(path) and path.is_dir():
            for parent, dirs, names in os.walk(
                path, followlinks=False, onerror=walk_error
            ):
                base = Path(parent)
                for name in list(dirs):
                    child = base / name
                    if not safe(child) or name.startswith((".", "_")):
                        dirs.remove(name)
                        if not child.is_symlink():
                            exclusions[relative(child)] = "non_production"
                found.extend(base / name for name in names if safe(base / name))
        return sorted(found)

    readme, index = read("README.md"), read("MODULE_INDEX.md")
    manifest, catalog = load("module-manifest.yaml"), load("data/catalog.yaml")
    if not isinstance(manifest, list) or not all(
        isinstance(m, dict)
        and isinstance(m.get("id"), str)
        and IDENTIFIER.fullmatch(m["id"])
        for m in manifest
    ):
        raise ValueError("invalid input: module-manifest.yaml")
    ids = [m["id"] for m in manifest]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate module ID: module-manifest.yaml")
    if not isinstance(catalog, dict) or not all(
        isinstance(k, str)
        and IDENTIFIER.fullmatch(k)
        and isinstance(v, dict)
        and isinstance(v.get("datasets"), list)
        for k, v in catalog.items()
    ):
        raise ValueError("invalid input: data/catalog.yaml")
    indexed, in_table = set(), False
    for line in index.splitlines():
        cells = [cell.strip().strip("`") for cell in line.strip().split("|")[1:-1]]
        if not line.strip().startswith("|"):
            in_table = False
        elif cells and cells[0].lower() == "module":
            in_table = True
        elif in_table and cells and IDENTIFIER.fullmatch(cells[0]):
            indexed.add(cells[0])
    owners = {}
    bases = [root / "src/worldenergydata"]
    packages = root / "packages"
    if safe(packages) and packages.is_dir():
        bases += [
            p / "src/worldenergydata" for p in sorted(packages.iterdir()) if safe(p)
        ]
    for base in bases:
        if not safe(base) or not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not safe(child):
                continue
            if not child.is_dir():
                exclusions[relative(child)] = "support_file"
            elif child.name.startswith((".", "_")) or not child.name.isidentifier():
                exclusions[relative(child)] = "non_production"
            elif any(p.suffix == ".py" for p in files(child)):
                owners.setdefault(child.name, []).append(relative(child))
            else:
                exclusions[relative(child)] = "no_python"
    evidence = {}
    for name in ("tests", "docs"):
        path = root / name
        paths = files(path) if safe(path) and path.is_dir() else None
        if name == "tests" and paths is not None:
            paths = [p for p in paths if p.match("test_*.py") or p.match("*_test.py")]
        evidence[name] = paths
    read("config/scheduler/scheduler_config.yml", required=False)
    rows, findings = [], []
    for name in sorted(set(owners) | indexed | set(ids) | set(catalog)):
        matches = re.compile(r"(?:^|[/_-])" + re.escape(name) + r"(?:$|[/_.-])")
        row = {
            "module": name,
            "source_paths": sorted(owners.get(name, [])),
            "index": name in indexed,
            "manifest": name in ids,
            "catalog": name in catalog,
            "catalog_status": (
                ("nonempty" if catalog[name]["datasets"] else "empty")
                if name in catalog
                else "absent"
            ),
            "collectability": "not_evaluated",
            "readme_mentions": [
                f"README.md:{i}"
                for i, line in enumerate(readme.splitlines(), 1)
                if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", line)
            ],
        }
        for kind, paths in evidence.items():
            row[kind] = (
                None
                if paths is None
                else [relative(p) for p in paths if matches.search(relative(p))]
            )
        if len(row["source_paths"]) > 1:
            findings.append(f"duplicate_ownership:{name}")
        if not row["source_paths"]:
            findings.append(f"unresolved_source:{name}")
        rows.append(row)
    return {
        "schema_version": "1.0",
        "inputs": inputs,
        "modules": rows,
        "findings": sorted(findings),
        "exclusions": [{"path": p, "reason": r} for p, r in sorted(exclusions.items())],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        payload = build_inventory(args.project_root)
        args.json_output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, UnicodeError):
        print("inventory failed: I/O or UTF-8 error", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"inventory failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
