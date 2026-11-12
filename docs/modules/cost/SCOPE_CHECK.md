# Scope cost cross-check

The scope check returns alternative project CAPEX ranges from a supplied unit-cost
benchmark table. The result retains comparable project identifiers, grouping keys,
sample counts, currency basis and the limits of the escalation evidence. This is
a screening calculation; scope equivalence and a calibrated prediction interval
are not established by matching these groups.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-11-12 | Introduce explicit per-metric screening ranges and JSON interfaces without adding overlapping CAPEX estimates. |
| 1 | 2026-11-12 | Compare equally close groups together and reject unusable tables, missing quantities and unrecognised labels so input defects cannot appear as missing comparables. |

## Python and command line

```python
from worldenergydata.cost.scope_check import check_scope

result = check_scope(scope, "reports/cost/unit_cost_benchmarks.csv")
```

```sh
worldenergydata cost-check examples/cost_check_invented_scope.json \
  --benchmarks reports/cost/unit_cost_benchmarks.csv
```

Both arguments are local files. The table defaults to
`reports/cost/unit_cost_benchmarks.csv`, relative to the current working directory.
A missing table produces an explicit error; invented fixture values are never
substituted. The CLI writes JSON and exits nonzero on invalid input or an absent
table. A header-only table or a table without a row with `n >= 1` is invalid.
A scope requires at least one positive `wells`, `trees`, `surf_km`,
`peak_production_kboed` or `recoverable_resource_boe` quantity; unsupported-only
and all-zero quantities are rejected. A valid scope without close comparables
produces `range: null` and
`reason: "no close comparables"` with a successful exit.

`examples/cost_check_invented_scope.json` contains an **invented** scope and quote,
not a bid or an engineering reference. All test benchmark prices and identifiers
are invented. The demonstration requires a supplied benchmark table; this change
does not produce or publish benchmark prices.

Input: [scope_check_input.schema.json](scope_check_input.schema.json).
Success output: [scope_check_output.schema.json](scope_check_output.schema.json).
Errors contain an `error` string, defined by the output schema's `$defs/error`.
The Python API raises `ValueError` for invalid data and `FileNotFoundError` for an
absent table. Its result is a JSON-serializable dictionary.

## Matching and fallback

Water-depth band and host type are mandatory and never relaxed. Depths in metres
map to `shallow` through 300, `mid` above 300 through 1000, `deep` above 1000 through
2000, and `ultra_deep` above 2000. A supplied depth band and depth must agree.
These bands follow the table convention in
`data_collection.calibration_schema.WaterDepthBand`; each shared boundary belongs
to the shallower band here. Labels are matched exactly after surrounding
whitespace is removed. The supplied table defines the case-sensitive region,
development-type and host labels. A host label must occur in a usable table row;
an unrecognised spelling is an input error. The producer's `unknown` placeholder
is rejected, case-insensitively, in scope grouping keys. Omit an unknown optional
scope key instead. Table rows carrying that placeholder in any grouping key are
excluded from matching and the host vocabulary. A sampled excluded row is counted
in the output limitations and makes the result indicative; a table without any
remaining usable row is rejected. Usable table depth bands must use the four
labels above.
Static schema validation does not establish membership in a supplied table's
host vocabulary; runtime validation performs that check after loading the table.

For each metric with a positive supplied quantity, an exact group is tried first.
Fallback considers both one-key relaxations together, then dropping both keys.
Omitted optional group keys are also listed as dropped. At each stage all
distinct matching rows across its relaxations are considered together. The
nearest nonempty stage is used only if it contains exactly one row with
`n >= 1`. Multiple rows are ambiguous even when one relaxation has a singleton
and another has several matches. A wider stage cannot resolve that tie. The
limitation names the group count and the total omitted plus relaxed key count;
`range: null` retains `reason: "no close comparables"` when no metric is usable.
The result will not pick an arbitrary row or pool their summary percentiles.
Each selected row's actual keys and `dropped_keys` are returned under
`matched_group[metric]`.
A different region's row can therefore serve only as an explicitly flagged
proxy. Dropped keys make the output indicative, regardless of sample size.

Every range includes its own comparables; the top-level `comparables` is their
sorted union. A row must name exactly `n` unique project identifiers. Duplicate
metric/group rows, unsupported units, invalid sample counts and non-finite or
unordered percentiles are rejected for rows with samples. Zero-sample rows do
not qualify for matching or establish the host vocabulary. Fewer than five
comparables makes a result indicative even if the input flag disagrees.
Unsupported or unmatched positive
scope quantities are listed in `unbenchmarked_elements` and also make a result
indicative.

