# Texas operator opportunity screen

The local build target rolls an explicitly normalized public snapshot into an
operator registry, an explainable oil-production screen and self-contained HTML
reports. Lease production stays at lease grain. The screen describes statistical
candidacy; it supplies no recoverable volumes or predicted uplift. Synthetic
fixtures demonstrate the method, not a real operator's opportunity.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-20 | Add registry, descriptive screen and HTML build target with explicit evidence gaps. |

## Scope of the three slices

1. Registry: normalize diagnostic name variants, retain operator numbers, count
   inventory wells, sum production once, report coverage and export Parquet,
   CSV and JSON with a digest manifest.
2. Screen: compare like-grain reporting units to other operators' peers, describe
   endpoint decline, variability and inactive units with prior oil production.
   Every candidate retains contributing signals and their numeric evidence.
3. Report: generate an escaped HTML summary for any registry operator, including
   a peer chart, source vintage, mandatory limits and a golden-file test.

PDF rendering, a measured single-page overflow check, calibrated validation on
publicly documented reworks, pressure-table integration, depth-matched peers,
Indiana ingestion and the shared fetcher remain later slices. Their checks are
`NOT_EVALUATED`. None is represented as completed by this implementation.

## Production grain and identity

The [RRC PDQ Dump Manual](https://www.rrc.texas.gov/media/50ypu2cg/pdq-dump-user-manual.pdf),
current public edition accessed 2026-10-20, identifies `OG_LEASE_CYCLE` as
production reported by lease and month (table descriptions, printed page 5;
columns, pages 12–13). It separately defines `OG_WELL_COMPLETION` as completion
identity. A completion/API join does not create per-well production.

`normalize_pdq_rows()` accepts records from the existing PDQ member reader's
`OG_LEASE_CYCLE_DATA_TABLE.dsv` output. It preserves string identifiers,
`DISTRICT_NO`, `OIL_GAS_CODE`, `LEASE_NO`, `OPERATOR_NO` and `CYCLE_YEAR_MONTH`.
It reads oil from `LEASE_OIL_PROD_VOL` and adds gas-well and casinghead gas
(`LEASE_GAS_PROD_VOL` + `LEASE_CSGD_PROD_VOL`, Mcf; manual field descriptions,
printed pages 34 and 35). Oil excludes condensate. Missing numeric volumes are
rejected rather than converted to zero. Unfiled reports are omitted, leaving
unknown months. This table supplies no water volume.

The reporting-unit key is district + fluid code + lease number. Oil leases can
contain multiple wells; gas reporting IDs still require a verified completion
mapping before any API-level claim. Raw PDQ records remain `lease` grain even
when an ID happens to resolve to one completion. An independently verified
well-level source can explicitly supply `granularity: well` and an API.

The manifest reports input rows by grain. The synthetic example has six lease
rows and no well rows. The actual Texas statewide well/lease split is
`NOT_EVALUATED`: the bulk snapshot is not part of this checkout. No statewide
coverage count is inferred from the fixture.

Names are uppercase, punctuation-normalized, with `&` expanded to `AND` and
terminal `INC`, `LLC`, `CO`, `CORP`, `LTD` removed for collision diagnostics.
Names within one operator number form a variant list; different numbers are
never merged automatically. Collision counts count other IDs sharing any
normalized name. Transfers require a dated inventory join; a production row
whose operator differs from the supplied inventory is rejected. Operator of
record denotes the filing entity and does not establish working interest.

## Input and build contract

The committed [synthetic bundle](../../../../tests/unit/texas_rrc/fixtures/operator_screen.json)
is a complete input example. Supply:

- `source`: dataset description, public HTTPS URL, snapshot date and inventory
  date in ISO date form. The snapshot must not predate the analysis month.
- `wells`: unique API, operator number/name, district, county, fluid code,
  lease number, normalized status and optional field number/completion year.
  Status is `producing`, `inactive`, `plugged` or `unknown`. Completion year is
  an integer or null. All identifiers remain strings, preserving leading zeros.
- `production`: operator number, reporting-unit key, `YYYY-MM`, explicit grain,
  oil bbl, gas Mcf and optional water bbl. Well grain also requires the API.
- `policy`: every field of `Policy`; all are required caller choices. No field
  is a default engineering acceptance limit. The values in the fixture are
  chosen solely to expose the independently calculated test cases below.

The inventory is an explicitly dated snapshot, not an ownership history.
Normalize wellbore/completion records and resolve repeated APIs upstream.
The adapter handles production columns; automatic wellbore parsing and transfer
reconstruction are not included. The inventory date must fall in the analysis month and must not postdate the
source snapshot. Future production rows do not contribute to the screen.

For an installed package with its existing PyArrow dependency:

```bash
python -m worldenergydata.texas_rrc.operator_screen \
  --input normalized.json --as-of 2025-02 --output "$OUTPUT_DIR"

make onepager INPUT=normalized.json AS_OF=2025-02 \
  OUTPUT="$OUTPUT_DIR" OPERATOR=000001
```

`--operator` limits HTML generation; the full registry/rankings are still written.
`--config policy.yml` overrides the bundle policy with a YAML `operator_screen`
section. The template in `config/texas_rrc.yml` contains nulls intentionally:
fill all fields before use. Results record the effective policy. Generated
outputs belong outside the repository. A rebuild replaces matching artifacts;
use a distinct output directory per snapshot to avoid retaining older reports.

The module does no network access. Existing PDQ download and member-reading
code remains the ingestion surface. Duplicate unit/month rows, mixed well and
lease grain, negative or nonfinite volumes and ambiguous operator joins fail
validation. No snapshot wins merely by arriving last.

## Methods and required decisions

All comparisons use unrounded values. Displayed numbers use one decimal place.
A full window requires every calendar month. A missing month is unknown, not a
shut-in. Window totals remain unknown if any inventory well lacks complete
unit coverage. First/last production dates are the first/last **observed**
positive months in the supplied history, not original production dates.

| Method | Definition and source | Required decisions |
| --- | --- | --- |
| M1: rate and deficit | Calendar-day rate `q = monthly oil / days in that calendar month`; `deficit = max(0, median_peer - q) / median_peer`. Local descriptive definitions using the RRC monthly volume basis and [NIST e-Handbook §1.3.5.1](https://www.itl.nist.gov/div898/handbook/eda/section3/eda351.htm), current online edition accessed 2026, for the median. Zero peer medians give an unevaluated deficit. | `deficit_fraction`, `min_peers` |
| M2: endpoint change | `(first_rate - last_rate) / first_rate`, then subtract the peer median change. Local descriptive difference, not an Arps fit or reservoir model. Nonpositive initial rates give an unevaluated change. | `decline_excess_fraction`, `window_months` |
| M3: variability | Population standard deviation of calendar-day rates divided by their mean. [NIST Dataplot, Coefficient of Variation](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/coefvari.htm), current online edition accessed 2026, defines the SD/mean ratio; this implementation deliberately uses the entire observed window's population SD rather than its sample estimator. Zero mean is unevaluated; a near-zero mean can destabilize the ratio. | `erratic_cv` |
| M4: water cut | `water / (oil + water)`, a local volumetric definition on matching reported volumes. Any missing water or nonpositive denominator gives an unevaluated result. | Matching water evidence required |
| M5: concentration | Sum of squared **well-count fractions** by district/field. [DOJ, HHI definition, updated 2024](https://www.justice.gov/atr/herfindahl-hirschman-index). Uses fractions, not percentage shares; no antitrust cutoff is transferred to engineering. Unknown field IDs give an unevaluated result. | No acceptance threshold applied |
| M6: idle evidence | Inventory inactive, current reported oil zero, and an earlier positive oil record. Prior calendar-day rate and calendar months since the last positive month are retained. Local descriptive definition; elapsed reporting months are not measured downtime. | Full window required |

Peers match district, field, fluid, grain, inventory well count and a completion
vintage bucket starting at `floor(year / vintage_years) * vintage_years`.
All members of a lease must share one known vintage bucket and field. The subject
operator is excluded. Each external unit gets one observation; multiple units
from the same external operator can influence the median. Missing completion
age or insufficient peers prevents a peer comparison. Depth and completion
technology remain unadjusted confounders. Equal lease well count does not imply
equal productive capacity.

Signals trigger strictly above their supplied limits. Ranking sorts by the
unweighted number of supported signals, then operator ID and unit ID for stable
ties. Operator evidence counts sum unit counts, so larger inventories can rank
higher; this is an explicit prioritization convention, not calibrated upside.

Size eligibility uses caller-supplied inclusive `min_wells`/`max_wells`.
Stripper share is the fraction of inventory wells with a **verified well-level**
latest-month oil rate `0 < q <= stripper_bopd`; all wells must have a known rate.
It is a latest-month screening proxy, not a regulatory classification. Zero-rate
wells are not counted as stripper producers. `min_stripper_share` is also a caller
choice. Lease-only inventories have `selection_status: NOT_EVALUATED` inside
the size band; they remain in the provisional ranked list with that visible gap.
Gas production is aggregated, but gas-unit oil signals and gas stripper
classification are not evaluated. Concentration is reported as context, not an
additional weighted signal.

## Worked example and sensitivity

The fixture describes three synthetic operators, each with one two-well oil
lease in the same field/vintage group. Monthly volumes and calendar-day rates
are calculated independently in the test module docstring:

| Synthetic ID | January bbl / days | February bbl / days | Window oil bbl |
| --- | --- | --- | --- |
| 000001 | 62 / 31 = 2.0 | 28 / 28 = 1.0 | 90.0 |
| 000002 | 248 / 31 = 8.0 | 224 / 28 = 8.0 | 472.0 |
| 000003 | 62 / 31 = 2.0 | 0 / 28 = 0.0 | 62.0 |

For 000001, the other operators' February median is `(8 + 0) / 2 = 4.0`
bbl/day per lease. Its deficit is `(4 - 1) / 4 = 3/4`, or 75.0 %. This is a
comparison of reported lease rates; the difference is not recoverable oil.
For 000003, endpoint decline is 1.0, versus peer median `(0.5 + 0) / 2 = 1/4`;
excess decline is 3/4. Its rate CV is 1.0. With the fixture policy it ranks
first with four signals, followed by 000001 with one, then 000002 with zero.
Stripper share remains unknown for all three because the production is lease
level. The HTML golden fixture records that gap explicitly.

Increasing `min_peers` from two to three removes all peer comparisons while
retaining independent idle/variability evidence. A separate sensitivity test
moves the third operator's completion year to 2001: five-year buckets retain
three peer-eligible units; one-year buckets retain none. These are synthetic
sensitivity demonstrations, not field validation. The manifest states the
peer definition, policy and eligible-unit count for comparisons between runs.

A separate verified-well fixture supplies two 1.0 bbl/day wells for the first
operator: both pass the supplied 2.0 bbl/day threshold, giving stripper share
`2 / 2 = 1.0`. Another test supplies matching water/oil totals of 90.0 bbl each,
giving water cut `90 / 180 = 0.5`; splitting two wells between two fields gives
fraction HHI `(1/2)^2 + (1/2)^2 = 0.5`.

## Multi-state expansion decision

Reuse the repository's [state database catalogue](../state-well-databases/source-catalog.md)
(survey dated 2026-07-02) as reconnaissance, not a fresh bulk-access approval.
It records lease-level bulk production in Kansas and well/completion bulk
production routes in Colorado, New Mexico, Utah and Pennsylvania. Kansas is a
candidate for another lease-grain adapter; a well-grain adapter must verify its
actual identifiers, volume basis, terms and vintage before reuse. Indiana's
operator enumeration and lease-production constraint remain separate work under
#1129; its bulk-access terms have not been verified here. No new state fetch,
throughput claim or reachability test is included. The shared fetcher in #1130
is deferred until those source permissions and limits are recorded.

## Verification and limits

Focused tests cover independent arithmetic, calendar/leap handling, provenance,
name collisions, duplicate/transfer/mixed-grain rejection, missing production,
zero denominators, gas exclusion, sensitivity, HTML escaping, golden output,
Parquet round-trip, repeatable writes, CLI policy overrides and the Make target.
Ruff checks the touched Python files. The full repository suite is not claimed.

No public rework outcome dataset was supplied, so recovery of known cases and
false-positive rate are `NOT_EVALUATED`. Public rate histories cannot distinguish
a reservoir limitation from a mechanical failure. The error budget is not
quantified; reporting revisions, downtime, lease composition and incomplete
inventories can alter each inference. Raw bulk data was not available for a
statewide run. The implementation is in-memory and its statewide performance
has not been measured. The HTML report cannot suppress these limits or its
source date; it does not promise a single-page PDF.
