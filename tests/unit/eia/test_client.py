"""Tests for EIA API v2 weekly feed client.

All tests use mocked HTTP responses — no live API calls are made.
TDD: these tests were written before the implementation.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from worldenergydata.eia.client import (
    EIA_BASE_URL,
    EIAFeedClient,
    EIAFeedError,
    EIAKeyError,
)
from worldenergydata.eia.ingestion import (
    EIAIngestionState,
    EIAIngestionSync,
    JSONL_SCHEMA_VERSION,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def api_key() -> str:
    return "TEST_EIA_KEY_123"


@pytest.fixture
def client(api_key: str) -> EIAFeedClient:
    return EIAFeedClient(api_key=api_key)


@pytest.fixture
def petroleum_response() -> Dict[str, Any]:
    """Mocked EIA API v2 response for weekly petroleum status."""
    return {
        "response": {
            "total": 3,
            "dateFormat": "YYYY-MM-DD",
            "frequency": "weekly",
            "data": [
                {
                    "period": "2024-01-05",
                    "area-name": "U.S.",
                    "product-name": "Crude Oil",
                    "process-name": "Field Production",
                    "series": "WCRFPUS2",
                    "value": "13150",
                    "units": "Thousand Barrels",
                },
                {
                    "period": "2024-01-12",
                    "area-name": "U.S.",
                    "product-name": "Crude Oil",
                    "process-name": "Field Production",
                    "series": "WCRFPUS2",
                    "value": "13200",
                    "units": "Thousand Barrels",
                },
                {
                    "period": "2024-01-19",
                    "area-name": "U.S.",
                    "product-name": "Crude Oil",
                    "process-name": "Field Production",
                    "series": "WCRFPUS2",
                    "value": "13050",
                    "units": "Thousand Barrels",
                },
            ],
        },
        "request": {
            "command": "/petroleum/sum/snd/w/",
            "params": {"api_key": "REDACTED"},
        },
    }


@pytest.fixture
def gas_storage_response() -> Dict[str, Any]:
    """Mocked EIA API v2 response for weekly natural gas storage."""
    return {
        "response": {
            "total": 2,
            "dateFormat": "YYYY-MM-DD",
            "frequency": "weekly",
            "data": [
                {
                    "period": "2024-01-05",
                    "duoarea": "NUS",
                    "area-name": "U.S.",
                    "product": "3300",
                    "product-name": "Natural Gas",
                    "process": "SAX",
                    "process-name": "Working Gas in Underground Storage",
                    "series": "NW2_EPG0_SAX_NUS_BCF",
                    "value": "3100",
                    "units": "Bcf",
                },
                {
                    "period": "2024-01-12",
                    "duoarea": "NUS",
                    "area-name": "U.S.",
                    "product": "3300",
                    "product-name": "Natural Gas",
                    "process": "SAX",
                    "process-name": "Working Gas in Underground Storage",
                    "series": "NW2_EPG0_SAX_NUS_BCF",
                    "value": "3050",
                    "units": "Bcf",
                },
            ],
        },
        "request": {
            "command": "/natural-gas/stor/sum/dcu/nus/w/",
            "params": {"api_key": "REDACTED"},
        },
    }


@pytest.fixture
def empty_response() -> Dict[str, Any]:
    """Mocked empty response with no data records."""
    return {
        "response": {
            "total": 0,
            "data": [],
        }
    }


# ── EIAFeedClient: Initialisation ──────────────────────────────────────────


class TestEIAFeedClientInit:
    def test_client_accepts_explicit_api_key(self, api_key: str) -> None:
        client = EIAFeedClient(api_key=api_key)
        assert client.api_key == api_key

    def test_client_reads_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EIA_API_KEY", "ENV_KEY_XYZ")
        client = EIAFeedClient()
        assert client.api_key == "ENV_KEY_XYZ"

    def test_client_raises_when_no_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("EIA_API_KEY", raising=False)
        with pytest.raises(EIAKeyError, match="EIA_API_KEY"):
            EIAFeedClient()

    def test_client_uses_default_base_url(self, client: EIAFeedClient) -> None:
        assert client.base_url == EIA_BASE_URL

    def test_client_accepts_custom_base_url(self, api_key: str) -> None:
        custom = "https://custom.eia.gov/v2"
        client = EIAFeedClient(api_key=api_key, base_url=custom)
        assert client.base_url == custom

    def test_eia_base_url_points_to_v2(self) -> None:
        assert "api.eia.gov/v2" in EIA_BASE_URL


# ── EIAFeedClient: URL Building ────────────────────────────────────────────


class TestEIAFeedClientUrlBuilding:
    def test_build_petroleum_url(self, client: EIAFeedClient) -> None:
        url = client.build_endpoint_url("petroleum/sum/snd/w")
        assert "petroleum/sum/snd/w" in url
        assert url.startswith("https://")

    def test_build_gas_storage_url(self, client: EIAFeedClient) -> None:
        url = client.build_endpoint_url("natural-gas/stor/sum/dcu/nus/w")
        assert "natural-gas/stor/sum/dcu/nus/w" in url

    def test_url_does_not_contain_api_key(self, client: EIAFeedClient) -> None:
        url = client.build_endpoint_url("petroleum/sum/snd/w")
        assert client.api_key not in url


# ── EIAFeedClient: Response Parsing ───────────────────────────────────────


class TestEIAFeedClientParsing:
    def test_parse_petroleum_response_returns_list(
        self,
        client: EIAFeedClient,
        petroleum_response: Dict[str, Any],
    ) -> None:
        records = client.parse_response(petroleum_response)
        assert isinstance(records, list)
        assert len(records) == 3

    def test_parse_petroleum_period_is_string(
        self,
        client: EIAFeedClient,
        petroleum_response: Dict[str, Any],
    ) -> None:
        records = client.parse_response(petroleum_response)
        assert all(isinstance(r["period"], str) for r in records)

    def test_parse_petroleum_value_is_float(
        self,
        client: EIAFeedClient,
        petroleum_response: Dict[str, Any],
    ) -> None:
        records = client.parse_response(petroleum_response)
        assert all(isinstance(r["value"], float) for r in records)

    def test_parse_gas_storage_response(
        self,
        client: EIAFeedClient,
        gas_storage_response: Dict[str, Any],
    ) -> None:
        records = client.parse_response(gas_storage_response)
        assert len(records) == 2
        assert records[0]["value"] == 3100.0
        assert records[0]["units"] == "Bcf"

    def test_parse_empty_response_returns_empty_list(
        self,
        client: EIAFeedClient,
        empty_response: Dict[str, Any],
    ) -> None:
        records = client.parse_response(empty_response)
        assert records == []

    def test_parse_null_value_becomes_none(
        self, client: EIAFeedClient
    ) -> None:
        response = {
            "response": {
                "data": [{"period": "2024-01-05", "value": None, "units": "Bcf"}]
            }
        }
        records = client.parse_response(response)
        assert records[0]["value"] is None

    def test_parse_preserves_period_ordering(
        self,
        client: EIAFeedClient,
        petroleum_response: Dict[str, Any],
    ) -> None:
        records = client.parse_response(petroleum_response)
        periods = [r["period"] for r in records]
        assert periods == ["2024-01-05", "2024-01-12", "2024-01-19"]


# ── EIAFeedClient: Fetch with mocked HTTP ─────────────────────────────────


class TestEIAFeedClientFetch:
    def test_fetch_petroleum_weekly_uses_correct_path(
        self,
        client: EIAFeedClient,
        petroleum_response: Dict[str, Any],
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = petroleum_response

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            records = client.fetch_petroleum_weekly()

        assert len(records) == 3

    def test_fetch_gas_storage_weekly_uses_correct_path(
        self,
        client: EIAFeedClient,
        gas_storage_response: Dict[str, Any],
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = gas_storage_response

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            records = client.fetch_gas_storage_weekly()

        assert len(records) == 2

    def test_fetch_raises_on_http_error(self, client: EIAFeedClient) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            with pytest.raises(EIAFeedError, match="403"):
                client.fetch_petroleum_weekly()

    def test_fetch_raises_on_rate_limit(self, client: EIAFeedClient) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            with pytest.raises(EIAFeedError, match="[Rr]ate"):
                client.fetch_petroleum_weekly()

    def test_fetch_passes_api_key_as_query_param(
        self,
        client: EIAFeedClient,
        petroleum_response: Dict[str, Any],
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = petroleum_response

        with patch(
            "worldenergydata.eia.client.requests.get", return_value=mock_resp
        ) as mock_get:
            client.fetch_petroleum_weekly()

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs[0][1]
        assert params.get("api_key") == client.api_key

    def test_fetch_with_start_date_param(
        self,
        client: EIAFeedClient,
        petroleum_response: Dict[str, Any],
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = petroleum_response

        with patch(
            "worldenergydata.eia.client.requests.get", return_value=mock_resp
        ) as mock_get:
            client.fetch_petroleum_weekly(start_date="2024-01-01")

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs[0][1]
        assert "start" in params

    def test_fetch_returns_records_with_schema_source_field(
        self,
        client: EIAFeedClient,
        petroleum_response: Dict[str, Any],
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = petroleum_response

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            records = client.fetch_petroleum_weekly()

        assert all("_feed" in r for r in records)
        assert all(r["_feed"] == "petroleum_weekly" for r in records)


# ── EIAIngestionState ─────────────────────────────────────────────────────


class TestEIAIngestionState:
    def test_state_file_created_on_save(self, tmp_path: Path) -> None:
        state = EIAIngestionState(state_dir=tmp_path)
        state.save_last_fetch("petroleum_weekly", "2024-01-19")
        assert (tmp_path / "eia_ingestion_state.json").exists()

    def test_state_load_returns_saved_date(self, tmp_path: Path) -> None:
        state = EIAIngestionState(state_dir=tmp_path)
        state.save_last_fetch("petroleum_weekly", "2024-01-19")
        loaded = EIAIngestionState(state_dir=tmp_path)
        assert loaded.get_last_fetch("petroleum_weekly") == "2024-01-19"

    def test_state_missing_feed_returns_none(self, tmp_path: Path) -> None:
        state = EIAIngestionState(state_dir=tmp_path)
        assert state.get_last_fetch("nonexistent_feed") is None

    def test_state_updates_existing_date(self, tmp_path: Path) -> None:
        state = EIAIngestionState(state_dir=tmp_path)
        state.save_last_fetch("gas_storage_weekly", "2024-01-05")
        state.save_last_fetch("gas_storage_weekly", "2024-01-19")
        loaded = EIAIngestionState(state_dir=tmp_path)
        assert loaded.get_last_fetch("gas_storage_weekly") == "2024-01-19"

    def test_state_tracks_multiple_feeds(self, tmp_path: Path) -> None:
        state = EIAIngestionState(state_dir=tmp_path)
        state.save_last_fetch("petroleum_weekly", "2024-01-19")
        state.save_last_fetch("gas_storage_weekly", "2024-01-12")
        loaded = EIAIngestionState(state_dir=tmp_path)
        assert loaded.get_last_fetch("petroleum_weekly") == "2024-01-19"
        assert loaded.get_last_fetch("gas_storage_weekly") == "2024-01-12"


# ── EIAIngestionSync: JSONL writing ───────────────────────────────────────


class TestEIAIngestionSyncJsonl:
    def test_write_jsonl_creates_file(
        self,
        tmp_path: Path,
        api_key: str,
    ) -> None:
        sync = EIAIngestionSync(api_key=api_key, output_dir=tmp_path)
        records = [
            {"period": "2024-01-05", "value": 13150.0, "units": "Thousand Barrels",
             "_feed": "petroleum_weekly"},
        ]
        sync.write_jsonl("petroleum_weekly", records)
        jsonl_files = list(tmp_path.glob("*.jsonl"))
        assert len(jsonl_files) == 1

    def test_write_jsonl_one_record_per_line(
        self,
        tmp_path: Path,
        api_key: str,
    ) -> None:
        sync = EIAIngestionSync(api_key=api_key, output_dir=tmp_path)
        records = [
            {"period": "2024-01-05", "value": 13150.0, "_feed": "petroleum_weekly"},
            {"period": "2024-01-12", "value": 13200.0, "_feed": "petroleum_weekly"},
        ]
        sync.write_jsonl("petroleum_weekly", records)
        jsonl_file = list(tmp_path.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_write_jsonl_adds_schema_version(
        self,
        tmp_path: Path,
        api_key: str,
    ) -> None:
        sync = EIAIngestionSync(api_key=api_key, output_dir=tmp_path)
        records = [
            {"period": "2024-01-05", "value": 13150.0, "_feed": "petroleum_weekly"},
        ]
        sync.write_jsonl("petroleum_weekly", records)
        jsonl_file = list(tmp_path.glob("*.jsonl"))[0]
        line = jsonl_file.read_text().strip()
        record = json.loads(line)
        assert "_schema_version" in record
        assert record["_schema_version"] == JSONL_SCHEMA_VERSION

    def test_write_jsonl_each_line_is_valid_json(
        self,
        tmp_path: Path,
        api_key: str,
    ) -> None:
        sync = EIAIngestionSync(api_key=api_key, output_dir=tmp_path)
        records = [
            {"period": "2024-01-05", "value": 13150.0, "_feed": "petroleum_weekly"},
            {"period": "2024-01-12", "value": 13200.0, "_feed": "petroleum_weekly"},
        ]
        sync.write_jsonl("petroleum_weekly", records)
        jsonl_file = list(tmp_path.glob("*.jsonl"))[0]
        for line in jsonl_file.read_text().strip().split("\n"):
            parsed = json.loads(line)
            assert isinstance(parsed, dict)

    def test_write_jsonl_appends_to_existing_file(
        self,
        tmp_path: Path,
        api_key: str,
    ) -> None:
        sync = EIAIngestionSync(api_key=api_key, output_dir=tmp_path)
        batch_1 = [{"period": "2024-01-05", "value": 1.0, "_feed": "petroleum_weekly"}]
        batch_2 = [{"period": "2024-01-12", "value": 2.0, "_feed": "petroleum_weekly"}]
        sync.write_jsonl("petroleum_weekly", batch_1)
        sync.write_jsonl("petroleum_weekly", batch_2)
        jsonl_file = list(tmp_path.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text().strip().split("\n")
        assert len(lines) == 2


# ── EIAIngestionSync: Incremental sync ────────────────────────────────────


class TestEIAIngestionSyncIncremental:
    def test_sync_petroleum_only_fetches_since_last_date(
        self,
        tmp_path: Path,
        api_key: str,
        petroleum_response: Dict[str, Any],
    ) -> None:
        # Pre-seed state so only new records after 2024-01-12 should be stored
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        state = EIAIngestionState(state_dir=state_dir)
        state.save_last_fetch("petroleum_weekly", "2024-01-12")

        sync = EIAIngestionSync(
            api_key=api_key, output_dir=tmp_path, state_dir=state_dir
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = petroleum_response

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            result = sync.run_petroleum_sync()

        assert result["feed"] == "petroleum_weekly"
        assert "records_written" in result

    def test_sync_updates_state_after_successful_run(
        self,
        tmp_path: Path,
        api_key: str,
        petroleum_response: Dict[str, Any],
    ) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        sync = EIAIngestionSync(
            api_key=api_key, output_dir=tmp_path, state_dir=state_dir
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = petroleum_response

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            sync.run_petroleum_sync()

        loaded_state = EIAIngestionState(state_dir=state_dir)
        last_fetch = loaded_state.get_last_fetch("petroleum_weekly")
        assert last_fetch == "2024-01-19"

    def test_sync_gas_storage_writes_jsonl(
        self,
        tmp_path: Path,
        api_key: str,
        gas_storage_response: Dict[str, Any],
    ) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        sync = EIAIngestionSync(
            api_key=api_key, output_dir=tmp_path, state_dir=state_dir
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = gas_storage_response

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            result = sync.run_gas_storage_sync()

        assert result["feed"] == "gas_storage_weekly"
        jsonl_files = list(tmp_path.glob("*.jsonl"))
        assert len(jsonl_files) >= 1

    def test_sync_run_all_executes_both_feeds(
        self,
        tmp_path: Path,
        api_key: str,
        petroleum_response: Dict[str, Any],
        gas_storage_response: Dict[str, Any],
    ) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        sync = EIAIngestionSync(
            api_key=api_key, output_dir=tmp_path, state_dir=state_dir
        )

        def side_effect(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            url = args[0] if args else kwargs.get("url", "")
            if "natural-gas" in url:
                mock_resp.json.return_value = gas_storage_response
            else:
                mock_resp.json.return_value = petroleum_response
            return mock_resp

        with patch("worldenergydata.eia.client.requests.get", side_effect=side_effect):
            results = sync.run_all()

        assert len(results) == 2
        feed_names = {r["feed"] for r in results}
        assert "petroleum_weekly" in feed_names
        assert "gas_storage_weekly" in feed_names

    def test_sync_skips_records_on_or_before_last_fetch(
        self,
        tmp_path: Path,
        api_key: str,
        petroleum_response: Dict[str, Any],
    ) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        state = EIAIngestionState(state_dir=state_dir)
        # Last fetch was 2024-01-12 — only 2024-01-19 should be written
        state.save_last_fetch("petroleum_weekly", "2024-01-12")

        sync = EIAIngestionSync(
            api_key=api_key, output_dir=tmp_path, state_dir=state_dir
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = petroleum_response

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            result = sync.run_petroleum_sync()

        assert result["records_written"] == 1

    def test_sync_result_includes_records_written_count(
        self,
        tmp_path: Path,
        api_key: str,
        petroleum_response: Dict[str, Any],
    ) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir()

        sync = EIAIngestionSync(
            api_key=api_key, output_dir=tmp_path, state_dir=state_dir
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = petroleum_response

        with patch("worldenergydata.eia.client.requests.get", return_value=mock_resp):
            result = sync.run_petroleum_sync()

        assert result["records_written"] == 3


# ── JSONL_SCHEMA_VERSION constant ─────────────────────────────────────────


class TestSchemaVersion:
    def test_schema_version_is_string(self) -> None:
        assert isinstance(JSONL_SCHEMA_VERSION, str)

    def test_schema_version_not_empty(self) -> None:
        assert len(JSONL_SCHEMA_VERSION) > 0
