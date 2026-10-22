# EIA US method overlap and synthetic adapter boundary

The package-local [enrollment proposal](implementation-map.json) inventories the
existing methods and records bounded overlap discovery. It is pending review;
engineering qualification and external registry acceptance are NOT_EVALUATED.
An `EiaUsAdapter` success exercises a separate synthetic generator, so it gives
no evidence that the EIA US loaders or live retrieval work.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-21 | Inventory methods, retain overlap evidence and distinguish synthetic adapter output from loader integration for #1608. |

## Evidence and registry maintenance

All method references below are relative to
`packages/worldenergydata-eia_us/src/worldenergydata/eia_us/` unless qualified.
The source revision is `f82ff2f186158d6f3fa4c457d4049f7ec08c1aeb`.
The proposal records symbols, line ranges and whole-file SHA-256 digests at that
revision; it does not derive engineering authority from a source-code citation.
The source pack is the EIA US pack in #1267, section 9, based on
`285d65c40896b17ccf44568e59f5b789d59c943e`. Its original empty inventory is
historical evidence, not the inventory of the new proposal.

The external `digitalmodel` registry, `docs/registry/implementation-map.yaml`,
was read at artifact commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`;
its embedded revision is `947fa50ff9a9e210de7e8f90e01b37add85c5954`.
The proposal's `external_map` records the byte digest and membership observation:
13 families inspected, zero EIA US implementation rows. These counts come from
`families[].implementations[].path`, not a name-only search.

Following the existing drilling package's `docs/implementation-map.json`
enrollment precedent, this change supplies a local proposal without editing a
registry owned by another repository. All five proposed families remain
`counted: false`. The external counted-family result remains NOT_APPLICABLE;
there is no claim of a completed external counted-family audit.

The maintenance sequence is:

1. Review the proposal's family boundaries, symbols, delegations and candidates.
2. Submit accepted rows through the external registry's maintenance process.
3. Pin that resulting map artifact commit, embedded revision and byte digest.
4. Recompute in-package membership and counted-family selection at that revision;
   repeat the recorded searches for each selected family and classify definition
   hits at symbol level before claiming the audit complete.

The last steps require external registry review and remain follow-up work.
This proposal already repeats discovery for **every proposed family**, including
those not yet counted. No miss allowance or uniqueness conclusion is inferred.

## Method inventory

Counts below are derived from the proposal's `implementations` arrays. All
package functions and class methods, including helpers and constructors, appear
exactly once. Dataclass-generated methods are not source definitions.

| Family | Definitions | Methods and overlap classification |
| --- | ---: | --- |
| Retrieval/cache | 13 | `client/eia_api.py`: cache expiry/storage, URL/key construction, parsing, fetch and request spacing. `fetch_series` orchestrates mock/cache/live paths; `_fetch_live` calls the local parser and cache plus `requests.get`. These are infrastructure, not independent production calculations. |
| Normalisation/aggregation | 24 | State, regional, basin and country loaders transform caller records independently. State/regional annual sums, country maxima and DPR latest-period selection are local computations. `DrillingProductivityReport.load_all_basins` delegates to `BasinProductionLoader.load`. Scalar `BasinRecord.net_change_bopd` and vectorized `net_change_summary` compute the same addition independently. |
| Decline | 7 | `arps_hyperbolic` owns the rate equation; `HyperbolicDeclineModel.predict` calls it and applies local switching/clipping. `ShaleDeclineResult.predict` delegates to the model. `ShaleDeclineAnalyzer.fit` uses SciPy's optimizer and owns guesses, fallback and diagnostics; it does not implement a second optimizer. |
| Fiscal | 4 | Federal and state calculations perform their own revenue-based arithmetic; none delegates to another fiscal implementation. Current fiscal authority and effective-date qualification remain NOT_EVALUATED under #361. |
| Production crosscheck | 2 | `GoMCrosscheck` stores a tolerance and computes local difference/relative error. No BSEE loader is called. The zero-reference substitution remains #1607; it is not an independently qualified acceptance rule. |

### Repository overlap discovery

Each family records its regex, the exact source revision and all matching
tracked Python paths, including scripts and tests. Replay the Git command in
`search.command` with the recorded `pattern` and `revision`. The regression
suite compares the pinned path set with Git's maintained-source output (excluding
its own new consumer file), so it also runs in shallow checkouts. Historical
replay uses the recorded revision command. Neither check equates a text
hit with an independent definition.

| Family | Matching files | Meaning |
| --- | ---: | --- |
| Retrieval/cache | 13 | Separate feed retrieval and series-client consumers. |
| Normalisation/aggregation | 53 | Loaders, summaries and consumers; outside candidates require review. |
| Decline | 23 | Rate/fit implementations and their consumers. |
| Fiscal | 7 | Fiscal classes, royalty-script candidates and consumers. |
| Production crosscheck | 2 | Local comparison and tests. |

These are counts of matching files at the source pin, not counts of methods or
approved families. Uninspected outside hits are explicitly
`candidate_requires_review`; test files are `test_consumer`.
The proposal's `overlaps` array pins the following inspected definitions:

- The separate `eia` package's `EIAFeedClient.fetch_petroleum_weekly` uses its own
  `_get` HTTP path; it does not call `EIAApiClient`.
- The production package's `ArpsDeclineCurve._rate_fn`, the fiscal-data package's
  `ProductionForecaster.hyperbolic_decline`, and the country packages'
  `DeclineCurveAnalyzer._fit_hyperbolic` methods contain independent formulas.
- The source-data package's `ProductionForecaster._fit_hyperbolic_decline`
  fits its own local function. A shared formula does not establish shared units,
  fitting bounds, fallback, switching policy or diagnostic semantics.

The exact package paths and symbols are in `overlaps`; no equivalence or
interchangeability is claimed. Annual rate aggregation (#1605), horizon-based
switching and fit diagnostics (#1604), and cache-mode separation (#1606) remain
separate changes. The response-shape correction in #1271 is already present at
the source revision; it does not qualify the remaining transport behavior.

## Synthetic adapter boundary

`packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py`
contains a different implementation. Its `region = "eia_us"` is a router key.
`fetch` expands the adapter's own `_FIELDS` table through `_generate_field_rows`,
then delegates date/field filtering to the shared adapter base. Every emitted row
has `source = "eia_us_mock"`. The bbl/Mcf column labels are synthetic monthly
schema quantities, not measured production or verified unit conversions.

The table magnitudes, ramp and decline assumptions are unqualified demonstration
inputs. No coefficients are recommended for engineering use. The adapter does
not import or invoke these series clients, production loaders, decline models,
fiscal calculations or crosschecks. Filtering generated rows does not transform
that provenance. A production query, schema check or nonempty-result assertion
therefore cannot establish EIA US loader coverage.

`test_adapter_provenance_without_loader_calls` replaces the table with a neutral
synthetic fixture, makes every production loader and the series fetch method
fail on invocation, and verifies a successful filtered query retains both the
router label and synthetic source tag. It makes no live request.

## Worked example: duplicate arithmetic versus delegation

This example is synthetic arithmetic, not an EIA observation. Inputs are a
new-well contribution of 120 bbl/day and a legacy change of -45 bbl/day.
The independent hand calculation is `120 + (-45) = 75 bbl/day`.
Both `BasinRecord.net_change_bopd` and
`DrillingProductivityReport.net_change_summary` return that value by separate
scalar and vectorized additions. Neither is a second measurement.

The method basis is the two named source definitions at the source pin; the
expected value comes from the written addition, not either implementation.
`test_dpr_independent_arithmetic_and_delegation` also substitutes a sentinel
loader result and proves `load_all_basins` returns that same object. This
separates independent arithmetic from delegation without relying on live data,
fiscal rates, decline coefficients or an acceptance tolerance.

## Verification and limits

Run `tests/unit/eia_us/test_implementation_map.py` with the EIA US, production,
core and root source directories importable. The tests cover complete inventory
membership, source digests and ranges, discovery evidence against tracked sources, the hand
calculation, delegation and synthetic loader isolation. Existing EIA US and
unified-adapter tests remain applicable. No existing engineering equation or
numeric default is changed.

External registry promotion and the subsequent counted-family audit remain
pending. Outside lexical candidates need symbol review; the recorded searches
are bounded by their regexes and source revision. Engineering qualification is
NOT_EVALUATED for the existing decline, fiscal, unit and tolerance policies.
