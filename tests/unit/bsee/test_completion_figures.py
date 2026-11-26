"""Check the figure files that feed the completion article."""

import csv
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

import pytest

OUTPUT = (
    Path(__file__).resolve().parents[3] / "examples/bsee/completions_by_depth/output"
)


def test_figure_manifest_links_bullets_to_plotted_cells():
    figures = json.loads((OUTPUT / "figures.json").read_text(encoding="utf-8"))
    assert [f["svg"] for f in figures] == [
        "01_approvals_by_period.svg",
        "02_recompletion_by_period.svg",
        "03_perforation_flags.svg",
        "04_drilled_to_completed.svg",
        "03_approvals_per_well.svg",
    ]
    assert len({f["question"] for f in figures}) == 5
    for figure in figures:
        svg = ET.parse(OUTPUT / figure["svg"])
        assert figure["layout"] == "4x1_shared_x"
        assert figure["question"].endswith("?")
        assert (figure["view"], figure["x_unit"], figure["trend"]) == (
            "yearly",
            "year",
            "moving_average_5y_trailing",
        )
        assert 2 <= len(figure["bullets"]) <= 4
        with (OUTPUT / figure["csv"]).open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        for bullet in figure["bullets"]:
            assert "approval" in bullet["text"].lower()
            assert bullet["cells"]
            for cell in bullet["cells"]:
                matching = [
                    row
                    for row in rows
                    if all(row[key] == value for key, value in cell["row"].items())
                ]
                assert len(matching) == 1
                value = float(matching[0][cell["column"]])
                reading = re.escape(f'{value:,.{cell["decimals"]}f}')
                assert re.search(rf"(?<![\d.,]){reading}(?!\d|[.,]\d)", bullet["text"])
        assert not re.search(
            r"[-\u2010-\u2015\u2212]", "".join(svg.getroot().itertext())
        )


def test_drilled_figure_shows_first_drilling_periods_and_follow_up():
    with (OUTPUT / "figures.json").open(encoding="utf-8") as stream:
        drilled = json.load(stream)[3]
    assert drilled["csv"] == "04_drilled_to_completed.csv"
    assert "first drill" in drilled["question"].lower()
    assert "2026" in drilled["note"]
    assert "less time" in drilled["note"]
    root = ET.parse(OUTPUT / "04_drilled_to_completed.svg").getroot()
    text = [element.text for element in root.findall(".//{*}text")]
    assert text.index("Exploratory wells") < text.index("Development wells")
    assert "Share of drilled wells (%)" in text
    assert "Year of first drilling" in text
    for label in (
        "2005",
        "2026",
        "Under 100 m",
        "100 to 500 m",
        "500 to 1,500 m",
        "1,500 m and deeper",
    ):
        assert label in text
    assert "less time" in " ".join(text)
    tags = {el.tag.rsplit("}", 1)[-1] for el in root.iter()}
    assert tags.isdisjoint(
        {"clipPath", "pattern", "filter", "mask", "foreignObject", "image"}
    )


def test_drilled_year_bullets_quote_the_counts_behind_each_share():
    figure = json.loads((OUTPUT / "figures.json").read_text())[3]
    with (OUTPUT / figure["csv"]).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {
        (year, group)
        for year in ("2025", "2026")
        for group in ("Exploratory wells", "Development wells")
    }
    observed = []
    for bullet in figure["bullets"]:
        for cell in bullet["cells"]:
            if cell["column"] != "value":
                continue
            observed.append((cell["row"]["year"], cell["row"]["group"]))
            row = next(
                r for r in rows if all(r[k] == v for k, v in cell["row"].items())
            )
            for field in ("with_initial_completion_approval", "wells_first_drilled"):
                assert any(
                    ref["column"] == field and ref["row"] == cell["row"]
                    for ref in bullet["cells"]
                )
            assert (
                f"{row['with_initial_completion_approval']} of {row['wells_first_drilled']}"
                in bullet["text"]
            )
    assert len(observed) == len(expected) and set(observed) == expected


