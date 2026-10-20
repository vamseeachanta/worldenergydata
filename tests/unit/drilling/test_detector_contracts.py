"""Synthetic contract cases; expectations are hand calculations, not field data.

Calendar and disposition rules: detector-contract.md, sections Input contracts
and Reconciliation. Regression: NIST/SEMATECH e-Handbook (2012), 4.4.3.1.
Floating comparisons use pytest's default numerical tolerance; it is not an
engineering acceptance limit. Each regression oracle is derived below.
"""

import logging
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from worldenergydata.drilling import BSEEBatchDetector


def activity(dates, **columns):
    """Construct synthetic rows with unique identifiers and one grouping key."""
    return pd.DataFrame(
        {
            "well_id": [f"well-{i}" for i in range(len(dates))],
            "rig_name": "rig",
            "field_name": "field",
            "spud_date": dates,
            **columns,
        }
    )


def fit(positions, durations, **policies):
    return BSEEBatchDetector().fit_learning_curve_with_report(
        pd.DataFrame({"well_position": positions, "days_to_drill": durations}),
        **policies,
    )


def assert_counts(report, accepted, rejected, excluded):
    assert report.counts == {
        "accepted": accepted,
        "rejected": rejected,
        "excluded": excluded,
    }
    assert sum(report.counts.values()) == len(report.rows)
    assert report.rows["row_number"].tolist() == list(range(len(report.rows)))


def test_activity_reconciliation_and_duplicate_index():
    """Seven inputs = two accepted + four rejected + one exact duplicate."""
    frame = activity(
        [
            "2024-01-01",
            "bad",
            None,
            "2024-01-01",
            "2024-01-01",
            "2024-01-01",
            "2024-01-02",
        ],
        well_id=["a", "b", "c", "d", "e", "a", "f"],
        rig_name=["rig", "rig", "rig", None, "rig", "rig", "rig"],
        field_name=["field", "field", "field", "field", " ", "field", "field"],
    )
    frame.index = [0] * len(frame)
    original = frame.copy(deep=True)
    result = BSEEBatchDetector().detect_batches_with_report(frame)
    assert_counts(result.reconciliation, 2, 4, 1)
    assert result.reconciliation.rows["reason"].tolist() == [
        "accepted",
        "invalid_spud_date",
        "missing_spud_date",
        "missing_rig_name",
        "missing_field_name",
        "duplicate_record",
        "accepted",
    ]
    assert result.batches["well_ids"].tolist() == [["a", "f"]]
    assert result.batches["batch_size"].sum() == 2
    pd.testing.assert_frame_equal(frame, original)


def test_conflicting_well_ids_are_all_rejected():
    """Two different dates for one well provide no unique spud event."""
    result = BSEEBatchDetector().detect_batches_with_report(
        activity(["2024-01-01", "2024-01-02"], well_id=["same", "same"])
    )
    assert_counts(result.reconciliation, 0, 2, 0)
    assert set(result.reconciliation.rows["reason"]) == {"conflicting_well_id"}
    assert result.batches.empty


def test_calendar_month_inclusive_anchor_and_fractional_span():
    """Jan 31 + one calendar month = Feb 29 in 2024; March 1 starts anew.

    Jan 31 noon to Feb 29 midnight = 28 days + half a day = 28.5 days.
    The last row lies within a month of Feb 29 but outside the first anchor.
    """
    result = BSEEBatchDetector().detect_batches_with_report(
        activity(
            ["2024-03-01", "2024-02-29T12:00:00Z", "2024-01-31T12:00:00Z", "2024-02-29"]
        ),
        time_window_months=1,
    )
    assert result.batches["batch_size"].tolist() == [3, 1]
    assert result.batches["span_days"].tolist() == [29.0, 0.0]
    half_day = BSEEBatchDetector().detect_batches_with_report(
        activity(["2024-01-31T12:00:00Z", "2024-02-29"]),
        time_window_months=1,
    )
    assert half_day.batches["span_days"].tolist() == [28.5]


