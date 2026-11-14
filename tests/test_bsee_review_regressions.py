"""Regression tests for PR 1985's second-provider review."""

import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.generate_catalog import generate_catalog
from scripts.ingest import bsee_binary_formats as formats
from scripts.ingest.bsee_binary_ingest import ingest
from tests.bsee_ingest_support import entries, workspace, write_zip

__all__ = ["workspace"]  # Re-export the shared pytest fixture.


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
        json.loads(manifest.read_text())["datasets"][0]["source_sha256"]
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


def test_multiline_fixture_preserves_values_with_windows_newlines(
    workspace, monkeypatch
):
    """Exercise the existing integration test with Windows text translation."""
    from tests.test_bsee_binary_ingest import (
        test_quoted_multiline_current_values_with_escaped_quotes_match_exactly,
    )

    write_text = Path.write_text

    def windows_write_text(path, data, *args, **kwargs):
        if kwargs.get("newline") is None:
            data = data.replace("\n", "\r\n")
            kwargs["newline"] = ""
        return write_text(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", windows_write_text)
    test_quoted_multiline_current_values_with_escaped_quotes_match_exactly(workspace)
