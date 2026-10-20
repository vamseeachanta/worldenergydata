"""Integrated synthetic example and deterministic, escaped report contracts."""

import importlib.util
import json
from decimal import Decimal as D
from pathlib import Path

from worldenergydata.cost.portfolio.accounting import Interval
from worldenergydata.cost.portfolio.report import (
    compare_estimates,
    render_html,
    write_report,
)


def example_module():
    path = (
        Path(__file__).resolve().parents[3] / "scripts/cost/build_portfolio_example.py"
    )
    spec = importlib.util.spec_from_file_location("portfolio_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_model_consistency_preserves_uncertainty():
    """[13,19]-[12,18]=[-5,7]; intersection [13,18] is nonempty."""
    result = compare_estimates(Interval(D(13), D(19)), Interval(D(12), D(18)))
    assert result["relation"] == "overlap"
    assert result["variance"] == Interval(D(-5), D(7))
    assert compare_estimates(None, Interval(D(1), D(2)))["relation"] == "indeterminate"
    assert (
        compare_estimates(Interval(D(3), D(4)), Interval(D(1), D(2)))["relation"]
        == "direct_above"
    )


def test_generated_example_answers_and_deterministic_bytes(tmp_path):
    """Map: [100,120]-[30,40]=[60,90]. Model: 10+2*3=16, interval [13,19]."""
    payload = example_module().build_example()
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_report(payload, first)
    write_report(payload, second)
    for filename in (
        "portfolio_example.html",
        "portfolio_example.json",
        "portfolio_example_manifest.json",
    ):
        assert (first / filename).read_bytes() == (second / filename).read_bytes()
    report = json.loads((first / "portfolio_example.json").read_text())
    assert report["bottom_up"]["residual"] == {"low": "60", "high": "90"}
    assert report["estimator"]["interval"] == {"low": "13", "high": "19"}
    assert report["estimator"]["point"] == "16"
    assert report["workbook"]["variance"] == {"low": "10", "high": "30"}
    assert report["synthetic"] is True


def test_html_escapes_input_and_shows_provenance_and_revision():
    payload = example_module().build_example()
    payload["summary"] = '<script>alert("unsafe")</script>'
    html = render_html(payload)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert html.index("Summary") < html.index("Revision history") < html.index("Inputs")
    assert "NOT_EVALUATED" in html
    assert "Marginal bands are not additive" in html
    assert "assumed" in html
