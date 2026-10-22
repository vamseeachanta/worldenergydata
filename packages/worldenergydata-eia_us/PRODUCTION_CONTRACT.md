# Production units, missingness and calendar aggregation

Monthly inputs normalize to an explicit rate or period-volume schema. An absent
number remains missing. An annual volume is reported only when every calendar
month for that component is present and numeric; a separate subtotal describes
what was reported. These are arithmetic contracts, not source qualification.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-22 | Defined units, missingness, calendar integration and provenance to prevent silent substitutions. |

## Input and output contracts

| Input | Declared unit and basis | Output |
| --- | --- | --- |
| State `value` | Required `unit`; optional `basis` must agree | Monthly `crude_bbl`, `unit=bbl`, `basis=volume_per_period`, `value_missing`, original `input_unit` and `input_basis` |
| Alaska `crude_bopd`, `ngl_bopd` | Field suffix declares barrels/day, `rate_per_day` | Same rates, per-field missing flags, `unit=bopd`, `basis=rate_per_day` |
| DPR `new_well_ip_bopd`, `legacy_decline_bopd`, `total_production_bopd` | Field suffix declares barrels/day, `rate_per_day`; `rig_count` is a count | Same rates/count, per-field missing flags; per-column unit/basis in `attrs["measurements"]` |
| Country `production_kbd` | Field suffix declares thousand barrels/day, `rate_per_day`; `year` identifies the averaging year | Same rate, missing flag, `unit=kbd`, basis, source, revision and engineering status |

Generic state values cannot inherit a unit from a series identifier. Supported
exact spellings are `Barrels`/`bbl`, `Thousand Barrels`/`kbbl`, `Barrels per
Day`/`bbl/day`/`bopd`, and `Thousand Barrels per Day`/`kbd`. Ambiguous `Mbbl`,
unknown units and absent generic units raise `ValueError`, including for missing
values. A unit or basis supplied alongside a named rate field must agree with
that field's declared scale and basis. No generic rate is interpreted as a period
volume. DPR legacy change may be signed; unsigned production/count inputs must
be nonnegative. Malformed and infinite numbers fail; `None`, numeric NaN and
nullable scalars represent missing values. Neither negative clamping nor
missing-to-zero filling is performed.

Monthly periods must be exact `YYYY-MM` calendar values; invalid months raise
`ValueError` instead of disappearing. Duplicate entity/year/month rows raise
when aggregating. Empty inputs produce the documented empty output schema.

## Method and sources

For scale factor `s`, monthly average daily rate `q`, period volume `v`, and
Gregorian month duration `d`:

- Rate input: `monthly_bbl = s * q * d`.
- Period-volume input: `monthly_bbl = s * v`.
- Complete annual volume: `annual_bbl = sum(monthly_bbl)` over January–December.
- Missing row or missing component: annual volume is NaN, `status=MISSING`;
  `reported_<component>_bbl` sums reported months only, and
  `<component>_missing_months` lists absent/null months. If nothing is reported,
  the subtotal is also NaN. Complete annual rows have `status=COMPLETE`.

