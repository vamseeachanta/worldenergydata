# Reserves & Resources Classification

> Petroleum-domain reference: how recoverable volumes are categorised by
> commercial maturity and technical certainty.
> Last Updated: 2026-06-21

## Overview

Reserves are the quantities of petroleum **anticipated to be commercially
recoverable** from known accumulations under defined conditions. Three
dimensions frame every reserves statement:

1. **Technical confidence** — how well the volume is constrained by data.
2. **Uncertainty** — the spread of outcomes given subsurface and market unknowns.
3. **Economic viability** — whether the volume is commercial at the price/cost case.

A volume is **Reserves** only if it is simultaneously:

- **Recoverable** — technically feasible to extract with current technology,
- **Commercial** — economically viable to produce, and
- **Uncertain** — subject to subsurface and market variables (so reported as a range).

These definitions follow the **SPE/WPC/AAPG/SPEE Petroleum Resources Management
System (SPE-PRMS)**, the industry-standard framework. The same classification
underpins regulatory reporting (e.g. SEC) and field-development economics.

## Resources classes by commercial maturity

| Class | Discovered? | Commercial? | Notes |
|---|---|---|---|
| **Reserves** | Yes | Yes (commercial) | On production, approved, or justified for development |
| **Contingent Resources** | Yes | Not yet commercial | Discovered but pending a contingency (commerciality, technology, market, infrastructure) |
| **Prospective Resources** | No (undiscovered) | — | Estimated volumes in undrilled prospects |

Maturity is the **vertical** axis (discovered → commercial); certainty is the
**horizontal** axis (low → high confidence) within each class.

## Reserves — certainty categories

Within commercial Reserves, certainty is split into incremental categories.
These are **certainty levels, not a maturity ladder** — a project carries some
of each.

| Category | Name | Meaning |
|---|---|---|
| **1P** | Proved (P1) | Reasonably certain to be recoverable — high confidence |
| **2P** | Proved + Probable | Best estimate; Probable is *more likely than not* to be recovered |
| **3P** | Proved + Probable + Possible | High estimate; Possible has a lower chance of recovery |

The cumulative scenarios are the way volumes are usually quoted:
`1P ≤ 2P ≤ 3P`.

## Probabilistic ranges (P90 / P50 / P10)

When estimated probabilistically, the categories map to confidence percentiles
of the recoverable-volume distribution:

| Percentile | Probability the actual volume **equals or exceeds** this value | Aligns with |
|---|---|---|
| **P90** | 90 % | 1P (Proved) — conservative |
| **P50** | 50 % | 2P (best estimate / median) |
| **P10** | 10 % | 3P (optimistic) |

So P90 is the low/confident number and P10 the high/optimistic number; the
deterministic 1P/2P/3P categories are intended to be broadly consistent with
P90/P50/P10 respectively.

## Contingent Resources (1C / 2C / 3C)

Discovered volumes that are **not yet commercial** carry the same low/best/high
confidence split, labelled with a **C**:

- **1C** — low estimate (≈ P90)
- **2C** — best estimate (≈ P50)
- **3C** — high estimate (≈ P10)

They share commercial maturity (sub-commercial, pending a contingency) and are
differentiated only by confidence. A maturing project migrates **1C/2C/3C →
1P/2P/3P** once the contingency clears (e.g. a development is sanctioned).

> A reviewer's caution worth repeating: 1P/2P/3P (and 1C/2C/3C) are **different
> certainty categories**, not steps of increasing commercial maturity — and
> because commerciality depends on price, **hydrocarbon-price scenarios move the
> reserves boundary** materially.

## Economic evaluation

The commerciality test rests on a discounted-cash-flow (DCF) model of the
project. Core metrics:

| Metric | What it tells you |
|---|---|
| **Cash flow** | Net revenue less capex, opex, taxes/royalties over time |
| **Payout (payback) period** | Time to recover the initial investment |
| **NPV** | Present value of net cash flows at the discount rate — the value created |
| **IRR** | Discount rate at which NPV = 0 — the project's return |
| **Economic limit** | Production rate/time at which net cash flow turns negative; defines the end of commercial life and hence the recoverable volume |

Because the economic limit and commerciality both depend on price and cost, the
reserves number is **conditional on a price/cost case** and is re-tested as those
assumptions change.

## In this repository

DCF / NPV / IRR machinery lives in
[`src/worldenergydata/economics/dcf.py`](../../../src/worldenergydata/economics/dcf.py);
recoverable-volume estimation in
[`src/worldenergydata/reservoir/resource_estimation.py`](../../../src/worldenergydata/reservoir/resource_estimation.py).
See also the economic methods in [`../../analysis-guides/index.md`](../../analysis-guides/index.md).

## References

- SPE/WPC/AAPG/SPEE — **Petroleum Resources Management System (PRMS)** (the
  authoritative definitions for the classes and categories above).
- U.S. SEC reserves reporting rules (Proved-reserves disclosure).
- Industry primer (the explainer that prompted this note).

> Source attribution: definitions framed as standard reservoir-engineering
> knowledge per SPE-PRMS; prompted by an industry primer. Last reviewed 2026-06-21.
