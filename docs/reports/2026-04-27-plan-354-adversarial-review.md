# Adversarial Plan Review — Issue #354

Verdict: MAJOR (resolved by plan revision before plan-review handoff)

## Findings

1. Plan was directionally correct but left too many implementation choices open (`appendix or expand manifest`, `rebuild or manually update`, etc.).
2. Source-of-truth model was not frozen before implementation.
3. `eia` vs `eia_us` relationship was not explicitly resolved.
4. Off-manifest classification policy was open-ended and could cause scope creep.
5. Data-readiness taxonomy needed derivation rules for mixed/sample modules.
6. CLI `info()` scope needed sharper definition, including top-level help/docstring if user-facing narrative remains stale.
7. Test plan needed concrete mechanics: AST parsing, exact count invariants, allowlist policy, schema completeness.

## Required plan fixes applied

- Freeze contract model: manifest is curated registry, catalog is data inventory, source tree is discovery input, scheduler config is runtime authority, MODULE_INDEX is derived public index.
- Define `eia` as CLI alias/front door for the curated `eia_us` capability unless a separate manifest record is deliberately introduced later.
- Define off-manifest policy: classify source directories into manifest, appendix, ignored internal file, empty namespace, or back-compat shim; fail on unclassified source packages.
- Define `catalog_status` derivation rules.
- Use AST/static parsing as default for CLI checks until #353 runtime import issue is resolved.
- Add required invariants for `total_modules`, scheduler config matching, source allowlist, schema fields, and CLI info parity.
