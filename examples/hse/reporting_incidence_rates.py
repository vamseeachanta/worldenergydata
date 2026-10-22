"""Calculate qualified reporting rates from synthetic counts and exposure.

Source: Cal/OSHA, Brief Guide to Recordkeeping Requirements, 2021 PDF revision,
p. 5, Calculating Injury and Illness Incidence Rates:
https://www.dir.ca.gov/dosh/dosh_publications/RecKeepOverview.pdf
See docs/hse/reporting-incidence-rates.md for the method and input contract.
"""

from worldenergydata.bsee.reports.comprehensive.templates.compliance_models import (
    SafetyMetrics,
)


def main() -> None:
    """Print rates for a synthetic population observed over one period."""
    # Synthetic inputs, not acceptance criteria: seven recordables, two of
    # which are lost-time cases, with matching actual employee-hours.
    metrics = SafetyMetrics(
        total_recordables=7,
        lost_time_incidents=2,
        man_hours_worked=400_000,
    )
    # Cited formula: 7 * 200,000 / 400,000 = 3.5;
    #                  2 * 200,000 / 400,000 = 1.0.
    print(f"TRIR: {metrics.calculate_trir():.1f}")
    print(f"LTIR: {metrics.calculate_ltir():.1f}")

    # Zero cases without qualified exposure do not establish a measured zero.
    try:
        SafetyMetrics().calculate_trir()
    except ValueError:
        print("Rate unavailable: supply finite, positive actual employee-hours.")


if __name__ == "__main__":
    main()