def test_utc_normalization_and_equal_date_stability():
    """Offset midnight equals 01:00 UTC; naive 01:00 is assumed UTC."""
    result = BSEEBatchDetector().detect_batches_with_report(
        activity(
            [
                "2024-01-01T00:00:00-01:00",
                pd.Timestamp("2024-01-01T01:00"),
                "2024-01-01T01:00:00Z",
            ]
        )
    )
    assert result.batches["well_ids"].tolist() == [["well-0", "well-1", "well-2"]]
    assert result.batches["span_days"].tolist() == [0.0]
    assert str(result.batches["start_date"].dt.tz) == "UTC"


@pytest.mark.parametrize("date", ["01/02/2024", 0, "2024-02-30", True, "tomorrow"])
def test_ambiguous_and_invalid_dates_are_rejected(date):
    result = BSEEBatchDetector().detect_batches_with_report(activity([date]))
    assert_counts(result.reconciliation, 0, 1, 0)
    assert result.reconciliation.rows.loc[0, "reason"] == "invalid_spud_date"


@pytest.mark.parametrize("months", [0, -1, 1.5, True, "1", np.inf])
def test_window_requires_positive_integer_months(months):
    with pytest.raises(ValueError, match="positive integer"):
        BSEEBatchDetector().detect_batches_with_report(activity([]), months)


def test_empty_and_missing_columns():
    detector = BSEEBatchDetector()
    result = detector.detect_batches_with_report(activity([]))
    assert_counts(result.reconciliation, 0, 0, 0)
    assert list(result.batches.columns) == list(
        detector.detect_batches(activity([])).columns
    )
    empty_fit = fit([], [])
    assert empty_fit.factor is None
    assert empty_fit.status == "NOT_EVALUATED"
    assert_counts(empty_fit.reconciliation, 0, 0, 0)
    for method in (
        detector.detect_batches_with_report,
        detector.fit_learning_curve_with_report,
    ):
        with pytest.raises(ValueError, match="missing required columns"):
            method(pd.DataFrame())


def test_numeric_text_filtering_reconciliation():
    """Eight inputs = two accepted + four malformed + two nonpositive.

    Accepted (N,T) = (1,8), (2,4). log slope = -1, factor = 2**-1 = 0.5.
    Scientific decimal text is accepted; locale punctuation and units are not.
    """
    result = fit(
        [" 1 ", "2e0", "1,000", None, "3", True, "-1", "4"],
        ["8.0", "+4", "2", "2", "2 days", "2", "2", "0"],
    )
    assert_counts(result.reconciliation, 2, 4, 2)
    assert result.reconciliation.rows["reason"].tolist() == [
        "accepted",
        "accepted",
        "invalid_well_position",
        "missing_well_position",
        "invalid_days_to_drill",
        "invalid_well_position",
        "nonpositive_well_position",
        "nonpositive_days_to_drill",
    ]
    assert result.factor == pytest.approx(0.5)
    assert result.slope == pytest.approx(-1)
    assert result.status == "FITTED"


@pytest.mark.parametrize(
    "value", [np.nan, np.inf, -np.inf, "NaN", "inf", "1_000", "2,5"]
)
def test_nonfinite_and_nondecimal_numbers(value):
    result = fit([1, 2, 3], [8, 4, value])
    assert_counts(result.reconciliation, 2, 1, 0)
    assert result.factor == pytest.approx(0.5)


def test_fractional_positions_and_repeated_observations():
    """N must be an integer; repeated N observations have equal weight.

    Two observations at N=1,T=8 and one at N=2,T=4 remain collinear:
    slope=-1, factor=0.5. The fractional position is rejected.
    """
    result = fit([1, 1, 2, 1.5], [8, 8, 4, 100])
    assert_counts(result.reconciliation, 3, 1, 0)
    assert result.factor == pytest.approx(0.5)
    assert result.reconciliation.rows.loc[3, "reason"] == "noninteger_well_position"


