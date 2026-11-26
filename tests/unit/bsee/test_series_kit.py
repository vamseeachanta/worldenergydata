"""Series-kit rules checked with independent annual values and rendered artifacts."""

import csv
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import pytest

from worldenergydata.bsee.series import BAND_COLORS, BANDS, depth_band, with_trends
from worldenergydata.bsee.series.charts import (
    assign_scales,
    make_figure,
    scale,
    write_figures,
)


def test_calendar_windows_count_zero_and_recover_after_a_gap():
    # 2018 has no row. The first full window after it is 2019 through 2023.
    annual = {
        2011: 0,
        2012: 2,
        2013: 4,
        2014: 6,
        2015: 8,
        2016: None,
        2017: 10,
        2019: 10,
        2020: 8,
        2021: 6,
        2022: 4,
        2023: 2,
        2024: 80,
    }
    rows = [
        dict(group="rate", year=y, value=v, partial=int(y == 2024))
        for y, v in reversed(annual.items())
    ]
    rows += [dict(group="other", year=y, value=5, partial=0) for y in range(2011, 2016)]
    result = with_trends(rows).set_index(["group", "year"])
    means = result.loc["rate", "moving_average"]
    assert means.dropna().to_dict() == {2015: 4, 2023: 6}
    assert result.loc[("other", 2015), "moving_average"] == 5
    assert pd.isna(result.loc[("rate", 2016), "value"])
    assert result.loc[("rate", 2024), "value"] == 80


def test_missing_value_suppresses_exactly_its_five_windows():
    values = [1, 1, 1, 1, 1, None, 2, 2, 2, 2, 2]
    result = with_trends(
        [dict(group="count", year=2000 + i, value=v) for i, v in enumerate(values)]
    )
    assert result.set_index("year").moving_average.dropna().to_dict() == {
        2004: 1,
        2010: 2,
    }


def test_depth_band_uses_inclusive_lower_bound_and_series_palette():
    bands = ("Under 100 m", "100 to 500 m", "500 to 1,500 m", "1,500 m and deeper")
    assert tuple(BANDS) == bands
    assert [BAND_COLORS[b] for b in bands] == [
        "#6588a6",
        "#427298",
        "#245476",
        "#102e46",
    ]
    depths = [0, 99.999, 100, 499.999, 500, 1499.999, 1500, 4000]
    assert [depth_band(d) for d in depths] == [b for b in bands for _ in range(2)]


@pytest.fixture
def completion_figure(tmp_path):
    group = "count|All water depths"
    # The source marks 2017 unavailable and supplies no row at all for 2023.
    rows = [dict(group=group, year=2017, value=50, availability="unavailable")]
    rows += [
        dict(group=group, year=year, value=value)
        for year, value in enumerate([0, 1, 2, 3, 4], 2018)
    ]
    rows.append(dict(group=group, year=2024, value=15, partial=0))
    annual = with_trends(rows, partial_year="2024")
    figure = make_figure(
        "1A",
        "Well completions",
        "Count (completions per year)",
        "count",
        [(group, "Completions")],
        "The 2024 data end on 30 September.",
    )
    write_figures(
        tmp_path,
        [figure],
        annual.to_dict("records"),
        xlabel="Completion year",
        partial_label="partial through September",
        previous=("Permitting and drilling", "../drilling.html"),
        next_part=("Production", "../production.html"),
    )
    return tmp_path