The rate equation is derived from the definition of a monthly average daily
rate: average rate is period volume divided by elapsed calendar days. It uses
the quantity-equation approach of [NIST SP 811 (2008), section 7.11](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf).
The same source's section 4, Table 5 defines kilo as 1000; identity conversions
have factor one by definition. No barrel-to-SI-volume conversion is performed.
Gregorian durations and century/leap rules use [Python calendar documentation
(2026), `monthrange` and `isleap`](https://docs.python.org/3/library/calendar.html).
All sources were opened on 2026-10-22. These sources establish unit/calendar
arithmetic; they supply no production estimate or engineering acceptance limit.

State `annual_total` returns `crude_bbl`, with reported subtotal, missing-month
list and status. Alaska `annual_total` returns `crude_bbl` and `ngl_bbl`, each
with its own subtotal and missing-month list. This replaces the old sum of rates
under `*_bopd` names. Callers must migrate to the volume names. Aggregation does
not mutate its input, interpolate, extrapolate or invent entity/year rows with
no observations. A zero year is complete only if all months were reported zero.

## Worked example: mixed units and an absent month

All values and the year below are selected synthetic inputs. The expected answer
is independently calculated here and in `test_mixed_units_missing_month_worked_example`.

| Month in 2024 | Input value | Unit | Days | Reported monthly bbl |
| --- | --- | --- | --- | --- |
| January | 100 | Barrels per Day | 31 | 3100 |
| February | 2 | Thousand Barrels | 29 | 2000 |
| March | 1 | Thousand Barrels per Day | 31 | 31000 |
| April | 0 | Barrels | 30 | 0 |
| May | absent row | unknown | 31 | missing |
| June | 10 | Barrels | 30 | 10 |
| July | 10 | Barrels | 31 | 10 |
| August | 10 | Barrels | 31 | 10 |
| September | 10 | Barrels | 30 | 10 |
| October | 10 | Barrels | 31 | 10 |
| November | 10 | Barrels | 30 | 10 |
| December | 10 | Barrels | 31 | 10 |

Hand calculation: `100*31 + 2*1000 + 1*1000*31 + 0 + 7*10 = 36170 bbl`.
The annual volume is **unknown**, the reported subtotal is **36170 bbl**, and
`crude_missing_months=(5,)`. The missing row has no input unit because no input
exists; an explicit May row still requires its unit even if its value is null.

Independent constant-rate cases use 100 bbl/day in every month: seven months
of 31 days plus four of 30 plus February give `217+120+28=365` days in 2023 and
`217+120+29=366` in 2024, hence **36500 bbl** and **36600 bbl** respectively.
The tests also cover common century 2100 and leap century 2000. No tolerance is
needed for these exact synthetic arithmetic cases.

## Provenance and limits

The historical built-in country table contains unqualified estimates. Every row
is labelled `source=synthetic`, `source_revision=None`, and
`engineering_status=NOT_EVALUATED`. Filtering and ranking preserve those fields
and select an actual row rather than discarding its provenance during grouping.
DPR measurement metadata lives in DataFrame attributes so its numeric columns
remain compatible with direct DPR consumers; formats such as CSV need a separate
schema when serialized. Caller-supplied source revisions survive normalization but do not automatically
qualify engineering use. No built-in estimate has a revision-qualified source.

The weekly API client already sorts by `(period, series)` and advances offset
by the number of records received. Existing tied-boundary and short-page tests
are reused; a combined case checks several short pages with tied periods for
both feeds. Protocol source: [EIA APIv2 documentation (accessed 2026-10-22),
Sort Results and length/offset](https://www.eia.gov/opendata/documentation.php#SortResults).
Offset paging assumes the remote dataset does not change between requests.

Crosscheck arithmetic and synthetic adapter provenance are complementary tests
in the related work, not evidence of live-source validation here. Source-refresh
qualification remains separate. DPR summaries propagate missing rate components;
no new DPR annual aggregation or country annual-volume API is introduced.

## Executable example

This repeats the table's synthetic inputs and checks the independently derived
subtotal, missing-month list and missing total.

```pycon
>>> from worldenergydata.eia_us.production.state_production import StateProductionLoader
>>> loader = StateProductionLoader()
>>> rows = [{"period": "2024-01", "value": 100, "unit": "Barrels per Day"},
...         {"period": "2024-02", "value": 2, "unit": "Thousand Barrels"},
...         {"period": "2024-03", "value": 1, "unit": "Thousand Barrels per Day"},
...         {"period": "2024-04", "value": 0, "unit": "Barrels"}]
>>> rows += [{"period": f"2024-{m:02d}", "value": 10, "unit": "Barrels"} for m in range(6, 13)]
>>> annual = loader.annual_total(loader.load(rows, "TX"))
>>> float(annual.loc[0, "reported_crude_bbl"])
36170.0
>>> annual.loc[0, "crude_missing_months"]
(5,)
>>> annual.loc[0, "status"]
'MISSING'
>>> import math
>>> math.isnan(annual.loc[0, "crude_bbl"])
True

```
