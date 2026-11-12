"""Draft values and their condition metadata must change together."""

import csv
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts/vessel_fleet/ingest_contractor_spec_pdfs.py"
)


@pytest.fixture
def ingest():
    spec = importlib.util.spec_from_file_location("draft_update_ingest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extraction(specs):
    return {"vessels": {"Rig": {"aliases": ["Former Rig"], "specs": specs}}}


@pytest.mark.parametrize("destination", ["raw", "curated"])
def test_draft_update_clears_missing_condition(ingest, monkeypatch, destination):
    store = Mock()
    store.load.return_value = [
        {"VESSEL_NAME": "Former Rig", "DRAFT_M": 6.7, "RAW_DRAFT_LOAD_LINE_FT": 21.9}
    ]
    monkeypatch.setattr(ingest, "ParquetStore", Mock(return_value=store))
    update = extraction({"DRAFT_M": 6.1})

    if destination == "raw":
        assert ingest.write_raw_source(update, Path("."), {}, "sample") == 1
    else:
        assert ingest.apply_to_curated(update, Path("."), {}) == 1

    [record] = store.save.call_args.args[0]
    assert record["DRAFT_M"] == 6.1
    assert record["RAW_DRAFT_LOAD_LINE_FT"] is None


@pytest.mark.parametrize("name", ["Rig", " former rig "])
@pytest.mark.parametrize(
    "specs, expected",
    [
        ({"DRAFT_M": 6.1}, None),
        ({"DRAFT_M": 6.1, "RAW_DRAFT_LOAD_LINE_FT": None}, None),
        ({"DRAFT_M": 6.1, "RAW_DRAFT_LOAD_LINE_FT": 20.0}, 20.0),
    ],
)
def test_curated_draft_replaces_condition(ingest, tmp_path, name, specs, expected):
    store = ingest.ParquetStore(base_dir=tmp_path / "curated")
    store.save(
        [{"VESSEL_NAME": name, "DRAFT_M": 6.7, "RAW_DRAFT_LOAD_LINE_FT": 21.9}],
        "drilling_rigs.parquet",
    )

    assert ingest.apply_to_curated(extraction(specs), tmp_path, {}) == 1

    [record] = store.load("drilling_rigs.parquet")
    assert record["DRAFT_M"] == 6.1
    assert record["RAW_DRAFT_LOAD_LINE_FT"] == expected
    with (tmp_path / "curated/drilling_rigs.csv").open(newline="") as handle:
        [exported] = csv.DictReader(handle)
    assert exported["DRAFT_M"] == "6.1"
    assert exported["RAW_DRAFT_LOAD_LINE_FT"] == (
        "" if expected is None else str(expected)
    )


def test_unrelated_update_preserves_draft_pair(ingest, tmp_path):
    store = ingest.ParquetStore(base_dir=tmp_path / "curated")
    original = [
        {"VESSEL_NAME": "Rig", "DRAFT_M": 6.7, "RAW_DRAFT_LOAD_LINE_FT": 21.9},
        {"VESSEL_NAME": "Other Rig", "DRAFT_M": 7.3, "RAW_DRAFT_LOAD_LINE_FT": 24.0},
    ]
    store.save(original, "drilling_rigs.parquet")

    assert ingest.apply_to_curated(extraction({"BEAM_M": 35.0}), tmp_path, {}) == 1

    records = store.load("drilling_rigs.parquet")
    assert records[0]["BEAM_M"] == 35.0
    for before, after in zip(original, records):
        for field in ("VESSEL_NAME", "DRAFT_M", "RAW_DRAFT_LOAD_LINE_FT"):
            assert after[field] == before[field]


@pytest.mark.parametrize(
    "specs, expected",
    [
        ({"DRAFT_M": 6.1}, None),
        ({"DRAFT_M": 6.1, "RAW_DRAFT_LOAD_LINE_FT": None}, None),
        ({"DRAFT_M": 6.1, "RAW_DRAFT_LOAD_LINE_FT": 20.0}, 20.0),
    ],
)
def test_raw_draft_writes_explicit_condition(ingest, tmp_path, specs, expected):
    assert ingest.write_raw_source(extraction(specs), tmp_path, {}, "sample") == 1

    store = ingest.ParquetStore(base_dir=tmp_path / "raw/spec_pdf_dimensions")
    [record] = store.load("sample.parquet")
    assert record["DRAFT_M"] == 6.1
    assert record["RAW_DRAFT_LOAD_LINE_FT"] == expected