def test_body_figures_have_distinct_accessible_names():
    figures = json.loads((OUTPUT / "figures.json").read_text(encoding="utf-8"))
    names = [
        ET.parse(OUTPUT / f["svg"]).getroot().attrib["aria-label"] for f in figures
    ]
    assert len(set(names)) == len(figures)


def test_every_delivered_average_uses_five_complete_annual_values():
    figures = json.loads((OUTPUT / "figures.json").read_text())
    for figure in figures:
        with (OUTPUT / figure["csv"]).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        cells = {(r["group"], r["band"], int(r["year"])): r for r in rows}
        assert len(cells) == len(rows)
        for (group, band, year), row in cells.items():
            assert (row["partial_year"] == "True") == (year == 2026)
            window = [
                cells.get((group, band, y), {}).get("value")
                for y in range(year - 4, year + 1)
            ]
            if year == 2026 or any(v in ("", None) for v in window):
                assert row["moving_average"] == ""
            else:
                assert (
                    abs(float(row["moving_average"]) - sum(map(float, window)) / 5)
                    < 1e-12
                )


def test_approvals_per_standing_well_is_the_appendix_figure():
    figures = json.loads((OUTPUT / "figures.json").read_text())
    assert [f["csv"] for f in figures if f.get("role") == "appendix"] == [
        "03_approvals_per_well.csv"
    ]


def test_split_charts_use_exact_original_series():
    from worldenergydata.bsee.yearly_trend import render_svg

    figures = json.loads((OUTPUT / "figures.json").read_text())
    csv_name = "02_recompletion_by_period.csv"
    with (OUTPUT / csv_name).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    split = [f for f in figures if f["csv"] == csv_name]
    groups = [["Recompletion"], ["Modify Perforations", "Reperforation"]]
    assert [f["groups"] for f in split] == groups
    assert set(row["group"] for row in rows) == set(groups[0] + groups[1])
    for figure, selected in zip(split, groups):
        actual = (OUTPUT / figure["svg"]).read_text()
        expected = render_svg(
            [row for row in rows if row["group"] in selected],
            title=ET.fromstring(actual).findtext("{*}title"),
            ylabel="Approved permits per year",
            xlabel="Calendar year of approval",
            note=figure["note"],
        )
        assert actual == expected
        for bullet in figure["bullets"]:
            assert all(cell["row"]["group"] in selected for cell in bullet["cells"])


def test_all_completion_charts_meet_article_width_minimums():
    figures = json.loads((OUTPUT / "figures.json").read_text())
    files = [f["svg"] for f in figures]
    files.extend(["02_bores_first_completed.svg", "03_fluid_by_year.svg"])
    for name in files:
        root = ET.parse(OUTPUT / name).getroot()
        scale = 860 / float(root.get("viewBox").split()[2])
        for label in root.findall(".//{*}text"):
            minimum = 18 if label.text == root.findtext("{*}title") else 15
            assert scale * float(label.get("font-size")) >= minimum, name
        for marker in root.findall(".//{*}circle"):
            assert 2 * scale * float(marker.get("r")) >= 9, name
        for line in root.findall(".//{*}path"):
            minimum = 4 if line.get("class") == "average" else 2
            assert scale * float(line.get("stroke-width")) >= minimum, name


@pytest.mark.parametrize("index", range(5))
def test_delivered_axes_match_manifest_and_cover_every_plotted_cell(index):
    figure = json.loads((OUTPUT / "figures.json").read_text())[index]
    scale = figure["y_scale"]
    top, step = (Decimal(str(scale[key])) for key in ("max", "step"))
    for x in (top, step):
        assert x > 0 and x.scaleb(-x.adjusted()) in (1, 2, 5)
    expected = [i * step for i in range(int(top / step) + 1)]
    assert expected[-1] == top and 4 <= len(expected) <= 6
    panels = ET.parse(OUTPUT / figure["svg"]).findall(".//{*}g[@class='panel']")
    assert len(panels) == 4
    for panel in panels:
        assert [
            Decimal(t.text.replace(",", ""))
            for t in panel.findall("{*}text[@text-anchor='end']")
        ] == expected
    with (OUTPUT / figure["csv"]).open(newline="") as stream:
        for row in csv.DictReader(stream):
            if "groups" in figure and row["group"] not in figure["groups"]:
                continue
            for key in ("value", "moving_average"):
                if row[key]:
                    assert 0 <= Decimal(row[key]) <= top


