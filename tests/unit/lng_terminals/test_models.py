"""Tests for LNG terminal data models."""

from datetime import date, datetime

import pytest

from worldenergydata.lng_terminals.constants import (
    PipelineType,
    Region,
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from worldenergydata.lng_terminals.models.data_quality import (
    QualityScore,
    SourceCitation,
)
from worldenergydata.lng_terminals.models.design import (
    HullDesign,
    MarineInfrastructure,
    PipelineSpec,
    ProcessEquipment,
    StorageSpec,
)
from worldenergydata.lng_terminals.models.terminal import LNGTerminal


class TestEnums:
    """Test all enumeration types."""

    def test_terminal_type_values(self):
        assert TerminalType.FSRU.value == "fsru"
        assert TerminalType.FLNG.value == "flng"
        assert TerminalType.ONSHORE_IMPORT.value == "onshore_import"
        assert len(TerminalType) == 5

    def test_terminal_function_values(self):
        assert TerminalFunction.IMPORT.value == "import"
        assert TerminalFunction.BIDIRECTIONAL.value == "bidirectional"
        assert len(TerminalFunction) == 3

    def test_terminal_status_values(self):
        assert TerminalStatus.OPERATIONAL.value == "operational"
        assert TerminalStatus.MOTHBALLED.value == "mothballed"
        assert len(TerminalStatus) == 6

    def test_pipeline_type_values(self):
        assert PipelineType.FEED_GAS.value == "feed_gas"
        assert PipelineType.BOIL_OFF_GAS.value == "boil_off_gas"
        assert len(PipelineType) == 7

    def test_region_display_names(self):
        assert Region.ASIA_PACIFIC.value == "Asia Pacific"
        assert Region.MIDDLE_EAST.value == "Middle East"

    def test_source_reliability(self):
        assert SourceReliability.HIGH.value == "high"
        assert len(SourceReliability) == 3


class TestHullDesign:
    """Test HullDesign model."""

    def test_minimal(self):
        hull = HullDesign(hull_type="ship-shaped")
        assert hull.hull_type == "ship-shaped"
        assert hull.loa_m is None

    def test_full(self):
        hull = HullDesign(
            hull_type="barge",
            loa_m=300.0,
            beam_m=50.0,
            depth_m=25.0,
            draft_m=12.0,
            displacement_tonnes=100000,
            mooring_type="internal_turret",
            year_built=2020,
        )
        assert hull.loa_m == 300.0
        assert hull.mooring_type == "internal_turret"

    def test_year_built_bounds(self):
        with pytest.raises(ValueError, match="year_built"):
            HullDesign(hull_type="spar", year_built=1900)


class TestPipelineSpec:
    """Test PipelineSpec model."""

    def test_minimal(self):
        pipe = PipelineSpec(pipeline_type=PipelineType.FEED_GAS)
        assert pipe.pipeline_type == PipelineType.FEED_GAS
        assert pipe.offshore_segment is False

    def test_full(self):
        pipe = PipelineSpec(
            pipeline_type=PipelineType.LNG_TRANSFER,
            diameter_inches=16.0,
            length_km=5.0,
            material="9% nickel steel",
            design_pressure_barg=70.0,
            design_temperature_c=-162.0,
            insulation_type="vacuum",
            offshore_segment=True,
        )
        assert pipe.diameter_inches == 16.0
        assert pipe.offshore_segment is True


class TestProcessEquipment:
    """Test ProcessEquipment model."""

    def test_minimal(self):
        proc = ProcessEquipment()
        assert proc.liquefaction_process is None

    def test_full(self):
        proc = ProcessEquipment(
            liquefaction_process="C3MR",
            number_of_trains=3,
            capacity_per_train_mtpa=5.0,
            compressor_type="centrifugal",
            compressor_driver="gas turbine",
            regasification_type="ORV",
        )
        assert proc.number_of_trains == 3


class TestStorageSpec:
    """Test StorageSpec model with auto-compute validator."""

    def test_auto_compute_total(self):
        storage = StorageSpec(
            tank_type="full_containment",
            number_of_tanks=4,
            capacity_per_tank_m3=160000,
        )
        assert storage.total_capacity_m3 == 640000

    def test_explicit_total_preserved(self):
        storage = StorageSpec(
            tank_type="membrane_mark_iii",
            number_of_tanks=2,
            capacity_per_tank_m3=170000,
            total_capacity_m3=300000,
        )
        assert storage.total_capacity_m3 == 300000

    def test_partial_no_compute(self):
        storage = StorageSpec(tank_type="moss", number_of_tanks=5)
        assert storage.total_capacity_m3 is None


class TestMarineInfrastructure:
    """Test MarineInfrastructure model."""

    def test_minimal(self):
        marine = MarineInfrastructure()
        assert marine.water_depth_m is None

    def test_full(self):
        marine = MarineInfrastructure(
            water_depth_m=15.0,
            jetty_count=2,
            berth_count=3,
            max_vessel_size_m3=266000,
            loading_arms_count=4,
            breakwater=True,
        )
        assert marine.berth_count == 3


class TestSourceCitation:
    """Test SourceCitation model."""

    def test_create(self):
        src = SourceCitation(
            source_name="GIIGNL Annual Report 2024",
            source_url="https://giignl.org",
            access_date=date(2024, 6, 1),
            fields_sourced=["capacity_mtpa", "status"],
            reliability=SourceReliability.HIGH,
        )
        assert src.source_name == "GIIGNL Annual Report 2024"
        assert len(src.fields_sourced) == 2


class TestQualityScore:
    """Test QualityScore computation."""

    def test_compute_all_present(self):
        fields = {
            "name": True,
            "country": True,
            "type": True,
            "status": True,
            "capacity_mtpa": True,
            "operator": True,
            "hull_loa_m": True,
            "pipeline_count": True,
        }
        score = QualityScore.compute(fields, source_count=3)
        assert score.required_fields_score == 100.0
        assert score.total_score == 100.0
        assert score.source_count == 3

    def test_compute_partial(self):
        fields = {
            "name": True,
            "country": True,
            "type": False,
            "status": True,
            "capacity_mtpa": False,
        }
        score = QualityScore.compute(fields)
        assert score.required_fields_score == 75.0
        assert score.total_score < 100.0

    def test_compute_empty_engineering(self):
        fields = {
            "name": True,
            "country": True,
            "type": True,
            "status": True,
        }
        score = QualityScore.compute(fields)
        # No engineering or optional fields => both score 100% (empty bucket)
        assert score.engineering_score == 100.0


class TestLNGTerminal:
    """Test core LNGTerminal model."""

    def _make_terminal(self, **overrides):
        defaults = {
            "terminal_name": "Sabine Pass LNG",
            "country": "USA",
            "terminal_type": TerminalType.ONSHORE_EXPORT,
            "function": TerminalFunction.EXPORT,
            "status": TerminalStatus.OPERATIONAL,
            "last_updated": datetime(2024, 1, 1),
        }
        defaults.update(overrides)
        return LNGTerminal(**defaults)

    def test_auto_generate_id(self):
        t = self._make_terminal()
        assert t.terminal_id == "sabine-pass-lng-usa"

    def test_explicit_id_preserved(self):
        t = self._make_terminal(terminal_id="custom-id")
        assert t.terminal_id == "custom-id"

    def test_country_validation_uppercase(self):
        t = self._make_terminal(country="usa")
        assert t.country == "USA"

    def test_country_validation_invalid(self):
        with pytest.raises(ValueError, match="country"):
            self._make_terminal(country="US")

    def test_country_validation_invalid_chars(self):
        with pytest.raises(ValueError, match="country"):
            self._make_terminal(country="U1A")

    def test_with_hull_design(self):
        t = self._make_terminal(
            terminal_type=TerminalType.FSRU,
            hull_design=HullDesign(hull_type="ship-shaped", loa_m=300),
        )
        assert t.hull_design.loa_m == 300

    def test_with_pipelines(self):
        t = self._make_terminal(
            pipelines=[
                PipelineSpec(pipeline_type=PipelineType.FEED_GAS, diameter_inches=36),
                PipelineSpec(pipeline_type=PipelineType.SEND_OUT, diameter_inches=24),
            ]
        )
        assert len(t.pipelines) == 2

    def test_to_flat_dict(self):
        t = self._make_terminal(
            capacity_mtpa=15.0,
            pipelines=[PipelineSpec(pipeline_type=PipelineType.FEED_GAS)],
            storage=StorageSpec(
                tank_type="full_containment",
                number_of_tanks=4,
                capacity_per_tank_m3=160000,
            ),
        )
        flat = t.to_flat_dict()
        assert flat["terminal_name"] == "Sabine Pass LNG"
        assert flat["capacity_mtpa"] == 15.0
        assert flat["storage_total_capacity_m3"] == 640000
        assert flat["pipeline_1_pipeline_type"] == "feed_gas"
        assert flat["pipeline_2_pipeline_type"] is None  # placeholder

    def test_generate_terminal_id_unicode(self):
        slug = LNGTerminal.generate_terminal_id("Sao Paulo LNG", "BRA")
        assert slug == "sao-paulo-lng-bra"

    def test_generate_terminal_id_special_chars(self):
        slug = LNGTerminal.generate_terminal_id("Hoegh LNG (FSRU)", "NOR")
        assert slug == "hoegh-lng-fsru-nor"
