"""Riser metadata and catalog arithmetic; no engineering acceptance limits.

Numeric fixtures are either identified catalog dimensions or synthetic inputs.
Geometry bounds follow a hollow circular tube: ID = OD - wall - wall > 0.
"""

import json
import runpy
from dataclasses import asdict
from math import inf, nan
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError
from worldenergydata.vessel_fleet.loaders.drilling_riser_loader import (
    DrillingRiserLoader,
)
from worldenergydata.vessel_fleet.models.drilling_riser import (
    AuxiliaryLineEntry,
    RiserJointEntry,
)
from worldenergydata.vessel_fleet.schemas.drilling_riser import RiserJointSchema


@pytest.mark.parametrize("od,buoyed,expected", [(21, 49, 7 / 3), (18.75, 44, 176 / 75)])
def test_ratio_hand_calculation(od, buoyed, expected):
    """Issue #1138 catalog inputs: 49/21 = 7/3; 44/(75/4) = 176/75."""
    joint = RiserJointEntry(
        component_id="synthetic",
        od_in=od,
        buoyancy_od_in=buoyed,
        buoyancy_coverage_pct=100,
    )
    assert joint.buoyancy_od_ratio == pytest.approx(expected)


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"od_in": None},
        {"od_in": 0},
        {"od_in": -1},
        {"od_in": nan},
        {"od_in": inf},
        {"buoyancy_od_in": None},
        {"buoyancy_od_in": 0},
        {"buoyancy_od_in": -1},
        {"buoyancy_od_in": nan},
        {"buoyancy_od_in": inf},
        {"buoyancy_coverage_pct": 0},
        {"buoyancy_coverage_pct": None},
        {"buoyancy_coverage_pct": nan},
        {"buoyancy_coverage_pct": inf},
    ],
)
def test_ratio_unavailable(values):
    """Synthetic incomplete/invalid inputs have no usable ratio, not a zero ratio."""
    defaults = {"od_in": 21, "buoyancy_od_in": 49, "buoyancy_coverage_pct": 100}
    defaults.update(values)
    if not values:
        defaults.pop("buoyancy_od_in")
    assert RiserJointEntry("synthetic", **defaults).buoyancy_od_ratio is None


def test_legacy_defaults():
    assert RiserJointSchema(COMPONENT_ID="synthetic").RISER_CLASS == "drilling"
    assert RiserJointEntry("synthetic").riser_class == "drilling"
    assert RiserJointEntry("synthetic").auxiliary_lines == ()


def test_signed_submerged_weight():
    """Packaged catalog RJ-21-75-BUOY records net uplift of -4.2 kips."""
    record = RiserJointSchema(COMPONENT_ID="synthetic", WEIGHT_WATER_KIPS="-4.2")
    assert record.WEIGHT_WATER_KIPS == -4.2


@pytest.mark.parametrize("riser_class", ["drilling", "lift", "production"])
def test_class_and_bundle_round_trip(riser_class):
    """Synthetic auxiliary OD=4, wall=0.5 implies ID=4-0.5-0.5=3 inches."""
    line = AuxiliaryLineEntry(
        function="hydraulic return", od_in=4, wall_thickness_in=0.5
    )
    schema = RiserJointSchema(
        COMPONENT_ID="synthetic",
        RISER_CLASS=riser_class,
        AUXILIARY_LINES=[asdict(line)],
        INTERNAL_MEDIUM="solids-laden water",
        DESIGN_WATER_DEPTH_M=1234,
    )
    recovered = RiserJointSchema.model_validate_json(schema.model_dump_json())
    assert recovered.AUXILIARY_LINES == (line,)
    assert recovered.RISER_CLASS == riser_class
    assert recovered.INTERNAL_MEDIUM == "solids-laden water"
    assert (
        recovered.DESIGN_WATER_DEPTH_M == 1234
    )  # Synthetic caller input, not a rating.


@pytest.mark.parametrize(
    "values",
    [
        {"function": ""},
        {"function": "  "},
        {"od_in": 0},
        {"od_in": inf},
        {"wall_thickness_in": 0},
        {"wall_thickness_in": nan},
        {"wall_thickness_in": 2},
        {"wall_thickness_in": 3},
    ],
)
def test_invalid_auxiliary_geometry(values):
    """Synthetic OD=4: wall >=2 closes the bore; zero/nonfinite lengths are invalid."""
    fields = {"function": "return", "od_in": 4, "wall_thickness_in": 0.5}
    fields.update(values)
    with pytest.raises(ValueError):
        AuxiliaryLineEntry(**fields)
    with pytest.raises(ValidationError):
        RiserJointSchema(COMPONENT_ID="synthetic", AUXILIARY_LINES=[fields])


@pytest.mark.parametrize(
    "fields",
    [
        {"RISER_CLASS": "unknown"},
        {"AUXILIARY_LINES": "invalid json"},
        {"AUXILIARY_LINES": '{"function":"return"}'},
        {"DESIGN_WATER_DEPTH_M": -1},
        {"DESIGN_WATER_DEPTH_M": inf},
    ],
)
def test_invalid_extension_fields(fields):
    with pytest.raises(ValidationError):
        RiserJointSchema(COMPONENT_ID="synthetic", **fields)


