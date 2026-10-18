"""
Pytest configuration with performance tracking and common fixtures.

This module provides:
- Performance tracking hooks
- Common fixtures for all tests
- Test collection filtering
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict

import numpy as np
import pandas as pd
import pytest

# Fix pandas/pyarrow compatibility issue with pytest-cov JSON reporting.
# pandas 3.0+ uses pyarrow string backend by default, which can cause
# ArrowTypeError during pytest session finish when coverage data is serialized.
pd.options.mode.string_storage = "python"

# Add src directory to sys.path so pytest can resolve validators module
# (validators is a top-level package at src/validators/, separate from worldenergydata)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from worldenergydata.testing.performance import TestPerformanceTracker

# ==============================================================================
# COMMON FIXTURES - Available to all tests
# ==============================================================================


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root: Path) -> Path:
    """Return the test data directory, creating it if needed."""
    test_data = project_root / "tests" / "fixtures"
    test_data.mkdir(parents=True, exist_ok=True)
    return test_data


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for test files (auto-cleaned)."""
    return tmp_path


@pytest.fixture
def sample_production_data() -> pd.DataFrame:
    """Generate sample production data for testing.

    Returns a DataFrame with 36 months of production data mimicking
    BSEE production report format.
    """
    np.random.seed(42)  # Reproducible results

    # Generate 36 months of data
    n_months = 36
    base_date = datetime(2022, 1, 1)
    dates = [base_date + timedelta(days=30 * i) for i in range(n_months)]

    # Simulate declining production
    initial_oil = 10000  # bbls/month
    decline_rate = 0.05  # 5% monthly decline

    oil_production = [
        initial_oil * (1 - decline_rate) ** i + np.random.normal(0, 500)
        for i in range(n_months)
    ]
    oil_production = [max(0, p) for p in oil_production]

    # Gas production with GOR ~ 2000 scf/bbl
    gas_production = [
        oil * 2000 + np.random.normal(0, 100000) for oil in oil_production
    ]
    gas_production = [max(0, g) for g in gas_production]

    # Water production increases over time
    water_production = [
        1000 * (1.02**i) + np.random.normal(0, 200) for i in range(n_months)
    ]
    water_production = [max(0, w) for w in water_production]

    df = pd.DataFrame(
        {
            "production_date": dates,
            "api_well_number": "608124003301",
            "oil_production_bbl": oil_production,
            "gas_production_mcf": gas_production,
            "water_production_bbl": water_production,
            "days_on_production": [
                28 + np.random.randint(-3, 4) for _ in range(n_months)
            ],
            "status": ["PRODUCING"] * n_months,
        }
    )

    return df


@pytest.fixture
def sample_well_data() -> Dict[str, Any]:
    """Generate sample well data for testing.

    Returns a dictionary mimicking BSEE well header data.
    """
    return {
        "api_well_number": "608124003301",
        "well_name": "JULIA A-001",
        "field": "JULIA",
        "block": "GC 627",
        "area": "GREEN CANYON",
        "water_depth_ft": 7087.0,
        "total_depth_ft": 23500.0,
        "spud_date": datetime(2021, 3, 15),
        "completion_date": datetime(2021, 11, 20),
        "operator": "SHELL OFFSHORE INC",
        "well_status": "PRODUCING",
        "well_type": "OIL",
        "reservoir": "MIOCENE",
        "latitude": 27.8501,
        "longitude": -90.3422,
    }


