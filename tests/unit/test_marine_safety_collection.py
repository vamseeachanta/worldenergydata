"""Collection contract from issue #1239 and compatibility pack gate C3 (2026)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def marine_collection(tmp_path_factory):
    """Compare independent disk and pytest inventories, including skipped files.

    Issue #1239 requires every test file, so the expected set comes from disk,
    not from pytest's item list. Module-level skips still produce file reports.
    Gate C3 requires no collection errors. No numerical tolerance is involved.
    A directory exclusion or an import error must fail this test.
    """
    tmp_path = tmp_path_factory.mktemp("marine-collection")
    root = Path(__file__).resolve().parents[2]
    folders = [
        root / "tests/unit/marine_safety",
        root / "tests/modules/marine_safety",
        root / "tests/marine_safety",
    ]
    expected = {
        path.relative_to(root).as_posix()
        for folder in folders
        # Source: pyproject.toml, tool.pytest.ini_options.python_files.
        for pattern in ("test_*.py", "*_test.py")
        for path in folder.rglob(pattern)
    }
    plugin = tmp_path / "collection_inventory.py"
    inventory = tmp_path / "inventory.json"
    plugin.write_text(
        "import json, os\n"
        "reports = {}\n"
        "def pytest_collectreport(report):\n"
        "    if report.nodeid.endswith('.py'):\n"
        "        reports[report.nodeid] = report.outcome\n"
        "def pytest_sessionfinish(session):\n"
        "    with open(os.environ['MARINE_COLLECTION_INVENTORY'], 'w') as stream:\n"
        "        items = []\n"
        "        for item in session.items:\n"
        "            marker = item.get_closest_marker('xfail')\n"
        "            skip = item.get_closest_marker('skip')\n"
        "            items.append(dict(nodeid=item.nodeid,\n"
        "                strict=marker.kwargs.get('strict') if marker else None,\n"
        "                raises=marker.kwargs['raises'].__name__\n"
        "                    if marker and 'raises' in marker.kwargs else None,\n"
        "                reason=marker.kwargs.get('reason') if marker else None,\n"
        "                skip_reason=skip.kwargs.get('reason') if skip else None))\n"
        "        json.dump(dict(files=reports, items=items), stream)\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), *sys.path])
    env["MARINE_COLLECTION_INVENTORY"] = str(inventory)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *map(str, folders),
            "--collect-only",
            "--continue-on-collection-errors",
            "--import-mode=importlib",
            "--allow-existing-tree-changes",
            "--basetemp",
            str(tmp_path / "collection"),
            "--cov-report=term",
            "--cov-report=html:" + str(tmp_path / "html"),
            "--cov-report=xml:" + str(tmp_path / "coverage.xml"),
            "--cov-report=json:" + str(tmp_path / "coverage.json"),
            "-p",
            "no:cacheprovider",
            "-p",
            "collection_inventory",
            "-q",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert inventory.exists(), result.stdout + result.stderr
    data = json.loads(inventory.read_text(encoding="utf-8"))
    return expected, data, result


def test_every_marine_safety_file_is_collected(marine_collection):
    """Issue #1239: disk inventory equals collected file inventory, with no errors."""
    expected, data, result = marine_collection
    reports = data["files"]
    assert set(reports) == expected, {
        "missing": sorted(expected - set(reports)),
        "unexpected": sorted(set(reports) - expected),
    }
    assert len(reports) == len(expected)
    assert not {
        node: outcome for node, outcome in reports.items() if outcome == "failed"
    }
    assert result.returncode == 0, result.stdout + result.stderr


def test_baseline_markers_are_exact_and_strict(marine_collection):
    """Drafts define the node set; established causes define exception classes.

    Gate C3 in the compatibility pack (2026) permits no omitted files, including
    known failures. Every listed failure must still collect and must retain a
    strict, exception-specific xfail rather than an exclusion or a broad mark.
    """
    _, data, _ = marine_collection
    root = Path(__file__).resolve().parents[2]
    failures = json.loads(
        (root / "tests/unit/marine_safety/baseline_failures.json").read_text(
            encoding="utf-8"
        )
    )
    items = {item["nodeid"]: item for item in data["items"]}
    expected = {entry["nodeid"] for entry in failures}
    assert len(expected) == len(failures), "Duplicate baseline node"
    actual = {
        node
        for node, item in items.items()
        if item["reason"]
        and "Canonical marine-safety docs/ISSUES_DRAFT.md" in item["reason"]
    }
    assert actual == expected
    for entry in failures:
        item = items[entry["nodeid"]]
        assert item["strict"] is True
        assert item["raises"] == entry["exception"]
        assert "draft " + entry["draft"] + " (#1351)" in item["reason"]


def test_unavailable_classifier_dependencies_skip_collected_nodes(marine_collection):
    """Issue #1239 requires a reasoned skip for absent optional dependencies."""
    import importlib.util

    _, data, _ = marine_collection
    missing = [
        name
        for name in ("transformers", "torch")
        if importlib.util.find_spec(name) is None
    ]
    items = [
        item
        for item in data["items"]
        if item["nodeid"].startswith(
            "tests/unit/marine_safety/analysis/test_llm_classifier.py::"
        )
    ]
    assert items
    if missing:
        for item in items:
            assert item["skip_reason"] == (
                "Optional classifier dependencies unavailable: " + ", ".join(missing)
            )
