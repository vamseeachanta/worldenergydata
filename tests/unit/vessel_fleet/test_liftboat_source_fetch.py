"""Fetch resumption and source integrity without external requests."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from worldenergydata.vessel_fleet.source_fetch import fetch_sources


@pytest.fixture
def manifest(tmp_path):
    payload = b"%PDF-1.7\nexample source\n"
    document = {
        "kind": "public_document",
        "url": "https://example.org/report.pdf",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "raw_file": "report.pdf",
    }
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {"sources": {"report": document, "seed": {"kind": "repository_seed"}}}
        )
    )
    return path, payload


def fake_download(payload, status="200"):
    def download(command, **kwargs):
        Path(command[command.index("--output") + 1]).write_bytes(payload)
        from subprocess import CompletedProcess

        return CompletedProcess(command, 0, stdout=status, stderr="")

    return download


def test_download_digest_receipt_and_resume(manifest, tmp_path):
    path, payload = manifest
    output = tmp_path / "raw"
    with patch(
        "worldenergydata.vessel_fleet.source_fetch.subprocess.run",
        side_effect=fake_download(payload),
    ) as run:
        assert fetch_sources(output, path) == ["report"]
        assert run.call_count == 1
        assert "--proto-redir" in run.call_args.args[0]
    receipt = json.loads((output / "report.pdf.receipt.json").read_text())
    assert receipt["sha256"] == hashlib.sha256(payload).hexdigest()
    assert receipt["http_status"] == 200
    assert receipt["url"] == "https://example.org/report.pdf"
    assert receipt["retrieved_at"]
    with patch("worldenergydata.vessel_fleet.source_fetch.subprocess.run") as run:
        assert fetch_sources(output, path) == ["report"]
        run.assert_not_called()


def test_existing_digest_mismatch_stops_without_overwrite(manifest, tmp_path):
    path, _ = manifest
    output = tmp_path / "raw"
    output.mkdir()
    (output / "report.pdf").write_bytes(b"different")
    with patch("worldenergydata.vessel_fleet.source_fetch.subprocess.run") as run:
        with pytest.raises(ValueError, match="digest"):
            fetch_sources(output, path)
        run.assert_not_called()
    assert (output / "report.pdf").read_bytes() == b"different"


def test_download_digest_mismatch_is_not_promoted(manifest, tmp_path):
    path, _ = manifest
    with patch(
        "worldenergydata.vessel_fleet.source_fetch.subprocess.run",
        side_effect=fake_download(b"different"),
    ):
        with pytest.raises(ValueError, match="digest"):
            fetch_sources(tmp_path / "raw", path)
    assert not (tmp_path / "raw/report.pdf").exists()
    assert (tmp_path / "raw/report.pdf.part").exists()


@pytest.mark.parametrize("name", ["../report.pdf", "folder/report.pdf", "/report.pdf"])
def test_unsafe_raw_filenames_rejected(manifest, tmp_path, name):
    path, _ = manifest
    data = json.loads(path.read_text())
    data["sources"]["report"]["raw_file"] = name
    path.write_text(json.dumps(data))
    with patch("worldenergydata.vessel_fleet.source_fetch.subprocess.run") as run:
        with pytest.raises(ValueError, match="filename"):
            fetch_sources(tmp_path / "raw", path)
        run.assert_not_called()


def test_partial_download_not_overwritten(manifest, tmp_path):
    path, _ = manifest
    output = tmp_path / "raw"
    output.mkdir()
    (output / "report.pdf.part").write_bytes(b"partial")
    with patch("worldenergydata.vessel_fleet.source_fetch.subprocess.run") as run:
        with pytest.raises(FileExistsError):
            fetch_sources(output, path)
        run.assert_not_called()


def test_unknown_or_local_source_cannot_be_downloaded(manifest, tmp_path):
    path, _ = manifest
    for identity in ("unknown", "seed"):
        with pytest.raises(ValueError, match="downloadable"):
            fetch_sources(tmp_path / "raw", path, [identity])
