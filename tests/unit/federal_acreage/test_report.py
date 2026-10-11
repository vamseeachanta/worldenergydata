import json
from html.parser import HTMLParser

import pytest
from fixture_paths import EXAMPLE_DIR, FIXTURE

from worldenergydata.federal_acreage.evidence import evaluate
from worldenergydata.federal_acreage.provider import FixtureRecordProvider
from worldenergydata.federal_acreage.report import render_html, write_outputs


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self.tables[-1].append([])
        elif tag in {"td", "th"}:
            self.cell = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in {"td", "th"}:
            self.tables[-1][-1].append(self.cell)
            self.cell = None


def expected_area(item):
    if item.value is not None:
        return f"{item.value:.3f}"
    return f"unavailable ({item.status}: {item.note})"


def assert_record_cells(html, result):
    parser = TableParser()
    parser.feed(html)
    inputs, _, records, _, _ = parser.tables
    assert dict(inputs[1:])["aliquots"] == ", ".join(result.tract.aliquots)
    assert len(records[1:]) == len(result.records)
    for cells, record in zip(records[1:], result.records):
        assert cells[0] == record.record_serial
        assert cells[8] == expected_area(record.area_acres)
        assert cells[9] == expected_area(record.intersect_acres)
    for table in parser.tables:
        for row in table:
            for cell in row:
                assert cell != "None"
                assert not any(token in cell for token in ("{'", "['", "model_dump"))


def test_report_contract_and_determinism(tmp_path):
    provider = FixtureRecordProvider(FIXTURE)
    result = evaluate(provider.tract, *provider.records_for_tract(provider.tract))
    outputs = write_outputs(result, tmp_path, "pilot")
    before = {key: path.read_bytes() for key, path in outputs.items()}
    html = outputs["report_html"].read_text()
    assert_record_cells(html, result)
    assert "derived-no-record" in html
    assert result.acreage.no_record_acres.note in html
    assert "Derived from tract-input and fixture-mlrs-synthetic" in html
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


@pytest.mark.parametrize("record_area", [100, 160])
def test_report_ambiguity_and_missing_values(record_area):
    provider = FixtureRecordProvider(FIXTURE)
    records, sources = provider.records_for_tract(provider.tract)
    record = records[0].model_copy(
        update={"area": records[0].area.model_copy(update={"value": record_area})}
    )
    result = evaluate(provider.tract, [record], sources)
    html = render_html(result)
    assert_record_cells(html, result)
    assert "not stated" in html


def test_committed_outputs_match_fresh_render(tmp_path):
    example = EXAMPLE_DIR
    provider = FixtureRecordProvider(example / "fixture_records.json")
    result = evaluate(provider.tract, *provider.records_for_tract(provider.tract))
    outputs = write_outputs(result, tmp_path, "federal_acreage_evidence")
    for path in outputs.values():
        assert path.read_bytes() == (example / "outputs" / path.name).read_bytes()
