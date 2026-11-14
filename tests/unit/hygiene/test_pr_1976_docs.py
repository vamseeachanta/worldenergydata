"""Review regressions for the UKCS replay addendum and proposed PR body."""

from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "packages/worldenergydata-ukcs/src/worldenergydata/ukcs/docs/agent-pack.md"
DESCRIPTION = ROOT / "docs/reviews/pr-1976-description.md"


def assert_rendered_table(text, header, columns):
    """Check the GFM table actually renders, including every data column."""
    rendered = MarkdownIt("commonmark").enable("table").render(text)
    tables = rendered.split("<table>")[1:]
    matches = [table for table in tables if f"<th>{header}</th>" in table]
    assert len(matches) == 1, f"Expected one rendered {header} table"
    table = matches[0].split("</table>")[0]
    assert table.count("<th>") == columns
    rows = table.split("<tbody>")[1].split("</tbody>")[0].split("<tr>")[1:]
    assert len(rows) == 3
    assert all(row.count("<td>") == columns for row in rows)


def test_pack_replay_table_renders():
    """P2-1: five-column evidence must render as a table on GitHub."""
    assert_rendered_table(PACK.read_text(encoding="utf-8"), "Replay", 5)


def test_description_does_not_claim_unshipped_evidence():
    """P2-2: a description must identify unavailable replay attachments."""
    text = DESCRIPTION.read_text(encoding="utf-8")
    assert "accompany the patch" not in text
    assert "not retained" in text
    assert "historical" in text.lower()


def test_description_count_table_renders():
    """P3-1: the six-column run counts must render as a table on GitHub."""
    assert_rendered_table(DESCRIPTION.read_text(encoding="utf-8"), "Run", 6)


def test_description_records_pr_existence_and_authorship():
    """P3-2: current PR metadata must distinguish original and follow-up work."""
    text = DESCRIPTION.read_text(encoding="utf-8")
    assert "no PR was opened" not in text
    assert "Nothing was pushed" not in text
    assert "Generated with Claude Code" not in text
    assert "Codex" in text
    assert "existing PR" in text


def test_revision_history_accounts_for_replay_addendum():
    """P3-3: revision 2 must account for the same-day verification addendum."""
    text = PACK.read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith("| 2 |")]
    assert len(rows) == 1
    assert "replay addendum" in rows[0]