@pytest.mark.parametrize(
    "positions,durations,reason",
    [
        ([], [], "insufficient_data"),
        ([1], [8], "insufficient_data"),
        ([0, 1], [8, 4], "insufficient_data"),
        ([1, 1], [8, 4], "indistinct_positions"),
    ],
)
def test_default_requires_explicit_policy(positions, durations, reason):
    """No slope exists with fewer than two distinct usable positions.

    The supplied 0.75 is a synthetic caller assumption, not a fitted value.
    """
    result = fit(positions, durations)
    assert result.status == "NOT_EVALUATED"
    assert result.factor is None
    assert result.reason == reason
    defaulted = fit(positions, durations, default_factor=0.75)
    assert defaulted.status == "DEFAULTED"
    assert defaulted.factor == 0.75
    assert defaulted.raw_factor is None
    assert defaulted.reason == reason


@pytest.mark.parametrize(
    "durations,raw,expected,status",
    [
        ([8, 2], 0.25, 0.5, "CLIPPED"),  # slope=-2, so 2**-2=0.25
        ([8, 4], 0.5, 0.5, "FITTED"),  # lower boundary is inclusive
        ([8, 8], 1.0, 1.0, "FITTED"),  # slope=0, so 2**0=1
        ([8, 16], 2.0, 1.0, "CLIPPED"),  # slope=1, so 2**1=2
    ],
)
def test_clipping_is_explicit_and_boundaries_are_inclusive(
    durations, raw, expected, status
):
    """Bounds [0.5,1] are synthetic test policy; the raw doubling ratios are exact."""
    unbounded = fit([1, 2], durations)
    assert unbounded.factor == pytest.approx(raw)
    result = fit([1, 2], durations, clip_bounds=(0.5, 1.0))
    assert result.raw_factor == pytest.approx(raw)
    assert result.factor == pytest.approx(expected)
    assert result.status == status


@pytest.mark.parametrize(
    "policy",
    [
        {"default_factor": 0},
        {"default_factor": np.nan},
        {"default_factor": True},
        {"clip_bounds": (1, 0.5)},
        {"clip_bounds": (0, 1)},
        {"clip_bounds": (0.5, np.inf)},
        {"default_factor": 2, "clip_bounds": (0.5, 1)},
        {"default_factor": 10**1000},  # cannot be represented as a finite float
        {"clip_bounds": 0.5},
        {"clip_bounds": "0.5,1"},
        {"clip_bounds": ()},
        {"clip_bounds": (0.5, 1, 2)},
    ],
)
def test_invalid_fit_policy(policy):
    with pytest.raises(ValueError):
        fit([1, 2], [8, 4], **policy)


def test_wrappers_warn_when_information_is_discarded(caplog):
    detector = BSEEBatchDetector()
    with caplog.at_level(logging.WARNING):
        detector.detect_batches(activity([None]))
        factor = detector.fit_learning_curve(
            pd.DataFrame({"well_position": [1], "days_to_drill": [8]})
        )
        clipped = detector.fit_learning_curve(
            pd.DataFrame({"well_position": [1, 2], "days_to_drill": [8, 2]})
        )
    # Legacy compatibility values: pinned detector, code revision b1394197,
    # lines 138-140 (default) and 159-160 (clipping); no calibration claimed.
    assert factor == 0.85
    assert clipped == 0.5
    assert "rejected=1" in caplog.text
    assert "DEFAULTED" in caplog.text
    assert "CLIPPED" in caplog.text


def test_numerically_unrepresentable_fit_is_not_evaluated():
    """Huge finite duration ratio over adjacent large N overflows 2**slope."""
    result = fit([10**12, 10**12 + 1], [1e-200, 1e200])
    assert result.status == "NOT_EVALUATED"
    assert result.reason == "nonfinite_fit"
    assert result.factor is None


def test_worked_example():
    """Calendar oracle: Jan 31 to Feb 29 is 29 days; doubling halves duration.

    Thus b=-1, LC=0.5; counts are obtained by enumerating the four input rows.
    """
    example = (
        Path(__file__).resolve().parents[3]
        / "examples"
        / "drilling_detector_contract.py"
    )
    result = runpy.run_path(str(example))["worked_example"]()
    assert result["activity_counts"] == {"accepted": 2, "rejected": 1, "excluded": 1}
    assert result["fit_counts"] == {"accepted": 3, "rejected": 0, "excluded": 1}
    assert result["batch_sizes"] == [2]
    assert result["spans_days"] == [29.0]
    assert result["slope"] == pytest.approx(-1)
    assert result["factor"] == pytest.approx(0.5)
    assert result["fit_status"] == "FITTED"


