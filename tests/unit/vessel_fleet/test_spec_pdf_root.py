"""External source-PDF routing and repo-lean acceptance for issue #1151."""

import hashlib
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = (
    REPO_ROOT
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/_data"
)
SCRIPT = REPO_ROOT / "scripts/vessel_fleet/ingest_contractor_spec_pdfs.py"


@pytest.fixture
def ingest():
    spec = importlib.util.spec_from_file_location("spec_pdf_ingest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_env_root_wins(monkeypatch, tmp_path):
    from worldenergydata.vessel_fleet.spec_pdf_root import resolve_spec_pdf_root

    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path))
    assert resolve_spec_pdf_root() == tmp_path


def test_default_root(monkeypatch):
    from worldenergydata.vessel_fleet.spec_pdf_root import resolve_spec_pdf_root

    monkeypatch.delenv("WORLDENERGYDATA_SPEC_PDF_ROOT", raising=False)
    assert resolve_spec_pdf_root() == Path(
        "/mnt/ace/worldenergydata/data/modules/vessel_fleet/raw/spec_pdfs"
    )


def test_reparse_missing_root(ingest, monkeypatch, tmp_path):
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path / "absent"))
    with pytest.raises(
        ingest.SpecPdfUnavailableError, match="WORLDENERGYDATA_SPEC_PDF_ROOT"
    ):
        ingest.reparse_report(
            {
                "vessels": {
                    "Rig": {"extraction": "text_parse", "pdf": "rig.pdf", "specs": {}}
                }
            },
            DATA_DIR,
            "noble",
        )


def test_reparse_missing_file(ingest, monkeypatch, tmp_path):
    (tmp_path / "noble").mkdir()
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path))
    extraction = {
        "vessels": {"Rig": {"extraction": "text_parse", "pdf": "missing.pdf"}}
    }
    with pytest.raises(
        ingest.SpecPdfUnavailableError,
        match="missing.pdf.*WORLDENERGYDATA_SPEC_PDF_ROOT",
    ):
        ingest.reparse_report(extraction, DATA_DIR, "noble")


def test_reparse_reads_external_pdf(ingest, monkeypatch, tmp_path):
    pdf, data_dir, _ = _verified_fixture(tmp_path)
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path))

    calls = []

    def extract_text(path):
        calls.append(path)
        assert path == pdf
        return "Year Built /          2013\n"

    monkeypatch.setattr(ingest, "_extract_text", extract_text)
    extraction = {
        "vessels": {
            "Rig": {
                "extraction": "text_parse",
                "pdf": "rig.pdf",
                "specs": {"YEAR_BUILT": 2013},
            }
        }
    }
    assert ingest.reparse_report(extraction, data_dir, "noble") == 0
    assert calls == [pdf]


@pytest.mark.parametrize("script_name", [SCRIPT.name, "ingest_noble_spec_pdfs.py"])
def test_cli_missing_root(script_name, monkeypatch, tmp_path):
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path / "absent"))
    result = subprocess.run(
        [sys.executable, str(SCRIPT.with_name(script_name)), "--reparse"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3
    assert "WORLDENERGYDATA_SPEC_PDF_ROOT" in result.stderr
    assert "Traceback" not in result.stderr


def test_yaml_inputs_do_not_depend_on_pdf_root(ingest, monkeypatch, tmp_path):
    pdf_root = tmp_path / "external_pdfs"
    output_dir = tmp_path / "repo_data"
    (pdf_root / "noble").mkdir(parents=True)
    decoy = pdf_root / "noble/extracted_specs.yaml"
    decoy.write_text("vessels: {}\n")
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(pdf_root))
    extraction = ingest.load_extraction(DATA_DIR, "noble")
    urls = ingest.load_manifest_urls(DATA_DIR, "noble")
    assert "Noble Valiant" in extraction["vessels"]
    assert urls["noble-valiant.pdf"].startswith("https://")
    assert ingest.write_raw_source(extraction, output_dir, urls, "noble") > 0
    assert (output_dir / "raw/spec_pdf_dimensions/noble.parquet").is_file()
    assert not (pdf_root / "raw").exists()
    assert decoy.read_text() == "vessels: {}\n"


def test_manifest_entries_have_source_and_digest():
    manifests = sorted((DATA_DIR / "raw/spec_pdfs").glob("*/manifest.yaml"))
    assert len(manifests) >= 11
    for manifest in manifests:
        entries = yaml.safe_load(manifest.read_text())["files"]
        for filename, entry in entries.items():
            assert entry["url"].startswith("https://"), (manifest, filename)
            assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), (manifest, filename)
            local_pdf = manifest.parent / filename
            if local_pdf.is_file():
                assert (
                    hashlib.sha256(local_pdf.read_bytes()).hexdigest()
                    == entry["sha256"]
                )


