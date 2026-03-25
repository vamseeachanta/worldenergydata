"""Tests for data normalizer."""

from worldenergydata.marine_safety.processors.data_normalizer import DataNormalizer


class TestNormalizeIncidentType:
    def test_collision(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("collision") == "collision"

    def test_vessel_collision(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("vessel collision") == "collision"

    def test_allision(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("allision") == "collision"

    def test_grounding(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("grounding") == "grounding"

    def test_run_aground(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("run aground") == "grounding"

    def test_fire(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("fire") == "fire"

    def test_fire_explosion(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("fire/explosion") == "fire"

    def test_sinking_maps_to_flooding(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("sinking") == "flooding"

    def test_capsizing(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("capsizing") == "capsizing"

    def test_equipment_failure(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("material failure") == "equipment_failure"

    def test_personnel_casualty(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("personnel casualty") == "personnel_injury"

    def test_oil_spill(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("oil spill") == "pollution"

    def test_case_insensitive(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("COLLISION") == "collision"

    def test_whitespace_stripped(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("  grounding  ") == "grounding"

    def test_none_returns_none(self):
        n = DataNormalizer()
        assert n.normalize_incident_type(None) is None

    def test_empty_returns_none(self):
        n = DataNormalizer()
        assert n.normalize_incident_type("") is None

    def test_unknown_returns_snake_case(self):
        n = DataNormalizer()
        result = n.normalize_incident_type("mystery event")
        assert isinstance(result, str)

    def test_partial_match(self):
        n = DataNormalizer()
        # "fire" is in "fire/explosion" patterns, partial match
        result = n.normalize_incident_type("a large fire broke out")
        assert result == "fire"


class TestNormalizeVesselType:
    def test_cargo(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("cargo") == "cargo_vessel"

    def test_cargo_ship(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("cargo ship") == "cargo_vessel"

    def test_container_ship(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("container ship") == "cargo_vessel"

    def test_tanker(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("tanker") == "tanker"

    def test_oil_tanker(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("oil tanker") == "tanker"

    def test_tug(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("tug") == "tug"

    def test_supply_vessel(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("supply vessel") == "supply_vessel"

    def test_platform(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("platform") == "production_platform"

    def test_none_returns_none(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type(None) is None

    def test_empty_returns_none(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("") is None

    def test_case_insensitive(self):
        n = DataNormalizer()
        assert n.normalize_vessel_type("TANKER") == "tanker"


class TestNormalizeCountry:
    def test_usa(self):
        n = DataNormalizer()
        assert n.normalize_country("united states") == "USA"

    def test_usa_abbreviation(self):
        n = DataNormalizer()
        assert n.normalize_country("us") == "USA"

    def test_uk(self):
        n = DataNormalizer()
        assert n.normalize_country("united kingdom") == "GBR"

    def test_three_letter_code_passthrough(self):
        n = DataNormalizer()
        assert n.normalize_country("USA") == "USA"

    def test_panama(self):
        n = DataNormalizer()
        assert n.normalize_country("panama") == "PAN"

    def test_none_returns_none(self):
        n = DataNormalizer()
        assert n.normalize_country(None) is None

    def test_empty_returns_none(self):
        n = DataNormalizer()
        assert n.normalize_country("") is None


class TestNormalizeSeverity:
    def test_integer_within_range(self):
        n = DataNormalizer()
        assert n.normalize_severity(3) == 3

    def test_integer_clamped_high(self):
        n = DataNormalizer()
        assert n.normalize_severity(10) == 5

    def test_integer_clamped_low(self):
        n = DataNormalizer()
        assert n.normalize_severity(0) == 1

    def test_string_minor(self):
        n = DataNormalizer()
        assert n.normalize_severity("minor") == 1

    def test_string_moderate(self):
        n = DataNormalizer()
        assert n.normalize_severity("moderate") == 2

    def test_string_major(self):
        n = DataNormalizer()
        assert n.normalize_severity("major") == 3

    def test_string_severe(self):
        n = DataNormalizer()
        assert n.normalize_severity("severe") == 4

    def test_string_catastrophic(self):
        n = DataNormalizer()
        assert n.normalize_severity("catastrophic") == 5

    def test_string_case_insensitive(self):
        n = DataNormalizer()
        assert n.normalize_severity("CRITICAL") == 5

    def test_fatalities_high(self):
        n = DataNormalizer()
        assert n.normalize_severity(None, fatalities=10) == 5

    def test_fatalities_medium(self):
        n = DataNormalizer()
        assert n.normalize_severity(None, fatalities=5) == 4

    def test_fatalities_low(self):
        n = DataNormalizer()
        assert n.normalize_severity(None, fatalities=1) == 3

    def test_injuries_high(self):
        n = DataNormalizer()
        assert n.normalize_severity(None, injuries=20) == 4

    def test_injuries_medium(self):
        n = DataNormalizer()
        assert n.normalize_severity(None, injuries=10) == 3

    def test_injuries_low(self):
        n = DataNormalizer()
        assert n.normalize_severity(None, injuries=1) == 2

    def test_default_moderate(self):
        n = DataNormalizer()
        assert n.normalize_severity(None) == 2


class TestNormalizeStatus:
    def test_none_returns_draft(self):
        n = DataNormalizer()
        assert n.normalize_status(None) == "draft"

    def test_empty_returns_draft(self):
        n = DataNormalizer()
        assert n.normalize_status("") == "draft"

    def test_draft(self):
        n = DataNormalizer()
        assert n.normalize_status("draft") == "draft"

    def test_preliminary(self):
        n = DataNormalizer()
        assert n.normalize_status("preliminary") == "draft"

    def test_reported(self):
        n = DataNormalizer()
        assert n.normalize_status("reported") == "reported"

    def test_under_investigation(self):
        n = DataNormalizer()
        assert n.normalize_status("under investigation") == "under_investigation"

    def test_investigating(self):
        n = DataNormalizer()
        assert n.normalize_status("investigating") == "under_investigation"

    def test_in_review(self):
        n = DataNormalizer()
        assert n.normalize_status("in review") == "in_review"

    def test_completed(self):
        n = DataNormalizer()
        assert n.normalize_status("completed") == "completed"

    def test_closed(self):
        n = DataNormalizer()
        assert n.normalize_status("closed") == "completed"

    def test_unknown_returns_draft(self):
        n = DataNormalizer()
        assert n.normalize_status("xyz_unknown") == "draft"


class TestProcess:
    def test_normalize_full_record(self):
        n = DataNormalizer()
        data = {
            "incident_type": "collision",
            "vessel_type": "tanker",
            "country": "united states",
            "severity_level": "major",
            "status": "completed",
        }
        result = n.process(data)
        assert result["incident_type"] == "collision"
        assert result["vessel_type"] == "tanker"
        assert result["country"] == "USA"
        assert result["severity_level"] == 3
        assert result["status"] == "completed"

    def test_normalize_none_data(self):
        n = DataNormalizer()
        result = n.process(None)
        assert result is None
        assert n.stats["errors"] == 1

    def test_normalize_empty_record(self):
        n = DataNormalizer()
        result = n.process({})
        assert result == {}

    def test_stats_updated(self):
        n = DataNormalizer()
        n.process({"incident_type": "fire"})
        assert n.stats["processed"] == 1


class TestBatchProcess:
    def test_batch_multiple(self):
        n = DataNormalizer()
        data_list = [
            {"incident_type": "fire"},
            {"incident_type": "grounding"},
            {"vessel_type": "tanker"},
        ]
        results = n.batch_process(data_list)
        assert len(results) == 3
        assert results[0]["incident_type"] == "fire"
        assert results[1]["incident_type"] == "grounding"
        assert results[2]["vessel_type"] == "tanker"

    def test_batch_empty(self):
        n = DataNormalizer()
        results = n.batch_process([])
        assert results == []

    def test_batch_resets_stats(self):
        n = DataNormalizer()
        n.stats["processed"] = 99
        n.batch_process([{"incident_type": "fire"}])
        assert n.stats["processed"] == 1


class TestCustomMappings:
    def test_custom_incident_mapping(self):
        n = DataNormalizer(config={"incident_type_mappings": {"space event": "space"}})
        assert n.normalize_incident_type("space event") == "space"

    def test_custom_vessel_mapping(self):
        n = DataNormalizer(config={"vessel_type_mappings": {"submarine": "sub"}})
        assert n.normalize_vessel_type("submarine") == "sub"

    def test_custom_country_mapping(self):
        n = DataNormalizer(config={"country_mappings": {"atlantis": "ATL"}})
        assert n.normalize_country("atlantis") == "ATL"
