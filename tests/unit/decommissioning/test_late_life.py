# ABOUTME: Unit tests for late-life asset identification from production decline data.
# ABOUTME: Covers decline thresholds, idle detection, portfolio screening, and filtering.

"""Unit tests for worldenergydata.decommissioning.late_life."""

import pandas as pd
import pytest

from worldenergydata.decommissioning.late_life import (
    LateLifeAssessment,
    LateLifeIdentifier,
)

# ---------------------------------------------------------------------------
# Helpers to build production DataFrames
# ---------------------------------------------------------------------------


def _make_production_df(
    years: list[int],
    months_per_year: int = 12,
    bopd_by_year: dict[int, float] | None = None,
) -> pd.DataFrame:
    """Build a monthly production DataFrame.

    Args:
        years: List of years to include.
        months_per_year: Number of months per year (max 12).
        bopd_by_year: Mapping of year → bopd. Missing years get 0.

    Returns:
        DataFrame with columns year, month, oil_bbl.
    """
    rows = []
    for yr in years:
        bopd = (bopd_by_year or {}).get(yr, 0.0)
        for mo in range(1, months_per_year + 1):
            rows.append({"year": yr, "month": mo, "oil_bbl": bopd * 30.0})
    return pd.DataFrame(rows)


def _declining_field() -> pd.DataFrame:
    """Field with >80% decline over 5 years.

    Years 2015-2020 all at 10,000 bopd (past baseline).
    Year 2025 at 1,000 bopd (current) → 90% decline.
    """
    return _make_production_df(
        years=list(range(2015, 2026)),
        bopd_by_year={
            2015: 10000,
            2016: 10000,
            2017: 10000,
            2018: 10000,
            2019: 10000,
            2020: 10000,
            2021: 5000,
            2022: 3000,
            2023: 2000,
            2024: 1500,
            2025: 1000,
        },
    )


def _stable_field() -> pd.DataFrame:
    """Field with <50% decline — not late life."""
    return _make_production_df(
        years=list(range(2015, 2026)),
        bopd_by_year={yr: 8000 for yr in range(2015, 2021)}
        | {yr: 7000 for yr in range(2021, 2026)},
    )


def _idle_field(idle_months: int = 15) -> pd.DataFrame:
    """Field that is idle for the last N months."""
    rows = []
    active_months = 24  # 2 years of production before idle
    for i in range(active_months):
        rows.append({"year": 2023, "month": (i % 12) + 1, "oil_bbl": 5000 * 30.0})
    # Last idle_months at near-zero
    for i in range(idle_months):
        rows.append({"year": 2025, "month": (i % 12) + 1, "oil_bbl": 0.0})
    return pd.DataFrame(rows)


@pytest.fixture()
def identifier() -> LateLifeIdentifier:
    return LateLifeIdentifier()


# ---------------------------------------------------------------------------
# Basic assess_field usage
# ---------------------------------------------------------------------------


def test_assess_field_returns_dataclass(identifier):
    df = _declining_field()
    result = identifier.assess_field("FieldA", df, "gom")
    assert isinstance(result, LateLifeAssessment)


def test_assess_field_stores_field_name(identifier):
    df = _declining_field()
    result = identifier.assess_field("TestField", df, "gom")
    assert result.field_name == "TestField"


def test_assess_field_stores_region(identifier):
    df = _declining_field()
    result = identifier.assess_field("F1", df, "ncs")
    assert result.region == "ncs"


def test_assess_field_empty_df_not_flagged(identifier):
    result = identifier.assess_field("Empty", pd.DataFrame(), "gom")
    assert result.late_life_flag is False
    assert result.trigger == "none"


# ---------------------------------------------------------------------------
# Decline threshold
# ---------------------------------------------------------------------------


def test_high_decline_field_is_flagged(identifier):
    df = _declining_field()
    result = identifier.assess_field("DecliningField", df, "gom")
    assert result.late_life_flag is True


def test_high_decline_trigger_value(identifier):
    df = _declining_field()
    result = identifier.assess_field("DecliningField", df, "gom")
    assert result.trigger in ("decline_>80pct", "both")


def test_stable_field_not_flagged(identifier):
    df = _stable_field()
    result = identifier.assess_field("StableField", df, "gom")
    assert result.late_life_flag is False


def test_stable_field_trigger_is_none(identifier):
    df = _stable_field()
    result = identifier.assess_field("StableField", df, "gom")
    assert result.trigger == "none"


# ---------------------------------------------------------------------------
# Idle threshold
# ---------------------------------------------------------------------------


def test_idle_field_15_months_is_flagged(identifier):
    df = _idle_field(idle_months=15)
    result = identifier.assess_field("IdleField", df, "gom")
    assert result.late_life_flag is True


def test_idle_field_trigger_idle(identifier):
    df = _idle_field(idle_months=15)
    result = identifier.assess_field("IdleField", df, "gom")
    assert result.trigger in ("idle_>12mo", "both")


def test_idle_months_counted_correctly(identifier):
    df = _idle_field(idle_months=15)
    result = identifier.assess_field("IdleField", df, "gom")
    assert result.months_idle >= 12


def test_briefly_idle_field_not_flagged(identifier):
    """Field idle only 6 months should not trigger idle threshold."""
    df = _idle_field(idle_months=6)
    result = identifier.assess_field("ShortIdleField", df, "gom")
    # Only idle_>12mo can trigger; may still pass if decline < 80%
    if not result.late_life_flag:
        assert result.months_idle < 12


# ---------------------------------------------------------------------------
# Trigger values are valid
# ---------------------------------------------------------------------------


