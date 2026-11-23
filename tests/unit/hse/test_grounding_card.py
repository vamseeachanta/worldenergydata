# ABOUTME: Tests for worldenergydata.hse.grounding_card — HTML grounding card renderer.
# ABOUTME: Pure render; no network. Verifies structure, vintage, and no-operator-names.

"""Tests for the grounding card renderer (#490)."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from worldenergydata.hse.grounding import ground
from worldenergydata.hse.grounding_card import AnalysisSummary, render_html

FIXTURE = Path(__file__).parent / "fixtures" / "bsee_incinv_sample.txt"

ANALYSIS = AnalysisSummary(
    title="Mooring Fatigue — Test",
    headline="Min fatigue life 18.4 yr at the fairlead.",
    metrics=[("18.4 yr", "Min fatigue life"), ("Line 3", "Governing line")],
    method="T-N screening",
    basis="illustrative",
)


def _doc():
    g = ground("mooring_fatigue", bsee_path=FIXTURE).to_dict()
    return render_html(g, ANALYSIS, generated_on="2026-06-18")


def test_html_is_well_formed():
    # HTMLParser raises on malformed markup via our error override path
    class P(HTMLParser):
        def error(self, message):  # pragma: no cover - only on bad markup
            raise ValueError(message)

    P().feed(_doc())


def test_card_carries_interactive_plot():
    doc = _doc()
    assert "cdn.plot.ly" in doc
    assert "Plotly.newPlot" in doc


def test_vintage_stamp_present():
    assert "current to 2026-01-08" in _doc()  # corpus-wide newest record


def test_analysis_panel_rendered():
    doc = _doc()
    assert "Min fatigue life 18.4 yr at the fairlead." in doc
    assert "Line 3" in doc


def test_real_incidents_present():
    doc = _doc()
    assert "MC 437" in doc and "GC 237" in doc


def test_no_operator_names_and_attribution():
    doc = _doc().lower()
    # no operator/company names (Operator Aggregation Contract, #423)
    for banned in ("chevron", "shell", "apache", "exxon", "hess", "talos"):
        assert banned not in doc
    # the policy disclaimer + data attribution must be present
    assert "no operator names" in doc
    assert "data.bsee.gov" in doc


def test_html_escaping_of_analysis_fields():
    a = AnalysisSummary(title="A & B <x>", headline="risk > 1", metrics=[])
    doc = render_html(
        ground("mooring_fatigue", bsee_path=FIXTURE).to_dict(), a, "2026-06-18"
    )
    assert "A &amp; B &lt;x&gt;" in doc
    assert "risk &gt; 1" in doc
