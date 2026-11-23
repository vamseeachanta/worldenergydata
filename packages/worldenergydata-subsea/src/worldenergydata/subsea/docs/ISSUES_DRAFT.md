# Subsea issue drafts

These ten unfiled drafts correspond to the numbered markers in [the module knowledge pack](agent-pack.md). Each draft retains its number until the maintainers file the issue and replace the matching markers.

## Draft 1: subsea: Define supplier availability, cache and query policies

Cover S01-S08 and S57 with caller-path missing/header-only files, reload/mutation checks, unknown filter values, ambiguous matches and empty queries.

## Draft 2: subsea: Define supplier depth coercion and bounds

Cover S18-S22 with fractional values, localized separators, zero depth and the raw OverflowError from infinite depth text.

## Draft 3: subsea: Validate component finite values, signs and missing cells

Cover S23-S31 and S52-S59 through both CSV loaders and direct models; include positive infinity, negative weights, geometry and default NA tokens.

## Draft 4: subsea: Define supplier normalization and provenance requirements

Cover S09-S17 and S32-S42 with blank scalars, omitted lists, null elements, source/date validation and unknown keys.

## Draft 5: subsea: Qualify numeric field units

Resolve U1 and S43-S51 against independent dimensional evidence before numeric reuse; reconcile weight and pressure metadata.

## Draft 6: subsea: Make the working CAD environment reproducible

Preserve the observed CadQuery 2.8.0 and nlopt 2.11.0 environment and reproduce all seven CAD nodes under automation. The current isolated run passes all seven; full locked-project resolution and other supported environments remain unverified. Context #580.

## Draft 7: subsea: Register subsea methods and downstream map gaps

Add the six section-3 families to the implementation map, classify outside-package selection/normalization helpers and index the pack.

## Draft 8: subsea: Establish independent source basis and a worked example

Resolve U3 with source rights, freshness and catalogue accuracy evidence; add an independently validated catalogue example. V1 establishes synthetic geometry only.

## Draft 9: subsea: Verify documentation exclusion from distribution

Resolve U4 by building the wheel, inspecting package members and qualifying recursive Markdown inclusion.

## Draft 10: subsea: Nominate an independent deputy

Resolve U5 with a maintainer-nominated independent reviewer and a recorded review assignment.
