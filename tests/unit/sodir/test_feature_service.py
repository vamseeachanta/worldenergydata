"""Offline contracts for the bounded FeatureServer reader; all rows synthetic."""

import json
from pathlib import Path
from typing import TypedDict

import pytest
import requests
from typing_extensions import Unpack

from worldenergydata.sodir.api_client import SodirAPIClient
from worldenergydata.sodir.feature_service import (
    DEFAULT_FIELDS,
    emit_manifest,
    parse_metadata,
    processor_record,
    validate_record,
)


class BufferedResponse(requests.Response):
    """Typed response buffer for offline transport fixtures."""

    _content_consumed: bool


class RequestArguments(TypedDict):
    params: dict[str, str | int]
    headers: dict[str, str]
    timeout: float
    stream: bool
    allow_redirects: bool


class QueryOptions(TypedDict, total=False):
    page_size: int
    max_pages: int
    max_bytes: int
    select: list[str]


TransportCalls = list[tuple[str, RequestArguments]]


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("network forbidden in offline tests")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(
        "worldenergydata.sodir.feature_service.time.sleep", lambda _: None
    )


@pytest.fixture
def client() -> SodirAPIClient:
    return SodirAPIClient("https://factmaps.sodir.no/api/rest", max_retries=0)


def response(data: object, status: int = 200) -> requests.Response:
    result = BufferedResponse()
    result.status_code = status
    result._content = json.dumps(data).encode()
    result._content_consumed = True
    return result


def transport(
    monkeypatch: pytest.MonkeyPatch,
    client: SodirAPIClient,
    pages: list[dict[str, object]],
) -> TransportCalls:
    calls: TransportCalls = []

    def get(url: str, **kwargs: Unpack[RequestArguments]) -> requests.Response:
        calls.append((url, kwargs))
        return response(pages[len(calls) - 1])

    assert client.session is not None
    monkeypatch.setattr(client.session, "get", get)
    return calls


def test_metadata_and_invalid_metadata() -> None:
    assert parse_metadata(
        {"fields": [{"name": "x", "type": "esriFieldTypeString"}]}
    ) == {"x": "esriFieldTypeString"}
    with pytest.raises(ValueError):
        parse_metadata({"fields": []})


@pytest.mark.parametrize("entity", ["fields", "wellbores", "production"])
def test_entity_schema_and_query(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient, entity: str
) -> None:
    rows = json.loads((FIXTURES / "feature_rows.synthetic.json").read_text())
    calls = transport(
        monkeypatch, client, [{"features": [{"attributes": rows[entity]}]}]
    )
    assert client.query_entity(entity) == [rows[entity]]
    validate_record(entity, rows[entity])
    query = calls[0][1]
    assert query["timeout"] == 30
    assert query["stream"] is True
    assert query["allow_redirects"] is False
    assert query["params"]["resultRecordCount"] == 2
    assert query["params"]["returnGeometry"] == "false"
    assert (
        "https://github.com/vamseeachanta/worldenergydata"
        in query["headers"]["User-Agent"]
    )


def test_paging_and_select(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient
) -> None:
    row = {"OBJECTID": 1, "fldName": "SYNTHETIC"}
    calls = transport(
        monkeypatch,
        client,
        [
            {"features": [{"attributes": row}], "exceededTransferLimit": True},
            {"features": [{"attributes": dict(row, OBJECTID=2)}]},
        ],
    )
    result = client.query_entity("fields", select=["OBJECTID", "fldName"], max_pages=2)
    assert len(result) == 2
    assert calls[1][1]["params"]["resultOffset"] == 1
    assert calls[0][1]["params"]["outFields"] == "OBJECTID,fldName"


@pytest.mark.parametrize(
    "kwargs",
    [{"page_size": 0}, {"max_pages": 0}, {"max_bytes": 0}, {"select": ["invented"]}],
)
def test_invalid_query_before_network(
    client: SodirAPIClient, kwargs: QueryOptions
) -> None:
    with pytest.raises(ValueError):
        client.query_entity("fields", **kwargs)


def test_page_cap(monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient) -> None:
    transport(
        monkeypatch,
        client,
        [
            {
                "features": [{"attributes": {"OBJECTID": 1}}],
                "exceededTransferLimit": True,
            }
        ],
    )
    with pytest.raises(ValueError, match="page cap"):
        client.query_entity("fields")


def test_byte_cap(monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient) -> None:
    transport(monkeypatch, client, [{"features": []}])
    with pytest.raises(ValueError, match="byte cap"):
        client.query_entity("fields", max_bytes=1)


