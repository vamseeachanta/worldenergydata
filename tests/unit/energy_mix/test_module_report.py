"""Numerical anchors and delivery checks for the offline module report."""

import importlib.util
import json
import re
import socket
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from urllib import request

import pytest

from worldenergydata.energy_mix.irena import load_export
from worldenergydata.energy_mix.query import query_export

ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / "scripts/reporting/build_wenergymix_report.py"
SPEC = importlib.util.spec_from_file_location("wenergymix_report", BUILDER)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
REBUILD = "PYTHONPATH=src python scripts/reporting/build_wenergymix_report.py"


class Report(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.values = []
        self.ids = []
        self.links = []
        self.headings = []
        self.visible = []
        self.hidden = 0
        self.metric = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in ("script", "style"):
            self.hidden += 1
        if "data-metric" in attributes:
            self.metric = attributes["data-metric"]
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "a":
            self.links.append(attributes.get("href", ""))
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden -= 1
        if tag in ("span", "text"):
            self.metric = None

    def handle_data(self, text):
        if self.metric:
            self.values.append((self.metric, text))
        if not self.hidden:
            self.visible.append(text)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("The report is built without network access")

    monkeypatch.setattr(request, "urlopen", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def test_three_hand_worked_energy_anchors():
    example = builder.calculate_example()
    # BIPM SI Brochure, 9th ed. (2019), v4.01 (2026), section 3,
    # table 7: giga/mega = 10**9 / 10**6 = 1000; the hour cancels.
    # First fixture observation: 20.25 * 1000 = 20250 MWh, exactly.
    assert Decimal(example["converted"][0]["generation_mwh"]) == Decimal("20250")
    # Third fixture observation: 1 * 1000 = 1000 MWh, exactly.
    assert Decimal(example["converted"][2]["generation_mwh"]) == Decimal("1000")
    # Reported-zero boundary case: 0 * 1000 = 0 MWh, exactly.
    # This is a separate synthetic variation, not the missing middle value.
    assert Decimal(example["zero"][0]["generation_mwh"]) == Decimal("0")


def payload(text):
    match = re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>', text, re.S
    )
    assert match, REBUILD
    return json.loads(match[1])


def test_report_rebuild_and_worked_example_consistency(tmp_path):
    before = builder.FIXTURE.read_bytes()
    output = tmp_path / "report.html"
    builder.build_report(output)
    fresh = output.read_text(encoding="utf-8")
    committed = (builder.REPORT_DIR / "index.html").read_text(encoding="utf-8")
    data = payload(fresh)
    assert data["example"]["converted"] == builder.csv_rows(
        query_export(before, generation_unit="MWh")
    )
    assert data["example"]["original"] == builder.csv_rows(before)
    assert data["example"]["manifest"]["rows"] == len(load_export(before))
    # Every marked number in the worked example, including chart labels, uses
    # this common metric map. Decimal comparison tolerance is 1e-12 absolute.
    for text in (fresh, committed):
        report = Report(text)
        assert report.values
        for key, value in report.values:
            assert abs(
                Decimal(value.replace(",", "")) - Decimal(data["metrics"][key])
            ) <= Decimal("1e-12"), REBUILD

    # Mask numeric presentation and the document binding before comparing
    # structure. Values and embedded payloads are compared separately above.
    def masked(text):
        text = re.sub(r'(?<=content=")[a-f0-9]{64}(?=")', "BINDING", text)
        text = re.sub(
            r'(<(?:span|text)[^>]*data-metric="[^"]+"[^>]*>)[^<]+', r"\1VALUE", text
        )
        return re.sub(
            r'(<script id="report-data" type="application/json">).*?(</script>)',
            r"\1DATA\2",
            text,
            flags=re.S,
        )

    assert payload(committed) == data, REBUILD
    assert masked(committed) == masked(fresh), REBUILD
    assert builder.FIXTURE.read_bytes() == before
    assert b"\r" not in output.read_bytes()


def test_headline_is_calculated_from_displayed_inputs():
    text = (builder.REPORT_DIR / "index.html").read_text(encoding="utf-8")
    metrics = payload(text)["metrics"]
    # Displayed 20.25 GWh * displayed 1000 MWh/GWh = 20250 MWh.
    assert Decimal(metrics["alpha_gwh"]) * Decimal(metrics["conversion"]) == Decimal(
        metrics["alpha_mwh"]
    )


def test_report_structure_references_and_public_text():
    text = (builder.REPORT_DIR / "index.html").read_text(encoding="utf-8")
    report = Report(text)
    assert len(report.ids) == len(set(report.ids))
    assert report.headings.count("h1") == 1
    assert report.headings.count("h2") == 10
    assert set(report.headings) == {"h1", "h2", "h3"}
    assert '<body class="hs-doc">' in text
    assert "<strong" not in text and "<b>" not in text
    for href in report.links:
        if href.startswith("#"):
            assert href[1:] in report.ids
        elif not href.startswith("https:"):
            assert (builder.REPORT_DIR / href).is_file(), href
    visible = " ".join(report.visible)
    assert "Draft for maintainer review" in visible
    assert "authored synthetic data" in visible
    assert not re.search(
        r"\b(owner|lane|seat|job|session|could|should|would)\b", visible, re.I
    )
    assert not re.search(r"/(home|mnt|tmp)/|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="https?:', text)


def test_text_inputs_and_outputs_are_utf8_and_lf():
    paths = [BUILDER, Path(__file__), *builder.REPORT_DIR.iterdir()]
    for path in paths:
        raw = path.read_bytes()
        raw.decode("utf-8")
        assert b"\r" not in raw, path.name
        assert raw.endswith(b"\n"), path.name
    changes = json.loads(
        (builder.REPORT_DIR / "changes.json").read_text(encoding="utf-8")
    )
    for change in changes["revisions"][0]["changes"]:
        assert change in (builder.REPORT_DIR / "index.html").read_text(encoding="utf-8")


def test_missing_measurement_and_source_preservation_consistency():
    example = builder.calculate_example()
    assert example["converted"][1]["generation_mwh"] == ""
    assert example["converted"][1]["capacity_mw"] == "0"
    assert len(example["selected"]) == 1
    for before, after in zip(example["original"], example["converted"]):
        for key in (
            "country",
            "iso_code",
            "year",
            "technology",
            "capacity_mw",
            "source_url",
            "citation",
        ):
            assert after[key] == before[key]


def test_every_worked_metric_matches_module_results_consistency():
    text = (builder.REPORT_DIR / "index.html").read_text(encoding="utf-8")
    data = payload(text)
    raw = builder.FIXTURE.read_bytes()
    loaded = load_export(raw)
    converted = builder.csv_rows(query_export(raw, generation_unit="MWh"))
    metrics = data["metrics"]
    for index, row in enumerate(loaded):
        for field in ("year", "capacity_mw", "generation_gwh"):
            if row[field] is not None:
                assert Decimal(metrics[f"row_{index}_{field}"]) == Decimal(
                    str(row[field])
                )
        value = converted[index]["generation_mwh"]
        if value:
            assert Decimal(metrics[f"row_{index}_generation_mwh"]) == Decimal(value)
    assert metrics["alpha_gwh"] == data["example"]["original"][0]["generation_gwh"]
    assert metrics["alpha_mwh"] == converted[0]["generation_mwh"]
    assert metrics["beta_gwh"] == data["example"]["original"][2]["generation_gwh"]
    assert metrics["beta_mwh"] == converted[2]["generation_mwh"]
    assert int(metrics["input_rows"]) == len(loaded)
    assert int(metrics["selected_rows"]) == len(data["example"]["selected"])
    assert int(metrics["source_bytes"]) == len(raw)
