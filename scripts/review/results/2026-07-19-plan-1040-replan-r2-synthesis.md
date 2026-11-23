# Adversarial plan review — #1040 replan — R2 synthesis

**Verdict:** REJECT, then patched inline

R2 found these remaining defect classes:

- Project and requirement identities still lacked canonical source bindings and lifecycle closure.
- Coverage numerators, denominators, unknown handling, and bundle de-duplication were undefined.
- Counting disposition had no evidence-backed input and needed a fail-closed `unknown` state.
- Scope completeness could not distinguish `unknown`, `none`, `partial`, and `full` deterministically.
- Raw `open_range` was not representable by the source.
- Lineage needed trusted `origin/main` hydration, one-parent squash fixtures, deleted feature refs, and separate hostile cases.
- Exact enums, canonical JSON/path ordering, structural tests, and approval-authenticity limits needed to be explicit.

The main session patched these findings directly, following the R3 inline loop-break rule. It added project and requirement crosswalk/identity surfaces, exact set formulas, per-award scope components and counting decisions, raw accounting enums, trusted-main hydration, independent hostile lineage nodes, and explicit approval verification limits.
