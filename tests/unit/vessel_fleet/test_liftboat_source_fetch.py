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
        ),
        encoding="utf-8",
        newline="\n",
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
    receipt_path = output / "report.pdf.receipt.json"
    original_receipt = receipt_path.read_bytes()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["sha256"] == hashlib.sha256(payload).hexdigest()
    assert receipt["http_status"] == 200
    assert receipt["url"] == "https://example.org/report.pdf"
    assert receipt["retrieved_at"]
    with patch("worldenergydata.vessel_fleet.source_fetch.subprocess.run") as run:
        assert fetch_sources(output, path) == ["report"]
        run.assert_not_called()
    assert receipt_path.read_bytes() == original_receipt


def test_receipt_write_failure_cannot_resume_as_complete(manifest, tmp_path):
    path, payload = manifest
    output = tmp_path / "raw"
    with (
        patch(
            "worldenergydata.vessel_fleet.source_fetch.subprocess.run",
            side_effect=fake_download(payload),
        ),
        patch.object(Path, "write_text", side_effect=OSError("receipt write failed")),
    ):
        with pytest.raises(OSError, match="receipt write failed"):
            fetch_sources(output, path)
    assert (output / "report.pdf").read_bytes() == payload
    assert not (output / "report.pdf.receipt.json").exists()
    with patch("worldenergydata.vessel_fleet.source_fetch.subprocess.run") as run:
        with pytest.raises(ValueError, match="receipt"):
            fetch_sources(output, path)
        run.assert_not_called()
    assert (output / "report.pdf").read_bytes() == payload
    assert not (output / "report.pdf.receipt.json").exists()


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        "{}",
        '{"retrieved_at": "2026-10-01T12:00:00Z"}',
    ],
)
def test_existing_invalid_receipt_is_rejected_without_overwrite(
    manifest, tmp_path, content
):
    path, payload = manifest
    output = tmp_path / "raw"
    output.mkdir()
    (output / "report.pdf").write_bytes(payload)
    receipt = output / "report.pdf.receipt.json"
    receipt.write_text(content, encoding="utf-8", newline="\n")
    with patch("worldenergydata.vessel_fleet.source_fetch.subprocess.run") as run:
        with pytest.raises(ValueError, match="receipt"):
            fetch_sources(output, path)
        run.assert_not_called()
    assert receipt.read_text(encoding="utf-8") == content
    assert (output / "report.pdf").read_bytes() == payload


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "https://example.org/other.pdf"),
        ("http_status", 404),
        ("sha256", "0" * 64),
        ("size_bytes", 0),
        ("retrieved_at", None),
        ("retrieved_at", "not a timestamp"),
        ("retrieved_at", "2026-10-01T12:00:00"),
    ],
)
def test_receipt_metadata_must_match_source(manifest, tmp_path, field, value):
    path, payload = manifest
    output = tmp_path / "raw"
    with patch(
        "worldenergydata.vessel_fleet.source_fetch.subprocess.run",
        side_effect=fake_download(payload),
    ):
        fetch_sources(output, path)
    receipt_path = output / "report.pdf.receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt[field] = value
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8", newline="\n")
    original = receipt_path.read_bytes()
    with patch("worldenergydata.vessel_fleet.source_fetch.subprocess.run") as run:
        with pytest.raises(ValueError, match="receipt"):
            fetch_sources(output, path)
        run.assert_not_called()
    assert receipt_path.read_bytes() == original
    assert (output / "report.pdf").read_bytes() == payload


@pytest.mark.parametrize(
    "content", [None, b"not json\n", b""], ids=["valid", "invalid", "empty"]
)
def test_orphaned_receipt_preserved_without_download(manifest, tmp_path, content):
    path, payload = manifest
    output = tmp_path / "raw"
    output.mkdir()
    receipt_path = output / "report.pdf.receipt.json"
    if content is None:
        content = json.dumps(
            {
                "url": "https://example.org/report.pdf",
                "http_status": 200,
                "retrieved_at": "2026-10-01T12:00:00Z",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        ).encode("utf-8")
    receipt_path.write_bytes(content)
    with patch(
        "worldenergydata.vessel_fleet.source_fetch.subprocess.run",
        side_effect=fake_download(payload),
    ) as run:
        with pytest.raises(FileExistsError, match="receipt"):
            fetch_sources(output, path)
        run.assert_not_called()
    assert receipt_path.read_bytes() == content
    assert not (output / "report.pdf").exists()
    assert not (output / "report.pdf.part").exists()


def test_orphaned_receipt_directory_preserved_without_download(manifest, tmp_path):
    path, payload = manifest
    output = tmp_path / "raw"
    receipt_path = output / "report.pdf.receipt.json"
    receipt_path.mkdir(parents=True)
    retained = receipt_path / "retained.json"
    retained.write_bytes(b"retained evidence\n")
    with patch(
        "worldenergydata.vessel_fleet.source_fetch.subprocess.run",
        side_effect=fake_download(payload),
    ) as run:
        with pytest.raises(FileExistsError, match="receipt"):
            fetch_sources(output, path)
        run.assert_not_called()
    assert receipt_path.is_dir()
    assert retained.read_bytes() == b"retained evidence\n"
    assert not (output / "report.pdf").exists()
    assert not (output / "report.pdf.part").exists()


def test_orphaned_receipt_link_preserved_without_download(manifest, tmp_path):
    path, payload = manifest
    output = tmp_path / "raw"
    output.mkdir()
    receipt_path = output / "report.pdf.receipt.json"
    receipt_path.symlink_to("missing-receipt.json")
    with patch(
        "worldenergydata.vessel_fleet.source_fetch.subprocess.run",
        side_effect=fake_download(payload),
    ) as run:
        with pytest.raises(FileExistsError, match="receipt"):
            fetch_sources(output, path)
        run.assert_not_called()
    assert receipt_path.is_symlink()
    assert receipt_path.readlink().as_posix() == "missing-receipt.json"
    assert not (output / "missing-receipt.json").exists()
    assert not (output / "report.pdf").exists()
    assert not (output / "report.pdf.part").exists()


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
    data = json.loads(path.read_text(encoding="utf-8"))
    data["sources"]["report"]["raw_file"] = name
    path.write_text(json.dumps(data), encoding="utf-8", newline="\n")
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
