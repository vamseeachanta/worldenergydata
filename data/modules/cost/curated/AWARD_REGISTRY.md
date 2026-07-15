# AWARD_REGISTRY — provenance

**Datasets:** `data/modules/cost/curated/contract_awards.csv` · `project_cost_statements.csv`
**Issue:** [#1025](https://github.com/vamseeachanta/worldenergydata/issues/1025) (E2, child of hardening epic [#1023](https://github.com/vamseeachanta/worldenergydata/issues/1023))
**Builder:** `scripts/cost/build_award_registry.py`
**Accessed:** 2026-07-15

The machine-readable form of the [#1020](https://github.com/vamseeachanta/worldenergydata/issues/1020)
tranche-1 award research. Where `sanctioned_projects.csv` is the *top-down* total, this is the
*bottom-up* decomposition — who was paid to build which asset — so the reconciliation harness (E5)
can compare the two and report the residual.

## `contract_awards.csv` — 58 rows, 12 projects (27 carry a value or band)

One row per public award, classed `production_hub / sps / surf / installation / drilling_rig / other`.

**A band is a sourced range, never a point.** Contractors disclose award size in named tiers, and
we record the tier's *published definition* as `VALUE_LOW_MM`/`VALUE_HIGH_MM` plus the `BAND_WORD`:

| Contractor | tier → range (USD MM) |
|---|---|
| TechnipFMC | significant 75–250 · substantial 250–500 · large 500–1000 · major 1000+ |
| Subsea7 | sizeable 50–150 · large 300–500 · very large 500–750 · major 750+ |
| Technip Energies | major 1000+ (EUR) |

`VALUE_BASIS` says what kind of number each row is — and three of its values are guardrails against
double-counting or over-crediting in E5:

- **`lease_contract`** — Barossa's BW Opal "$4.6bn" is a 15-year lease+operate value spanning opex,
  **not** capex. Flagged so it is never summed into capex coverage.
- **`midstream`** — Kaskida's Enbridge $700MM is third-party-owned export infra, **outside** BP's
  project capex.
- **`combined`** — Saipem's Payara/Yellowtail values bundle other projects; only an upper bound is
  knowable, so `VALUE_LOW_MM` is blank.

**31 of 58 rows are `not_public`** — and that is the finding, not a gap. US GoM operators procure
hulls, topsides, trees and SURF under long-term frame/master agreements with values never announced
(Whale: every award undisclosed). Recording the award *without* a value preserves the scope and the
contractor; a test forbids a `not_public` row from carrying a number.

## `project_cost_statements.csv` — 19 rows, 11 projects

Operator and partner project-level figures (gross capex, partner net share, carry mechanics), from
press releases and SEC/ASX filings. This is the **second independent costing ladder**: a partner's
net share ÷ its interest cross-checks the gross.

- **Hess's Guyana nets exclude the FPSO element** — proven exactly on Yellowtail: $2.3bn ÷ 30% =
  $7.67bn ≈ $10bn gross − $2.32bn FPSO buyout ($7.68bn). A test enforces that every net/interest lands
  in a sane band around gross.
- **APA's GranMorgu share is a `carry`, not a flat interest** (TotalEnergies pays 87.5% of the first
  $10bn, 75% of the next $5bn) — the `FIGURE_TYPE` records this so the number is not read as a
  working-interest share.
- **JERA's Barossa $300MM is an `entry_price`** for its 12.5% interest, not a capex share — flagged
  so E5 does not treat it as net capex.

## What v1 covers, and what is next

Tranche 1 = the 12 strongest reconciliation-anchor projects. Award + partner-statement research for
the rest of the 80-project set (including the E1 additions) is **E3 (#1026)**. The EDGAR partner-filing
leads noted in the E1 record (Statoil 20-F → Agbami, Total 20-F → Egina) feed that pass.
