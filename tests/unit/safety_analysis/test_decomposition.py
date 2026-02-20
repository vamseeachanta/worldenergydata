"""Tests for safety_analysis.analysis.decomposition module."""

import pytest

from worldenergydata.safety_analysis.analysis.decomposition import (
    _HAS_STATSMODELS,
    _require_statsmodels,
)
from worldenergydata.safety_analysis.exceptions import OptionalDependencyError


class TestRequireStatsmodels:
    def test_flag_is_boolean(self):
        assert isinstance(_HAS_STATSMODELS, bool)

    @pytest.mark.skipif(_HAS_STATSMODELS, reason="statsmodels is installed")
    def test_raises_when_missing(self):
        with pytest.raises(OptionalDependencyError, match="statsmodels"):
            _require_statsmodels()

    @pytest.mark.skipif(not _HAS_STATSMODELS, reason="statsmodels not installed")
    def test_does_not_raise_when_available(self):
        _require_statsmodels()


class TestDecomposeSignalMissing:
    @pytest.mark.skipif(_HAS_STATSMODELS, reason="statsmodels is installed")
    def test_decompose_raises_without_statsmodels(self):
        import pandas as pd
        from worldenergydata.safety_analysis.analysis.decomposition import decompose_signal
        ts = pd.DataFrame({"value": range(24)})
        with pytest.raises(OptionalDependencyError):
            decompose_signal(ts, "value", period=12)

    @pytest.mark.skipif(_HAS_STATSMODELS, reason="statsmodels is installed")
    def test_remove_trend_raises_without_statsmodels(self):
        import pandas as pd
        from worldenergydata.safety_analysis.analysis.decomposition import remove_trend_and_seasonality
        ts = pd.DataFrame({"datetime": range(24), "value": range(24)})
        with pytest.raises(OptionalDependencyError):
            remove_trend_and_seasonality(ts, periods=[12])
