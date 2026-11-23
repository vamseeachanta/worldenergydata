"""Synthetic direct-label DP classes; tokens are inputs, not equipment ratings.

The public-source label grammar observed for #1102 is represented anonymously
as ``DP System DP-3 rated ...``. No certification or corpus result is asserted.
"""

import csv
import importlib.util
from io import BytesIO
from pathlib import Path

import pytest

from worldenergydata.vessel_fleet.parsers.rig_summary import parse_rig_summary_text


@pytest.mark.parametrize(
    "text, expected",
    [
        ("DP System: DP-3", 3),
        ("DP System DP 2", 2),
        ("DP System DP1", 1),
        ("  dp\tSYSTEM : dp-2", 2),
        ("\tDP   System\tDP-3 rated for synthetic conditions", 3),
        ("DP System: DP-2\nDP System DP 2", 2),
        ("DP System: DP-3 / DP3", 3),
        ("DP System: synthetic SDP-23 controller, DP-3", 3),
        ("DP System: DP-1\r\nLength: 100 ft", 1),
        ("DP System: DP 2, synthetic equipment", 2),
    ],
)
def test_explicit_same_line_class(text, expected):
    parsed = parse_rig_summary_text(text)
    assert parsed["DP_CLASS"] == expected
    assert type(parsed["DP_CLASS"]) is int


@pytest.mark.parametrize(
    "text",
    [
        "",
        "DP System:",
        "DP System: synthetic controller",
        "DP System: SDP-23",
        "DP System: DPS-3",
        "Classification: DPS-3",
        "Model: SDP-23",
        "Rig Design: DP-3 capable",
        "Drill pipe DP 2",
        "Marketing: DP-3 performance",
        "DP-3",
        "Other DP System: DP-3",
        "DP Systems: DP-3",
        "DP Systematic DP-3",
        "DP\nSystem: DP-3",
        "DP System:\nDP-3",
        "DP System:\nOther equipment DP-3",
        "DP System: DP-0",
        "DP System: DP-4",
        "DP System: DP-23",
        "DP System: DP-2.0",
        "DP System: DP-2,5",
        "DP System: DP-3a",
        "DP System: DP-2.0a",
        "DP System: DP-2,50x",
        "DP System: DP--1",
        "DP System: DP-2 and DP-4",
    ],
)
def test_missing_or_unsupported_evidence_is_omitted(text):
    assert "DP_CLASS" not in parse_rig_summary_text(text)


@pytest.mark.parametrize(
    "text",
    ["DP System: DP-2 and DP-3", "DP System: DP-1\nDP System: DP-3"],
)
def test_conflicting_classes_warn_and_are_omitted(text, caplog):
    assert "DP_CLASS" not in parse_rig_summary_text(text)
    assert "Conflicting DP System classes" in caplog.text


def _pdf_bytes(*, image_only=False):
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    stream = BytesIO()
    canvas = Canvas(stream)
    if image_only:
        canvas.drawImage(ImageReader(Image.new("RGB", (10, 10), "black")), 40, 600)
    else:
        for y, text in [(700, "DP System: DP-3"), (680, "Length: 100 ft")]:
            canvas.drawString(40, y, text)
    canvas.save()
    return stream.getvalue()


@pytest.mark.parametrize("with_mapping", [False, True])
def test_real_pdf_retains_typed_class_and_source(monkeypatch, with_mapping):
    from worldenergydata.vessel_fleet.collectors.spec_pdf_collector import (
        SpecPdfCollector,
    )
    from worldenergydata.vessel_fleet.dedup.deduplicator import deduplicate_fleet

    collector = SpecPdfCollector(
        name="synthetic",
        owner="synthetic",
        rate_limit=0,
        field_mapping={"DP System": "DP_CLASS"} if with_mapping else None,
    )
    monkeypatch.setattr(collector, "get_bytes", lambda url: _pdf_bytes())
    url = "https://example.org/spec.pdf"
    [record] = collector.collect_from_urls({"synthetic": url})
    assert record["DP_CLASS"] == 3
    assert type(record["DP_CLASS"]) is int
    assert record["DATA_SOURCE"] == "contractor_spec_pdf"
    assert record["DATA_SOURCE_URL"] == url
    assert record["OWNER"] == "synthetic"
    # 100 ft * 0.3048 m/ft, rounded to the parser's one decimal place.
    assert record["LOA_M"] == 30.5
    table_record = {"VESSEL_NAME": "synthetic", "DATA_SOURCE": "contractor_fleet_page"}
    [merged] = deduplicate_fleet([{**table_record, "DP_CLASS": 1}, record])
    assert merged["DP_CLASS"] == 3


def test_image_only_pdf_preserves_separate_fleet_record(monkeypatch, caplog):
    from worldenergydata.vessel_fleet.collectors.spec_pdf_collector import (
        SpecPdfCollector,
    )
    from worldenergydata.vessel_fleet.dedup.deduplicator import deduplicate_fleet

    collector = SpecPdfCollector(name="synthetic", owner="synthetic", rate_limit=0)
    monkeypatch.setattr(collector, "get_bytes", lambda url: _pdf_bytes(image_only=True))
    table_record = {
        "VESSEL_NAME": "synthetic",
        "DATA_SOURCE": "contractor_fleet_page",
        "DP_CLASS": 2,
    }
    records = collector.collect_from_urls({"synthetic": "https://example.org/spec.pdf"})
    assert records == []
    assert deduplicate_fleet([table_record, *records]) == [table_record]
    assert "Empty PDF text" in caplog.text


@pytest.fixture
def ingest():
    script = (
        Path(__file__).resolve().parents[3]
        / "scripts/vessel_fleet/ingest_contractor_spec_pdfs.py"
    )
    spec = importlib.util.spec_from_file_location("dp_spec_ingest", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("specs", [{"DP_CLASS": 3}, {}])
@pytest.mark.parametrize("destination", ["raw", "curated"])
def test_class_survives_isolated_stores_and_csv(ingest, tmp_path, specs, destination):
    from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

    extraction = {
        "owner": "synthetic",
        "vessels": {"synthetic": {"pdf": "sample.pdf", "specs": specs}},
    }
    urls = {"sample.pdf": "https://example.org/spec.pdf"}
    store = ParquetStore(tmp_path / "curated")
    original = {
        "VESSEL_NAME": "synthetic",
        "DATA_SOURCE": "contractor_fleet_page",
        "DP_CLASS": 2,
        "LOA_M": 100.0,
    }
    store.save([original], "drilling_rigs.parquet")
    assert ingest.write_raw_source(extraction, tmp_path, urls, "synthetic") == 1
    [raw] = ParquetStore(tmp_path / "raw/spec_pdf_dimensions").load("synthetic.parquet")
    assert raw["DATA_SOURCE"] == "contractor_spec_pdf"
    if destination == "raw":
        if specs:
            assert raw["DP_CLASS"] == 3
        else:
            assert "DP_CLASS" not in raw

    assert ingest.apply_to_curated(extraction, tmp_path, urls) == 1
    [curated] = store.load("drilling_rigs.parquet")
    expected = specs.get("DP_CLASS", original["DP_CLASS"])
    assert curated["DP_CLASS"] == expected
    assert curated["LOA_M"] == original["LOA_M"]
    with (tmp_path / "curated/drilling_rigs.csv").open(newline="") as stream:
        [exported] = csv.DictReader(stream)
    assert int(exported["DP_CLASS"]) == expected
