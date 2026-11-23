# Petrophysics Fundamentals: Porosity, Permeability, Compressibility

> Petroleum-domain reference: the rock/fluid properties that decide how much
> hydrocarbon a reservoir stores and how readily it flows.
> Last Updated: 2026-06-21

## Overview

> Store it, then flow it — **porosity holds the oil, permeability delivers it.**

Three properties underpin volumetrics, dynamic models, and development
decisions. Without reliable values for them, even the most sophisticated
simulation rests on an uncertain foundation.

## Porosity (φ) — storage capacity

Porosity is the fraction of the rock volume that is **pore space available to
hold fluids** (hydrocarbons + water).

- **Total porosity** — all void space, including isolated/non-connected pores.
- **Effective porosity** — excludes isolated pores; the connected pore space
  that actually participates in fluid movement. **Effective porosity is the
  metric that matters** for producible volumes and flow.

Porosity feeds the **volumetric** estimate of hydrocarbons in place (alongside
net pay, area, saturation, and formation volume factor).

## Permeability (k) — connectivity / flow capacity

Permeability is the **connectivity** of the pore space — the rock's ability to
transmit fluid under a pressure gradient (Darcy's law; field unit: millidarcy,
mD). High porosity does **not** guarantee high permeability: a rock can store a
lot yet flow poorly if its pores are poorly connected.

### The φ–k relationship is rarely linear

Porosity and permeability are correlated but **not linearly** — the relationship
varies with rock type, sorting, cementation, and pore geometry.
**Porosity–permeability crossplots** are a practical tool to:

- identify productive ("pay") zones,
- characterise **reservoir heterogeneity** and rock-typing,
- flag diagenetic or facies controls on flow.

## Compressibility — pressure response

Both rock and fluids respond to changing pressure:

- **Rock (pore-volume) compressibility** — pore volume shrinks as reservoir
  pressure declines; a component of the reservoir's energy and of compaction.
- **Fluid compressibility** — governs **expansion drive** as pressure drops
  (oil, water, and especially gas expand to help push fluids to the well).

Total system compressibility (`ct`) combines rock and fluid terms weighted by
saturation. It **directly influences recovery estimates and well productivity**
over the field's operating life, and enters material-balance and well-test
analysis.

## Why it matters

Reliable porosity, permeability, and compressibility data underpin:

- **Volumetrics** — hydrocarbons in place (porosity, saturation, net pay),
- **Dynamic models** — flow simulation and history matching (permeability,
  heterogeneity, compressibility),
- **Development decisions** — well count/placement, recovery, and economics.

## In this repository

Reservoir-characterisation and resource-estimation code lives under
[`src/worldenergydata/reservoir/`](../../../src/worldenergydata/reservoir/).
A petrophysics workflow reference is linked from
[`../../petrophysics.md`](../../petrophysics.md).

## References

- Tiab, D. & Donaldson, E.C. — *Petrophysics* (porosity, permeability,
  compressibility fundamentals).
- Darcy's law / SCAL (special core analysis) for permeability and relative
  permeability.
- Industry primer (the explainer that prompted this note).

> Source attribution: definitions framed as standard petrophysics knowledge;
> prompted by an industry primer. Last reviewed 2026-06-21.
