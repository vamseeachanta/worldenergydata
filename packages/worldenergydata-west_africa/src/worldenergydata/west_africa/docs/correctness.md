# West Africa production and fiscal calculation

The corrections for #1292 establish report identity, explicit production-rate
units, a conserved fiscal cash ledger, and visible discovery/schema failures.
Offline examples establish arithmetic and error handling. Live source coverage
and legal fiscal applicability remain **NOT_EVALUATED**.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-21 | Document report validation and fiscal accounting to prevent silent misattribution and duplicate allocations. |

## Report identity and failure handling

The PDF parser supports blend tables explicitly labeled `kbd` or thousand
barrels per day, with one unambiguous full month name and year in the page
text or table header. It does not infer a rate from a monthly barrel total.
Multi-period tables, abbreviated month labels, and unsupported units raise
`NuprcAPIError`; additional layouts need source fixtures before support is added.

Total, subtotal and grand-total labels are excluded. Equal repeated rows with
the same normalized blend, year and month are retained once; different values
for that identity raise an error. Non-finite, negative or nonnumeric production
also raises an error. A parsing exception never returns partial records.

`BlendProductionLoader.load` validates its requested month before download,
including when an explicit URL is supplied. Every returned row must contain
the requested report period. Missing or conflicting periods raise an error;
request arguments cannot supply missing evidence. Constructed PDF URLs are
candidates whose existence is unverified. Download failure retains the legacy
empty-list behavior; callers requiring transport diagnostics should use
`NuprcClient.download_pdf` directly.

`list_report_urls` raises `NuprcAPIError` on missing dependencies, transport or
HTTP failure, or an index with no PDF links. Relative references resolve against
the supplied portal URI, including query strings and network-path references,
under [RFC 3986 (2005), section 5](https://www.rfc-editor.org/rfc/rfc3986#section-5).
Repeated URLs appear once.

EITI getters accept a list of record dictionaries or a dictionary containing a
`data` list of record dictionaries. An explicit empty list is valid; a missing,
null or malformed collection raises `EitiApiError` before caching. This local
shape contract does not establish live endpoint compatibility, pagination,
record units, geographic scope or completeness. The downstream production and
payment loaders retain their existing handling of API errors.

## Fiscal method and assumptions

Pass exactly one of `production_rate_bopd` or `production_rate_kbd` to either
`calculate_profit_oil_split` or `NigeriaDeepwaterPSC.calculate`. Package
production records and catalog plateaus use kbd. Conversion is
`bopd = kbd * 1000`: kilo denotes ten cubed in the
[BIPM SI Brochure, ninth edition (2019), section 3, Table 7](https://www.bipm.org/documents/20126/41483022/SI-Brochure-9.pdf).
Missing, negative, non-finite or ambiguous rate inputs are rejected. A rate with
no configured tier is rejected instead of assigning an unsupported share.

The allocation equations below are bookkeeping definitions, not tax law.
They correct the duplicate levy allocation identified in #1292. Let gross
revenue be `G`, royalty be `R`, recovery fraction be `f`, recoverable expenses
be `O + K`, government profit share be `s`, modeled tax rate be `t`, and modeled
gross-revenue levy rate be `l`:

- Cost recovery: `C = min(O + K, (G - R) * f)`.
- Profit oil: `P = G - R - C`.
- Government profit oil: `N = P * s`; contractor profit oil: `Q = P * (1 - s)`.
- Modeled tax: `T = max(Q * PPT rate, Q * CITA rate)`.
- Modeled levy: `L = G * l`.
- Contractor cash after tax and levy: `I = Q - T - L`.
- Government cash: `H = R + N + T + L`.

Substitution gives `C + I + H = G`; this independent identity is the regression
oracle. Contractor cash can be negative when the modeled levy exceeds profit
after tax. Flooring that obligation at zero would invent revenue. Cost recovery
is a separate cash allocation; contractor net income alone excludes it.

The existing royalty bands, profit-share tiers, tax coefficients, levy rate and
levy base are retained legacy assumptions, **NOT_EVALUATED** for any contract or
accounting period. No statutory applicability is claimed. Statutory qualification
requires applicable source clauses and contract terms under #919. No new fiscal
coefficient is supplied by this correction. The example below substitutes
synthetic inputs and does not qualify the legacy defaults.

## Worked example

All cash amounts are synthetic USD, with no rounding tolerance needed. Assume
gross revenue 128, expenses 16 plus 16, royalty zero, recovery ceiling one half,
government profit share one half above a synthetic lower tier, tax one quarter,
and gross levy one eighth. Production is 30 kbd, or 30,000 bopd, so the second
synthetic tier applies. These assumed inputs are chosen for exact binary
arithmetic; they are not published fiscal terms.

Hand calculation: cost recovery is `min(32, 64) = 32`; profit oil is 96;
government and contractor profit oil are each 48. Tax is 12 and levy is 16.
Contractor cash is `48 - 12 - 16 = 20`; government cash is `48 + 12 + 16 = 76`.
The allocations reconcile: `32 + 20 + 76 = 128`.

The executable example substitutes synthetic coefficients only within the
context manager; the standard library restores the legacy assumptions on exit.

```pycon
>>> from unittest.mock import patch
>>> from worldenergydata.west_africa.analysis import field_economics as fiscal
>>> terms = dict(PPT_RATE_PSC=0.25, CITA_RATE=0.0, NDDC_LEVY_RATE=0.125,
...              PROFIT_OIL_TIERS=[(20_000, 0.25), (40_000, 0.5)])
>>> with patch.multiple(fiscal, **terms):
...     result = fiscal.NigeriaDeepwaterPSC(cost_oil_ceiling=0.5).calculate(
...         128, 16, 16, production_rate_kbd=30)
>>> (result.cost_oil, result.total_government_take, result.contractor_net_income)
(32, 76.0, 20.0)
>>> result.cost_oil + result.total_government_take + result.contractor_net_income
128.0

```

The same hand calculations are tested in
`tests/unit/west_africa/test_issue_1292.py`, alongside production-table,
period, unit, URL and schema regressions. No live data or licensed publication
is required to reproduce the examples.
