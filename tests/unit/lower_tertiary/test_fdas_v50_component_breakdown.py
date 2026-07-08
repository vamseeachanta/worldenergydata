"""Regression tests for the FDAS V50-vs-wed component comparison."""

from __future__ import annotations

from pathlib import Path

REPORT = (
    Path(__file__).resolve().parents[3]
    / "reports"
    / "lower_tertiary"
    / "fdas_revision_comparison.md"
)


def _section_45() -> str:
    md = REPORT.read_text(encoding="utf-8")
    return md.split("## 4.5 Economics reconciliation", 1)[1].split(
        "## 4.6 Roy's V50 script", 1
    )[0]


def test_fdas_v50_comparison_uses_wed_latest_component_basis():
    section = _section_45()

    assert "wed (available basis)" not in section
    assert "only window where wed recomputes the full royalty/opex split" not in section
    assert "not recomputed on that basis" not in section

    assert "| Anchor | 1,336 | 1,279 | +57 | 1,067 |" in section
    assert "| Shenandoah | 1,588 | 1,460 | +128 | 649 |" in section
    assert "| Jack St Malo | 28,035 | 27,891 | +144 | 26,892 |" in section

    for heading in (
        "**Royalty ($MM):**",
        "**OPEX ($MM):**",
        "**Net cash flow ($MM):**",
        "**MIRR (annual):**",
    ):
        assert heading in section

    assert "| Julia | 974 | 969 | +5 |" in section
    assert "| Stones | 1,947 | 1,769 | +178 |" in section
    assert "| Jack St Malo | 3,877 | 6,344 | −2,467 |" in section
    assert "| Buckskin | 6.66% | 4.47% | +2.19 pp |" in section