@pytest.fixture
def reset_environment():
    """Reset environment variables after test.

    Saves current environment, allows test to modify it,
    then restores original environment after test completes.
    """
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def assert_dataframe_equal() -> Callable:
    """Provide a helper function for DataFrame equality assertion.

    Returns a callable that compares two DataFrames with detailed error messages.
    """

    def _assert_equal(
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        check_dtype: bool = True,
        check_index: bool = True,
    ) -> None:
        """Assert two DataFrames are equal.

        Args:
            df1: First DataFrame
            df2: Second DataFrame
            check_dtype: Whether to check column dtypes
            check_index: Whether to check index equality

        Raises:
            AssertionError: If DataFrames are not equal
        """
        # Check shape
        assert df1.shape == df2.shape, f"Shape mismatch: {df1.shape} vs {df2.shape}"

        # Check columns
        assert list(df1.columns) == list(
            df2.columns
        ), f"Column mismatch: {list(df1.columns)} vs {list(df2.columns)}"

        # Check dtypes
        if check_dtype:
            for col in df1.columns:
                assert (
                    df1[col].dtype == df2[col].dtype
                ), f"Dtype mismatch for column {col}: {df1[col].dtype} vs {df2[col].dtype}"

        # Check index
        if check_index:
            assert df1.index.equals(df2.index), "Index mismatch"

        # Check values
        pd.testing.assert_frame_equal(df1, df2, check_dtype=check_dtype)

    return _assert_equal


@pytest.fixture
def mock_excel_file(tmp_path: Path) -> Path:
    """Create a mock Excel file for testing.

    Creates a simple Excel file with sample data.
    """
    excel_path = tmp_path / "test_data.xlsx"

    # Create sample data
    df = pd.DataFrame(
        {
            "api_well_number": ["608124003301", "608124003302"],
            "oil_bbls": [10000.0, 8000.0],
            "gas_mcf": [20000000.0, 16000000.0],
        }
    )

    df.to_excel(excel_path, index=False)
    return excel_path


@pytest.fixture
def mock_yaml_config(tmp_path: Path) -> Path:
    """Create a mock YAML config file for testing."""
    import yaml

    yaml_path = tmp_path / "config.yml"
    config = {
        "meta": {
            "library": "worldenergydata",
            "basename": "test_config",
            "mode": "enhanced",
        },
        "data": {"well": True, "production": True, "war": False},
        "processing": {"in_memory": True, "chunk_size": 10000},
    }

    with open(yaml_path, "w") as f:
        yaml.dump(config, f)

    return yaml_path


@pytest.fixture
def sample_csv_file(tmp_path: Path, sample_production_data: pd.DataFrame) -> Path:
    """Create a sample CSV file from production data."""
    csv_path = tmp_path / "production_data.csv"
    sample_production_data.to_csv(csv_path, index=False)
    return csv_path


# ==============================================================================
# PERFORMANCE TRACKING
# ==============================================================================

# Initialize global tracker lazily. Collection-only and fully deselected sessions
# must not open the performance database.
_performance_tracker = None
_performance_db_path = None
_TREE_GUARD_PARENT_ENV = "WORLDENERGYDATA_TREE_GUARD_PARENT"


def _tree_git_environment():
    """Prevent inherited Git bindings from selecting another checkout."""
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)
    return env


def _tree_git(root, *arguments):
    """Run a read-only Git command against the selected checkout."""
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        env=_tree_git_environment(),
        capture_output=True,
        check=False,
    )


def _tree_changes(root):
    """Return changed, deleted and new paths, using NUL-delimited Git status."""
    result = _tree_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    result.check_returncode()
    changes = {}
    entries = iter(result.stdout.split(b"\0"))
    for entry in entries:
        if not entry:
            continue
        flags = entry[:2].decode("ascii")
        path = os.fsdecode(entry[3:])
        if flags == "??" or "A" in flags:
            kind = "new"
        elif "D" in flags:
            kind = "deleted"
        else:
            kind = "changed"
        changes[path] = kind
        if "R" in flags or "C" in flags:
            original = os.fsdecode(next(entries))
            if "R" in flags:
                changes[original] = "deleted"
                changes[path] = "new"
    return changes


