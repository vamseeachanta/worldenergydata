"""Boundary and conservation checks for the existing detector contract.

All inputs are synthetic. Calendar answers follow pandas DateOffset (2026),
Time series guide, DateOffset objects. Numeric rules and compatibility bounds
are defined in docs/detector-contracts.md, Record accounting and Learning-fit
contract (revision 1, 2026). No fixture represents physical qualification.
"""

import pandas as pd
import pytest

from worldenergydata.drilling import BSEEBatchDetector


def events(dates):
    return pd.DataFrame(
        {
            "well_id": [str(i) for i in range(len(dates))],
            "rig_name": ["R"] * len(dates),
            "field_name": ["F"] * len(dates),
            "spud_date": dates,
        }
    )


def assert_conserved(result, frame):
    """Each positional input has exactly one reason and one disposition."""
    assert len(frame) == sum(result.counts.values()) == len(result.records)
    assert result.records.row_position.tolist() == list(range(len(frame)))
    assert result.records.source_index.tolist() == frame.index.tolist()
    assert set(result.records.disposition) <= {"accepted", "rejected", "excluded"}
    assert result.records.reason.map(bool).all()


def test_record_conservation_and_all_rejection_reasons():
    """Hand accounting: 5 rows = 2 accepted + 2 rejected + 1 excluded.

    Whitespace/numeric ID normalization makes rows 0 and 1 duplicates; row 2
    lacks both grouping keys and a date. Additional columns do not define identity.
    """
    frame = events(["2024-01-01", "2024-01-01", None, "bad", "2024-01-02"])
    frame["well_id"] = pd.Series([1, " 1 ", "2", "3", "4"], dtype=object)
    frame.loc[2, ["rig_name", "field_name"]] = [None, " "]
    frame["unused"] = range(len(frame))
    frame.index = [9] * len(frame)
    before = frame.copy(deep=True)
    result = BSEEBatchDetector().detect_batches_with_diagnostics(frame)
    assert_conserved(result, frame)
    assert result.counts == {"accepted": 2, "rejected": 2, "excluded": 1}
    assert result.records.reason.tolist() == [
        "accepted",
        "duplicate_record",
        "missing_rig_name;missing_field_name;invalid_spud_date",
        "invalid_spud_date",
        "accepted",
    ]
    assert result.batches.batch_size.sum() == result.counts["accepted"]
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("dates", [[], [None, "bad"], ["2024-01-01"]])
def test_empty_rejected_and_accepted_inputs_conserve_counts(dates):
    """Hand counts are respectively zero, two rejected, and one accepted."""
    frame = events(dates)
    result = BSEEBatchDetector().detect_batches_with_diagnostics(frame)
    assert_conserved(result, frame)
    assert result.batches.batch_size.sum() == result.counts["accepted"]


@pytest.mark.parametrize("learning", [False, True])
def test_duplicate_columns_raise_before_reconciliation(learning):
    """Ambiguous schema is an error, rather than a partial row report."""
    frame = (
        pd.DataFrame({"well_position": [1], "days_to_drill": [8]})
        if learning
        else events(["2024-01-01"])
    )
    frame = pd.concat([frame, frame.iloc[:, :1]], axis=1)
    detector = BSEEBatchDetector()
    method = (
        detector.fit_learning_curve_with_diagnostics
        if learning
        else detector.detect_batches_with_diagnostics
    )
    with pytest.raises(ValueError, match="input columns must be unique"):
        method(frame)


@pytest.mark.parametrize(
    "start,endpoint,days",
    [
        ("2023-01-31T12:00:00Z", "2023-02-28T12:00:00Z", 28),
        ("2024-01-31T12:00:00Z", "2024-02-29T12:00:00Z", 29),
        ("2024-12-31T12:00:00Z", "2025-01-31T12:00:00Z", 31),
    ],
)
def test_calendar_endpoint_one_second_either_side(start, endpoint, days):
    """Calendar hand answers: Jan31->Feb28=28d, leap Feb29=29d, Dec31->Jan31=31d.

    Inclusive endpoint admits the preceding second and equality, but the next
    second starts a new batch. These are calendar fixtures, not duration laws.
    """
    end = pd.Timestamp(endpoint)
    frame = events(
        [start, end - pd.Timedelta(seconds=1), end, end + pd.Timedelta(seconds=1)]
    )
    result = BSEEBatchDetector().detect_batches_with_diagnostics(frame, 1)
    assert_conserved(result, frame)
    assert result.batches.batch_size.tolist() == [3, 1]
    assert result.batches.span_days.tolist() == [days, 0]


def test_windows_anchor_to_first_member_not_last_member():
    """Jan1+1 month=Feb1; Feb15 remains outside even though Jan20+1 month=Feb20."""
    frame = events(["2024-02-15", "2024-01-20", "2024-01-01"])
    result = BSEEBatchDetector().detect_batches_with_diagnostics(frame, 1)
    assert result.batches.well_ids.tolist() == [["2", "1"], ["0"]]
    assert result.batches.span_days.tolist() == [19, 0]


@pytest.mark.parametrize(
    "value,reason",
    [
        (None, "missing"),
        (" ", "missing"),
        ("1,5", "invalid"),
        ("1 day", "invalid"),
        (True, "invalid"),
        (-1, "nonpositive"),
        (0, "nonpositive"),
        (float("inf"), "nonfinite"),
    ],
)
def test_duration_parsing_conserves_filtered_rows(value, reason):
    """One valid row plus one invalid duration = two inputs; no identifiable slope.

    Missing and grammar rules come from detector-contracts.md revision 1;
    -1, 0 and +1 exercise either side of the positive-duration boundary.
    """
    frame = pd.DataFrame({"well_position": [1, 2], "days_to_drill": [1, value]})
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(frame)
    assert_conserved(result, frame)
    assert result.counts == {"accepted": 1, "rejected": 1, "excluded": 0}
    assert result.records.reason.tolist() == ["accepted", f"{reason}_days_to_drill"]
    assert result.status == "defaulted"
    assert result.reason == "insufficient_data"


