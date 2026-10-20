# Texas RRC operator registry

The operator registry joins selected local production and well-inventory
snapshots at operator-of-record level. It preserves lease totals and reports
where individual-well statistics cannot be evaluated. It performs no downloads
and makes no working-interest ownership inference. No statewide coverage is
claimed until actual snapshots have been processed.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Add operator roll-up with explicit lease allocation and coverage limits. |

## Sources and production granularity

The [RRC Production Data Query System FAQ](https://www.rrc.texas.gov/about-us/faqs/oil-gas-faq/production-data-query-system-faqs/)
(accessed 2026-10-19, question on reporting production) states that production
is reported by lease. Oil leases may contain multiple wells; gas leases contain
one gas well. Therefore PDQ cannot substantiate a well-by-well oil stripper
population. Even an oil lease with one current inventory match is not allocated:
the snapshot does not prove the historical producing-well population.

The quality output reports oil-lease and gas-well row and unit counts separately,
plus the split of rows in the selected window. It also reports producing wells
without usable individual rates. Gas-well rates require exactly one inventory
match in the same operator, district, oil/gas code and lease. An ambiguous gas
lease is excluded. Oil-well rates, oil stripper share, transfer identity and
working-interest ownership remain **NOT_EVALUATED** without additional evidence.
Oil-well BOPD and stripper share remain null with `per_well_metrics_status`
**NOT_EVALUATED**, even if a stripper threshold is supplied. A threshold cannot
replace missing oil-well volume evidence. The additional
`gas_mcfd_per_well_median` describes **eligible gas wells only**;
`gas_rate_eligible_well_count` and `gas_per_well_metrics_status` expose its
coverage. Gas-well condensate is not relabelled as crude oil.

The repository's source catalog (`production_pdq`, `wellbore_query`) and
[storage contract](storage-contract.md) govern provenance and storage. The filer
in a production month is retained; production is never reassigned to a successor
using a current well snapshot. Operator of record identifies the filer and does
not establish ownership, equity, working interest or entitlement to production.

## Selected inputs and validation

Use `load_operator_inputs(production_path, wells_path)` for local CSV, DSV or
Parquet files. CSV identifiers are read as strings, preserving leading zeros.
A production ZIP must have exactly one `OG_LEASE_CYCLE_DATA_TABLE` table;
field, operator and district aggregate tables are excluded to avoid double
counting. A well ZIP must have exactly one headered inventory table. Native
headerless wellbore dumps must first be normalized using the existing lifecycle
readers and explicitly enriched with the reporting type and status mapping.
The loader accepts common PDQ aliases such as `OPERATOR_NO`, `OG_OPER_NO`,
`LEASE_NO`, `DISTRICT_NO`, `LEASE_OIL_PROD_VOL` and `CYCLE_YEAR_MONTH`.
It accepts the calendar month as `YYYY-MM` or compact `YYYYMM` in files.
Separate `CYCLE_YEAR` and `CYCLE_MONTH` columns are also supported.

| Input | Required columns | Optional columns |
| --- | --- | --- |
| Production | `operator_no`, `operator_name`, `district`, `oil_gas_code`, `lease_no`, `production_month` | `oil_bbl`, `gas_mcf`, `water_bbl`, `field_no`, `county` |
| Current well inventory | `operator_no`, `operator_name`, `district`, `oil_gas_code`, `lease_no`, `well_id`, `well_status` | `field_no`, `county` |

`oil_gas_code` must be `O` or `G`; it is never inferred from nonzero volumes.
Each `well_id` must identify one counting unit in a selected current snapshot.
If using API14, counts are completion/wellbore identities; if physical API10
wells are required, reconcile completion rows before this step. No silent
API14-to-API10 collapse is performed. Keep sidetrack/completion policy consistent
across snapshots. The exact source spelling and identifier format must agree
across the inputs; the loader does not pad or guess incomplete identifiers.

`well_status` values `producing` and `inactive` are counted explicitly;
all other values are counted in `well_count_other`. An `active` regulatory
status alone does not establish production. Translate source codes using the
appropriate source dictionary before supplying these classifications. Inactive
counts are retained even though lease production cannot identify which idle
oil well previously produced. County coverage is the union of supplied county
identifiers, not a geographic inference; absent counties produce an empty list.

`validate_operator_inputs` rejects empty join identifiers, invalid months,
negative/non-finite/malformed volumes and conflicting unit-month or well rows.
Exact duplicates collapse. Conflicting revisions require explicit snapshot
selection. A reporting unit is `(district, oil_gas_code, lease_no)`; operator
is deliberately excluded from the production uniqueness key so an unresolved
transfer in the same month cannot double count volume. The same lease number
in another district or reporting type remains separate. A blank name can be
flagged; a blank operator number cannot be joined.

Some raw lease-cycle tables lack operator or name columns. Such tables require
an explicit, dated reference-table join before loading. The loader fails rather
than attributing historical volume from a current well inventory. No automatic
transfer reconciliation or fuzzy cross-number merge is implemented.

## Name matching

Within each operator number, all observed names are retained. A candidate name
key uppercases text, converts punctuation to spaces, collapses whitespace and
removes terminal legal suffixes (`INC`, `INCORPORATED`, `LLC`, `LTD`, `LIMITED`,
`CO`, `COMPANY`, `CORP`, `CORPORATION`); dotted `L.L.C.` is recognized.
This is a deterministic matching policy, not proof of corporate continuity.
Spelling differences beyond these transformations remain an ambiguity. Different
cores under the same number flag `operator_name_ambiguous`. Shared cores across
numbers flag `operator_name_collision` and list the other numbers. Numbers stay
separate, including possible successors after transfers. The display name is
the lexically first observed variant, not an assertion of the current legal name.

Quality counts distinguish operators with name variants, ambiguous operators,
and candidate keys shared by multiple numbers. They do not report these
candidate collisions as verified corporate matches.

## Metrics and missing data

The inclusive **12 calendar month** window comes from issue #1126's output
contract. `as_of` is required; the system clock never chooses the window.
No technical coefficients or regulatory screening limits are embedded.

| Metric | Method and evidence |
| --- | --- |
| Last12 oil, gas, water | Sum observed monthly volumes attributed to each operator; issue #1126 output contract. A missing value makes that volume total null; absent rows remain a coverage gap. |
| Oil vs other liquids | Oil is crude oil, not condensate; RRC PDQ FAQ, question on crude oil and condensate. No condensate-to-oil or BOE conversion is made. |
| Gas | Supplied `gas_mcf` is total gas. Native separately reported `LEASE_CSGD_PROD_VOL` is added to gas; missing components remain unknown. |
| Calendar-day rate | Eligible gas-well window gas volume divided by actual calendar days in that window, including leap days. This is an arithmetic definition, not an operating-day rate. |
| Water cut estimate | Sum(water) / (sum(oil) + sum(water)); volume-fraction definition on the same window. Missing water or a zero denominator returns null. |
| First/last production | Earliest/latest supplied month with positive oil or gas through `as_of`; not evidence of production before the supplied history. |
| Field count | Distinct supplied `(district, field_no)` pairs in the current well inventory. Missing fields are excluded from the count and invalidate concentration. |
| Field concentration | Sum of squared fractions of inventory wells per field; [DOJ HHI definition](https://www.justice.gov/atr/herfindahl-hirschman-index), updated 2024, adapted to field well-count shares. Fractional shares are used, with no market-concentration threshold. |
| Stripper share | NOT_EVALUATED: PDQ lacks individual oil-well allocation. `stripper_bopd` reserves an explicit policy input for later allocation evidence; supplying it alone cannot evaluate this metric. |
| Size band | Current inventory count compared to caller-supplied, increasing inclusive upper bounds. Above the last bound: `ABOVE_CONFIGURED_BANDS`; absent policy/inventory: `NOT_EVALUATED`. |

`usable_last12` requires every observed reporting unit in the window to contain
all window months with known oil and gas, and every current inventory unit to
have window reports. Historical-only units outside the window do not create a
current reporting obligation. This flag measures completeness of the supplied
units; it does not prove all statewide units were supplied. Missing months are
never filled with zero. Observed partial sums remain available with
`last12_incomplete`; downstream ranking must inspect this flag. Missing well
inventory gives null well counts, not a claim of zero wells. Coverage counts
operators by size band and by district; multi-district operators appear in each
district and district counts must not be summed as a statewide total.

## Build and storage

The module has a standalone build command:

```bash
python -m worldenergydata.texas_rrc.operators \
  --production "$PRODUCTION_SNAPSHOT" --wells "$WELL_SNAPSHOT" \
  --as-of 2025-12 --output-root "$SNAPSHOT_ROOT" \
  --config config/texas_rrc.yml --code-revision "$CODE_REVISION"
```

The package must be importable, for example by including its `src` directory in
`PYTHONPATH`. Set `operator_registry.size_bands` and `stripper_bopd` in the config
when an approved screening policy exists; their defaults deliberately leave
screening unevaluated. These are analysis choices, not official RRC limits.

A fresh snapshot root receives `curated/operators/operator_registry/` with
`operator_registry.parquet`, `quality.json` and `manifest.json`. The default
storage guard requires the catalog root. `--allow-non-catalog-root` permits an
isolated example or test output root. Store heavy outputs outside Git. Existing
output directories are refused; choose a fresh snapshot root for a later run.
The manifest is written last. Without it a partial directory is not complete.
It records the policy, source IDs, input byte digests, output digests, row count,
UTC generation time and caller-supplied code revision. An absent code revision
is explicitly **NOT_EVALUATED**. Input locators use basenames, not host paths;
retain the selected input files beside their existing source manifests.

## Worked example

Run `python examples/texas_rrc/operator_registry.py --output-root "$EXAMPLE_ROOT"`
with a fresh external output root. It builds a synthetic oil lease with two
wells and a gas lease with one well. Each of the calendar months of 2025 has:

| Lease | Type | Oil, bbl | Gas, Mcf | Water, bbl | Current inventory |
| --- | --- | ---: | ---: | ---: | --- |
| L1 | Oil lease | 150 | 10 | 100 | One producing, one inactive |
| L2 | Gas lease | 0 | 20 | 150 | One producing |

Independent hand calculation: oil = `12 × (150 + 0) = 1800 bbl`, gas =
`12 × (10 + 20) = 360 Mcf`, water = `12 × (100 + 150) = 3000 bbl`.
Water fraction = `3000 / (1800 + 3000)` = **62.5 %**.
Field inventory shares are `2/3` and `1/3`; HHI = **5/9**.
The sole eligible gas well has `240 / 365` = **0.7 Mcf/calendar day**.
The two oil wells receive no allocation. Total/producing/inactive counts are
**3/2/1**. The synthetic size bounds are two and four wells, giving `medium`.
The synthetic stripper threshold is **2.0 bbl/calendar day**, but oil-well BOPD
and stripper share remain **NOT_EVALUATED** because no oil-well production
allocation is available. Gas-rate coverage is `PARTIAL`: one eligible gas well
out of two producing inventory wells. The supplied threshold and size bands
are input choices, not acceptance limits.

The fixture tests write out the same calculations independently, and cover
name collisions, missing data, duplicate revisions, ambiguous gas joins,
future months, leap years, file aliases, manifests and the command entry point.
No real operator, statewide result or technical uplift is inferred.
