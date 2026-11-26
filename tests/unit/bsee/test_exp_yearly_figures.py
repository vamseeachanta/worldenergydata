"""Round-trip checks for the EXP annual figure build using a small calendar."""

import csv
import importlib.util
import json
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/exploration_leasing"
BANDS = ("Under 100 m", "100 to 500 m", "500 to 1,500 m", "1,500 m and deeper")
STATUS = (
    "CANCEL",
    "EXPIR",
    "OPERNS",
    "PRIMRY",
    "PROD",
    "RELINQ",
    "SOP",
    "TERMIN",
    "UNIT",
)
METRICS = (
    "effective_leases",
    "spud_share_observed",
    "spud_share_5y",
    "spud_years_observed",
    "spud_years_5y",
    "crude_share_5y",
    "crude_years_5y",
)


class TestAnnualCharts(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def chart_fixture(self, tmp_path):
        spec = importlib.util.spec_from_file_location(
            "lease_charts", EXAMPLE / "lease_charts.py"
        )
        self.charts = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.charts)
        self.output = tmp_path
        rows = []
        for metric in (*METRICS, *("status_" + code for code in STATUS)):
            bands = (
                ("All water depths",)
                if metric.startswith("status_")
                else ("All water depths", *BANDS)
            )
            for index, band in enumerate(bands):
                for year in range(2020, 2027):
                    # Blanks break both annual paths and five-year windows.
                    value = "" if year == 2022 else 1 + index
                    mean = 2 if year == 2024 else ""
                    rows.append(
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
                                if year == 2022 and metric == "crude_years_5y"
                                else "verified"
                            ),
                        )
                    )
        with (self.output / "annual_trends.csv").open(
            "w", encoding="utf-8", newline=""
        ) as stream:
            writer = csv.writer(stream, lineterminator="\n")
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
                )
            )
            writer.writerows(rows)

    def test_round_trip(self):
        self.charts.write_figures(self.output)
        manifest = json.loads((self.output / "figures.json").read_bytes())
        self.assertEqual(
            [f["figure_number"] for f in manifest],
            [
                "1A",
                "1B",
                "2A",
                "2B",
                "2C",
                "3A",
                "3B",
                "3C",
                "4A",
                "4B",
                "4C",
                "4D",
                "5",
            ],
        )
        for figure in manifest:
            svg = (self.output / figure["svg"]).read_text(encoding="utf-8")
            html = (self.output / figure["interactive"]).read_text(encoding="utf-8")
            self.assertIn(svg.strip(), html)
            self.assertIn("aria-pressed", html)
            self.assertIn("pointerover", html)
            root = ET.fromstring(svg)
            for legend in root.findall(".//{*}g[@data-legend]"):
                self.assertEqual(legend.find("{*}rect").get("fill"), "white")
            series = root.findall(".//{*}g[@data-series]")
            self.assertEqual(len(series), len(figure["groups"]))
            if figure["series_by"] == "depth_band":
                self.assertEqual([g.get("data-label") for g in series], list(BANDS))
            for g in series:
                dots = g.findall("{*}circle")
                self.assertEqual(len(dots), 6)
                self.assertTrue(all(float(dot.get("r")) >= 4.5 for dot in dots))
                self.assertEqual(dots[-1].get("fill"), "white")
                self.assertIn("2026", dots[-1].findtext("{*}title"))
                annual = g.find("{*}path[@class='annual']")
                self.assertEqual(annual.get("d").count("M"), 2)
                trend = g.find("{*}path[@class='trend']")
                self.assertGreaterEqual(float(trend.get("stroke-width")), 4)
            self.assertEqual(figure["layout"], "overlay")
        pair = ET.parse(self.output / "figure-2a.svg").findall(
            ".//{*}path[@class='annual']"
        )
        self.assertIsNone(pair[0].get("stroke-dasharray"))
        self.assertTrue(pair[1].get("stroke-dasharray"))
        self.assertEqual(len(manifest[-1]["groups"]), 9)
        self.assertEqual(manifest[9]["unavailable_cells"], 1)
        self.assertIn(
            "Source records are unavailable",
            (self.output / "figure-4b.svg").read_text(),
        )
        first = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.charts.write_figures(self.output)
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.output.iterdir()})

    def test_scale_uses_selected_groups_and_treats_cutoff_as_inclusive(self):
        figures = [
            {"figure_number": str(i), "measure": "count", "groups": [str(i)]}
            for i in range(1, 4)
        ]
        self.charts.assign_scales(figures, {"1": 81, "2": 30, "3": 29})
        self.assertEqual([fig["y_scale"]["max"] for fig in figures], [100, 100, 50])
        self.assertEqual(
            [fig["y_scale"]["shared"] for fig in figures],
            ["measure:count", "measure:count", "panels"],
        )
        for figure in figures:
            self.assertTrue(figure["scale_note"])
