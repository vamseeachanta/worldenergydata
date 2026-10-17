# Analysis module issue drafts

These numbered drafts accompany [the knowledge pack](agent-pack.md), revision 2.
They are proposed work, not filed issues or completed acceptance checks. Draft N
is the target of the pack's `issue pending (N)` references and open item ON.

## Draft 1: Validate pressure inputs and establish an independent benchmark

Problem: The estimator assumes compatible psia, ft and Rankine values and uses
an unqualified coefficient and tier thresholds. Positive infinite depth passes
the depth check: reported pressure yields a zero gradient and a false severe
tier, while shut-in pressure yields a nonfinite gradient that selection drops.
Negative pressure can classify severe and trigger the shut-in vacuum flag;
positive infinite pressure can classify normal. Configuration ranges are unchecked.

Acceptance:

- Reject nonfinite or non-positive pressure and depth before calculation, with
  counted exclusions and reasons in the summary; test each pressure kind.
- Test NaN, both infinities, zero and negative pressure/depth, invalid settings,
  threshold order, unknown pressure kinds and fractional participation minima.
- Establish a public independent source for coefficient units, applicability and
  tier assumptions; add an independently calculated expected pressure and a
  declared tolerance. Repeating the implemented formula is insufficient.
- Coordinate the numeric-flag regressions in draft 2 with the invalid-input tests.

## Draft 2: Validate normalization, numeric flags and source completeness

Problem: Column presence does not establish value or provenance validity. The
flag parser accepts text `1`, `true` and `yes`, but float-typed `1.0` becomes false.
With usable-proxy filtering this can remove every source row without an error;
earliest flags can all become lower priority. Text `NA` also becomes false.
Empty inputs and missing quality metadata can appear usable.

Acceptance:

- Accept numeric 1/0 flags, including nullable float columns; test Boolean,
  integer, float, null, padded text and unsupported tokens with an explicit policy.
- Test usable-proxy filtering and all three source earliest-flag routes; account
  for every excluded row and reject an unexpectedly empty usable source.
- Validate schema selection, required values, identifier preservation, unique
  source names, provenance conflicts, quality payload shape and all-empty inputs.
- Add detection checks for the uncovered normalization paths S01–S19.

## Draft 3: Preserve selected-record identity and complete ranking counts

Problem: First-non-null aggregation can combine cells from different observations.
Missing keys, metadata and gradients disappear from selection or summaries;
group labels can combine states and tied rankings lack a secondary key.

Acceptance:

- Select one original observation using a stable record identifier and explicit
  year/priority tie rules; prove that selected cells belong to that record.
- Report missing-data and small-group exclusions and reconcile input, selected
  and ranked counts, including null keys and labels.
- Use explicit group identity across states/sources and deterministic tied order;
  cover S26–S33, S39 and S45–S48, including summary rounding bounds.

## Draft 4: Reject vacuous gates and publish accepted outputs transactionally

Problem: Empty recovery or participation requirements can pass. Outputs are
written before gate failure and have no acceptance marker or input digests.
Missing summary counts and warnings default to empty dictionaries.

Acceptance:

- Reject absent or empty mandatory rules and validate minimum counts; test
  missing identifiers, empty rules and both failed gates.
- Publish accepted outputs atomically or mark failed/incomplete outputs so that
  file presence cannot imply acceptance; test interruption and failure paths.
- Retain input digests, warning disposition and signed QA evidence; implement
  C11 and the uncovered S35–S44 detection checks.

## Draft 5: Test metadata and invalid-date round-trip fidelity

Problem: Date coercion falls back to text for an entire column after any parse
failure; other object values lose their original types. The existing round-trip
example checks selected counts without general metadata equality.

Acceptance:

- Declare supported metadata types and date/null preservation rules.
- Test invalid and mixed dates, null objects and supported object types through
  Parquet write/read, asserting values and types rather than row counts alone.
- Document explicit rejection or conversion for unsupported types; cover S49–S51.

## Draft 6: Reconcile compatibility routes and the dashboard test skip

Problem: A compatibility test skips unconditionally although the wrapper exists;
legacy verification guides advertise a different import route. Dashboard
algorithms belong to the delegated package and are not qualified by this pack.

Acceptance:

- Audit the section-10 discovery list against executable import and command routes.
- Restore relevant tests against supported routes, with a reason for each
  genuinely unavailable dependency; preserve coverage when replacing stale tests.
- Identify the dashboard algorithm/documentation owner and qualification scope.

## Draft 7: Qualify source readiness and record pack ownership

Problem: Offline fixtures do not establish historical totals or current source
readiness. Deputy appointment and shared knowledge indexing remain open.

Acceptance:

- Retain versioned input manifests, source identities, units and digests with
  native readback and reconciled totals before adopting historical results.
- Record warning disposition and distinguish assumed data from qualified data.
- Appoint a deputy and record the pack and lesson entries in the existing index.

## Draft 8: Register the analysis method families in the implementation map

Problem: The pinned map contains no implementation row in this package, so its
counted-family search cannot assess the section-3 methods.

Acceptance:

- Add candidate rows and search signals for observation normalization, static
  gas-column estimation, gradient tiers, earliest selection, group ranking,
  recovery/participation gates and metadata serialization.
- Record the resulting map revision and inventory in section 9; rank applicable
  families by in-package row counts and run the required definition-level search.

## Draft 9: Replace identifying labels with neutral dataset IDs

Problem: Existing test fixtures and discovered documentation contain identifying
labels that must not propagate into new public knowledge artifacts.

Acceptance:

- Inventory identifying labels without reproducing them in the issue text.
- Obtain approved neutral dataset IDs, preserve numeric fixture behavior and
  update references consistently; rerun the affected tests and the name scan.
- Retain provenance in the appropriate restricted record when required.
