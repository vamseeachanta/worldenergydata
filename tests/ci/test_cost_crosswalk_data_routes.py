"""Data-only crosswalk/register edits must execute identity validation in CI."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "path",
    [
        "data/modules/cost/curated/project_field_crosswalk.csv",
        "data/modules/cost/curated/project_field_crosswalk.manifest.json",
        "data/modules/cost/curated/sanctioned_projects.csv",
        "data/modules/cost/staging/batch/projects.csv",
    ],
)
def test_cost_data_runs_crosswalk_validation(path):
    spec = importlib.util.spec_from_file_location(
        "selector", ROOT / "scripts/ci/select_test_targets.py"
    )
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    for select in (selector.select, selector.select_fast):
        assert "tests/unit/cost" in select([path], ROOT)["xdist"]
