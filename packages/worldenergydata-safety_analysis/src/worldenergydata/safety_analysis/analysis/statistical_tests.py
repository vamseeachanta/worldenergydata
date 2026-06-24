"""
Statistical Tests for Safety Analysis

Common statistical tests for comparing safety metrics across
groups, time periods, and assets.
"""

from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


def ttest_two_groups(
    group_a: pd.Series,
    group_b: pd.Series,
    equal_var: bool = False,
) -> Dict[str, float]:
    """
    Independent samples t-test between two groups.

    Args:
        group_a: First group of values.
        group_b: Second group of values.
        equal_var: Assume equal variance (False = Welch's t-test).

    Returns:
        Dict with t_statistic, p_value, mean_a, mean_b, effect_size (Cohen's d).
    """
    t_stat, p_val = scipy_stats.ttest_ind(
        group_a.dropna(), group_b.dropna(), equal_var=equal_var
    )

    mean_a = group_a.mean()
    mean_b = group_b.mean()
    pooled_std = np.sqrt((group_a.std() ** 2 + group_b.std() ** 2) / 2)
    cohens_d = (mean_a - mean_b) / pooled_std if pooled_std > 0 else 0.0

    return {
        "t_statistic": float(t_stat),
        "p_value": float(p_val),
        "mean_a": float(mean_a),
        "mean_b": float(mean_b),
        "effect_size": float(cohens_d),
    }


def anova_test(
    groups: List[pd.Series],
) -> Dict[str, float]:
    """
    One-way ANOVA test across multiple groups.

    Args:
        groups: List of Series, one per group.

    Returns:
        Dict with f_statistic, p_value, and group_means.
    """
    cleaned = [g.dropna() for g in groups]
    f_stat, p_val = scipy_stats.f_oneway(*cleaned)

    return {
        "f_statistic": float(f_stat),
        "p_value": float(p_val),
        "group_means": [float(g.mean()) for g in cleaned],
    }


def chi_square_test(
    observed: pd.DataFrame,
) -> Dict[str, float]:
    """
    Chi-square test of independence on a contingency table.

    Args:
        observed: Contingency table (DataFrame or 2D array).

    Returns:
        Dict with chi2_statistic, p_value, degrees_of_freedom, expected_frequencies.
    """
    chi2, p_val, dof, expected = scipy_stats.chi2_contingency(observed)

    return {
        "chi2_statistic": float(chi2),
        "p_value": float(p_val),
        "degrees_of_freedom": int(dof),
    }


def pearson_correlation(x: pd.Series, y: pd.Series) -> Dict[str, float]:
    """
    Pearson correlation coefficient between two series.

    Returns:
        Dict with correlation, p_value.
    """
    mask = x.notna() & y.notna()
    r, p_val = scipy_stats.pearsonr(x[mask], y[mask])
    return {"correlation": float(r), "p_value": float(p_val)}


def spearman_correlation(x: pd.Series, y: pd.Series) -> Dict[str, float]:
    """
    Spearman rank correlation between two series.

    Returns:
        Dict with correlation, p_value.
    """
    mask = x.notna() & y.notna()
    r, p_val = scipy_stats.spearmanr(x[mask], y[mask])
    return {"correlation": float(r), "p_value": float(p_val)}


def linear_regression_summary(x: pd.Series, y: pd.Series) -> Dict[str, float]:
    """
    Simple linear regression summary (observations vs incidents).

    Returns:
        Dict with slope, intercept, r_squared, r_squared_adjusted, p_value.
    """
    mask = x.notna() & y.notna()
    x_clean = x[mask].values
    y_clean = y[mask].values

    slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(
        x_clean, y_clean
    )

    n = len(x_clean)
    r_sq = r_value**2
    r_sq_adj = 1 - ((1 - r_sq) * (n - 1)) / (n - 2) if n > 2 else r_sq

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_sq),
        "r_squared_adjusted": float(r_sq_adj),
        "p_value": float(p_value),
        "std_error": float(std_err),
    }
