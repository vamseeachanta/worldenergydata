# Adversarial plan review — #1040 replan — provenance R1

**Reviewed base:** `5b2cf22`
**Verdict:** REJECT

Defects found:

1. V1 immutability trusted hashes inside the mutable manifest instead of pinning the external manifest SHA.
2. PR1 left the checked-in v2 manifest state ambiguous and could repeat unreachable squash lineage.
3. Coarse award-class mappings fabricated scope links.
4. Raw bound-shape normalization contradicted v1 `MoneyInterval`, including the GranMorgu 753/1050 `point` anomaly.
5. Owner-decision evidence lacked quote, actor, time, issue comment, plan path, and plan hash.
6. Project/award/requirement correction, override, and migration artifacts were missing.
7. V2 executable provenance did not close over every imported producer module.
8. Delimiter locators were not canonically encoded.

All findings were patched in the 2026-07-19 HTML replan before R2.
