# Landman diligence pack

The offline generator assembles explicitly cleared evidence into a human-facing,
self-contained HTML report and a separate JSON summary. It reports observations
and gaps, without assigning ownership, underwriting scores, reserves, depletion,
environmental clearance, or infrastructure access rights.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| initial | 2026-10-20 | Introduce the normalized evidence contract, report generator and synthetic example to expose missing coverage. |

## Scope and source basis

The report covers asset/location, wells, production, pressure/depletion,
permits/completions, infrastructure, HSE/environmental overlays, and
lease/title/mineral availability. All sections appear even without evidence.
An observation-bearing section is `OBSERVATIONS_ONLY`; an empty section is
`NOT_EVALUATED`. Neither is a passed diligence check. Gaps and cautions remain
visible alongside supplied observations.

The contract implements #916, with acquisition and coverage dependencies #910
(data inventory), #911 (U.S. onshore matrix), #912 (source discovery), #913
(public land), #914 (county/title feasibility), and #915 (join readiness).
No inventory or matrix artifact is invented when those inputs are unavailable.
The report includes their required reference entries with `NOT_EVALUATED` and
the relevant issue reference until an actual artifact is supplied.

Existing source documentation remains authoritative for upstream limitations:

- [State well-database source catalog](../data-sources/onshore/state-well-databases/source-catalog.md)
  (2026), pressure-data availability and state-specific source descriptions.
- [Texas pressure observations](../data-sources/onshore/texas-rrc/pressure-observations.md)
  and [Kansas pressure observations](../data-sources/onshore/kansas-kgs/pressure-observations.md)
  (2026), observation provenance and test-type boundaries.
- [Texas field-atlas reports](../data-sources/onshore/texas-rrc/field-atlas-reports.md)
  (2026), separate HTML/summary convention and infrastructure caveats.
- Source code integration points: `worldenergydata.texas_rrc.reports`,
  `worldenergydata.kansas_kgs`, `worldenergydata.analysis.underpressured_screen`, and
  `worldenergydata.landman`. These are references, not imports or readiness claims.

## Run

From a repository checkout with the package importable:

```bash
PYTHONPATH=src python -m worldenergydata.underwriting \
  examples/underwriting/input.json diligence-output/pack
```

The destination must be new. The command reads the supplied input only and
creates `index.html` and `summary.json`. It neither downloads nor refreshes
upstream datasets. No existing output is overwritten. For a relocated report,
set `--repository-url` to the public repository root URL; the default relative
root suits the example's directory layout. Repository document links require
that layout or the supplied root URL; the report's text and tables work offline.

## Input contract

See the complete [example input](../../examples/underwriting/input.json).
Unknown fields and section keys are rejected to make typing errors visible.

| Field | Meaning |
| --- | --- |
| `asset`, `as_of` | Display identifier and UTC evidence cutoff date (also the issue date), not a sourced location claim. Location facts belong in observations. |
| `revision`, `revision_note` | Issue identifier and description of the change and reason. Retain prior issued reports. |
| `previous_revisions` (optional) | Earlier revision/date/change rows, copied unchanged before the current row. IDs must be unique and dates chronological. Re-issues supply the complete prior history. |
| `sources` | Source declarations with unique ID, kind, materialization status, explicit publication clearance, citation, URL, timezone-aware retrieval timestamp, SHA-256, license, coverage and caveats. |
| `observations` | Section, subject key, label, unchanged value, unit, source ID, row/document locator and observation date. Include the period and scope in the label or locator. |
| `gaps` | Additional section-specific missing evidence or unresolved joins. |
| `references` | Data inventory, U.S. onshore matrix, and source modules/issues, each with status, note and link if available. |

Source statuses use #910's vocabulary: `downloaded`, `derived`,
`configured-only`, `partial/error`, `missing`, and `private/legacy`.
Observations require `downloaded` or `derived`; configuration and partial
artifacts cannot supply facts. `private/legacy` is rejected entirely.
Other unavailable sources may be listed as provenance only, with caveats and
no observations. Their existence does not make any report section evaluated.

