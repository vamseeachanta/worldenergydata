"""Value checks for date totals and trailing means of synthetic rig counts.

Mathematical reference: NIST/SEMATECH e-Handbook of Statistical Methods,
section 6.4.2.1, Single Moving Average, online edition accessed 2026-10-19:
https://www.itl.nist.gov/div898/handbook/pmc/section4/pmc421.htm
All counts and window lengths below are synthetic test inputs, not field data
or recommended engineering limits. Expected values are calculated by hand.
"""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from worldenergydata.baker_hughes import aggregate_rig_counts, load_summary


def test_date_totals_and_trailing_mean():
    """Reproduce the reference's first five observations as synthetic counts.

    Disjoint rows sum to 4+5=9, 3+5=8, 2+7=9, 5+7=12, 4+5=9 rigs.
    With a supplied three-observation window, the full trailing means are
    (9+8+9)/3 = 26/3, (8+9+12)/3 = 29/3, (9+12+9)/3 = 10 rigs.
    NIST section 6.4.2.1 publishes the same input sequence and rounded means.
    The first two means are undefined because the window is incomplete.
    """
    dates = pd.date_range("2026-01-02", periods=5, freq="7D")
    rows = pd.DataFrame(
        {"date": dates.repeat(2), "rig_count": [4, 5, 3, 5, 2, 7, 5, 7, 4, 5]}
    ).iloc[::-1]
    original = rows.copy(deep=True)

    result = aggregate_rig_counts(rows, window=3)

    expected = pd.DataFrame(
        {
            "date": dates,
            "rig_count": [9, 8, 9, 12, 9],
            "rolling_mean": [float("nan"), float("nan"), 26 / 3, 29 / 3, 10.0],
        }
    )
    assert_frame_equal(result, expected, check_exact=True)
    assert_frame_equal(rows, original, check_exact=True)


def test_missing_dates_are_not_zero_filled():
    """Two supplied totals 6 and 10 give (6+10)/2=8, despite a date gap.

    The supplied window counts observations, following NIST section 6.4.2.1;
    no observation or count is inferred for the absent intervening week.
    """
    rows = pd.DataFrame({"date": ["2026-01-02", "2026-01-16"], "rig_count": [6, 10]})
    result = aggregate_rig_counts(rows, window=2)
    assert result["rig_count"].tolist() == [6, 10]
    assert pd.isna(result.loc[0, "rolling_mean"])
    assert result.loc[1, "rolling_mean"] == 8.0


def test_summary_loader_to_date_totals(tmp_path):
    """Disjoint synthetic rows total 4+5=9 and 3+5=8, mean (9+8)/2=8.5.

    The mean uses NIST section 6.4.2.1; no workbook values are field data.
    This checks the existing wide-to-long loader followed by aggregation.
    """
    dates = pd.to_datetime(["2026-01-02", "2026-01-09"])
    workbook = tmp_path / "synthetic-counts.xlsx"
    pd.DataFrame({"state": ["A", "B"], dates[0]: [4, 5], dates[1]: [3, 5]}).to_excel(
        workbook, sheet_name="Rigs by State", index=False
    )

    result = aggregate_rig_counts(load_summary(workbook), window=2)

    assert result["rig_count"].tolist() == [9, 8]
    assert pd.isna(result.loc[0, "rolling_mean"])
    assert result.loc[1, "rolling_mean"] == 8.5


def test_intraday_records_share_calendar_date():
    """Two disjoint counts in one calendar date sum to 4+5=9, mean 9/1=9."""
    rows = pd.DataFrame(
        {"date": ["2026-01-02 08:00", "2026-01-02 16:00"], "rig_count": [4, 5]}
    )
    result = aggregate_rig_counts(rows, window=1)
    assert result["date"].tolist() == [pd.Timestamp("2026-01-02")]
    assert result["rig_count"].tolist() == [9]
    assert result["rolling_mean"].tolist() == [9.0]


@pytest.mark.parametrize("window", [1, 3])
def test_zero_counts_and_incomplete_window(window):
    """A single observed zero has mean 0/1=0 only for a complete window.

    NIST section 6.4.2.1 requires the supplied number of observations.
    A window of three has no complete mean in this one-observation fixture.
    """
    rows = pd.DataFrame({"date": ["2026-01-02"], "rig_count": [0]})
    result = aggregate_rig_counts(rows, window=window)
    assert result.loc[0, "rig_count"] == 0
    if window == 1:
        assert result.loc[0, "rolling_mean"] == 0.0
    else:
        assert pd.isna(result.loc[0, "rolling_mean"])


def test_empty_input_has_declared_output_columns():
    """An empty series contains no complete window or inferred counts."""
    rows = pd.DataFrame(
        {"date": pd.Series(dtype="datetime64[ns]"), "rig_count": pd.Series(dtype=int)}
    )
    result = aggregate_rig_counts(rows, window=3)
    assert result.empty
    assert result.columns.tolist() == ["date", "rig_count", "rolling_mean"]


@pytest.mark.parametrize("window", [0, -1, 1.5, True, "3", None])
def test_invalid_window_is_rejected(window):
    """A finite observation count must be a positive integer (NIST formula)."""
    rows = pd.DataFrame({"date": ["2026-01-02"], "rig_count": [1]})
    with pytest.raises(ValueError, match="window"):
        aggregate_rig_counts(rows, window=window)


@pytest.mark.parametrize(
    "count", [None, float("nan"), float("inf"), -1, 1.5, True, "bad"]
)
def test_invalid_count_is_rejected(count):
    """Input contract: counts are known, finite, nonnegative whole rigs.

    These synthetic counterexamples test the count definition, not a physical
    acceptance threshold. Missing observations must never become true zeros.
    """
    rows = pd.DataFrame({"date": ["2026-01-02"], "rig_count": [count]})
    with pytest.raises(ValueError, match="rig_count"):
        aggregate_rig_counts(rows, window=1)


@pytest.mark.parametrize("date", [None, "bad", "2026-01-02T00:00:00Z", 1])
def test_invalid_date_is_rejected(date):
    """The date-key contract excludes missing, invalid and zoned timestamps."""
    rows = pd.DataFrame({"date": [date], "rig_count": [1]})
    with pytest.raises(ValueError, match="date"):
        aggregate_rig_counts(rows, window=1)


@pytest.mark.parametrize("column", ["date", "rig_count"])
def test_required_column_is_rejected_when_absent(column):
    rows = pd.DataFrame({"date": ["2026-01-02"], "rig_count": [1]}).drop(columns=column)
    with pytest.raises(ValueError, match=column):
        aggregate_rig_counts(rows, window=1)
