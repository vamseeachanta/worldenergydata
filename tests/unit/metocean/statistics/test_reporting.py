"""
ABOUTME: Tests for MetoceanReport (HTML report combining all analyses).
ABOUTME: Uses synthetic results — no live API calls.
"""

import ast
import os
import re
import tempfile

import numpy as np
import pandas as pd
import pytest

from worldenergydata.metocean.statistics.environmental_contours import (
    EnvironmentalContour,
)
from worldenergydata.metocean.statistics.eva import ExtremeValueAnalysis
from worldenergydata.metocean.statistics.joint_probability import (
    JointModel,
    JointProbabilityModel,
)
from worldenergydata.metocean.statistics.reporting import MetoceanReport
from worldenergydata.metocean.statistics.weather_windows import (
    WeatherWindowAnalysis,
)


def _make_hs_series(n_years: int = 5, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    n = n_years * 365 * 8
    dates = pd.date_range("2015-01-01", periods=n, freq="3h")
    hs = rng.weibull(1.5, size=n) * 2.0 + 0.1
    return pd.Series(hs, index=dates, name="hs")


def _make_hs_tp(n: int = 3000, seed: int = 42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2010-01-01", periods=n, freq="h")
    hs = rng.weibull(1.5, size=n) * 2.0 + 0.3
    tp = 4.0 * np.sqrt(hs) + rng.normal(0, 1.0, size=n)
    tp = np.clip(tp, 3.0, 25.0)
    return (
        pd.Series(hs, index=dates, name="hs"),
        pd.Series(tp, index=dates, name="tp"),
    )


@pytest.fixture
def eva_result():
    hs = _make_hs_series()
    eva = ExtremeValueAnalysis()
    return eva.fit_pot(hs)


@pytest.fixture
def joint_model():
    hs, tp = _make_hs_tp()
    jpm = JointProbabilityModel()
    return jpm.fit(hs, tp)


@pytest.fixture
def contour_result(joint_model):
    ec = EnvironmentalContour()
    return ec.lonowe(joint_model, return_period=50)


@pytest.fixture
def operability_result():
    hs = _make_hs_series()
    wwa = WeatherWindowAnalysis()
    return wwa.operability(hs, threshold=2.5)


class TestMetoceanReportInit:
    def test_report_initialises(self):
        report = MetoceanReport(
            location_name="Test Location",
            lat=29.0,
            lon=-94.0,
        )
        assert report.location_name == "Test Location"
        assert report.lat == pytest.approx(29.0)
        assert report.lon == pytest.approx(-94.0)

    def test_report_sections_empty_on_init(self):
        report = MetoceanReport(location_name="Test", lat=29.0, lon=-94.0)
        assert len(report._sections) == 0


class TestMetoceanReportAddSections:
    def setup_method(self):
        self.report = MetoceanReport(location_name="GoM Test Site", lat=29.0, lon=-94.0)

    def test_add_eva_increases_sections(self, eva_result):
        count_before = len(self.report._sections)
        self.report.add_eva(eva_result)
        assert len(self.report._sections) == count_before + 1

    def test_add_joint_increases_sections(self, joint_model):
        count_before = len(self.report._sections)
        self.report.add_joint(joint_model)
        assert len(self.report._sections) == count_before + 1

    def test_add_contour_increases_sections(self, contour_result):
        count_before = len(self.report._sections)
        self.report.add_contour(contour_result)
        assert len(self.report._sections) == count_before + 1

    def test_add_weather_windows_increases_sections(self, operability_result):
        count_before = len(self.report._sections)
        self.report.add_weather_windows(operability_result)
        assert len(self.report._sections) == count_before + 1


class TestMetoceanReportSaveHTML:
    def test_save_html_retains_fitted_conditional_coefficients(
        self, joint_model, tmp_path
    ):
        report = MetoceanReport(location_name="Synthetic", lat=0.0, lon=0.0)
        report.add_joint(joint_model)
        path = tmp_path / "joint-summary.html"
        report.save_html(path.as_posix())
        content = path.read_text(encoding="utf-8")

        for label, group in (("mu_tp", "mu"), ("variance_tp", "variance")):
            row = re.search(rf"<strong>{label}</strong></td><td>(.*?)</td>", content)
            assert row is not None, f"Missing conditional coefficient group: {group}"
            coefficients = ast.literal_eval(row.group(1))
            assert coefficients == pytest.approx(joint_model.conditional_tp[group])
        assert "sigma_tp" not in content

    def test_save_html_preserves_literal_conditional_coefficients(self, tmp_path):
        # Stipulated synthetic coefficients are copied without calculation.
        model = JointModel(
            marginal_hs={"distribution": "LoNoWe"},
            conditional_tp={
                "model": "lognormal_conditional",
                "mu": {"a1": 1.5, "a2": 0.4, "a3": 0.36},
                "variance": {"b1": 0.005, "b2": 0.1, "b3": 0.5},
            },
            n_samples=5000,
        )
        report = MetoceanReport(location_name="Synthetic", lat=0.0, lon=0.0)
        report.add_joint(model)
        path = tmp_path / "joint-summary.html"
        report.save_html(path.as_posix())
        content = path.read_text(encoding="utf-8")

        for label, expected in (
            ("mu_tp", {"a1": 1.5, "a2": 0.4, "a3": 0.36}),
            ("variance_tp", {"b1": 0.005, "b2": 0.1, "b3": 0.5}),
        ):
            row = re.search(rf"<strong>{label}</strong></td><td>(.*?)</td>", content)
            assert row is not None, f"Missing conditional coefficient group: {label}"
            assert ast.literal_eval(row.group(1)) == pytest.approx(expected)

    def test_save_html_creates_file(self, eva_result):
        report = MetoceanReport(location_name="Test", lat=29.0, lon=-94.0)
        report.add_eva(eva_result)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            report.save_html(path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    def test_save_html_contains_location_name(self, eva_result):
        report = MetoceanReport(
            location_name="Gulf of Mexico Site", lat=29.0, lon=-94.0
        )
        report.add_eva(eva_result)
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8", newline="\n"
        ) as f:
            path = f.name
        try:
            report.save_html(path)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            assert "Gulf of Mexico Site" in content
        finally:
            os.unlink(path)

    def test_save_html_with_multiple_sections(
        self, eva_result, joint_model, contour_result, operability_result
    ):
        report = MetoceanReport(location_name="Full Test", lat=29.0, lon=-94.0)
        report.add_eva(eva_result)
        report.add_joint(joint_model)
        report.add_contour(contour_result)
        report.add_weather_windows(operability_result)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            report.save_html(path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 500
        finally:
            os.unlink(path)
