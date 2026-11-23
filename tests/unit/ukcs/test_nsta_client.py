"""Tests for NSTA CSV downloader client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.ukcs.production.nsta_client import NSTAClient

MOCK_PRODUCTION_CSV = (
    "FieldName,Year,Month,OilProduction (Thousand Tonnes),"
    "GasProduction (MMscf),WaterProduction (Thousand Tonnes)\n"
    "FORTIES,2022,1,450.3,12.5,310.2\n"
    "BUZZARD,2022,1,780.1,8.9,210.5\n"
    "FORTIES,2022,2,430.0,11.0,295.7\n"
)

MOCK_PPRS_JSON = {
    "features": [
        {
            "attributes": {
                "FIELDNAME": "ABIGAIL",
                "PERIODYR": "2022",
                "PERIODMNTH": "10",
                "OILPRODMAS": 6948.1176,
                "AGASPROKSM": 2787.0,
                "DGASPROKSM": 0.0,
                "WATPRODVOL": 1393.0,
            }
        },
        {
            "attributes": {
                "FIELDNAME": "ABIGAIL",
                "PERIODYR": "2022",
                "PERIODMNTH": "11",
                "OILPRODMAS": 16983.0378,
                "AGASPROKSM": 6390.0,
                "DGASPROKSM": 0.0,
                "WATPRODVOL": 2599.0,
            }
        },
    ],
    "exceededTransferLimit": False,
}


class TestNSTAClientInit:
    def test_default_cache_dir_created(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        assert client.cache_dir == Path(tmp_path)

    def test_creates_cache_dir_if_missing(self, tmp_path):
        cache = tmp_path / "nsta_cache"
        NSTAClient(cache_dir=str(cache))
        assert cache.exists()

    def test_default_base_url_contains_ukcs_service(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        assert "UKCS_hydrocarbon_field_production_reports" in client.base_url


class TestNSTAClientCacheKey:
    def test_cache_key_includes_year(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        key = client._cache_key(year=2022)
        assert "2022" in key

    def test_cache_key_includes_dataset_type(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        key = client._cache_key(year=2022, dataset="monthly")
        assert "monthly" in key.lower() or "2022" in key

    def test_cache_key_differs_by_year(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        assert client._cache_key(year=2021) != client._cache_key(year=2022)

    def test_cache_key_differs_by_dataset(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        k1 = client._cache_key(year=2022, dataset="monthly")
        k2 = client._cache_key(year=2022, dataset="annual")
        assert k1 != k2


class TestNSTAClientUrl:
    def test_build_url_uses_official_arcgis_query_endpoint(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        url = client._build_url(year=2026, dataset="monthly")
        assert (
            url == "https://services-eu1.arcgis.com/OZMfUznmLTnWccBc/arcgis/rest/"
            "services/UKCS_hydrocarbon_field_production_reports_PPRS_points_(WGS84)/"
            "FeatureServer/0/query"
        )


class TestNSTAClientCache:
    def test_is_cached_false_when_missing(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        assert client.is_cached(year=2022) is False

    def test_is_cached_true_when_file_exists(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text(MOCK_PRODUCTION_CSV)
        assert client.is_cached(year=2022) is True

    def test_load_cached_returns_dataframe(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text(MOCK_PRODUCTION_CSV)
        df = client.load_cached(year=2022)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_load_cached_field_column_present(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text(MOCK_PRODUCTION_CSV)
        df = client.load_cached(year=2022)
        assert any("field" in col.lower() or "Field" in col for col in df.columns)


class TestNSTAClientDownload:
    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_download_queries_official_arcgis_endpoint(self, mock_requests, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_PPRS_JSON
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download(year=2022, max_records=2, force_refresh=True)

        assert df.to_dict("records") == [
            feature["attributes"] for feature in MOCK_PPRS_JSON["features"]
        ]
        mock_requests.get.assert_called_once_with(
            client._build_url(2022, "monthly"),
            params={
                "where": "PERIODYR = '2022'",
                "outFields": "*",
                "returnGeometry": "false",
                "resultOffset": 0,
                "resultRecordCount": 2,
                "f": "json",
            },
            timeout=60,
        )

    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_download_paginates_official_arcgis_endpoint(self, mock_requests, tmp_path):
        """Hand calculation: offset 0 + one returned row = next offset 1.

        Source: ArcGIS REST API, Query (Feature Service/Layer), resultOffset
        and resultRecordCount (online reference, accessed 2026-10-19):
        https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/
        The requested count is an upper bound, not the number consumed.
        """
        client = NSTAClient(cache_dir=str(tmp_path))
        first_response = MagicMock()
        first_response.json.return_value = {
            "features": [MOCK_PPRS_JSON["features"][0]],
            "exceededTransferLimit": True,
        }
        first_response.raise_for_status = MagicMock()
        second_response = MagicMock()
        second_response.json.return_value = {
            "features": [MOCK_PPRS_JSON["features"][1]],
            "exceededTransferLimit": False,
        }
        second_response.raise_for_status = MagicMock()
        mock_requests.get.side_effect = [first_response, second_response]

        df = client.download(year=2022, force_refresh=True)

        assert len(df) == 2
        assert mock_requests.get.call_args_list[0].kwargs["params"]["resultOffset"] == 0
        assert (
            mock_requests.get.call_args_list[0].kwargs["params"]["resultRecordCount"]
            == 2000
        )
        assert mock_requests.get.call_args_list[1].kwargs["params"]["resultOffset"] == 1
        assert (
            mock_requests.get.call_args_list[1].kwargs["params"]["resultRecordCount"]
            == 2000
        )

    @pytest.mark.parametrize(
        "server_limit,max_records,expected_ids,expected_offsets,expected_counts",
        [
            (2, None, [1, 2, 3, 4, 5], [0, 2, 4], [2000, 2000, 2000]),
            (1, None, [1, 2, 3, 4, 5], [0, 1, 2, 3, 4], [2000] * 5),
            (2, 3, [1, 2, 3], [0, 2], [3, 1]),
            (2, 4, [1, 2, 3, 4], [0, 2], [4, 2]),
            (2, 5, [1, 2, 3, 4, 5], [0, 2, 4], [5, 3, 1]),
        ],
    )
    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_short_pages_preserve_rows_and_record_cap(
        self,
        mock_requests,
        tmp_path,
        server_limit,
        max_records,
        expected_ids,
        expected_offsets,
        expected_counts,
    ):
        """Independent hand calculation for a synthetic five-row service.

        Source: ArcGIS REST API, Query (Feature Service/Layer), resultOffset
        and resultRecordCount (online reference, accessed 2026-10-19):
        https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/
        Offsets count consumed rows; requested counts are upper bounds.
        The fixture's IDs 1..5, year 2022, and service limits 1 or 2 are
        arbitrary test inputs, not production measurements or API limits.

        With pages of two rows: 0 + 2 = 2, then 2 + 2 = 4; the final
        page contains ID 5. With pages of one row: offsets 0, 1, 2, 3, 4.
        Caps 3, 4 and 5 leave 3 - 2 = 1, 4 - 2 = 2 and 5 - 2 = 3
        rows after the first page; cap 5 then leaves 5 - 4 = 1 row.
        Uncapped requests retain the existing implementation default of
        2000 rows (source above, Example six: default maxRecordCount).
        This is a regression expectation, not a service limit guarantee.
        """
        client = NSTAClient(cache_dir=str(tmp_path))
        features = [{"attributes": {"OBJECTID": row_id}} for row_id in [1, 2, 3, 4, 5]]

        def query_page(url, *, params, timeout):
            offset = params["resultOffset"]
            count = min(server_limit, params["resultRecordCount"])
            response = MagicMock()
            response.json.return_value = {
                "features": features[offset : offset + count],
                "exceededTransferLimit": offset + count < len(features),
            }
            return response

        mock_requests.get.side_effect = query_page

        df = client.download(year=2022, max_records=max_records, force_refresh=True)

        assert df["OBJECTID"].tolist() == expected_ids
        assert [
            call.kwargs["params"]["resultOffset"]
            for call in mock_requests.get.call_args_list
        ] == expected_offsets
        assert [
            call.kwargs["params"]["resultRecordCount"]
            for call in mock_requests.get.call_args_list
        ] == expected_counts
        pd.testing.assert_frame_equal(df, client.load_cached(year=2022))

    @pytest.mark.parametrize(
        "invalid_feature,server_limit,max_records,expected_offsets,expected_counts",
        [
            ({"attributes": None}, 4, 4, [0, 4], [4, 1]),
            (None, 4, 4, [0, 4], [4, 1]),
            ({"attributes": None}, 4, None, [0, 4], [2000, 2000]),
            ({"attributes": None}, 2, 4, [0, 2, 4], [4, 3, 1]),
        ],
    )
    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_mixed_validity_pages_advance_by_raw_feature_count(
        self,
        mock_requests,
        tmp_path,
        invalid_feature,
        server_limit,
        max_records,
        expected_offsets,
        expected_counts,
    ):
        """Hand calculation for five synthetic entries, with entry 2 invalid.

        A four-entry page consumes positions 0..3 but retains IDs 1, 3, 4.
        The next offset is 4 and a four-row cap leaves 4 - 3 = 1 row.
        Two-entry pages consume offsets 0, 2, 4 and retain 1, 2, 1 rows;
        remaining counts are 4, 3, 1. Uncapped requests keep count 2000.
        Every case returns and caches exactly IDs 1, 3, 4, 5.
        """
        client = NSTAClient(cache_dir=str(tmp_path))
        features = [
            {"attributes": {"OBJECTID": 1}},
            invalid_feature,
            *[{"attributes": {"OBJECTID": row_id}} for row_id in [3, 4, 5]],
        ]

        def query_page(url, *, params, timeout):
            offset = params["resultOffset"]
            count = min(server_limit, params["resultRecordCount"])
            response = MagicMock()
            response.json.return_value = {
                "features": features[offset : offset + count],
                "exceededTransferLimit": offset + count < len(features),
            }
            return response

        mock_requests.get.side_effect = query_page

        df = client.download(year=2022, max_records=max_records, force_refresh=True)

        assert df["OBJECTID"].tolist() == [1, 3, 4, 5]
        assert [
            call.kwargs["params"]["resultOffset"]
            for call in mock_requests.get.call_args_list
        ] == expected_offsets
        assert [
            call.kwargs["params"]["resultRecordCount"]
            for call in mock_requests.get.call_args_list
        ] == expected_counts
        pd.testing.assert_frame_equal(df, client.load_cached(year=2022))

    @pytest.mark.parametrize("exceeded_transfer_limit", [False, True])
    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_empty_page_stops_pagination(
        self, mock_requests, tmp_path, exceeded_transfer_limit
    ):
        """Hand calculation: zero returned rows cannot advance an offset.

        An empty synthetic response must stop after one request regardless
        of the transfer-limit flag, preserving the existing loop guard.
        Year 2022 is an arbitrary request input.
        """
        client = NSTAClient(cache_dir=str(tmp_path))
        mock_requests.get.return_value.json.return_value = {
            "features": [],
            "exceededTransferLimit": exceeded_transfer_limit,
        }

        df = client.download(year=2022, force_refresh=True)

        assert df.empty
        mock_requests.get.assert_called_once()

    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_download_saves_to_cache(self, mock_requests, tmp_path):
        client = NSTAClient(
            cache_dir=str(tmp_path),
            base_url="https://example.test/nsta_{year}_{dataset}.csv",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = MOCK_PRODUCTION_CSV.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download(year=2022)
        assert isinstance(df, pd.DataFrame)
        assert client.is_cached(year=2022)

    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_download_uses_cache_when_available(self, mock_requests, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text(MOCK_PRODUCTION_CSV)

        df = client.download(year=2022)
        mock_requests.get.assert_not_called()
        assert len(df) == 3

    @patch("worldenergydata.ukcs.production.nsta_client.requests")
    def test_download_force_refresh_ignores_cache(self, mock_requests, tmp_path):
        client = NSTAClient(
            cache_dir=str(tmp_path),
            base_url="https://example.test/nsta_{year}_{dataset}.csv",
        )
        cache_path = tmp_path / client._cache_key(year=2022)
        cache_path.write_text("old,data\n1,2\n")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = MOCK_PRODUCTION_CSV.encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        df = client.download(year=2022, force_refresh=True)
        mock_requests.get.assert_called_once()
        assert "FieldName" in df.columns or "field" in df.columns[0].lower()

    def test_download_without_requests_raises(self, tmp_path):
        client = NSTAClient(cache_dir=str(tmp_path))
        with patch("worldenergydata.ukcs.production.nsta_client.requests", None):
            with pytest.raises(RuntimeError, match="requests"):
                client.download(year=2022, force_refresh=True)
