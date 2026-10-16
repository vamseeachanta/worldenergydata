# EIA qualification issue drafts

These ten numbered drafts support the pack's linked pending references. No issue number is assigned by this document. The maintainers file the drafts, then replace each linked pending reference with the resulting issue number. Existing related open issues are #266 and #431.

## Draft 1

**Title:** Validate weekly feed envelopes and pagination completeness

**Problem:** Missing response/data/total fields can appear to be a successful empty feed or stop pagination early. String totals raise `TypeError`. A fixed 5000-record offset step can silently skip or repeat records when returned or requested page lengths differ. Timeout ranges are unchecked. Pack rows: S01, S05, S06, S21, S29, S35.

**Acceptance:** Add regressions for malformed envelopes, absent and string totals, empty pages before the declared end, short non-final pages, overridden lengths below and above 5000, and invalid timeouts. Define explicit failure or complete-record behavior for each; assert requested offsets and final record identities/counts. Do not treat a one-page fixture as completeness evidence.

**Related:** #431 covers HTTP transport/retry behavior; this draft adds the untested weekly pagination cases.

## Draft 2

**Title:** Qualify numeric values, serialized types and units

**Problem:** Missing, null and invalid values become indistinguishable; locale separators fail conversion, nonfinite values pass, unsupported JSON objects become strings, and units are copied without qualification. Pack rows: S02–S04, S13, S16.

**Acceptance:** Define and test handling of missing/null/invalid values, thousands/decimal separators, nonfinite numbers, unsupported serialized values and incompatible unit strings. Preserve source values and explicit rejection evidence without silently changing units.

## Draft 3

**Title:** Validate ingestion state and define correction recovery

**Problem:** Corrupt state falls back to an empty mapping, invalid periods are omitted or ordered lexically, and append/state writes can race or be interrupted. A watermark can exclude later corrections. Pack rows: S07–S12, S14–S15, S20.

**Acceptance:** Add state-shape/date validation tests, corrected same-period records, missing/non-string periods, corrupt/unreadable state and interrupted/concurrent writes. Specify replay and recovery behavior and prove record identities are neither lost nor duplicated.

**Related:** #431 identifies lexical-date and transport weaknesses.

## Draft 4

**Title:** Cover runner exits, empty feeds and partial results

**Problem:** Empty output and unknown feed handling lack detection checks; a second-feed failure can follow successful writes; downstream conversion/metadata failures can remain warnings. Pack rows: S17–S18, S22–S27, S31–S33.

**Acceptance:** Test runner exit codes 1 and 2, empty feeds, unchanged state on empty results, unknown feeds and first-feed success followed by second-feed failure. Assert output/state side effects. Add adapter checks for conversion and refresh-metadata failures and define when they prevent success.

**Related:** #266 requires successful operational materialization; mocked adapter success alone does not establish it.

## Draft 5

**Title:** Add independent source-value evidence and acceptance records

**Problem:** Five mocked regression examples provide no independent source-value benchmark, generated QA appendix or shared lesson record. Independent acceptance remains pending.

**Acceptance:** Add an openly available, revisioned source-value reference with provenance, units and numeric tolerances. Run the mapped checks against it, record an independent QA decision and a shared lesson, and promote examples only when that evidence supports validation. Complete independent pack acceptance after the tracked qualification gaps are assessed.

**Related:** #266 separately covers live compatibility and freshness.

## Draft 6

**Title:** Exclude the nested knowledge pack from package distributions

**Problem:** The EIA package-data configuration includes nested Markdown; exclusion of this pack and its issue drafts from distributions is unproved.

**Acceptance:** Inspect wheel and source-distribution contents, define the intended documentation boundary, and add packaging checks showing that nested pack documentation is excluded while required runtime assets remain included.

## Draft 7

**Title:** Index weekly feed methods and normalization map gaps

**Problem:** The pinned implementation map contains no in-package family rows. Section 3 covers HTTP pagination, response normalization, incremental selection and persistence; separate series/state normalization routes also need indexing.

**Acceptance:** Add map entries for the four families and their listed implementations, including the outside-package series and state-production routes. Supply reproducible search signals, rerun inventory/ranking at the new map revision and update the pack's pinned map reference.

## Draft 8

**Title:** Codename the omitted discovery locator

**Problem:** One discovery file has identifying names and is omitted from the public reading index.

**Acceptance:** Assign neutral identifiers to the discovery material, verify the public name scan, and add a neutral reading locator. Do not copy identifying names into the issue or its evidence.

## Draft 9

**Title:** Align CLI documentation with the weekly sync command

**Problem:** The CLI documentation describes `eia fetch` while the command implementation exposes `sync`.

**Acceptance:** Update usage and examples to the supported command, add an offline help/example smoke check, and ensure documented output matches the command contract.

## Draft 10

**Title:** Redact authentication material in the quickstart example

**Problem:** The quickstart can print configured authentication material. Pack row: S34.

**Acceptance:** Remove authentication values from example output and add an output-capture regression using synthetic input. Cover configured and absent authentication; confirm neither stdout nor stderr contains the supplied value. Retain only file/line and rule identifiers in disclosure evidence.