def _declared_tree_outputs(config):
    """Read exact file and directory destinations from active session options."""
    files, directories = [], []
    junit = config.getoption("xmlpath", default=None)
    if junit:
        files.append(os.path.expanduser(os.path.expandvars(junit)))
    benchmark = config.getoption("benchmark_json", default=None)
    if benchmark is not None:
        files.append(benchmark.name)
    plugin = config.pluginmanager.getplugin("_cov")
    controller = getattr(plugin, "cov_controller", None)
    cov = getattr(controller, "cov", None)
    if cov is not None:
        files.append(cov.config.data_file)
        defaults = {
            "html": cov.config.html_dir,
            "xml": cov.config.xml_output,
            "json": cov.config.json_output,
            "lcov": cov.config.lcov_output,
        }
        reports = config.getoption("cov_report", default={})
        if not isinstance(reports, dict):
            reports = dict.fromkeys(reports)
        for kind, destination in reports.items():
            if kind in ("term", "term-missing", ""):
                continue
            destination = destination or defaults.get(kind)
            if kind == "annotate" and destination is None:
                files.extend(
                    name + ",cover" for name in cov.get_data().measured_files()
                )
            elif destination is not None:
                outputs = directories if kind in ("html", "annotate") else files
                outputs.append(destination)

    def absolute(paths):
        """Keep plug-in pathname semantics without resolving symlink targets."""
        return {
            Path(os.path.abspath(config._tree_guard_cwd / path))
            for path in paths
            if path not in ("-", "<stdout>", "<stderr>")
        }

    return absolute(files), absolute(directories)


def _undeclared_tree_changes(config, changes):
    """Exclude only exact requested files and descendants of requested folders."""
    files, directories = _declared_tree_outputs(config)
    result = {}
    for path, kind in changes.items():
        absolute = Path(os.path.abspath(config._tree_guard_root / path))
        if absolute in files:
            continue
        if any(
            absolute == folder or folder in absolute.parents for folder in directories
        ):
            continue
        result[path] = kind
    return result


def _tree_content(path):
    """Digest initially dirty bytes, preserving symlink and absent-file state."""
    if path.is_symlink():
        return "symlink", hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError:
        return None
    return "file", digest.hexdigest()


def _configure_tree_guard(config):
    """Capture pre-existing work only when the developer requests that mode."""
    if hasattr(config, "workerinput"):
        return
    config._tree_guard_child = False
    config._tree_guard_parent_set = False
    config._tree_guard_root = None
    config._tree_guard_cwd = Path.cwd()
    config._tree_guard_initial = {}
    config._tree_guard_error = None
    config._tree_guard_note = None
    if shutil.which("git") is None:
        config._tree_guard_note = "Git is not available"
        return
    result = _tree_git(config.rootpath, "rev-parse", "--show-toplevel")
    if result.returncode:
        if b"not a git repository" in result.stderr.lower():
            config._tree_guard_note = "outside a Git checkout"
        else:
            config._tree_guard_error = "Git could not resolve the checkout"
        return
    config._tree_guard_root = Path(os.fsdecode(result.stdout).strip())
    parent = os.environ.get(_TREE_GUARD_PARENT_ENV)
    if parent == str(config._tree_guard_root):
        config._tree_guard_child = True
        return
    config._tree_guard_previous_parent = parent
    os.environ[_TREE_GUARD_PARENT_ENV] = str(config._tree_guard_root)
    config._tree_guard_parent_set = True
    if config.getoption("allow_existing_tree_changes"):
        try:
            config._tree_guard_initial = {
                path: _tree_content(config._tree_guard_root / path)
                for path in _tree_changes(config._tree_guard_root)
            }
        except (OSError, subprocess.SubprocessError):
            config._tree_guard_error = "Git could not record the initial tree"


