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


@pytest.mark.parametrize("value", ["DP-4", "DP 3 (DP-22)"])
def test_unsupported_tokens_warn_and_are_omitted(value, caplog):
    assert "DP_CLASS" not in parse_rig_summary_text(f"DP System: {value}")
    assert "Unsupported DP System token" in caplog.text


def _pdf_bytes(*, dp_value="DP-3", image_only=False):
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    stream = BytesIO()
    canvas = Canvas(stream)
    if image_only:
        canvas.drawImage(ImageReader(Image.new("RGB", (10, 10), "black")), 40, 600)
    else:
        for y, text in [(700, f"DP System: {dp_value}"), (680, "Length: 100 ft")]:
            canvas.drawString(40, y, text)
    canvas.save()
    return stream.getvalue()


@pytest.mark.parametrize(
    "dp_value, with_mapping, pdf_class",
    [
        ("DP-3", False, 3),
        ("DP-3", True, 3),
        ("DP-2 and DP-3", True, None),
        ("DP-4", True, None),
        ("synthetic controller", True, None),
    ],
)
def test_real_pdf_retains_typed_class_and_source(
    monkeypatch, dp_value, with_mapping, pdf_class
):
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
    payload = _pdf_bytes(dp_value=dp_value)
    monkeypatch.setattr(collector, "get_bytes", lambda url: payload)
    url = "https://example.org/spec.pdf"
    [record] = collector.collect_from_urls({"synthetic": url})
    if pdf_class is None:
        assert "DP_CLASS" not in record
    else:
        assert record["DP_CLASS"] == pdf_class
        assert type(record["DP_CLASS"]) is int
    assert record["DATA_SOURCE"] == "contractor_spec_pdf"
    assert record["DATA_SOURCE_URL"] == url
    assert record["OWNER"] == "synthetic"
    # 100 ft * 0.3048 m/ft, rounded to the parser's one decimal place.
    assert record["LOA_M"] == 30.5
    table_record = {"VESSEL_NAME": "synthetic", "DATA_SOURCE": "contractor_fleet_page"}
    [merged] = deduplicate_fleet([{**table_record, "DP_CLASS": 2}, record])
    assert merged["DP_CLASS"] == (2 if pdf_class is None else pdf_class)
    assert type(merged["DP_CLASS"]) is int


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


@pytest.mark.parametrize(
    "specs, expected", [({"DP_CLASS": 3}, 3), ({}, 2), ({"DP_CLASS": None}, 2)]
)
def test_class_survives_isolated_stores_and_csv(ingest, tmp_path, specs, expected):
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
    if "DP_CLASS" in specs:
        assert raw["DP_CLASS"] == specs["DP_CLASS"]
    else:
        assert "DP_CLASS" not in raw

    assert ingest.apply_to_curated(extraction, tmp_path, urls) == 1
    [curated] = store.load("drilling_rigs.parquet")
    assert curated["DP_CLASS"] == expected
    assert curated["LOA_M"] == original["LOA_M"]
    with (tmp_path / "curated/drilling_rigs.csv").open(newline="") as stream:
        [exported] = csv.DictReader(stream)
    assert int(exported["DP_CLASS"]) == expected


def test_mixed_pdf_classes_survive_storage_and_fusion(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    from worldenergydata.vessel_fleet.dedup.deduplicator import deduplicate_fleet
    from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

    store = ParquetStore(tmp_path)
    pdf = {"DATA_SOURCE": "contractor_spec_pdf"}
    pdf_rows = [
        {**pdf, "VESSEL_NAME": "A", "DP_CLASS": None},
        {**pdf, "VESSEL_NAME": "B", "DP_CLASS": 3},
        {**pdf, "VESSEL_NAME": "C"},
        {**pdf, "VESSEL_NAME": "D"},
    ]
    path = store.save(pdf_rows, "pdf.parquet")
    raw = store.load("pdf.parquet")
    fleet = [
        {"DATA_SOURCE": "contractor_fleet_page", "VESSEL_NAME": name, "DP_CLASS": 2}
        for name in ("A", "B", "C")
    ]
    merged = deduplicate_fleet(fleet + raw)
    classes = {row["VESSEL_NAME"]: row.get("DP_CLASS") for row in merged}
    assert classes == {"A": 2, "B": 3, "C": 2, "D": None}
    assert all(type(classes[name]) is int for name in ("A", "B", "C"))
    assert [row["DP_CLASS"] for row in raw] == [None, 3, None, None]
    assert pa.types.is_integer(pq.read_schema(path).field("DP_CLASS").type)

    store.save(merged, "merged.parquet")
    with store.export_csv("merged.parquet", "merged.csv").open(newline="") as stream:
        exported = {
            row["VESSEL_NAME"]: row["DP_CLASS"] for row in csv.DictReader(stream)
        }
    assert exported == {"A": "2", "B": "3", "C": "2", "D": ""}


def test_legacy_float_classes_load_and_export_as_nullable_integers(tmp_path):
    import pandas as pd

    from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

    store = ParquetStore(tmp_path)
    pd.DataFrame({"DP_CLASS": [None, 3.0]}).to_parquet(
        tmp_path / "legacy.parquet", engine="pyarrow", index=False
    )
    missing, known = store.load("legacy.parquet")
    assert missing["DP_CLASS"] is None
    assert known["DP_CLASS"] == 3
    assert type(known["DP_CLASS"]) is int
    with store.export_csv("legacy.parquet", "legacy.csv").open(newline="") as stream:
        assert [row["DP_CLASS"] for row in csv.DictReader(stream)] == ["", "3"]
