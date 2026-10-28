"""Offline metadata contracts; synthetic inputs have literal expected mappings.

Source: Esri REST API, Layer (Feature Service), JSON response syntax, accessed
2026-10-19: https://developers.arcgis.com/rest/services-reference/enterprise/layer-feature-service/
Layer IDs and known properties come from the committed feature_schemas.json.
No physical quantities or service capacity limits are inferred by these tests.
"""

import copy
import json
from pathlib import Path

import pytest
import requests

from worldenergydata.sodir.api_client import SodirAPIClient
from worldenergydata.sodir.feature_service import parse_metadata

# Expected mappings are read independently from the committed source document,
# rather than from an object exported by the implementation under test.
SCHEMAS = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_schemas.json"
    ).read_text()
)


@pytest.fixture
def client(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network forbidden in offline tests")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(
        "worldenergydata.sodir.feature_service.time.sleep", lambda _: None
    )
    return SodirAPIClient("https://factmaps.sodir.no/api/rest", max_retries=0)


def metadata(entity):
    """Build synthetic metadata; identity and types must survive unchanged."""
    schema = SCHEMAS[entity]
    return {
        "objectIdField": schema["object_id_field"],
        "fields": [
            {"name": name, "type": kind} for name, kind in schema["properties"].items()
        ],
    }


def transport(monkeypatch, client, payload, status=200):
    raw = json.dumps(payload).encode()
    calls = []

    def get(url, **kwargs):
        calls.append((url, copy.deepcopy(kwargs)))
        result = requests.Response()
        result.status_code = status
        result.url = url + "?f=json"
        result._content = raw
        result._content_consumed = True
        return result

    monkeypatch.setattr(client.session, "get", get)
    return calls, raw


@pytest.mark.parametrize("entity", ["fields", "wellbores", "production"])
def test_metadata_reader_uses_observed_layer(monkeypatch, client, entity):
    payload = metadata(entity)
    calls, raw = transport(monkeypatch, client, payload)
    result = client.get_entity_metadata(entity, max_bytes=len(raw))
    assert result == SCHEMAS[entity]["properties"]
    assert calls[0][0] == SCHEMAS[entity]["source_url"].split("?")[0]
    assert calls[0][1]["params"] == {"f": "json"}
    assert calls[0][1]["stream"] is True
    assert calls[0][1]["allow_redirects"] is False
    assert len(calls) == len(client.feature_observations) == 1
    assert client.feature_observations[0]["size_bytes"] == len(raw)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"fields": [None]},
        {"fields": [{}]},
        {"fields": [{"name": "x"}]},
        {"fields": [{"type": "esriFieldTypeString"}]},
        {"fields": [{"name": "", "type": "esriFieldTypeString"}]},
        {"fields": [{"name": [], "type": "esriFieldTypeString"}]},
        {"fields": [{"name": "x", "type": []}]},
        {"fields": [{"name": "x", "type": "unsupported"}]},
        {
            "fields": [
                {"name": "x", "type": "esriFieldTypeString"},
                {"name": "x", "type": "esriFieldTypeString"},
            ]
        },
    ],
)
def test_malformed_metadata_rejected(payload):
    with pytest.raises((TypeError, ValueError), match="metadata"):
        parse_metadata(payload)


@pytest.mark.parametrize("change", ["missing", "type", "object_id", "oid_type"])
def test_metadata_drift_rejected(monkeypatch, client, change):
    payload = metadata("fields")
    if change == "missing":
        payload["fields"] = payload["fields"][:-1]
    elif change == "type":
        next(f for f in payload["fields"] if f["name"] == "fldName")[
            "type"
        ] = "esriFieldTypeInteger"
    elif change == "object_id":
        payload["objectIdField"] = "different_id"
    else:
        payload["fields"][0]["type"] = "esriFieldTypeInteger"
    transport(monkeypatch, client, payload)
    with pytest.raises(ValueError, match="schema|object ID"):
        client.get_entity_metadata(
            "fields", max_bytes=len(json.dumps(payload).encode())
        )


