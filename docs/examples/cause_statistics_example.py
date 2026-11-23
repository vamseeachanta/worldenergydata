"""
Example usage of the CauseStatistics module for marine safety incident analysis.

This script demonstrates how to use the statistical analysis capabilities
for analyzing incident causes including frequency distributions, temporal
trends, and cross-tabulations.
"""

from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from worldenergydata.modules.marine_safety.analysis import CauseStatistics
from worldenergydata.modules.marine_safety.database.models import Base
from worldenergydata.modules.marine_safety.constants import SeverityLevel


def main():
    """Run example statistical analyses on incident cause data."""

    # Setup database connection (replace with your actual database URL)
    engine = create_engine('postgresql://user:password@localhost/marine_safety')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Initialize statistics analyzer
    stats = CauseStatistics(session)

    # Example 1: Calculate overall frequency distribution
    print("\n" + "="*60)
    print("EXAMPLE 1: Frequency Distribution of Incident Causes")
    print("="*60)
    distribution = stats.calculate_frequency_distribution(
        include_confidence_intervals=True
    )
    print(distribution.data)
    print(f"\nTotal incidents analyzed: {distribution.total_count}")

    # Export to CSV
    distribution.to_csv('cause_distribution.csv')
    print("\nDistribution exported to: cause_distribution.csv")

    # Example 2: Temporal trends by month
    print("\n" + "="*60)
    print("EXAMPLE 2: Temporal Trends (Monthly)")
    print("="*60)
    trends = stats.calculate_temporal_trends(
        period='month',
        start_date=date(2024, 1, 1)
    )
    print(trends.data.head(10))
    print(f"\nAnalyzed period: {trends.date_range[0]} to {trends.date_range[1]}")

    # Export trends
    trends.to_csv('temporal_trends_monthly.csv')
    print("\nTrends exported to: temporal_trends_monthly.csv")

    # Example 3: Cross-tabulation with severity
    print("\n" + "="*60)
    print("EXAMPLE 3: Causes vs Severity Levels")
    print("="*60)
    crosstab = stats.calculate_cause_severity_crosstab(
        include_percentages=True
    )
    print(crosstab.data)

    # Perform chi-square test
    chi2_result = crosstab.chi_square_test()
    print(f"\nChi-square test results:")
    print(f"  Chi-square statistic: {chi2_result['chi2_statistic']:.2f}")
    print(f"  P-value: {chi2_result['p_value']:.4f}")
    print(f"  Significant relationship: {chi2_result['significant']}")

    # Example 4: Filter by severity level
    print("\n" + "="*60)
    print("EXAMPLE 4: Serious and Catastrophic Incidents Only")
    print("="*60)
    serious_dist = stats.calculate_frequency_distribution(
        min_severity=SeverityLevel.SERIOUS
    )
    print(serious_dist.data)

    # Example 5: Hatch maloperation statistics
    print("\n" + "="*60)
    print("EXAMPLE 5: Hatch/Opening Maloperation Analysis")
    print("="*60)
    hatch_stats = stats.calculate_hatch_maloperation_stats()
    print(f"Total hatch incidents: {hatch_stats['total_incidents']}")
    print(f"Fatalities: {hatch_stats['fatalities']}")
    print(f"Injuries: {hatch_stats['injuries']}")
    print(f"Average severity: {hatch_stats['average_severity']:.2f}")
    print("\nCause distribution:")
    for cause, count in hatch_stats['by_cause'].items():
        print(f"  {cause}: {count}")

    # Example 6: Comprehensive summary report
    print("\n" + "="*60)
    print("EXAMPLE 6: Comprehensive Statistical Summary")
    print("="*60)
    summary = stats.generate_summary_report(
        start_date=date(2023, 1, 1),
        end_date=date(2024, 12, 31)
    )
    summary.print_report()

    # Export summary as JSON
    import json
    with open('statistical_summary.json', 'w') as f:
        json.dump(summary.to_dict(), f, indent=2)
    print("\nSummary exported to: statistical_summary.json")

    # Clean up
    session.close()
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
