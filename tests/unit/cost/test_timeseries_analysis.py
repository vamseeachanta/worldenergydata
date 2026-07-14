"""
ABOUTME: Tests normalization, trend fitting and sanctioned-project back-allocation (issue #844).
ABOUTME: Focus is the honesty rails — refusing to extrapolate a deflator, refusing to fit 3 points.

Boundary: pure math on synthetic inputs. No network. The reference-series
fetcher is exercised separately by the refresh CLI, not here.
"""

from __future__ import annotations

from datetime import date

import pytest

from worldenergydata.cost.timeseries.back_allocation import (
    STAGE_SHARE_PRIORS,
    DevelopmentType,
    LifecycleStage,
    StageShares,
    allocate_project,
    reconcile_drilling,
)
from worldenergydata.cost.timeseries.normalization import (
    DeflatorBasis,
    build_deflator,
    compare_against_inflation,
    to_real,
)
from worldenergydata.cost.timeseries.schema import (
    CostComponent,
    CostObservation,
    DisclosureConfidence,
    Provenance,
    SourcePriority,
)
from worldenergydata.cost.timeseries.trend_fit import (
    MIN_POINTS_FOR_FIT,
    FunctionalForm,
    fit_component,
    predict,
)


def _sourced(year: int, component: CostComponent, value: float) -> CostObservation:
    return CostObservation(
        year=year,
        component=component,
        value=value,
        unit="usd_per_day",
        provenance=Provenance.SOURCED,
        source_title="test source",
        source_url="https://example.com/report",
        page_reference="p.1",
        quoted_text=f"{year}: {value}",
        accessed_date=date(2026, 7, 14),
        confidence=DisclosureConfidence.HIGH,
        source_priority=SourcePriority.PRESS_RELEASE,
    )


def _cpi_rows(start: int, end: int, start_value: float = 100.0, rate: float = 0.02):
    """A synthetic CPI series growing at a constant `rate`."""
    return [
        _sourced(year, CostComponent.INDEX_CPI, start_value * (1 + rate) ** (year - start))
        for year in range(start, end + 1)
    ]


# ---------------------------------------------------------------------------
# Deflators / normalization
# ---------------------------------------------------------------------------


def test_cpi_deflator_is_complete_and_uninterpolated() -> None:
    deflator = build_deflator(_cpi_rows(2000, 2020), DeflatorBasis.CPI)
    assert deflator.interpolated_years == frozenset()
    assert deflator.covers(2010)


def test_to_real_converts_to_the_basis_year() -> None:
    deflator = build_deflator(_cpi_rows(2000, 2020, rate=0.02), DeflatorBasis.CPI)
    # 100 nominal dollars in 2000, expressed in 2020 dollars, at 2%/yr for 20 yrs
    real = to_real(100.0, from_year=2000, basis_year=2020, deflator=deflator)
    assert real == pytest.approx(100.0 * (1.02**20), rel=1e-9)


def test_to_real_returns_none_rather_than_extrapolating() -> None:
    """The deflator does not cover 1995. We must not invent a 1995 price level."""
    deflator = build_deflator(_cpi_rows(2000, 2020), DeflatorBasis.CPI)
    assert to_real(100.0, from_year=1995, basis_year=2020, deflator=deflator) is None


def test_ucci_deflator_interpolates_gaps_and_flags_them() -> None:
    """UCCI is proprietary and only anchor years are sourceable."""
    anchors = [
        _sourced(2000, CostComponent.INDEX_UCCI, 100.0),
        _sourced(2005, CostComponent.INDEX_UCCI, 150.0),
    ]
    deflator = build_deflator(anchors, DeflatorBasis.UCCI)
    assert deflator.values[2000] == 100.0
    assert deflator.values[2005] == 150.0
    # linear across the gap
    assert deflator.values[2002] == pytest.approx(120.0)
    # ...and every gap year is flagged as inferred
    assert deflator.interpolated_years == frozenset({2001, 2002, 2003, 2004})
    # anchors themselves are not flagged
    assert 2000 not in deflator.interpolated_years


