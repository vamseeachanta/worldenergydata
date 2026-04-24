from pathlib import Path


REPORT = Path(__file__).resolve().parents[3] / "docs" / "ci" / "flake8-inventory-2026-04-23.md"


def test_flake8_inventory_report_records_provenance_and_decomposition():
    text = REPORT.read_text(encoding="utf-8")

    assert "Command: `uv run flake8 src/ --max-line-length=100 --extend-ignore=E203,W503 --exclude=__pycache__,*.egg-info,.git,.venv`" in text
    assert "Exit code: `1` (expected before remediation)" in text
    assert "Total parsed findings: `4752`" in text
    assert "Unique files with findings: `280`" in text
    assert "`src/worldenergydata/marine_safety/_cross_database_data.py` with `4060` findings" in text
    assert "`workspace-hub#2467`" in text
    assert "`workspace-hub#2468`" in text
    assert "Final closure remains owned by #2469" in text


def test_flake8_inventory_report_preserves_transient_draft_evidence_warning():
    text = REPORT.read_text(encoding="utf-8")

    assert "`/tmp/2452-flake8.txt` was transient draft evidence only" in text
    assert "not a durable artifact" in text
