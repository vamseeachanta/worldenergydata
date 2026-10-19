"""Synthetic rig PDF collection examples; no contractor data is embedded.

Length basis: NIST SP 811 (2008), Appendix B.8, row 'foot (ft)':
https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8
The fixture dimensions and loads below are arbitrary test inputs, not ratings.
"""

from io import BytesIO
from pathlib import Path

import pytest

URL = "https://example.org/spec.pdf"
TEXT = """Length: 100 ft
Breadth: 50 ft
Depth: 20 ft
Moonpool: 10 ft x 5 ft
Hook Load: 1,000 kips
Custom Equipment: synthetic equipment
"""


@pytest.fixture
def module():
    from worldenergydata.vessel_fleet.collectors import spec_pdf_collector

    return spec_pdf_collector


@pytest.fixture
def collector(module):
    return module.SpecPdfCollector(name="synthetic", owner="synthetic", rate_limit=0)


@pytest.fixture
def stub_pdf(collector, monkeypatch, module):
    """Download bytes are synthetic; extraction is isolated in these unit tests."""
    paths = []
    monkeypatch.setattr(collector, "get_bytes", lambda url: b"synthetic bytes")

    def extract(path):
        paths.append(Path(path))
        assert paths[-1].read_bytes() == b"synthetic bytes"
        return TEXT

    monkeypatch.setattr(module, "extract_text_from_pdf", extract)
    return paths


def test_parses_rig_specs_without_field_mapping(collector, stub_pdf):
    """Hand calculation: multiply each input ft value by 0.3048 m/ft.

    100 -> 30.48 -> 30.5; 50 -> 15.24 -> 15.2; 20 -> 6.096 -> 6.1;
    10 -> 3.048 -> 3.0; 5 -> 1.524 -> 1.5, using parser rounding to
    one decimal. The 1,000 kips input requires only removing its comma.
    Conversion source: NIST SP 811 (2008), Appendix B.8, foot row.
    """
    [record] = collector.collect_from_urls({"synthetic": URL})
    assert record == {
        "VESSEL_NAME": "synthetic",
        "VESSEL_CATEGORY": "drilling_rig",
        "OWNER": "synthetic",
        "DATA_SOURCE": "contractor_spec_pdf",
        "DATA_SOURCE_URL": URL,
        "LOA_M": 30.5,
        "RAW_LENGTH_FT": 100.0,
        "BEAM_M": 15.2,
        "RAW_BREADTH_FT": 50.0,
        "DEPTH_M": 6.1,
        "RAW_DEPTH_FT": 20.0,
        "MOONPOOL_LENGTH_M": 3.0,
        "MOONPOOL_WIDTH_M": 1.5,
        "RAW_MOONPOOL_FT": "10 x 5",
        "HOOKLOAD_RATING_KIPS": 1000,
    }
    assert all(not path.exists() for path in stub_pdf)


def test_mapping_adds_custom_fields_without_overwriting_typed_specs(
    collector, stub_pdf
):
    """The direct text mapping must not replace converted metre values with ft."""
    collector.field_mapping = {"Length": "LOA_M", "Custom Equipment": "EQUIPMENT"}
    [record] = collector.collect_from_urls({"synthetic": URL})
    assert record["LOA_M"] == 30.5  # Hand calculation in the preceding test.
    assert record["EQUIPMENT"] == "synthetic equipment"


def test_mapping_cannot_overwrite_source_identity(collector, stub_pdf):
    collector.field_mapping = {"Custom Equipment": "DATA_SOURCE"}
    [record] = collector.collect_from_urls({"synthetic": URL})
    assert record["DATA_SOURCE"] == "contractor_spec_pdf"


def test_non_rig_mapping_is_preserved(collector, stub_pdf):
    collector.vessel_category = "construction_vessel"
    collector.field_mapping = {"Custom Equipment": "EQUIPMENT"}
    [record] = collector.collect_from_urls({"synthetic": URL})
    assert record["EQUIPMENT"] == "synthetic equipment"
    assert "LOA_M" not in record


@pytest.mark.parametrize("text", ["", " \n ", "Marketing: no recognised rig specs"])
def test_no_specs_returns_no_high_priority_record(
    collector, stub_pdf, monkeypatch, caplog, text, module
):
    monkeypatch.setattr(module, "extract_text_from_pdf", lambda path: text)
    assert collector.collect_from_urls({"synthetic": URL}) == []
    assert "synthetic" in caplog.text


