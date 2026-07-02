# Code Review: Issue #695 Texas RRC Field Opportunity Ranking

Reviewer: Codex inline
Date: 2026-07-02
Scope: implementation branch `feat/onshore-rrc-field-opportunities-695`

## Verdict

APPROVE after fixes below.

## Findings

### MAJOR - Fractional infrastructure scores were treated as 0..1 component scores

Evidence: live `/mnt/ace` publication showed top-ranked direct-access fields with
`infrastructure_access_score=1.0` but `infrastructure_component_score` near `1`
instead of `100`, suppressing total opportunity scores.

Mitigation:
- Added `test_fractional_infrastructure_scores_are_scaled_to_component_percent`.
- Updated `opportunities/scoring.py` so fractional infrastructure values are
  scaled to percent before weighting.

### MAJOR - Fractional remaining-activity scores were treated as 0..1 component scores

Evidence: corrected live `/mnt/ace` publication still showed
`remaining_activity_score=0.98` becoming `remaining_activity_component_score=0.98`,
which made top scores peak near `45` despite strong remaining-activity signals.

Mitigation:
- Added `test_fractional_remaining_activity_scores_are_scaled_to_component_percent`.
- Updated `opportunities/scoring.py` so remaining-activity series expressed as
  `0..1` ratios are normalized to `0..100`.

### MAJOR - Routine caveats forced every field to `low_confidence`

Evidence: first full `/mnt/ace` publication after infrastructure scaling produced
67,082 rows all classified as `low_confidence`, because routine caveats such as
lease-level production allocation counted the same as missing core evidence.

Mitigation:
- Added `test_quality_caveats_do_not_force_low_confidence_when_core_sources_exist`.
- Changed opportunity-class logic so only missing core evidence forces
  `low_confidence`; routine caveats remain visible through quality penalty and
  driver text.

### MINOR - Manifest provenance must be regenerated after commit

Evidence: pre-commit live publications correctly wrote full output files, but
`manifest.json` still recorded `code_revision=23bcb710...` because the
implementation had not yet been committed.

Mitigation:
- Required closeout step: after committing, rerun the full
  `build-field-opportunities` publication and verify `manifest.json` code
  revision equals the implementation commit SHA.

## Verification Evidence

- `uv run --no-sync black --check packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities src/worldenergydata/cli/commands/texas_rrc.py tests/unit/texas_rrc/test_field_opportunity_*.py`
- `uv run --no-sync isort --check-only packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities src/worldenergydata/cli/commands/texas_rrc.py tests/unit/texas_rrc/test_field_opportunity_*.py`
- `uv run --no-sync pytest --noconftest -o addopts='' tests/unit/texas_rrc/test_field_opportunity_*.py -q` -> 21 passed
- `uv run --no-sync pytest --noconftest -o addopts='' tests/unit/texas_rrc -q` -> 526 passed
- `uv run --no-sync worldenergydata texas-rrc build-field-opportunities --root /mnt/ace/worldenergydata/data/modules/texas_rrc --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc --require-sources --max-fields 100`
- `uv run --no-sync worldenergydata texas-rrc build-field-opportunities --root /mnt/ace/worldenergydata/data/modules/texas_rrc --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc --require-sources`

Latest pre-commit `/mnt/ace` quality summary:

```json
{
  "row_count": 67082,
  "source_gaps": [],
  "opportunity_class_counts": {
    "low_confidence": 45721,
    "monitor_only": 17278,
    "screening_candidate": 4083
  },
  "architecture_class_counts": {
    "emerging_growth": 12,
    "high_access_infill_redevelopment": 2208,
    "infrastructure_constrained_activity": 3,
    "low_data_confidence": 50295,
    "mature_harvest": 10840,
    "monitor_only": 3724
  },
  "score_max": 74.79
}
```
