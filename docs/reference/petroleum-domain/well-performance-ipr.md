# Well Performance: Productivity Index & IPR

> Petroleum-domain reference: how a well's inflow rate relates to drawdown, and
> the difference between the Productivity Index and the Inflow Performance
> Relationship.
> Last Updated: 2026-06-21

## Overview

Production is driven by the **pressure difference between the reservoir and the
wellbore** (the *drawdown*). Two related tools quantify how much a well will
flow for a given drawdown:

- **Productivity Index (PI / J)** — a single number summarising deliverability.
- **Inflow Performance Relationship (IPR)** — the full rate-vs-pressure curve.

## Productivity Index (PI)

For (under-saturated) flow above the bubble point, inflow is approximately
linear in drawdown:

```
q = PI · (Pr − Pwf)
```

| Symbol | Meaning | Units (field) |
|---|---|---|
| `q` | production (flow) rate | STB/d (oil) or Mscf/d (gas) |
| `PI` (`J`) | productivity index | STB/d/psi |
| `Pr` | average reservoir (drainage) pressure | psi |
| `Pwf` | flowing bottom-hole pressure | psi |

`(Pr − Pwf)` is the drawdown. PI is the **slope** of the inflow line — a single
performance number.

## Inflow Performance Relationship (IPR)

The IPR curve plots `q` against `Pwf` across the operating range. Lower flowing
pressure → larger drawdown → higher rate; higher `Pwf` → lower rate. Where PI is
one number, the **IPR is the complete picture** of how the well performs over
its whole pressure range.

### Linear above, non-linear below the bubble point

- **Above the bubble point** (`Pwf > Pb`): single-phase liquid inflow — the IPR
  is essentially **straight** (constant PI).
- **Below the bubble point** (`Pwf < Pb`): gas comes out of solution, relative
  permeability to oil falls, and the IPR **bends over** (curved). PI is no longer
  constant.

For solution-gas-drive reservoirs below `Pb`, the curved region is commonly
modelled with **Vogel's correlation**:

```
q / q_max = 1 − 0.2 (Pwf/Pr) − 0.8 (Pwf/Pr)²
```

where `q_max` is the absolute open-flow potential (AOF) at `Pwf = 0`. Composite
IPRs use the straight line above `Pb` and Vogel below it.

## Factors that shape the IPR

- **Reservoir pressure** (`Pr`) — depletes over field life, lowering the curve.
- **Permeability** (`k`) — higher k steepens PI (more rate per psi).
- **Skin factor** (`s`) — near-well damage (`s > 0`) reduces PI; stimulation
  (`s < 0`) raises it.
- **Fluid properties** — viscosity, formation volume factor, `Pb`.
- **Reservoir drive mechanism** — sets how `Pr` and GOR evolve.

## Why it matters

Engineers use the IPR to:

- estimate well **deliverability** and predict future production,
- **design artificial lift** (the IPR sets the inflow the lift must match — its
  intersection with the tubing/outflow curve is the operating point in nodal
  analysis),
- **optimise** production strategy, and
- **evaluate stimulation** (an IPR shift after acidising/fracturing quantifies
  the skin improvement).

> Key distinction: the **Productivity Index gives a single performance number;
> the IPR curve gives the complete picture** of how the well will perform.

## In this repository

Production / deliverability modelling lives under
[`src/worldenergydata/production/`](../../../src/worldenergydata/production/).
Decline-curve and forecast methods are described in
[`../../analysis-guides/index.md`](../../analysis-guides/index.md).

## References

- Vogel, J.V. (1968), *Inflow Performance Relationships for Solution-Gas Drive
  Wells*, JPT — the standard solution-gas-drive IPR correlation.
- Standing, M.B. — extensions of Vogel for flow efficiency / skin.
- Industry primer (the explainer that prompted this note).

> Source attribution: definitions framed as standard production-engineering
> knowledge (Vogel IPR); prompted by an industry primer. Last reviewed 2026-06-21.
