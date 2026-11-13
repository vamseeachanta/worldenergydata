"""Report calculations checked against independent hand calculations."""

import json
import math
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from worldenergydata.cost.data_collection.disclosure_seed_dataset import (
    load_seed_disclosure_records,
)
from worldenergydata.cost.reporting.benchmark_report import build_report_facts


def points(values=(10, 20, 30, 40, 100)):
    """Synthetic arithmetic fixture; amounts are not engineering input."""
    return [
        SimpleNamespace(
            region="Region A",
            water_depth_band="deep",
            cost_type="total_capex",
            activity_type="drilling",
            operator="Operator A",
            year_sanction=2020,
            cost_usd_mm=value,
            source="Supplied arithmetic fixture",
        )
        for value in values
    ]


def test_cohort_median_and_outlier_from_hand_calculation():
    """Sorted [10,20,30,40,100]: median=30, inclusive Q1=20, Q3=40.

    NIST/SEMATECH e-Handbook, section 1.3.3.7, Box Plot (web edition
    retrieved 2026-10-20): IQR = Q3-Q1 = 20; inner fences are
    20-1.5*20=-10 and 40+1.5*20=70, so only 100 is flagged.
    """
    facts = build_report_facts(load_seed_disclosure_records(), points(), "2026-10-20")
    cohort = facts["cohorts"][0]
    assert cohort["count"] == 5
    assert cohort["median_usd_mm"] == 30
    assert cohort["q1_usd_mm"] == 20
    assert cohort["q3_usd_mm"] == 40
    assert cohort["upper_fence_usd_mm"] == 70
    assert [r["cost_usd_mm"] for r in facts["outliers"]] == [100]
    assert facts["operators_covered"] == 3
    assert facts["operator_rows"][0]["provenance"]["source_sha256"]
    assert facts["operator_rows"][0]["normalized_yoy_pct"] is None


@pytest.mark.parametrize("values", [(), (10,), (10, 20), (10, 20, 30)])
def test_small_cohorts_are_not_evaluated(values):
    facts = build_report_facts([], points(values), "2026-10-20")
    assert facts["outliers"] == []
    if values:
        assert facts["cohorts"][0]["outlier_status"] == "NOT_EVALUATED"


def test_render_is_offline_escaped_and_repeatable(tmp_path):
    from worldenergydata.cost.reporting.benchmark_report import (
        render_html,
        write_report,
    )

    outputs = write_report(tmp_path, "2026-10-20")
    first = {name: path.read_bytes() for name, path in outputs.items()}
    assert first == {
        name: path.read_bytes()
        for name, path in write_report(tmp_path, "2026-10-20").items()
    }
    html = outputs["html"].read_text(encoding="utf-8")
    for forbidden in ("<script src=", "<link href=", 'src="http', "cdn.plot"):
        assert forbidden not in html
    for required in (
        "<svg",
        "Illustrative seed — not yet ingested",
        "ungated — #336 pending",
        "pending #344",
        "Revision history",
        "source_sha256",
        "fiscal_basis",
        "retrieval_date",
        "Operator",
    ):
        assert required in html
    record = replace(
        load_seed_disclosure_records()[0],
        operator='<img src=x onerror="bad()">',
        provenance={
            **load_seed_disclosure_records()[0].provenance,
            "source_url": "javascript:bad()",
        },
    )
    rendered = render_html(build_report_facts([record], [], "2026-10-20"))
    assert "<img src=x" not in rendered
    assert "&lt;img" in rendered
    assert 'href="javascript:' not in rendered


def test_pending_dependencies_use_portable_issue_references():
    from worldenergydata.cost.reporting.benchmark_report import render_html

    facts = build_report_facts([], [], "2026-10-20")
    rendered = render_html(facts)
    assert 'href="https://github.com/' not in rendered
    for issue, description in facts["pending"].items():
        assert f"#{issue}: {description}" in rendered


@pytest.mark.parametrize("kind", ["html", "facts"])
def test_report_uses_lf_with_crlf_platform_default(tmp_path, monkeypatch, kind):
    from worldenergydata.cost.reporting.benchmark_report import write_report

    original_open = Path.open

    def crlf_default_open(path, mode="r", **kwargs):
        if "b" not in mode and kwargs.get("newline") is None:
            kwargs["newline"] = "\r\n"
        return original_open(path, mode, **kwargs)

    with monkeypatch.context() as platform:
        platform.setattr(Path, "open", crlf_default_open)
        outputs = write_report(tmp_path, "2026-10-20")

    output = outputs[kind].read_bytes()
    output.decode("utf-8")
    assert b"\n" in output
    assert b"\r" not in output


def test_outliers_retain_operator_and_source_identity():
    facts = build_report_facts([], points(), "2026-10-20")
    assert facts["outliers"][0]["operator"] == "Operator A"
    assert facts["outliers"][0]["source_record_index"] == 5
    assert len(facts["outliers"][0]["source_record_sha256"]) == 64


