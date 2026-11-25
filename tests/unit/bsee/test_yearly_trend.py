"""Calendar windows and portable SVG requirements for yearly well series charts."""

import unicodedata
from decimal import Decimal
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


def assert_article_sizes(root):
    scale = 860 / float(root.attrib["viewBox"].split()[2])

    def rendered(element, attribute):
        return float(element.attrib[attribute]) * scale

    title = root.findtext("{*}title")
    labels = root.findall(".//{*}text")
    assert title in {label.text for label in labels}
    for label in labels:
        assert rendered(label, "font-size") >= (18 if label.text == title else 15)
    for marker in root.findall(".//{*}circle"):
        assert 2 * rendered(marker, "r") >= 9

    panels = root.findall("{*}g[@class='panel']")
    plot_strokes = set()
    average_colours = set()
    for panel in panels:
        for path in panel.findall("{*}path"):
            average = path.attrib["class"] == "average"
            assert rendered(path, "stroke-width") >= (4 if average else 2)
            if average:
                average_colours.add(path.attrib["stroke"])
        for marker in panel.findall("{*}circle"):
            plot_strokes.add((marker.attrib["stroke"], marker.attrib["stroke-width"]))

    # Band keys are direct children of the root. Named keys are nested by series.
    legend = [el for child in root if child not in panels for el in child.iter()]
    markers = [el for el in legend if el.tag.endswith("}circle")]
    assert markers
    for marker in markers:
        assert marker.attrib["fill"] == marker.attrib["stroke"]
        assert (marker.attrib["stroke"], marker.attrib["stroke-width"]) in plot_strokes
    lines = [el for el in legend if el.tag.endswith("}line")]
    assert any(line.attrib["stroke"] in average_colours for line in lines)
    assert any(
        line.attrib["stroke"] in {colour for colour, _ in plot_strokes}
        for line in lines
    )
    for line in lines:
        minimum = 4 if line.attrib["stroke"] in average_colours else 2
        assert rendered(line, "stroke-width") >= minimum


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
    assert_article_sizes(root)
    panels = root.findall(".//{*}g[@class='panel']")
    assert len(panels) == 4
    for panel, colour in zip(panels, ("#6588a6", "#427298", "#245476", "#102e46")):
        lines = panel.findall("{*}path")
        assert len(lines) == 4
        yearly = [el for el in lines if el.get("class") == "yearly"]
        trend = [el for el in lines if el.get("class") == "average"]
        assert len(yearly) == len(trend) == 2
        assert all(el.get("stroke") == colour for el in yearly)
        assert all(el.get("stroke") != colour for el in trend)
        for pair in (yearly, trend):
            assert pair[0].get("stroke-dasharray") is None
            assert pair[1].get("stroke-dasharray")
        assert len(panel.findall("{*}circle[@fill='white']")) == 2


def test_depth_panels_share_one_calendar_axis_in_series_order():
    rows = [
        dict(year=year, band=band, value=1)
        for band in reversed(BANDS)
        for year in range(2005, 2013)
    ]
    root = ET.fromstring(
        render_svg(with_trend(rows, partial_year=2012), **CHART_LABELS)
    )
    panels = root.findall("{*}g[@class='panel']")
    labels = [p.find("{*}text") for p in panels]
    assert [label.text for label in labels] == list(BANDS)
    assert len({label.get("x") for label in labels}) == 1
    tops = [float(label.get("y")) for label in labels]
    assert all(a < b for a, b in zip(tops, tops[1:]))
    coordinates = [
        [float(marker.get("cx")) for marker in p.findall("{*}circle")] for p in panels
    ]
    assert len(coordinates[0]) == 8
    assert all(xs == coordinates[0] for xs in coordinates)
    for i, panel in enumerate(panels):
        words = [t.text for t in panel.findall("{*}text")]
        ticks = [int(word) for word in words if word.isdigit() and len(word) == 4]
        if i == 3:
            assert (ticks[0], ticks[-1]) == (2005, 2012)
            assert words.count("partial") == 1
        else:
            assert not ticks and "partial" not in words
        assert len(panel.findall("{*}circle[@fill='white']")) == 1


def test_depth_panels_require_a_separate_figure_above_four_lines():
    rows = [dict(group=g, year=2025, band=BANDS[0], value=2) for g in ("A", "B", "C")]
    with pytest.raises(ValueError, match="four lines per panel"):
        render_svg(with_trend(rows), **CHART_LABELS)