def test_ucci_deflator_never_extrapolates_beyond_its_anchors() -> None:
    anchors = [
        _sourced(2000, CostComponent.INDEX_UCCI, 100.0),
        _sourced(2005, CostComponent.INDEX_UCCI, 150.0),
    ]
    deflator = build_deflator(anchors, DeflatorBasis.UCCI)
    assert not deflator.covers(2010)
    assert to_real(100.0, 2010, 2005, deflator) is None


def test_build_deflator_refuses_to_substitute_a_different_index() -> None:
    """No UCCI rows must mean 'no UCCI deflator', not 'quietly use CPI'."""
    with pytest.raises(ValueError, match="Refusing to substitute"):
        build_deflator(_cpi_rows(2000, 2005), DeflatorBasis.UCCI)


def test_compare_against_inflation_detects_outpacing() -> None:
    """A component doubling while CPI grows 2%/yr must read as OUTPACED."""
    rows = _cpi_rows(2000, 2010, rate=0.02)
    rows += [
        _sourced(2000, CostComponent.RIG_DAY_RATE_DRILLSHIP, 100_000.0),
        _sourced(2010, CostComponent.RIG_DAY_RATE_DRILLSHIP, 400_000.0),
    ]
    deflator = build_deflator(rows, DeflatorBasis.CPI)
    verdict = compare_against_inflation(
        rows, deflator, CostComponent.RIG_DAY_RATE_DRILLSHIP, basis_year=2010
    )
    assert verdict is not None
    assert "OUTPACED" in verdict.verdict
    assert verdict.nominal_cagr_pct == pytest.approx(14.87, abs=0.05)
    assert verdict.excess_cagr_pct > 0


def test_compare_against_inflation_detects_lagging() -> None:
    rows = _cpi_rows(2000, 2010, rate=0.05)
    rows += [
        _sourced(2000, CostComponent.RIG_DAY_RATE_JACKUP, 100_000.0),
        _sourced(2010, CostComponent.RIG_DAY_RATE_JACKUP, 101_000.0),
    ]
    deflator = build_deflator(rows, DeflatorBasis.CPI)
    verdict = compare_against_inflation(
        rows, deflator, CostComponent.RIG_DAY_RATE_JACKUP, basis_year=2010
    )
    assert verdict is not None
    assert "LAGGED" in verdict.verdict


def test_compare_against_inflation_needs_two_points() -> None:
    """One observation cannot have a trend, and we must not assert one."""
    rows = _cpi_rows(2000, 2010)
    rows += [_sourced(2005, CostComponent.RIG_DAY_RATE_SEMI, 300_000.0)]
    deflator = build_deflator(rows, DeflatorBasis.CPI)
    assert (
        compare_against_inflation(
            rows, deflator, CostComponent.RIG_DAY_RATE_SEMI, basis_year=2010
        )
        is None
    )


def test_compare_ignores_fitted_rows_when_picking_endpoints() -> None:
    """The verdict must be anchored on real data at both ends."""
    rows = _cpi_rows(2000, 2010)
    rows += [
        _sourced(2004, CostComponent.RIG_DAY_RATE_SEMI, 200_000.0),
        _sourced(2008, CostComponent.RIG_DAY_RATE_SEMI, 400_000.0),
        CostObservation(
            year=2010,
            component=CostComponent.RIG_DAY_RATE_SEMI,
            value=999_000.0,
            unit="usd_per_day",
            provenance=Provenance.FITTED,
            notes="fitted, must not become an endpoint",
        ),
    ]
    deflator = build_deflator(rows, DeflatorBasis.CPI)
    verdict = compare_against_inflation(
        rows, deflator, CostComponent.RIG_DAY_RATE_SEMI, basis_year=2010
    )
    assert verdict is not None
    assert verdict.end_year == 2008  # not 2010
    assert verdict.end_nominal == 400_000.0


# ---------------------------------------------------------------------------
# Trend fitting
# ---------------------------------------------------------------------------


def test_fit_declines_below_the_minimum_point_count() -> None:
    rows = [
        _sourced(y, CostComponent.RIG_DAY_RATE_SEMI, 100.0 + y)
        for y in range(2000, 2000 + MIN_POINTS_FOR_FIT - 1)
    ]
    assert fit_component(rows, CostComponent.RIG_DAY_RATE_SEMI) is None


