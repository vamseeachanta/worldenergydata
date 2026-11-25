"""Calendar windows and portable SVG requirements for yearly well series charts."""

import unicodedata
from xml.etree import ElementTree as ET

import pytest

from worldenergydata.bsee.yearly_trend import (
    BANDS,
    render_svg,
    trailing_average,
    with_trend,
)


def test_fifth_complete_year_and_partial_cutoff():
    values = dict(zip(range(2019, 2026), (2, 4, 6, 8, 10, 12, 99)))
    assert list(trailing_average(values, partial_year=2025).values()) == [
        None,
        None,
        None,
        None,
        6,
        8,
        None,
    ]
    assert trailing_average(values)[2025] == 27


def test_gap_breaks_rate_window_but_counts_can_fill_with_zero():
    values = {y: 10 for y in range(2005, 2016) if y != 2010}
    ratios = trailing_average(values)
    assert ratios[2009] == ratios[2015] == 10
    assert all(ratios[y] is None for y in range(2010, 2015))
    counts = trailing_average(values, is_count=True)
    assert all(counts[y] == 8 for y in range(2010, 2015))
    assert trailing_average({**values, 2010: 0})[2014] == 8
    assert trailing_average({**values, 2010: None})[2014] is None


def test_windows_do_not_mix_bands_or_measures():
    rows = [
        dict(group=g, band=b, year=y, value=v)
        for g, b, v in [
            ("Initial", BANDS[0], 2),
            ("Other", BANDS[0], 8),
            ("Initial", BANDS[1], 20),
        ]
        for y in range(2005, 2011)
        if y != 2007 or v != 8
    ]
    result = with_trend(rows, is_count=True, partial_year=2010)
    assert [(r["value"], r["moving_average"]) for r in result if r["year"] == 2009] == [
        (2, 2),
        (8, 6.4),
        (20, 20),
    ]
    assert all(r["moving_average"] is None for r in result if r["partial_year"])
    with pytest.raises(ValueError, match="duplicate"):
        with_trend(rows + rows[:1])


def test_svg_encodes_yearly_trend_measures_and_partial():
    rows = [
        dict(year=y, band=b, group=g, value=y - 2000 + i)
        for b in BANDS
        for i, g in enumerate(("First", "Second"))
        for y in range(2005, 2013)
    ]
    series = with_trend(rows, partial_year=2012)
    args = dict(title="Test & counts", ylabel="Permits (count)", xlabel="Approval year")
    doc = render_svg(series, **args)
    assert doc.encode() == render_svg(series, **args).encode()
    root = ET.fromstring(doc)
    assert root.attrib["font-family"] == "'DejaVu Sans','Segoe UI',Arial,sans-serif"
    assert {el.tag.split("}")[-1] for el in root.iter()}.isdisjoint(
        {"clipPath", "pattern", "filter", "mask", "foreignObject", "image"}
    )
    words = " ".join(root.itertext())
    for label in (
        "Yearly value",
        "5 year trailing moving average",
        "partial",
        "First",
        "Second",
        *BANDS,
        args["xlabel"],
        args["ylabel"],
    ):
        assert label in words
    assert not any(unicodedata.category(c) == "Pd" or c == "\u2212" for c in words)
    labels = root.findall(".//{*}text")
    assert all(float(el.get("font-size")) >= 15 for el in labels)
    assert any(
        el.text == args["title"] and float(el.get("font-size")) >= 18 for el in labels
    )
    assert all(float(el.get("r")) >= 4.5 for el in root.findall(".//{*}circle"))
    panels = root.findall(".//{*}g[@class='panel']")
    assert len(panels) == 4
    for panel, colour in zip(panels, ("#6588a6", "#427298", "#245476", "#102e46")):
        lines = panel.findall("{*}path")
        assert len(lines) == 4
        yearly = [el for el in lines if el.get("class") == "yearly"]
        trend = [el for el in lines if el.get("class") == "average"]
        assert len(yearly) == len(trend) == 2
        assert all(
            float(el.get("stroke-width")) >= 2 and el.get("stroke") == colour
            for el in yearly
        )
        assert all(
            float(el.get("stroke-width")) >= 4 and el.get("stroke") != colour
            for el in trend
        )
        for pair in (yearly, trend):
            assert pair[0].get("stroke-dasharray") is None
            assert pair[1].get("stroke-dasharray")
        assert len(panel.findall("{*}circle[@fill='white']")) == 2


def test_renderer_breaks_paths_at_missing_years_and_rejects_dash_text():
    rows = [
        dict(year=y, band=BANDS[0], value=1) for y in range(2000, 2013) if y != 2006
    ]
    series = with_trend(rows)
    root = ET.fromstring(
        render_svg(series, title="Rates", xlabel="Year", ylabel="Rate (%)")
    )
    for kind in ("yearly", "average"):
        assert root.find(f".//{{*}}path[@class='{kind}']").get("d").count("M") == 2
    with pytest.raises(ValueError, match="dash"):
        render_svg(series, title="Five-year rates", xlabel="Year", ylabel="Rate (%)")


