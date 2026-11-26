"""Check the COMP overlay set, appendix selection and offline figure readback."""

import csv
import importlib.util
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/completions_by_depth"
BANDS = ("Under 100 m", "100 to 500 m", "500 to 1,500 m", "1,500 m and deeper")
INVENTORY = {
    "1A": ("initial", "other"),
    "1B": ("initial",),
    "1C": ("other",),
    "2A": ("recompletion",),
    "2B": ("recompletion",),
    "3A": ("exploratory_share", "development_share"),
    "3B": ("exploratory_share",),
    "3C": ("development_share",),
    "E3": ("approvals_per_well",),
    "E4": ("modify_perforations", "reperforation"),
}


@pytest.fixture
def charts(monkeypatch):
    monkeypatch.syspath_prepend(
        str(EXAMPLE.parents[2] / "packages/worldenergydata-bsee/src")
    )
    spec = importlib.util.spec_from_file_location(
        "comp_charts", EXAMPLE / "comp_charts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_round_trip_from_one_csv(charts, tmp_path):
    metrics = dict.fromkeys(
        metric for metrics in INVENTORY.values() for metric in metrics
    )
    with (tmp_path / "annual_trends.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(
            (
                "group",
                "metric",
                "band",
                "year",
                "partial",
                "value",
                "moving_average",
                "availability",
                "denominator",
            )
        )
        for metric in metrics:
            for band in ("All water depths", *BANDS):
                for year in range(2016, 2027):
                    value = "" if year == 2021 else (79 if metric == "initial" else 12)
                    mean = value if year == 2020 else ""
                    writer.writerow(
                        (
                            metric + "|" + band,
                            metric,
                            band,
                            year,
                            int(year == 2026),
                            value,
                            mean,
                            (
                                "unavailable"
                                if year == 2021 and metric.endswith("_share")
                                else "verified"
                            ),
                            0 if year == 2021 and metric.endswith("_share") else "",
                        )
                    )
    charts.write_figures(tmp_path)
    manifest = json.loads((tmp_path / "figures.json").read_bytes())
    assert [f["figure_number"] for f in manifest] == list(INVENTORY)
    for fig in manifest:
        number = fig["figure_number"]
        metrics = INVENTORY[number]
        svg = (tmp_path / fig["svg"]).read_text(encoding="utf-8")
        root = ET.fromstring(svg)
        assert {group.split("|")[0] for group in fig["groups"]} == set(metrics)
        if number.startswith("E"):
            assert fig["role"] == "appendix"
            assert len(root.findall(".//{*}g[@class='panel']")) == 4
            continue
        assert fig["layout"] == "overlay"
        html = (tmp_path / fig["interactive"]).read_text(encoding="utf-8")
        assert svg.strip() in html
        for control in ("pointerover", "click", "aria-pressed", 'id="year"'):
            assert control in html
        assert "23 November 2026" in " ".join(root.itertext())
        assert fig["xlabel"] in html
        data = json.loads(html.split("const series = ", 1)[1].split(";", 1)[0])
        groups = root.findall(".//{*}g[@data-series]")
        if fig["series_by"] == "depth_band":
            assert [g.get("data-label") for g in groups] == list(BANDS)
        for index, g in enumerate(groups):
            dots = g.findall("{*}circle")
            assert len(dots) == 10 and all(dot.get("r") == "5" for dot in dots)
            assert dots[-1].get("fill") == "white"
            assert data[index][-1][2:4] == [None, True]
            assert data[index][5][1:3] == [None, None]
            if number.startswith("3"):
                assert data[index][5][4] == "No wells first drilled"
                assert "zero denominator" in fig["coverage_note"]
                assert "Source records are unavailable" not in fig["coverage_note"]
            path = g.find("{*}path[@class='annual']")
            assert path.get("d").count("M") == 2
            if number == "1A":
                for line in g.findall("{*}path"):
                    assert bool(line.get("stroke-dasharray")) == bool(index)
    first = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    charts.write_figures(tmp_path)
    assert first == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_scale_note_names_each_selected_figure(charts):
    figures = [
        {"figure_number": str(i), "measure": "count", "groups": [str(i)]}
        for i in range(1, 4)
    ]
    charts.assign_scales(figures, {"1": 81, "2": 30, "3": 29})
    assert [f["y_scale"]["max"] for f in figures] == [100, 100, 50]
    assert (
        figures[2]["scale_note"]
        == "Y maximum 50, against 100 in Figure 1, 100 in Figure 2."
    )