def test_additional_metadata_properties_are_preserved(monkeypatch, client):
    payload = metadata("fields")
    payload["fields"].append({"name": "newColumn", "type": "esriFieldTypeString"})
    _, raw = transport(monkeypatch, client, payload)
    result = client.get_entity_metadata("fields", max_bytes=len(raw))
    assert result == dict(
        SCHEMAS["fields"]["properties"], newColumn="esriFieldTypeString"
    )


@pytest.mark.parametrize("status", [302, 403, 429, 500])
def test_metadata_http_error_stops_without_retry(monkeypatch, client, status):
    calls, raw = transport(monkeypatch, client, {}, status)
    with pytest.raises(ValueError, match="HTTP"):
        client.get_entity_metadata("fields", max_bytes=len(raw))
    assert len(calls) == 1


def test_metadata_byte_cap(monkeypatch, client):
    _, raw = transport(monkeypatch, client, metadata("fields"))
    with pytest.raises(ValueError, match="byte cap"):
        client.get_entity_metadata("fields", max_bytes=len(raw) - 1)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, float("inf")])
def test_metadata_invalid_budget_before_network(client, limit):
    with pytest.raises(ValueError, match="limits"):
        client.get_entity_metadata("fields", max_bytes=limit)


@pytest.mark.parametrize("method", ["query_entity", "get_entity_metadata"])
@pytest.mark.parametrize("entity", ["invented", "", None, []])
def test_unknown_entity_before_network(client, method, entity):
    with pytest.raises(ValueError, match="entity"):
        getattr(client, method)(entity, max_bytes=1)


def test_metadata_wrong_base_before_network(client):
    client.base_url = "https://example.invalid"
    with pytest.raises(ValueError, match="service base"):
        client.get_entity_metadata("fields", max_bytes=1)


def test_metadata_retrying_adapter_before_network(client):
    client.session.get_adapter(client.base_url).max_retries.total = 1
    with pytest.raises(ValueError, match="transport retries must be disabled"):
        client.get_entity_metadata("fields", max_bytes=1)


@pytest.mark.parametrize("entity", ["fields", "wellbores", "production"])
def test_missing_selected_attribute_is_not_a_null(monkeypatch, client, entity):
    """A requested key absent from {OBJECTID: 1} differs from a present null."""
    transport(monkeypatch, client, {"features": [{"attributes": {"OBJECTID": 1}}]})
    with pytest.raises(ValueError, match="requested attributes"):
        client.query_entity(entity)


def test_explicit_null_in_requested_attribute_is_preserved(monkeypatch, client):
    row = {"OBJECTID": 1, "fldName": None}
    transport(monkeypatch, client, {"features": [{"attributes": row}]})
    assert client.query_entity("fields", select=["OBJECTID", "fldName"]) == [row]


def test_missing_attribute_on_continuation_page(monkeypatch, client):
    pages = iter(
        [
            {
                "features": [{"attributes": {"OBJECTID": 1, "fldName": "SYNTHETIC"}}],
                "exceededTransferLimit": True,
            },
            {"features": [{"attributes": {"OBJECTID": 2}}]},
        ]
    )

    def get(*args, **kwargs):
        result = requests.Response()
        result.status_code = 200
        result._content = json.dumps(next(pages)).encode()
        result._content_consumed = True
        return result

    monkeypatch.setattr(client.session, "get", get)
    with pytest.raises(ValueError, match="requested attributes"):
        client.query_entity("fields", select=["OBJECTID", "fldName"], max_pages=2)


@pytest.mark.parametrize("select", ["OBJECTID", ["OBJECTID", []], ["OBJECTID"] * 2])
def test_invalid_projection_before_network(client, select):
    with pytest.raises(ValueError, match="select"):
        client.query_entity("fields", select=select)
