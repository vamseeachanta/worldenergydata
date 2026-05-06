"""Bounded capability drift checks for issue #354.

Tests are static/non-networked: they parse YAML, CLI source, and Markdown only.
No imports of heavyweight runtime modules; no data refreshes; no network calls.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml
import pytest

_REPO = Path(__file__).resolve().parents[3]
_MANIFEST = _REPO / "module-manifest.yaml"
_SCHEDULER_CONFIG = _REPO / "config" / "scheduler" / "scheduler_config.yml"
_CLI_MAIN = _REPO / "src" / "worldenergydata" / "cli" / "main.py"
_MODULE_INDEX = _REPO / "MODULE_INDEX.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_manifest() -> dict:
    with _MANIFEST.open() as f:
        return yaml.safe_load(f)


def _load_scheduler_config() -> dict:
    with _SCHEDULER_CONFIG.open() as f:
        return yaml.safe_load(f) or {}


def _cli_registered_names() -> set[str]:
    """Parse app.add_typer(name=...) calls from cli/main.py via AST."""
    tree = ast.parse(_CLI_MAIN.read_text())
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_typer"):
            continue
        for kw in node.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                names.add(kw.value.value)
    return names


def _info_table_names() -> set[str]:
    """Extract module names from table.add_row() calls in info() via AST."""
    tree = ast.parse(_CLI_MAIN.read_text())
    names = set()
    in_info = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "info":
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                func = child.func
                if isinstance(func, ast.Attribute) and func.attr == "add_row":
                    if child.args and isinstance(child.args[0], ast.Constant):
                        names.add(child.args[0].value)
            in_info = True
            break
    return names


def _scheduler_job_names() -> set[str]:
    """Extract job names from scheduler_config.yml."""
    cfg = _load_scheduler_config()
    jobs = cfg.get("jobs", [])
    return {j["name"] for j in jobs if isinstance(j, dict) and "name" in j}


def _module_index_scheduler_wired() -> set[str]:
    """Extract module IDs from the scheduler table rows in MODULE_INDEX.md."""
    text = _MODULE_INDEX.read_text()
    section = re.search(
        r"## Scheduler Status.*?(?=^##|\Z)", text, re.DOTALL | re.MULTILINE
    )
    if not section:
        return set()
    # Match rows like: | `bsee` | ... |
    return set(re.findall(r"\|\s+`(\w+)`\s+\|", section.group()))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestManifestSchemaComplete:
    """Every manifest module must carry the four new required fields."""

    REQUIRED_FIELDS = {"in_scheduler", "public_cli", "catalog_status", "capability_source"}

    def test_all_modules_have_required_fields(self):
        data = _load_manifest()
        modules = data.get("modules", [])
        assert modules, "module-manifest.yaml has no modules"
        missing = {}
        for m in modules:
            absent = self.REQUIRED_FIELDS - set(m.keys())
            if absent:
                missing[m.get("id", "unknown")] = absent
        assert not missing, (
            f"Modules missing required schema fields: {missing}"
        )

    def test_catalog_status_values_are_valid(self):
        valid = {
            "full", "sample", "empty", "runtime_fetched",
            "reference_data", "not_applicable", "unknown",
        }
        data = _load_manifest()
        bad = {
            m["id"]: m["catalog_status"]
            for m in data.get("modules", [])
            if m.get("catalog_status") not in valid
        }
        assert not bad, f"Invalid catalog_status values: {bad}"

    def test_capability_source_values_are_valid(self):
        valid = {"manifest", "source_tree", "catalog_only", "back_compat"}
        data = _load_manifest()
        bad = {
            m["id"]: m["capability_source"]
            for m in data.get("modules", [])
            if m.get("capability_source") not in valid
        }
        assert not bad, f"Invalid capability_source values: {bad}"


class TestSchedulerIndexMatchesConfig:
    """MODULE_INDEX.md scheduler table must match scheduler_config.yml."""

    def test_scheduler_config_wired_modules_in_index(self):
        scheduler_jobs = _scheduler_job_names()
        # Map job name → module id prefix (e.g. bsee_refresh → bsee)
        job_module_ids = {j.replace("_refresh", "") for j in scheduler_jobs}
        index_wired = _module_index_scheduler_wired()
        not_in_index = job_module_ids - index_wired
        assert not not_in_index, (
            f"Scheduler jobs present in scheduler_config.yml but module IDs "
            f"not found in MODULE_INDEX.md scheduler table: {not_in_index}"
        )

    def test_manifest_scheduler_matches_config(self):
        scheduler_jobs = _scheduler_job_names()
        job_module_ids = {j.replace("_refresh", "") for j in scheduler_jobs}
        data = _load_manifest()
        manifest_wired = {
            m["id"] for m in data.get("modules", []) if m.get("in_scheduler") is True
        }
        # Every manifest-wired module should have a job in scheduler_config
        stale_claims = manifest_wired - job_module_ids
        # We allow manifest to claim 'wired' only for modules that have a job
        assert not stale_claims, (
            f"Manifest has in_scheduler: true for modules with no corresponding "
            f"job in scheduler_config.yml: {stale_claims}"
        )


class TestCliInfoListsAllRegisteredSubapps:
    """worldenergydata info table must list every registered CLI sub-app."""

    def test_info_covers_all_registered_subapps(self):
        registered = _cli_registered_names()
        info_names = _info_table_names()
        missing_from_info = registered - info_names
        assert not missing_from_info, (
            f"CLI sub-apps registered in add_typer() but missing from info() table: "
            f"{missing_from_info}"
        )


class TestManifestTotalModulesAccurate:
    """total_modules claim in manifest must match actual module count."""

    def test_total_modules_matches_actual_count(self):
        data = _load_manifest()
        declared = data.get("total_modules", 0)
        actual = len(data.get("modules", []))
        assert declared == actual, (
            f"module-manifest.yaml total_modules={declared} but "
            f"actual module count={actual}"
        )
