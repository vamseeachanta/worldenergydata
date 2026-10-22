# worldenergydata-brazil_anp

`brazil_anp` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.brazil_anp` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Illustrative concession royalty scale

`analysis.field_economics.ROYALTY_SCALE` is **illustrative**.
`ROYALTY_SCALE_IS_ILLUSTRATIVE = True` records that the five bands are not
source-qualified fiscal terms. Their values and calculated outputs are retained
for compatibility; no legal production-rate table matching these bands has been
established.

`calculate_royalties_concession` selects the first inclusive threshold and
multiplies gross revenue by its rate. Thresholds use externally supplied barrels
per day. `ConcessionRegime` describes a field context, but the interface does not
establish field aggregation, an averaging basis, a production year, or a location
class. The revenue period and currency are also supplied without qualification.

The first disagreement is the selection rule: daily production selects a rate
in this example, whereas Decreto 2.705/1998, art. 12, §§1–2 specifies a concession
percentage established in the bidding terms and contract. A percentage within
the statutory range alone does not establish a matching production band.

| Code upper threshold (barrels/day) | Code rate (%) | Official comparison | Disposition |
| --- | --- | --- | --- |
| 5,000 | 5 | 5% is the art. 12 §1 minimum; no 5,000 barrels/day threshold is specified | Differ |
| 15,000 | 7.5 | Contract percentage under art. 12 §2; no 15,000 barrels/day threshold is specified | Unconfirmed band |
| 30,000 | 10 | 10% is the art. 12 default; no 30,000 barrels/day threshold is specified | Unconfirmed band |
| 50,000 | 12.5 | Above the art. 12 default of 10%; no 50,000 barrels/day threshold is specified | Differ |
| Unbounded | 15 | Above the art. 12 default of 10%; no corresponding royalty band is specified | Differ |

Table 1. Every band is compared with the cited concession framework; a contract-specific rate is not established for this example.

Sources examined on 2026-10-12:

- Presidency of the Republic, [Lei 9.478, de 6 de agosto de 1997](https://www.planalto.gov.br/ccivil_03/leis/l9478.htm), art. 47, caput and §1: monthly royalties per field, with a 10% default and provision for reduction to a 5% minimum.
- Presidency of the Republic, [Decreto 2.705, de 3 de agosto de 1998](https://www.planalto.gov.br/ccivil_03/decreto/d2705.htm), arts. 11–12, §§1–2: monthly field production valued at reference prices and the contractual concession percentage. Art. 22, caput and §1/I, concerns special participation, with quarterly field production in thousands of cubic metres of oil equivalent, net revenue, production year and location class. That table does not qualify a daily-rate royalty scale.
- ANP, [Royalties](https://www.gov.br/anp/pt-br/assuntos/royalties-e-outras-participacoes/royalties), opening calculation factors and variable definitions: contractual field percentage multiplied by monthly field production and reference prices; oil and gas volumes are in cubic metres. The page's general 5–15% range does not provide the five production-rate bands or establish their concession case.
- ANP, [Participação especial](https://www.gov.br/anp/pt-br/assuntos/royalties-e-outras-participacoes/participacao-especial), opening calculation paragraphs: progressive rates on quarterly net revenue depend on field location, years of production and quarterly production volume.

The shipped `fdas/fiscal/decks/` resources (`norway.yml`, `uk.yml`, `us_gom.yml`)
and production builders `fdas.fiscal.schema` and `fdas.fiscal.terms` exclude this
scale. The synthetic runtime parity test in
`tests/unit/fdas/fiscal/test_deck_parity.py` checks agreement with existing code;
it does not establish regulatory qualification and does not ship a country deck.
These illustrative values shall not be copied into a fiscal deck until the
applicable contract, units, period and governing case are source-qualified.


## Ingestion integrity

The archive reader raises `ANPIngestionError` for an archive without CSV members,
an archive without production rows, a missing period column, or any invalid
period. Periods must be complete year/month strings with a valid calendar month.
Entirely blank CSV rows are layout rather than observations. The existing
sea/pre-salt overlap rule still chooses one observation for an overlapping key.
Other duplicates still raise. Rejected rows are never silently dropped.
A downloaded archive is parsed before replacing an existing cache entry.

`WellProductionLoader.load` requires nonblank textual field and well identities
in both schemas. Literal text labels remain text; missing scalars never become
text labels. Current-schema rates must be present, finite and nonnegative.
Numeric values and dot-decimal strings retain their magnitude. Decimal-comma
strings can use dot grouping, as in `"1.000,5"`. Without a comma, a dot is always
decimal: `"1.000"` means one. Callers supplying dot-only grouped integers must
normalize them explicitly before loading. This is an input convention, not a
claim that every source vintage uses the same numeric notation.

The refresh job rejects empty raw data and any normalization row-count loss
before writing either parquet snapshot or success metadata. Archive contract
failures are terminal for that attempt. Network retry behavior is retained.
This does not provide a transaction across filesystem writes: an output write
failure can leave an earlier snapshot. Source completeness beyond the received
CSV partitions is not established.

Metadata well counts require linked rows with nonblank well identities. Counts
use distinct trimmed identities, rather than well-month rows. Missing links,
missing identity columns, empty selections or incomplete identities return
`None`; they cannot establish a measured zero. Unknown production field
summaries continue to raise `ValueError`.

## Explicit participation basis

The former fixed-currency special-participation bands have been removed.
`calculate_special_participation` and `ConcessionRegime.calculate` require a
`ParticipationSchedule` and a matching revenue currency and period. A schedule
records its source and increasing upper bounds with fractional marginal rates;
the final bound must be unbounded. Missing or mismatched inputs raise, including
for zero revenue. No foreign-exchange or period conversion is inferred.
The concession royalty helper likewise rejects missing, nonfinite or negative
production rates before any revenue shortcut.

The ANP [Participação especial calculation guidance](https://www.gov.br/anp/pt-br/assuntos/royalties-e-outras-participacoes/participacao-especial),
calculation paragraphs, accessed 2026-10-21, describes quarterly net revenue and
rates dependent on location, years of production and quarterly volume, with
deductions under Lei 9.478/1997, art. 50, paragraph 1. It does not qualify the
removed fixed monetary thresholds. A caller-supplied schedule is a generic
marginal-band calculation; supplying a citation does not prove statutory
applicability. Fiscal qualification remains **NOT_EVALUATED**. The existing
illustrative royalty scale and other fiscal assumptions remain unqualified.

This is an intentional API change: callers of the participation helper must
supply `schedule=`, `currency=` and `period=`. Callers of the concession regime
must supply `participation_schedule=`, `currency=` and `period=`. The existing
concession basis `gross_revenue - opex - capex` remains a simplified basis, not a
statutory determination of deductible net revenue.

## Worked synthetic example

Summary: a supplied daily oil rate becomes a monthly volume without decimal
rescaling; a supplied marginal schedule produces an explicit monetary result.
These inputs are synthetic and provide no field-specific or statutory values.

### Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-21 | Add explicit inputs and hand calculations to demonstrate integrity checks. |

Inputs: February 2024 daily oil rate `0.5` bbl/day; net revenue `150` TEST units
per quarter; caller-supplied untaxed band through `100` TEST units, followed by
a fractional marginal rate `0.2`. Source for these magnitudes: this synthetic
hand calculation, not regulatory data. Calendar day count comes from Python's
[`calendar.monthrange`](https://docs.python.org/3/library/calendar.html#calendar.monthrange)
API; February 2024 has 29 days.

Method and answer: monthly oil is daily rate times days, `0.5 * 29 = 14.5` bbl.
The marginal-band sum is `max(0, min(revenue, upper) - lower) * rate` per band;
`100 * 0 + (150 - 100) * 0.2 = 10.0` TEST units per quarter. No conversion between
volume and revenue is asserted. The independent arithmetic appears in
`tests/unit/brazil_anp/test_ingestion_integrity.py` and
`tests/unit/brazil_anp/test_field_economics.py`.

```python
from worldenergydata.brazil_anp.analysis.field_economics import (
    ParticipationSchedule,
    calculate_special_participation,
)

schedule = ParticipationSchedule(
    currency="TEST",
    period="quarter",
    bands=((100, 0), (float("inf"), 0.2)),
    source="Synthetic hand calculation in the package README",
)
answer = calculate_special_participation(
    150, schedule=schedule, currency="TEST", period="quarter"
)
assert answer == 10
```

Later work: validate live partition inventories, qualify contractual fiscal
terms and source vintages, and address the shared empty reference-chain behavior
tracked separately in #1289. No live archive or metadata service is used by the
regression examples.
