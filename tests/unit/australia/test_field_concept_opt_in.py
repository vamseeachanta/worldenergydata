"""Pin omitted-well compatibility to executed main output; wells are synthetic."""

import copy
import json
from pathlib import Path
from typing import Any, Callable, Dict

import pytest

from worldenergydata.australia.field_concept import (
    australia_field_to_concept,
    build_australia_field_concept,
)
from worldenergydata.australia.metadata import nopta_wells as nw
from worldenergydata.australia.metadata.well_enrichment import enrich_field_metadata
from worldenergydata.field_development.models import FieldConcept

FIXTURES = Path(__file__).parent / "fixtures"
BASELINE = json.loads((FIXTURES / "field_concept_main_outputs.json").read_text())


@pytest.mark.parametrize("case", BASELINE["cases"], ids=lambda case: case["name"])
def test_omitted_wells_match_recorded_main(case: Dict[str, Any]) -> None:
    inputs = copy.deepcopy(case["input"])
    for build in (australia_field_to_concept, build_australia_field_concept):
        concept = build(inputs)
        assert concept.model_dump(mode="json") == case["output"]
        assert sorted(concept.model_fields_set) == case["fields_set"]
        assert concept.__pydantic_private__ == case["private_attributes"]
        assert inputs == case["input"]


@pytest.mark.parametrize(
    "build", [australia_field_to_concept, build_australia_field_concept]
)
def test_explicit_wells_opt_into_provenance(build: Callable[..., FieldConcept]) -> None:
    sample = json.loads((FIXTURES / "nopta_synthetic.json").read_text())
    wells = nw.normalize_page(sample["pages"][0], nw.parse_layer(sample["layer"]))
    inputs = BASELINE["cases"][0]["input"]
    original = build(inputs)
    options: list[list[Dict[str, Any]]] = [wells, []]
    for opted_in in options:
        enriched = enrich_field_metadata(inputs, opted_in)
        assert "value_origins" in enriched
        assert "value_origins" not in inputs
        concept = build(inputs, wells=opted_in)
        assert concept.data_source != original.data_source
        assert concept.data_source == enriched["source"]
