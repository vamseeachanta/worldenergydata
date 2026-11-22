# Constant 2026 USD project costs

[Issue 1896](https://github.com/vamseeachanta/worldenergydata/issues/1896), under
[epic 1038](https://github.com/vamseeachanta/worldenergydata/issues/1038).

`worldenergydata.cost.escalation` restates the held USD labels without changing
nominal costs or introducing an exchange rate. The derived view is
`data/modules/cost/curated/sanctioned_projects_2026.csv`. It is a calculation
output, not another source dataset; it shall not be ingested as a disclosure.

The view retains one sanctioned row per project, including undisclosed amounts,
plus a separate row for each nonblank actual/revised amount.
`NOMINAL_COST_COLUMN` identifies which original field is escalated. The held
snapshot contains 80 projects, 67 sanctioned labels and three actual/revised
labels: 70 derived amounts in 83 rows. Blank sanctioned amounts stay blank.
Actual/revised rows are not summed with sanctioned rows.

## Method

For a nominal amount C with nominal purchasing-power year a:

`CAPEX_USD_MM_2026 = C * ESCALATION_FACTOR`

A single-index segment from a to b has factor `I[b]/I[a]`. The machinery/drilling
PPI blend is an arithmetic mean of **endpoint growth ratios**:

`PPI(a,b) = 0.5 * machinery[b]/machinery[a] + 0.5 * drilling[b]/drilling[a]`

The equal weights are an explicit method assumption. They are not measured
project cost shares or fitted coefficients. Index levels with different reference
bases are never averaged directly. Independent rebasing of either PPI leaves
the factor unchanged. The blend is not chained through annual mean ratios.

Selection, in order:

1. UCCI when every year of the requested segment is covered.
2. One contiguous UCCI block from a to its last anchor j, followed by
   `PPI(j,2026)`: factor `UCCI[j]/UCCI[a] * PPI(j,2026)`. There is no UCCI re-entry.
3. Both covered PPIs for the full interval.
4. Covered CPI as the last resort.
5. Both PPIs with explicitly flagged endpoint extrapolation, then CPI with
   explicitly flagged endpoint extrapolation. Neither may extend more than one
   year beyond held coverage. A mixed covered/extrapolated PPI pair qualifies
   only when both components can be evaluated. One PPI alone never qualifies.

UCCI is never extrapolated. A base equal to its block end uses PPI directly,
without a redundant UCCI identity segment. Reverse conversions are supported by
the Python factor API: contiguous UCCI is tried first, otherwise PPI/CPI; the
forward-only UCCI/PPI splice is not inverted implicitly.

Multiple UCCI prints in one year are averaged, following existing
`timeseries.normalization.build_deflator`. These are means of **held period
prints**, not complete annual means. Interpolation is linear in level between
surrounding annual anchors, with at most `MAX_INTERPOLATION_SPAN=3` missing years
(`right_year-left_year-1 <= 3`). Four missing years do not qualify. The one-year
extrapolation rule uses the two nearest outer annual anchors and their linear
slope, not a forecast model. Nonpositive/nonfinite results fail validation.

In the held snapshot, UCCI's contiguous blocks are 2006–2013 (2007 interpolated)
and 2019–2020. The 2014–2018 blackout stays unbridged. Earlier bases in the first
block join PPI at 2013; a 2019 base joins at 2020. Bases 2013 and 2020 use PPI
directly. CPI and extrapolation fallbacks are tested synthetically but are not
used for current held project values.

Independent held-data checks:

- 2010 factor = `(229/207) * 0.5*(332.822/263.7667 + 396.3942/433.7167)`.
- 2013 factor = `0.5*(332.822/263.7667 + 396.3942/433.7167)`.
- 2009 UCCI annual anchor = `(210+202)/2 = 206`.
- A 2026 nominal amount has factor 1 and is unchanged.

Monotonicity is a property check on a fixed index path: non-decreasing indices
give non-increasing factors for later nominal years, and vice versa. Observed
downturns remain valid. Switching index paths between project years can introduce
discontinuities; factor monotonicity across path switches is not asserted.

## Nominal year and original caveats

`INDEX_BASE_YEAR` is the purchasing-power year of the nominal cost, not the
reference year printed in an index's units. Precedence is:

1. Explicit `COST_STATEMENT_YEAR` for sanctioned amounts, or independently
   `ACTUAL_COST_STATEMENT_YEAR` for actual/revised amounts, in the project input.
2. A matching held-evidence decision in
   `data/modules/cost/curated/sanctioned_project_cost_years.csv`.
3. FID, labeled `FID year fallback: cost statement year unestablished`.

An explicit year conflicting with a reviewed sidecar decision is rejected;
the evidence decision must be reconciled before calculation.

The sidecar pins PROJECT, SOURCE_URL, COST_COLUMN, COST_STATEMENT_YEAR, EVIDENCE
and RATIONALE. Evidence shall occur verbatim in held CAPEX_BASIS, SOURCE_TITLE or
NOTES and contain the selected year. Orphans, duplicates and unsupported years
fail validation. A substring check establishes traceability, not independent
source verification; these year decisions require review when held data changes.

Explicit historical sanction/approval years are retained for amounts restated
in later documents only when held text dates the identical amount to that event.
An FY-labelled statement alone does not establish an earlier price vintage.
Thus the original 2009 and 2014 amounts retain their original
years even though the held documents postdate them. The FY2011 decision is an
annual approximation; its fiscal-to-calendar price vintage is not established.
The revised 2017 amount has its own statement year, separate from its historical
2013 sanction figure. The original GBP-only sanction source's later USD
restatement carries an inherited FX-basis limitation, recorded in the sidecar;
the escalation module does not invent another FX rate.

Two actual/revised statement years are not established by the held dated
evidence. They retain the issue-authorized FID fallback (2009 and 2019) with a
visible chronology and bias warning. Bias direction is unknown and path-dependent:
the fallback can overstate or understate escalation. Its magnitude cannot be
established until that year is obtained. The 2009 actual-cost fallback explicitly
predates the related held 2010 first-oil statement: this chronology inversion is
flagged rather than presenting 2009 as an established outturn price vintage.
The issue's fallback rule is retained because a lower-bound year is not a known
cost-statement year. These results are approximate on that
basis. Obtaining dated actual/revised statements is an open data point.

Floors, ceilings, approximate labels, gross/net ownership, integrated onshore LNG
scope, phase boundaries and disputed currency labels remain in the original
fields and `ESCALATION_NOTE`. They are preserved as **historical source context**;
a populated nominal label takes precedence over stale “left null” research notes.
Restatement does not qualify a bound as a point estimate, turn a revised estimate
into audited outturn, resolve a currency dispute, or equalize project scope.
Native-currency-only figures with blank USD columns remain blank; no FX occurs.

## Held index sources and limitations

The authoritative observations and their quotes, URLs, access dates, units and
source notes remain in
`data/modules/cost/curated/cost_component_timeseries.csv`. The following are
source identities **as held**, not a claim of fresh external verification.

| Component | Held coverage and source identity |
|---|---|
| `index_ppi_machinery` | 1998–2026; BLS via FRED, “PPI by Industry: Oil and Gas Field Machinery and Equipment (NAICS 333132) (PCU333132333132)”; December 1980=100 |
| `index_ppi_drilling` | 1998–2026; BLS via FRED, “PPI by Industry: Drilling Oil and Gas Wells (NAICS 213111) (PCU213111213111)”; December 1985=100 |
| `index_cpi` | 1998–2026; BLS via FRED, “CPI for All Urban Consumers: All Items in U.S. City Average (CPIAUCSL)”; 1982–84=100 |
| `index_ucci` | IHS/CERA, now S&P, Upstream Capital Costs Index, 2000=100; 13 period prints, nine held years, 2006–2020 |

Table 1. Held component identities; no new index levels are supplied by this method.

The held UCCI publications are:

| Print | Held SOURCE_TITLE |
|---|---|
| 2006 | Offshore Magazine, GLOBAL DATA |
| 2008 | IHS CERA press release |
| 2009 Q1 | Oil & Gas Journal (22 Jun 2009) |
| 2009 Q3 | Oil & Gas Journal (8 Dec 2009) |
| 2010 Q3 | Oil & Gas Journal |
| 2011 approximately Q2 | Offshore Magazine, 'Operating costs rise' (1 Aug 2011) |
| 2012 Q1 | Oil & Gas Journal |
| 2012 Q3 | Oil & Gas Journal (4 Dec 2012) |
| 2013 Q3 | Oilfield Technology (11 Dec 2013) |
| 2019 Q3 and Q4 | Oil & Gas Journal (two separate held source URLs) |
| 2020 Q2 and Q3 | Oil & Gas Journal (two separate held source URLs) |

Table 2. Period identities and titles are resolved to exact source URLs in each index trace.

The 2006 observation covers six months ending October; 2008 is a Q3 peak print;
2011 is an implicitly stated, medium-confidence level. Global UCCI and US PPI
measure different baskets and geographies. Different selected paths across rows
limit comparability. There is no qualified uncertainty interval for these proxies.

As retrieved on 2026-11-12, the two PPI 2026 means contain **nine monthly
observations** (January to September) and the CPI 2026 mean contains ten
(January to October), not twelve. CPI 2025 contains eleven. The month counts
change with each monthly refresh; the `NOTES` of each held row and
`reference_series.manifest.json` state the current ones. Results therefore
represent provisional part-year 2026 price levels, not established full-calendar-2026 USD. Partial-year source notes
are propagated to every affected result. Seasonal and timing bias against
complete annual means is not quantified. A refreshed full-year dataset is needed
before interpreting these as final 2026 comparisons.

## Trace, regeneration and validation

`INDEX_USED` encodes components, weights, joining years and interval endpoints.
`INDEX_TRACE` is compact JSON containing evaluated endpoints, held/interpolated/
extrapolated methods, source-resolvable annual anchors, and any interpolated
intervening UCCI coverage years. Source titles, URLs, access dates and notes are
retained; original quotes resolve through the pinned held index CSV.
`ESCALATION_METHOD` versions the calculation policy. PROJECTS_SHA256,
TIMESERIES_SHA256 and STATEMENT_YEARS_SHA256 identify the inputs using SHA-256 over
UTF-8 text with CRLF/CR normalized to LF (`INPUT_DIGEST_BASIS=sha256_utf8_lf`).
These are text-normalized digests, not raw-byte fingerprints. Inputs are checked
again before results are returned. Nominal input files are never rewritten.

The module validates on read through existing project/index schemas, then rejects
uncited, nonpositive/nonfinite, non-nominal, incompatible-region or incompatible-
unit index anchors. The held projects table has no per-row CURRENCY/PRICE_BASIS
columns: its nominal USD interpretation rests on the named `*_USD_MM` columns,
not an independent verification of each currency label. Optional explicit
CURRENCY/PRICE_BASIS fields are validated. A disputed held label is restated as
held with its caveat, not resolved. Valued projects require a cost basis, source
provenance and a usable year. The output cannot overwrite any input, including
through a resolved link or hardlink. All rows are validated before output opens.
CSV bytes are written to a temporary sibling and atomically replaced after the
write succeeds; a failed write preserves the previous result and removes the
temporary file. Validation/I/O errors from the module CLI exit 2 with a concise
stderr message.
Output is UTF-8 LF CSV in input project order, with round-trip float strings and
sorted compact JSON, without generated timestamps. No reporting rounding is
applied to machine-readable values.

The derived row key is `(PROJECT, NOMINAL_COST_COLUMN)` for this one-row-per-
project input snapshot. Joining or summing solely by PROJECT will double-count
sanctioned and actual/revised labels. Existing typed source readers still read
their specifically named input files. The workbook reconciliation's CSV glob is
used only for byte fingerprints; evidence is loaded by explicitly named tables.

From the repository root with its namespace members installed:

```bash
python -m worldenergydata.cost.escalation \
  --output data/modules/cost/curated/sanctioned_projects_2026.csv
```

An input named `sanctioned_projects.csv` automatically selects an existing year
sidecar beside its resolved input path, independent of the working directory.
For future staging tables, pass `--projects`, `--indices` and optionally
`--statement-years` explicitly, using the existing sanctioned-project schema.
Omitting a sidecar for a custom table uses its explicit year columns or labeled
FID fallback. Run the command after refreshing held indices; the derived view
is not refreshed by a live fetch during calculation.
