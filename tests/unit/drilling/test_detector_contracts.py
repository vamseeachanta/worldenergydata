"""Detector contracts; all data are synthetic arithmetic/calendar fixtures.

Removing row validation, using fixed-length months, discarding fractional days,
or returning a clipped/default fit without its status must fail these tests.
"""

import math

import pandas as pd
import pytest

from worldenergydata.drilling.batch_economics.bsee_batch_detector import (
    BSEEBatchDetector,
)


def activities(dates):
    return pd.DataFrame(
        {
            "well_id": [f"W{i}" for i in range(len(dates))],
            "rig_name": ["R"] * len(dates),
            "field_name": ["F"] * len(dates),
            "spud_date": dates,
        }
    )


def test_reconciliation_preserves_positions_and_does_not_mutate():
    """Five inputs = two accepted + two rejected + one exact duplicate."""
    df = activities(["2024-01-01", "2024-01-02", "bad", None, "2024-01-01"])
    df.loc[1, "rig_name"] = None
    df.loc[3, "spud_date"] = "2024-01-03"
    df.loc[4, "well_id"] = "W0"
    df.index = [7] * len(df)
    before = df.copy(deep=True)
    result = BSEEBatchDetector().detect_batches_with_diagnostics(df)
    assert result.counts == {"accepted": 2, "rejected": 2, "excluded": 1}
    assert result.records.row_position.tolist() == list(range(5))
    assert result.records.source_index.tolist() == [7] * 5
    assert result.records.reason.tolist() == [
        "accepted",
        "missing_rig_name",
        "invalid_spud_date",
        "accepted",
        "duplicate_record",
    ]
    assert result.batches.batch_size.sum() == result.counts["accepted"]
    assert result.batches.iloc[0].well_ids == ["W0", "W3"]
    pd.testing.assert_frame_equal(df, before)


@pytest.mark.parametrize("column", ["well_id", "rig_name", "field_name"])
@pytest.mark.parametrize("value", [None, "", "  ", 5])
def test_invalid_identifiers_are_reconciled(column, value):
    """Each synthetic invalid key accounts for one rejected input row."""
    df = activities(["2024-01-01"])
    df[column] = pd.Series([value], dtype=object)
    result = BSEEBatchDetector().detect_batches_with_diagnostics(df)
    assert result.counts == {"accepted": 0, "rejected": 1, "excluded": 0}
    assert result.batches.empty
    assert column in result.records.iloc[0].reason


@pytest.mark.parametrize("date", [None, "", "01/02/2024", 1704067200, True])
def test_missing_ambiguous_and_epoch_dates_are_rejected(date):
    """Epoch units and locale date order are deliberately not inferred."""
    result = BSEEBatchDetector().detect_batches_with_diagnostics(activities([date]))
    assert result.counts["rejected"] == 1


def test_calendar_month_boundary_and_fractional_days():
    """Jan 31 + one calendar month = Feb 29 in 2024; next instant is outside.

    Jan 31 noon to Feb 29 noon is 29 elapsed days; noon to 18:00 is 1/4 day.
    The third row forms a new batch (anchored, not chained, inclusive window).
    """
    df = activities(
        [
            "2024-01-31T12:00:00Z",
            "2024-02-29T12:00:00Z",
            "2024-02-29T12:00:01Z",
            "2024-02-29T18:00:01Z",
        ]
    )
    result = BSEEBatchDetector().detect_batches(df, time_window_months=1)
    assert result.batch_size.tolist() == [2, 2]
    assert result.span_days.tolist() == [29.0, 0.25]


def test_timezones_and_normalized_duplicates():
    """01:00 +01:00 and 00:00 UTC denote the same instant and record."""
    df = activities(["2024-01-01T01:00:00+01:00", "2024-01-01"])
    df.loc[1, "well_id"] = " W0 "
    result = BSEEBatchDetector().detect_batches_with_diagnostics(df)
    assert result.counts == {"accepted": 1, "rejected": 0, "excluded": 1}
    assert str(result.batches.iloc[0].start_date.tz) == "UTC"


@pytest.mark.parametrize("window", [0, -1, 1.5, True, "1"])
def test_invalid_window_is_rejected_even_on_empty_data(window):
    with pytest.raises(ValueError, match="positive integer"):
        BSEEBatchDetector().detect_batches(activities([]), window)


def test_repeated_well_with_distinct_event_is_retained():
    """Event rows are counted, not distinct wells: two dates remain two rows."""
    df = activities(["2024-01-01", "2024-02-01"])
    df["well_id"] = "W"
    result = BSEEBatchDetector().detect_batches_with_diagnostics(df)
    assert result.counts["accepted"] == 2
    assert result.batches.iloc[0].well_ids == ["W", "W"]