def test_typed_loader_preserves_catalog():
    """Catalog anchors independently reduce to 7/3, 176/75 and 55/24.

    Packaged drilling_riser_components.csv, observed 2026-10-20: all five
    buoyed rows span 55/24 to 176/75. No margin or industry limit is assumed.
    A failure requests review of new data, rather than declaring it wrong.
    """
    loader = DrillingRiserLoader()
    original = loader.load().copy(deep=True)
    joints = loader.get_riser_joint_entries()
    expected = {
        "RJ-21-75-BUOY": 7 / 3,
        "RJ-18.75-75-BUOY": 176 / 75,
        "RJ-21-75-NOV-MERLIN-BUOY": 7 / 3,
        "RJ-21-75-CAM-BUOY": 7 / 3,
        "RJ-24-75-BUOY": 55 / 24,
    }
    buoyed = {joint.component_id: joint for joint in joints if joint.has_buoyancy}
    for component_id, ratio in expected.items():
        assert buoyed[component_id].buoyancy_od_ratio == pytest.approx(ratio)
    for joint in buoyed.values():
        assert joint.buoyancy_od_in > joint.od_in
        assert joint.buoyancy_od_ratio is not None
        assert 55 / 24 <= joint.buoyancy_od_ratio <= 176 / 75, (
            "new data departs from the observed range, review the row"
        )
    assert all(joint.riser_class == "drilling" for joint in joints)
    assert loader.get_riser_joint_entries(riser_class="lift") == []
    pd.testing.assert_frame_equal(loader.load(), original)


def test_extended_csv_loading(tmp_path):
    """Synthetic bundle rows exercise optional columns without changing catalog data."""
    template = DrillingRiserLoader().get_riser_joints().iloc[[0]].copy()
    template["COMPONENT_ID"] = "synthetic"
    template["RISER_CLASS"] = "lift"
    template["AUXILIARY_LINES"] = json.dumps(
        [
            {"function": "return", "od_in": 4, "wall_thickness_in": 0.5},
        ]
    )
    template["INTERNAL_MEDIUM"] = "solids-laden water"
    template["DESIGN_WATER_DEPTH_M"] = 1234  # Synthetic input; no rated depth claim.
    template.to_csv(tmp_path / "drilling_riser_components.csv", index=False)
    loader = DrillingRiserLoader(tmp_path)
    (joint,) = loader.get_riser_joint_entries(riser_class="lift")
    assert joint.auxiliary_lines[0].function == "return"
    assert joint.auxiliary_lines[0].od_in == 4
    assert joint.internal_medium == "solids-laden water"
    assert joint.design_water_depth_m == 1234
    assert loader.get_riser_joint_entries(riser_class="production") == []


def test_empty_optional_csv_columns(tmp_path):
    template = DrillingRiserLoader().get_riser_joints().iloc[[0]].copy()
    for column in (
        "RISER_CLASS",
        "AUXILIARY_LINES",
        "INTERNAL_MEDIUM",
        "DESIGN_WATER_DEPTH_M",
    ):
        template[column] = ""
    template.to_csv(tmp_path / "drilling_riser_components.csv", index=False)
    (joint,) = DrillingRiserLoader(tmp_path).get_riser_joint_entries()
    assert joint.riser_class == "drilling"
    assert joint.auxiliary_lines == ()
    assert joint.internal_medium is None
    assert joint.design_water_depth_m is None


@pytest.mark.parametrize("value", [None, "", "  ", " drilling "])
def test_legacy_class_normalization(value):
    assert (
        RiserJointSchema(COMPONENT_ID="synthetic", RISER_CLASS=value).RISER_CLASS
        == "drilling"
    )


@pytest.mark.parametrize(
    "column,value",
    [
        ("RISER_CLASS", "unsupported"),
        ("AUXILIARY_LINES", "invalid json"),
        ("AUXILIARY_LINES", '[{"function":"return","od_in":4,"wall_thickness_in":3}]'),
    ],
)
def test_invalid_csv_metadata_reports_component(tmp_path, column, value):
    """Synthetic closed bore: OD=4 minus two walls of 3 cannot be positive."""
    template = DrillingRiserLoader().get_riser_joints().iloc[[0]].copy()
    template["COMPONENT_ID"] = "synthetic"
    template[column] = value
    template.to_csv(tmp_path / "drilling_riser_components.csv", index=False)
    with pytest.raises(ValueError, match="Invalid riser joint synthetic"):
        DrillingRiserLoader(tmp_path).get_riser_joint_entries()


def test_missing_csv(tmp_path):
    assert DrillingRiserLoader(tmp_path).get_riser_joint_entries() == []


def test_worked_example():
    """Catalog input 49/21 reduces by seven to 7/3; not code-derived output."""
    example_path = (
        Path(__file__).resolve().parents[3] / "examples/vessel_fleet/riser_metadata.py"
    )
    example = runpy.run_path(str(example_path))
    result = example["catalog_example"]()
    assert result["bare_od_in"] == 21
    assert result["buoyancy_od_in"] == 49
    assert result["buoyancy_od_ratio"] == pytest.approx(7 / 3)
