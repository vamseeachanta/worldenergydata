"""Manifest INCINV reader boundaries using independent synthetic truth tables."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def drilling_cli():
    script = (
        Path(__file__).resolve().parents[3]
        / "scripts/exploration/drilling_hse_patterns_analysis.py"
    )
    spec = importlib.util.spec_from_file_location(
        "drilling_hse_patterns_analysis_under_test", script
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def incinv_loader(drilling_cli):
    # Exercise the manifest reader used by the current CLI, not its retired
    # INCINV_CANDIDATES / _load_incinv interface.
    return drilling_cli.workflow()


def seal_sources(directory, paths):
    manifest = {
        "source_kind": "synthetic",
        "files": [
            {
                "file": path.name,
                "url": "https://www.data.bsee.gov/Other/Files/IncInvRawData.zip",
                "downloaded_at": "2026-10-01T00:00:00Z",
                "size_bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in paths
        ],
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


@pytest.fixture
def csv_sources(tmp_path):
    header = (
        b"DATE_OCCURRED,MILITARY_TIME,AREA_BLOCK,ACCIDENT_TYPE,LEASE_NUMBER,"
        b"PANEL_DISTRICT,STATUS,DESCRIPTION,NOTE\r\n"
    )
    primary = tmp_path / "primary.csv"
    # ISO-8859-1 maps byte E9 to U+00E9; build the non-ASCII byte explicitly.
    primary.write_bytes(
        header
        + b'01/02/2020, 1200 , AA 1 , DRILL , L1 , D1 , closed ,"  caf'
        + bytes([0xE9])
        + b', sample  ", keep  inner  spaces \r\n'
        + b"01/03/2020,1400,AA 2,DRILL,L3,D1,closed,plain text,   \r\n"
    )
    fallback = tmp_path / "fallback.csv"
    fallback.write_bytes(
        header + b"02/03/2021,1300,BB 2,DRILL,L2,D2,closed,synthetic fallback,   \r\n"
    )
    # Independent truth tables preserve quoted commas and inner spaces;
    # cell boundaries are stripped, including whitespace-only cells.
    expected = {
        primary: [
            {
                "DATE_OCCURRED": "01/02/2020",
                "MILITARY_TIME": "1200",
                "AREA_BLOCK": "AA 1",
                "ACCIDENT_TYPE": "DRILL",
                "LEASE_NUMBER": "L1",
                "PANEL_DISTRICT": "D1",
                "STATUS": "closed",
                "DESCRIPTION": "café, sample",
                "NOTE": "keep  inner  spaces",
            },
            {
                "DATE_OCCURRED": "01/03/2020",
                "MILITARY_TIME": "1400",
                "AREA_BLOCK": "AA 2",
                "ACCIDENT_TYPE": "DRILL",
                "LEASE_NUMBER": "L3",
                "PANEL_DISTRICT": "D1",
                "STATUS": "closed",
                "DESCRIPTION": "plain text",
                "NOTE": "",
            },
        ],
        fallback: [
            {
                "DATE_OCCURRED": "02/03/2021",
                "MILITARY_TIME": "1300",
                "AREA_BLOCK": "BB 2",
                "ACCIDENT_TYPE": "DRILL",
                "LEASE_NUMBER": "L2",
                "PANEL_DISTRICT": "D2",
                "STATUS": "closed",
                "DESCRIPTION": "synthetic fallback",
                "NOTE": "",
            }
        ],
    }
    config = {
        "data_dir": str(tmp_path),
        "source_kind": "synthetic",
        "source_file": primary.name,
        "encoding": "latin-1",
        "quantity": "investigation records",
        "unit": "count",
        "earliest_date": "1900-01-01",
        "latest_date": "2026-10-01",
    }
    return config, primary, fallback, expected


@pytest.mark.parametrize("selected", ["primary", "fallback"])
def test_load_incinv_selects_configured_manifest_source(
    incinv_loader, csv_sources, selected
):
    config, primary, fallback, expected = csv_sources
    source = primary if selected == "primary" else fallback
    config["source_file"] = source.name
    # Reverse manifest order: source_file, rather than first eligible file,
    # determines which independently sealed CSV is read.
    manifest = seal_sources(primary.parent, [fallback, primary])

    rows, actual_manifest = incinv_loader._qualify(config, {})

    assert actual_manifest == manifest
    assert rows == expected[source]


@pytest.mark.parametrize("unused_state", ["missing", "empty"])
def test_load_incinv_ignores_unconfigured_sources(
    incinv_loader, csv_sources, unused_state
):
    config, primary, fallback, expected = csv_sources
    if unused_state == "missing":
        primary.unlink()
    else:
        primary.write_bytes(b"")
    config["source_file"] = fallback.name
    seal_sources(fallback.parent, [fallback])

    rows, _ = incinv_loader._qualify(config, {})

    assert rows == expected[fallback]


@pytest.mark.parametrize(
    ("selected_state", "reason"),
    [
        ("missing", "provenance"),
        ("empty", "schema: required columns absent"),
        ("header_only", "row_count: empty source"),
        ("tampered", "integrity"),
    ],
)
def test_load_incinv_rejects_unusable_source_without_fallback(
    incinv_loader, csv_sources, selected_state, reason
):
    config, primary, fallback, _ = csv_sources
    if selected_state == "empty":
        primary.write_bytes(b"")
    elif selected_state == "header_only":
        primary.write_bytes(primary.read_bytes().splitlines(keepends=True)[0])
    seal_sources(primary.parent, [primary, fallback])
    if selected_state == "missing":
        primary.unlink()
    elif selected_state == "tampered":
        primary.write_bytes(primary.read_bytes() + b"tampered")

    with pytest.raises(incinv_loader.QAError, match=reason):
        incinv_loader._qualify(config, {})


def test_load_incinv_requires_manifest_even_with_valid_csv(incinv_loader, csv_sources):
    config, _, _, _ = csv_sources

    with pytest.raises(incinv_loader.QAError, match="provenance"):
        incinv_loader._qualify(config, {})


def test_load_incinv_rejects_whitespace_in_required_headers(incinv_loader, csv_sources):
    config, primary, _, _ = csv_sources
    primary.write_bytes(
        primary.read_bytes().replace(b"DATE_OCCURRED", b" DATE_OCCURRED ")
    )
    seal_sources(primary.parent, [primary])

    with pytest.raises(incinv_loader.QAError, match="schema: required columns absent"):
        incinv_loader._qualify(config, {})


def test_cli_workflow_preserves_registered_modules(drilling_cli):
    before = sys.modules.copy()

    reader = drilling_cli.workflow()

    assert drilling_cli.__name__ == "drilling_hse_patterns_analysis_under_test"
    assert Path(reader.__file__).name == "public_refresh.py"
    assert callable(reader._qualify)
    assert sys.modules == before
