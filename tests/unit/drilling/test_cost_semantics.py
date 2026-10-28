"""Regression arithmetic, not an empirical drilling calibration.

Accounting basis: OpenStax, Principles of Accounting, Volume 2: Managerial
Accounting (2019), section 3.2, fixed plus variable cost. The drilling adaptation
is recorded in drilling/docs/agent-pack.md, revision 2 (2026), section 3:
B = M + R*sum(T_i), S = N*(M + R*T_1), savings = S - B.
All numbers below are synthetic inputs; hand calculations specify every oracle.
No engineering acceptance tolerance is used: these cases are exactly representable.
"""

import pytest

from worldenergydata.drilling import BatchDrillingEconomics, DrillCampaign, DrillingSite


@pytest.fixture
def calculator(monkeypatch):
    """Supply a synthetic 20-day base; do not qualify the depth heuristic."""
    calc = BatchDrillingEconomics()
    monkeypatch.setattr(calc, "_estimate_base_well_days", lambda campaign: 20.0)
    return calc


def make_campaign(n_wells, mobilization, learning):
    """Synthetic rate 10 USD/day; zero coordinates/depths are unused metadata."""
    return DrillCampaign(
        campaign_id="synthetic",
        rig_name="synthetic",
        rig_day_rate_usd=10.0,
        mobilization_cost_usd=mobilization,
        learning_curve_factor=learning,
        wells=[
            DrillingSite(
                well_id=str(i),
                field_name="synthetic",
                location_coords=(0.0, 0.0),
                water_depth_ft=0.0,
                planned_md_ft=0.0,
                well_type="development",
            )
            for i in range(n_wells)
        ],
    )


@pytest.mark.parametrize(
    "n_wells,mobilization,learning,batch,standalone,savings",
    [
        (1, 100.0, 0.5, 300.0, 300.0, 0.0),
        (2, 100.0, 0.5, 400.0, 600.0, 200.0),
        (2, 100.0, 1.0, 500.0, 600.0, 100.0),
        (2, 0.0, 0.5, 300.0, 400.0, 100.0),
        (2, 0.0, 1.0, 400.0, 400.0, 0.0),
    ],
)
def test_undiscounted_costs(
    calculator, n_wells, mobilization, learning, batch, standalone, savings
):
    """Independent hand results using the module-level source equations.

    T_1=20; T_2=10 with LC=0.5, or 20 with LC=1. Rate=10.
    One well: B=S=100+10*20=300, saving=0.
    Two wells, M=100: B=100+10*(20+10)=400, S=2*(100+200)=600,
    saving=200; without learning B=100+10*(20+20)=500, saving=100.
    With M=0: B=10*(20+10)=300, S=2*200=400, saving=100;
    without learning B=S=10*(20+20)=400, saving=0.
    """
    campaign = make_campaign(n_wells, mobilization, learning)
    assert calculator.batch_vs_standalone_npv(campaign) == {
        "batch_npv": batch,
        "standalone_npv": standalone,
        "batch_savings": savings,
    }
    assert calculator.campaign_total_cost(campaign, base_days_per_well=20.0) == batch


@pytest.mark.parametrize("discount_rate", [0.0, 0.1, 0.5])
def test_discount_argument_is_ignored(calculator, discount_rate):
    """Hand result: B=100+10*(20+10)=400; S=2*(100+200)=600; saving=200.

    Rates are synthetic compatibility probes, not recommended discount rates.
    No dated cash flows are supplied, so changing this argument changes nothing.
    """
    campaign = make_campaign(2, 100.0, 0.5)
    assert calculator.batch_vs_standalone_npv(campaign, discount_rate) == {
        "batch_npv": 400.0,
        "standalone_npv": 600.0,
        "batch_savings": 200.0,
    }


@pytest.mark.parametrize("standalone_count", [1, 2, 10])
def test_standalone_allocation_argument_is_ignored(calculator, standalone_count):
    """Hand result: shared allocation M/N=100/2=50 USD/well.

    Standalone counts are synthetic compatibility probes; the batch denominator
    alone controls allocation (source: pack revision 2, section 3).
    """
    assert calculator.mobilization_savings(100.0, 2, standalone_count) == 50.0


def test_no_savings_returns_legacy_sentinel(calculator):
    """M=0, LC=1, R=10, T=20: B=S=N*200 for every N.

    No strict saving exists; 1 is a legacy sentinel, not a financial threshold.
    Source: pack revision 2 (2026), section 3 and break-even regression gate.
    """
    assert calculator.break_even_n_wells(0.0, 10.0, 20.0, 1.0) == 1
