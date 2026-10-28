"""INCINV reader boundary tests using independent, synthetic CSV truth tables."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def incinv_loader():
    # Ascend safety_analysis -> unit -> tests -> repository root.
    script = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "exploration"
        / "drilling_hse_patterns_analysis.py"
    )
    spec = importlib.util.spec_from_file_location("drilling_incinv_reader", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def csv_candidates(tmp_path):
    missing = tmp_path / "missing.csv"
    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    primary = tmp_path / "primary.csv"
    # ISO-8859-1 maps byte E9 to U+00E9 (e acute); assemble the byte at runtime.
    primary.write_bytes(
        b" RECORD , DESCRIPTION , NOTE \r\n"
        b' alpha ,"  caf' + bytes([0xE9]) + b', sample  ", keep  inner  spaces \r\n'
        b" beta , plain text ,   \r\n"
    )
    fallback = tmp_path / "fallback.csv"
    fallback.write_bytes(b"RECORD,DESCRIPTION,NOTE\nbackup,synthetic fallback,unused\n")

    # Hand-written truth tables: quoted comma stays in one cell, outer spaces
    # disappear, inner spaces remain, and a whitespace-only cell becomes empty.
    expected = {
        primary: [
            {
                "RECORD": "alpha",
                "DESCRIPTION": "café, sample",
                "NOTE": "keep  inner  spaces",
            },
            {"RECORD": "beta", "DESCRIPTION": "plain text", "NOTE": ""},
        ],
        fallback: [
            {
                "RECORD": "backup",
                "DESCRIPTION": "synthetic fallback",
                "NOTE": "unused",
            }
        ],
    }
    return missing, empty, primary, fallback, expected


@pytest.mark.parametrize("preferred", ["primary", "fallback"])
def test_load_incinv_selects_first_eligible_candidate(
    incinv_loader, csv_candidates, monkeypatch, preferred
):
    missing, empty, primary, fallback, expected = csv_candidates
    first, second = (
        (primary, fallback) if preferred == "primary" else (fallback, primary)
    )
    monkeypatch.setattr(
        incinv_loader, "INCINV_CANDIDATES", [missing, empty, first, second]
    )

    source, rows = incinv_loader._load_incinv()

    assert source == first
    assert rows == expected[first]


@pytest.mark.parametrize("preferred_state", ["missing", "empty"])
def test_load_incinv_uses_fallback_when_preferred_unusable(
    incinv_loader, csv_candidates, monkeypatch, preferred_state
):
    missing, empty, primary, fallback, expected = csv_candidates
    # Replace the preferred candidate with a distinct absent or empty path.
    preferred = primary.parent / "unusable.csv"
    if preferred_state == "empty":
        preferred.write_bytes(b"")
    monkeypatch.setattr(
        incinv_loader, "INCINV_CANDIDATES", [missing, empty, preferred, fallback]
    )

    source, rows = incinv_loader._load_incinv()

    assert source == fallback
    assert rows == expected[fallback]


@pytest.mark.parametrize("candidate_state", ["all_missing", "all_empty", "mixed"])
def test_load_incinv_rejects_unusable_candidates(
    incinv_loader, tmp_path, monkeypatch, candidate_state
):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    if candidate_state == "all_empty":
        first.write_bytes(b"")
    if candidate_state in ("all_empty", "mixed"):
        second.write_bytes(b"")
    monkeypatch.setattr(incinv_loader, "INCINV_CANDIDATES", [first, second])

    with pytest.raises(
        FileNotFoundError, match="INCINV source not found; checked:"
    ) as exc:
        incinv_loader._load_incinv()

    message = str(exc.value)
    assert "first.csv" in message
    assert "second.csv" in message
