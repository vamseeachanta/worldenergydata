"""Tests for Canada module."""

import pytest

from worldenergydata.canada.canada import Canada


class TestCanadaInit:
    def test_defaults(self):
        c = Canada()
        assert c.module_name == "canada"
        assert c.aer_instance is None
        assert c.bcer_instance is None
        assert c.analysis_instance is None


class TestValidateConfig:
    def test_empty_config_raises(self):
        c = Canada()
        with pytest.raises(ValueError, match="cannot be empty"):
            c._validate_config({})

    def test_none_config_raises(self):
        c = Canada()
        with pytest.raises(ValueError):
            c._validate_config(None)

    def test_valid_minimal(self):
        c = Canada()
        # Should not raise
        c._validate_config({"provinces": ["ab"]})

    def test_invalid_province(self):
        c = Canada()
        with pytest.raises(ValueError, match="Invalid provinces"):
            c._validate_config({"provinces": ["ontario"]})

    def test_valid_provinces(self):
        c = Canada()
        c._validate_config({"provinces": ["ab", "bc"]})

    def test_valid_provinces_full_names(self):
        c = Canada()
        c._validate_config({"provinces": ["alberta", "british_columbia"]})

    def test_invalid_data_type(self):
        c = Canada()
        with pytest.raises(ValueError, match="Invalid data types"):
            c._validate_config({"data_types": ["invalid_type"]})

    def test_valid_data_types(self):
        c = Canada()
        c._validate_config({"data_types": ["wells", "production", "facilities"]})

    def test_valid_api_rate_limit(self):
        c = Canada()
        c._validate_config({"api": {"rate_limit": 5}})

    def test_invalid_api_rate_limit_zero(self):
        c = Canada()
        with pytest.raises(ValueError, match="Invalid rate limit"):
            c._validate_config({"api": {"rate_limit": 0}})

    def test_invalid_api_rate_limit_negative(self):
        c = Canada()
        with pytest.raises(ValueError, match="Invalid rate limit"):
            c._validate_config({"api": {"rate_limit": -1}})

    def test_invalid_api_rate_limit_string(self):
        c = Canada()
        with pytest.raises(ValueError, match="Invalid rate limit"):
            c._validate_config({"api": {"rate_limit": "fast"}})

    def test_valid_cache_ttl(self):
        c = Canada()
        c._validate_config({"api": {"cache_ttl": 300}})

    def test_valid_cache_ttl_zero(self):
        c = Canada()
        c._validate_config({"api": {"cache_ttl": 0}})

    def test_invalid_cache_ttl_negative(self):
        c = Canada()
        with pytest.raises(ValueError, match="Invalid cache TTL"):
            c._validate_config({"api": {"cache_ttl": -10}})

    def test_invalid_cache_ttl_string(self):
        c = Canada()
        with pytest.raises(ValueError, match="Invalid cache TTL"):
            c._validate_config({"api": {"cache_ttl": "long"}})

    def test_module_mismatch_warning(self):
        c = Canada()
        # Should not raise, just log a warning
        c._validate_config({"module": "other_module"})


class TestSummarizeData:
    def test_error_payload_is_not_a_record(self):
        """Issue 1270: an error mapping contains no acquired records, hence 0."""
        assert Canada()._summarize_data(
            {"aer": {"wells": {"error": "collection failed"}}}
        ) == {"aer_wells": 0}

    def test_empty(self):
        c = Canada()
        assert c._summarize_data({}) == {}

    def test_list_data(self):
        c = Canada()
        result = c._summarize_data(
            {
                "aer": {"wells": [1, 2, 3], "production": [4, 5]},
            }
        )
        assert result["aer_wells"] == 3
        assert result["aer_production"] == 2

    def test_dict_data(self):
        c = Canada()
        result = c._summarize_data(
            {
                "aer": {"wells": {"w1": {}, "w2": {}}},
            }
        )
        assert result["aer_wells"] == 2

    def test_scalar_data(self):
        c = Canada()
        result = c._summarize_data(
            {
                "aer": {"status": "complete"},
            }
        )
        assert result["aer_status"] == 1

    def test_multiple_provinces(self):
        c = Canada()
        result = c._summarize_data(
            {
                "aer": {"wells": [1, 2]},
                "bcer": {"wells": [3]},
            }
        )
        assert result["aer_wells"] == 2
        assert result["bcer_wells"] == 1

    def test_non_dict_province(self):
        c = Canada()
        # If province data is not a dict, skip it
        result = c._summarize_data({"aer": "just a string"})
        assert result == {}


@pytest.mark.parametrize("province", ["ab", "bc"])
@pytest.mark.parametrize("mixed", [False, True])
def test_router_reports_collection_errors(monkeypatch, province, mixed):
    """Issue 1270: failed wells contribute 0; one synthetic facility gives 1.

    The counts are hand enumerations of the returned lists, not field data.
    """
    from worldenergydata.canada.aer.aer import AER
    from worldenergydata.canada.bcer.bcer import BCER

    collector = AER if province == "ab" else BCER

    def collect(self, data_type, cfg):
        if data_type == "wells":
            raise RuntimeError("collection failed")
        return [{"id": "synthetic-facility"}]

    monkeypatch.setattr(collector, "_collect_data_type", collect)
    result = Canada().router(
        {
            "provinces": [province],
            "data_types": ["wells", "facilities"] if mixed else ["wells"],
        }
    )["canada"]
    prefix = "aer" if province == "ab" else "bcer"
    assert result["status"] == "error"
    assert result["data_collected"][f"{prefix}_wells"] == 0
    assert result["errors"] == {f"{prefix}_wells": "collection failed"}
    if mixed:
        assert result["data_collected"][f"{prefix}_facilities"] == 1


def test_router_success_remains_completed(monkeypatch):
    """Hand count: the successful synthetic list has one record; no errors."""
    monkeypatch.setattr(
        Canada, "_collect_aer_data", lambda self, cfg: {"wells": [{"id": "well"}]}
    )
    result = Canada().router({"provinces": ["ab"]})["canada"]
    assert result["status"] == "completed"
    assert result["data_collected"] == {"aer_wells": 1}
    assert result["errors"] == {}
