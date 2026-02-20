"""Tests for BCER (BC Energy Regulator) data collection module."""

from worldenergydata.canada.bcer.bcer import BCER


class TestBCERInit:
    def test_defaults(self):
        b = BCER()
        assert b.module_name == "bcer"
        assert b.base_url == "https://maps.bcer.gov.bc.ca"
        assert b.api_client is None
        assert b._cache == {}

    def test_custom_base_url(self):
        b = BCER(base_url="https://custom.example.com")
        assert b.base_url == "https://custom.example.com"

    def test_class_constants(self):
        assert BCER.DEFAULT_BASE_URL == "https://maps.bcer.gov.bc.ca"
        assert BCER.DEFAULT_MAX_RECORDS == 1000


class TestBuildArcgisUrl:
    def test_basic(self):
        b = BCER()
        url = b._build_arcgis_url("/arcgis/rest/test/query")
        assert "maps.bcer.gov.bc.ca" in url
        assert "where=1%3D1" in url
        assert "outFields=%2A" in url
        assert "f=json" in url
        assert "returnGeometry=true" in url
        assert "resultOffset=0" in url

    def test_custom_where(self):
        b = BCER()
        url = b._build_arcgis_url("/arcgis/rest/test/query", where="STATUS='ACTIVE'")
        assert "STATUS" in url

    def test_out_fields(self):
        b = BCER()
        url = b._build_arcgis_url(
            "/arcgis/rest/test/query", out_fields="WELL_NAME,STATUS"
        )
        assert "WELL_NAME" in url

    def test_return_geometry_false(self):
        b = BCER()
        url = b._build_arcgis_url(
            "/arcgis/rest/test/query", return_geometry=False
        )
        assert "returnGeometry=false" in url

    def test_result_offset(self):
        b = BCER()
        url = b._build_arcgis_url(
            "/arcgis/rest/test/query", result_offset=500
        )
        assert "resultOffset=500" in url

    def test_result_record_count(self):
        b = BCER()
        url = b._build_arcgis_url(
            "/arcgis/rest/test/query", result_record_count=200
        )
        assert "resultRecordCount=200" in url

    def test_no_result_record_count_when_none(self):
        b = BCER()
        url = b._build_arcgis_url("/arcgis/rest/test/query")
        assert "resultRecordCount" not in url

    def test_custom_base_url(self):
        b = BCER(base_url="https://custom.example.com")
        url = b._build_arcgis_url("/arcgis/rest/test/query")
        assert "custom.example.com" in url


class TestRouter:
    def test_default_data_types(self):
        b = BCER()
        result = b.router({})
        # Default data_types is ["wells"]
        assert isinstance(result, dict)

    def test_wells_only(self):
        b = BCER()
        result = b.router({"data_types": ["wells"]})
        assert isinstance(result, dict)

    def test_multiple_data_types(self):
        b = BCER()
        result = b.router({"data_types": ["wells", "production", "facilities"]})
        assert isinstance(result, dict)

    def test_unknown_data_type(self):
        b = BCER()
        result = b.router({"data_types": ["unknown_type"]})
        # Unknown types return None from _collect_data_type, not added to collected_data
        assert isinstance(result, dict)

    def test_all_known_data_types(self):
        b = BCER()
        result = b.router({
            "data_types": ["wells", "production", "facilities", "pipelines", "pools"]
        })
        assert isinstance(result, dict)


class TestCollectDataType:
    def test_wells(self):
        b = BCER()
        result = b._collect_data_type("wells", {})
        assert isinstance(result, list)

    def test_production(self):
        b = BCER()
        result = b._collect_data_type("production", {})
        assert isinstance(result, list)

    def test_facilities(self):
        b = BCER()
        result = b._collect_data_type("facilities", {})
        assert isinstance(result, list)

    def test_pipelines(self):
        b = BCER()
        result = b._collect_data_type("pipelines", {})
        assert isinstance(result, list)

    def test_pools(self):
        b = BCER()
        result = b._collect_data_type("pools", {})
        assert isinstance(result, list)

    def test_unknown_returns_none(self):
        b = BCER()
        result = b._collect_data_type("unknown", {})
        assert result is None


class TestCollectWells:
    def test_basic(self):
        b = BCER()
        result = b._collect_wells({})
        assert result == []

    def test_with_filters(self):
        b = BCER()
        result = b._collect_wells({"filters": {"where": "STATUS='ACTIVE'"}})
        assert result == []

    def test_with_limit(self):
        b = BCER()
        result = b._collect_wells({"limit": 50})
        assert result == []


class TestGetWellByUwi:
    def test_not_found(self):
        b = BCER()
        result = b.get_well_by_uwi("200/B-001-A/094-A-01/00")
        assert result is None

    def test_cache_hit(self):
        b = BCER()
        expected = {"uwi": "200/B-001-A/094-A-01/00", "name": "Test Well"}
        b._cache["200/B-001-A/094-A-01/00"] = expected
        result = b.get_well_by_uwi("200/B-001-A/094-A-01/00")
        assert result == expected

    def test_cache_miss(self):
        b = BCER()
        b._cache["other_uwi"] = {"name": "Other Well"}
        result = b.get_well_by_uwi("200/B-001-A/094-A-01/00")
        assert result is None


class TestGetWellByWaNum:
    def test_not_found(self):
        b = BCER()
        result = b.get_well_by_wa_num("12345")
        assert result is None


class TestGetProductionByUwi:
    def test_returns_empty_list(self):
        b = BCER()
        result = b.get_production_by_uwi("200/B-001-A/094-A-01/00")
        assert result == []

    def test_with_date_range(self):
        b = BCER()
        result = b.get_production_by_uwi(
            "200/B-001-A/094-A-01/00",
            start_date="2024-01",
            end_date="2024-06",
        )
        assert result == []


class TestSearchWells:
    def test_no_filters(self):
        b = BCER()
        result = b.search_wells()
        assert result == []

    def test_field_name_filter(self):
        b = BCER()
        result = b.search_wells(field_name="Montney")
        assert result == []

    def test_operator_filter(self):
        b = BCER()
        result = b.search_wells(operator="Shell")
        assert result == []

    def test_well_status_filter(self):
        b = BCER()
        result = b.search_wells(well_status="ACTIVE")
        assert result == []

    def test_multiple_filters(self):
        b = BCER()
        result = b.search_wells(
            field_name="Montney",
            operator="Shell",
            well_status="ACTIVE",
        )
        assert result == []


class TestGetWellsInArea:
    def test_valid_bbox(self):
        b = BCER()
        result = b.get_wells_in_area([-122.0, 49.0, -121.0, 50.0])
        assert result == []

    def test_invalid_bbox_too_few(self):
        b = BCER()
        import pytest

        with pytest.raises(ValueError, match="4 values"):
            b.get_wells_in_area([-122.0, 49.0])

    def test_invalid_bbox_too_many(self):
        b = BCER()
        import pytest

        with pytest.raises(ValueError, match="4 values"):
            b.get_wells_in_area([-122.0, 49.0, -121.0, 50.0, 0.0])

    def test_invalid_bbox_empty(self):
        b = BCER()
        import pytest

        with pytest.raises(ValueError, match="4 values"):
            b.get_wells_in_area([])

    def test_with_custom_limit(self):
        b = BCER()
        result = b.get_wells_in_area([-122.0, 49.0, -121.0, 50.0], limit=500)
        assert result == []
