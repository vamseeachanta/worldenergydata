"""Envelope and identity contract for the composite Explorer sidecar."""

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.field_development.explorer_contract import (
    explorer_panel_schema,
    validate_explorer_payload,
)

REPO = Path(__file__).resolve().parents[3]
SCHEMA = (
    REPO / "src/worldenergydata/field_development/schema/explorer_panel.schema.json"
)


@pytest.fixture
def payload():
    return {
        "meta": {"generated_by": "synthetic producer"},
        "fields": {"field_a": {"id": "field_a", "name": "Synthetic field"}},
        "wells": {},
    }


def test_minimal_composite_is_returned_unchanged(payload):
    before = copy.deepcopy(payload)
    assert validate_explorer_payload(payload) is payload
    assert payload == before


@pytest.mark.parametrize("wells", [{}, {"fields": {}, "wells": []}])
def test_empty_wells_are_valid(payload, wells):
    payload["wells"] = wells
    assert validate_explorer_payload(payload) is payload


def test_empty_field_map_is_valid(payload):
    payload["fields"] = {}
    assert validate_explorer_payload(payload) is payload


def test_optional_panels_and_additions_are_lossless(payload):
    payload["extension"] = {"revision": "future"}
    field = payload["fields"]["field_a"]
    field.update(
        performance=None,
        norms=[],
        metrics={"reported_text": "1,234.5", "unknown": None},
        future_panel={"values": [None, "unknown", False]},
    )
    before = copy.deepcopy(payload)
    assert validate_explorer_payload(payload) == before
    assert "reservoir" not in field


@pytest.mark.parametrize("value", [None, [], "object", 1])
def test_non_object_root_is_rejected(value):
    with pytest.raises(ValidationError):
        validate_explorer_payload(value)


@pytest.mark.parametrize("key", ["meta", "fields", "wells"])
def test_envelope_objects_are_required(payload, key):
    del payload[key]
    with pytest.raises(ValidationError, match=key):
        validate_explorer_payload(payload)


@pytest.mark.parametrize("key", ["meta", "fields", "wells"])
@pytest.mark.parametrize("value", [None, [], "object"])
def test_envelope_objects_have_strict_types(payload, key, value):
    payload[key] = value
    with pytest.raises(ValidationError, match=key):
        validate_explorer_payload(payload)


@pytest.mark.parametrize("value", [None, [], "field"])
def test_field_record_must_be_an_object(payload, value):
    payload["fields"]["field_a"] = value
    with pytest.raises(ValidationError):
        validate_explorer_payload(payload)


@pytest.mark.parametrize("key", ["id", "name"])
def test_field_identity_is_required(payload, key):
    del payload["fields"]["field_a"][key]
    with pytest.raises(ValidationError, match=key):
        validate_explorer_payload(payload)


@pytest.mark.parametrize("key", ["id", "name"])
@pytest.mark.parametrize("value", [None, 12, True, [], {}])
def test_field_identity_is_a_strict_string(payload, key, value):
    payload["fields"]["field_a"][key] = value
    with pytest.raises(ValidationError, match=key):
        validate_explorer_payload(payload)


def test_map_key_must_match_field_id(payload):
    payload["fields"]["field_a"]["id"] = "field_b"
    with pytest.raises(ValidationError, match="map key must match field id"):
        validate_explorer_payload(payload)


def test_map_key_must_be_a_string(payload):
    payload["fields"] = {12: {"id": "12", "name": "Synthetic field"}}
    with pytest.raises(ValidationError):
        validate_explorer_payload(payload)


def test_committed_composite_is_validated_in_memory():
    sidecar = REPO / "reports/lower_tertiary/lifecycle/_explorer.json"
    raw = sidecar.read_bytes()
    payload = json.loads(raw)
    before = copy.deepcopy(payload)
    assert validate_explorer_payload(payload) is payload
    assert payload == before
    assert sidecar.read_bytes() == raw


def test_generated_schema_matches_committed_schema():
    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == explorer_panel_schema()


def test_schema_states_envelope_guarantees_and_limits():
    schema = explorer_panel_schema()
    assert set(schema["required"]) == {"meta", "fields", "wells"}
    assert schema["additionalProperties"] is True
    field_ref = schema["properties"]["fields"]["additionalProperties"]["$ref"]
    field_schema = schema["$defs"][field_ref.rsplit("/", 1)[1]]
    assert set(field_schema["required"]) == {"id", "name"}
    assert all(
        field_schema["properties"][key]["type"] == "string" for key in ("id", "name")
    )
    assert field_schema["additionalProperties"] is True
    assert "procedural" in schema["description"]
    assert "Nested panel bodies are not validated" in schema["description"]
    assert '"default"' not in json.dumps(schema)
