# ABOUTME: Arps decline curve forecasting package for production analysis.
# ABOUTME: Exports ArpsDeclineCurve, ForecastResult, and ArpsModel type alias.

"""Arps decline curve production forecasting.

Provides exponential, hyperbolic, and harmonic decline curve fitting,
EUR computation, and forecast generation from historical production data.
"""

from typing import Literal

from worldenergydata.production.forecast.decline import ArpsDeclineCurve, ForecastResult

ArpsModel = Literal["exponential", "hyperbolic", "harmonic"]

__all__ = ["ArpsDeclineCurve", "ForecastResult", "ArpsModel"]
