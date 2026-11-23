import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

from worldenergydata.engine import engine

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "docs" / "registry" / "workflows.yaml"


def _load_registry():
    with REGISTRY_PATH.open() as fp:
        registry = yaml.safe_load(fp)
    assert registry["schema_version"] == 2
    return registry


def _workflow_cases():
    return _load_registry()["workflows"]


def _pythonpath_env():
    env = os.environ.copy()
    paths = [
        str(REPO_ROOT / "src"),
        str(REPO_ROOT.parent / "assetutilities" / "src"),
    ]
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def _expected_oil_bbl(input_path: Path) -> float:
    with input_path.open() as fp:
        cfg = yaml.safe_load(fp)
    total = 0.0
    for group in cfg["data"]["groups"]:
        for file_name in group["production"]["files"]:
            csv_path = input_path.parent / file_name
            df = pd.read_csv(csv_path)
            total += pd.to_numeric(df["OIL_PRODUCTION"], errors="raise").sum()
    return total


def _get_nested(payload, dotted_path):
    value = payload
    for part in dotted_path.split("."):
        value = value[part]
    return value


def _assert_json_expectations(workflow, output_root=REPO_ROOT):
    for assertion in workflow.get("assertions", {}).get("json", []):
        with (output_root / assertion["path"]).open() as fp:
            payload = json.load(fp)

        for dotted_path, expected in assertion.get("equals", {}).items():
            assert _get_nested(payload, dotted_path) == expected

        for dotted_path, expected in assertion.get("approx", {}).items():
            assert _get_nested(payload, dotted_path) == pytest.approx(expected)


def _assert_csv_expectations(workflow, output_root=REPO_ROOT):
    for assertion in workflow.get("assertions", {}).get("csv", []):
        df = pd.read_csv(output_root / assertion["path"])

        if "row_count" in assertion:
            assert len(df) == assertion["row_count"]

        for column, expected_counts in assertion.get("column_counts", {}).items():
            actual_counts = df[column].value_counts().sort_index().to_dict()
            assert actual_counts == expected_counts

        for column, expected_sum in assertion.get("column_sums", {}).items():
            actual_sum = pd.to_numeric(df[column], errors="raise").sum()
            assert actual_sum == pytest.approx(expected_sum)


def _assert_bsee_production_summary(workflow, input_path: Path, output_root=REPO_ROOT):
    if workflow["basename"] != "bsee":
        return

    summary_outputs = [
        output
        for output in workflow["outputs"]
        if output.endswith(".csv") and "prod_summ_" in output
    ]
    if not summary_outputs:
        return

    expected_oil_bbl = _expected_oil_bbl(input_path)
    summary_df = pd.read_csv(output_root / summary_outputs[0])
    actual_oil_bbl = summary_df["O_CUMMULATIVE_PROD_MMBBL"].sum() * 1_000_000
    assert actual_oil_bbl == pytest.approx(expected_oil_bbl)

    summary_json = (output_root / summary_outputs[0]).with_suffix(".json")
    with summary_json.open() as fp:
        payload = json.load(fp)
    assert payload["totals"]["oil_bbl"] == pytest.approx(expected_oil_bbl)


@pytest.fixture
def workflow_root(workflow, tmp_path):
    """Copy adjacent input files and registered fixtures without prior outputs."""
    source_dir = REPO_ROOT / Path(workflow["input"]).parent
    inputs = [
        path.relative_to(REPO_ROOT) for path in source_dir.iterdir() if path.is_file()
    ]
    inputs.extend(workflow.get("data_source", {}).get("fixtures", []))
    for relative_path in dict.fromkeys(inputs):
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative_path, destination)
    return tmp_path


@pytest.mark.parametrize(
    "workflow",
    _workflow_cases(),
    ids=[workflow["id"] for workflow in _workflow_cases()],
)
def test_registry_workflow_outputs(workflow, workflow_root):
    input_path = workflow_root / workflow["input"]

    cfg = engine(inputfile=str(input_path))

    assert cfg is not None
    assert cfg["basename"] == workflow["basename"]

    for output in workflow["outputs"]:
        assert (workflow_root / output).exists(), output

    _assert_bsee_production_summary(workflow, input_path, workflow_root)
    _assert_json_expectations(workflow, workflow_root)
    _assert_csv_expectations(workflow, workflow_root)


@pytest.mark.parametrize(
    "workflow",
    _workflow_cases(),
    ids=[workflow["id"] for workflow in _workflow_cases()],
)
def test_module_yaml_invocation_exits_zero(workflow, workflow_root):
    result = subprocess.run(
        [sys.executable, "-m", "worldenergydata", workflow["input"]],
        cwd=workflow_root,
        env=_pythonpath_env(),
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr


def test_module_help_uses_typer_cli():
    result = subprocess.run(
        [sys.executable, "-m", "worldenergydata", "--help"],
        cwd=REPO_ROOT,
        env=_pythonpath_env(),
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    help_output = result.stdout + result.stderr
    assert "BSEE" in help_output
    assert "marine-safety" in help_output


# --------------------------------------------------------------------------- #
# Versioned-routing schema (schema_version 2): optional algorithm-version triple
# per row. Guards the multi-version case so a caller can resolve a pinned
# `<repo>:<id>@N` or the latest-stable default unambiguously.
# --------------------------------------------------------------------------- #
_VERSION_STATUSES = {"stable", "deprecated", "experimental", "retired"}


def test_workflow_registry_version_invariants() -> None:
    workflows = _load_registry()["workflows"]  # also asserts schema_version == 2
    groups: dict[str, list[dict]] = {}
    for row in workflows:
        groups.setdefault(str(row["id"]), []).append(row)

    for wid, rows in groups.items():
        # Any version field present must be a positive int with a valid status.
        for row in rows:
            if "version" in row:
                assert isinstance(row["version"], int) and row["version"] >= 1, wid
            assert row.get("status", "stable") in _VERSION_STATUSES, wid
        if len(rows) == 1:
            continue
        # A workflow id with multiple rows is a genuine multi-version workflow:
        # every row must pin a distinct version and exactly one latest-stable.
        versions = [row.get("version") for row in rows]
        assert all(isinstance(v, int) for v in versions), f"{wid}: versions required"
        assert len(set(versions)) == len(versions), f"{wid}: duplicate versions"
        latest = [row for row in rows if row.get("latest")]
        assert len(latest) == 1, f"{wid}: need exactly one latest:true row"
        assert (
            latest[0].get("status", "stable") == "stable"
        ), f"{wid}: latest not stable"
