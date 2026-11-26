"""Read back the appendix depth layout, annual marks and offline legend bindings."""

from pathlib import Path
from xml.etree import ElementTree as ET

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/exploration_leasing"


def test_depth_panels_share_calendar_and_value_axes(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    from lease_charts import BANDS, interactive
    from lease_panels import render_panels

    keys = [f"spud_share_5y|{band}" for band in BANDS]
    years = list(range(2005, 2011))
    groups = {
        key: {
            year: {
                "value": None if band == 1 and year == 2006 else band + 1,
                "moving_average": band + 1 if year >= 2009 and band != 1 else None,
                "partial": "0",
                "availability": "verified",
            }
            for year in years
        }
        for band, key in enumerate(keys)
    }
    figure = {
        "title": "Leases with a first exploratory spud by block water depth",
        "ylabel": "Share of effective leases (%)",
        "groups": keys,
        "labels": BANDS,
        "note": "The five year window ends at the fifth anniversary.",
        "y_scale": {"max": 5, "step": 1},
    }
    svg = render_panels(figure, groups)
    root = ET.fromstring(svg)
    panels = root.findall(".//{*}g[@class='panel']")
    assert len(panels) == 4
    first_points = []
    last_baseline = 0
    for index, panel in enumerate(panels):
        ticks = panel.findall("{*}text[@text-anchor='end']")
        assert [tick.text for tick in ticks] == ["0", "1", "2", "3", "4", "5"]
        offset = float(
            panel.get("transform").removeprefix("translate(0 ").removesuffix(")")
        )
        assert offset + float(ticks[-1].get("y")) > last_baseline
        last_baseline = offset + float(ticks[0].get("y"))
        legend = panel.find(f".//{{*}}g[@data-legend='{index}']")
        assert legend.findtext("{*}text") == BANDS[index]
        series = panel.find(f".//{{*}}g[@data-series='{index}']")
        assert series.get("data-label") == BANDS[index]
        annual = series.find("{*}path[@class='annual']")
        assert annual.get("stroke-dasharray") == legend.find("{*}line").get(
            "stroke-dasharray"
        )
        assert annual.get("stroke-dasharray")
        assert annual.get("d").count("M") == (2 if index == 1 else 1)
        assert (series.find("{*}path[@class='trend']") is None) == (index == 1)
        points = series.findall("{*}circle")
        assert len(points) == (5 if index == 1 else 6)
        assert float(points[0].get("cy")) == float(ticks[index + 1].get("y")) - 5
        first_points.append(points[0].get("cx"))
        year_labels = [
            label.text
            for label in panel.findall("{*}text")
            if label.text in map(str, years)
        ]
        assert year_labels == (["2005", "2010"] if index == 3 else [])
    assert len(set(first_points)) == 1
    assert svg.strip() in interactive(figure, svg, groups)
