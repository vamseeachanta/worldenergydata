"""Check the assumptions record against the committed reconciliation evidence."""

import importlib.util
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / "config/analysis/lower_tertiary/v50_assumptions_change_log.html"
EVIDENCE = ROOT / "reports/lower_tertiary/fdas_revision_comparison.md"


class CostTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.in_table = False
        self.in_cell = False
        self.row = []

    def handle_starttag(self, tag, attrs):
        if tag == "table" and dict(attrs).get("id") == "cost-changes":
            self.in_table = True
        if self.in_table and tag == "tr":
            self.row = []
        if self.in_table and tag == "td":
            self.in_cell = True
            self.row.append("")

    def handle_data(self, data):
        if self.in_cell:
            self.row[-1] += data

    def handle_endtag(self, tag):
        if tag == "td":
            self.in_cell = False
        if tag == "tr" and self.in_table and self.row:
            self.rows.append(self.row)
        if tag == "table":
            self.in_table = False


def test_cost_changes_match_independent_reconciliation():
    """Expected values: committed reconciliation (2026-07-07), section 3.4.

    This is a transcription check, with no new economic equations or values.
    The source table enumerates thirteen changed cells, each old/new pair.
    """
    source = EVIDENCE.read_text().split("### 3.4", 1)[1].split("### 3.5", 1)[0]
    expected = re.findall(r"\| ([\w$/]+) \| (\w+) \| (\d+) → (\d+) \|", source)
    assert len(expected) == 13  # Reconciliation (2026-07-07), section 3.4.
    parser = CostTableParser()
    parser.feed(LOG.read_text())
    assert [tuple(row[:4]) for row in parser.rows] == expected
    for row in parser.rows:
        assert len(row) == 8
        assert all(cell.strip() for cell in row)
        assert row[5] == "S1 §3.4"
        assert row[6] == "UNRESOLVED"
        assert row[7] == "No; approval required for the affected system."


def test_log_records_model_decisions_and_source_links():
    text = LOG.read_text()
    for anchor in ("tax", "leases", "wti", "mirr", "disposition"):
        assert f'id="{anchor}"' in text
    assert "NOT_EVALUATED" in text
    assert "v50-assumptions-r1" in text
    for href in re.findall(r'href="([^"]+)"', text):
        if not href.startswith(("https://", "#")):
            assert (LOG.parent / href.split("#", 1)[0]).is_file(), href
    comparison = EVIDENCE.read_text()
    assert "v50_assumptions_change_log.html" in comparison
    assert "does not approve the cost/after-tax V50 basis" in comparison


def test_comparison_generator_retains_assumptions_gate(tmp_path, monkeypatch):
    """Exercise the shipped generator against frozen inputs, without OGOR access."""
    path = ROOT / "scripts/lower_tertiary/build_v30_vs_v50_comparison.py"
    spec = importlib.util.spec_from_file_location("comparison", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "comparison.md"
    monkeypatch.setattr(module, "OUT", output)
    module.main()
    published = ROOT / "reports/lower_tertiary/v30_vs_v50_comparison.md"
    # Prove the required EOF hook only removes terminal newlines: all generated
    # content, including every financial table cell, matches the committed report.
    assert output.read_text().rstrip("\n") == published.read_text().rstrip("\n")
    for report in (output, ROOT / "reports/lower_tertiary/v30_vs_v50_comparison.md"):
        text = report.read_text()
        assert "v50_assumptions_change_log.html" in text
        assert "does not approve the cost/after-tax V50 basis" in text
        assert text.index("v50_assumptions_change_log.html") < text.index(
            "## Producing fields"
        )
