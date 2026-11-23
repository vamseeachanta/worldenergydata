"""Tests for vessel hull models data models."""

from datetime import datetime
from pathlib import Path

from worldenergydata.vessel_hull_models.data.models import (
    ModelQuality,
    ModelSource,
    VesselHullModel,
    VesselHullModelCreate,
    VesselHullModelUpdate,
    VesselType,
)


class TestVesselTypeEnum:
    def test_all_members(self):
        names = {m.name for m in VesselType}
        assert "CRANE_VESSEL" in names
        assert "PIPELAY_VESSEL" in names
        assert "FPSO" in names
        assert "GENERIC" in names
        assert "FPV" in names

    def test_string_enum(self):
        assert isinstance(VesselType.CRANE_VESSEL, str)


class TestModelSourceEnum:
    def test_all_members(self):
        names = {m.name for m in ModelSource}
        assert "CGTRADER" in names
        assert "PARAMETRIC" in names
        assert "ORCAWAVE" in names
        assert "RHINO" in names
        assert "MANUAL" in names


class TestModelQualityEnum:
    def test_all_members(self):
        names = {m.name for m in ModelQuality}
        assert "ENGINEERING" in names
        assert "PROFESSIONAL" in names
        assert "PLACEHOLDER" in names


class TestVesselHullModel:
    def test_minimal(self):
        model = VesselHullModel(
            vessel_name="Test Vessel",
            length_overall=100.0,
            beam=20.0,
            obj_file_path="/tmp/test.obj",
        )
        assert model.vessel_name == "Test Vessel"
        assert model.length_overall == 100.0
        assert model.beam == 20.0
        assert model.vessel_type == VesselType.GENERIC.value
        assert model.source == ModelSource.MANUAL.value
        assert model.model_quality == ModelQuality.ENGINEERING.value

    def test_full(self):
        model = VesselHullModel(
            vessel_name="Sleipnir",
            imo_number="9781400",
            vessel_type=VesselType.CRANE_VESSEL,
            operator="Heerema",
            length_overall=220.0,
            beam=102.0,
            depth=45.0,
            draft=12.0,
            displacement=275000.0,
            obj_file_path="/models/sleipnir.obj",
            source=ModelSource.GRABCAD,
            vertex_count=50000,
            face_count=100000,
            file_size_bytes=5000000,
        )
        assert model.imo_number == "9781400"
        assert model.vertex_count == 50000

    def test_path_conversion(self):
        model = VesselHullModel(
            vessel_name="V",
            length_overall=100.0,
            beam=20.0,
            obj_file_path=Path("/tmp/hull.obj"),
        )
        assert model.obj_file_path == "/tmp/hull.obj"
        assert isinstance(model.obj_file_path, str)

    def test_defaults(self):
        model = VesselHullModel(
            vessel_name="V",
            length_overall=50.0,
            beam=10.0,
            obj_file_path="test.obj",
        )
        assert model.id is None
        assert model.imo_number is None
        assert model.depth == 0.0
        assert model.draft == 0.0
        assert model.displacement is None
        assert model.units == "meters"
        assert model.notes is None


class TestVesselHullModelCreate:
    def test_minimal(self):
        create = VesselHullModelCreate(
            vessel_name="New Vessel",
            length_overall=150.0,
            beam=30.0,
            obj_file_path="/models/new.obj",
        )
        assert create.vessel_name == "New Vessel"
        assert create.vessel_type == VesselType.GENERIC
        assert create.source == ModelSource.MANUAL
        assert create.model_quality == ModelQuality.ENGINEERING

    def test_with_all_fields(self):
        create = VesselHullModelCreate(
            vessel_name="Full Vessel",
            vessel_type=VesselType.CRANE_VESSEL,
            imo_number="1234567",
            operator="TestOp",
            length_overall=200.0,
            beam=50.0,
            depth=25.0,
            draft=10.0,
            displacement=100000.0,
            obj_file_path="/models/full.obj",
            source=ModelSource.CGTRADER,
            notes="Test note",
        )
        assert create.imo_number == "1234567"
        assert create.notes == "Test note"


class TestVesselHullModelUpdate:
    def test_empty(self):
        update = VesselHullModelUpdate()
        assert update.vessel_name is None
        assert update.vessel_type is None
        assert update.length_overall is None

    def test_partial(self):
        update = VesselHullModelUpdate(
            vessel_name="Updated Name",
            notes="Updated notes",
        )
        assert update.vessel_name == "Updated Name"
        assert update.notes == "Updated notes"
        assert update.beam is None
