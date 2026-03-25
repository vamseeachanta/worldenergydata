"""Tests for vessel hull models constants."""

from worldenergydata.vessel_hull_models.constants import (
    DECIMATION_HIGH,
    DECIMATION_LOW,
    DECIMATION_MEDIUM,
    DEFAULT_TOLERANCE,
    GOM_OPERATORS,
    MAX_FACE_COUNT,
    MAX_FILE_SIZE_BYTES,
    MAX_VERTEX_COUNT,
    PRIORITY_VESSELS,
    HullFormType,
    ModelQuality,
    ModelSource,
    VesselType,
)


class TestVesselType:
    def test_all_members(self):
        expected = {
            "CRANE_VESSEL", "PIPELAY_VESSEL", "DERRICK_LAY_VESSEL",
            "SINGLE_LIFT_VESSEL", "PSV", "AHTS", "CONSTRUCTION_VESSEL",
            "DIVING_SUPPORT_VESSEL", "FPSO", "SEMI_SUBMERSIBLE",
            "JACK_UP", "GENERIC",
        }
        assert {m.name for m in VesselType} == expected

    def test_string_enum(self):
        assert isinstance(VesselType.CRANE_VESSEL, str)
        assert VesselType.CRANE_VESSEL == "crane_vessel"


class TestModelSource:
    def test_all_members(self):
        expected = {
            "CGTRADER", "SKETCHFAB", "TURBOSQUID",
            "GRABCAD", "PARAMETRIC", "MANUAL",
        }
        assert {m.name for m in ModelSource} == expected


class TestModelQuality:
    def test_all_members(self):
        expected = {"ENGINEERING", "PROFESSIONAL", "ARTISTIC", "SYNTHETIC"}
        assert {m.name for m in ModelQuality} == expected


class TestHullFormType:
    def test_all_members(self):
        expected = {"SERIES_60", "WIGLEY", "NPL", "BARGE", "SEMI_SUB", "PONTOON"}
        assert {m.name for m in HullFormType} == expected

    def test_values(self):
        assert HullFormType.WIGLEY.value == "wigley"
        assert HullFormType.BARGE.value == "barge"


class TestGOMOperators:
    def test_is_list(self):
        assert isinstance(GOM_OPERATORS, list)
        assert len(GOM_OPERATORS) == 7

    def test_known_operators(self):
        assert "Heerema" in GOM_OPERATORS
        assert "Saipem" in GOM_OPERATORS
        assert "Allseas" in GOM_OPERATORS


class TestPriorityVessels:
    def test_known_vessels(self):
        assert "sleipnir" in PRIORITY_VESSELS
        assert "thialf" in PRIORITY_VESSELS
        assert "pioneering_spirit" in PRIORITY_VESSELS

    def test_vessel_has_required_fields(self):
        for name, vessel in PRIORITY_VESSELS.items():
            assert "imo" in vessel
            assert "operator" in vessel
            assert "type" in vessel
            assert "loa" in vessel
            assert "beam" in vessel
            assert "draft" in vessel

    def test_vessel_types(self):
        assert PRIORITY_VESSELS["sleipnir"]["type"] == VesselType.CRANE_VESSEL
        assert PRIORITY_VESSELS["pioneering_spirit"]["type"] == VesselType.SINGLE_LIFT_VESSEL


class TestScalarConstants:
    def test_default_tolerance(self):
        assert DEFAULT_TOLERANCE == 0.05

    def test_max_vertex_count(self):
        assert MAX_VERTEX_COUNT == 10_000_000

    def test_max_face_count(self):
        assert MAX_FACE_COUNT == 10_000_000

    def test_max_file_size(self):
        assert MAX_FILE_SIZE_BYTES == 500 * 1024 * 1024

    def test_decimation_order(self):
        assert DECIMATION_LOW < DECIMATION_MEDIUM < DECIMATION_HIGH
