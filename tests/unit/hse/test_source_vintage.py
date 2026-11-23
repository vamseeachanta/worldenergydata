# ABOUTME: Tests for the HSE source-vintage helper + contract stamp (#489).
# ABOUTME: Guards that the contract proves freshness from the dataset field, not mtime.

"""Tests for corpus_vintage() and scripts/hse/stamp_source_vintage.py (#489)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from worldenergydata.hse.grounding import corpus_vintage

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures" / "bsee_incinv_sample.txt"
CONTRACT = REPO_ROOT / "data" / "source-refresh-acceptance-contract.json"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "hse"))
from stamp_source_vintage import stamp  # noqa: E402


def test_corpus_vintage_is_max_date_from_dataset_field():
    # newest DATE_OCCURRED in the fixture is 2026-01-08
    assert corpus_vintage(FIXTURE) == "2026-01-08"


def test_corpus_vintage_none_when_unavailable(tmp_path):
    assert corpus_vintage(tmp_path / "missing.txt") is None


def test_committed_contract_hse_row_has_proven_vintage():
    """Regression guard: the HSE row must prove freshness from the dataset
    field, never a prohibited metadata basis (#489)."""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    hse = next(r for r in contract["sources"] if r["module_id"] == "hse")
    assert hse["source_data_latest_date_basis"] == "dataset_field"
    assert hse["source_data_latest_date"] is not None
    prohibited = set(contract["prohibited_source_data_latest_date_basis_values"])
    assert hse["source_data_latest_date_basis"] not in prohibited


def test_stamp_is_format_preserving_and_surgical(tmp_path):
    # two compact rows; only the hse row may change
    other = '{"module_id":"bsee","source_data_latest_date":null,"x":1}'
    hse = (
        '{"module_id":"hse","source_data_latest_date":null,'
        '"source_data_latest_date_basis":"unknown",'
        '"source_data_latest_date_unknown_reason":"not inspected"}'
    )
    raw = '{"sources":[' + other + "," + hse + "]}\n"
    p = tmp_path / "contract.json"
    p.write_text(raw, encoding="utf-8")

    result = stamp(p, vintage="2026-01-08", write=True)
    assert result["changed"] is True

    out = p.read_text(encoding="utf-8")
    assert other in out  # the bsee row is byte-for-byte untouched
    new = json.loads(out)
    hse_row = next(r for r in new["sources"] if r["module_id"] == "hse")
    assert hse_row["source_data_latest_date"] == "2026-01-08"
    assert hse_row["source_data_latest_date_basis"] == "dataset_field"
    assert hse_row["source_data_latest_date_unknown_reason"] == ""


def test_stamp_check_mode_does_not_write(tmp_path):
    hse = (
        '{"module_id":"hse","source_data_latest_date":null,'
        '"source_data_latest_date_basis":"unknown"}'
    )
    raw = '{"sources":[' + hse + "]}\n"
    p = tmp_path / "contract.json"
    p.write_text(raw, encoding="utf-8")
    stamp(p, vintage="2026-01-08", write=False)
    assert p.read_text(encoding="utf-8") == raw  # unchanged
