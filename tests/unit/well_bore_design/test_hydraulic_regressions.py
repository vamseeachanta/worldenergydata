"""Independent annular-flow cases; synthetic inputs, no field-data defaults."""

import math

import pytest

from worldenergydata.well_bore_design.decision_framework import BoreTypeDecision
from worldenergydata.well_bore_design.hydraulics import WellBoreHydraulics
from worldenergydata.well_bore_design.schemas import BoreType


@pytest.mark.parametrize(
    "q,mw,pv,yp,hole,pipe,floor,legacy,ratio",
    [
        (500, 10, 20, 15, 8.5, 5, 10 / 7, 0.0487, 29.3),
        (100, 9, 10, 10, 8.5, 5, 20 / 21, 0.0023, 418.6),
        (100, 9, 40, 10, 8.5, 5, 20 / 21, 0.0029, 333.1),
        (500, 10, 20, 15, 6, 3.5, 2, 0.2497, 8.0),
    ],
)
def test_annular_yield_floor(q, mw, pv, yp, hole, pipe, floor, legacy, ratio):
    """2025 annular-flow paper, DOI 10.1007/s13202-024-01919-z, A4/A6/A9.

    Stationary-wall force balance gives G >= 4*tau_y/(D_h-D_p).
    In field units: 4*(YP/100)*12*100/(144*gap) = YP/(3*gap)
    psi/100 ft. Hand floors are 15/(3*3.5)=10/7, 10/(3*3.5)=20/21
    (twice), and 15/(3*2.5)=2. Revision 1, Table C11 of the package
    knowledge pack records the rounded legacy losses and unrounded ratios:
    29.3, 418.6, 333.1 and 8.0. These are historical evidence, not targets.
    """
    assert legacy < floor
    assert ratio >= 8
    loss = WellBoreHydraulics().pressure_loss_psi_per_100ft(q, mw, pv, yp, hole, pipe)
    assert loss >= floor


def test_laminar_bingham_worked_case():
    """Paper (2025), A1, A29/A30 with N=1, K=mu, slot clearance h.

    v = G*h^2/(12*mu)*(1 - 3*a/2 + a^3/2), a=2*tau_y/(G*h).
    NIST SP 811 (2008), Appendix B.8: inch=.0254 m, cP=.001 Pa s,
    psi=6894.757 Pa, gpm=6.309020e-5 m^3/s; ft=.3048 m.
    Synthetic 8/4 in annulus: h=.0508 m, PV=100 cP, YP=10/100 lbf/ft2.
    Set a=1/2: tau_y=10*6894.757/14400 Pa, G=4*tau_y/h.
    Then v=G*h^2/(12*.1)*(5/16); Q=v*pi*(.2032^2-.1016^2)/4
    divided by 6.309020e-5. This gives Q=97.67549018539191 gpm and
    G*30.48/6894.757 = 5/3 psi/100 ft. The tolerance is numerical only.
    """
    loss = WellBoreHydraulics().pressure_loss_psi_per_100ft(
        97.67549018539191, 10, 100, 10, 8, 4
    )
    assert loss == pytest.approx(5 / 3, rel=1e-10)


def test_pressure_window_uses_actual_rheology():
    """Same hand case: 100 sections at 5/3 psi gives 500/3 psi.

    The stored ECD convention (pack R2) gives 10+(500/3)/(.052*10000)
    = 10+25/78 ppg. A 10.25 ppg fracture limit is exceeded.
    """
    result = BoreTypeDecision().pressure_window_check(
        BoreType.STANDARD,
        10,
        10.25,
        9.5,
        97.67549018539191,
        10000,
        plastic_viscosity_cp=100,
        yield_point_lbf_100ft2=10,
        hole_od_in=8,
        pipe_od_in=4,
        minimum_window_ppg=0.5,
    )
    assert result["ecd_ppg"] == pytest.approx(10 + 25 / 78, abs=0.00005)
    assert result["compatible"] is False
    assert result["plastic_viscosity_cp"] == 100
    assert result["yield_point_lbf_100ft2"] == 10


@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan, -1])
def test_invalid_pressure_loss_input_refused(bad):
    with pytest.raises(ValueError):
        WellBoreHydraulics().pressure_loss_psi_per_100ft(bad, 10, 20, 15, 8.5, 5)


def test_zero_flow_has_no_circulating_loss():
    assert WellBoreHydraulics().pressure_loss_psi_per_100ft(0, 10, 20, 15, 8.5, 5) == 0


def test_pressure_below_pore_is_incompatible():
    """Zero flow: ECD equals 8 ppg, below the caller's 10 ppg pore bound."""
    result = BoreTypeDecision().pressure_window_check(
        BoreType.STANDARD,
        8,
        12,
        10,
        0,
        8000,
        plastic_viscosity_cp=20,
        yield_point_lbf_100ft2=15,
        hole_od_in=8.5,
        pipe_od_in=5,
        minimum_window_ppg=0.5,
    )
    assert result["compatible"] is False
    assert result["limiting_factor"] == "ecd_below_pore_pressure"


@pytest.mark.parametrize(
    "parameter",
    [
        "mud_weight_ppg",
        "plastic_viscosity_cp",
        "yield_point_lbf_100ft2",
        "hole_od_in",
        "pipe_od_in",
    ],
)
@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan])
def test_each_annular_input_must_be_finite(parameter, bad):
    args = {
        "flow_rate_gpm": 500,
        "mud_weight_ppg": 10,
        "plastic_viscosity_cp": 20,
        "yield_point_lbf_100ft2": 15,
        "hole_od_in": 8.5,
        "pipe_od_in": 5,
    }
    args[parameter] = bad
    with pytest.raises(ValueError, match="finite"):
        WellBoreHydraulics().pressure_loss_psi_per_100ft(**args)


def test_newtonian_limit_without_yield():
    """Paper A29/A30 with N=1 and tau_y=0 gives v=G*h^2/(12*mu).

    Use the earlier hand-case flow, but YP=0: removing the plug multiplier
    5/16 scales the gradient from 5/3 to (5/3)*(5/16)=25/48 psi/100 ft.
    """
    loss = WellBoreHydraulics().pressure_loss_psi_per_100ft(
        97.67549018539191, 10, 100, 0, 8, 4
    )
    assert loss == pytest.approx(25 / 48, rel=1e-10)
