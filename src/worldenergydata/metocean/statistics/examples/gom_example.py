"""
ABOUTME: GoM example — NDBC 42035 mock data → Hs EVA + Hs-Tp joint + contours.
ABOUTME: Uses synthetic data matching GoM statistical characteristics.

Gulf of Mexico Example
======================

Demonstrates the full statistical workflow for a Gulf of Mexico site:
  1. Generate synthetic GoM-like Hs and Tp data (NDBC 42035 characteristics)
  2. Extreme Value Analysis (POT + Weibull)
  3. Hs-Tp Joint Probability (CMA)
  4. IFORM environmental contour (50-year)
  5. HTML report

To run:
    python -m worldenergydata.metocean.statistics.examples.gom_example

Outputs a file ``gom_report.html`` in the current working directory.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from worldenergydata.metocean.statistics import (
    ExtremeValueAnalysis,
    JointProbabilityModel,
    EnvironmentalContour,
    MetoceanReport,
    WeatherWindowAnalysis,
)


from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# GoM synthetic data parameters (typical NDBC 42035, West Cameron Block)
# ---------------------------------------------------------------------------
_GoM_HS_WEIBULL_SCALE = 0.85   # metres  (light sea state, Gulf swell dominated)
_GoM_HS_WEIBULL_SHAPE = 1.2
_GoM_HS_MIN = 0.1               # metres
_GoM_TP_COEFF = 4.3             # Tp ~ a * sqrt(Hs) + noise
_GoM_TP_NOISE_STD = 1.2         # seconds
_GoM_TP_CLIP_MIN = 3.0          # seconds
_GoM_TP_CLIP_MAX = 18.0         # seconds
_GoM_LAT = 29.232
_GoM_LON = -94.413
_GoM_N_YEARS = 10
_GoM_TIMESTEP_H = 1             # hourly


def _generate_gom_data(seed: int = 42) -> tuple[pd.Series, pd.Series]:
    """
    Synthetic GoM metocean data mirroring NDBC 42035 statistics.

    Returns
    -------
    (hs, tp) — hourly time series over ``_GoM_N_YEARS`` years.
    """
    rng = np.random.default_rng(seed)
    n = _GoM_N_YEARS * 365 * 24

    dates = pd.date_range("2010-01-01", periods=n, freq="h")

    # Hs: Weibull + annual seasonality (hurricane season peaks Aug-Oct)
    hs_raw = rng.weibull(_GoM_HS_WEIBULL_SHAPE, size=n) * _GoM_HS_WEIBULL_SCALE
    # Add hurricane season peak
    month = dates.month.values
    season_factor = 1.0 + 0.6 * np.exp(-0.5 * ((month - 9) / 1.5) ** 2)
    hs = np.clip(hs_raw * season_factor + _GoM_HS_MIN, _GoM_HS_MIN, None)

    # Tp correlated with Hs
    tp = _GoM_TP_COEFF * np.sqrt(hs) + rng.normal(0, _GoM_TP_NOISE_STD, size=n)
    tp = np.clip(tp, _GoM_TP_CLIP_MIN, _GoM_TP_CLIP_MAX)

    hs_series = pd.Series(hs, index=dates, name="hs")
    tp_series = pd.Series(tp, index=dates, name="tp")
    return hs_series, tp_series


def run_gom_example(output_path: str = "gom_report.html") -> None:
    """
    Run the full GoM statistical workflow and save an HTML report.

    Parameters
    ----------
    output_path:
        Output HTML file path.
    """
    logger.info("=" * 60)
    logger.info("GoM Example — NDBC 42035 (West Cameron Block)")
    logger.info("=" * 60)

    # 1. Generate synthetic data
    logger.info("\n[1/5] Generating synthetic GoM data...")
    hs, tp = _generate_gom_data()
    logger.info(f"      {len(hs):,} hourly records | Hs range: {hs.min():.2f}–{hs.max():.2f} m")
    logger.info(f"      Tp range: {tp.min():.2f}–{tp.max():.2f} s")

    # 2. EVA
    logger.info("\n[2/5] Extreme Value Analysis (POT, Weibull_2P)...")
    eva = ExtremeValueAnalysis()
    eva_result = eva.fit_pot(hs, periods=[1, 10, 50, 100, 1000])
    table = eva.return_period_table(eva_result)
    logger.info("      Return Period Table:")
    logger.info(table.to_string())

    # 3. Joint probability
    logger.info("\n[3/5] Hs-Tp Joint Probability (CMA)...")
    jpm = JointProbabilityModel()
    joint_model = jpm.fit(hs, tp, periods=[50])
    scatter = jpm.scatter_diagram(hs, tp)
    logger.info(f"      Scatter diagram: {scatter.shape[0]} Hs bins × {scatter.shape[1]} Tp bins")
    logger.info(f"      Total occurrence sum: {scatter.values.sum():.2f}%")

    # 4. IFORM contour
    logger.info("\n[4/5] IFORM Environmental Contour (50-year)...")
    ec = EnvironmentalContour()
    contour = ec.iform(joint_model, return_period=50)
    logger.info(f"      Contour points: {len(contour.hs_values)}")
    logger.info(f"      Hs max on contour: {contour.hs_values.max():.2f} m")

    # 5. Weather windows
    logger.info("\n[5/5] Weather Windows (Hs < 2.0 m threshold)...")
    wwa = WeatherWindowAnalysis()
    ww_result = wwa.operability(hs, threshold=2.0, min_window_hours=12)
    logger.info(f"      Operability: {ww_result.operability_pct:.1f}%")
    logger.info(f"      Total windows >= 12h: {ww_result.total_windows}")

    # Report
    logger.info(f"\n[Report] Assembling HTML report → {output_path}")
    report = MetoceanReport(
        location_name="GoM — West Cameron Block (NDBC 42035)",
        lat=_GoM_LAT,
        lon=_GoM_LON,
    )
    report.add_eva(eva_result)
    report.add_joint(joint_model)
    report.add_contour(contour)
    report.add_weather_windows(ww_result)
    report.save_html(output_path)
    logger.info(f"[Done]  Report saved: {output_path}")


if __name__ == "__main__":
    run_gom_example()
