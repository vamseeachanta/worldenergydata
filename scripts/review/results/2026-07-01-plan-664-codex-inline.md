# Inline Adversarial Plan Review: Issue #664

**Plan:** `docs/plans/2026-07-01-issue-664-texas-rrc-field-development-metrics.md`
**Reviewer:** Codex inline
**Date:** 2026-07-01
**Verdict:** APPROVE WITH MINOR FOLLOW-UP

## Findings

### 1. Upstream lifecycle artifacts must not be assumed

Severity: Major if omitted; addressed in plan.

The plan correctly treats merged prerequisite code as insufficient proof that
the `/mnt/ace` lifecycle spine exists. It includes fail-closed source loading
and a direct-source hardening task before the lifecycle-production join. This is
required because #664 depends on actual local curated inputs, not only source
code availability.

### 2. Well density could be misrepresented

Severity: Major if omitted; addressed in plan.

The acceptance criteria ask for well density, but #665 owns GIS acreage and
pipeline/GIS infrastructure. The plan avoids inventing true areal density and
instead emits `well_density_proxy` with `well_density_basis = wells_per_lease`.
This is the correct bounded metric for #664.

### 3. Production per well could imply false allocation precision

Severity: Major if omitted; addressed in plan.

Texas RRC PDQ production is lease/field/operator grain, not clean per-well
allocation. The plan computes field-level `production_per_well_boe` only as a
field aggregate divided by lifecycle well count and requires
`no_per_well_allocation` / `lease_level_production` caveats.

### 4. CLI command may inherit slow global startup

Severity: Minor.

The plan identifies the risk that `worldenergydata` CLI startup may import
unrelated heavy scientific modules. The implementation should not expand #664
into a broad CLI architecture refactor. If startup remains a blocker, file a
follow-on issue for lazy command imports and use the Texas RRC APIs directly for
artifact generation.

## Required Implementation Guardrails

- Do not mark #664 `status:plan-approved` from the agent side.
- Keep direct-source hardening scoped to completion directory dedupe and
  wellbore reader support needed by #664.
- Preserve lifecycle-only and production-only fields in the output; do not
  inner join them away.
- Keep pipeline proximity, GIS acreage density, economics, and reports out of
  #664.