def test_fit_recovers_a_clean_linear_trend() -> None:
    rows = [
        _sourced(y, CostComponent.RIG_DAY_RATE_SEMI, 100_000.0 + 10_000.0 * (y - 2000))
        for y in range(2000, 2012)
    ]
    fit = fit_component(rows, CostComponent.RIG_DAY_RATE_SEMI)
    assert fit is not None
    assert fit.r_squared == pytest.approx(1.0, abs=1e-6)
    assert fit.coefficients["b"] == pytest.approx(10_000.0, rel=1e-6)
    assert not fit.is_weak


def test_fit_prefers_the_oil_linked_form_when_the_series_tracks_oil() -> None:
    """Day rates are cyclical in the oil price, not monotone in time.

    Construct a series that is flat-ish in time but a clean function of oil, and
    assert the fitter picks the oil-linked form. This is the #844 'cycle driver'
    finding, mechanised.
    """
    oil = {2000: 30.0, 2001: 25.0, 2002: 25.0, 2003: 29.0, 2004: 38.0,
           2005: 55.0, 2006: 65.0, 2007: 72.0, 2008: 97.0, 2009: 62.0,
           2010: 80.0, 2011: 111.0}
    rows = [
        _sourced(year, CostComponent.RIG_DAY_RATE_DRILLSHIP, 50_000.0 + 4_000.0 * price)
        for year, price in oil.items()
    ]
    fit = fit_component(rows, CostComponent.RIG_DAY_RATE_DRILLSHIP, oil_price_by_year=oil)
    assert fit is not None
    assert fit.form is FunctionalForm.OIL_LINKED
    assert fit.coefficients["b"] == pytest.approx(4_000.0, rel=1e-6)
    assert fit.oil_price_corr == pytest.approx(1.0, abs=1e-6)


def test_predict_flags_extrapolation_beyond_the_fitted_window() -> None:
    rows = [
        _sourced(y, CostComponent.RIG_DAY_RATE_SEMI, 100_000.0 + 10_000.0 * (y - 2000))
        for y in range(2000, 2012)
    ]
    fit = fit_component(rows, CostComponent.RIG_DAY_RATE_SEMI)
    assert fit is not None

    inside = predict(fit, 2005)
    assert inside is not None and inside[1] is False

    outside = predict(fit, 2030)
    assert outside is not None and outside[1] is True  # flagged as extrapolated


def test_predict_returns_none_when_an_oil_linked_curve_lacks_its_input() -> None:
    # The oil path must be genuinely CYCLICAL, not monotone in time. If oil rose
    # linearly with the year, a linear-in-time fit would be exactly as good as
    # the oil-linked one (both R²=1) and the fitter would rightly prefer the
    # simpler form — which would make this test about tie-breaking rather than
    # about the missing-input guard it is meant to cover.
    oil = {2000: 30.0, 2001: 25.0, 2002: 25.0, 2003: 29.0, 2004: 38.0,
           2005: 55.0, 2006: 65.0, 2007: 72.0, 2008: 97.0, 2009: 62.0,
           2010: 80.0, 2011: 111.0}
    rows = [
        _sourced(year, CostComponent.RIG_DAY_RATE_DRILLSHIP, 50_000.0 + 4_000.0 * price)
        for year, price in oil.items()
    ]
    fit = fit_component(rows, CostComponent.RIG_DAY_RATE_DRILLSHIP, oil_price_by_year=oil)
    assert fit is not None and fit.form is FunctionalForm.OIL_LINKED
    # 2050 oil price is unknown -> the curve has no input -> no prediction.
    assert predict(fit, 2050, oil_price_by_year=oil) is None


# ---------------------------------------------------------------------------
# Back-allocation
# ---------------------------------------------------------------------------


def test_every_prior_sums_to_one() -> None:
    for dev_type, shares in STAGE_SHARE_PRIORS.items():
        assert sum(shares.mid.values()) == pytest.approx(1.0, abs=0.02), dev_type


