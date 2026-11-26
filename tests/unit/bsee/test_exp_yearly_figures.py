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

    def test_caption_tracks_selected_annual_blanks_and_window_styles(self):
        def figures():
            self.charts.write_figures(self.output)
            return {
                f["figure_number"]: f
                for f in json.loads((self.output / "figures.json").read_bytes())
            }

        chart = figures()
        expected = [f"2022 {band}" for band in BANDS]
        self.assertEqual(chart["2B"]["blank_cells"], expected)
        for cell in expected:
            self.assertIn(cell, chart["2B"]["caption"])
        for number in ("2A", "3A"):
            windows = chart[number]["windows"]
            self.assertEqual(set(windows), {"solid", "dashed"})
            self.assertEqual(windows["solid"]["label"], "Observed by file date")
            self.assertIn("23 November 2026", windows["solid"]["definition"])
            self.assertEqual(windows["dashed"]["label"], "Within five years")
            self.assertIn("fifth anniversary", windows["dashed"]["definition"])
            for style, window in windows.items():
                self.assertTrue(
                    any(
                        all(term in clause for term in (style, *window.values()))
                        for clause in chart[number]["caption"].split(". ")
                    )
                )
        self.assertNotIn("windows", chart["2B"])

        # A measured zero restores one selected cell. A newly blank annual
        # value moves its identifier, even though both moving averages are empty.
        series = self.output / "annual_trends.csv"
        source = series.read_bytes()
        group = b"spud_share_observed|Under 100 m,spud_share_observed,Under 100 m,"
        source = source.replace(group + b"2022,0,,,", group + b"2022,0,0,,")
        series.write_bytes(source.replace(group + b"2023,0,2,,", group + b"2023,0,,,"))
        revised = figures()
        self.assertEqual(
            revised["2B"]["blank_cells"], ["2023 Under 100 m", *expected[1:]]
        )
        self.assertNotIn(expected[0], revised["2B"]["caption"])
        self.assertIn("2023 Under 100 m", revised["2B"]["caption"])
        self.assertEqual(chart["2C"], revised["2C"])

    def test_partial_year_cutoff_and_fixed_point_tooltip(self):
        series = self.output / "annual_trends.csv"
        series.write_bytes(
            series.read_bytes().replace(
                b"2026,1,1,,verified", b"2026,1,12345,,verified", 1
            )
        )
        self.charts.write_figures(self.output)
        html = (self.output / "figure-1a.html").read_text(encoding="utf-8")
        self.assertIn("2026 (partial through October 2026)</option>", html)
        self.assertIn("Annual value 12,345.", html)
        self.assertEqual(self.charts.format_readout(1.0625), "1.063")

    def test_smallest_covering_scale(self):
        for peak, top, step in (
            (21.69, 25, 5),
            (579, 600, 200),
            (6.92, 8, 2),
            (1.42, 1.5, 0.5),
            (7.69, 8, 2),
            (29, 30, 10),
            (0.3, 0.3, 0.1),
        ):
            with self.subTest(peak=peak):
                self.assertEqual(self.charts.scale(peak), (top, step))

    def test_scale_uses_selected_groups_and_treats_cutoff_as_inclusive(self):
        figures = [
            {"figure_number": str(i), "measure": "count", "groups": [str(i)]}
            for i in range(1, 4)
        ]
        self.charts.assign_scales(figures, {"1": 81, "2": 30, "3": 29})
        self.assertEqual([fig["y_scale"]["max"] for fig in figures], [100, 100, 30])
        self.assertEqual(
            [fig["y_scale"]["shared"] for fig in figures],
            ["measure:count", "measure:count", "panels"],
        )
        for figure in figures:
            self.assertTrue(figure["scale_note"])


def test_yearly_svg_build_gate(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    from lease_analysis import validate_yearly_svg

    yearly = EXAMPLE / "output/yearly"
    for entry in json.loads((yearly / "figures.json").read_bytes()):
        validate_yearly_svg(yearly / entry["svg"])

    path = tmp_path / "figure-1a.svg"
    source = (yearly / path.name).read_text(encoding="utf-8")
    for tag in ("clipPath", "pattern", "filter", "mask", "foreignObject", "image"):
        path.write_text(source.replace("</svg>", f"<{tag}/></svg>"), encoding="utf-8")
        with pytest.raises(ValueError, match=tag):
            validate_yearly_svg(path)

    for selector, attribute, value, message in [
        (".", "font-family", "Arial", "incorrect font-family"),
        (".//{*}g[@data-legend]", "font-size", "14", "font-size below"),
        ("{*}text", "font-size", "17", "font-size below"),
        (".//{*}circle", "r", "4", "marker radius below"),
        (
            ".//{*}path[@class='annual']",
            "stroke-width",
            "1",
            "annual stroke-width below",
        ),
        (".//{*}path[@class='trend']", "stroke-width", "3", "trend stroke-width below"),
        (".//{*}g[@data-series]", "clip-path", "url(#crop)", "prohibited clip-path"),
    ]:
        root = ET.fromstring(source)
        root.find(selector).set(attribute, value)
        ET.ElementTree(root).write(path, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            validate_yearly_svg(path)

    for selector, dash in [
        ("{*}text", "-"),
        (".//{*}circle/{*}title", "–"),
        ("{*}title", "—"),
        (".//{*}circle/{*}title", "‑"),
        (".//{*}circle/{*}title", "−"),
    ]:
        root = ET.fromstring(source)
        root.find(selector).text += dash
        ET.ElementTree(root).write(path, encoding="utf-8")
        with pytest.raises(ValueError, match="dash"):
            validate_yearly_svg(path)
