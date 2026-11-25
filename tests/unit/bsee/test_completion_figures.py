"""Check the four figure files that feed the completion article."""

import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

OUTPUT = (
    Path(__file__).resolve().parents[3] / "examples/bsee/completions_by_depth/output"
)


def test_figure_manifest_links_bullets_to_plotted_cells():
    figures = json.loads((OUTPUT / "figures.json").read_text(encoding="utf-8"))
    assert [f["svg"] for f in figures] == [
        "01_approvals_by_period.svg",
        "02_recompletion_by_period.svg",
        "03_approvals_per_well.svg",
        "04_drilled_to_completed.svg",
    ]
    assert len({f["question"] for f in figures}) == 4
    for figure in figures:
        svg = ET.parse(OUTPUT / figure["svg"])
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