def test_new_source_pdfs_are_ignored():
    candidate = DATA_DIR / "raw/spec_pdfs/noble/new-spec-sheet.pdf"
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", str(candidate)],
        cwd=REPO_ROOT,
        env={
            key: value
            for key, value in os.environ.items()
            if key
            not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "Source PDFs must not be re-added to git"


def test_reparse_checks_present_files_before_reporting_missing(
    ingest, monkeypatch, tmp_path
):
    pdf, data_dir, _ = _verified_fixture(tmp_path)
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path))
    calls = []

    def extract_text(path):
        calls.append(path)
        return "Year Built /          2013\n"

    monkeypatch.setattr(ingest, "_extract_text", extract_text)
    extraction = {
        "vessels": {
            "Missing": {"extraction": "text_parse", "pdf": "missing.pdf", "specs": {}},
            "Present": {"extraction": "text_parse", "pdf": "rig.pdf", "specs": {}},
        }
    }
    with pytest.raises(ingest.SpecPdfUnavailableError, match="missing.pdf"):
        ingest.reparse_report(extraction, data_dir, "noble")
    assert calls == [pdf]


def test_empty_env_uses_default(monkeypatch):
    from worldenergydata.vessel_fleet.spec_pdf_root import resolve_spec_pdf_root

    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", "")
    assert resolve_spec_pdf_root() == Path(
        "/mnt/ace/worldenergydata/data/modules/vessel_fleet/raw/spec_pdfs"
    )


def _verified_fixture(tmp_path):
    folder = tmp_path / "noble"
    folder.mkdir()
    pdf = folder / "rig.pdf"
    pdf.write_bytes(b"synthetic PDF path fixture")
    data_dir = tmp_path / "repo_data"
    manifest_dir = data_dir / "raw/spec_pdfs/noble"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "files": {
                    "rig.pdf": {"sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}
                }
            }
        )
    )
    extraction = {
        "vessels": {"Rig": {"extraction": "text_parse", "pdf": "rig.pdf", "specs": {}}}
    }
    return pdf, data_dir, extraction


def test_reparse_rejects_hash_mismatch(ingest, monkeypatch, tmp_path):
    pdf, data_dir, extraction = _verified_fixture(tmp_path)
    pdf.write_bytes(b"tampered synthetic bytes")
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path))
    calls = []
    monkeypatch.setattr(ingest, "_extract_text", lambda path: calls.append(path) or "")
    with pytest.raises(
        ingest.SpecPdfUnavailableError, match="sha256.*WORLDENERGYDATA_SPEC_PDF_ROOT"
    ):
        ingest.reparse_report(extraction, data_dir, "noble")
    assert not calls


def test_cli_extraction_failure_is_not_drift(ingest, monkeypatch, tmp_path, caplog):
    _, data_dir, extraction = _verified_fixture(tmp_path)
    (data_dir / "raw/spec_pdfs/noble/extracted_specs.yaml").write_text(
        yaml.safe_dump(extraction)
    )
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path))
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), "--reparse", "--data-dir", str(data_dir)]
    )

    def extraction_error(path):
        raise subprocess.CalledProcessError(1, "pdftotext")

    monkeypatch.setattr(ingest, "_extract_text", extraction_error)
    assert ingest.main() == 4
    assert "failed" in caplog.text.lower()


def test_cli_unknown_contractor_is_not_drift(monkeypatch):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--reparse", "--contractor", "absent-contractor"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "FileNotFoundError" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_hash_mismatch_is_incomplete(ingest, monkeypatch, tmp_path):
    pdf, data_dir, extraction = _verified_fixture(tmp_path)
    pdf.write_bytes(b"tampered synthetic bytes")
    (data_dir / "raw/spec_pdfs/noble/extracted_specs.yaml").write_text(
        yaml.safe_dump(extraction)
    )
    monkeypatch.setenv("WORLDENERGYDATA_SPEC_PDF_ROOT", str(tmp_path))
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), "--reparse", "--data-dir", str(data_dir)]
    )
    assert ingest.main() == 3
