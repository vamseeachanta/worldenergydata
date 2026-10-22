"""Calendar exposure is an inclusive count, not elapsed fractional time."""

import pandas as pd
import pytest

from worldenergydata.well_planning.risk_calibrator import RiskCalibrator


@pytest.mark.parametrize(
    "time_column",
    [
        {"year": [2020, 2021]},
        {"date": ["2020-12-31", "2021-01-01"]},
        {"incident_date": pd.to_datetime(["2020-01-01", "2021-12-31"])},
    ],
)
def test_two_calendar_years_count_both_endpoints(time_column):
    """Inclusive integer cardinality: {2020, 2021} contains two years.

    Independent hand count is 2021 - 2020 + 1 = 2, even when the two
    observations are only one day apart. This is the calendar-exposure
    convention, not evidence that the observation interval is complete.
    """
    frame = pd.DataFrame(
        dict(
            incident_type=["kick"] * 2, sub_type=["pressure_control"] * 2, **time_column
        )
    )
    report = RiskCalibrator().calibrate(frame).calibration_report()
    assert report.years_covered == 2
    record = next(r for r in report.records if r.risk_id == "OP-002")
    assert record.events_per_year == 1  # Two default-weight records / two years.


@pytest.mark.parametrize(
    "values", [[2020, 2021], [2020.0, 2021.0], [2020, "2021-01-01"]]
)
@pytest.mark.parametrize("column", ["date", "incident_date"])
def test_numeric_date_values_rejected_with_message(values, column):
    frame = pd.DataFrame(
        dict(
            incident_type=["kick"] * 2,
            sub_type=["pressure_control"] * 2,
            year=[2020, 2021],
            **{column: values},
        )
    )
    with pytest.raises(ValueError, match="numeric.*year column"):
        RiskCalibrator().calibrate(frame)


def test_missing_dates_retain_existing_fallback():
    frame = pd.DataFrame(
        {
            "incident_type": ["kick"],
            "sub_type": ["pressure_control"],
            "date": [float("nan")],
        }
    )
    report = RiskCalibrator().calibrate(frame).calibration_report()
    assert (
        report.years_covered == 1
    )  # Existing missing-time fallback, not an exposure claim.
