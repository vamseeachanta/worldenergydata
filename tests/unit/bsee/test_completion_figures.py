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
        assert 2 <= len(figure["bullets"]) <= 4
        with (OUTPUT / figure["csv"]).open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        for bullet in figure["bullets"]:
            assert bullet["cells"]
            for cell in bullet["cells"]:
                matching = [
                    row
                    for row in rows
                    if all(row[key] == value for key, value in cell["row"].items())
                ]
                assert len(matching) == 1
                value = float(matching[0][cell["column"]])
                assert f'{value:,.{cell["decimals"]}f}' in bullet["text"]
        assert not re.search(
            r"[-\u2010-\u2015\u2212]", "".join(svg.getroot().itertext())
        )


def test_drilled_figure_shows_exploratory_first():
    root = ET.parse(OUTPUT / "04_drilled_to_completed.svg").getroot()
    text = list(root.itertext())
    assert text.index("Exploratory wells") < text.index("Development wells")
    assert text.index("51 %  (353 of 686)") < text.index("82 %  (674 of 826)")
    legend = root.findall("{*}rect")[1:3]
    assert [item.get("fill") for item in legend] == ["#6588a6", "#245476"]


def test_body_figures_have_distinct_accessible_names():
    figures = json.loads((OUTPUT / "figures.json").read_text(encoding="utf-8"))
    names = [
        ET.parse(OUTPUT / f["svg"]).getroot().attrib["aria-label"] for f in figures
    ]
    assert len(set(names)) == len(figures)
