"""Public chart contract for the well series."""

import csv
import io
import unicodedata
from xml.etree import ElementTree as ET

import pytest

from worldenergydata.bsee.half_decade import depth_band, render_svg, summarize

BANDS = ["Under 100 m", "100 to 500 m", "500 to 1,500 m", "1,500 m and deeper"]
PERIODS = [
    "2005 to 2009",
    "2010 to 2014",
    "2015 to 2019",
    "2020 to 2024",
    "2025 to 2026 (partial)",
]


@pytest.mark.parametrize(
    "metres,index",
    [(0, 0), (99.99, 0), (100, 1), (499.99, 1), (500, 2), (1499.99, 2), (1500, 3)],
)
def test_lower_depth_boundary_is_inclusive(metres, index):
    assert depth_band(metres) == BANDS[index]


def test_missing_depth_does_not_become_shallow():
    for depth in [None, -1, float("nan"), float("inf")]:
        with pytest.raises(ValueError):
            depth_band(depth)


def test_inclusive_years_and_empty_bands():
    years = [2004, 2005, 2009, 2010, 2014, 2015, 2019, 2020, 2024, 2025, 2026, 2027]
    rows = [
        {"year": year, "band": "under 100 m", "count": 2**i}
        for i, year in enumerate(years)
    ]
    table = summarize(rows)
    assert len(table) == 20
    assert list(dict.fromkeys(r["band"] for r in table)) == BANDS
    counts = [r for r in table if r["band"] == BANDS[0]]
    assert [r["period"] for r in counts] == PERIODS
    assert [r["count"] for r in counts] == [6, 24, 96, 384, 1536]
    assert [r["value"] for r in counts] == [6, 24, 96, 384, 1536]
    assert all(r["value"] == 0 for r in table if r["band"] != BANDS[0])


def test_nominal_calendar_years_and_partial_period():
    rows = [
        {"year": year, "group": group, "band": "500 to 1500 m", "value": 20}
        for year in [2024, 2025]
        for group in ["Initial", "Other"]
    ]
    table = summarize(rows, mode="per_year")
    assert len(table) == 40
    part = [r for r in table if r["group"] == "Other" and r["count"]]
    assert [(r["period"], r["band"], r["years"], r["value"]) for r in part] == [
        (PERIODS[3], BANDS[2], 5, 4),
        (PERIODS[4], BANDS[2], 2, 10),
    ]


def test_rates_pool_exposure_and_distinguish_no_wells_from_no_approvals():
    rows = [
        {"year": 2025, "band": BANDS[0], "count": 2, "exposure": 5},
        {"year": 2026, "band": BANDS[0], "count": 0, "exposure": 15},
        {"year": 2025, "band": BANDS[1], "count": 0, "exposure": 10},
    ]
    table = summarize(rows, mode="per_well")
    last = [r for r in table if r["period"] == PERIODS[4]]
    assert [(r["count"], r["exposure"], r["value"]) for r in last] == [
        (2, 20, 0.1),
        (0, 10, 0),
        (0, 0, None),
        (0, 0, None),
    ]
    with pytest.raises(ValueError, match="exposure"):
        summarize([{"year": 2025, "band": BANDS[0], "count": 2}], mode="per_well")


def test_unknown_band_cannot_disappear_from_totals():
    with pytest.raises(ValueError, match="band"):
        summarize([{"year": 2026, "band": "no depth", "count": 1}])


def test_svg_is_deterministic_portable_and_labels_every_band():
    table = summarize([{"year": 2010, "band": BANDS[1], "count": 4, "group": "A & B"}])
    svg = render_svg(table, ylabel="Approvals (count)", note="Through 23 November 2026")
    assert svg == render_svg(
        table, ylabel="Approvals (count)", note="Through 23 November 2026"
    )
    root = ET.fromstring(svg)
    tags = {e.tag.rsplit("}", 1)[-1] for e in root.iter()}
    assert tags.isdisjoint(
        {"clipPath", "pattern", "filter", "mask", "foreignObject", "image"}
    )
    visible = " ".join(root.itertext())
    assert all(
        unicodedata.category(char) != "Pd" and char != "\u2212" for char in visible
    )
    assert "'DejaVu Sans','Segoe UI',Arial,sans-serif" in svg
    for label in [*BANDS, *PERIODS, "A & B", "Approval period", "Approvals (count)"]:
        assert label in visible
    for color in ["#6588a6", "#427298", "#245476", "#102e46"]:
        assert color in svg


def test_svg_rejects_dash_in_user_label():
    with pytest.raises(ValueError, match="dash"):
        render_svg(summarize([]), ylabel="Per-well rate")


def test_undefined_rate_survives_csv_round_trip():
    table = summarize(
        [{"year": 2015, "band": BANDS[0], "count": 1, "exposure": 10}],
        mode="per_well",
    )
    stream = io.StringIO()
    writer = csv.DictWriter(stream, table[0].keys())
    writer.writeheader()
    writer.writerows(table)
    stream.seek(0)
    label = "Approvals per standing well year"
    assert render_svg(csv.DictReader(stream), ylabel=label) == render_svg(
        table, ylabel=label
    )


def test_axis_spans_a_maximum_close_to_the_next_power_of_ten():
    table = summarize([{"year": 2015, "band": BANDS[1], "count": 97}])
    labels = ET.fromstring(render_svg(table, ylabel="Approvals (count)")).itertext()
    assert "100" in labels


def test_each_group_has_a_zero_based_scale_for_its_own_values():
    table = summarize(
        [
            {"year": 2010, "band": BANDS[0], "group": "Large", "count": 560},
            {"year": 2010, "band": BANDS[0], "group": "Small", "count": 34},
        ]
    )
    root = ET.fromstring(render_svg(table, ylabel="Approvals (count)"))
    labels = [t.text for t in root.findall(".//{*}text")]
    split = labels.index("Small")
    large_ticks = [int(t) for t in labels[labels.index("Large") : split] if t.isdigit()]
    small_ticks = [int(t) for t in labels[split:] if t.isdigit()]
    assert min(large_ticks) == min(small_ticks) == 0
    assert max(small_ticks) == 40 and max(large_ticks) == 600


def test_mature_periods_and_distinct_panel_units():
    table = summarize(
        [
            {"year": 2005, "band": BANDS[0], "group": g, "count": 3}
            for g in ("Incidence", "Timing")
        ]
    )
    mature = [row for row in table if row["period"] in PERIODS[:3]]
    options = dict(
        ylabel="First crude oil",
        periods=PERIODS[:3],
        panel_ylabels={"Incidence": "Share (%)", "Timing": "Median (years)"},
    )
    labels = set(ET.fromstring(render_svg(mature, **options)).itertext())
    assert {"Share (%)", "Median (years)", *PERIODS[:3]} <= labels
    assert labels.isdisjoint(PERIODS[3:])
    with pytest.raises(ValueError):
        render_svg(mature[1:], **options)
