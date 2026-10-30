"""Annual-max selector dispatch, independent of the optional fitting backend.

All dates, heights (m), periods (years) and backend levels (m) below are
stipulated synthetic dispatch sentinels. The independent expected mapping is
simply the two supplied period/level pairs; no statistical fit is asserted.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def annual_maxima(monkeypatch):
    """Load the real wrapper with isolated, function-scoped backend spies."""
    periods = [10, 100]
    levels = {10: 4.0, 100: 6.0}
    stats = ModuleType("metocean_stats.stats")
    stats.return_levels_annual_max = Mock(
        return_value=pd.DataFrame(
            {"return_levels": list(levels.values())}, index=periods
        )
    )
    stats.return_levels_annual_max_uncertainty = Mock(return_value=pd.DataFrame())
    backend = ModuleType("metocean_stats")
    backend.stats = stats
    monkeypatch.setitem(sys.modules, "metocean_stats", backend)
    monkeypatch.setitem(sys.modules, "metocean_stats.stats", stats)

    source = (
        Path(__file__).resolve().parents[3]
        / "packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/eva.py"
    )
    spec = importlib.util.spec_from_file_location("_annual_maxima_contract_eva", source)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    series = pd.Series(
        [1.0, 2.0, 3.0],
        index=pd.to_datetime(["2000-01-01", "2001-01-01", "2002-01-01"]),
        name="hs",
    )
    return SimpleNamespace(
        eva=module.ExtremeValueAnalysis(),
        stats=stats,
        series=series,
        periods=periods,
        levels=levels,
    )


@pytest.mark.parametrize(
    "distribution",
    [
        "",
        "Weibull_2P",
        "GPD",
        "GUMBEL",
        "gev",
        "gum",
        "Gev",
        " GEV",
        "GUM ",
        " \t",
        None,
        0,
        1.0,
        True,
        b"GEV",
        ["GEV"],
        {"distribution": "GEV"},
        np.array(["GEV", "GUM"]),
        pd.NA,
    ],
    ids=[
        "empty",
        "pot-distribution",
        "unsupported-gpd",
        "alias",
        "lowercase-gev",
        "lowercase-gum",
        "mixed-case",
        "leading-space",
        "trailing-space",
        "whitespace",
        "none",
        "integer",
        "float",
        "boolean",
        "bytes",
        "list",
        "mapping",
        "array",
        "missing-value",
    ],
)
def test_invalid_distribution_rejected_before_backend(annual_maxima, distribution):
    point_fit = annual_maxima.stats.return_levels_annual_max
    uncertainty_fit = annual_maxima.stats.return_levels_annual_max_uncertainty
    try:
        with pytest.raises(ValueError, match="GEV.*GUM"):
            annual_maxima.eva.fit_annual_maxima(
                annual_maxima.series,
                distribution=distribution,
                periods=annual_maxima.periods,
            )
    finally:
        point_fit.assert_not_called()
        uncertainty_fit.assert_not_called()


@pytest.mark.parametrize(
    "kwargs,expected",
    [({}, "GEV"), ({"distribution": "GEV"}, "GEV"), ({"distribution": "GUM"}, "GUM")],
    ids=["default-gev", "gev", "gum"],
)
def test_supported_distributions_forward_unchanged(annual_maxima, kwargs, expected):
    result = annual_maxima.eva.fit_annual_maxima(
        annual_maxima.series, periods=annual_maxima.periods, **kwargs
    )

    for backend_call in (
        annual_maxima.stats.return_levels_annual_max,
        annual_maxima.stats.return_levels_annual_max_uncertainty,
    ):
        backend_call.assert_called_once()
        arguments = backend_call.call_args.kwargs
        assert arguments["dist"] == expected
        assert arguments["periods"] is annual_maxima.periods
        assert arguments["var"] == annual_maxima.series.name
        pd.testing.assert_frame_equal(
            arguments["data"], annual_maxima.series.to_frame()
        )
    assert (
        annual_maxima.stats.return_levels_annual_max_uncertainty.call_args.kwargs[
            "uncertainty"
        ]
        is None
    )
    assert result.method == "AM"
    assert result.distribution == expected
    assert result.return_levels == annual_maxima.levels