@pytest.mark.parametrize("calibration_values", [(1,), (10000,) * 4])
def test_calibration_rows_do_not_enter_disclosure_statistics(calibration_values):
    from worldenergydata.cost.reporting.benchmark_report import render_html

    observed = points()
    calibration = points(calibration_values)
    for point in calibration:
        point.source += "; derived calibration sub-observation"
        point.operator = "Calibration fixture"
        point.year_sanction = 2009
    inputs = [*calibration, *observed]
    original = [vars(point).copy() for point in inputs]

    facts = build_report_facts([], inputs, "2026-10-20")

    cohort = facts["cohorts"][0]
    assert len(facts["cohorts"]) == 1
    assert cohort["count"] == 5
    assert cohort["median_usd_mm"] == 30
    assert cohort["q1_usd_mm"] == 20
    assert cohort["q3_usd_mm"] == 40
    assert cohort["year_min"] == cohort["year_max"] == 2020
    assert [row["cost_usd_mm"] for row in facts["outliers"]] == [100]
    outlier = facts["outliers"][0]
    assert outlier["source_record_index"] == len(inputs)
    assert (
        outlier["source_record_sha256"]
        == sha256(json.dumps(vars(observed[-1]), sort_keys=True).encode()).hexdigest()
    )
    assert "Calibration fixture" not in json.dumps(facts)
    assert "Calibration fixture" not in render_html(facts)
    assert "derived calibration rows excluded" in facts["cohort_basis"]
    assert "derived calibration rows excluded" in render_html(facts)
    assert [vars(point) for point in inputs] == original


def test_public_calibration_rows_are_excluded_from_reported_observations():
    from worldenergydata.cost.data_collection.public_dataset import load_public_dataset
    from worldenergydata.cost.reporting.benchmark_report import render_html

    inputs = load_public_dataset()
    disclosed = [
        point
        for point in inputs
        if "derived calibration sub-observation" not in point.source
    ]
    assert len(disclosed) < len(inputs)
    facts = build_report_facts([], inputs, "2026-10-20")
    expected = build_report_facts([], disclosed, "2026-10-20")

    assert facts["cohorts"] == expected["cohorts"]
    assert sum(cohort["count"] for cohort in facts["cohorts"]) == len(disclosed)
    assert facts["outliers"] == expected["outliers"]
    assert render_html(facts) == render_html(expected)
    for row in facts["outliers"]:
        point = inputs[row["source_record_index"] - 1]
        assert "derived calibration sub-observation" not in point.source
        assert (
            row["source_record_sha256"]
            == sha256(
                json.dumps(point.model_dump(mode="json"), sort_keys=True).encode()
            ).hexdigest()
        )


def test_yoy_gap_zero_and_comparability_are_explicit():
    """Hand calculation: (20-10)/10=1; a zero prior has no ratio.

    A missing year cannot supply an annual change. Comparable means the
    upstream policy has qualified both records on the same stated basis.
    """
    base = load_seed_disclosure_records()[0]
    first = replace(base, fiscal_year=2020, reported_capex_usd_mm=0)
    second = replace(base, fiscal_year=2021, reported_capex_usd_mm=10)
    third = replace(base, fiscal_year=2023, reported_capex_usd_mm=20)
    rows = build_report_facts([third, first, second], [], "2026-10-20")["operator_rows"]
    assert rows[1]["yoy_delta_usd_mm"] == 10
    assert rows[1]["yoy_delta_pct"] is None
    assert rows[2]["yoy_delta_usd_mm"] is None
    qualified = [
        replace(second, comparability_status="comparable", comparability_basis="same"),
        replace(
            third,
            fiscal_year=2022,
            comparability_status="comparable",
            comparability_basis="same",
        ),
    ]
    assert (
        build_report_facts(qualified, [], "2026-10-20")["operator_rows"][1][
            "normalized_yoy_pct"
        ]
        == 1
    )


@pytest.mark.parametrize("amount", [-1, math.nan, math.inf])
def test_invalid_disclosure_amount_rejected(amount):
    record = replace(load_seed_disclosure_records()[0], reported_capex_usd_mm=amount)
    with pytest.raises(ValueError, match="CAPEX"):
        build_report_facts([record], [], "2026-10-20")


def test_duplicates_and_non_usd_rejected():
    record = load_seed_disclosure_records()[0]
    with pytest.raises(ValueError, match="Duplicate"):
        build_report_facts([record, record], [], "2026-10-20")
    with pytest.raises(ValueError, match="USD"):
        build_report_facts([replace(record, currency="EUR")], [], "2026-10-20")


def test_cohorts_do_not_mix_cost_types():
    mixed = points((10, 20))
    mixed[1].cost_type = "drilling"
    facts = build_report_facts([], mixed, "2026-10-20")
    assert len(facts["cohorts"]) == 2
    assert {c["median_usd_mm"] for c in facts["cohorts"]} == {10, 20}


@pytest.mark.parametrize("year", [True, 2020.5, "<script>bad()</script>"])
def test_non_integer_fiscal_year_is_rejected(year):
    record = replace(load_seed_disclosure_records()[0], fiscal_year=year)
    with pytest.raises(ValueError, match="year"):
        build_report_facts([record], [], "2026-10-20")