STATUS_NAMES = ["Relinquished", "Expired", "Primary term", "Other"]
CHART_LABELS = dict(
    title="Lease status", xlabel="Effective year", ylabel="Leases (count)"
)


def test_named_series_share_one_panel_in_declared_order():
    rows = [
        dict(group=name, band="All water depths", year=year, value=10 * i + year - 2018)
        for i, name in reversed(list(enumerate(STATUS_NAMES)))
        for year in range(2019, 2025)
    ]
    trends = with_trend(
        rows, series_names=STATUS_NAMES, is_count=True, partial_year=2024
    )
    assert list(dict.fromkeys(row["group"] for row in trends)) == STATUS_NAMES
    # The five complete values for Expired are 11, 12, 13, 14 and 15.
    assert [r["moving_average"] for r in trends if r["group"] == "Expired"] == [
        None,
        None,
        None,
        None,
        13,
        None,
    ]

    args = dict(
        **CHART_LABELS,
        series_names=STATUS_NAMES,
        panel_title="All water depths",
        note="Counts include all leases.",
    )
    svg = render_svg(trends, **args)
    csv_rows = [
        {key: "" if value is None else str(value) for key, value in row.items()}
        for row in reversed(trends)
    ]
    assert svg.encode() == render_svg(csv_rows, **args).encode()
    root = ET.fromstring(svg)
    (panel,) = root.findall("{*}g[@class='panel']")
    assert panel.findtext("{*}text") == args["panel_title"]
    words = [el.text for el in root.findall(".//{*}text")]
    assert [word for word in words if word in STATUS_NAMES] == STATUS_NAMES
    assert {"Yearly value", "5 year trailing moving average", "partial"} <= set(words)
    assert words[-2:] == [args["xlabel"], args["note"]]
    assert {el.tag.split("}")[-1] for el in root.iter()}.isdisjoint(
        {"clipPath", "pattern", "filter", "mask", "foreignObject", "image"}
    )
    assert not any(
        unicodedata.category(c) == "Pd" or c == "\u2212"
        for c in "".join(root.itertext())
    )
    assert all(float(el.get("font-size")) >= 15 for el in root.findall(".//{*}text"))
    title = next(el for el in root.findall("{*}text") if el.text == args["title"])
    assert float(title.get("font-size")) >= 18

    colours = ["#0072b2", "#d55e00", "#009e73", "#663399"]
    tints = ["#6badd2", "#e7a26b", "#6bc7ae", "#a689c4"]
    for kind, strokes, min_width in [("yearly", colours, 2), ("average", tints, 4)]:
        paths = panel.findall(f"{{*}}path[@class='{kind}']")
        assert [el.get("stroke") for el in paths] == strokes
        assert all(float(el.get("stroke-width")) >= min_width for el in paths)

    first_year_y = []
    for name, colour, tint in zip(STATUS_NAMES, colours, tints):
        entry = next(g for g in root.findall("{*}g") if g.findtext("{*}text") == name)
        assert [el.get("stroke") for el in entry.findall("{*}line")] == [colour, tint]
        markers = panel.findall(f"{{*}}circle[@stroke='{colour}']")
        assert [m.get("fill") for m in markers] == [colour] * 5 + ["white"]
        assert all(float(m.get("r")) >= 4.5 for m in markers)
        first_year_y.append(float(markers[0].get("cy")))
    # Counts of 1, 11, 21 and 31 occupy progressively higher points in the SVG.
    assert all(lower > higher for lower, higher in zip(first_year_y, first_year_y[1:]))


@pytest.mark.parametrize("render", [False, True])
def test_named_series_limit_applies_to_both_entry_points(render):
    names = [*STATUS_NAMES, "Active"]
    with pytest.raises(ValueError, match=r"chart-standard\.md item 6.*4"):
        if render:
            render_svg([], series_names=names, **CHART_LABELS)
        else:
            with_trend([], series_names=names)


def test_named_series_allow_rows_without_a_band_or_panel_title():
    rows = [dict(group="Other", year=2020, value=5)]
    trends = with_trend(rows, series_names=["Other"])
    svg = render_svg(trends, series_names=["Other"], **CHART_LABELS)
    assert len(ET.fromstring(svg).findall(".//{*}path[@class='yearly']")) == 1
    with pytest.raises(ValueError, match="dash"):
        render_svg(
            trends, series_names=["Other"], panel_title="All-depth", **CHART_LABELS
        )
    with pytest.raises(ValueError, match="unknown.*series"):
        with_trend(rows, series_names=["Expired"])
    with pytest.raises(ValueError, match="band"):
        with_trend(
            [dict(rows[0], band=b, year=2020 + i) for i, b in enumerate(BANDS)],
            series_names=["Other"],
        )