def _finish_tree_guard(session):
    """Fail the controlling session when its tree does not meet the criterion."""
    config = session.config
    if hasattr(config, "workerinput") or config._tree_guard_child:
        return
    if config._tree_guard_note:
        print("Tree preservation check did not run: " + config._tree_guard_note + ".")
        return
    error = config._tree_guard_error
    changes = {}
    if error is None:
        try:
            changes = _tree_changes(config._tree_guard_root)
            for path, initial in config._tree_guard_initial.items():
                current = _tree_content(config._tree_guard_root / path)
                if current == initial:
                    changes.pop(path, None)
                else:
                    changes[path] = changes.get(
                        path, "deleted" if current is None else "changed"
                    )
            changes = _undeclared_tree_changes(config, changes)
        except (OSError, subprocess.SubprocessError):
            error = "The final tree could not be read"
    if not changes and error is None:
        return
    print("\nRepository tree preservation failed:")
    if error:
        print("  " + error)
    for path, kind in sorted(changes.items())[:50]:
        print(f"  {kind}: {repr(path)[1:-1]}")
    if len(changes) > 50:
        print(f"  {len(changes) - 50} additional path(s) not shown")
    print(
        "Use --allow-existing-tree-changes for pre-existing work; "
        "see docs/development/index.md."
    )
    if session.exitstatus == pytest.ExitCode.OK:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def _restore_tree_guard_environment(config):
    """Restore inherited parent state after the owning session finishes."""
    if not getattr(config, "_tree_guard_parent_set", False):
        return
    previous = config._tree_guard_previous_parent
    if previous is None:
        os.environ.pop(_TREE_GUARD_PARENT_ENV, None)
    else:
        os.environ[_TREE_GUARD_PARENT_ENV] = previous
    config._tree_guard_parent_set = False


def pytest_unconfigure(config):
    """Also restore parent state when configuration or session setup fails."""
    _restore_tree_guard_environment(config)


def pytest_addoption(parser):
    """Register performance output and tree-preservation options."""
    parser.addoption(
        "--allow-existing-tree-changes",
        action="store_true",
        default=False,
        help="Compare existing dirty content and report new changes; see docs/development/index.md",
    )
    parser.addoption(
        "--performance-db-path",
        default=None,
        help="SQLite path for pytest performance records",
    )


def _get_performance_tracker(config):
    """Construct the tracker only when pytest is about to execute a test."""
    global _performance_tracker
    if _performance_tracker is None:
        db_path = _performance_db_path
        if db_path is None:
            # Xdist gives each worker its own session temporary directory.
            db_path = config._tmp_path_factory.getbasetemp() / ".test_performance.db"
        _performance_tracker = TestPerformanceTracker(db_path)
    return _performance_tracker


