"""Review regressions for the UKCS replay addendum."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = (
    ROOT / "packages/worldenergydata-ukcs/src/worldenergydata/ukcs/docs/agent-pack.md"
)


def assert_rendered_table(text, header, columns):
    """Check the GFM table actually renders, including every data column."""
    MarkdownIt = pytest.importorskip("markdown_it").MarkdownIt
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


def test_revision_history_accounts_for_replay_addendum():
    """P3-3: revision 2 must account for the same-day verification addendum."""
    text = PACK.read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith("| 2 |")]
    assert len(rows) == 1
    assert "replay addendum" in rows[0]
