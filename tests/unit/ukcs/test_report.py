"""Report contracts; numeric expectations below are independent hand calculations."""

import copy
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from worldenergydata.ukcs.report import build_report_facts, render_report_html


def chain_result():
    """Two rows in January sum to oil=2+3=5, gas=4+6=10, water=1+2=3.

    February oil=7, so total oil=12. These are invented normalized inputs,
    not published production or conversion-factor validation.
    """
    return {
        "field_name": '<Example & "field">',
        "unified_production": pd.DataFrame(
            {
                "year": [2024, 2024, 2024],
                "month": [2, 1, 1],
                "oil_bbl": [7.0, 2.0, 3.0],
                "gas_mcf": [8.0, 4.0, 6.0],
                "water_bbl": [4.0, 1.0, 2.0],
                "source": ["nsta"] * 3,
            }
        ),
        "ranked_concepts": [
            SimpleNamespace(
                concept_type="example",
                tree_type="wet",
                topology=None,
                total_score=np.float64(0.5),
                rationale=["<assumed>"],
                warnings=["Sparse metadata"],
            )
        ],
        "economics_label": "chain_plumbing_pre_tax",
        "pre_tax_metrics": {
            "months": np.int64(2),
            "gross_revenue_usd": np.float64(120),
        },
    }


def facts(**kwargs):
    return build_report_facts(
        chain_result(), input_echo={"scenario": "synthetic"}, **kwargs
    )


def test_facts_group_sort_and_serialize():
    result = facts()
    assert result["coverage"] == {
        "row_count": 3,
        "month_count": 2,
        "span_month_count": 2,
        "missing_month_count": 0,
        "missing_periods": [],
        "first_period": "2024-01",
        "last_period": "2024-02",
    }
    assert result["production_history"][0] == {
        "period": "2024-01",
        "oil_bbl": 5.0,
        "gas_mcf": 10.0,
        "water_bbl": 3.0,
    }
    assert result["economics_label"] == "chain_plumbing_pre_tax"
    assert result["ranked_concepts"][0]["score"] == 0.5
    assert json.loads(json.dumps(result, allow_nan=False)) == result


@pytest.mark.parametrize("provenance", ["nsta_live", "unknown", "fixture"])
def test_string_alone_cannot_claim_live_provenance(provenance):
    assert facts(provenance=provenance)["provenance"] == "fixture"


def test_live_requires_evidence_and_adapter_tags():
    evidence = {"sha256": "a" * 64, "cache_verified": True}
    stamp = "2026-10-20T00:00:00+00:00"
    result = facts(provenance="nsta_live", refreshed_at=stamp, source_evidence=evidence)
    assert result["provenance"] == "nsta_live"
    chain = chain_result()
    chain["unified_production"]["source"] = "ukcs_mock"
    assert (
        build_report_facts(
            chain,
            provenance="nsta_live",
            refreshed_at=stamp,
            source_evidence=evidence,
            input_echo={},
        )["provenance"]
        == "fixture"
    )


def test_missing_values_are_json_null_and_not_zero():
    chain = chain_result()
    chain["unified_production"]["water_bbl"] = np.nan
    result = build_report_facts(chain, input_echo={})
    assert result["production_history"][0]["water_bbl"] is None
    json.dumps(result, allow_nan=False)


def test_html_escapes_data_and_has_no_external_assets():
    result = facts()
    result["source"]["url"] = 'javascript:alert("bad")'
    html = render_report_html(result)
    assert '<Example & "field">' not in html
    assert "&lt;Example &amp; &quot;field&quot;&gt;" in html
    assert "&lt;assumed&gt;" in html
    assert "javascript:" not in html
    assert "SYNTHETIC: invented inputs, not NSTA data" in html
    assert "chain_plumbing_pre_tax" in html
    assert "NOT a UK investment NPV" in html
    assert "#736" in html
    assert "<svg" in html and "<details>" in html
    assert "<script" not in html and "<link" not in html
    assert "Revision history" in html


def test_renderer_rejects_live_badge_without_verified_source():
    result = copy.deepcopy(facts())
    result["provenance"] = "nsta_live"
    html = render_report_html(result)
    assert "real: NSTA live" not in html


def test_empty_history_renders_explicit_missing_data():
    chain = chain_result()
    chain["unified_production"] = chain["unified_production"].iloc[:0]
    html = render_report_html(build_report_facts(chain, input_echo={}))
    assert "No production records" in html


@pytest.mark.parametrize("stamp", ["invalid", "2026-10-20", "2026-10-20T00:00:00"])
def test_live_timestamp_must_be_timezone_qualified(stamp):
    result = facts(
        provenance="nsta_live",
        refreshed_at=stamp,
        source_evidence={"sha256": "a" * 64, "cache_verified": True},
    )
    assert result["provenance"] == "fixture"


def test_fixture_source_is_schema_reference_without_production_licence():
    result = facts()
    assert result["source"]["kind"] == "schema_reference"
    assert result["source"]["licence"] is None
    assert result["source"]["licence_url"] is None
    html = render_report_html(result)
    assert "NSTA PPRS schema reference" in html
    assert "NSTA PPRS production source" not in html
    assert "NSTA Open User Licence</a>" not in html


def test_verified_live_keeps_production_source_and_licence():
    result = facts(
        provenance="nsta_live",
        refreshed_at="2026-10-20T00:00:00+00:00",
        source_evidence={"sha256": "a" * 64, "cache_verified": True},
    )
    assert result["source"]["kind"] == "production_source"
    assert result["source"]["licence"] == "NSTA Open User Licence"
    assert "NSTA PPRS production source" in render_report_html(result)


def test_scores_remain_distinct_and_months_render_as_integer():
    result = facts()
    first = result["ranked_concepts"][0]
    first["score"] = 0.688
    second = copy.deepcopy(first)
    second["score"] = 0.661
    result["ranked_concepts"].append(second)
    html = render_report_html(result)
    assert "68.8%" in html and "66.1%" in html
    assert "<td>months</td><td>2</td>" in html


@pytest.mark.parametrize(
    "year,months,missing",
    [
        (2024, [1, 2, 4], "2024-03"),
        (2023, [11, 12, 14], "2024-01"),
    ],
)
def test_missing_calendar_months_are_counted_and_break_chart(year, months, missing):
    chain = chain_result()
    frame = chain["unified_production"]
    frame["year"] = [year + (m - 1) // 12 for m in months]
    frame["month"] = [(m - 1) % 12 + 1 for m in months]
    result = build_report_facts(chain)
    assert result["coverage"]["month_count"] == 3
    assert result["coverage"]["span_month_count"] == 4
    assert result["coverage"]["missing_month_count"] == 1
    assert result["coverage"]["missing_periods"] == [missing]
    assert result["production_history"][2] == {
        "period": missing,
        "oil_bbl": None,
        "gas_mcf": None,
        "water_bbl": None,
    }
    html = render_report_html(result)
    assert html.count("<polyline ") == 6  # Two disconnected segments per unit.
    assert f"<td>{missing}</td><td>Not available</td>" in html
