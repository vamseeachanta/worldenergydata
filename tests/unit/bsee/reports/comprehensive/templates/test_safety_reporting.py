"""Reporting integration for qualified incidence rates and validation errors.

Equation source: Cal/OSHA, Brief Guide to Recordkeeping Requirements,
2021 PDF revision, p. 5, Calculating Injury and Illness Incidence Rates.
https://www.dir.ca.gov/dosh/dosh_publications/RecKeepOverview.pdf
All example counts and exposure values below are synthetic.
"""

import runpy
from pathlib import Path

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.compliance_template import (
    ComplianceTemplate,
    SafetyMetrics,
)


def test_report_uses_qualified_case_subsets(tmp_path):
    """Hand calculation: 7 * 200,000 / 400,000 = 3.5 recordables;
    2 * 200,000 / 400,000 = 1.0 lost-time cases for the same group/period.
    The unrelated incident total must not enter either rate.
    """
    report = ComplianceTemplate(template_path=tmp_path)
    report.add_safety_compliance_metrics(
        SafetyMetrics(
            incident_count=99,
            total_recordables=7,
            lost_time_incidents=2,
            man_hours_worked=400_000,
        )
    )
    assert report.context["safety_compliance"]["trir"] == 3.5
    assert report.context["safety_compliance"]["ltir"] == 1.0


@pytest.mark.parametrize("hours", [0, -1, None, float("nan"), float("inf")])
def test_report_propagates_invalid_exposure(tmp_path, hours):
    """A missing denominator cannot publish a measured zero for either rate."""
    report = ComplianceTemplate(template_path=tmp_path)
    with pytest.raises(ValueError, match="hours_worked"):
        report.add_safety_compliance_metrics(SafetyMetrics(man_hours_worked=hours))
    assert "safety_compliance" not in report.context


@pytest.mark.parametrize("field", ["total_recordables", "lost_time_incidents"])
def test_invalid_count_does_not_replace_valid_report(tmp_path, field):
    """A rejected update leaves the previous qualified context intact."""
    report = ComplianceTemplate(template_path=tmp_path)
    report.add_safety_compliance_metrics(SafetyMetrics(man_hours_worked=400_000))
    previous = report.context["safety_compliance"]
    with pytest.raises(ValueError, match="incident_count"):
        report.add_safety_compliance_metrics(
            SafetyMetrics(man_hours_worked=400_000, **{field: -1})
        )
    assert report.context["safety_compliance"] is previous


def test_worked_example(capsys):
    """Independent example answers: 7 * 200,000 / 400,000 = 3.5;
    2 * 200,000 / 400,000 = 1.0, using the cited normalization.
    """
    example = (
        Path(__file__).resolve().parents[6]
        / "examples/hse/reporting_incidence_rates.py"
    )
    runpy.run_path(str(example), run_name="__main__")
    assert capsys.readouterr().out.splitlines() == [
        "TRIR: 3.5",
        "LTIR: 1.0",
        "Rate unavailable: supply finite, positive actual employee-hours.",
    ]
