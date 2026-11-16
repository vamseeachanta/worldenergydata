"""Executable documentation contracts for issue #1351 (2026), defects 1–5."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPAT = ROOT / "src/worldenergydata/modules/marine_safety/docs"
CANONICAL = (
    ROOT
    / "packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs"
)


def test_compatibility_drafts_have_explicit_placeholders():
    """Defects 1–2 require committed drafts rather than unfiled issue numbers."""
    pack = (COMPAT / "agent-pack.md").read_text(encoding="utf-8")
    assert "issue pending" not in pack.lower()
    for name in ("Draft 1:", "Draft 4:"):
        assert name in (COMPAT / "ISSUES_DRAFT.md").read_text(encoding="utf-8")
    canonical_drafts = (CANONICAL / "ISSUES_DRAFT.md").read_text(encoding="utf-8")
    referenced = set(
        re.findall(
            r"issue pending \((\d+)\)",
            (CANONICAL / "agent-pack.md").read_text(),
            re.IGNORECASE,
        )
    )
    available = set(re.findall(r"^## Draft (\d+):", canonical_drafts, re.MULTILINE))
    assert referenced <= available
    assert "Canonical issue drafts" in pack
    assert "ISSUES_DRAFT.md" in pack


def test_gate_c3_has_baseline_verdict_and_is_counted():
    """Defect 3: the audit's excluded-file count and collection error remain FAIL.

    Source: issue #1351, defect 3 (2026): 52 omitted files and one collection
    error at the historical pin. Gate total is independently counted from rows.
    """
    pack = (COMPAT / "agent-pack.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (C\d+) \|.*$", pack, re.MULTILINE)
    c3 = next(line for line in pack.splitlines() if line.startswith("| C3 |"))
    assert "baseline FAIL" in c3
    assert "52" in c3 and "1 collection error" in c3 and "#1239" in c3
    total = re.search(r"total = (\d+)\.", pack)
    assert total and int(total.group(1)) == len(rows)
    assert "C3 included" in pack


def test_c4_counts_only_legacy_examples():
    """Defect 4: R3's canonical import cannot count toward compatibility C4."""
    pack = (COMPAT / "agent-pack.md").read_text(encoding="utf-8")
    c4 = next(line for line in pack.splitlines() if line.startswith("| C4 |"))
    assert "R1 and R2" in c4
    assert "R3" not in c4
    assert "2 PASS" in c4  # Source: the two legacy-path nodes in pack section 4.
    assert "canonical-only" in pack


def test_identity_example_cites_executable_evidence():
    """Defect 5: every inventoried suffix has measured identity and warning data."""
    pack = (COMPAT / "agent-pack.md").read_text(encoding="utf-8")
    # The suffix inventory is the application contract in pack sections 2 and 5.
    for suffix in (
        "(empty)",
        ".analysis",
        ".analysis.incidents",
        ".importers",
        ".processors",
    ):
        assert f"| `{suffix}` | True | DeprecationWarning |" in pack
    assert "test_marine_safety_redirect_identity_and_warning" in pack
    assert "Before: 4/56" in pack  # Source: collection regression's recorded red run.
    assert "After: 56/56" in pack  # Source: the independent disk/pytest set comparison.