def test_only_initial_approvals_and_recompletions_share_the_permit_scale():
    figures = json.loads((OUTPUT / "figures.json").read_text())
    scales = [f["y_scale"] for f in figures]
    assert scales[:3] == [
        dict(max=1000, step=200, shared="measure:approvals_per_year"),
        dict(max=1000, step=200, shared="measure:approvals_per_year"),
        dict(max=100, step=20, shared="panels"),
    ]
    assert [f["measure"] for f in figures[:3]] == ["approvals_per_year"] * 3
    assert scales[3:] == [
        dict(max=100, step=20, shared="panels"),
        dict(max=0.5, step=0.1, shared="panels"),
    ]


def test_delivered_manifest_names_each_approval_figures_scale():
    figures = json.loads((OUTPUT / "figures.json").read_text())
    assert [f.get("scale_note") for f in figures] == [
        "Note the scale: y maximum 1,000 in Figures 1 and 2, against 100 in Figure 3.",
        "Note the scale: y maximum 1,000 in Figures 1 and 2, against 100 in Figure 3.",
        "Note the scale: y maximum 100, against 1,000 in Figures 1 and 2.",
        None,
        None,
    ]


def test_plot_command_preserves_delivered_csv_bytes(tmp_path):
    before = {p.name: p.read_bytes() for p in OUTPUT.glob("*.csv")}
    for name, data in before.items():
        (tmp_path / name).write_bytes(data)
    subprocess.run(
        [sys.executable, OUTPUT.parent / "plot_charts.py", "--out", tmp_path],
        check=True,
    )
    assert {p.name: p.read_bytes() for p in tmp_path.glob("*.csv")} == before


@pytest.mark.parametrize(
    "flag_peak,should_share", [("290", False), ("300", True), ("310", True)]
)
def test_plot_command_selects_members_at_30_percent_of_the_nice_maximum(
    tmp_path, flag_peak, should_share
):
    for source in OUTPUT.glob("*.csv"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    # A partial-year value changes only the flag chart, which shares its CSV with Figure 2.
    path = tmp_path / "02_recompletion_by_period.csv"
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    row = next(
        r for r in rows if r["group"] == "Modify Perforations" and r["year"] == "2026"
    )
    row["value"] = flag_peak
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerows(rows)

    subprocess.run(
        [sys.executable, OUTPUT.parent / "plot_charts.py", "--out", tmp_path],
        check=True,
    )
    figures = json.loads((tmp_path / "figures.json").read_text())
    scales = [figure["y_scale"] for figure in figures[:3]]
    if should_share:
        assert all("scale_note" not in figure for figure in figures)
        assert (
            scales
            == [dict(max=1000, step=200, shared="measure:approvals_per_year")] * 3
        )
    else:
        assert scales == [
            dict(max=1000, step=200, shared="measure:approvals_per_year"),
            dict(max=1000, step=200, shared="measure:approvals_per_year"),
            dict(max=500, step=100, shared="panels"),
        ]
        assert [figure["scale_note"] for figure in figures[:3]] == [
            "Note the scale: y maximum 1,000 in Figures 1 and 2, against 500 in Figure 3.",
            "Note the scale: y maximum 1,000 in Figures 1 and 2, against 500 in Figure 3.",
            "Note the scale: y maximum 500, against 1,000 in Figures 1 and 2.",
        ]
