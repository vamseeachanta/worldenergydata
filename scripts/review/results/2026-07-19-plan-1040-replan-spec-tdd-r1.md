# Adversarial plan review — #1040 replan — specification/TDD R1

**Reviewed base:** `5b2cf22`
**Verdict:** REJECT

Defects found:

1. Asset classes could silently confirm false links for live SPS, SURF, installation, and `other` counterexamples.
2. `bound_type=unknown` was incompatible with the pinned v1 schema.
3. Data artifacts lacked exact fields, enums, keys, nullability, and set invariants.
4. Implementation/test paths and literal RED/GREEN nodes were missing.
5. Stable identity correction/tombstone behavior had no persisted contract.
6. Exactly-once visitation was undefined beside many-to-many edges.
7. Architecture inference could masquerade as project evidence.
8. Value-basis counting/eligibility semantics were incomplete.
9. Hostile URL, HTML, and CSV-formula tests and executable size checks were absent.

All findings were patched before R2.
