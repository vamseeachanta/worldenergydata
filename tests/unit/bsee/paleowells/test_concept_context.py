"""Geological context from synthetic, explicitly supplied field-era maps."""

import copy
import json

import pytest
from pydantic import ValidationError

from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.schema import export_schema


def enrich(concept, *, field_code="FX1", eras=None, source="Synthetic era table"):
    from worldenergydata.bsee.paleowells.concept_context import enrich_concept_context

    return enrich_concept_context(
        concept,
        field_code=field_code,
        field_era_map={"FX1": "Eocene"} if eras is None else eras,
        source_reference=source,
    )


def test_old_inputs_leave_context_null_and_unset():
    concept = FieldConcept(name="Synthetic")
    assert concept.geological_era is None
    assert concept.play_group is None
    assert concept.model_fields_set == {"name"}
    assert FieldConcept.model_validate_json(concept.model_dump_json()) == concept


@pytest.mark.parametrize("attribute", ["geological_era", "play_group"])
@pytest.mark.parametrize("value", ["", " \t\n", 7])
def test_invalid_context_is_rejected(attribute, value):
    with pytest.raises(ValidationError):
        FieldConcept(name="Synthetic", **{attribute: value})


def test_context_and_measurements_survive_json_roundtrip():
    concept = FieldConcept(
        name="Synthetic",
        geological_era="Eocene",
        play_group="Lower Tertiary",
        reservoir_depth_tvd_m=1250.5,
        reservoir_pressure_psi=2500.25,
        reservoir_temperature_f=-40.5,
        fluid_type="oil",
        api_gravity=35.5,
        hpht=False,
    )
    restored = FieldConcept.model_validate_json(concept.model_dump_json())
    assert restored == concept
    assert restored.geological_era == "Eocene"
    assert restored.play_group == "Lower Tertiary"


@pytest.mark.parametrize("era", ["Paleocene", "Eocene", "Oligocene", "Miocene"])
def test_known_era_updates_only_context_and_returns_provenance(era):
    concept = FieldConcept(
        name="Synthetic",
        reservoir_depth_tvd_m=1250.5,
        reservoir_pressure_psi=2500.25,
        reservoir_temperature_f=-40.5,
        fluid_type="oil",
        api_gravity=35.5,
        hpht=True,
        data_source="Original synthetic source",
    )
    eras = {"FX1": era, "FX2": "Pliocene"}
    original = concept.model_dump()
    original_set = concept.model_fields_set.copy()
    original_map = copy.deepcopy(eras)
    result, receipt = enrich(concept, eras=eras)
    expected_play = None if era == "Miocene" else "Lower Tertiary"
    assert result.model_dump() == {
        **original,
        "geological_era": era,
        "play_group": expected_play,
    }
    assert result is not concept
    assert concept.model_dump() == original
    assert concept.model_fields_set == original_set
    assert eras == original_map
    assert receipt.field_code == "FX1"
    assert receipt.source_reference == "Synthetic era table"
    assert receipt.geological_era == era
    assert receipt.mapping_method == "dominant_field_era_exact_code"
    assert "producing reservoir" in receipt.limitation
    assert FieldConcept.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "eras", [{}, {"FX2": "Eocene"}, {"FX1": "Unknown"}, {"FX1": None}]
)
def test_unavailable_context_is_a_noop(eras):
    concept = FieldConcept(name="Synthetic", geological_era="Miocene")
    result, receipt = enrich(concept, eras=eras)
    assert result == concept
    assert result is not concept
    assert result.model_fields_set == concept.model_fields_set
    assert receipt is None


def test_lookup_does_not_normalize_or_guess_field_identity():
    concept = FieldConcept(name="Synthetic")
    for code in ("fx1", " FX1 "):
        result, receipt = enrich(concept, field_code=code)
        assert result == concept
        assert receipt is None


@pytest.mark.parametrize(
    "context",
    [
        {"geological_era": "Miocene"},
        {"play_group": "Other synthetic group"},
        {"geological_era": "Eocene", "play_group": "Other synthetic group"},
    ],
)
def test_conflicting_context_raises_without_mutating_inputs(context):
    concept = FieldConcept(name="Synthetic", **context)
    original = concept.model_dump()
    eras = {"FX1": "Eocene"}
    with pytest.raises(ValueError, match="conflicting"):
        enrich(concept, eras=eras)
    assert concept.model_dump() == original
    assert eras == {"FX1": "Eocene"}


def test_identical_context_is_preserved():
    concept = FieldConcept(
        name="Synthetic", geological_era="Eocene", play_group="Lower Tertiary"
    )
    result, receipt = enrich(concept)
    assert result == concept
    assert receipt.geological_era == "Eocene"


def test_other_era_does_not_erase_supplied_play():
    concept = FieldConcept(name="Synthetic", play_group="Supplied synthetic group")
    result, _ = enrich(concept, eras={"FX1": "Miocene"})
    assert result.geological_era == "Miocene"
    assert result.play_group == concept.play_group


@pytest.mark.parametrize("keyword", ["field_code", "source"])
@pytest.mark.parametrize("value", [None, "", " \t", 7, {}])
def test_invalid_metadata_raises_even_without_a_match(keyword, value):
    with pytest.raises(ValueError, match="non-empty string"):
        enrich(FieldConcept(name="Synthetic"), eras={}, **{keyword: value})


@pytest.mark.parametrize("value", ["", " \t", 7, {}])
def test_invalid_matched_era_is_not_silently_ignored(value):
    with pytest.raises(ValueError, match="non-empty string"):
        enrich(FieldConcept(name="Synthetic"), eras={"FX1": value})


@pytest.mark.parametrize("eras", [{}, {"FX1": "Eocene"}])
def test_existing_model_is_revalidated(eras):
    concept = FieldConcept(name="Synthetic").model_copy(update={"api_gravity": 150})
    with pytest.raises(ValidationError):
        enrich(concept, eras=eras)


def test_adapter_does_not_load_files(monkeypatch):
    from worldenergydata.bsee.paleowells import field_era

    def unexpected_load(*args, **kwargs):
        pytest.fail("The adapter must use only the supplied era map")

    monkeypatch.setattr(field_era, "build_field_era_map", unexpected_load)
    monkeypatch.setattr(field_era, "_load_apiraw_pickle", unexpected_load)
    result, _ = enrich(FieldConcept(name="Synthetic"))
    assert result.geological_era == "Eocene"


def test_schema_generation_uses_temporary_output(tmp_path, monkeypatch):
    target = tmp_path / "schema.json"
    monkeypatch.setattr(export_schema, "SCHEMA_PATH", target)
    assert export_schema.write_schema() == target
    schema = json.loads(target.read_text())
    assert schema == export_schema.build_schema()
    for attribute in ("geological_era", "play_group"):
        assert schema["properties"][attribute]["default"] is None
        assert attribute not in schema["required"]
