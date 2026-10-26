"""Offline regression evidence for observed WAR abandonment display milestones.

All identifiers and dates are synthetic inputs defined in ``war_frames`` below.
Hand calculation for LEASE-A through the inclusive cutoff 2024-04-30:
SYNTH-A/TA: min(April 3, April 9) = April 3;
SYNTH-B/TA: min(April 7, April 25) = April 7;
SYNTH-A/PA: min(April 12, April 20) = April 12;
SYNTH-B/PA: April 30, exactly the cutoff, is included.
SYNTH-C has only an invalid PA date and a TA date after the cutoff; neither
qualifies. LEASE-B independently contributes SYNTH-A/PA on April 1 and
SYNTH-OTHER/TA on April 5. DRL is excluded to avoid duplicate spud milestones.

Expected records are enumerated from this ledger, independently of the helper.
Labels pin observed milestone display behavior, not abandonment durations or
a new official activity-code source. The empty columns follow the row schema
documented by ``ops_timeline.derive_war_operations``.
"""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from worldenergydata.lower_tertiary import ops_timeline


@pytest.fixture
def war_frames(monkeypatch):
    """Replace only the archive reader; preserve both shared input frames."""
    reports = pd.DataFrame(
        [
            ("a-pa-late", ' "lease-a" ', " SYNTH-A ", " Well A ", "2024-04-20", "PA"),
            ("b-ta-late", "LEASE-A", "SYNTH-B", "Well B", "2024-04-25", " ta "),
            ("a-ta-early", "LEASE-A", "SYNTH-A", " Well A ", "2024-04-03", " tA "),
            ("b-pa-cutoff", "LEASE-A", "SYNTH-B", "Well B", "2024-04-30", " pA\t"),
            ("a-pa-early", " lease -a ", "SYNTH-A", " Well A ", "2024-04-12", "pA"),
            ("a-ta-late", "LEASE-A", " SYNTH-A ", " Well A ", "2024-04-09", "TA"),
            ("b-ta-early", "LEASE-A", "SYNTH-B", "Well B", "2024-04-07", "TA"),
            ("c-pa-invalid", "LEASE-A", "SYNTH-C", "Well C", "invalid-date", "PA"),
            ("c-ta-after", "LEASE-A", "SYNTH-C", "Well C", "2024-05-01", "TA"),
            ("a-drl", "LEASE-A", "SYNTH-A", " Well A ", "2024-04-02", " drl "),
            ("other-ta", "LEASE-B", "SYNTH-OTHER", "Other well", "2024-04-05", "ta"),
            ("other-pa", "LEASE-B", "SYNTH-A", " Well A ", "2024-04-01", "PA"),
        ],
        columns=[
            "SN_WAR",
            "SURF_LEASE_NUM",
            "API_WELL_NUMBER",
            "WELL_NAME",
            "WAR_START_DT",
            "WELL_ACTIVITY_CD",
        ],
    )
    main = reports.drop(columns="WELL_ACTIVITY_CD")
    prop = reports[["SN_WAR", "WELL_ACTIVITY_CD"]].copy()
    original_main = main.copy(deep=True)
    original_prop = prop.copy(deep=True)
    frames = {"mv_war_main.bin": main, "mv_war_main_prop.bin": prop}
    monkeypatch.setattr(ops_timeline, "_read_war_bin", frames.__getitem__)

    yield

    assert_frame_equal(main, original_main)
    assert_frame_equal(prop, original_prop)


def test_abandonment_codes_keep_earliest_in_cutoff_milestone(war_frames):
    result = ops_timeline.derive_war_operations("lease-a", end_date="2024-04-30")

    assert result.to_dict("records") == [
        {
            "API_WELL_NUMBER": "SYNTH-A",
            "date": pd.Timestamp("2024-04-03"),
            "operation": "Temporary abandonment",
            "detail": "Well A (SYNTH-A)",
        },
        {
            "API_WELL_NUMBER": "SYNTH-B",
            "date": pd.Timestamp("2024-04-07"),
            "operation": "Temporary abandonment",
            "detail": "Well B (SYNTH-B)",
        },
        {
            "API_WELL_NUMBER": "SYNTH-A",
            "date": pd.Timestamp("2024-04-12"),
            "operation": "Plug & abandon",
            "detail": "Well A (SYNTH-A)",
        },
        {
            "API_WELL_NUMBER": "SYNTH-B",
            "date": pd.Timestamp("2024-04-30"),
            "operation": "Plug & abandon",
            "detail": "Well B (SYNTH-B)",
        },
    ]
    assert result["date"].is_monotonic_increasing
    assert result["date"].is_unique


def test_abandonment_lease_filter_does_not_leak(war_frames):
    result = ops_timeline.derive_war_operations("lease-b", end_date="2024-04-30")

    assert result.to_dict("records") == [
        {
            "API_WELL_NUMBER": "SYNTH-A",
            "date": pd.Timestamp("2024-04-01"),
            "operation": "Plug & abandon",
            "detail": "Well A (SYNTH-A)",
        },
        {
            "API_WELL_NUMBER": "SYNTH-OTHER",
            "date": pd.Timestamp("2024-04-05"),
            "operation": "Temporary abandonment",
            "detail": "Other well (SYNTH-OTHER)",
        },
    ]
    assert result["date"].is_monotonic_increasing
    assert result["date"].is_unique


def test_empty_lease_returns_stable_schema(war_frames):
    result = ops_timeline.derive_war_operations("LEASE-EMPTY", end_date="2024-04-30")

    assert result.empty
    assert list(result.columns) == ["API_WELL_NUMBER", "date", "operation", "detail"]
    assert result.to_dict("records") == []
