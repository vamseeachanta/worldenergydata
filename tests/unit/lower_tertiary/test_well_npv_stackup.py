"""Tests for the per-well NPV stackup decomposition.

The stackup must sum *exactly* (to the cent) to the field terminal NPV produced
by :func:`build_field_npv_timeline`, on both the frozen V30 window and an
extended ("latest") window. These tests depend on BSEE OGOR-A data (the yearly
zip archives or the pickled ``.bin`` fallback); when neither source is present
they skip rather than fail.
"""

from __future__ import annotations

import pytest

from worldenergydata.lower_tertiary.v30_financial_reproducer import (
    build_field_npv_timeline,
    build_well_npv_stackup,
)


def _ensure_ogor_or_skip() -> None:
    """Patch the .bin OGOR loader (as the report generator does) or skip.

    Mirrors ``generate_field_economics_report._ensure_ogor_loader`` so the
    tests run in checkouts that only carry the pickled ``.bin`` DataFrames.
    """
    try:
        import scripts.lower_tertiary.generate_field_economics_report as gen
    except Exception as exc:  # pragma: no cover - import guard
        pytest.skip(f"report generator unimportable: {exc}")
    try:
        gen._ensure_ogor_loader()
        # Probe that at least one OGOR source resolves.
        from worldenergydata.lower_tertiary import v30_reproducer as r

        r.load_ogor_production(start_year=2016, end_year=2016)
    except FileNotFoundError:
        pytest.skip("BSEE OGOR-A data not present (run `make data`)")


# Sanctioned frozen Julia terminal NPV (golden-baseline reproduction).
JULIA_FROZEN_NPV = -530_642_813.91


class TestWellStackupSumsToField:
    def test_frozen_window_sums_to_field(self):
        _ensure_ogor_or_skip()
        field = build_field_npv_timeline("Julia", end_date=None)
        stk = build_well_npv_stackup("Julia", end_date=None)

        # Frozen field NPV is the sanctioned value.
        assert field["terminal_npv_usd"] == pytest.approx(JULIA_FROZEN_NPV, abs=0.01)
        # Per-well net NPVs sum to the field terminal NPV (to the cent).
        assert stk["sum_well_npv_usd"] == pytest.approx(
            field["terminal_npv_usd"], abs=0.01
        )
        assert abs(stk["residual_usd"]) < 0.01
        # Monthly decomposition is exact up to float noise.
        assert stk["monthly_decomposition_residual_usd"] < 1.0

    def test_latest_window_sums_to_field(self):
        _ensure_ogor_or_skip()
        end_date = "2026-04-30"
        field = build_field_npv_timeline("Julia", end_date=end_date)
        stk = build_well_npv_stackup("Julia", end_date=end_date)

        assert stk["sum_well_npv_usd"] == pytest.approx(
            field["terminal_npv_usd"], abs=0.01
        )
        assert abs(stk["residual_usd"]) < 0.01
        # The latest window must differ from the frozen one (extended production).
        assert field["terminal_npv_usd"] != pytest.approx(JULIA_FROZEN_NPV, abs=1.0)

    def test_well_shares_sum_to_one(self):
        _ensure_ogor_or_skip()
        stk = build_well_npv_stackup("Julia", end_date=None)
        assert stk["wells"], "expected at least one well"
        total_share = sum(w["oil_share"] for w in stk["wells"])
        assert total_share == pytest.approx(1.0, abs=1e-9)
        # Wells sorted by net NPV impact (largest absolute magnitude first).
        abs_nets = [abs(w["net_npv_usd"]) for w in stk["wells"]]
        assert abs_nets == sorted(abs_nets, reverse=True)

    def test_gross_plus_shared_equals_net(self):
        _ensure_ogor_or_skip()
        stk = build_well_npv_stackup("Julia", end_date=None)
        for w in stk["wells"]:
            assert w["gross_npv_usd"] + w["shared_npv_usd"] == pytest.approx(
                w["net_npv_usd"], abs=0.01
            )
