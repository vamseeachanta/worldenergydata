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
    source = (
        EVIDENCE.read_text(encoding="utf-8")
        .split("### 3.4", 1)[1]
        .split("### 3.5", 1)[0]
    )
    expected = re.findall(r"\| ([\w$/]+) \| (\w+) \| (\d+) → (\d+) \|", source)
    assert len(expected) == 13  # Reconciliation (2026-07-07), section 3.4.
    parser = CostTableParser()
    parser.feed(LOG.read_text(encoding="utf-8"))
    assert [tuple(row[:4]) for row in parser.rows] == expected
    for row in parser.rows:
        assert len(row) == 8
        assert all(cell.strip() for cell in row)
        assert row[5] == "S1 §3.4"
        assert row[6] == "UNRESOLVED"
        assert row[7] == "No; approval required for the affected system."


def test_log_records_model_decisions_and_source_links():
    text = LOG.read_text(encoding="utf-8")
    for anchor in ("tax", "leases", "wti", "mirr", "disposition"):
        assert f'id="{anchor}"' in text
    assert "NOT_EVALUATED" in text
    assert "v50-assumptions-r1" in text
    for href in re.findall(r'href="([^"]+)"', text):
        if not href.startswith(("https://", "#")):
            assert (LOG.parent / href.split("#", 1)[0]).is_file(), href
    comparison = EVIDENCE.read_text(encoding="utf-8")
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
    assert output.read_bytes() == published.read_bytes()
    assert output.read_bytes().endswith(b"\n")
    assert not output.read_bytes().endswith(b"\n\n")
    for report in (output, ROOT / "reports/lower_tertiary/v30_vs_v50_comparison.md"):
        text = report.read_text(encoding="utf-8")
        assert "v50_assumptions_change_log.html" in text
        assert "does not approve the cost/after-tax V50 basis" in text
        assert text.index("v50_assumptions_change_log.html") < text.index(
            "## Producing fields"
        )


def _source_section(number):
    source = EVIDENCE.read_text(encoding="utf-8")
    heading = re.search(rf"^##?# {re.escape(number)}[ .]", source, re.MULTILINE)
    assert heading, number
    remainder = source[heading.end() :]
    return re.split(r"^##?# ", remainder, maxsplit=1, flags=re.MULTILINE)[0]


def _model_row(anchor):
    text = LOG.read_text(encoding="utf-8")
    row = re.search(rf'<tr id="{anchor}">(.*?)</tr>', text)
    assert row, anchor
    return re.findall(r"<td>(.*?)</td>", row.group(1))


def test_tax_settings_match_cited_sections():
    row = _model_row("tax")
    citations = re.findall(r"§(\d+(?:\.\d+)?)", row[3])
    assert citations
    cited = " ".join(_source_section(number) for number in citations)
    assert "severance and ad-valorem at 0%" in row[2]
    assert re.search(r"severance (?:and|&) ad-valorem rates are 0\b", cited)
    assert "corporate tax at 21%" in row[2]
    assert re.search(r"corporate tax at 21\s*%", cited)
    assert "monthly NOL carryforward" in row[2]
    assert "monthly NOL carryforward" in cited


def test_wti_sensitivity_matches_cited_sections():
    row = _model_row("wti")
    citations = re.findall(r"§(\d+(?:\.\d+)?)", row[3])
    assert citations
    cited = " ".join(_source_section(number) for number in citations)
    assert "extended deck" in cited
    assert "as a sensitivity" in cited
