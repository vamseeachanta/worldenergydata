"""Analysis components for safety data.

Modules:
    time_series: Time series construction and normalization
    correlation: Lag cross-correlation analysis
    feature_engineering: Statistical/FFT feature extraction
    incident_aggregation: Severity aggregation and hurt indices
    statistical_tests: Hypothesis testing (t-test, ANOVA, chi-square)
    decomposition: Seasonal decomposition (optional statsmodels)
"""

from worldenergydata.modules.safety_analysis.analysis.correlation import (
    LaggedCrossCorrelation,
    create_incident_counts,
    create_observation_counts,
    crosscorr,
    extract_asset_rates,
)
from worldenergydata.modules.safety_analysis.analysis.feature_engineering import (
    FeatureEngineer,
)
from worldenergydata.modules.safety_analysis.analysis.incident_aggregation import (
    aggregate_by_group,
    aggregate_by_severity,
    aggregate_by_time,
    compute_hurt_index,
    compute_time_series_hurt_index,
)
from worldenergydata.modules.safety_analysis.analysis.statistical_tests import (
    anova_test,
    chi_square_test,
    linear_regression_summary,
    pearson_correlation,
    spearman_correlation,
    ttest_two_groups,
)
from worldenergydata.modules.safety_analysis.analysis.time_series import (
    TimeSeriesBuilder,
    calculate_gradient,
    calculate_moving_average,
    calculate_multiple_moving_averages,
)

__all__ = [
    # Time series
    "TimeSeriesBuilder",
    "calculate_gradient",
    "calculate_moving_average",
    "calculate_multiple_moving_averages",
    # Correlation
    "LaggedCrossCorrelation",
    "crosscorr",
    "create_observation_counts",
    "create_incident_counts",
    "extract_asset_rates",
    # Feature engineering
    "FeatureEngineer",
    # Incident aggregation
    "aggregate_by_severity",
    "aggregate_by_time",
    "aggregate_by_group",
    "compute_hurt_index",
    "compute_time_series_hurt_index",
    # Statistical tests
    "ttest_two_groups",
    "anova_test",
    "chi_square_test",
    "pearson_correlation",
    "spearman_correlation",
    "linear_regression_summary",
]
