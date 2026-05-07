"""
Tests for production_api10 module — covers the #326 bug fix.

Verifies that ProductionAPI10Analysis.router() does not raise
AttributeError because prepare_production_data is now defined on the
class, and that prepare_production_data dispatches per completion to the
existing aggregator methods.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.production_api10 import (
    ProductionAPI10Analysis,
)


@pytest.fixture
def analyzer():
    """Create a ProductionAPI10Analysis instance for tests."""
    return ProductionAPI10Analysis()


@pytest.fixture
def two_completion_df():
    """Two distinct completions with the columns the aggregators read."""
    return pd.DataFrame(
        {
            "COMPLETION_NAME": ["A", "A", "B", "B"],
            "PRODUCTION_DATETIME": [
                "2023-01-01",
                "2023-02-01",
                "2023-01-01",
                "2023-02-01",
            ],
            "O_PROD_RATE_BOPD": [100.0, 110.0, 200.0, 210.0],
            "MON_O_PROD_VOL": [3000.0, 3100.0, 6000.0, 6300.0],
        }
    )


@pytest.fixture
def single_completion_df():
    return pd.DataFrame(
        {
            "COMPLETION_NAME": ["A", "A"],
            "PRODUCTION_DATETIME": ["2023-01-01", "2023-02-01"],
            "O_PROD_RATE_BOPD": [100.0, 110.0],
            "MON_O_PROD_VOL": [3000.0, 3100.0],
        }
    )


class TestProductionAPI10Analysis:

    def test_router_no_attribute_error(self, analyzer, single_completion_df):
        """router() must not raise AttributeError after the fix."""
        analyzer.router({}, single_completion_df)

    def test_prepare_production_data_calls_per_completion_delegates(
        self, analyzer, two_completion_df
    ):
        """For 2 unique completions, each delegate is called twice."""
        with (
            patch.object(analyzer, "prepare_field_production_rate") as mock_rate,
            patch.object(analyzer, "prepare_field_production") as mock_prod,
        ):
            analyzer.prepare_production_data({}, two_completion_df)
            assert mock_rate.call_count == 2
            assert mock_prod.call_count == 2

    def test_prepare_production_data_single_completion(
        self, analyzer, single_completion_df
    ):
        """For 1 unique completion, each delegate is called exactly once."""
        with (
            patch.object(analyzer, "prepare_field_production_rate") as mock_rate,
            patch.object(analyzer, "prepare_field_production") as mock_prod,
        ):
            analyzer.prepare_production_data({}, single_completion_df)
            assert mock_rate.call_count == 1
            assert mock_prod.call_count == 1

    def test_prepare_production_data_empty_dataframe(self, analyzer):
        """Empty DataFrame must short-circuit without calling delegates."""
        with (
            patch.object(analyzer, "prepare_field_production_rate") as mock_rate,
            patch.object(analyzer, "prepare_field_production") as mock_prod,
        ):
            analyzer.prepare_production_data({}, pd.DataFrame())
            mock_rate.assert_not_called()
            mock_prod.assert_not_called()

    def test_prepare_production_data_missing_column(self, analyzer):
        """DataFrame without COMPLETION_NAME must raise ValueError."""
        df = pd.DataFrame({"OTHER_COL": [1, 2, 3]})
        with pytest.raises(ValueError, match="COMPLETION_NAME"):
            analyzer.prepare_production_data({}, df)

    def test_router_invokes_prepare_production_data(
        self, analyzer, single_completion_df
    ):
        """router() forwards (cfg, api12_production_data) to prepare_production_data."""
        cfg = {"sentinel": True}
        with patch.object(analyzer, "prepare_production_data") as mock_prep:
            analyzer.router(cfg, single_completion_df)
            mock_prep.assert_called_once_with(cfg, single_completion_df)

    def test_prepare_production_data_defined_on_instance(self, analyzer):
        """Sanity: method exists on the class (regression guard for #326)."""
        assert hasattr(analyzer, "prepare_production_data")
        assert callable(analyzer.prepare_production_data)
