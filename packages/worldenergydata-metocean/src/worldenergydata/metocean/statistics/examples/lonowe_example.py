"""Synthetic LoNoWe example; run as a Python module to print contour points.

Stipulated inputs (not environmental estimates): seed 42, 5000 hourly pairs,
Hs=0.3+2*W with Weibull shape 1.5, log(Tp)|Hs normal with
mu=1.5+0.4*Hs**0.36 and variance=0.005+0.1*exp(-0.5*Hs).
The inverse sampling equations are Hs=loc+scale*(-ln(1-U))**(1/shape)
and Tp=exp(mu+sqrt(variance)*Z), U uniform and Z standard normal.
Source of the model form and fixed exponents: metocean-stats v.1.2.0
extreme.py L631-L742; all other generator values above are synthetic inputs.
Distribution basis: NIST/SEMATECH e-Handbook of Statistical Methods,
online edition accessed 2026, sections 1.3.6.6.8 (Weibull inverse CDF) and
1.3.6.6.9 (lognormal PDF); links in the knowledge pack worked example.
No design-use qualification is claimed.
"""

import numpy as np
import pandas as pd
from worldenergydata.metocean.statistics.environmental_contours import (
    EnvironmentalContour,
)
from worldenergydata.metocean.statistics.joint_probability import JointProbabilityModel


def synthetic_sample() -> tuple[pd.Series, pd.Series]:
    """Generate exactly the stipulated input sample from the module docstring."""
    rng = np.random.default_rng(42)
    hs = 0.3 + 2.0 * rng.weibull(1.5, 5000)
    mu = 1.5 + 0.4 * hs**0.36
    variance = 0.005 + 0.1 * np.exp(-0.5 * hs)
    tp = np.exp(mu + np.sqrt(variance) * rng.standard_normal(len(hs)))
    index = pd.date_range("2010-01-01", periods=len(hs), freq="h")
    return pd.Series(hs, index=index, name="hs"), pd.Series(tp, index=index, name="tp")


def main() -> None:
    """Print branch pairs nearest median Hs and at maximum contour Hs."""
    hs, tp = synthetic_sample()
    model = JointProbabilityModel().fit(hs, tp, periods=[1, 100])
    print("| Return period (years) | Hs (m) | Lower Tp (s) | Upper Tp (s) |")
    print("| --- | --- | --- | --- |")
    for period in model.fitted_periods:
        contour = EnvironmentalContour().lonowe(model, period)
        heights = np.unique(contour.hs_values)
        selected = [heights[np.argmin(abs(heights - hs.median()))], heights[-1]]
        for height in selected:
            periods = contour.tp_values[contour.hs_values == height]
            print(f"| {period:g} | {height:.1f} | {periods.min():.1f} | {periods.max():.1f} |")


if __name__ == "__main__":
    main()
