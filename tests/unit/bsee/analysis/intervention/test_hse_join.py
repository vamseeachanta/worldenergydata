"""Synthetic join examples; no production incident data is included.

Expected values are independent enumerations of equality and closed intervals,
as specified in the issue-416 plan, section Pseudocode, step 3 (2026-05-18).
"""

from datetime import date, datetime

import pytest

from worldenergydata.bsee.analysis.intervention import hse_join


def test_normalizes_only_case_and_whitespace():
    """Case/spacing variants coincide; punctuation and leading zeros survive."""
    key = hse_join.normalize_join_key("  GROUP   ALPHA ", " g0012 ", "2024-02-29")
    assert key == ("group alpha", "G0012", date(2024, 2, 29))
    assert key != hse_join.normalize_join_key("group alpha", "G12", "2024-02-29")
    assert key != hse_join.normalize_join_key("group-alpha", "G0012", "2024-02-29")


@pytest.mark.parametrize("missing", [None, "", "  ", float("nan"), 12, True])
def test_missing_or_nontext_identity_is_not_joinable(missing):
    """Each incomplete identity has no valid equality key."""
    assert hse_join.normalize_join_key(missing, "G0012", "2024-01-01") is None
    assert hse_join.normalize_join_key("group alpha", missing, "2024-01-01") is None


@pytest.mark.parametrize(
    "invalid", [None, "02/03/2024", "2024-02-30", "20240101", datetime(2024, 1, 1)]
)
def test_dates_require_unambiguous_calendar_days(invalid):
    """No locale, compact-date or timestamp interpretation is inferred."""
    assert hse_join.normalize_join_key("group alpha", "G0012", invalid) is None


def test_date_object_is_supported():
    """An explicit calendar date retains its day without a timezone conversion."""
    assert hse_join.normalize_join_key("a", "G1", date(2024, 1, 1))[-1] == date(
        2024, 1, 1
    )


def incident(day="2024-01-02", operator="group alpha", lease="G0012"):
    return {"operator": operator, "lease_number": lease, "incident_date": day}


def window(start="2024-01-01", end="2024-01-03", lease="G0012"):
    return {
        "BUS_ASC_NAME": "GROUP ALPHA",
        "BOTM_LEASE_NUM": lease,
        "WAR_START_DT": start,
        "WAR_END_DT": end,
    }


def test_closed_windows_and_exact_identity_matching():
    """Jan 1 and 3 are in [Jan 1, Jan 3]; Jan 4 and different keys are out.

    Hand enumeration gives matched=2, unmatched=3, invalid=1, ambiguous=0;
    counts sum to the six input incidents. Input order is retained.
    """
    incidents = [
        incident("2024-01-01"),
        incident("2024-01-03"),
        incident("2024-01-04"),
        incident(operator="group beta"),
        incident(lease="G12"),
        incident(day=None),
    ]
    result = hse_join.match_intervention_windows(incidents, [window()])
    assert [m.status for m in result.matches] == [
        "matched",
        "matched",
        "unmatched",
        "unmatched",
        "unmatched",
        "invalid_key",
    ]
    assert [m.window_indices for m in result.matches] == [(0,), (0,), (), (), (), ()]
    assert result.counts == {
        "matched": 2,
        "unmatched": 3,
        "invalid_key": 1,
        "ambiguous": 0,
    }
    assert result.invalid_window_indices == ()
    assert result.pattern_status == "NOT_EVALUATED"


def test_overlaps_are_ambiguous_including_duplicate_windows():
    """Jan 2 belongs to both supplied intervals; no arbitrary winner is chosen."""
    result = hse_join.match_intervention_windows([incident()], [window(), window()])
    assert result.matches[0].status == "ambiguous"
    assert result.matches[0].window_indices == (0, 1)
    assert result.counts["ambiguous"] == 1


def test_invalid_windows_are_reported_without_fabricating_duration():
    """Missing, reversed and non-ISO spans are rejected; fourth span matches."""
    windows = [
        window(end=None),
        window(start="2024-01-04"),
        window(start="01/01/2024"),
        window(),
    ]
    result = hse_join.match_intervention_windows([incident()], windows)
    assert result.invalid_window_indices == (0, 1, 2)
    assert result.matches[0].window_indices == (3,)


def test_empty_inputs_and_missing_columns():
    """No windows means one unmatched complete key; missing keys stay invalid."""
    empty = hse_join.match_intervention_windows([], [])
    assert empty.matches == ()
    assert sum(empty.counts.values()) == 0
    result = hse_join.match_intervention_windows([incident(), {}], [{}])
    assert result.counts == {
        "matched": 0,
        "unmatched": 1,
        "invalid_key": 1,
        "ambiguous": 0,
    }
    assert result.invalid_window_indices == (0,)


def test_inputs_are_not_modified():
    """Pure matching preserves the supplied raw identity and dates."""
    row, period = incident(), window()
    row_before, period_before = row.copy(), period.copy()
    hse_join.match_intervention_windows([row], [period])
    assert row == row_before
    assert period == period_before


def test_one_day_window_and_generator_inputs():
    """For [Jan 2, Jan 2], only Jan 2 matches; Jan 1 and Jan 3 do not.

    Independent enumeration: one matched incident, two unmatched incidents.
    """
    rows = (incident(day) for day in ("2024-01-01", "2024-01-02", "2024-01-03"))
    periods = (window(start="2024-01-02", end="2024-01-02") for _ in range(1))
    result = hse_join.match_intervention_windows(rows, periods)
    assert [m.status for m in result.matches] == ["unmatched", "matched", "unmatched"]
    assert result.counts["matched"] == 1


def test_invalid_window_identity_is_not_a_wildcard():
    """Neither a missing operator nor a missing lease matches a complete key."""
    periods = [window(), window()]
    periods[0]["BUS_ASC_NAME"] = None
    periods[1]["BOTM_LEASE_NUM"] = None
    result = hse_join.match_intervention_windows([incident()], periods)
    assert result.invalid_window_indices == (0, 1)
    assert result.matches[0].status == "unmatched"
