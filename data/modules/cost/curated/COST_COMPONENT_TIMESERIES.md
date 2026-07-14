# COST_COMPONENT_TIMESERIES — provenance

**Dataset:** `data/modules/cost/curated/cost_component_timeseries.csv`
**Issue:** [#844](https://github.com/vamseeachanta/worldenergydata/issues/844)
**Contract:** every row validates against `worldenergydata.cost.timeseries.schema.CostObservation`
**Accessed:** 2026-07-14

`year × cost-component × band`, with full provenance on every row.

## Composition (349 rows)

| Component | Rows | Span | Primary source |
|---|---|---|---|
| `rig_day_rate_drillship` | 24 | 2000–2026 | Transocean & Valaris fleet status reports; Rigzone |
| `rig_day_rate_semi` | 28 | 2004–2026 | Transocean & Valaris fleet status reports |
| `rig_day_rate_jackup` | 18 | 2004–2026 | Valaris FSRs; Rigzone fixture averages |
| `vessel_day_rate_osv_psv` | 48 | 2000–2025 | Tidewater & GulfMark 10-Ks; Bourbon; Seabrokers |
| `vessel_day_rate_ahts` | 20 | 2000–2025 | Tidewater 10-Ks; Seabrokers (GBP) |
| `vessel_day_rate_msv` | 8 | 2012–2019 | Bourbon Subsea Services — the only public MSV series |
| `surf_cost` (lump-sum awards) | 5 | 2023–2024 | Saipem, McDermott, Subsea7 award releases |
| `index_ucci` / `index_uoci` | 24 | 2006–2020 | Oil & Gas Journal, Offshore Magazine (IHS/S&P quotes) |
| `index_cpi`, `index_ppi_*`, `oil_price_*` | 174 | 1998–2026 | FRED (BLS, EIA) — fetched, not typed |

## Read this before using the day-rate series

### 1. `FIGURE_TYPE` is not decoration — it is the most important column

* **`fleet_average`** — a contractor's "Estimated Average Contract Dayrate" (Transocean),
  "Average Day Rates" (Valaris), "Average Rate Per Day Worked" (Tidewater/GulfMark/Bourbon).
  These are **backlog-weighted averages of units already under contract**. They **lag the
  market** and are **survivorship-biased upward**: stacked rigs are excluded from the
  average, and expensive legacy contracts persist for years after the market has moved.
* **`single_fixture`** — an actual contract award. The market-clearing price.
* **`market_average`** — a third-party average of *awards* (Rigzone, Esgian).

> Transocean's ultra-deepwater fleet average read **$484,000 in Q1-2016** while its own new
> fixtures were being signed at **$170,000** (Transocean Arctic, Det Norske).

**Never average across figure types.** The analysis code (`series.annual_means`) refuses to,
by default. Doing so manufactures a cost history that never happened.

### 2. Currency

Mostly USD. The **Seabrokers North Sea spot rates are GBP** and are stored **unconverted** —
no source states an FX rate and inventing one would inject exactly the kind of unsourced
number this dataset exists to avoid. **Filter on `CURRENCY` before aggregating.**

### 3. Region

Regional and global series are different series. The AHTS series contains one Gulf-of-Mexico
row (a point-in-time March-2000 figure at a regional trough); left unfiltered it anchors a
26-year growth rate to a non-comparable endpoint. `series.annual_means` filters to
`region="global"` by default.

### 4. Splice hazards

* **Tidewater pre-2017** tables are by vessel class on *active* vessels (fiscal years ending
  31 March). **Tidewater 2018-onward** is a whole-fleet average *including stacked vessels*
  (calendar years). **Not splice-compatible.**
* **Calendar-2017 has no clean Tidewater figure at all** — the year is split by a Chapter 11
  Predecessor/Successor accounting boundary. Bourbon covers 2017 instead.
* **Rigzone's mid-2000s deepwater figures pool semis and drillships** into one category and
  cannot be split by class (`confidence=medium`).

## Deliberate exclusions — what we refused to record

| Excluded | Why |
|---|---|
| An entire trade-press day-rate "tracker" domain | Two research passes hit it independently; one assessed it as thin AI-generated SEO content with an unpopulated fixture log and no primary attribution — and one of its figures **contradicted the Seabrokers broker data**. Its numbers were plausible. That is not a reason to trust them. |
| IHS Petrodata 2013 jackup figures (487, 599) | These are **index values, not dollars**. Real and sourced, but mixing them into a $/day series would corrupt it. |
| "$130,000 drillship average, 2000" | The source states a *band* ($120k–$140k across mid-2000 to mid-2004). The midpoint is a derivation, not a printed figure. The band endpoints are recorded; the midpoint is not. |
| Heavy-lift and pipelay day rates | **They do not exist publicly, for any year.** These vessels are not chartered on a published market — they are deployed inside lump-sum EPCI contracts by vertically-integrated owners, and Allseas and Heerema are private and disclose nothing. Any "heavy-lift day rate" in circulation is a broker's model output, not an observed transaction. The honest substitute is the `surf_cost` lump-sum award rows, which carry disclosed km scope and yield a defensible $/km. |
| Well-intervention day rates | Helix discloses utilisation and rate *direction* every quarter, but never a dollar day rate. |

## Known gaps (see the report's §8)

* **Rig day rates 2009–2013** — the largest hole; covers the post-GFC dip and the 2011–12
  re-tightening. Transocean FSRs from that era were not at fetchable URLs.
* **Jackup day rates 2016–2021** — thin through the crash and COVID.
* **UCCI/UOCI 2014–2018** — a **hard gap**. IHS stopped publishing free index levels after
  2013; OGJ resumed printing them in 2019. This is precisely the window containing the 2014
  peak and the 2016 crash. The deflator **refuses to interpolate across it** (see
  `normalization.MAX_INTERPOLATION_SPAN`) — a straight line from 229 to 183 would erase both
  events while looking entirely plausible.
* **MSV 2020–2026** — Bourbon was restructured and stopped publishing; no comparable
  successor series is public.

## Highest-value next sources

1. **SEC EDGAR** — `bp.com`, `chevron.com` and `woodside.com` return HTTP 403 to fetchers,
   but their SEC filings are fetchable and carry the same figures.
2. **Noble Corp fleet status reports** — disclose per-rig rates for *both* floaters and
   jackups; the best route to closing the 2016–2021 jackup gap.
3. **Transocean FSR archive** (2009–2013) — would close the largest rig gap in one pass.
4. **Asmar & Patel (2025), SSRN** — an academic reconstruction of the UCCI series; would
   close the 2014–2018 blackout. Behind Cloudflare.
5. **EIA "Trends in U.S. Oil and Natural Gas Upstream Costs" (March 2016)** — its appendix
   *is* a commissioned IHS study with a dedicated deepwater GOM chapter. Public and free.
