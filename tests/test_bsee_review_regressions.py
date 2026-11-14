"""Regression tests for PR 1985's second-provider review."""

import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path, PureWindowsPath

import pandas as pd
import pytest

from scripts import generate_catalog as catalog_module
from scripts.generate_catalog import generate_catalog
from scripts.ingest import bsee_binary_formats as formats
from scripts.ingest.bsee_binary_ingest import ingest
from tests.bsee_ingest_support import entries, workspace, write_zip

__all__ = ["workspace"]  # Re-export the shared pytest fixture.


def test_catalog_generator_loads_by_file_location_in_fresh_interpreter(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/generate_catalog.py"
    probe = """
import importlib.util
from pathlib import Path
import sys

before = sys.path.copy()
spec = importlib.util.spec_from_file_location("catalog_generator", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.generate_catalog)
assert sys.path == before
helper = Path(module.preserve_ingest_entries.__code__.co_filename).resolve()
assert helper == Path(sys.argv[1]).parent / "ingest/bsee_ingest_manifest.py"
"""
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("inside", [False, True])
def test_catalog_paths_use_forward_slashes(inside):
    path = PureWindowsPath("project/data/modules/bsee/war/table.csv")
    root = PureWindowsPath("project" if inside else "other")
    expected = "data/modules/bsee/war/table.csv"
    assert catalog_module._rel_path(path, root) == (
        expected if inside else "project/" + expected
    )


@pytest.mark.parametrize("invalid", [b"\xc3", b"\xef\xbb\xbf\xc3"])
def test_utf8_truncated_only_input_is_not_reported_as_empty(invalid):
    with pytest.raises(UnicodeDecodeError):
        list(formats.text_chunks(io.BytesIO(invalid), "t", 1, "utf-8"))


@pytest.mark.parametrize("body", [b"", b"\xef\xbb\xbf"])
def test_empty_decoded_input_retains_empty_diagnostic(body):
    with pytest.raises(ValueError, match="^Empty input$"):
        list(formats.text_chunks(io.BytesIO(body), "t", 1, "utf-8"))


@pytest.mark.parametrize("bom", [False, True])
def test_utf8_sniff_boundary_preserves_multibyte_value(bom):
    prefix = (b"\xef\xbb\xbf" if bom else b"") + b"ID,REMARK\n01,"
    body = prefix + b"a" * (8191 - len(prefix)) + "é\n".encode()
    encoding = "latin-1" if bom else "utf-8"
    chunks = list(formats.text_chunks(io.BytesIO(body), "table", 1, encoding))
    assert chunks[0].iloc[0]["ID"] == "01"
    assert chunks[0].iloc[0]["REMARK"] == "a" * (8191 - len(prefix)) + "é"


@pytest.mark.parametrize("invalid", [b"\xff", b"\xc3"])
def test_utf8_invalid_bytes_still_fail_after_sniffing(invalid):
    body = b"ID,REMARK\n01," + b"a" * 8192 + invalid
    with pytest.raises(UnicodeDecodeError):
        list(formats.text_chunks(io.BytesIO(body), "t", 1, "utf-8"))


@pytest.mark.parametrize("outputs_present", [False, True])
def test_ingest_provenance_survives_catalog_regeneration(
    workspace, tmp_path, outputs_present
):
    source, project, current = workspace
    write_zip(source, "bin/war/raw.zip", {"table.txt": "ID,REMARK\n01,old snapshot\n"})
    records = ingest(source, project, current, ["war"], date(2026, 11, 13))
    record = records[0]
    target = project / record["path"]
    measured_size = target.stat().st_size
    if not outputs_present:
        target.unlink()
    for _ in range(2):
        catalog = generate_catalog(
            project, module_filter="bsee", output_root=tmp_path / "generated"
        )
        datasets = catalog["modules"]["bsee"]["datasets"]
        assert len(datasets) == 1  # The manifest itself is not a dataset.
        actual = datasets[0]
        for field in (
            "source_sha256",
            "sha256",
            "row_count",
            "deduplication",
            "source_vintage",
        ):
            assert actual[field] == record[field]
        assert actual["local_only"] is True
        assert actual["availability"] == ("present" if outputs_present else "missing")
        assert actual["measured_size_bytes"] == measured_size
        assert actual["size_bytes"] == (measured_size if outputs_present else 0)
        assert catalog["total_size_bytes"] == actual["size_bytes"]
    manifest = project / "data/modules/bsee/war/ingest_manifest.json"
    assert (
        json.loads(manifest.read_text(encoding="utf-8"))["datasets"][0]["source_sha256"]
        == record["source_sha256"]
    )


def test_manifest_upserts_dates_without_losing_previous_snapshots(workspace):
    source, project, current = workspace
    write_zip(source, "bin/war/raw.zip", {"table.txt": "ID\n01\n"})
    for day in (12, 13, 13):
        ingest(source, project, current, ["war"], date(2026, 11, day))
    catalog = generate_catalog(project, module_filter="bsee", dry_run=True)
    actual = catalog["modules"]["bsee"]["datasets"]
    assert len(actual) == 2
    assert all(r.get("source_sha256") for r in actual)


@pytest.mark.parametrize("windows_paths", [False, True])
def test_manifest_overlay_counts_present_export_once(
    workspace, monkeypatch, windows_paths
):
    source, project, current = workspace
    write_zip(source, "bin/war/raw.zip", {"table.txt": "ID\n01\n"})
    record = ingest(source, project, current, ["war"], date(2026, 11, 13))[0]
    scan_module = catalog_module.scan_module

    def scan_with_platform_paths(*args, **kwargs):
        schema = scan_module(*args, **kwargs)
        if windows_paths:
            for entry in schema["datasets"]:
                entry["path"] = str(PureWindowsPath(entry["path"]))
        return schema

    monkeypatch.setattr(catalog_module, "scan_module", scan_with_platform_paths)
    catalog = generate_catalog(project, module_filter="bsee", dry_run=True)
    datasets = catalog["modules"]["bsee"]["datasets"]
    assert len(datasets) == 1
    assert datasets[0]["path"] == record["path"]
    assert datasets[0]["source_sha256"] == record["source_sha256"]
    assert datasets[0]["availability"] == "present"
    assert catalog["total_size_bytes"] == record["measured_size_bytes"]


def test_committed_manifests_retain_all_recorded_exports_without_payloads(workspace):
    _, project, _ = workspace
    root = Path(__file__).resolve().parents[1]
    for manifest in (root / "data/modules/bsee").glob("*/ingest_manifest.json"):
        target = project / manifest.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(manifest.read_bytes())
    catalog = generate_catalog(project, module_filter="bsee", dry_run=True)
    records = catalog["modules"]["bsee"]["datasets"]
    assert len(records) == 13
    assert sum(r["row_count"] for r in records) == 11948059
    assert sum(r["measured_size_bytes"] for r in records) == 2017902020
    assert all(r["availability"] == "missing" and r["local_only"] for r in records)
    assert catalog["total_size_bytes"] == 0


def test_manifest_serialization_failure_preserves_prior_run(workspace, monkeypatch):
    from scripts.ingest import bsee_ingest_manifest

    source, project, current = workspace
    raw = write_zip(source, "bin/war/raw.zip", {"table.txt": "ID\n01\n"})
    record = ingest(source, project, current, ["war"], date(2026, 11, 13))[0]
    paths = [
        project / record["path"],
        project / "data/catalog.yaml",
        project / "data/modules/bsee/war/ingest_manifest.json",
    ]
    before = [p.read_bytes() for p in paths]
    raw.unlink()
    write_zip(source, "bin/war/raw.zip", {"table.txt": "ID\n02\n"})

    def fail_dump(*args, **kwargs):
        raise RuntimeError("manifest serialization failed")

    with monkeypatch.context() as patcher:
        patcher.setattr(bsee_ingest_manifest.json, "dumps", fail_dump)
        with pytest.raises(RuntimeError, match="manifest serialization failed"):
            ingest(source, project, current, ["war"], date(2026, 11, 13))
    assert [p.read_bytes() for p in paths] == before


def test_changed_export_cannot_reuse_stale_manifest_provenance(workspace):
    source, project, current = workspace
    write_zip(source, "bin/war/raw.zip", {"table.txt": "ID\n01\n"})
    record = ingest(source, project, current, ["war"], date(2026, 11, 13))[0]
    (project / record["path"]).write_bytes(b"ID\n02\n")
    before = (project / "data/catalog.yaml").read_bytes()
    with pytest.raises(ValueError, match="Ingest output differs from manifest"):
        generate_catalog(project, module_filter="bsee")
    assert (project / "data/catalog.yaml").read_bytes() == before


def test_numeric_text_overlap_is_reported_as_exact_text_only(workspace):
    source, project, current = workspace
    pd.DataFrame(
        [["001", "0.0", "-8e-06"]], columns=["API_WELL_NUMBER", "MD", "DX"]
    ).to_csv(current / "points.csv", index=False)
    write_zip(
        source,
        "bin/war/raw.zip",
        {"points.txt": "API_WELL_NUMBER,MD,DX\n001,0,-.000008\n"},
    )
    ingest(source, project, current, ["war"], date(2026, 11, 13))
    record = entries(project)[0]
    assert record["row_count"] == 1
    assert record["duplicate_rows"] == 0
    assert record["deduplication"]["status"] == "exact_text_only"


@pytest.mark.parametrize("matching_newlines", [False, True])
def test_multiline_fixture_preserves_values_with_windows_newlines(
    workspace, matching_newlines
):
    """Deduplicate equal CRLF values while retaining different embedded LF."""
    source, project, current = workspace
    body = 'SN_WAR,TEXT_REMARK\n01,"He said ""NA, Inc"".\nSecond line"\n'
    current_bytes = body.replace("\n", "\r\n").encode("utf-8")
    current_file = current / "remarks.csv"
    current_file.write_bytes(current_bytes)
    raw = current_bytes if matching_newlines else body.encode("utf-8")
    write_zip(source, "bin/war/raw.zip", {"mv_war_main.txt": raw})
    record = ingest(source, project, current, ["war"], date(2026, 11, 13))[0]
    assert current_file.read_bytes() == current_bytes
    assert record["source_row_count"] == 1
    assert record["duplicate_rows"] == (1 if matching_newlines else 0)
    assert record["row_count"] == (0 if matching_newlines else 1)
    compared = record["deduplication"]["compared_sources"]
    assert compared[0]["sha256"] == hashlib.sha256(current_bytes).hexdigest()