def pytest_configure(config):
    """Capture performance configuration and the initial tree state."""
    _configure_tree_guard(config)
    global _performance_db_path
    db_path = config.getoption("performance_db_path")
    _performance_db_path = Path(db_path) if db_path is not None else None


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Called before test setup."""
    _get_performance_tracker(item.config).start_test(item.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Called to create test report."""
    outcome = yield
    report = outcome.get_result()

    # Only record on test call (not setup/teardown)
    if report.when == "call" and _performance_tracker:
        _performance_tracker.end_test(item.nodeid, report)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Check tree preservation and report performance at session finish."""
    try:
        _finish_tree_guard(session)
    finally:
        _restore_tree_guard_environment(session.config)
    if _performance_tracker:
        summary = _performance_tracker.get_session_summary()

        print("\n" + "=" * 60)
        print("Test Performance Summary")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print(f"Average Duration: {summary['avg_duration']:.3f}s")
        print(f"Success Rate: {summary['success_rate']:.1f}%")

        # Check for regressions
        from worldenergydata.testing.performance import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer(_performance_tracker.db)
        regressions = analyzer.detect_regressions(lookback_days=7)

        if regressions:
            print("\n⚠️  Performance Regressions Detected:")
            for reg in regressions[:3]:
                print(f"  - {reg['test_name']}: {reg['regression_factor']:.2f}x slower")

        print("=" * 60)


# Skip collection of experimental/archived test files
def pytest_ignore_collect(collection_path, config):
    """Skip collection of experimental and archived test files.

    Test directory structure (2025-01):
        tests/
        ├── unit/           # Module-grouped unit tests
        │   ├── bsee/
        │   ├── fdas/
        │   ├── marine_safety/
        │   ├── hse/
        │   ├── reporting/
        │   ├── vessel_hull_models/
        │   └── well_production_dashboard/
        ├── integration/    # Integration tests
        │   └── modules/
        ├── e2e/            # End-to-end tests
        ├── fixtures/       # Test fixtures
        ├── helpers/        # Test helpers
        └── _archived/      # Legacy tests (not collected)
            ├── legacy/
            └── validation_runs/
    """
    import re

    path_str = str(collection_path)
    basename = collection_path.name

    # Skip query_*.py files (exploratory scripts)
    if basename.startswith("query_") and basename.endswith("_test.py"):
        return True

    # Skip _archive and _archived directories and all subdirectories (consolidated 2025-01)
    if "/_archive/" in path_str or path_str.endswith("/_archive"):
        return True
    if "/_archived/" in path_str or path_str.endswith("/_archived"):
        return True

    # Legacy pattern - keep for backward compatibility
    if "_archived_tests" in path_str:
        return True

    # Skip 2025-* dated experimental directories
    if re.search(r"202\d-\d{2}-\d{2}", basename):
        return True

    # Skip directories explicitly listed in norecursedirs but not being honored
    excluded_patterns = [
        "comprehensive-report-system",
        "financial-analysis-sme-code",
        "well-data-verification",
        "/legacy/",
        "legacy_",
        "custom_scripts",
    ]

    for pattern in excluded_patterns:
        if pattern in path_str:
            return True

    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent

    # Issue #2433: skip known broken collection targets until missing modules/data are restored.
    broken_module_tests = {
        # Duplicate basename clashes with tests/integration/workflows/test_end_to_end.py
        Path("tests/modules/fdas/integration/test_end_to_end.py"),
        # Missing sodir_module.* package
        Path("tests/modules/sodir-integration/test_api_client.py"),
        Path("tests/modules/sodir-integration/test_cross_regional_validation.py"),
        Path("tests/modules/sodir-integration/test_integration.py"),
        Path("tests/modules/sodir-integration/test_performance.py"),
        # Missing well production dashboard modules
        Path("tests/modules/well_production_dashboard/test_monitoring.py"),
        Path(
            "tests/modules/well_production_dashboard/test_well_production_dashboard.py"
        ),
        # Missing proxy comparison module
        Path("tests/unit/cost/test_proxy_comparison.py"),
        # Duplicate basename clash with tests/modules/marine_safety/test_models.py
        Path("tests/unit/hse/database/test_models.py"),
        # Duplicate basename clashes with tests/modules/hse/importers/*
        Path("tests/unit/hse/importers/test_bsee_incidents_importer_url.py"),
        Path("tests/unit/hse/importers/test_bsee_penalties_importer_url.py"),
        Path("tests/unit/hse/importers/test_bsee_statistics_importer_url.py"),
        # Missing repo_yml_status.csv fixture/input
        Path("tests/unit/pipeline_ci_cd/test_pipeline_utils.py"),
    }

    broken_module_dirs = {
        # Missing tests.modules.marine_safety.fixtures package for directory conftest imports
        Path("tests/unit/marine_safety"),
    }

    try:
        rel_path = Path(collection_path).resolve().relative_to(repo_root)
    except ValueError:
        return False

    # Statistics is an optional member extra (#1313). Collect its tests whenever
    # installed, and let import errors in an installed backend surface normally.
    if rel_path.parts[:4] == ("tests", "unit", "metocean", "statistics"):
        from importlib.util import find_spec

        if find_spec("metocean_stats") is None:
            return True

    if rel_path in broken_module_tests:
        return True

    for dir_pattern in broken_module_dirs:
        try:
            rel_path.relative_to(dir_pattern)
            return True
        except ValueError:
            continue

    return False