def test_interactive_values_and_gaps_match_svg(completion_figure):
    svg = (completion_figure / "figure-1a.svg").read_text(encoding="utf-8")
    page = (completion_figure / "figure-1a.html").read_text(encoding="utf-8")
    assert svg.strip() in page
    assert "Completion year" in svg and "Completion year<select" in page
    assert "30 September" in svg
    assert "partial through September" in svg and "partial through September" in page
    with (completion_figure / "annual_trends.csv").open(
        encoding="utf-8", newline=""
    ) as f:
        table = {int(row["year"]): row for row in csv.DictReader(f)}
    assert table[2017]["value"] == table[2017]["moving_average"] == ""
    assert table[2024]["partial"] == "1" and table[2024]["moving_average"] == ""
    assert 'href="../drilling.html"' in page and "Permitting and drilling" in page
    assert 'href="../production.html"' in page and "Production" in page
    (series,) = json.loads(re.search(r"^const series = (.+);$", page, re.M).group(1))
    assert [row[0] for row in series] == list(range(2017, 2025))
    assert [row[1] for row in series] == [None, 0, 1, 2, 3, 4, None, 15]
    assert [row[2] for row in series] == [None, None, None, None, None, 2, None, None]
    assert series[0][4] == series[-2][4] == "unavailable"
    assert [row[0] for row in series if row[3]] == [2024]
    root = ET.fromstring(svg)
    dots = {int(dot.get("data-year")): dot for dot in root.findall(".//{*}circle")}
    # The single legend row leaves a 275 px plot from y=420 to y=145.
    assert set(dots) == {2018, 2019, 2020, 2021, 2022, 2024}
    ticks = root.findall("{*}text[@text-anchor='end']")
    assert [t.text for t in ticks] == [
        "0",
        "5",
        "10",
        "15",
        "partial through September",
    ]
    for year, expected_y in {
        2018: 420,
        2019: 401.67,
        2020: 383.33,
        2021: 365,
        2022: 346.67,
        2024: 145,
    }.items():
        dot = dots[year]
        assert float(dot.get("cy")) == pytest.approx(expected_y, abs=0.005)
        _, value, mean, partial, *_ = series[year - 2017]
        title = dot.findtext("{*}title")
        assert f"Annual value {value:g}." in title
        expected = "unavailable" if mean is None else f"{mean:g}"
        assert f"Five year mean {expected}." in title
        assert (dot.get("fill") == "white") == partial
    assert root.find(".//{*}path[@class='annual']").get("d").count("M") == 2


