import json

import pytest
from pydantic import ValidationError

from worldenergydata.federal_acreage.evidence import evaluate
from worldenergydata.federal_acreage.models import SourcedValue, TractOfInterest
from worldenergydata.federal_acreage.provider import FixtureRecordProvider

FIXTURE = "examples/workflows/federal-acreage-evidence/fixture_records.json"


def test_tract_validation():
    provider = FixtureRecordProvider(FIXTURE)
    tract = provider.tract.model_dump()
    tract["gross_area_acres"] = 319
    with pytest.raises(ValidationError):
        TractOfInterest(**tract)
    tract["gross_area_acres"] = 320
    tract["aliquots"][0] = "BAD"
    with pytest.raises(ValidationError):
        TractOfInterest(**tract)


@pytest.mark.parametrize("status", ["unavailable", "ambiguous"])
def test_marker_states(status):
    marker = SourcedValue(
        value=None, status=status, source_id=None, note="Unknown geometry"
    )
    assert marker.model_dump()["value"] is None
    with pytest.raises(ValidationError):
        SourcedValue(value=40, status=status, source_id=None, note="Unknown geometry")
    with pytest.raises(ValidationError):
        SourcedValue(value=40, status="available", source_id=None, note=None)


def test_schema_shape_round_trip():
    provider = FixtureRecordProvider(FIXTURE)
    result = evaluate(provider.tract, *provider.records_for_tract(provider.tract))
    payload = json.loads(result.model_dump_json())
    assert payload["schema_version"] == "federal-acreage-result-v1"
    assert payload["screening_status"] == "evidence_partial"
    assert payload["title_chain_gap"]["status"] == "not_evaluated"
    expected = dict(
        gross_area_acres=320.0,
        federal_record_coverage_acres=280.0,
        leased_acres=200.0,
        expired_or_nonleased_acres=80.0,
        no_record_acres=40.0,
    )
    assert set(payload["acreage"]) == set(expected)
    for key, value in expected.items():
        assert payload["acreage"][key] == dict(
            value=value,
            status="available",
            source_id=(
                "tract-input" if key == "gross_area_acres" else "fixture-mlrs-synthetic"
            ),
            note=None,
        )
        assert isinstance(payload["acreage"][key]["value"], float)
    assert type(result).model_validate_json(result.model_dump_json()) == result


def test_reversed_lease_dates_rejected():
    from worldenergydata.federal_acreage.models import FederalLandRecord

    with pytest.raises(ValidationError, match="Expiration precedes effectiveness"):
        FederalLandRecord(
            record_serial="SYN-REVERSED",
            record_type="lease",
            record_status="expired",
            effective_date="2030-01-01",
            expiration_date="2024-01-01",
            area={"value": 40.0, "unit": "acres"},
            aliquots=["NE-NE"],
            source_id="fixture-mlrs-synthetic",
        )