def test_group_separation_and_normalized_duplicates():
    """Same timestamp, separate rig/field; stripped duplicate equals first event."""
    frame = activity(
        ["2024-01-01"] * 4,
        well_id=["a", "b", "c", " a "],
        rig_name=["rig", "other-rig", "rig", " rig "],
        field_name=["field", "field", "other-field", " field "],
    )
    result = BSEEBatchDetector().detect_batches_with_report(frame)
    assert_counts(result.reconciliation, 3, 0, 1)
    assert sorted(result.batches["batch_size"]) == [1, 1, 1]
    assert sorted(well for wells in result.batches["well_ids"] for well in wells) == [
        "a",
        "b",
        "c",
    ]


@pytest.mark.parametrize(
    "identifier,reason",
    [(None, "missing_well_id"), (" ", "missing_well_id"), (123, "invalid_well_id")],
)
def test_identifier_contract_and_reason_precedence(identifier, reason):
    result = BSEEBatchDetector().detect_batches_with_report(
        activity(["bad"], well_id=[identifier], rig_name=[None])
    )
    assert_counts(result.reconciliation, 0, 1, 0)
    assert result.reconciliation.rows.loc[0, "reason"] == reason


def test_filtered_fit_does_not_modify_input_and_warns(caplog):
    """The accepted pair (1,8),(2,4) has factor=0.5; zero N is excluded."""
    frame = pd.DataFrame({"well_position": [1, 2, 0], "days_to_drill": [8, 4, 2]})
    original = frame.copy(deep=True)
    with caplog.at_level(logging.WARNING):
        assert BSEEBatchDetector().fit_learning_curve(frame) == pytest.approx(0.5)
    assert "excluded=1" in caplog.text
    pd.testing.assert_frame_equal(frame, original)


def test_duplicate_columns_are_schema_errors():
    detector = BSEEBatchDetector()
    frame = pd.DataFrame(columns=["well_position", "days_to_drill", "days_to_drill"])
    with pytest.raises(ValueError, match="duplicate column"):
        detector.fit_learning_curve_with_report(frame)


def test_all_excluded_fit_and_missing_duration():
    """Zero N, negative days and missing days leave no eligible pair."""
    result = fit([0, 1, 2], [8, -1, None])
    assert_counts(result.reconciliation, 0, 1, 2)
    assert result.status == "NOT_EVALUATED"
    assert result.reason == "insufficient_data"
    assert result.reconciliation.rows["reason"].tolist() == [
        "nonpositive_well_position",
        "nonpositive_days_to_drill",
        "missing_days_to_drill",
    ]


def test_supported_date_range_and_window_overflow():
    """The contract rejects dates outside nanosecond range and window overflow."""
    detector = BSEEBatchDetector()
    result = detector.detect_batches_with_report(activity(["9999-01-01"]))
    assert_counts(result.reconciliation, 0, 1, 0)
    with pytest.raises(ValueError, match="calendar window exceeds"):
        detector.detect_batches_with_report(activity(["2024-01-01"]), 10**12)


def test_zero_log_space_variance_cannot_look_like_a_fit():
    """Adjacent large integers can map to the same float logarithm.

    The positions are distinct as floats, but no representable log slope exists.
    No numerical conditioning threshold or fallback should manufacture a fit.
    """
    result = fit([2**53 - 1, 2**53], [8, 4])
    assert result.status == "NOT_EVALUATED"
    assert result.reason == "nonfinite_fit"
    with pytest.raises(ValueError, match="not evaluated"):
        BSEEBatchDetector().fit_learning_curve(
            pd.DataFrame(
                {
                    "well_position": [2**53 - 1, 2**53],
                    "days_to_drill": [8, 4],
                }
            )
        )
