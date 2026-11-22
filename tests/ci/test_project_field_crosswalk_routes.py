"""Catalog-only changes must execute the cost crosswalk contract."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "path",
    [
        "config/fields.yml",
        "src/worldenergydata/field_development/past_projects.yml",
        "scripts/cost/validate_project_field_crosswalk.py",
    ],
)
def test_crosswalk_input_routes(path):
    spec = importlib.util.spec_from_file_location(
        "selector", ROOT / "scripts/ci/select_test_targets.py"
    )
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    for select in (selector.select, selector.select_fast):
        assert (
            "tests/unit/cost/test_project_field_crosswalk.py"
            in select([path], ROOT)["xdist"]
        )
        if path == "src/worldenergydata/field_development/past_projects.yml":
            assert "tests/unit/field_development" in select([path], ROOT)["xdist"]
            assert (
                "tests/modules/field_development/test_past_projects.py"
                in select([path], ROOT)["xdist"]
            )
