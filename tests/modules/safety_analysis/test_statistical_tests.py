"""Tests for statistical tests."""

import numpy as np
import pandas as pd

from worldenergydata.modules.safety_analysis.analysis.statistical_tests import (
    anova_test,
    chi_square_test,
    linear_regression_summary,
    pearson_correlation,
    spearman_correlation,
    ttest_two_groups,
)


class TestTTest:
    def test_identical_groups(self):
        a = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        b = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ttest_two_groups(a, b)
        assert result["p_value"] == 1.0
        assert result["t_statistic"] == 0.0

    def test_different_groups(self):
        np.random.seed(42)
        a = pd.Series(np.random.normal(0, 1, 100))
        b = pd.Series(np.random.normal(5, 1, 100))
        result = ttest_two_groups(a, b)
        assert result["p_value"] < 0.05
        assert abs(result["effect_size"]) > 1.0


class TestANOVA:
    def test_identical_groups(self):
        groups = [pd.Series([1, 2, 3])] * 3
        result = anova_test(groups)
        assert result["p_value"] == 1.0

    def test_different_groups(self):
        np.random.seed(42)
        groups = [
            pd.Series(np.random.normal(0, 1, 50)),
            pd.Series(np.random.normal(5, 1, 50)),
            pd.Series(np.random.normal(10, 1, 50)),
        ]
        result = anova_test(groups)
        assert result["p_value"] < 0.05


class TestChiSquare:
    def test_basic_contingency(self):
        table = pd.DataFrame([[10, 20], [30, 40]])
        result = chi_square_test(table)
        assert "chi2_statistic" in result
        assert "p_value" in result
        assert result["degrees_of_freedom"] == 1


class TestCorrelations:
    def test_pearson_perfect(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
        result = pearson_correlation(x, y)
        assert abs(result["correlation"] - 1.0) < 1e-10

    def test_spearman_monotonic(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([1.0, 4.0, 9.0, 16.0, 25.0])
        result = spearman_correlation(x, y)
        assert abs(result["correlation"] - 1.0) < 1e-10


class TestLinearRegression:
    def test_perfect_linear(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
        result = linear_regression_summary(x, y)
        assert abs(result["r_squared"] - 1.0) < 1e-10
        assert abs(result["slope"] - 2.0) < 1e-10
        assert abs(result["intercept"]) < 1e-10

    def test_has_all_keys(self):
        x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        y = pd.Series([1.1, 2.3, 2.8, 4.2, 5.1])
        result = linear_regression_summary(x, y)
        assert "slope" in result
        assert "intercept" in result
        assert "r_squared" in result
        assert "r_squared_adjusted" in result
        assert "p_value" in result
        assert "std_error" in result