def test_arcgis_error(monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient) -> None:
    transport(monkeypatch, client, [{"error": {"code": 400}}])
    with pytest.raises(ValueError, match="service error"):
        client.query_entity("fields")


@pytest.mark.parametrize("status", [302, 403, 429, 500])
def test_http_error_no_retry(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient, status: int
) -> None:
    assert client.session is not None
    monkeypatch.setattr(client.session, "get", lambda *a, **k: response({}, status))
    with pytest.raises(ValueError, match="HTTP"):
        client.query_entity("fields")


@pytest.mark.parametrize(
    "entity,key",
    [
        ("fields", "fldNpdidField"),
        ("wellbores", "wlbNpdidWellbore"),
        ("production", "prfYear"),
    ],
)
def test_schema_rejects_wrong_types(entity: str, key: str) -> None:
    with pytest.raises(ValueError):
        validate_record(entity, {key: "not an integer"})


def test_processor_mapping() -> None:
    assert (
        processor_record("fields", {"fldCurrentActivitySatus": "PRODUCING"})[
            "fldStatus"
        ]
        == "PRODUCING"
    )
    assert (
        processor_record("wellbores", {"wlbWellboreName": "SYNTHETIC"})["wlbName"]
        == "SYNTHETIC"
    )
    row = {
        "prfInformationCarrier": "SYNTHETIC",
        "prfInformationCarrierKind": "FIELD",
        "prfMonth": 1,
        "prfYear": 2000,
        "prfPrdProducedWaterInFieldMillS": 1.0,
    }
    mapped = processor_record("production", row)
    assert mapped["field_name"] == "SYNTHETIC"
    assert mapped["water_produced_sm3"] == 1e6
    assert "water_injected_sm3" not in mapped
    assert mapped["oil_sm3"] is None


def test_curated_manifest_deterministic_serialization() -> None:
    """Hand-assembled observations are serialized, not produced by the client."""
    inputs = json.loads((FIXTURES / "service_observations.json").read_text())
    assert emit_manifest(inputs) == (FIXTURES / "service_manifest.json").read_bytes()


def test_production_adapter_rejects_annual_and_discovery() -> None:
    for row in [
        {"prfMonth": 0, "prfInformationCarrierKind": "FIELD"},
        {"prfMonth": 1, "prfInformationCarrierKind": "DISCOVERY"},
    ]:
        with pytest.raises(ValueError, match="monthly field"):
            processor_record("production", row)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"features": None},
        {"features": [{"attributes": None}]},
        {"features": [], "exceededTransferLimit": True},
        {"features": [], "exceededTransferLimit": "true"},
    ],
)
def test_malformed_payload(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient, payload: dict[str, object]
) -> None:
    transport(monkeypatch, client, [payload])
    with pytest.raises(ValueError):
        client.query_entity("fields")


def test_invalid_json_is_not_retried(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient
) -> None:
    value = response({})
    value._content = b"<html>invalid JSON</html>"
    assert client.session is not None
    monkeypatch.setattr(client.session, "get", lambda *a, **k: value)
    with pytest.raises(ValueError):
        client.query_entity("fields")


def test_total_byte_cap_across_pages(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient
) -> None:
    page = {
        "features": [{"attributes": {"OBJECTID": 1}}],
        "exceededTransferLimit": True,
    }
    transport(monkeypatch, client, [page, {"features": []}])
    with pytest.raises(ValueError, match="byte cap"):
        client.query_entity(
            "fields", max_pages=2, max_bytes=len(json.dumps(page).encode()) + 1
        )


def test_nonascending_page_rejected(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient
) -> None:
    transport(
        monkeypatch,
        client,
        [
            {
                "features": [
                    {"attributes": {"OBJECTID": 1}},
                    {"attributes": {"OBJECTID": 1}},
                ]
            }
        ],
    )
    with pytest.raises(ValueError, match="object ID"):
        client.query_entity("fields")


def test_pause_between_requests(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient
) -> None:
    pauses: list[float] = []
    monkeypatch.setattr(
        "worldenergydata.sodir.feature_service.time.monotonic", lambda: 100
    )
    monkeypatch.setattr(
        "worldenergydata.sodir.feature_service.time.sleep", pauses.append
    )
    transport(monkeypatch, client, [{"features": []}, {"features": []}])
    client.query_entity("fields")
    client.query_entity("fields")
    assert pauses == [2]


def test_unsafe_base_url_rejected(client: SodirAPIClient) -> None:
    client.base_url = "http://example.invalid"
    with pytest.raises(ValueError, match="service base"):
        client.query_entity("fields")


