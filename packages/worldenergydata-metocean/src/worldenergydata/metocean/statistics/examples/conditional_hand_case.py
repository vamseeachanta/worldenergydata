"""Constrained synthetic fit with an independent contour-point calculation.

Basis: 'Deriving environmental contours from highest density regions',
Coastal Engineering 123 (2017), Eqs. (2)–(4),(6). No published fit coefficients
are copied. The fixed shape, location and normal-space radius below are
chosen example inputs, not environmental design criteria.
"""

from math import erf, sqrt

import numpy as np

from worldenergydata.metocean.statistics.environmental_contours import (
    EnvironmentalContour,
)
from worldenergydata.metocean.statistics.joint_probability import JointModel


def worked_example():
    """Fit six pairs, then transform the normal-space point (0,1).

    With Weibull shape fixed to one and location zero, log likelihood is
    -n*log(scale)-sum(Hs)/scale; differentiation gives scale=mean(Hs)=2.
    ln(Tp) contains three zeros and three ln(4)'s. Differentiating the normal
    log likelihood gives mu=ln(2) and variance=ln(2)^2. Each Hs bin contains
    the same Tp pair, so zero dependence slopes are imposed explicitly.
    At (u_Hs,u_Tp)=(0,1), p_Hs=1/2 and p_Tp=Phi(1). Thus Hs=2*ln(2),
    Tp=exp(ln(2)+ln(2)*1)=4. This identifies one contour point, not a
    calibrated return-period design condition. The unconstrained backend
    fit is underdetermined on this sample and remains NOT_EVALUATED.
    """
    hs = np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0])
    tp = np.array([1.0, 4.0, 1.0, 4.0, 1.0, 4.0])
    shape, location = 1.0, 0.0
    scale = float(hs.mean())
    mu = float(np.log(tp).mean())
    variance = float(np.log(tp).var())
    model = JointModel(
        {"distribution": "Weibull_fixed_shape", "params": (shape, location, scale)},
        {
            "mu_coefficients": (mu, 0.0, 1.0),
            "variance_coefficients": (variance, 0.0, 1.0),
        },
        len(hs),
        hs_samples=hs,
        tp_samples=tp,
    )
    hs_point, tp_point = EnvironmentalContour.inverse_transform(
        model,
        np.array([0.5]),
        np.array([(1 + erf(1 / sqrt(2))) / 2]),
        weibull=(shape, location, scale),
    )
    return {
        "scale": scale,
        "mu": mu,
        "variance": variance,
        "hs_point": float(hs_point[0]),
        "tp_point": float(tp_point[0]),
        "backend_fit_validation": "NOT_EVALUATED",
    }


if __name__ == "__main__":
    for key, value in worked_example().items():
        print(f"{key}: {value:.1f}" if isinstance(value, float) else f"{key}: {value}")
