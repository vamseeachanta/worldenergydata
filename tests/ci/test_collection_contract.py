"""Regressions for the collection failures described in issue #313."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_single_configuration(pytestconfig):
    """Use the root configuration without an early error cutoff."""
    assert Path(pytestconfig.inipath) == REPO_ROOT / "pyproject.toml"
    assert not (REPO_ROOT / "pytest.ini").exists()
    assert not (REPO_ROOT / "tests/pytest.ini").exists()
    assert not any("maxfail" in option for option in pytestconfig.getini("addopts"))


def test_duplicate_basenames_collect(pytester):
    """Two independent test files must both execute, per pytest importlib docs.

    Source: pytest, 'pytest import mechanisms and sys.path/PYTHONPATH',
    importlib section: test module names do not need to be unique.
    The expected count is a hand count of the two generated test functions.
    """
    (pytester.path / "pyproject.toml").write_text(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for directory in ("first", "second"):
        target = pytester.path / "tests" / directory
        target.mkdir(parents=True)
        (target / "test_end_to_end.py").write_text(
            "def test_independent():\n    assert True\n", encoding="utf-8"
        )
    result = pytester.runpytest_subprocess("-q", "-p", "no:cacheprovider")
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize(
    "relative_path",
    [
        "tests/modules/fdas/integration/test_end_to_end.py",
        "tests/modules/sodir-integration/test_api_client.py",
        "tests/modules/sodir-integration/test_cross_regional_validation.py",
        "tests/modules/sodir-integration/test_integration.py",
        "tests/modules/sodir-integration/test_performance.py",
        "tests/modules/well_production_dashboard/test_monitoring.py",
        "tests/modules/well_production_dashboard/test_well_production_dashboard.py",
        "tests/unit/hse/database/test_models.py",
        "tests/unit/hse/importers/test_bsee_incidents_importer_url.py",
        "tests/unit/hse/importers/test_bsee_penalties_importer_url.py",
        "tests/unit/hse/importers/test_bsee_statistics_importer_url.py",
    ],
)
def test_repaired_targets_are_not_hidden(relative_path, pytestconfig):
    """The collection hook must allow repaired imports and duplicate names."""
    spec = importlib.util.spec_from_file_location(
        "collection_contract_conftest", REPO_ROOT / "tests/conftest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not module.pytest_ignore_collect(REPO_ROOT / relative_path, None)
    for option in pytestconfig.getini("addopts"):
        if option.startswith("--ignore="):
            ignored = Path(option.partition("=")[2])
            assert not (REPO_ROOT / relative_path).is_relative_to(REPO_ROOT / ignored)


def test_sodir_tests_use_canonical_imports(monkeypatch):
    """Inspect imports and mock targets, including imports inside test bodies."""
    directory = REPO_ROOT / "tests/modules/sodir-integration"
    paths = [*directory.glob("test_*.py"), directory / "performance/profile_api.py"]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("sodir_module"), path.name
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not node.value.startswith("sodir_module."), path.name

    from worldenergydata.sodir.api_client import SodirAPIClient

    spec = importlib.util.spec_from_file_location(
        "sodir_profile_collection_contract", directory / "performance/profile_api.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    assert module.SodirAPIClient is SodirAPIClient


@pytest.mark.parametrize("name", ["blasingame", "fetkovich", "models"])
def test_type_curve_implementations_are_available(name):
    """Canonical implementations must resolve in the installed namespace."""
    import importlib

    canonical = importlib.import_module(
        f"worldenergydata.bsee.analysis.type_curves.{name}"
    )
    legacy = importlib.import_module(
        f"worldenergydata.modules.bsee.analysis.type_curves.{name}"
    )
    assert legacy is canonical


def test_financial_dependency_is_required_at_runtime():
    """The root requires FDAS, which requires numpy-financial without extras."""
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    def dependencies(path):
        with path.open("rb") as stream:
            requirements = tomllib.load(stream)["project"]["dependencies"]
        return {requirement.split(">=")[0] for requirement in requirements}

    assert "worldenergydata-fdas" in dependencies(REPO_ROOT / "pyproject.toml")
    assert "numpy-financial" in dependencies(
        REPO_ROOT / "packages/worldenergydata-fdas/pyproject.toml"
    )
    from worldenergydata.fdas.core import financial

    assert financial.npf.__name__ == "numpy_financial"