def test_learning_numeric_text_and_rejection_reasons():
    """Two-point hand fit: T(1)=8, T(2)=4 -> b=-1, LC=2**(-1)=0.5.

    All remaining rows are invalid, so six = two accepted + four rejected.
    """
    df = pd.DataFrame(
        {
            "well_position": [" 1 ", "2e0", "1,000", True, 0, "3"],
            "days_to_drill": ["8.0", "4", "3", 2, 5, float("inf")],
        }
    )
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(df)
    assert result.counts == {"accepted": 2, "rejected": 4, "excluded": 0}
    assert result.factor == pytest.approx(0.5)
    assert result.raw_factor == pytest.approx(0.5)
    assert result.status == "fitted"
    assert result.records.reason.tolist() == [
        "accepted",
        "accepted",
        "invalid_well_position",
        "invalid_well_position",
        "nonpositive_well_position",
        "nonfinite_days_to_drill",
    ]


@pytest.mark.parametrize(
    "times, raw, factor, status",
    [
        ([8, 2], 0.25, 0.5, "clipped_lower"),
        ([8, 4], 0.5, 0.5, "fitted"),
        ([8, 8], 1.0, 1.0, "fitted"),
        ([8, 16], 2.0, 1.0, "clipped_upper"),
    ],
)
def test_learning_clipping_boundaries(times, raw, factor, status):
    """For N=(1,2), LC=T(2)/T(1); bounds are legacy application policy.

    Exact endpoint equality is fitted, not clipped. Numerical assertions use
    pytest's floating-point tolerance, not an engineering acceptance limit.
    """
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(
        pd.DataFrame({"well_position": [1, 2], "days_to_drill": times})
    )
    assert result.raw_factor == pytest.approx(raw)
    assert result.factor == pytest.approx(factor)
    assert result.status == status
    assert result.qualification == "NOT_EVALUATED"


@pytest.mark.parametrize(
    "positions, times, reason",
    [
        ([], [], "insufficient_data"),
        ([1], [8], "insufficient_data"),
        ([1, 0], [8, 4], "insufficient_data"),
        ([1, 1], [8, 4], "constant_position"),
    ],
)
def test_degenerate_fits_expose_legacy_default(positions, times, reason, caplog):
    """No identifiable slope: retain legacy 0.85, never claim a fitted result."""
    df = pd.DataFrame({"well_position": positions, "days_to_drill": times})
    detector = BSEEBatchDetector()
    result = detector.fit_learning_curve_with_diagnostics(df)
    assert result.factor == 0.85
    assert result.raw_factor is None
    assert result.status == "defaulted"
    assert result.reason == reason
    assert result.qualification == "NOT_EVALUATED"
    assert detector.fit_learning_curve(df) == 0.85
    assert "defaulted" in caplog.text


@pytest.mark.parametrize(
    "value", [None, "", "NaN", "inf", float("nan"), -2, "2 days", 1.5]
)
def test_learning_invalid_positions_are_reconciled(value):
    """One invalid row plus one good row leaves an insufficient-data default."""
    df = pd.DataFrame({"well_position": [value, 2], "days_to_drill": [8, 4]})
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(df)
    assert result.counts["accepted"] == result.counts["rejected"] == 1
    assert result.status == "defaulted"


def test_learning_filtered_scalar_reports_dispositions(caplog):
    """T(2)/T(1)=1/4 clips to 1/2 and one negative duration is rejected."""
    df = pd.DataFrame({"well_position": [1, 2, 3], "days_to_drill": [8, 2, -1]})
    assert BSEEBatchDetector().fit_learning_curve(df) == 0.5
    assert "clipped_lower" in caplog.text
    assert "rejected" in caplog.text


def test_learning_three_point_hand_result():
    """Synthetic T=(16,8,4) at N=(1,2,4) lies on b=-1, LC=1/2.

    log(T)=log(16)-log(N); covariance/variance therefore equals -1.
    """
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(
        pd.DataFrame({"well_position": [1, 2, 4], "days_to_drill": [16, 8, 4]})
    )
    assert math.isclose(result.factor, 0.5)
    assert result.status == "fitted"


def test_empty_schemas_and_missing_columns():
    detector = BSEEBatchDetector()
    result = detector.detect_batches_with_diagnostics(activities([]))
    assert result.counts == {"accepted": 0, "rejected": 0, "excluded": 0}
    assert result.records.columns.tolist() == [
        "row_position",
        "source_index",
        "disposition",
        "reason",
    ]
    for method in (detector.detect_batches, detector.fit_learning_curve):
        with pytest.raises(ValueError, match="missing required columns"):
            method(pd.DataFrame())


@pytest.mark.parametrize("first", [3, 9, 10, 100])
def test_lower_boundary_roundoff_is_not_reported_as_clipping(first):
    """T(2)=T(1)/2 gives LC=1/2 exactly despite log roundoff."""
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(
        pd.DataFrame({"well_position": [1, 2], "days_to_drill": [first, first / 2]})
    )
    assert result.factor == pytest.approx(0.5)
    assert result.status == "fitted"


@pytest.mark.parametrize("text", ["2024", "2024-01", "20240101"])
def test_partial_or_compact_dates_do_not_infer_missing_components(text):
    """Only complete extended calendar dates are accepted as text."""
    result = BSEEBatchDetector().detect_batches_with_diagnostics(activities([text]))
    assert result.counts["rejected"] == 1
