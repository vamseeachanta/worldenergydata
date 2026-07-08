"""Regression tests for frozen V30 references in per-field economics reports."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

import scripts.lower_tertiary.generate_field_economics_report as field_report

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "reports" / "lower_tertiary"
V30_BASELINE = (
    PROJECT_ROOT / "config" / "analysis" / "lower_tertiary" / "golden_baseline_v30.yml"
)

FIELDS = [
    ("jack_st_malo", "field_economics_jack_st_malo_v50.md"),
    ("cascade_chinook", "field_economics_cascade_chinook_v50.md"),
]

EXPECTED_GOLDEN_NPV = {
    "Jack St Malo": -881_064_818.72,
    "Cascade Chinook": -1_474_083_632.85,
}


def _golden_npv_mm(project_id: str) -> float:
    baseline = yaml.safe_load(V30_BASELINE.read_text(encoding="utf-8"))
    return baseline["projects"][project_id]["npv_usd"] / 1e6


def _usd_mm(value: float) -> str:
    return f"${value:,.1f} M"


def _compact_usd_mm(value: float) -> str:
    if value < 0:
        return f"-${abs(value):,.1f}M"
    return f"${value:,.1f}M"


@pytest.mark.parametrize("dev_name,expected", EXPECTED_GOLDEN_NPV.items())
def test_generator_reads_golden_v30_reference_financials(dev_name, expected):
    row = field_report._read_golden_v30_financials(dev_name)

    assert row is not None
    assert row["npv_usd"] == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("project_id,report_name", FIELDS)
def test_latest_report_uses_golden_v30_reference_npv(project_id, report_name):
    md = (REPORTS_DIR / report_name).read_text(encoding="utf-8")
    expected = _golden_npv_mm(project_id)

    assert f"frozen V30 reference NPV = {_compact_usd_mm(expected)}" in md
    assert re.search(
        rf"\| \*\*NPV @ 10%\*\* \| \*\*\$[-0-9,.]+ M\*\* \| "
        rf"{re.escape(_usd_mm(expected))} \|",
        md,
    )
    assert f"| **NPV @ 10%** | **{_usd_mm(expected)}** |" in md
