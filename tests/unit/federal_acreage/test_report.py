import json

from worldenergydata.federal_acreage.evidence import evaluate
from worldenergydata.federal_acreage.provider import FixtureRecordProvider
from worldenergydata.federal_acreage.report import write_outputs


def test_report_contract_and_determinism(tmp_path):
    provider = FixtureRecordProvider(
        "examples/workflows/federal-acreage-evidence/fixture_records.json"
    )
    result = evaluate(provider.tract, *provider.records_for_tract(provider.tract))
    outputs = write_outputs(result, tmp_path, "pilot")
    before = {key: path.read_bytes() for key, path in outputs.items()}
    html = outputs["report_html"].read_text()
    payload = json.loads(outputs["result_json"].read_text())
    assert payload == result.model_dump(mode="json")
    for sourced in payload["acreage"].values():
        assert f'{sourced["value"]:.3f}' in html
    for text in [
        "evidence_partial",
        "FIXTURE-DATA",
        "PILOT-TRACT-A",
        "Federal land records are not evidence of title.",
        "County recorder / title-chain records were NOT evaluated.",
    ]:
        assert text in html
    for forbidden in ["<script", "<link ", "src=", "url(", "@import"]:
        assert forbidden not in html
    write_outputs(result, tmp_path, "pilot")
    assert before == {key: path.read_bytes() for key, path in outputs.items()}