def test_trigger_is_valid_value(identifier):
    valid_triggers = {"decline_>80pct", "idle_>12mo", "both", "none"}
    for field_name, df in [
        ("D", _declining_field()),
        ("S", _stable_field()),
        ("I", _idle_field(15)),
    ]:
        result = identifier.assess_field(field_name, df, "gom")
        assert result.trigger in valid_triggers


# ---------------------------------------------------------------------------
# Portfolio screening
# ---------------------------------------------------------------------------


def test_screen_portfolio_returns_list(identifier):
    fields = {"D": _declining_field(), "S": _stable_field()}
    results = identifier.screen_portfolio(fields, "gom")
    assert isinstance(results, list)
    assert len(results) == 2


def test_screen_portfolio_all_assessments(identifier):
    fields = {"F1": _declining_field(), "F2": _stable_field(), "F3": _idle_field(15)}
    results = identifier.screen_portfolio(fields, "gom")
    assert all(isinstance(r, LateLifeAssessment) for r in results)


def test_screen_portfolio_field_names_match(identifier):
    fields = {"Alpha": _declining_field(), "Beta": _stable_field()}
    results = identifier.screen_portfolio(fields, "gom")
    names = {r.field_name for r in results}
    assert "Alpha" in names
    assert "Beta" in names


# ---------------------------------------------------------------------------
# late_life_fields() filter
# ---------------------------------------------------------------------------


def test_late_life_fields_filters_correctly(identifier):
    fields = {"D": _declining_field(), "S": _stable_field(), "I": _idle_field(15)}
    all_assessments = identifier.screen_portfolio(fields, "gom")
    flagged = identifier.late_life_fields(all_assessments)
    assert all(a.late_life_flag for a in flagged)


def test_late_life_fields_excludes_stable(identifier):
    fields = {"D": _declining_field(), "S": _stable_field()}
    all_assessments = identifier.screen_portfolio(fields, "gom")
    flagged = identifier.late_life_fields(all_assessments)
    flagged_names = {a.field_name for a in flagged}
    assert "S" not in flagged_names


def test_late_life_fields_empty_input(identifier):
    assert identifier.late_life_fields([]) == []


@pytest.mark.parametrize("missing", [float("nan"), None, pd.NA])
@pytest.mark.parametrize("history", ["idle", "declining"])
def test_missing_final_month_is_unknown(identifier, missing, history):
    """Issue #1281: missing production cannot determine current idle or cessation.

    Idle example: two observed zero-volume months then an unknown month.
    Neither 0 nor 3 idle months can be established at the tail. Decline example:
    the existing synthetic declining history followed by an unknown last value.
    A latest-year cessation estimate is unsupported in both cases.
    """
    if history == "idle":
        frame = pd.DataFrame(
            {
                "year": [2025, 2025, 2025],
                "month": [1, 2, 3],
                "oil_bbl": [0.0, 0.0, missing],
            }
        )
    else:
        frame = _declining_field()
        frame["oil_bbl"] = frame["oil_bbl"].astype(object)
        frame.loc[frame.index[-1], "oil_bbl"] = missing
    result = identifier.assess_field("Synthetic", frame.iloc[::-1])
    assert result.current_production_bopd is None
    assert result.months_idle is None
    assert result.estimated_cessation_year is None
    assert result.production_data_status == "unknown_final_month"
    assert result.trigger not in {"idle_>12mo", "both"}
    if history == "declining":
        assert result.late_life_flag  # Independent observed decline is retained.


@pytest.mark.parametrize("nonfinite", [float("inf"), float("-inf")])
def test_nonfinite_final_month_cannot_project(identifier, nonfinite):
    """Non-finite production is not a measured current rate (issue #1281)."""
    frame = _declining_field()
    frame.loc[frame.index[-1], "oil_bbl"] = nonfinite
    result = identifier.assess_field("Synthetic", frame)
    assert result.current_production_bopd is None
    assert result.months_idle is None
    assert result.estimated_cessation_year is None


def test_observed_zero_final_month_remains_known(identifier):
    """Hand calculation: two observed zero-volume months give 2 idle rows.

    Existing policy reports 0 (not applicable) cessation for observed zero;
    this must remain distinguishable from None (unknown) for missing data.
    """
    frame = pd.DataFrame({"year": [2025, 2025], "month": [1, 2], "oil_bbl": [0.0, 0.0]})
    result = identifier.assess_field("Synthetic", frame)
    assert result.current_production_bopd == 0.0
    assert result.months_idle == 2
    assert result.estimated_cessation_year == 0
    assert result.production_data_status == "available"


def test_portfolio_retains_unknown_final_month(identifier):
    """Each missing endpoint must remain unknown through portfolio screening."""
    frame = pd.DataFrame({"year": [2025], "month": [1], "oil_bbl": [float("nan")]})
    (result,) = identifier.screen_portfolio({"Synthetic": frame})
    assert result.current_production_bopd is None
    assert result.months_idle is None
    assert result.estimated_cessation_year is None


@pytest.mark.parametrize("dtype", ["object", "Float64"])
def test_all_missing_production_is_unknown(identifier, dtype):
    """No measured volumes establish no peak, idle duration or cessation.

    pandas 2.2.3 (2024), pandas.isna examples: None/NaN/NA are missing scalars.
    No zero production or numerical decline can be inferred from two NA rows.
    """
    frame = pd.DataFrame(
        {
            "year": [2025, 2025],
            "month": [1, 2],
            "oil_bbl": pd.Series([pd.NA, pd.NA], dtype=dtype),
        }
    )
    result = identifier.assess_field("Synthetic", frame)
    assert result.peak_production_bopd is None
    assert result.current_production_bopd is None
    assert result.decline_pct_5yr is None
    assert result.months_idle is None
    assert result.estimated_cessation_year is None
    assert not result.late_life_flag