def test_failed_extraction_cleans_temporary_file(
    collector, stub_pdf, monkeypatch, caplog, module
):
    paths = []

    def fail(path):
        paths.append(Path(path))
        raise ValueError("synthetic extraction failure")

    monkeypatch.setattr(module, "extract_text_from_pdf", fail)
    assert collector.collect_from_urls({"synthetic": URL}) == []
    assert paths and all(not path.exists() for path in paths)
    assert "synthetic extraction failure" in caplog.text


def test_failed_download_does_not_stop_batch(collector, monkeypatch, caplog, module):
    calls = []

    def download(url):
        calls.append(url)
        if url.endswith("missing.pdf"):
            raise OSError("synthetic download failure")
        return b"synthetic bytes"

    monkeypatch.setattr(collector, "get_bytes", download)
    monkeypatch.setattr(module, "extract_text_from_pdf", lambda path: TEXT)
    records = collector.collect_from_urls(
        {"missing": "https://example.org/missing.pdf", "synthetic": URL}
    )
    assert [record["VESSEL_NAME"] for record in records] == ["synthetic"]
    assert calls == ["https://example.org/missing.pdf", URL]
    assert "synthetic download failure" in caplog.text


def _pdf_bytes(*, image_only=False):
    """Build a PDF in memory; page coordinates and image sizes are arbitrary.

    A blank leading page exercises extraction across pages. The second page
    holds either the worked-example text or an image without a text layer.
    """
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    stream = BytesIO()
    canvas = Canvas(stream)
    canvas.showPage()
    if image_only:
        image = Image.new("RGB", (10, 10), "black")
        canvas.drawImage(ImageReader(image), 40, 600)
    else:
        text = canvas.beginText(40, 700)
        for line in TEXT.splitlines():
            text.textLine(line)
        canvas.drawText(text)
    canvas.save()
    return stream.getvalue()


def test_real_pdfplumber_extraction_and_deduplication(collector, monkeypatch):
    """The PDF dimensions follow the hand calculation above.

    A deliberately conflicting synthetic source-table length of 99.0 m must
    lose to the spec PDF, according to the existing source-priority table in
    dedup/deduplicator.py. Unstated source-table fields must remain present.
    """
    from worldenergydata.vessel_fleet.dedup.deduplicator import deduplicate_fleet

    payload = _pdf_bytes()
    monkeypatch.setattr(collector, "get_bytes", lambda url: payload)
    fleet_record = {
        "VESSEL_NAME": "synthetic",
        "DATA_SOURCE": "contractor_fleet_page",
        "LOA_M": 99.0,
        "RIG_TYPE": "drillship",
    }
    pdf_records = collector.collect_from_urls({"synthetic": URL})
    [merged] = deduplicate_fleet([fleet_record, *pdf_records])
    assert merged["LOA_M"] == 30.5
    assert merged["MOONPOOL_WIDTH_M"] == 1.5
    assert merged["HOOKLOAD_RATING_KIPS"] == 1000
    assert merged["RIG_TYPE"] == "drillship"
    assert merged["DATA_SOURCE"] == "contractor_spec_pdf"
    assert fleet_record["LOA_M"] == 99.0


def test_real_image_only_pdf_leaves_fleet_table_unchanged(
    collector, monkeypatch, caplog
):
    from worldenergydata.vessel_fleet.dedup.deduplicator import deduplicate_fleet

    payload = _pdf_bytes(image_only=True)
    monkeypatch.setattr(collector, "get_bytes", lambda url: payload)
    fleet_record = {
        "VESSEL_NAME": "synthetic",
        "DATA_SOURCE": "contractor_fleet_page",
        "RIG_TYPE": "drillship",
    }
    pdf_records = collector.collect_from_urls({"synthetic": URL})
    assert pdf_records == []
    assert deduplicate_fleet([fleet_record, *pdf_records]) == [fleet_record]
    assert "Empty PDF text" in caplog.text


def test_real_malformed_pdf_does_not_stop_batch(collector, monkeypatch, caplog):
    payload = _pdf_bytes()
    monkeypatch.setattr(
        collector,
        "get_bytes",
        lambda url: b"not a PDF" if url.endswith("bad.pdf") else payload,
    )
    records = collector.collect_from_urls(
        {"bad": "https://example.org/bad.pdf", "synthetic": URL}
    )
    assert [record["VESSEL_NAME"] for record in records] == ["synthetic"]
    assert "Failed to collect bad" in caplog.text
