"""
ABOUTME: North Sea example — Met Norway hindcast mock data → weather windows + operability.
ABOUTME: Uses synthetic data matching Norwegian Continental Shelf characteristics.

North Sea (NCS) Example
========================

Demonstrates the statistical workflow for a Norwegian Continental Shelf site:
  1. Generate synthetic NCS-like Hs and Tp data (Ekofisk area characteristics)
  2. Weather window analysis (installation vessel operability)
  3. Monthly operability heatmap
  4. Wave spectra (JONSWAP + Torsethaugen comparison)
  5. Scatter diagram
  6. HTML report

To run:
    python -m worldenergydata.metocean.statistics.examples.north_sea_example

Outputs a file ``north_sea_report.html`` in the current working directory.
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
    WaveSpectra,
    ScatterDiagram,
)


# ---------------------------------------------------------------------------
# NCS synthetic data parameters (typical Ekofisk area)
# ---------------------------------------------------------------------------
_NCS_HS_WEIBULL_SCALE = 1.8    # metres (harsher than GoM)
_NCS_HS_WEIBULL_SHAPE = 1.4
_NCS_HS_MIN = 0.2               # metres
_NCS_TP_COEFF = 4.8             # Tp ~ a * sqrt(Hs) + noise
_NCS_TP_NOISE_STD = 1.5         # seconds
_NCS_TP_CLIP_MIN = 4.0          # seconds
_NCS_TP_CLIP_MAX = 22.0         # seconds
_NCS_LAT = 56.533               # Ekofisk latitude
_NCS_LON = 3.211                # Ekofisk longitude
_NCS_N_YEARS = 20
_NCS_TIMESTEP_H = 3             # 3-hourly hindcast


def _generate_ncs_data(seed: int = 7) -> tuple[pd.Series, pd.Series]:
    """
    Synthetic NCS metocean data mirroring Ekofisk hindcast statistics.

    Returns
    -------
    (hs, tp) — 3-hourly time series over ``_NCS_N_YEARS`` years.
    """
    rng = np.random.default_rng(seed)
    n = _NCS_N_YEARS * 365 * (24 // _NCS_TIMESTEP_H)

    dates = pd.date_range("2000-01-01", periods=n, freq="3h")

    # Hs: Weibull + strong winter seasonality (North Sea winter storms)
    hs_raw = rng.weibull(_NCS_HS_WEIBULL_SHAPE, size=n) * _NCS_HS_WEIBULL_SCALE
    # Winter (Dec-Feb) storms: multiply by up to 2.5×
    month = dates.month.values
    # Peak in January (month=1), trough in July (month=7)
    season_factor = 1.0 + 0.9 * np.cos(2 * np.pi * (month - 1) / 12.0)
    hs = np.clip(hs_raw * season_factor + _NCS_HS_MIN, _NCS_HS_MIN, None)

    # Tp correlated with Hs (longer swells in N. Sea)
    tp = _NCS_TP_COEFF * np.sqrt(hs) + rng.normal(0, _NCS_TP_NOISE_STD, size=n)
    tp = np.clip(tp, _NCS_TP_CLIP_MIN, _NCS_TP_CLIP_MAX)

    hs_series = pd.Series(hs, index=dates, name="hs")
    tp_series = pd.Series(tp, index=dates, name="tp")
    return hs_series, tp_series


def run_north_sea_example(output_path: str = "north_sea_report.html") -> None:
    """
    Run the full NCS statistical workflow and save an HTML report.

    Parameters
    ----------
    output_path:
        Output HTML file path.
    """
    print("=" * 60)
    print("North Sea Example — NCS Ekofisk Area")
    print("=" * 60)

    # 1. Generate synthetic data
    print("\n[1/6] Generating synthetic NCS data (3-hourly)...")
    hs, tp = _generate_ncs_data()
    print(f"      {len(hs):,} records | Hs range: {hs.min():.2f}–{hs.max():.2f} m")
    print(f"      Tp range: {tp.min():.2f}–{tp.max():.2f} s")

    # 2. Weather windows
    print("\n[2/6] Weather Window Analysis...")
    wwa = WeatherWindowAnalysis()

    # Installation vessel: Hs < 2.5 m, 12-hour minimum window
    ww_install = wwa.operability(hs, threshold=2.5, min_window_hours=12)
    print(f"      Installation (Hs<2.5m, 12h): {ww_install.operability_pct:.1f}% operable")

    # Diving operations: Hs < 1.5 m
    ww_dive = wwa.operability(hs, threshold=1.5, min_window_hours=6)
    print(f"      Diving (Hs<1.5m, 6h):        {ww_dive.operability_pct:.1f}% operable")

    # 3. Monthly operability heatmap
    print("\n[3/6] Monthly Operability...")
    monthly_df = wwa.monthly_operability(hs, threshold=2.5)
    print(monthly_df[["month_name", "operability_pct"]].to_string())

    # 4. Wave spectra comparison
    print("\n[4/6] Wave Spectra (JONSWAP vs Torsethaugen)...")
    ws = WaveSpectra()
    design_hs = float(hs.quantile(0.99))
    design_tp = float(tp[hs >= hs.quantile(0.99)].median())
    print(f"      Design sea state: Hs={design_hs:.2f}m, Tp={design_tp:.2f}s")

    jonswap = ws.jonswap(hs=design_hs, tp=design_tp)
    torse = ws.torsethaugen(hs=design_hs, tp=design_tp)
    print(f"      JONSWAP m0 = {jonswap.spectral_moments['m0']:.4f} m²"
          f" → Hs_check = {4*jonswap.spectral_moments['m0']**0.5:.2f} m")
    print(f"      Torsethaugen m0 = {torse.spectral_moments['m0']:.4f} m²")

    # 5. Scatter diagram
    print("\n[5/6] Hs-Tp Scatter Diagram...")
    data_df = pd.DataFrame({"hs": hs.values, "tp": tp.values})
    sd = ScatterDiagram()
    scatter_df = sd.compute(data_df, var1="hs", var2="tp", step_var1=0.5, step_var2=1.0)
    print(f"      {scatter_df.shape[0]} Hs bins × {scatter_df.shape[1]} Tp bins")

    # 6. Report
    print(f"\n[6/6] Assembling HTML report → {output_path}")
    report = MetoceanReport(
        location_name="North Sea — NCS Ekofisk Area",
        lat=_NCS_LAT,
        lon=_NCS_LON,
    )

    # Add EVA as well
    eva = ExtremeValueAnalysis()
    eva_result = eva.fit_pot(hs, periods=[1, 10, 50, 100])
    report.add_eva(eva_result)

    # Joint + contour for completeness
    jpm = JointProbabilityModel()
    joint_model = jpm.fit(hs, tp, periods=[50])
    report.add_joint(joint_model)

    ec = EnvironmentalContour()
    contour = ec.iform(joint_model, return_period=50)
    report.add_contour(contour)

    # Weather windows
    report.add_weather_windows(ww_install)

    report.save_html(output_path)
    print(f"[Done]  Report saved: {output_path}")


if __name__ == "__main__":
    run_north_sea_example()
