"""Retire the connected component without breaking other legacy imports."""

import ast
import importlib
import importlib.util
from pathlib import Path

import pytest

LEGACY = "worldenergydata.common.legacy"
RETIRED_MODULES = (
    "ong_fd_components",
    "ong_fd_components_refactored",
    "ong_fd_drilling",
)
RETIRED_EXPORTS = {
    "ONGFDComponents",
    "assign_st_bp_tree_info",
    "get_rig_days_and_drilling_wt",
}


@pytest.mark.parametrize("module", RETIRED_MODULES)
def test_retired_modules_are_not_importable(module):
    assert importlib.util.find_spec(f"{LEGACY}.{module}") is None


def test_remaining_legacy_exports_and_data_imports_work():
    legacy = importlib.import_module(LEGACY)
    assert RETIRED_EXPORTS.isdisjoint(legacy.__all__)
    assert all(callable(getattr(legacy, name)) for name in legacy.__all__)
    data = importlib.import_module(f"{LEGACY}.data")
    assert callable(data.DateTimeUtility)
    assert callable(data.ReadDataFromSystemFiles)


def test_no_production_import_depends_on_the_retired_component():
    """Check import edges rather than historical mentions in comments/docs."""
    root = Path(__file__).resolve().parents[3]
    retired = {f"{LEGACY}.{module}" for module in RETIRED_MODULES}
    references = []
    for folder in ("src", "packages", "scripts"):
        for path in (root / folder).rglob("*.py"):
            source = path.read_bytes()
            # Only parse candidate callers. Unrelated historical scripts may
            # not be valid Python and are outside this dependency check.
            if not any(
                name.encode() in source for name in (*RETIRED_MODULES, *RETIRED_EXPORTS)
            ):
                continue
            tree = ast.parse(source, filename=str(path.relative_to(root)))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    targets = {alias.name for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    targets = {node.module}
                    if node.module in RETIRED_MODULES:
                        targets.add(f"{LEGACY}.{node.module}")
                    if node.module == LEGACY:
                        targets |= {f"{LEGACY}.{alias.name}" for alias in node.names}
                        if RETIRED_EXPORTS.intersection(
                            alias.name for alias in node.names
                        ):
                            references.append(
                                (str(path.relative_to(root)), node.lineno)
                            )
                else:
                    continue
                if retired.intersection(targets):
                    references.append((str(path.relative_to(root)), node.lineno))
    assert references == []
