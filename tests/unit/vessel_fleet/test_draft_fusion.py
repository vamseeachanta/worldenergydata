"""Synthetic draft pairs must retain one source through fusion and storage."""

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

from worldenergydata.vessel_fleet.dedup.deduplicator import _merge_records
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore


def load_script(name):
    path = Path(__file__).resolve().parents[3] / "scripts/vessel_fleet" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("source", ["bsee_war", "contractor_spec_pdf", "manual"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("condition", [{}, {"RAW_DRAFT_LOAD_LINE_FT": None}])
def test_winning_draft_clears_condition_from_other_source(source, reverse, condition):
    old = {"DATA_SOURCE": source, "DRAFT_M": 6.7, "RAW_DRAFT_LOAD_LINE_FT": 21.9}
    new = {"DATA_SOURCE": "contractor_spec_pdf", "DRAFT_M": 6.1, **condition}
    records = [new, old] if reverse else [old, new]

    merged = _merge_records(records)

    old_wins = source == "manual" or (source == "contractor_spec_pdf" and reverse)
    assert merged["DRAFT_M"] == (6.7 if old_wins else 6.1)
    assert merged["RAW_DRAFT_LOAD_LINE_FT"] == (21.9 if old_wins else None)
    assert old["RAW_DRAFT_LOAD_LINE_FT"] == 21.9
    assert new == {"DATA_SOURCE": "contractor_spec_pdf", "DRAFT_M": 6.1, **condition}


@pytest.mark.parametrize("missing_draft", [{}, {"DRAFT_M": None}])
@pytest.mark.parametrize("condition", [None, 21.9])
def test_record_without_draft_cannot_relabel_existing_pair(missing_draft, condition):
    draft = {"DATA_SOURCE": "bsee_war", "DRAFT_M": 6.1, "RAW_DRAFT_LOAD_LINE_FT": 20.0}
    unrelated = {
        "DATA_SOURCE": "manual",
        "BEAM_M": 35.0,
        "RAW_DRAFT_LOAD_LINE_FT": condition,
        **missing_draft,
    }

    merged = _merge_records([draft, unrelated])

    assert merged["DRAFT_M"] == 6.1
    assert merged["RAW_DRAFT_LOAD_LINE_FT"] == 20.0
    assert merged["BEAM_M"] == 35.0


@pytest.mark.parametrize("source", ["bsee_war", "contractor_spec_pdf"])
@pytest.mark.parametrize(
    "condition, expected",
    [
        ({}, None),
        ({"RAW_DRAFT_LOAD_LINE_FT": None}, None),
        ({"RAW_DRAFT_LOAD_LINE_FT": 20.0}, 20.0),
    ],
)
def test_raw_write_fuse_readback(tmp_path, monkeypatch, source, condition, expected):
    ingest = load_script("ingest_contractor_spec_pdfs")
    fuse = load_script("fuse_and_deduplicate")
    old = {
        "vessels": {
            "Rig": {
                "specs": {
                    "DRAFT_M": 6.7,
                    "RAW_DRAFT_LOAD_LINE_FT": 21.9,
                }
            }
        }
    }
    new = {"vessels": {"Rig": {"specs": {"DRAFT_M": 6.1, **condition}}}}
    assert ingest.write_raw_source(old, tmp_path, {}, "01-old") == 1
    assert ingest.write_raw_source(new, tmp_path, {}, "02-new") == 1
    raw = ParquetStore(tmp_path / "raw/spec_pdf_dimensions")
    [record] = raw.load("01-old.parquet")
    record["DATA_SOURCE"] = source
    raw.save([record], "01-old.parquet")
    monkeypatch.setattr(sys, "argv", ["fuse", "--data-dir", str(tmp_path)])

    assert fuse.main() == 0

    [record] = ParquetStore(tmp_path / "curated").load("drilling_rigs.parquet")
    assert record["DRAFT_M"] == 6.1
    assert record["RAW_DRAFT_LOAD_LINE_FT"] == expected
    with (tmp_path / "curated/drilling_rigs.csv").open(newline="") as handle:
        [exported] = csv.DictReader(handle)
    assert exported["DRAFT_M"] == "6.1"
    assert exported["RAW_DRAFT_LOAD_LINE_FT"] == (
        "" if expected is None else str(expected)
    )
