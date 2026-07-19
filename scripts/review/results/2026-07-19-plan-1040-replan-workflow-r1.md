# Adversarial plan review — #1040 replan — workflow/accounting R1

**Reviewed base:** `5b2cf22`
**Verdict:** REJECT

Defects found:

1. Accounting normalization could not satisfy the v1 interval contract.
2. Class-level mapping created false scope coverage.
3. The artifact map omitted executable schemas, modules, tests, nodes, and builder paths.
4. Composite-host exceptions had no override surface.
5. Shallow CI producer hydration was absent.
6. PR1/PR2 path boundaries, drift guards, reviews, comments, CI, and cleanup gates were ambiguous.
7. Identity migrations/tombstones had no durable surface.
8. Approval evidence was under-specified.

All findings were patched before R2.
