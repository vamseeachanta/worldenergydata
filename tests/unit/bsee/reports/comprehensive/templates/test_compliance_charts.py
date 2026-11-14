"""Chart regression cases with synthetic inputs and independent expectations.

Policy source: compliance_charts.py and compliance_calculations.py at
revision d867ba1e (2026). Existing display bands are presentation policy,
not regulatory acceptance limits. Percent scaling follows NIST SP 811,
section 7.10.2 (online revision 2025). All sample measurements are synthetic.
"""

import json
import re

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.compliance_charts import (
    create_compliance_dashboard,
    create_production_quota_chart,
)
from worldenergydata.bsee.reports.comprehensive.templates.compliance_models import (
    ComplianceMetrics,
    EnvironmentalMetrics,
    SafetyMetrics,
)
from worldenergydata.bsee.reports.comprehensive.templates.compliance_template import (
    ComplianceTemplate,
)


def chart_payload(html):
    """Read the actual traces and layout, excluding Plotly's default template."""
    match = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*', html)
    assert match is not None
    decoder = json.JSONDecoder()
    data, end = decoder.raw_decode(html[match.end() :])
    layout, _ = decoder.raw_decode(html[match.end() + end :].lstrip(" ,\n"))
    return data, layout


def test_dashboard_values_and_template_entry_point(tmp_path):
    """Hand calculation: 0.85, 0.92, 0.90 become 85, 92, 90 percent.

    Production is already a percentage, so 95 remains 95. The four titles
    and gauge bands come from compliance_charts.py at d867ba1e (2026).
    """
    inputs = {
        "production_compliance": 95.0,
        "environmental_score": 0.85,
        "safety_score": 0.92,
        "overall_compliance_score": 0.90,
    }
    original = inputs.copy()
    template = ComplianceTemplate(template_path=tmp_path)
    direct, _ = chart_payload(create_compliance_dashboard(inputs))
    wrapped, _ = chart_payload(template._create_compliance_dashboard(inputs))
    generated, _ = chart_payload(
        template.generate_compliance_visualizations(inputs)["compliance_dashboard"]
    )
    assert [trace["value"] for trace in direct] == [95.0, 85.0, 92.0, 90.0]
    assert [trace["gauge"]["threshold"]["value"] for trace in direct] == [
        90,
        80,
        85,
        90,
    ]
    assert direct == wrapped == generated
    assert inputs == original


@pytest.mark.parametrize(
    "invalid",
    [None, "invalid", "0.8", True, -1, float("nan"), float("inf"), 1e308, [], {}],
)
@pytest.mark.parametrize(
    "key, title",
    [
        ("safety_score", "Safety Score"),
        ("overall_compliance_score", "Overall Compliance"),
    ],
)
def test_invalid_score_is_not_evaluated(invalid, key, title, tmp_path):
    """Invalid values carry no numerical result; the valid 0.85 gives 85 %."""
    template = ComplianceTemplate(template_path=tmp_path)
    html = template.generate_compliance_visualizations(
        {key: invalid, "environmental_score": 0.85}
    )["compliance_dashboard"]
    traces, layout = chart_payload(html)
    assert len(traces) == 1
    assert traces[0]["value"] == 85.0
    assert traces[0]["title"]["text"] == "Environmental Score (%)"
    assert any(
        title in annotation["text"] and "NOT_EVALUATED" in annotation["text"]
        for annotation in layout["annotations"]
    )


@pytest.mark.parametrize("inputs", [None, {}, [], "invalid"])
def test_missing_dashboard_input_is_not_evaluated(inputs):
    """Absent measurements yield no numeric traces, never fabricated zeros."""
    traces, layout = chart_payload(create_compliance_dashboard(inputs))
    assert traces == []
    assert sum("NOT_EVALUATED" in a["text"] for a in layout["annotations"]) == 4


def test_score_bounds_and_overproduction():
    """Bounded scores lie in [0, 1]; production and overall can exceed it.

    Bounds source: compliance_models.py score clamps at d867ba1e (2026).
    Hand calculation: 0 * 100 = 0; 1 * 100 = 100; 1.1 * 100 = 110.
    Production is already a percentage and remains unscaled.
    """
    traces, layout = chart_payload(
        create_compliance_dashboard(
            {
                "production_compliance": 150.0,
                "environmental_score": 0.0,
                "safety_score": 1.0,
                "overall_compliance_score": 1.1,
            }
        )
    )
    assert [trace["value"] for trace in traces] == pytest.approx(
        [150.0, 0.0, 100.0, 110.0]
    )
    assert not any("NOT_EVALUATED" in a["text"] for a in layout["annotations"])