def test_absent_depth_band_keeps_its_row_without_fabricating_values():
    root = ET.fromstring(
        render_svg(
            with_trend([dict(year=2025, band=BANDS[0], value=2)]), **CHART_LABELS
        )
    )
    panels = root.findall("{*}g[@class='panel']")
    assert [p.findtext("{*}text") for p in panels] == list(BANDS)
    for panel in panels[1:]:
        assert not panel.findall("{*}circle")
        assert not panel.findall("{*}path")


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
    assert_article_sizes(root)

    colours = ["#0072b2", "#d55e00", "#009e73", "#663399"]
    tints = ["#6badd2", "#e7a26b", "#6bc7ae", "#a689c4"]
    for kind, strokes in [("yearly", colours), ("average", tints)]:
        paths = panel.findall(f"{{*}}path[@class='{kind}']")
        assert [el.get("stroke") for el in paths] == strokes

    first_year_y = []
    for name, colour, tint in zip(STATUS_NAMES, colours, tints):
        entry = next(g for g in root.findall("{*}g") if g.findtext("{*}text") == name)
        assert [el.get("stroke") for el in entry.findall("{*}line")] == [colour, tint]
        markers = panel.findall(f"{{*}}circle[@stroke='{colour}']")
        assert [m.get("fill") for m in markers] == [colour] * 5 + ["white"]
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


def vertical_ticks(panel):
    return [
        Decimal(label.text.replace(",", "").replace("(", "-").replace(")", ""))
        for label in panel.findall("{*}text[@text-anchor='end']")
    ]


@pytest.mark.parametrize(
    "values,peak_mean,expected",
    [
        ([1, 34, 0, None], 82, [0, 20, 40, 60, 80, 100]),
        ([0.03, None, 0.16, 0.01], None, [0, 0.05, 0.10, 0.15, 0.20]),
        ([0, None, 0, None], None, [0, 0.2, 0.4, 0.6, 0.8, 1]),
    ],
)
def test_depth_axis_covers_yearly_values_and_means_in_all_bands(
    values, peak_mean, expected
):
    rows = with_trend([dict(year=2020, band=b, value=v) for b, v in zip(BANDS, values)])
    rows[-1]["moving_average"] = peak_mean
    panels = ET.fromstring(render_svg(iter(rows), **CHART_LABELS)).findall(
        "{*}g[@class='panel']"
    )
    assert len(panels) == 4
    for panel in panels:
        assert vertical_ticks(panel) == [Decimal(str(t)) for t in expected]


def test_shared_depth_axis_preserves_signed_values():
    rows = with_trend(
        [dict(year=2020, band=b, value=v) for b, v in zip(BANDS, (-9, 4, 0, 1))]
    )
    panels = ET.fromstring(render_svg(rows, **CHART_LABELS)).findall(
        "{*}g[@class='panel']"
    )
    ticks = vertical_ticks(panels[0])
    assert 4 <= len(ticks) <= 6
    assert ticks[0] <= -9 and ticks[-1] >= 4 and 0 in ticks
    assert all(vertical_ticks(panel) == ticks for panel in panels)


def test_explicit_depth_scale_rejects_a_clipped_mean():
    from worldenergydata.bsee.yearly_trend import depth_y_scale

    rows = with_trend([dict(year=2020, band=BANDS[0], value=10)])
    scale = depth_y_scale(rows)
    rows[0]["moving_average"] = 11
    with pytest.raises(ValueError, match="cover"):
        render_svg(rows, **CHART_LABELS, y_scale=scale)


def test_same_measure_sharing_selects_members_at_30_percent_of_the_nice_maximum():
    from worldenergydata.bsee.yearly_trend import shared_depth_y_scales

    figures = {
        "below": [dict(value=29, moving_average=None)],
        "boundary": [dict(value=1, moving_average=30)],
        "above": [dict(value=31, moving_average=None)],
        "largest": [dict(value=67, moving_average=60)],
        "empty": [dict(value=None, moving_average=None)],
    }
    ticks = (0, 20, 40, 60, 80, 100)
    assert shared_depth_y_scales(figures) == dict.fromkeys(
        ("boundary", "above", "largest"), ticks
    )
    assert shared_depth_y_scales({k: figures[k] for k in ("below", "largest")}) == {}
