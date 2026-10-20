# Per-field well P&A screen

The screen counts temporarily abandoned (TA) and completed (COM) API12
boreholes on registered bottom leases. It optionally computes an undiscounted
cost scenario from supplied prices. Without both prices and their basis,
cost is `NOT_EVALUATED`. Counts do not establish independent well numbers,
ownership, outstanding obligations or geological targeting.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| A | 2026-10-20 | Connect the existing bottom-lease attribution to field screens; require explicit prices to avoid unsupported liability estimates. |

## Inputs and method

The existing `worldenergydata.bsee.borehole_status` loader validates API12 rows
and joins `Bottom Lease Number` through `FieldsRegistry.by_lease`. Surface
lease is never a fallback. Unmatched leases remain outside field totals with
explicit reasons. The screen consumes the committed
`data/modules/bsee/borehole_status/summary.json`; it neither downloads a new
snapshot nor changes the canonical registry.

For a field, let `n_TA` and `n_COM` be its borehole status counts. The candidate
count is `n_TA + n_COM`. The optional cost is:

```text
C_USD = n_TA * c_TA_USD_per_borehole + n_COM * c_COM_USD_per_borehole
```

This is additive variable-cost accounting: OpenStax, *Principles of Accounting,
Volume 2: Managerial Accounting* (2019), section 2.2, Variable Costs, relates
total variable costs to activity units at a constant per-unit cost. Summing
the two status groups gives the scoped scenario above, consistent with the repository's
`decommissioning/cost_model.py::total_cost_musd`; no empirical coefficient,
discount rate, contingency, inflation factor or acceptance threshold is used.
Both unit prices are required inputs, including when one count is zero.
Each field's basis must include `source` and `price_basis` describing price
date, currency basis and scope. The implementation checks that these are
nonblank; it does not authenticate the supplied source or its applicability.
Use only a qualified borehole-based basis; a cost per independent well cannot
be applied to sidetracks without reconciliation.

Costs use decimal arithmetic and JSON decimal strings in USD, preserving the
input precision. Negative, nonfinite or nonnumeric prices and inconsistent
counts are rejected. Partial prices or missing provenance return
`NOT_EVALUATED`, never a partial sum. Empty fields and fields with no TA/COM
boreholes retain a null cost. Other statuses, including PA, ST, unknown and
missing statuses, remain explicit and are excluded from the scenario.

## Worked example

Run `examples/bsee/well_pa_screen.py` with the package environment. Its inputs
are synthetic: two TA, three COM and one PA borehole on a registered bottom
lease, plus one unmatched borehole. The hypothetical prices are 10 USD per TA
borehole and 20 USD per COM borehole. These are arithmetic inputs, not field
estimates or published engineering costs.

The independent calculation is `2 + 3 = 5` candidate boreholes and
`2 * 10 + 3 * 20 = 80 USD`. The PA row and unmatched row contribute nothing
to this scoped scenario. Source rows reconcile as `6 + 1 = 7`. Removing the
prices gives the same counts with cost `NOT_EVALUATED`.

## Consumer contract

`build_well_pa_signals(snapshot, cost_inputs=None)` returns a dictionary keyed
by canonical field id. Each signal retains TA/COM counts, other status counts,
registered leases, availability, cost status and reason, source retrieval time,
source and registry digests, and global unmatched counts. Zero observed
boreholes on registered leases is a coverage condition, not zero liability.
The source date is displayed: this snapshot is not a current-status query.
Its recorded registry digest describes the attribution used at extraction,
not a claim that today's registry has identical coverage.

The lifecycle generator accepts optional `--well-pa-costs prices.json`, where
the JSON is keyed by canonical field id and follows this synthetic example:

```json
{
  "sample_field": {
    "unit_cost_usd": {"TA": "10", "COM": "20"},
    "source": "Hypothetical worked example above; not a field estimate",
    "price_basis": "Hypothetical constant USD; arithmetic only"
  }
}
```

Use actual registry ids with actual evidence for a real build. Unknown cost
field ids fail instead of silently discarding inputs. No default field prices
are committed. The generator embeds identical risk objects in posters,
`_explorer.json` and `_risk.json`. The Explorer reads the existing
`_explorer.json` contract; it does not perform a second join. Both views show
the source date, cost limitation and BSEE status-definition link. A missing
snapshot gives no count badge. Facility removal remains a separate signal.

The offline regression tests count the committed `attributed.json` API12 rows
independently and compare those counts with the consumer payloads. Arithmetic
tests show their expected calculations in docstrings.

## Sources and limits

- [OpenStax: Identify and Apply Basic Cost Behavior Patterns](https://openstax.org/books/principles-managerial-accounting/pages/2-2-identify-and-apply-basic-cost-behavior-patterns),
  *Principles of Accounting, Volume 2: Managerial Accounting* (2019), section
  2.2, Variable Costs, retrieved 2026-10-20 (HTTP 200). This supports only
  the additive quantity-times-unit-cost method; it supplies no P&A unit price.
- [BSEE Data Center: Borehole Status Code enumeration](https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields),
  retrieved 2026-10-20 (HTTP 200): COM means completed, TA means temporarily
  abandoned, PA means permanently abandoned. These are status definitions,
  not a cost schedule or legal test of outstanding work.
- The committed `borehole_status/source_manifest.json`, `schema.json` and
  `summary.json` record the dated source, status definitions and count basis.
  The snapshot contains 266 attributed boreholes, including 61 COM and eight
  TA across 11 registry fields. These observed counts come from that snapshot;
  the posters cover the subset with lifecycle facts.
- Costs require qualified field-specific inputs. Independent-well identity,
  current ownership, lease-ingest reconciliation, remaining work and risk
  severity need additional evidence. No monetary liability or severity is
  inferred from status alone.