@pytest.mark.parametrize("size", [0, 1, 2, 3])
def test_identifiability_boundary(size):
    """Two coefficients need two distinct positions; zero/one cannot fit.

    Synthetic N=(1,2,4), T=(8,4,2) gives log(T)=log(8)-log(N),
    b=-1 and LC=1/2 for either two or three retained points.
    """
    frame = pd.DataFrame(
        {"well_position": [1, 2, 4][:size], "days_to_drill": [8, 4, 2][:size]}
    )
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(frame)
    assert_conserved(result, frame)
    assert result.counts["accepted"] == size
    if size < 2:
        # Compatibility value: detector-contracts.md rev 1, Learning-fit contract.
        assert result.factor == 0.85
        assert result.raw_factor is None
        assert (result.status, result.reason) == ("defaulted", "insufficient_data")
    else:
        assert result.factor == pytest.approx(0.5)
        assert result.status == "fitted"


@pytest.mark.parametrize(
    "second,raw,status",
    [
        (3, 3 / 8, "clipped_lower"),
        (4, 4 / 8, "fitted"),
        (5, 5 / 8, "fitted"),
        (7, 7 / 8, "fitted"),
        (8, 8 / 8, "fitted"),
        (9, 9 / 8, "clipped_upper"),
    ],
)
def test_clipping_boundary_and_one_duration_step_either_side(second, raw, status):
    """Hand two-point slope gives LC=T(2)/T(1)=second/8, one day per step.

    Around the legacy 1/2 bound: 3/8, 4/8, 5/8. Around the legacy unity
    bound: 7/8, 8/8, 9/8. Bounds: detector-contracts.md rev 1, Learning-fit
    contract; pytest tolerance handles arithmetic roundoff only.
    """
    frame = pd.DataFrame(
        {"well_position": ["1", "2e0"], "days_to_drill": ["8", str(second)]}
    )
    before = frame.copy(deep=True)
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(frame)
    assert_conserved(result, frame)
    assert result.raw_factor == pytest.approx(raw)
    assert result.factor == pytest.approx(max(0.5, min(raw, 1.0)))
    assert result.status == status
    assert result.qualification == "NOT_EVALUATED"
    pd.testing.assert_frame_equal(frame, before)


def test_replicated_learning_positions_remain_observations():
    """N=(1,1,2), T=(8,8,4) still lies on log(T)=log(8)-log(N).

    Three accepted observations, zero exclusions; replicated positions do not
    prevent fitting when another distinct position identifies the slope.
    """
    frame = pd.DataFrame({"well_position": [1, 1, 2], "days_to_drill": [8, 8, 4]})
    result = BSEEBatchDetector().fit_learning_curve_with_diagnostics(frame)
    assert_conserved(result, frame)
    assert result.counts == {"accepted": 3, "rejected": 0, "excluded": 0}
    assert result.raw_factor == pytest.approx(0.5)
    assert result.status == "fitted"


def test_worked_example_dispositions_and_learning_line():
    """Reproduce detector-contracts.md's synthetic input/disposition tables.

    Seven events = four accepted + two rejected + one duplicate exclusion.
    Jan31 noon to leap Feb29 noon is 29 days; six hours is 1/4 day.
    Learning: N=(1,2), T=(8,2), b=log(2/8)/log(2)=-2, a=log(8).
    Thus the line predicts T(2)=8*2**(-2)=2 and LC=1/4; compatibility
    policy clips to 1/2. Two other rows are rejected explicitly.
    """
    frame = events(
        [
            "2024-01-31T12:00:00Z",
            "2024-01-31T12:00:00Z",
            "2024-02-29T12:00:00Z",
            "2024-02-29T12:00:01Z",
            "2024-02-29T18:00:01Z",
            "2024-02-29",
            "bad",
        ]
    )
    frame["well_id"] = pd.Series([101, "101", 102, 103, 104, 105, 106], dtype=object)
    frame.loc[5, "rig_name"] = None
    detector = BSEEBatchDetector()
    result = detector.detect_batches_with_diagnostics(frame, 1)
    assert_conserved(result, frame)
    assert result.counts == {"accepted": 4, "rejected": 2, "excluded": 1}
    assert result.records.reason.tolist() == [
        "accepted",
        "duplicate_record",
        "accepted",
        "accepted",
        "accepted",
        "missing_rig_name",
        "invalid_spud_date",
    ]
    assert result.batches.batch_size.tolist() == [2, 2]
    assert result.batches.span_days.tolist() == [29, 0.25]
    training = pd.DataFrame(
        {"well_position": ["1", "2", "3", "0"], "days_to_drill": ["8", "2", "bad", "4"]}
    )
    fit = detector.fit_learning_curve_with_diagnostics(training)
    assert_conserved(fit, training)
    assert fit.counts == {"accepted": 2, "rejected": 2, "excluded": 0}
    assert fit.records.reason.tolist() == [
        "accepted",
        "accepted",
        "invalid_days_to_drill",
        "nonpositive_well_position",
    ]
    assert fit.raw_factor == pytest.approx(1 / 4)
    assert fit.factor == 0.5
    assert fit.status == "clipped_lower"
    assert fit.qualification == "NOT_EVALUATED"