## Method, quantities and quote position

| Metric | Scope quantity | Permitted denominator |
| --- | --- | --- |
| `capex_per_well` | `wells` | `well` |
| `capex_per_tree` | `trees` | `tree` |
| `capex_per_surf_km` | `surf_km` | `km` |
| `capex_per_kboed` | `peak_production_kboed` | `kboe/d` |
| `capex_per_boe` | `recoverable_resource_boe` | `boe` |

Table 1. Each quantity scales a whole-project CAPEX intensity independently.

For a fixed positive quantity, each supplied intensity percentile is multiplied
by that quantity. This monotone scaling preserves the supplied percentile order.
`USD_MM_2026/...` and `USD_MM/...` are multiplied by one million; `USD_2026/...`
and `USD/...` are already dollars. Output ranges always use `unit: "USD"` and
retain `benchmark_unit`, quantity, `n` and comparables beside P10/P50/P90.

These metrics each divide whole-project CAPEX by a different denominator. Their
scope-scaled results are **alternative project estimates**, not costs of distinct
elements. They overlap and are never summed. No total-scope distribution,
dependence model or calibrated scope adjustment is supplied. Tree intensities
do not establish procurement-only tree prices, and SURF intensities do not
establish a stand-alone SURF package price. A component-only quote cannot be
compared with these project estimates without an independently established
scope reconciliation.

A `quote` is a nonnegative whole-project CAPEX amount in USD. It is compared
separately against each alternative metric range. Equality at P10 belongs to
`p10-p50`, equality at P50 belongs to `p50-p90`, and equality at P90 also belongs
to `p50-p90`. Strictly smaller than P10 is `below p10`; strictly greater than P90
is `above p90`. These are range buckets, not interpolated probability estimates.
When no range exists, `quote_position` is null.

## Cost and escalation basis

The table contract is:

```text
metric,unit,water_depth_band,region,development_type,host_type,n,p10,p50,p90,indicative_only,comparables,cost_basis
```

`comparables` contains semicolon-separated project identifiers. `cost_basis` is
`USD_2026` or `nominal` and is carried through without conversion. A nominal result
is **not** a 2026 USD result; its price year is unknown under this contract.
Selected metrics with mixed bases are rejected rather than combined or silently
converted. `quote_cost_basis` defaults to `USD_2026`; a quote is rejected if its
declared basis differs from the selected table basis. Explicitly choosing
`nominal` asserts a common nominal basis for comparison; a common price year
cannot be independently checked from this table.

`escalation_basis` always states that no conversion was applied. The contract
does not supply the upstream escalation index, factor, vintage or observation
dates. These details cannot be reconstructed from `USD_2026`; `index` and
`factor` remain null and that limitation is explicit even for a successful range.
The output records the SHA-256 digest of the exact table bytes, but a digest
does not establish source accuracy, freshness or engineering qualification.

Manifolds, umbilicals and risers have no standalone metric in this table. Award
and FID years are accepted as context but are not matching keys. No extrapolation
across depth or host type, currency conversion, cost-index lookup, statistical
pooling or replacement of missing cost values is performed.

## Local HTTP endpoint

The endpoint follows the Flask `route` / `request` / `jsonify` pattern in
`packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/api.py`.
Flask and Werkzeug must already be available in the dashboard environment; no
dependency is added to the core cost package. The Python calculation and CLI do
not import Flask. This is a local development interface, with no deployment or
authentication service supplied.

```sh
python -m worldenergydata.cost.scope_check_http \
  --benchmarks reports/cost/unit_cost_benchmarks.csv --port 8080
curl -H 'Content-Type: application/json' \
  --data-binary @examples/cost_check_invented_scope.json \
  http://127.0.0.1:8080/api/cost-check
```

The launcher binds to `127.0.0.1` with debug disabled. `POST /api/cost-check`
accepts the scope object directly and returns the same result as Python. Invalid
JSON or scope/table data returns 400; a non-JSON content type returns 415; a
request larger than 65,536 bytes returns 413. An absent or unreadable table
returns 503. Errors contain JSON without local filesystem paths. Applications
can create the Flask app with `create_app(benchmark_path)`; tests use a real HTTP
round trip on an ephemeral loopback port.
