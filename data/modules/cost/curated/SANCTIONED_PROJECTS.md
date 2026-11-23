# SANCTIONED_PROJECTS — provenance

**Dataset:** `data/modules/cost/curated/sanctioned_projects.csv`
**Issue:** [#844](https://github.com/vamseeachanta/worldenergydata/issues/844), scope addition #2
**Accessed:** 2026-07-14

The **top-down anchor**. Operators disclose a *total* and a *scope* at FID; that total is the
hardest number in this whole dataset — it is what someone actually committed to spend. The
bottom-up component series is reconciled against it (report §6).

**40 projects, FID 2011–2026. 23 carry a disclosed USD CAPEX, totalling $177bn.**
The other 17 are recorded with `SANCTIONED_CAPEX_USD_MM` blank — which is a *finding*, not a
failure. See below.

## `CAPEX_BASIS` is mandatory and load-bearing

A figure that is *gross project cost* and one that is *operator net share* differ by a factor
of two or more. Scarborough is `$12bn (100%, $6.9bn Woodside share)`. Mixing the two silently
is the fastest way to corrupt a benchmark table, so `SanctionedProject` **refuses to
construct** a row that carries a CAPEX without a stated basis.

## Why 17 projects have no CAPEX — and why that is correct

These are not research failures. They are how the industry actually discloses.

| Operator / project | What they disclose instead |
|---|---|
| **Shell** — Vito, Whale, Sparta, Appomattox, Bonga North | **Never a dollar figure.** Shell gives a break-even price (`<$35/bbl`), an IRR (`>25%`), or a % cost reduction (`>70% vs original concept`). The widely-cited "$10bn Appomattox" is **not in Shell's release** and is not recorded here. |
| **Petrobras** — Búzios, Mero, Sépia, Atapu, Itapu | No per-project sanctioned CAPEX. Only aggregate business-plan CAPEX and **FPSO *lease* values** — which are a lease commitment, not a project cost. Conflating the two would corrupt the column. Brazil is structurally the weakest region here; **Bacalhau is the only Brazilian row with a real sanctioned figure, and only because Equinor operates it.** |
| **Eni** — Coral South, Coral North, Greater PAJ | Systematically omits CAPEX from FID releases (confirmed across all three). Excellent on scope; useless on cost. |
| **BP** — GTA | Never published one; `bp.com` also 403s to fetchers. The $4.6–4.8bn circulating in trade press is **unverified and not imported**. |
| **TotalEnergies** — Kaminho | The universally-reported "$6bn" appears in a World Oil **headline** but **not in the article body**. A headline is not a source. |

## Three traps found and defused

1. **Agogo's "$7.8 billion" is contract-award value, not project CAPEX.** Azule disclosed
   *"main contracts worth approximately $7.8bn in total"*. Multiple outlets restate this as
   "total investment". Treating it as sanctioned CAPEX would have corrupted the column.
   **Recorded as `null`, with the trap documented in `NOTES`.**
2. **Sparta *is* North Platte.** TotalEnergies and Equinor exited North Platte in 2022; Shell
   farmed in, took operatorship and renamed it. Listing both would double-count a single
   development. **Recorded as one project.**
3. **Ichthys ($34bn) and Scarborough ($12bn) bundle an onshore LNG plant into the CAPEX.**
   These carry `SCOPE_IS_OFFSHORE_ONLY=False` and are **excluded from back-allocation**.
   Splitting a $34bn integrated LNG project with offshore stage-share priors would book
   ~$8bn of onshore gas-processing plant as "SURF", produce a per-stage cost wrong by an
   order of magnitude, and then feed that error straight into the reconciliation — corrupting
   the one independent check this dataset has. They remain in the table; they are just not
   allocated.

## Currency discipline

Norwegian (NOK 49bn / 41bn / 18.6bn), UK (£4.5bn) and Danish (DKK 21bn) figures are recorded
with `SANCTIONED_CAPEX_USD_MM` **blank** and the native figure preserved in `CAPEX_BASIS`.
**No FX rate was invented anywhere.** Vår Energi is the one operator that states cost in both
currencies (`USD 4.3 billion (NOK 40.7 billion)`), which solves the problem outright.

## Excluded rows

* **Jackdaw (Shell)** — the source page is JS-rendered and yielded **no verbatim quote**. A row
  without a quote fails the citation contract. Dropped rather than recorded on a headline.
* **Zohr (Eni)** — no CAPEX, no FID year. Nothing to anchor in a *sanctioned-project* table.

## The cost-overrun signal — the richest unmined seam here

Only **one** project in this table has a documented cost *revision* (Mad Dog 2: concept
~$20–22bn → sanctioned $9bn, a ~60% cut). `ACTUAL_COST_USD_MM` is blank on 39 of 40 rows,
because **as-spent costs are essentially never published**. The exceptions are worth chasing:

* **Johan Castberg** — NOK 49bn (2017) → 57bn (rebased) → 80bn (2023) → **86bn at startup**.
* **Balder X** — revised to **USD 4.3bn (NOK 40.7bn)**, +$1.2bn over the sanction.
* **Ichthys** — sanctioned $34bn (2012), actual widely reported ~$45bn (not verbatim-sourced,
  so not recorded).
* **Tyra** — DKK 21bn → reported outturn near DKK 27bn.

**Equinor and Vår Energi are unusually candid about restating.** Most operators simply go
silent after FID — which is precisely why a sanctioned-vs-actual dataset is valuable and
precisely why it is hard.

## Best sources, ranked

1. **ExxonMobil Guyana / Stabroek FID releases** — best-in-class disclosure. Every one of the
   seven phases states gross cost, well count, drill centres, FPSO, capacity, and resource.
2. **Equinor newsroom** — every Norwegian PDO carries an explicit NOK figure, well count,
   water depth and break-even, *and* honest overrun updates.
3. **Norwegian Offshore Directorate (Sodir) / norskpetroleum.no** — authoritative per-field
   investment and reserves for all Norwegian fields. Machine-readable. Highest-yield untapped
   source.
4. **SEC EDGAR** — the workaround for bp/Chevron/Woodside/Hess, all of which 403 to fetchers.
