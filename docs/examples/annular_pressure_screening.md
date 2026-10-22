# Annular pressure loss and invalid-depth screening analysis

The sourced laminar Bingham slot model preserves yield resistance and viscosity
sensitivity. In the synthetic vertical case below, total annular loss increases
from the historical estimate of 104.9 psi to 166.7 psi, and the estimated ECD
exceeds the caller's fracture limit. A nonfinite depth is refused before screening.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-22 | Add an independent laminar hand calculation and invalid-depth example to explain the corrected behavior. |

## Inputs and basis

All case values are synthetic caller inputs, not design defaults or acceptance
recommendations. The annulus is vertical, concentric and uniform, with stationary
walls, no cuttings and assumed laminar flow.

| Input | Value |
| --- | --- |
| Hole / pipe outside diameter | 8 / 4 in |
| Mud density | 10 ppg |
| Plastic viscosity / yield point | 100 cP / 10 lbf per 100 ft² |
| Annular length and true vertical depth | 10000 ft each |
| Pore / fracture equivalent density | 9.5 / 10.25 ppg |
| Caller minimum window width | 0.5 ppg |
| Flow | Derived below; displayed to one decimal place: 97.7 US gpm |

The method comes from the public paper *Stepwise derivation and comparison of the
Herschel–Bulkley Laminar Fluid Flow equations—in Annulus* (2025, corrected 2026),
Appendix A1, A29 and A30. Setting `N=1` and `K=mu` gives the Bingham slot form.
The source uses an annular slot analogy; this is not an exact solution for curved
walls. [Public paper](https://doi.org/10.1007/s13202-024-01919-z).

Unit conversions come from NIST SP 811 (2008), Appendix B.8: international inch,
foot, centipoise, psi and US gallon per minute. The psi conversion is rounded as
in that table. [NIST conversion reference](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf).

## Independent hand calculation

With clearance `h=(D_h-D_p)/2`, pressure gradient `G`, and plug ratio
`a=2*tau_y/(G*h)`, the average slot velocity is
`v=G*h²/(12*mu)*(1-a)²*(1+a/2)`.
The force-balance floor follows from Appendix A4, A6 and A9:
`G >= 4*tau_y/(D_h-D_p)`, or `YP/(3*(D_h-D_p))` psi/100 ft in field units.

Choose `a=1/2` for the stated mud. Independently set `G=4*tau_y/h`, giving
`(1-a)²*(1+a/2)=5/16`. The flow is velocity times annular area. In the following
reproduction, every conversion is from NIST Appendix B.8 and every model
coefficient is from the Bingham reduction above:

```python
import math

inch_m, psi_pa = 0.0254, 6894.757
h = (8 - 4) * inch_m / 2
mu = 100 * 0.001
tau_y = 10 * psi_pa / 14400
G = 4 * tau_y / h
velocity = G * h**2 / (12 * mu) * (5 / 16)
area = math.pi * ((8 * inch_m)**2 - (4 * inch_m)**2) / 4
flow_gpm = velocity * area / 6.309020e-5
expected_loss = G * (100 * 0.3048) / psi_pa  # Exactly 5/3 psi per 100 ft.
```

The historical laminar expression was `PV*AV_fpm/(300*gap²)+YP/(225*gap)`.
Its coefficients are recorded implementation history, not qualified physical
constants; see the historical method inventory in the bore-design knowledge
pack. Applied to the same inputs, it gave the following comparison. Calculations
use unrounded values; only displayed answers are rounded.

| Quantity | Historical estimate | Corrected laminar estimate |
| --- | --- | --- |
| Loss, psi/100 ft | 1.0 | 1.7 |
| Total loss, psi | 104.9 | 166.7 |
| ECD, ppg | 10.2 | 10.3 |
| Compatible with the stated pore/fracture limits | True | False |

Total loss is `(5/3)*(10000/100)=500/3 psi`.
The retained rounded hydrostatic convention gives
`ECD=10+(500/3)/(0.052*10000)=10+25/78 ppg`.
The increase in total loss is 61.8 psi (58.9 %). A fracture limit of 10.25 ppg is
exceeded by the corrected estimate. These are model estimates, not proof of
engineering suitability.

```python
from worldenergydata.well_bore_design.decision_framework import BoreTypeDecision
from worldenergydata.well_bore_design.schemas import BoreType

result = BoreTypeDecision().pressure_window_check(
    BoreType.STANDARD, 10, 10.25, 9.5, flow_gpm, 10000,
    plastic_viscosity_cp=100, yield_point_lbf_100ft2=10,
    hole_od_in=8, pipe_od_in=4, minimum_window_ppg=0.5,
)
assert result["compatible"] is False
assert result["limiting_factor"] == "ecd_exceeds_fracture_gradient"
```

## Invalid depth refusal

Pressure gradient is pressure divided by depth. The normal synthetic measured
case is `1200/5000=0.24 psi/ft`. A positive infinite depth cannot be used as a
physical denominator and must not produce a zero gradient or a severe tier.

```python
import pandas as pd

from worldenergydata.analysis.underpressured_screen.screen import estimate_bhp

observations = pd.DataFrame([{
    "reference_depth_ft": float("inf"),
    "pressure_psia": 1200,
    "pressure_kind": "BHP_measured",
}])
# Existing settings from the screen tests; measured BHP needs no gas correction.
settings = {"gas_sg": 0.65, "z_avg": 0.95, "t_avg_rankine": 520}
refused = estimate_bhp(observations, settings)
assert refused["screen_status"].iloc[0] == "NOT_EVALUATED"
assert pd.isna(refused["bhp_gradient_psi_ft"].iloc[0])
```

## Limits and way forward

The pressure-loss model assumes laminar slot flow and does not classify the flow
regime. Turbulence, eccentricity, rotation, cuttings and separate measured-length
versus TVD inputs need a separately qualified method. The caller must supply
rheology, geometry and acceptance policy. Calibration and selection heuristics
elsewhere in these modules retain the limitations recorded in their knowledge
packs. Independent engineering review remains necessary before design use.

Executable counterparts are
`tests/unit/well_bore_design/test_hydraulic_regressions.py::test_laminar_bingham_worked_case`,
`tests/unit/well_bore_design/test_hydraulic_regressions.py::test_pressure_window_uses_actual_rheology`
and
`tests/unit/analysis/test_screen_input_regressions.py::test_nonfinite_or_nonpositive_input_not_evaluated`.
