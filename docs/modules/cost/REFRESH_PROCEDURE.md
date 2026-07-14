# Cost-basis time-series — refresh procedure

**Issue:** [#844](https://github.com/vamseeachanta/worldenergydata/issues/844)
**Status:** milestone 1 (living dataset — this doc is a standing artifact, not a one-off)
**Owner:** cost module (`packages/worldenergydata-cost`)

This dataset is explicitly a **living** one. Issue #844's whole point is that the
FDAS cost deck went stale because nobody owned refreshing it. This document exists
so that does not happen again.

---

## 1. What this dataset is

A `year × cost-component × water-depth/development-system band` table of the cost
components used in offshore field economics, plus a top-down anchor table of
sanctioned deepwater project costs.

| Artifact | Path |
|---|---|
| Component time-series | `data/modules/cost/curated/cost_component_timeseries.csv` |
| Sanctioned projects | `data/modules/cost/curated/sanctioned_projects.csv` |
| Provenance doc (components) | `data/modules/cost/curated/COST_COMPONENT_TIMESERIES.md` |
| Provenance doc (projects) | `data/modules/cost/curated/SANCTIONED_PROJECTS.md` |
| HTML report | `reports/cost/cost_basis_timeseries.html` |
| Derived: inflation verdicts | `reports/cost/inflation_verdicts.csv` |
| Derived: stage allocations | `reports/cost/stage_allocations.csv` |
| Code | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/` |

---

## 2. The one rule

> **A figure without a source is a TODO row, not a guess.**

This is enforced structurally, not by discipline. `CostObservation` (in
`timeseries/schema.py`) will refuse to construct:

* a `sourced` row without a source title, URL, quote and access date;
* a `todo` row that carries a value (an unsourced number is a fabrication);
* a `real` row without a stated `basis_year`;
* a `fitted` / `allocated` / `assumed` row that does not explain its method.

`read_timeseries_csv` re-validates on read, so the CSV can be safely hand-edited
in a spreadsheet — a hand-added row that carries a number but no citation will
fail loudly on the next run rather than silently entering the deck.

**If you take one thing from this document:** when the refresh finds no source for
a cell, leave it blank and add a `todo` row. Do not interpolate it by hand. The
fitted curves (§6) are the *only* sanctioned way to fill a gap, and everything they
produce is stamped `fitted` and rendered differently in the report.

---

## 3. Re-run command

```bash
cd <repo root>
uv sync                                            # once

# 1. Re-pull the reference/deflator series from FRED (network).
uv run python -m worldenergydata.cost.timeseries.refresh

# 2. Rebuild the report + derived CSVs from the curated data (no network).
uv run python scripts/cost/build_cost_basis_report.py

# 3. Re-run the tests.
uv run pytest tests/unit/cost/ -v
```

Step 1 rewrites **only** the reference-series rows (CPI, PPI, Brent, WTI) — the
rows it owns and can fetch deterministically. It does **not** touch the
hand-curated rig/vessel/project rows, which are research outputs, not API pulls.
That separation is deliberate: an automated refresh must never be able to silently
overwrite a human-sourced, hand-cited figure.

---

## 4. Cadence

| Layer | Cadence | Why |
|---|---|---|
| **Reference series** (CPI, PPI, Brent, WTI) | **Monthly** — fully automated, zero research cost | BLS/EIA publish monthly; the deflators drift underneath every real figure |
| **Rig day rates** | **Quarterly** | Contractor fleet-status reports (Transocean, Valaris, Noble, Seadrill) drop quarterly and disclose actual contracted rates — the single best public source |
| **Vessel day rates** | **Quarterly** | Tidewater / Bourbon / Helix quarterly results disclose fleet-average day rates |
| **Sanctioned projects** | **Quarterly, or on any FID** | An FID press release is the highest-value event for this dataset. If a deepwater project is sanctioned, add it that week |
| **UCCI / UOCI anchors** | **Opportunistically** | Proprietary; values surface irregularly in press coverage and conference decks. Add anchors whenever one is spotted |
| **Full re-source sweep** | **Annually** | Re-verify that source URLs still resolve; sources rot |

---

## 5. Sources — where each component actually comes from

### Reference / deflator series — automated, primary
Pulled from FRED's public CSV endpoints (no API key). Series IDs are pinned in
`timeseries/reference_series.py` and **each was verified to return HTTP 200 with
real observations before being committed**; candidate IDs that 404'd were dropped,
not guessed at.

| Series | FRED ID | Publisher |
|---|---|---|
| CPI-U, all items | `CPIAUCSL` | BLS |
| PPI: drilling oil & gas wells (NAICS 213111) | `PCU213111213111` | BLS |
| PPI: support activities for O&G (NAICS 213112) | `PCU213112213112` | BLS |
| PPI: oil & gas field machinery (NAICS 333132) | `PCU333132333132` | BLS |
| Brent | `MCOILBRENTEU` | EIA |
| WTI | `MCOILWTICO` | EIA |

Monthly observations are reduced to a **calendar-year mean** (the right reduction
for a cost basis: a project spending through a year pays close to the year's
average, not its December print). Partial years are flagged as such in `NOTES`.

### Rig day rates — research, quarterly
Best sources, in priority order:
1. **Contractor fleet status reports** — Transocean, Valaris, Noble, Seadrill.
   These are SEC-adjacent disclosures listing *actual contracted day rates per rig*.
   Highest confidence available.
2. **Esgian Rig Analytics / Bassoe Offshore** — public market commentary and
   day-rate indices.
3. **S&P Global (IHS Petrodata)** — public summaries.
4. **Trade press** — Upstream, Offshore Magazine, Rigzone, Reuters. Usable, but
   mark as `press_release` / `secondary_operator_confirmed` priority.

Keep drillship / semi-sub / jackup **separate**, and keep ultra-deepwater,
harsh-environment and benign segments separate. They are different markets and
averaging them destroys the signal.

### Vessel day rates — research, quarterly
1. **Tidewater, Bourbon, Solstad, DOF, Havila** quarterly results — disclose
   *fleet-average day rates*. Excellent primary series.
2. **Helix Energy Solutions** quarterly — well-intervention vessel rates.
3. **Clarksons / Westwood / Riviera** — OSV/AHTS/PSV spot rate indices.

**Heavy-lift and pipelay day rates largely do not exist publicly** — that work is
contracted lump-sum, not chartered at a published rate. Do not invent them. Where
possible, capture **lump-sum SURF contract awards with scope** instead
(e.g. "$800MM SURF award, 100 km of flowline") which give a defensible $/km proxy.

### Sanctioned projects — research, on every FID
**Operator FID press releases are the gold source** — they almost always state the
sanctioned CAPEX and the scope (well count, host type, water depth).

Always record `CAPEX_BASIS`. A figure that is *gross project cost* and one that is
*operator net share* differ by a factor of two or more; a `$` figure without its
basis is worse than no figure, because it looks usable. Where a project's cost was
revised (Mad Dog 2 being the canonical example), record **both** figures with dates.

### UCCI / UOCI — opportunistic
Proprietary to S&P Global. There is no public endpoint. Only scattered values
quoted in press releases, conference decks and academic papers are sourceable.

**Oil & Gas Journal is the single most productive source** — it is not paywalled,
it fetches cleanly, and it reprinted UCCI/UOCI levels every quarter. Most of the
24 sourced anchors came from OGJ. A systematic crawl of its construction-cost
article series is the cheapest way to extend this series.

Consequently the UCCI deflator is **anchor-and-interpolate**: sourced anchor years
carry their citation, gap years are linearly interpolated and flagged, and the
series is **never extrapolated beyond its anchors**. Outside the anchor range, the
UCCI-real series is simply not published. `build_deflator` raises rather than
silently substituting CPI.

#### The 2014–2018 blackout — do not try to bridge it
There is **no sourceable UCCI or UOCI level for any quarter in 2014, 2015, 2016,
2017 or 2018.** IHS stopped issuing the free press releases that carried the
numbers after 2013; OGJ only resumed printing levels in 2019. The sourced record
therefore jumps from **229 (Q3 2013)** straight to **182.6 (Q3 2019)**.

That gap contains the two most important events in the entire series — the 2014
peak and the 2016 crash. A straight line across it would glide smoothly from 229
to 183, erase both, and look entirely plausible. So `MAX_INTERPOLATION_SPAN = 3`
**refuses to bridge it**, and the UCCI-real series is simply not published for
those years. *"We don't know what sector costs did in 2016"* is the true answer.

Two priors that were **checked and found unsupported** — do not let them back in:
* "UCCI recovered to the 220s in 2014" — **not confirmed** by any sourceable value.
* "UCCI fell to the 160s in 2016–17" — **not supported**; the 160s never appear
  for UCCI in any sourced year.

Also note a genuine **source conflict in UOCI 2009**: OGJ (June 2009) puts Q1-2009
at **187**; OGJ (Dec 2009) says the index "rose 1% ... to **168**" by Q3. These are
irreconcilable — most likely an IHS revision/rebasing in H2 2009. Both are recorded
with a conflict flag. **Do not interpolate across 2009 for UOCI.**

The fastest route to closing the blackout is **Asmar & Patel (2025), SSRN** — an
academic reconstruction of the UCCI series (and a companion UOCI paper). Behind
Cloudflare; needs institutional or manual access.

---

## 6. Method notes for the refresher

### Inflation normalization (scope addition #1)
Two deflator bases are published and **never averaged**:
* **CPI** — general purchasing power. "Did this outrun the broad price level?"
* **UCCI** — upstream sector. "Did this outrun the supply chain it sits inside?"

They routinely disagree in sign over a given window. **That disagreement is a
finding, not an error.** Report both.

Basis year is set by `BASIS_YEAR` in `scripts/cost/build_cost_basis_report.py`
(currently **2025**). Bump it there; do not scatter basis years through the data.

### Back-allocation (scope addition #2)
Stage shares are **priors, not measurements** — operators disclose a total and a
scope, essentially never a stage breakdown. The priors live in one reviewable table
(`STAGE_SHARE_PRIORS` in `back_allocation.py`), carry ±8–10 share-point bands, and
are flagged `assumed` everywhere they surface.

**Replace a prior with a disclosed split the moment one exists** — that is what
`StageShares.from_disclosed()` is for, and it collapses the uncertainty band to zero.

The bottom-up reconciliation gap (allocated drill slice vs day-rate × duration) is
a **deliverable, not a defect**. Do not tune the priors until the gap closes; that
would destroy the only independent check this dataset has. Report the gap.

### Fitted curves (scope addition #3)
Four candidate forms (linear / exponential / oil-linked / oil-linked-lagged),
chosen by **adjusted** R² so a richer model must earn its extra parameter.

When `oil_linked` wins, that is a substantive finding: the component is priced off
the *cycle*, not the *calendar*, and extrapolating it in time alone is meaningless.

Curves refuse to fit below **5 distinct sourced years**. If a component won't fit,
the answer is more data, not a lower threshold.

---

## 7. Adding a new sourced row by hand

1. Open `data/modules/cost/curated/cost_component_timeseries.csv` in a spreadsheet.
2. Add a row. Fill **every** provenance column:
   `SOURCE_TITLE`, `SOURCE_URL` (absolute http/https), `PAGE_REFERENCE`,
   `QUOTED_TEXT` (the *verbatim* sentence containing the number), `ACCESSED_DATE`,
   `CONFIDENCE`, `SOURCE_PRIORITY`.
3. Set `PROVENANCE=sourced`.
4. Re-run the report build. If you got the contract wrong, it will fail loudly.

If you cannot find a source: set `PROVENANCE=todo`, leave `VALUE` **blank**, and
put what you looked for in `NOTES`. That row is a genuine contribution — it tells
the next person where to dig.
