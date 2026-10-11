import json

import pytest

from worldenergydata.federal_acreage.evidence import evaluate
from worldenergydata.federal_acreage.federal_acreage import FederalAcreage
from worldenergydata.federal_acreage.provider import FixtureRecordProvider
from worldenergydata.federal_acreage.report import write_outputs

FIXTURE = "examples/workflows/federal-acreage-evidence/fixture_records.json"


def test_fixture_and_version(tmp_path):
    provider = FixtureRecordProvider(FIXTURE)
    records, sources = provider.records_for_tract(provider.tract)
    assert len(records) == 6
    assert sources[0].kind == "fixture"
    payload = json.loads(open(FIXTURE).read())
    payload["schema_version"] = "wrong"
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        FixtureRecordProvider(path)


def test_live_provider_seam(tmp_path):
    fixture = FixtureRecordProvider(FIXTURE)

    class LiveProvider:
        def records_for_tract(self, tract):
            records, sources = fixture.records_for_tract(tract)
            sources = [s.model_copy(update={"kind": "live"}) for s in sources]
            return records, sources

    result = evaluate(fixture.tract, *LiveProvider().records_for_tract(fixture.tract))
    outputs = write_outputs(result, tmp_path, "live_test")
    assert "FIXTURE-DATA" not in outputs["report_html"].read_text()
    assert result.acreage.leased_acres.value == 200


def test_router(tmp_path):
    cfg = dict(
        data=dict(source="fixture", file="fixture_records.json"),
        Analysis=dict(
            analysis_root_folder="examples/workflows/federal-acreage-evidence",
            result_folder=str(tmp_path),
        ),
        meta=dict(label="pilot"),
    )
    result = FederalAcreage().router(cfg)
    assert result["federal_acreage"]["status"] == "completed"
    cfg["data"]["source"] = "live"
    with pytest.raises(ValueError):
        FederalAcreage().router(cfg)
