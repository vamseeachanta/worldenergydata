"""
ABOUTME: Metocean statistical analysis engine — wraps metocean-stats v1.1.9.
ABOUTME: Provides EVA, joint probability, environmental contours, weather windows.

Statistical Analysis Module
============================

Powered by the real metocean-stats library (MET-OM/metocean-stats v1.1.9).
All visualisations use Plotly for interactive HTML output.

Modules
-------
eva                    Extreme Value Analysis (POT + annual maxima)
joint_probability      Hs-Tp joint probability / CMA fitting
environmental_contours IFORM/ISORM environmental contours
weather_windows        Operability % and weather window persistence
wave_spectra           JONSWAP, Torsethaugen, spectral moments
scatter_diagram        2D Hs-Tp occurrence tables
reporting              Combined Plotly HTML report
"""

from worldenergydata.metocean.statistics.environmental_contours import (
    ContourResult,
    EnvironmentalContour,
)
from worldenergydata.metocean.statistics.eva import (
    EVAResult,
    ExtremeValueAnalysis,
)
from worldenergydata.metocean.statistics.joint_probability import (
    JointModel,
    JointProbabilityModel,
)
from worldenergydata.metocean.statistics.reporting import MetoceanReport
from worldenergydata.metocean.statistics.scatter_diagram import ScatterDiagram
from worldenergydata.metocean.statistics.wave_spectra import (
    SpectralResult,
    WaveSpectra,
)
from worldenergydata.metocean.statistics.weather_windows import (
    OperabilityResult,
    WeatherWindowAnalysis,
)

__all__ = [
    # EVA
    "EVAResult",
    "ExtremeValueAnalysis",
    # Joint probability
    "JointModel",
    "JointProbabilityModel",
    # Environmental contours
    "ContourResult",
    "EnvironmentalContour",
    # Weather windows
    "OperabilityResult",
    "WeatherWindowAnalysis",
    # Wave spectra
    "SpectralResult",
    "WaveSpectra",
    # Scatter diagram
    "ScatterDiagram",
    # Reporting
    "MetoceanReport",
]

# Backend note: uses real metocean-stats library (not stubs)
BACKEND = "metocean-stats"
BACKEND_VERSION = "1.1.9"