Source kinds are `regulator`, `lease`, `title`, `mineral`, `infrastructure`,
`hse`, and `synthetic`. Non-synthetic sources require the caller's
`publication: public-approved` declaration. Synthetic sources require
`publication: synthetic` and cause a prominent report banner. This declaration
is an input boundary, not an automated legal review. Source clearance, rights,
row selection, raw-byte digest verification and public-safe wording must be
reviewed before preparing the input. Do not put private records into the input.

Regulator, infrastructure and HSE source kinds cannot populate the
lease/title/mineral section. Actual lease/title/mineral observations require
their own explicitly classified source. Even then the report supplies evidence,
not an ownership or title conclusion. Cross-source joins must be performed and
qualified upstream: the generator preserves subject keys and never associates a
lease-level volume with wells by proximity or an unpaired list.

Observation values must be nonempty text or finite numbers, with units (use
`text` or `identifier` for nonphysical values). No unit conversion is performed.
Repeated observation identities are rejected rather than silently double
counted. Different source records for the same well remain distinct observations;
they are not counted as distinct wells. Retrieval and observation dates cannot
follow the UTC evidence cutoff. Retrieval timestamps are converted to UTC before
comparing their dates. The cutoff `as_of` is also the current revision issue date;
a reissue advances it while retaining earlier observation dates.

Links permit public HTTP(S) URLs without embedded credentials and repository
paths under `docs`, `src`, `packages`, or `examples`. Filesystem URLs, parent
traversal and executable URL schemes are rejected. All report text is HTML
escaped. Reports include no scripts, remote styles, or raw embedded JSON.

## Inputs and method

The committed example is **synthetic**, not downloaded regulator data. Its
invented inputs are one location observation, two well-identifier observations,
and a lease-level monthly oil observation of **12 bbl**. This value is a chosen
test input, with no engineering coefficient or acceptance implication. The
example has no pressure, permit/completion, infrastructure, HSE, or title data.
The inventory and matrix artifacts were not supplied.

There are no engineering equations or acceptance limits. The independent hand
calculation is simply row counting: one location row plus two well rows plus
one production row equals **four supplied observations**. The oil value stays
**12 bbl**. No production summation across periods or allocation to wells occurs.
All five empty sections are `NOT_EVALUATED`. Production additionally carries an
explicit gap about well allocation.

The synthetic source digest identifies the invented observation list, encoded
as UTF-8 JSON with sorted keys and compact separators: `json.dumps(observations,
sort_keys=True, separators=(',', ':')).encode()`. The summary's `input_sha256`
identifies the complete input file bytes. The generator verifies source digest
syntax, but does not open external artifacts to verify declared source digests.

## Worked answer

Open the [HTML diligence pack](../../examples/underwriting/index.html).
The [machine-readable summary](../../examples/underwriting/summary.json) remains
a separate artifact. Tests regenerate both and require byte equality. Git attributes
preserve LF bytes for the example input and outputs on every platform.

The answer supports requesting the missing evidence, not an investment or legal
decision. Obtain the inventory and matrix, qualified pressure observations,
permit/completion records, spatial overlays and independently sourced lease,
title and mineral records. The existing production observation cannot close
any ownership gap. Pressure and depletion remain unevaluated without test
basis, datum and comparability review.

## Verification and remaining work

Contract tests cover independent row-count expectations, unchanged measurements,
all report sections, source clearance, missing provenance, unsafe URLs, escaped
markup, nonfinite values, duplicate observations, date bounds, reproducible
artifacts, CLI execution and preservation of existing outputs.

Slice 1 supplies normalized evidence validation and explicit gaps. Slice 2
supplies the HTML report, separate summary and offline command. Slice 3 supplies
the synthetic worked answer and regression tests. Materializing a real asset
pack remains dependent on reviewed inventory/matrix artifacts and qualified
public source extracts from #910--#915. Native raw-data adapters, engineering
depletion calculations, legal opinions and automatic source-rights decisions
remain later work.