@pytest.mark.parametrize(
    "key, title",
    [("environmental_score", "Environmental Score"), ("safety_score", "Safety Score")],
)
def test_bounded_scores_above_unity_are_not_evaluated(key, title):
    """The overall-score exception does not relax environmental or safety bounds."""
    traces, layout = chart_payload(create_compliance_dashboard({key: 1.1}))
    assert traces == []
    assert any(
        title in annotation["text"] and "NOT_EVALUATED" in annotation["text"]
        for annotation in layout["annotations"]
    )


def test_calculated_overall_score_survives_overproduction(tmp_path):
    """The context builder's uncapped aggregate reaches the rendered dashboard."""
    template = ComplianceTemplate(template_path=tmp_path)
    context = template.build_compliance_context(
        ComplianceMetrics(
            permitted_production_bbls=100000, actual_production_bbls=110000
        ),
        EnvironmentalMetrics(),
        SafetyMetrics(),
    )
    summary = context["compliance_summary"]
    # Hand calculation: 110000 / 100000 * 100 = 110 percent production;
    # environmental and safety scores of 1 each give 100 percent each.
    # The existing aggregate is (110 + 100 + 100) / 3 = 310 / 3 percent.
    assert summary["production_compliance"] == pytest.approx(110.0)
    assert summary["environmental_score"] == pytest.approx(1.0)
    assert summary["safety_score"] == pytest.approx(1.0)
    assert summary["overall_compliance_score"] == pytest.approx(31 / 30)
    assert context["regulatory_status"] == "Non-Compliant"
    traces, layout = chart_payload(
        template.generate_compliance_visualizations(summary)["compliance_dashboard"]
    )
    assert {
        trace["title"]["text"]: trace["value"] for trace in traces
    } == pytest.approx(
        {
            "Production Compliance (%)": 110.0,
            "Environmental Score (%)": 100.0,
            "Safety Score (%)": 100.0,
            "Overall Compliance (%)": 310 / 3,
        }
    )
    assert not any("NOT_EVALUATED" in a["text"] for a in layout["annotations"])


@pytest.mark.parametrize(
    "quota, expected",
    [
        ({"oil_quota": 100000, "oil_actual": 95000}, [[100000, None], [95000, None]]),
        ({"gas_quota": 500000, "gas_actual": 480000}, [[None, 500], [None, 480]]),
        ({"oil_quota": 0, "gas_actual": 0}, [[0, None], [None, 0]]),
        ({}, [[None, None], [None, None]]),
        ({"oil_quota": "invalid", "gas_actual": None}, [[None, None], [None, None]]),
    ],
)
def test_partial_quota_preserves_known_values(quota, expected):
    """Oil is unscaled; existing gas display is divided by a thousand.

    Source: compliance_charts.py::create_production_quota_chart at d867ba1e
    (2026). Hand calculation: 500000 / 1000 = 500, 480000 / 1000 = 480.
    A missing input has no answer; explicit zero remains a measured zero.
    """
    original = quota.copy()
    traces, layout = chart_payload(create_production_quota_chart(quota))
    assert [trace["y"] for trace in traces] == expected
    assert any("NOT_EVALUATED" in a["text"] for a in layout["annotations"])
    assert quota == original


@pytest.mark.parametrize(
    "score, expected",
    [(0.9, "#4CAF50"), (0.8, "#FF9800"), (0.7, "#FFC107"), (0.0, "#F44336")],
)
def test_status_color_boundaries(score, expected, tmp_path):
    """Existing color policy: inclusive lower bounds at 0.9, 0.8 and 0.7.

    Source: compliance_calculations.py::get_compliance_status_color,
    revision d867ba1e (2026); this is a presentation lookup, not a limit.
    """
    template = ComplianceTemplate(template_path=tmp_path)
    assert template.get_compliance_status_color(score) == expected