def test_schema_null_and_date() -> None:
    validate_record("fields", {"fldDateUpdated": 0, "fldName": None})
    with pytest.raises(ValueError):
        validate_record("fields", {"fldDateUpdated": "2000-01-01"})
    with pytest.raises(ValueError):
        validate_record("production", {"prfPrdOilNetMillSm3": float("nan")})


def test_failure_does_not_keep_previous_entity_evidence(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient
) -> None:
    client.feature_observations = [{"entity": "previous"}]
    value = response({})
    value._content = b"invalid JSON"
    assert client.session is not None
    monkeypatch.setattr(client.session, "get", lambda *a, **k: value)
    with pytest.raises(ValueError):
        client.query_entity("wellbores")
    assert client.feature_observations[0]["size_bytes"] == len(b"invalid JSON")
    assert client.feature_observations[0]["status"] == 200


def test_pause_after_slow_response(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient
) -> None:
    now = [100.0]
    pauses: list[float] = []
    monkeypatch.setattr(
        "worldenergydata.sodir.feature_service.time.monotonic", lambda: now[0]
    )
    monkeypatch.setattr(
        "worldenergydata.sodir.feature_service.time.sleep", pauses.append
    )

    def slow(*args: object, **kwargs: object) -> requests.Response:
        now[0] += 3
        return response({"features": []})

    assert client.session is not None
    monkeypatch.setattr(client.session, "get", slow)
    client.query_entity("fields")
    client.query_entity("fields")
    assert pauses == [2]


def test_processor_epoch_dates() -> None:
    from worldenergydata.sodir.processors.wellbore_processor import WellboreProcessor

    raw = {
        "wlbWellboreName": "1/1-1",
        "wlbEntryDate": 946684800000,
        "wlbCompletionDate": 947548800000,
    }
    processed = WellboreProcessor().process(processor_record("wellbores", raw))
    assert processed["entry_date"] == "2000-01-01"
    assert processed["completion_date"] == "2000-01-11"
    assert raw["wlbEntryDate"] == 946684800000


def test_infinite_timeout_rejected_before_transport(client: SodirAPIClient) -> None:
    client.timeout = float("inf")
    with pytest.raises(ValueError, match="positive"):
        client.query_entity("fields")


def test_default_projection_matches_successful_live_probe(
    monkeypatch: pytest.MonkeyPatch, client: SodirAPIClient
) -> None:
    calls = transport(monkeypatch, client, [{"features": []}])
    client.query_entity("wellbores")
    assert (
        calls[0][1]["params"]["outFields"]
        == "OBJECTID,wlbWellboreName,wlbNpdidWellbore"
    )


def test_default_client_http_error_has_one_transport_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = SodirAPIClient("https://factmaps.sodir.no/api/rest")
    assert client.session is not None
    assert client.session.get_adapter(client.base_url).max_retries.total == 0
    calls: list[tuple[object, ...]] = []

    def get(*args: object, **kwargs: object) -> requests.Response:
        calls.append(args)
        return response({}, 500)

    assert client.session is not None
    monkeypatch.setattr(client.session, "get", get)
    with pytest.raises(ValueError, match="HTTP 500"):
        client.query_entity("fields")
    assert len(calls) == 1


@pytest.mark.parametrize("retry_total", [1, None])
def test_retrying_adapter_refused_before_transport(
    client: SodirAPIClient, retry_total: int | None
) -> None:
    assert client.session is not None
    client.session.get_adapter(client.base_url).max_retries.total = retry_total
    with pytest.raises(ValueError, match="transport retries must be disabled"):
        client.query_entity("fields")


def test_default_production_projection_is_consumable() -> None:
    values: dict[str, str | int | float] = {
        "OBJECTID": 1,
        "prfInformationCarrier": "SYNTHETIC",
        "prfInformationCarrierKind": "FIELD",
        "prfYear": 2000,
        "prfMonth": 1,
        "prfPrdOilNetMillSm3": 1.0,
    }
    row = {key: values[key] for key in DEFAULT_FIELDS["production"]}
    assert set(row) == set(values)
    assert processor_record("production", row)["oil_sm3"] == 1e6


def test_curated_synthetic_record_has_generation_timestamp() -> None:
    records = json.loads((FIXTURES / "service_observations.json").read_text())
    synthetic = next(record for record in records if "dataset_kind" in record)
    assert "retrieved_at_utc" not in synthetic
    assert synthetic["generated_at_utc"] == "2026-10-11T20:23:38.131597+00:00"
