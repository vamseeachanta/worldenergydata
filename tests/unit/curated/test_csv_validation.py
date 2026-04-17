"""Tests for curated CSV loading and Pydantic validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.subsea.models.mooring import (
    MooringComponentSpec,
    load_mooring_components,
)
from worldenergydata.subsea.models.rigid_jumper import (
    RigidJumperSpec,
    load_rigid_jumpers,
)

DATA_DIR = (
    Path(__file__).resolve().parents[3] / "data" / "modules" / "subsea" / "curated"
)
RIGID_JUMPER_CSV = DATA_DIR / "rigid_jumper_specs.csv"
MOORING_CSV = DATA_DIR / "mooring_components.csv"


class TestRigidJumperLoading:
    """Tests for rigid jumper CSV loading and validation."""

    def test_load_rigid_jumpers_returns_list(self):
        result = load_rigid_jumpers(RIGID_JUMPER_CSV)
        assert isinstance(result, list)
        assert len(result) >= 10

    def test_all_entries_are_rigid_jumper_spec(self):
        result = load_rigid_jumpers(RIGID_JUMPER_CSV)
        for entry in result:
            assert isinstance(entry, RigidJumperSpec)

    def test_rigid_jumper_required_fields_present(self):
        result = load_rigid_jumpers(RIGID_JUMPER_CSV)
        for entry in result:
            assert entry.component_id
            assert entry.manufacturer
            assert entry.od_in > 0
            assert entry.data_source

    def test_negative_od_raises_validation_error(self):
        with pytest.raises(ValidationError, match="OD must be positive"):
            RigidJumperSpec(
                component_id="BAD-1",
                manufacturer="Test",
                od_in=-1.0,
                wall_thickness_in=0.5,
                length_ft=20.0,
                material_grade="X-52",
                pressure_rating_psi=5000,
                data_source="test",
            )

    def test_zero_od_raises_validation_error(self):
        with pytest.raises(ValidationError, match="OD must be positive"):
            RigidJumperSpec(
                component_id="BAD-2",
                manufacturer="Test",
                od_in=0.0,
                wall_thickness_in=0.5,
                length_ft=20.0,
                material_grade="X-52",
                pressure_rating_psi=5000,
                data_source="test",
            )


class TestMooringLoading:
    """Tests for mooring component CSV loading and validation."""

    def test_load_mooring_components_returns_list(self):
        result = load_mooring_components(MOORING_CSV)
        assert isinstance(result, list)
        assert len(result) >= 10

    def test_all_entries_are_mooring_spec(self):
        result = load_mooring_components(MOORING_CSV)
        for entry in result:
            assert isinstance(entry, MooringComponentSpec)

    def test_mooring_required_fields_present(self):
        result = load_mooring_components(MOORING_CSV)
        for entry in result:
            assert entry.component_id
            assert entry.component_type
            assert entry.manufacturer
            assert entry.mbl_kn > 0
            assert entry.data_source

    def test_invalid_component_type_raises_validation_error(self):
        with pytest.raises(ValidationError, match="component_type must be one of"):
            MooringComponentSpec(
                component_id="BAD-1",
                component_type="invalid_type",
                manufacturer="Test",
                size_mm=84.0,
                mbl_kn=5000,
                data_source="test",
            )

    def test_all_csv_rows_load_without_error(self):
        """Full coverage: every row in both CSVs validates successfully."""
        jumpers = load_rigid_jumpers(RIGID_JUMPER_CSV)
        moorings = load_mooring_components(MOORING_CSV)
        assert len(jumpers) > 0
        assert len(moorings) > 0
