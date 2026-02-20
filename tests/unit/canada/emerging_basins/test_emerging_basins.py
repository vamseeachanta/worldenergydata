"""
Tests for emerging basin watch list module.

Coverage targets:
- get_emerging_basins() returns 4 stubs
- Each stub has all required fields populated
- get_basin() retrieves by name correctly
- monitor_triggers is a non-empty list for every stub
- estimated_reserves_bboe > 0 for all basins
- Error handling for unknown basin names
- Status values are valid
- first_oil_estimate is a string
"""

import pytest

from worldenergydata.canada.emerging_basins.watch_list import (
    EMERGING_BASINS,
    EmergingBasinStub,
    get_basin,
    get_emerging_basins,
)

EXPECTED_BASIN_NAMES = {
    "Guyana Stabroek",
    "Suriname GranMorgu",
    "Namibia Orange Basin",
    "Falkland Islands Sea Lion",
}

VALID_STATUSES = {"exploration", "appraisal", "development", "production"}


# ---------------------------------------------------------------------------
# Test: get_emerging_basins
# ---------------------------------------------------------------------------


class TestGetEmergingBasins:
    def test_returns_list(self):
        result = get_emerging_basins()
        assert isinstance(result, list)

    def test_returns_exactly_four_stubs(self):
        result = get_emerging_basins()
        assert len(result) == 4

    def test_all_items_are_emerging_basin_stub(self):
        result = get_emerging_basins()
        assert all(isinstance(s, EmergingBasinStub) for s in result)

    def test_contains_guyana_stabroek(self):
        names = {s.basin_name for s in get_emerging_basins()}
        assert "Guyana Stabroek" in names

    def test_contains_suriname_gran_morgu(self):
        names = {s.basin_name for s in get_emerging_basins()}
        assert "Suriname GranMorgu" in names

    def test_contains_namibia_orange_basin(self):
        names = {s.basin_name for s in get_emerging_basins()}
        assert "Namibia Orange Basin" in names

    def test_contains_falkland_islands_sea_lion(self):
        names = {s.basin_name for s in get_emerging_basins()}
        assert "Falkland Islands Sea Lion" in names

    def test_all_expected_basins_present(self):
        names = {s.basin_name for s in get_emerging_basins()}
        assert names == EXPECTED_BASIN_NAMES


# ---------------------------------------------------------------------------
# Test: EmergingBasinStub fields
# ---------------------------------------------------------------------------


class TestEmergingBasinStubFields:
    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_basin_name_non_empty(self, stub):
        assert isinstance(stub.basin_name, str) and len(stub.basin_name) > 0

    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_country_non_empty(self, stub):
        assert isinstance(stub.country, str) and len(stub.country) > 0

    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_operator_non_empty(self, stub):
        assert isinstance(stub.operator, str) and len(stub.operator) > 0

    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_status_is_valid_value(self, stub):
        assert stub.status in VALID_STATUSES

    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_estimated_reserves_bboe_positive(self, stub):
        assert isinstance(stub.estimated_reserves_bboe, float)
        assert stub.estimated_reserves_bboe > 0

    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_first_oil_estimate_is_string(self, stub):
        assert isinstance(stub.first_oil_estimate, str)

    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_monitor_triggers_is_non_empty_list(self, stub):
        assert isinstance(stub.monitor_triggers, list)
        assert len(stub.monitor_triggers) > 0

    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_monitor_triggers_are_strings(self, stub):
        assert all(isinstance(t, str) for t in stub.monitor_triggers)

    @pytest.mark.parametrize("stub", EMERGING_BASINS)
    def test_source_non_empty(self, stub):
        assert isinstance(stub.source, str) and len(stub.source) > 0


# ---------------------------------------------------------------------------
# Test: get_basin
# ---------------------------------------------------------------------------


class TestGetBasin:
    def test_get_basin_guyana_stabroek(self):
        stub = get_basin("Guyana Stabroek")
        assert stub.basin_name == "Guyana Stabroek"

    def test_get_basin_returns_correct_country(self):
        stub = get_basin("Guyana Stabroek")
        assert stub.country == "Guyana"

    def test_get_basin_returns_correct_operator(self):
        stub = get_basin("Guyana Stabroek")
        assert stub.operator == "ExxonMobil"

    def test_get_basin_suriname_gran_morgu(self):
        stub = get_basin("Suriname GranMorgu")
        assert stub.basin_name == "Suriname GranMorgu"

    def test_get_basin_namibia_orange_basin(self):
        stub = get_basin("Namibia Orange Basin")
        assert stub.basin_name == "Namibia Orange Basin"

    def test_get_basin_falkland_sea_lion(self):
        stub = get_basin("Falkland Islands Sea Lion")
        assert stub.basin_name == "Falkland Islands Sea Lion"

    def test_get_basin_unknown_name_raises_key_error(self):
        with pytest.raises(KeyError):
            get_basin("NonExistentBasin")

    def test_get_basin_guyana_has_multiple_monitor_triggers(self):
        stub = get_basin("Guyana Stabroek")
        assert len(stub.monitor_triggers) >= 3

    def test_get_basin_guyana_reserves_gt_ten_bboe(self):
        stub = get_basin("Guyana Stabroek")
        assert stub.estimated_reserves_bboe >= 10.0

    def test_get_basin_namibia_status_appraisal(self):
        stub = get_basin("Namibia Orange Basin")
        assert stub.status == "appraisal"
