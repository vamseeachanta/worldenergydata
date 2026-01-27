# ABOUTME: Demonstrates extreme value analysis using the metocean-statistics skill.
# ABOUTME: Calculates return periods for wave heights using GEV distribution fitting.

"""
Extreme Value Analysis for Metocean Data - Return Period Calculation

This script demonstrates the statistical analysis workflow for calculating
extreme wave height return periods as documented in the metocean-statistics skill.

Workflow:
1. Generate synthetic wave height data (10 years of hourly observations)
2. Extract annual maxima using block maxima method
3. Fit GEV (Generalized Extreme Value) distribution using scipy.stats
4. Calculate return levels for standard return periods
5. Output formatted results table

Reference: metocean-statistics skill documentation
"""

import numpy as np
from scipy import stats
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple


def generate_synthetic_wave_data(
    n_years: int = 10,
    base_hs: float = 1.5,
    seasonal_amplitude: float = 0.8,
    storm_probability: float = 0.02,
    storm_hs_factor: float = 3.0,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate synthetic significant wave height data with realistic characteristics.

    Simulates hourly wave observations with:
    - Seasonal variation (higher waves in winter)
    - Random storms with elevated wave heights
    - Log-normal base distribution for typical conditions

    Args:
        n_years: Number of years of data to generate
        base_hs: Mean significant wave height (meters)
        seasonal_amplitude: Amplitude of seasonal variation (meters)
        storm_probability: Probability of storm conditions per hour
        storm_hs_factor: Multiplier for wave height during storms
        seed: Random seed for reproducibility

    Returns:
        DataFrame with columns: ['time', 'Hs_m']
    """
    np.random.seed(seed)

    # Generate hourly timestamps
    start_date = datetime(2014, 1, 1)
    n_hours = n_years * 365 * 24
    times = [start_date + timedelta(hours=i) for i in range(n_hours)]

    # Generate base wave heights (log-normal distribution)
    wave_heights = np.random.lognormal(
        mean=np.log(base_hs),
        sigma=0.4,
        size=n_hours
    )

    # Add seasonal variation (higher in winter months)
    day_of_year = np.array([t.timetuple().tm_yday for t in times])
    seasonal_factor = 1 + seasonal_amplitude * np.cos(2 * np.pi * (day_of_year - 15) / 365)
    wave_heights = wave_heights * seasonal_factor

    # Add storm events
    storm_mask = np.random.random(n_hours) < storm_probability
    storm_enhancement = np.where(storm_mask, storm_hs_factor, 1.0)
    wave_heights = wave_heights * storm_enhancement

    # Add persistence (waves don't change instantly)
    # Apply simple exponential smoothing
    alpha = 0.3
    smoothed = np.zeros_like(wave_heights)
    smoothed[0] = wave_heights[0]
    for i in range(1, len(wave_heights)):
        smoothed[i] = alpha * wave_heights[i] + (1 - alpha) * smoothed[i-1]

    return pd.DataFrame({
        'time': times,
        'Hs_m': smoothed
    })


def extract_annual_maxima(df: pd.DataFrame) -> np.ndarray:
    """
    Extract annual maximum wave heights using block maxima method.

    Args:
        df: DataFrame with 'time' and 'Hs_m' columns

    Returns:
        Array of annual maximum wave heights
    """
    df = df.copy()
    df['year'] = pd.to_datetime(df['time']).dt.year
    annual_max = df.groupby('year')['Hs_m'].max().values
    return annual_max


def fit_gev_distribution(annual_maxima: np.ndarray) -> Tuple[float, float, float]:
    """
    Fit GEV (Generalized Extreme Value) distribution to annual maxima.

    The GEV distribution is the standard choice for block maxima analysis.
    It encompasses three distribution families:
    - Type I (Gumbel): shape = 0
    - Type II (Frechet): shape > 0
    - Type III (Weibull): shape < 0

    Args:
        annual_maxima: Array of annual maximum values

    Returns:
        Tuple of (shape, location, scale) parameters
    """
    # scipy.stats.genextreme uses negative shape convention
    shape, loc, scale = stats.genextreme.fit(annual_maxima)
    return shape, loc, scale


def calculate_return_level(
    return_period: float,
    shape: float,
    loc: float,
    scale: float
) -> float:
    """
    Calculate return level for a given return period.

    The return level is the value expected to be exceeded once every T years.

    Args:
        return_period: Return period in years
        shape: GEV shape parameter
        loc: GEV location parameter
        scale: GEV scale parameter

    Returns:
        Return level value
    """
    # Non-exceedance probability
    p = 1 - 1 / return_period
    return stats.genextreme.ppf(p, shape, loc=loc, scale=scale)


def calculate_return_periods_table(
    annual_maxima: np.ndarray,
    return_periods: list[int] = None
) -> pd.DataFrame:
    """
    Calculate return levels for multiple return periods with confidence intervals.

    Uses bootstrap resampling to estimate 95% confidence intervals.

    Args:
        annual_maxima: Array of annual maximum values
        return_periods: List of return periods to calculate (years)

    Returns:
        DataFrame with return periods and levels
    """
    if return_periods is None:
        return_periods = [1, 10, 50, 100, 500]

    # Fit GEV to full dataset
    shape, loc, scale = fit_gev_distribution(annual_maxima)

    # Calculate return levels
    results = []
    n_bootstrap = 1000

    for T in return_periods:
        # Point estimate
        rl = calculate_return_level(T, shape, loc, scale)

        # Bootstrap confidence intervals
        bootstrap_rls = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(annual_maxima, size=len(annual_maxima), replace=True)
            s, l, sc = stats.genextreme.fit(sample)
            bootstrap_rls.append(calculate_return_level(T, s, l, sc))

        ci_lower = np.percentile(bootstrap_rls, 2.5)
        ci_upper = np.percentile(bootstrap_rls, 97.5)

        results.append({
            'Return Period (years)': T,
            'Hs (m)': round(rl, 2),
            'Lower 95% CI (m)': round(ci_lower, 2),
            'Upper 95% CI (m)': round(ci_upper, 2)
        })

    return pd.DataFrame(results)


def assess_gev_fit(annual_maxima: np.ndarray, shape: float, loc: float, scale: float) -> dict:
    """
    Assess goodness of fit for the GEV distribution.

    Args:
        annual_maxima: Array of annual maximum values
        shape: GEV shape parameter
        loc: GEV location parameter
        scale: GEV scale parameter

    Returns:
        Dictionary with fit assessment metrics
    """
    # Kolmogorov-Smirnov test
    ks_stat, ks_pvalue = stats.kstest(
        annual_maxima,
        'genextreme',
        args=(shape, loc, scale)
    )

    # Anderson-Darling test (using scipy's version for genextreme)
    # Note: scipy doesn't have AD test for genextreme directly,
    # so we use the KS test and empirical checks

    # Calculate empirical vs theoretical quantiles for QQ assessment
    sorted_data = np.sort(annual_maxima)
    n = len(sorted_data)
    theoretical_quantiles = stats.genextreme.ppf(
        (np.arange(1, n + 1) - 0.5) / n,
        shape, loc=loc, scale=scale
    )

    # R-squared for QQ plot
    correlation = np.corrcoef(sorted_data, theoretical_quantiles)[0, 1]
    r_squared = correlation ** 2

    return {
        'ks_statistic': round(ks_stat, 4),
        'ks_pvalue': round(ks_pvalue, 4),
        'qq_r_squared': round(r_squared, 4),
        'shape_parameter': round(shape, 4),
        'location_parameter': round(loc, 4),
        'scale_parameter': round(scale, 4)
    }


def print_formatted_results(
    df: pd.DataFrame,
    data_summary: dict,
    fit_assessment: dict
) -> None:
    """
    Print results in a formatted table with headers.

    Args:
        df: DataFrame with return period results
        data_summary: Summary statistics of input data
        fit_assessment: GEV fit assessment metrics
    """
    print("=" * 70)
    print("EXTREME VALUE ANALYSIS - SIGNIFICANT WAVE HEIGHT RETURN PERIODS")
    print("=" * 70)
    print()

    # Data summary
    print("DATA SUMMARY")
    print("-" * 40)
    print(f"  Record length:        {data_summary['n_years']} years")
    print(f"  Total observations:   {data_summary['n_observations']:,}")
    print(f"  Annual maxima count:  {data_summary['n_annual_max']}")
    print(f"  Overall maximum Hs:   {data_summary['overall_max']:.2f} m")
    print(f"  Mean annual maximum:  {data_summary['mean_annual_max']:.2f} m")
    print()

    # GEV fit assessment
    print("GEV DISTRIBUTION FIT")
    print("-" * 40)
    print(f"  Shape (xi):           {fit_assessment['shape_parameter']:.4f}")
    print(f"  Location (mu):        {fit_assessment['location_parameter']:.4f}")
    print(f"  Scale (sigma):        {fit_assessment['scale_parameter']:.4f}")
    print(f"  KS test statistic:    {fit_assessment['ks_statistic']:.4f}")
    print(f"  KS test p-value:      {fit_assessment['ks_pvalue']:.4f}")
    print(f"  QQ plot R-squared:    {fit_assessment['qq_r_squared']:.4f}")

    # Interpret shape parameter
    if fit_assessment['shape_parameter'] < -0.1:
        dist_type = "Type III (Weibull) - bounded upper tail"
    elif fit_assessment['shape_parameter'] > 0.1:
        dist_type = "Type II (Frechet) - heavy upper tail"
    else:
        dist_type = "Type I (Gumbel) - light upper tail"
    print(f"  Distribution type:    {dist_type}")
    print()

    # Return periods table
    print("RETURN PERIOD TABLE")
    print("-" * 70)
    print(f"{'Return Period':>15} {'Hs (m)':>12} {'Lower 95% CI':>15} {'Upper 95% CI':>15}")
    print(f"{'(years)':>15} {'':>12} {'(m)':>15} {'(m)':>15}")
    print("-" * 70)

    for _, row in df.iterrows():
        rp = int(row['Return Period (years)'])
        hs = row['Hs (m)']
        lower = row['Lower 95% CI (m)']
        upper = row['Upper 95% CI (m)']
        print(f"{rp:>15} {hs:>12.2f} {lower:>15.2f} {upper:>15.2f}")

    print("-" * 70)
    print()
    print("Notes:")
    print("  - Confidence intervals calculated using bootstrap resampling (n=1000)")
    print("  - GEV distribution fitted using Maximum Likelihood Estimation (MLE)")
    print("  - Return levels represent values expected to be exceeded once per period")
    print("=" * 70)


def run_extreme_value_analysis(
    n_years: int = 10,
    return_periods: list[int] = None,
    seed: int = 42,
    verbose: bool = True
) -> Tuple[pd.DataFrame, dict, dict]:
    """
    Run complete extreme value analysis workflow.

    Args:
        n_years: Years of synthetic data to generate
        return_periods: Return periods to calculate
        seed: Random seed for reproducibility
        verbose: Whether to print formatted results

    Returns:
        Tuple of (results_df, data_summary, fit_assessment)
    """
    if return_periods is None:
        return_periods = [1, 10, 50, 100, 500]

    # Step 1: Generate synthetic data
    df = generate_synthetic_wave_data(n_years=n_years, seed=seed)

    # Step 2: Extract annual maxima
    annual_max = extract_annual_maxima(df)

    # Step 3: Fit GEV distribution
    shape, loc, scale = fit_gev_distribution(annual_max)

    # Step 4: Calculate return periods
    results_df = calculate_return_periods_table(annual_max, return_periods)

    # Prepare summaries
    data_summary = {
        'n_years': n_years,
        'n_observations': len(df),
        'n_annual_max': len(annual_max),
        'overall_max': df['Hs_m'].max(),
        'mean_annual_max': annual_max.mean()
    }

    fit_assessment = assess_gev_fit(annual_max, shape, loc, scale)

    # Step 5: Print results
    if verbose:
        print_formatted_results(results_df, data_summary, fit_assessment)

    return results_df, data_summary, fit_assessment


# ============================================================================
# PYTEST TEST FUNCTIONS
# ============================================================================

class TestExtremeValueAnalysis:
    """Test suite for extreme value analysis functions."""

    def test_generate_synthetic_data_shape(self):
        """Test that synthetic data has correct shape and columns."""
        df = generate_synthetic_wave_data(n_years=2, seed=42)

        assert 'time' in df.columns
        assert 'Hs_m' in df.columns
        # 2 years * 365 days * 24 hours
        expected_rows = 2 * 365 * 24
        assert len(df) == expected_rows

    def test_generate_synthetic_data_values(self):
        """Test that synthetic data has realistic wave height values."""
        df = generate_synthetic_wave_data(n_years=5, seed=42)

        # Wave heights should be positive
        assert df['Hs_m'].min() > 0
        # Typical ocean waves rarely exceed 15m
        assert df['Hs_m'].max() < 20
        # Mean should be reasonable
        assert 0.5 < df['Hs_m'].mean() < 5

    def test_annual_maxima_extraction(self):
        """Test annual maxima extraction returns correct number of values."""
        df = generate_synthetic_wave_data(n_years=10, seed=42)
        annual_max = extract_annual_maxima(df)

        assert len(annual_max) == 10
        # All maxima should be positive
        assert all(annual_max > 0)

    def test_gev_fit_parameters(self):
        """Test GEV fit returns valid parameters."""
        df = generate_synthetic_wave_data(n_years=10, seed=42)
        annual_max = extract_annual_maxima(df)
        shape, loc, scale = fit_gev_distribution(annual_max)

        # Shape should be reasonable for ocean waves (-0.5 to 0.5)
        assert -1 < shape < 1
        # Location should be positive
        assert loc > 0
        # Scale should be positive
        assert scale > 0

    def test_return_level_monotonic(self):
        """Test that return levels increase with return period."""
        df = generate_synthetic_wave_data(n_years=10, seed=42)
        annual_max = extract_annual_maxima(df)
        shape, loc, scale = fit_gev_distribution(annual_max)

        return_periods = [1, 10, 50, 100, 500]
        return_levels = [
            calculate_return_level(T, shape, loc, scale)
            for T in return_periods
        ]

        # Return levels should be monotonically increasing
        for i in range(1, len(return_levels)):
            assert return_levels[i] > return_levels[i-1]

    def test_return_periods_table_structure(self):
        """Test return periods table has correct structure."""
        df = generate_synthetic_wave_data(n_years=10, seed=42)
        annual_max = extract_annual_maxima(df)
        results = calculate_return_periods_table(annual_max, [1, 10, 100])

        assert len(results) == 3
        assert 'Return Period (years)' in results.columns
        assert 'Hs (m)' in results.columns
        assert 'Lower 95% CI (m)' in results.columns
        assert 'Upper 95% CI (m)' in results.columns

    def test_confidence_intervals_ordering(self):
        """Test that confidence intervals are properly ordered."""
        df = generate_synthetic_wave_data(n_years=10, seed=42)
        annual_max = extract_annual_maxima(df)
        results = calculate_return_periods_table(annual_max, [100])

        row = results.iloc[0]
        # Lower CI < point estimate < Upper CI
        assert row['Lower 95% CI (m)'] < row['Hs (m)']
        assert row['Hs (m)'] < row['Upper 95% CI (m)']

    def test_fit_assessment_metrics(self):
        """Test GEV fit assessment returns expected metrics."""
        df = generate_synthetic_wave_data(n_years=10, seed=42)
        annual_max = extract_annual_maxima(df)
        shape, loc, scale = fit_gev_distribution(annual_max)
        assessment = assess_gev_fit(annual_max, shape, loc, scale)

        assert 'ks_statistic' in assessment
        assert 'ks_pvalue' in assessment
        assert 'qq_r_squared' in assessment
        # KS statistic should be between 0 and 1
        assert 0 <= assessment['ks_statistic'] <= 1
        # R-squared should be close to 1 for a good fit
        assert assessment['qq_r_squared'] > 0.9

    def test_full_analysis_workflow(self):
        """Test complete analysis workflow runs without error."""
        results_df, data_summary, fit_assessment = run_extreme_value_analysis(
            n_years=5,
            return_periods=[1, 10, 100],
            seed=42,
            verbose=False
        )

        assert len(results_df) == 3
        assert data_summary['n_years'] == 5
        assert 'shape_parameter' in fit_assessment

    def test_reproducibility_with_seed(self):
        """Test that results are reproducible with same seed."""
        results1, _, _ = run_extreme_value_analysis(n_years=5, seed=123, verbose=False)
        results2, _, _ = run_extreme_value_analysis(n_years=5, seed=123, verbose=False)

        pd.testing.assert_frame_equal(results1, results2)

    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different results."""
        results1, _, _ = run_extreme_value_analysis(n_years=5, seed=123, verbose=False)
        results2, _, _ = run_extreme_value_analysis(n_years=5, seed=456, verbose=False)

        # Results should differ
        assert not results1['Hs (m)'].equals(results2['Hs (m)'])


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    """
    Main execution: demonstrate the extreme value analysis workflow.

    This demonstrates the statistical analysis workflow documented in the
    metocean-statistics skill for calculating return periods using GEV
    distribution fitting.
    """
    print()
    print("Metocean Statistics Skill Demonstration")
    print("Return Period Analysis for Significant Wave Height")
    print()

    # Run the analysis
    results_df, data_summary, fit_assessment = run_extreme_value_analysis(
        n_years=10,
        return_periods=[1, 10, 50, 100, 500],
        seed=42,
        verbose=True
    )

    print()
    print("Analysis complete. Results stored in DataFrame.")
    print()
    print("DataFrame contents:")
    print(results_df.to_string(index=False))
