"""Sparse presentation charts must not imply values for missing calendar years.

Source: issue #1017, 'least assumptions lead'; SVG 2 (2018), sections
9.3.3 and 9.3.5: moveto starts a subpath, lineto joins points.
All years and values below are synthetic test inputs, not cost estimates.
"""

import importlib.util
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "stakeholder_presentation", ROOT / "scripts/cost/build_stakeholder_presentation.py"
)
presentation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(presentation)
schema = importlib.import_module("worldenergydata.cost.timeseries.schema")


def _commands(svg):
    return [
        re.findall(r"[ML]", node.attrib["d"])
        for node in ET.fromstring(svg).iter("path")
    ]


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({2000: 10, 2001: 20, 2003: 30}, ["M", "L", "M"]),
        ({2003: 30, 2000: 10, 2001: 20}, ["M", "L", "M"]),
        ({2000: 10, 2002: 20, 2004: 30}, ["M", "M", "M"]),
        ({2000: 10, 2001: 20, 2002: 30}, ["M", "L", "L"]),
        ({2000: 10}, ["M"]),
    ],
)
def test_lines_join_only_adjacent_calendar_years(values, expected):
    """Hand check: 2000→2001 joins; 2001→2003 skips 2002 and must restart.

    The same calendar rule gives each literal command list above, regardless
    of input ordering. A lone point has one moveto and no connecting segment.
    """
    svg = presentation._line_chart([("Synthetic", values, "red")], "Rates", "USD/day")
    assert _commands(svg) == [expected]
    assert len(list(ET.fromstring(svg).iter("title"))) == len(values)


def test_each_series_keeps_its_own_gaps():
    """Hand check: one series misses 2001; another has both 2000 and 2001."""
    svg = presentation._line_chart(
        [
            ("Sparse", {2000: 10, 2002: 30}, "red"),
            ("Dense", {2000: 10, 2001: 20}, "blue"),
            ("Empty", {}, "green"),
        ],
        "Rates",
        "USD/day",
    )
    assert _commands(svg) == [["M", "M"], ["M", "L"]]


def test_rebasing_preserves_calendar_gaps():
    """Hand calculation: 10/10×100=100; 20/10×100=200; 30/10×100=300.

    Rebasing changes values only; the missing 2002 observation stays absent.
    The existing index definition is in the presentation's formula card.
    """
    values = presentation._rebase_100({2000: 10, 2001: 20, 2003: 30})
    assert values == {2000: 100, 2001: 200, 2003: 300}
    svg = presentation._line_chart([("Index", values, "red")], "Index", "index")
    assert _commands(svg) == [["M", "L", "M"]]


def test_empty_chart_has_no_invented_points():
    svg = presentation._line_chart([("Empty", {}, "red")], "Rates", "USD/day")
    assert "No sourced data" in svg
    assert "<path" not in svg


def _observation(**changes):
    """Synthetic source rows; values and citation strings are test inputs."""
    fields = {
        "year": 2000,
        "component": schema.CostComponent.RIG_DAY_RATE_DRILLSHIP,
        "value": 10,
        "unit": "usd_per_day",
        "figure_type": schema.FigureType.FLEET_AVERAGE,
        "provenance": schema.Provenance.SOURCED,
        "source_title": "Synthetic source",
        "source_url": "https://example.org/source?x=1&y=2",
        "page_reference": "Test table",
        "quoted_text": 'A <tag> & "10"',
        "accessed_date": date(2026, 10, 19),
    }
    fields.update(changes)
    return schema.CostObservation(**fields)


def test_source_table_keeps_raw_inputs_and_escapes_citations():
    """Hand check: raw 10 and 30 contribute (10+30)/2=20 to one chart dot.

    The appendix must show both source rows, not replace them with the mean.
    Citation text and URL query separators must remain escaped HTML text.
    """
    table = presentation._source_table(
        [_observation(), _observation(value=30, source_title="Second synthetic source")]
    )
    assert table.count("<tr>") == 3  # Header plus the two synthetic inputs.
    assert ">10.0<" in table
    assert ">30.0<" in table
    assert "A &lt;tag&gt; &amp; &quot;10&quot;" in table
    assert "https://example.org/source?x=1&amp;y=2" in table
    assert "2026-10-19" in table
    assert "Test table" in table
    assert "fleet_average" in table


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "GBP"},
        {"region": "local"},
        {"figure_type": schema.FigureType.SINGLE_FIXTURE},
        {"component": schema.CostComponent.WELL_COST_COMPLETE},
        {"provenance": schema.Provenance.FITTED, "notes": "Synthetic fit"},
        {"provenance": schema.Provenance.ASSUMED, "notes": "Synthetic assumption"},
        {"provenance": schema.Provenance.ALLOCATED, "notes": "Synthetic allocation"},
        {"provenance": schema.Provenance.TODO, "value": None},
    ],
)
def test_source_table_uses_the_chart_lens(changes):
    """Excluded inputs follow the existing annual_means contract, not new policy."""
    table = presentation._source_table(
        [
            _observation(),
            _observation(source_title="Excluded synthetic source", **changes),
        ]
    )
    assert "Synthetic source" in table
    assert "Excluded synthetic source" not in table


def test_reference_sources_use_their_chart_regions():
    table = presentation._source_table(
        [
            _observation(component=schema.CostComponent.INDEX_CPI, region="US"),
            _observation(component=schema.CostComponent.OIL_PRICE_BRENT),
            _observation(
                component=schema.CostComponent.INDEX_CPI,
                source_title="Excluded global CPI",
            ),
        ]
    )
    assert "US CPI-U" in table
    assert "Brent" in table
    assert "Excluded global CPI" not in table


def test_empty_source_table_declares_no_contributing_observations():
    assert "No sourced observations" in presentation._source_table([])


def test_presentation_regenerates_without_advancing_approvals(tmp_path, monkeypatch):
    """Integration: real curated inputs render locally; no approvals are inferred."""
    output = tmp_path / "presentation.html"
    monkeypatch.setattr(presentation, "OUT", output)
    assert presentation.main() == 0
    rendered = output.read_text(encoding="utf-8")
    assert "Missing years break the line" in rendered
    assert "Revision history" in rendered
    assert 'href="#sources"' in rendered
    assert 'id="sources"' in rendered
    assert rendered.count("awaiting approval — decision recorded") == len(
        presentation.ASSUMPTIONS
    )
    charts = re.findall(r"<svg\b.*?</svg>", rendered, flags=re.DOTALL)
    assert charts
    for chart in charts:
        ET.fromstring(chart)