def test_svg_passes_overlay_checker(paired_figures):
    relative = Path("fleet-ops/intake/well-series/check_chart_standard.py")
    configured = os.environ.get("BSEE_CHART_CHECKER")
    if configured:
        checker = Path(configured)
    else:
        checker = next(
            (
                p / relative
                for p in Path(__file__).resolve().parents
                if (p / relative).is_file()
            ),
            None,
        )
        if checker is None:
            pytest.skip("Set BSEE_CHART_CHECKER to run the fleet-ops overlay checker")
    manifest = paired_figures / "figures.json"
    assert len(json.loads(manifest.read_text(encoding="utf-8"))) == 2
    result = subprocess.run(
        [sys.executable, "-I", str(checker), "--require-overlay", str(manifest)],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "(2 figures)" in result.stdout


@pytest.mark.parametrize(
    ("annual", "mean"),
    [
        ([(2018, 2), (2019, 2), (2021, 2), (2022, 2)], 2),
        ([(2018, 2), (2019, 2), (2020, None), (2021, 2), (2022, 2)], 2),
        ([(2018, 0), (2019, 1), (2020, 2), (2021, 3), (2022, 4)], 3),
    ],
    ids=["omitted-year", "blank-value", "wrong-mean"],
)
def test_csv_replay_rejects_invalid_trailing_mean(tmp_path, annual, mean):
    # The last case has five observed years with true mean (0+1+2+3+4)/5 = 2.
    csv_path = tmp_path / "annual_trends.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("group", "year", "value", "moving_average"))
        writer.writerows(("events", y, v, mean if y == 2022 else "") for y, v in annual)
    figure = make_figure(
        "1",
        "Annual completions",
        "Completions per year",
        "completions",
        [("events", "Completions")],
        "Completion year.",
    )
    with pytest.raises(ValueError, match="moving_average.*events.*2022"):
        write_figures(tmp_path, [figure], xlabel="Completion year")


@pytest.mark.parametrize(
    ("peak", "top", "step"),
    [
        (21.69, 25, 5),
        (579, 600, 200),
        (6.92, 8, 2),
        (1.42, 1.5, 0.5),
        (7.69, 8, 2),
        (29, 30, 10),
        (0, 1, 0.2),
    ],
)
def test_smallest_covering_scale(peak, top, step):
    assert scale(peak) == (top, step)


@pytest.mark.parametrize(
    ("second", "shared", "second_top"),
    [(7.5, True, 25), (7.4999, False, 8)],
)
def test_pooling_uses_thirty_percent_of_rounded_top(second, shared, second_top):
    figs = [
        make_figure(key, key, "Share (%)", "share", [(key, key)], "")
        for key in ("A", "B")
    ]
    assign_scales(figs, {"A": 21.69, "B": second})
    assert [f["y_scale"]["max"] for f in figs] == [25, second_top]
    expected = "measure:share" if shared else "panels"
    assert [f["y_scale"]["shared"] for f in figs] == [expected, expected]


@pytest.fixture
def paired_figures(tmp_path):
    # The partial-year peak sets the pooled top to 25. The depth peak of 7.5
    # lands exactly on its sharing threshold. Only one annual cell is blank.
    groups = ["observed", "within", *BANDS]
    rows = [dict(group=g, year=y, value=7.5) for g in groups for y in range(2020, 2026)]
    for row in rows:
        if (row["group"], row["year"]) == ("within", 2021):
            row["value"] = None
        if (row["group"], row["year"]) == ("observed", 2025):
            row["value"] = 21.69
    annual = with_trends(rows, partial_year=2025)
    figures = [
        make_figure(
            "1A",
            "Event shares",
            "Share (%)",
            "share",
            [("observed", "Observed by file date"), ("within", "Within five years")],
            "The dashed line uses the shorter window",
            window_definitions={
                "observed": "through October 2025",
                "within": "through the fifth anniversary",
            },
        ),
        make_figure(
            "1B",
            "Shares by depth",
            "Share (%)",
            "share",
            [(b, b) for b in BANDS],
            "The 2025 record ends in October.",
            by_depth=True,
        ),
    ]
    write_figures(
        tmp_path,
        figures,
        annual.to_dict("records"),
        xlabel="Event year",
        partial_label="Partial through October",
    )
    return tmp_path


def test_paired_windows_match_rendered_styles_and_selected_blanks(paired_figures):
    first, depth = json.loads(
        (paired_figures / "figures.json").read_text(encoding="utf-8")
    )
    assert first["blank_cells"] == ["2021 Within five years"]
    assert depth["blank_cells"] == []
    assert "windows" not in depth
    assert first["windows"] == {
        "solid": {
            "label": "Observed by file date",
            "definition": "through October 2025",
        },
        "dashed": {
            "label": "Within five years",
            "definition": "through the fifth anniversary",
        },
    }
    for entry in (first, depth):
        assert entry["y_scale"] == {"max": 25, "step": 5, "shared": "measure:share"}
    svg = ET.parse(paired_figures / first["svg"])
    visible = " ".join(n.text or "" for n in svg.findall(".//{*}text"))
    for phrase in (
        "2021 Within five years",
        "through October 2025",
        "through the fifth anniversary",
    ):
        assert phrase in first["caption"] and phrase in visible
    groups = svg.findall(".//{*}g[@data-series]")
    assert [g.get("data-label") for g in groups] == [
        "Observed by file date",
        "Within five years",
    ]
    # Only the full record has five complete consecutive years for a trend.
    paths = [g.findall("{*}path") for g in groups]
    assert [len(p) for p in paths] == [2, 1]
    for group_paths, dashed in zip(paths, (False, True)):
        assert all(("stroke-dasharray" in p.attrib) == dashed for p in group_paths)
    assert first["caption"].startswith(
        "The dashed line uses the shorter window. Observed by file date (solid)"
    )


@pytest.mark.parametrize(("value", "blanks"), [(None, ["2022 Count"]), (0, [])])
def test_blank_declaration_follows_annual_value(tmp_path, value, blanks):
    rows = [
        dict(group="count", year=2022, value=value),
        dict(group="elsewhere", year=2022, value=None),
    ]
    figure = make_figure(
        "1", "Annual event count", "Events", "events", [("count", "Count")], ""
    )
    write_figures(
        tmp_path, [figure], with_trends(rows).to_dict("records"), xlabel="Event year"
    )
    (entry,) = json.loads((tmp_path / "figures.json").read_text(encoding="utf-8"))
    assert entry["blank_cells"] == blanks


def test_coordinate_precision_applies_only_to_geometry(tmp_path):
    # Chart height is 275 px above baseline 420; 1.010001 on a 0..3 scale
    # plots at 327.416575 px. Paths and circles must agree at the chosen precision.
    rows = [
        dict(group="g", year=2020, value=1.010001),
        dict(group="g", year=2021, value=2.9),
    ]
    fig = make_figure(
        "1", "Annual event share", "Share (%)", "share", [("g", "Share")], ""
    )
    write_figures(
        tmp_path,
        [fig],
        with_trends(rows).to_dict("records"),
        xlabel="Year",
        coordinate_decimals=1,
    )
    svg = ET.parse(tmp_path / "figure-1.svg")
    assert float(svg.find(".//{*}circle").get("cy")) == 327.4
    assert "327.4" in svg.find(".//{*}path[@class='annual']").get("d")
    html = (tmp_path / "figure-1.html").read_text(encoding="utf-8")
    assert (
        json.loads(re.search(r"^const series = (.+);$", html, re.M)[1])[0][0][1]
        == 1.010001
    )


def test_window_style_conflict_is_rejected(tmp_path):
    rows = [dict(group=g, year=2025, value=1) for g in ("a", "b")]
    fig = make_figure(
        "1",
        "Timing",
        "Count",
        "count",
        [("a", "Full record"), ("b", "First year")],
        "Observed in 2025.",
        window_definitions={"a": "through 2025", "b": "within one year"},
    )
    with pytest.raises(ValueError, match="Solid window"):
        write_figures(
            tmp_path,
            [fig],
            with_trends(rows).to_dict("records"),
            xlabel="Year",
            dashed_groups=["a"],
        )


def test_svg_bytes_ignore_subpixel_noise(tmp_path):
    fig = make_figure("1", "Annual counts", "Events", "count", [("g", "Count")], "")
    for name, value in (("a", 0.3), ("b", 0.1 + 0.2)):
        rows = [
            dict(group="g", year=2020, value=value),
            dict(group="g", year=2021, value=1),
        ]
        write_figures(
            tmp_path / name, [fig], with_trends(rows).to_dict("records"), xlabel="Year"
        )
    assert (tmp_path / "a/figure-1.svg").read_bytes() == (
        tmp_path / "b/figure-1.svg"
    ).read_bytes()
    with (tmp_path / "b/annual_trends.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        assert next(csv.DictReader(stream))["value"] == "0.30000000000000004"


@pytest.mark.parametrize(
    ("high", "peer", "maxima"),
    [("25.000000000000001", "1", [30, 1]), ("21.69", "7.4999999999999999", [25, 8])],
)
def test_csv_decimal_precision_at_scale_and_pool_boundaries(
    tmp_path, high, peer, maxima
):
    # Both strings round onto a decision boundary in binary64. The first case
    # needs the next covering top; the second peer falls below 30% of 25.
    (tmp_path / "annual_trends.csv").write_text(
        f"group,year,value,moving_average\na,2024,{high},\nb,2024,{peer},\n",
        encoding="utf-8",
    )
    figs = [
        make_figure(
            key, f"Share for cohort {key}", "Share (%)", "share", [(key, key)], ""
        )
        for key in ("a", "b")
    ]
    write_figures(tmp_path, figs, xlabel="Year")
    manifest = json.loads((tmp_path / "figures.json").read_text(encoding="utf-8"))
    assert [entry["y_scale"]["max"] for entry in manifest] == maxima
    assert all(entry["y_scale"]["shared"] == "panels" for entry in manifest)


@pytest.mark.parametrize(
    ("value", "display", "axis_top"),
    [
        (0.00005, "0.00005", "0.00005"),
        (0.5, "0.5", "0.5"),
        (12345.6, "12,345.6", "15,000"),
        (1234567, "1,234,567", "1,500,000"),
        (-0.0, "0", "1"),
    ],
)
def test_fixed_point_labels_and_readout(tmp_path, value, display, axis_top):
    rows = [dict(group="g", year=y, value=value) for y in range(2020, 2025)]
    fig = make_figure("1", "Annual event rate", "Events", "rate", [("g", "Rate")], "")
    write_figures(tmp_path, [fig], with_trends(rows).to_dict("records"), xlabel="Year")
    svg = ET.parse(tmp_path / "figure-1.svg")
    texts = svg.findall(".//{*}text") + svg.findall(".//{*}title")
    assert all(
        unicodedata.category(c) != "Pd" and c != "\N{MINUS SIGN}"
        for t in texts
        for chunk in t.itertext()
        for c in chunk
    )
    assert svg.findall(".//{*}text[@text-anchor='end']")[-1].text == axis_top
    assert svg.findtext(".//{*}circle[@data-year='2024']/{*}title") == (
        f"Rate, 2024. Annual value {display}. Five year mean {display}."
    )
    page = (tmp_path / "figure-1.html").read_text(encoding="utf-8")
    (series,) = json.loads(re.search(r"^const series = (.+);$", page, re.M)[1])
    assert series[0][5:] == [display, None]
    assert series[-1][5:] == [display, display]


@pytest.mark.parametrize(
    ("peaks", "expected"),
    [
        (
            (100, 35, 10),
            [
                (
                    100,
                    20,
                    "measure:share",
                    "Y maximum 100, against 100 in Figure B, 10 in Figure C.",
                ),
                (
                    100,
                    20,
                    "measure:share",
                    "Y maximum 100, against 100 in Figure A, 10 in Figure C.",
                ),
                (
                    10,
                    2,
                    "panels",
                    "Y maximum 10, against 100 in Figure A, 100 in Figure B.",
                ),
            ],
        ),
        (
            (100, 25, 20),
            [
                (
                    100,
                    20,
                    "panels",
                    "Y maximum 100, against 25 in Figure B, 20 in Figure C.",
                ),
                (
                    25,
                    5,
                    "panels",
                    "Y maximum 25, against 100 in Figure A, 20 in Figure C.",
                ),
                (
                    20,
                    5,
                    "panels",
                    "Y maximum 20, against 100 in Figure A, 25 in Figure B.",
                ),
            ],
        ),
    ],
)
def test_three_figure_scales_and_notes(peaks, expected):
    figs = [make_figure(k, k, "Share (%)", "share", [(k, k)], "") for k in "ABC"]
    assign_scales(figs, dict(zip("ABC", peaks)))
    for fig, (top, step, scope, note) in zip(figs, expected):
        assert fig["y_scale"] == {"max": top, "step": step, "shared": scope}
        assert fig["scale_note"] == note


@pytest.mark.parametrize("measure", ["", "  ", None])
def test_figure_rejects_missing_measure(measure):
    with pytest.raises(ValueError, match="measure"):
        make_figure("1", "Count", "Events", measure, [("g", "Count")], "")


@pytest.mark.parametrize("measure", ["", "  ", None])
def test_assign_scales_rejects_missing_measure(measure):
    # Lower-level callers may supply their own figure dictionaries.
    with pytest.raises(ValueError, match="measure"):
        assign_scales([{"measure": measure, "groups": ["g"]}], {"g": 1})


def test_mixed_axes_and_empty_cohorts_with_static_depth_panels(tmp_path):
    # The appendix peak of 79 requires four intervals of 20, shared with the
    # main peak of 30. Omitted source cells and zero wells have distinct causes.
    main = make_figure("1", "Cohort", "Share (%)", "share", [("all", "All")], "")
    main.update(
        xlabel="First spud year", empty_denominator_label="No wells first drilled"
    )
    panels = make_figure(
        "E", "Rates by band", "Share (%)", "share", [(b, "Rate") for b in BANDS], ""
    )
    panels.update(role="appendix", panel_by="depth_band", layout="4x1_shared_x")
    del panels["interactive"]
    rows = [
        dict(group="all", year=2020, value=30),
        dict(
            group="all",
            year=2021,
            value=None,
            availability="unavailable",
            denominator=0,
        ),
        dict(group="all", year=2022, value=None, availability="unavailable"),
    ]
    for band in BANDS:
        for year in range(2020, 2023):
            if not (band == BANDS[0] and year == 2021):
                rows.append(dict(group=band, band=band, year=year, value=79))
    write_figures(
        tmp_path,
        [main, panels],
        with_trends(rows).to_dict("records"),
        xlabel="Approval year",
    )
    main, panels = json.loads((tmp_path / "figures.json").read_bytes())
    assert (
        main["y_scale"]
        == panels["y_scale"]
        == {"max": 80, "step": 20, "shared": "measure:share"}
    )
    page = (tmp_path / main["interactive"]).read_text(encoding="utf-8")
    series = json.loads(re.search(r"^const series = (.+);$", page, re.M)[1])[0]
    assert "First spud year" in page
    assert series[1][1] is None and series[1][5] == "No wells first drilled"
    assert series[2][5] is None
    assert "zero denominator" in main["coverage_note"]
    assert "Source records are unavailable for 1" in main["coverage_note"]
    assert panels["blank_cells"] == [f"2021 Rate ({BANDS[0]})"]
    svg = ET.parse(tmp_path / panels["svg"])
    assert len(svg.findall(".//{*}g[@class='panel']")) == 4
    assert "Approval year" in " ".join(svg.getroot().itertext())
    assert not (tmp_path / "figure-e.html").exists()