def test_allocation_conserves_the_disclosed_total() -> None:
    allocation = allocate_project(
        "Test FPSO", 5_000.0, DevelopmentType.NEW_HOST_FPSO, well_count=18
    )
    assert allocation is not None
    total = sum(stage.cost_mid_usd_mm for stage in allocation.stages)
    assert total == pytest.approx(5_000.0, rel=1e-9)


def test_tieback_puts_almost_nothing_on_the_host() -> None:
    """A tieback reuses a host — the split must reflect that or it is wrong."""
    allocation = allocate_project(
        "Test Tieback", 1_000.0, DevelopmentType.SUBSEA_TIEBACK, well_count=4
    )
    assert allocation is not None
    host = allocation.stage(LifecycleStage.HOST)
    surf = allocation.stage(LifecycleStage.SURF)
    assert host is not None and surf is not None
    assert host.share_mid < 0.06
    assert surf.share_mid > host.share_mid * 4


def test_well_count_tilts_drilling_share_sub_linearly() -> None:
    few = allocate_project("A", 5_000.0, DevelopmentType.NEW_HOST_FPSO, well_count=9)
    many = allocate_project("B", 5_000.0, DevelopmentType.NEW_HOST_FPSO, well_count=36)
    assert few is not None and many is not None
    few_drill = few.stage(LifecycleStage.DRILL)
    many_drill = many.stage(LifecycleStage.DRILL)
    assert few_drill is not None and many_drill is not None
    # 4x the wells must raise the drilling share, but nowhere near 4x it.
    ratio = many_drill.share_mid / few_drill.share_mid
    assert 1.0 < ratio < 2.5


def test_unknown_development_type_is_not_allocated() -> None:
    """We will not split a total we cannot characterise."""
    assert allocate_project("Mystery", 1_000.0, DevelopmentType.UNKNOWN) is None


def test_disclosed_shares_override_the_priors_and_carry_no_band() -> None:
    shares = StageShares.from_disclosed(
        {
            LifecycleStage.DRILL: 0.5,
            LifecycleStage.COMPLETE: 0.1,
            LifecycleStage.SURF: 0.1,
            LifecycleStage.HOST: 0.2,
            LifecycleStage.INSTALL: 0.05,
            LifecycleStage.HOOKUP: 0.05,
        },
        rationale="operator disclosed the split",
    )
    allocation = allocate_project(
        "Disclosed", 1_000.0, DevelopmentType.NEW_HOST_SEMI, well_count=99, shares=shares
    )
    assert allocation is not None
    assert allocation.shares_are_disclosed
    drill = allocation.stage(LifecycleStage.DRILL)
    assert drill is not None
    # Disclosed -> no well-count tilt applied, no uncertainty band invented.
    assert drill.share_mid == pytest.approx(0.5)
    assert drill.cost_low_usd_mm == pytest.approx(drill.cost_high_usd_mm)


def test_reconciliation_reports_the_gap_rather_than_hiding_it() -> None:
    allocation = allocate_project(
        "Test Semi", 4_000.0, DevelopmentType.NEW_HOST_SEMI, well_count=8
    )
    assert allocation is not None
    recon = reconcile_drilling(
        allocation, year=2020, rig_day_rate_usd=300_000.0, days_per_well=60.0
    )
    assert recon is not None
    # 8 wells x 60 d x $300k x 2.0 = $288MM bottom-up
    assert recon.bottom_up_drill_usd_mm == pytest.approx(288.0)
    assert recon.gap_usd_mm == pytest.approx(
        recon.bottom_up_drill_usd_mm - recon.top_down_drill_usd_mm
    )
    assert isinstance(recon.within_band, bool)


def test_reconciliation_declines_without_a_disclosed_well_count() -> None:
    """Manufacturing a well count to force a reconciliation defeats the point."""
    allocation = allocate_project(
        "No Wells Disclosed", 4_000.0, DevelopmentType.NEW_HOST_SEMI, well_count=None
    )
    assert allocation is not None
    assert (
        reconcile_drilling(
            allocation, year=2020, rig_day_rate_usd=300_000.0, days_per_well=60.0
        )
        is None
    )
