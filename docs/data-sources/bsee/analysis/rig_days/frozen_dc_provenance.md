# Frozen D&C provenance

## Summary

The frozen workbook retains its original bytes. Its adjacent
`drilling_and_completion_days.provenance.json` records the archived counting
method, binds it to the workbook with SHA-256, and explicitly leaves historical
PND days and coverage unknown. This is an archival description, not approval of
the historical algorithm or proof that its execution produced every frozen count.
Full reproduction remains `NOT_EVALUATED`.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-21 | Record the historical method and digest; add a loader so provenance can accompany the immutable workbook. |

## Evidence and historical method

The workbook and its adjacent `extract_drilling_completion_days.py` first occur
in repository revision `7493f54316cc1d1ee5b5813afe69c90c873c04e7`. The archived
source can be inspected without changing the worktree:

```bash
git show 7493f54316cc1d1ee5b5813afe69c90c873c04e7:docs/modules/bsee/analysis/production/FDAS_V30/extract_drilling_completion_days.py
```

This revision is the source edition for the following rules and constants:

- `main`, section `Drilling days (gap-adjust if >250)`: start with
  `(TOTAL_DEPTH_DATE - WELL_SPUD_DATE).days`; replace missing dates with zero.
  If the result exceeds **250 days**, clip available WAR intervals to spud..TD
  and use `union_days` when intervals exist. Otherwise retain calendar days.
  The threshold is a historical implementation detail with no established
  engineering justification; it is recorded, not recommended.
- `union_days`: normalize endpoints, merge overlapping intervals, and sum
  `(end - start).days` for each merged interval. Adjacent intervals remain
  separate. This exclusive counting differs from current activity-code unions.
- `derive_completion_days`: count distinct normalized dates from WAR intervals
  joined through remarks, clipped to dates **at or after TD**, inclusive.
  There is no activity-code filter, first-oil bound or gap cutoff. A single
  missing endpoint is replaced with the other. Missing TD, empty joined input,
  or no qualifying dates yields zero. The keyword list does not filter this
  function. Servicing can be counted, while intervals without joined remarks
  can be missed.

These are descriptions of code held beside the workbook. There is no retained
run manifest establishing the exact executable and raw-data vintage for the
historical run. The [existing basis comparison](day_basis_comparison.md),
“Rule and conventions” and “Wells compared and wells not computed”, also limits
its evidence to held records; it does not certify whole-population reproduction.
No scientific acceptance tolerance, day rate, or new numerical rule is introduced.

## Metadata contract

Edition 1 of this contract defines the JSON `schema_version` value `1` and the
basis identifier `legacy_calendar_or_war_union_post_td_remarks`. Required fields:

| Field | Meaning |
| --- | --- |
| `workbook_sha256` | SHA-256 of the complete original workbook bytes, including all sheets. |
| `sheet` | `Sheet1`, the historical bore-level counts. |
| `basis` | The archived hybrid drilling and post-TD remarks-joined completion rule above. |
| `rule` | Nonempty descriptions of drilling, completion, missing values, PND and coverage. |
| `sources` | Nonempty source citations identifying the archived implementation and limitations. |
| `limitations` | Nonempty statements of evidence gaps and scope. |
| `pnd_days` | JSON null; the workbook contains no separate PND measurement. |
| `days_status` | `historical_coverage_unknown`, never inferred from zero counts or missing dates. |
| `reproduction_status` | `NOT_EVALUATED`; recording an algorithm does not reproduce its historical run. |

The loader rejects missing or unknown fields, duplicate JSON keys, unsupported
schema/policy values and digest mismatches before publication writes. It reads
and labels the exact bytes that were hashed; it does not modify the workbook or
recompute its counts. The sidecar is reviewed repository metadata, not an external
authentication mechanism. A new rule, measured historical PND, or certified
coverage requires new evidence and a reviewed contract revision.

PND remains an opaque activity code. Historical completion could include
PND-coded intervals because it had no code filter; separate PND days cannot be
recovered from the totals. `PND_DAYS` therefore stays nullable and unknown on
**every frozen row**, including rows whose old day counts are zero. Coverage
stays `historical_coverage_unknown` on every frozen row. Original day values
remain available for archival inspection; their zeros do not certify inactivity.

## Loading and publication

The builder defaults to the JSON sidecar beside the frozen workbook. An explicit
metadata path is also supported:

```bash
python scripts/lower_tertiary/build_dc_vintage_diff.py --frozen-metadata docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.provenance.json
```

In Python, `lower_tertiary.frozen_dc_metadata.load_frozen(workbook, metadata_path)`
returns a labelled DataFrame. The scripts directory must be importable; this
loader is intended for repository builders. A candidate requires its own `BASIS`,
nullable `PND_DAYS`, and source `DAYS_STATUS`; metadata on the frozen side never
supplies candidate labels. Only the frozen loader may supply the historical
unknown status. The existing production candidate is unlabelled, so production
regeneration is still blocked and existing publications are retained.

The vintage CSV retains `basis_v30` and `basis_wed` and adds `pnd_days_v30`,
`pnd_days_wed`, `days_status_v30`, `days_status_wed` and `same_basis`. A genuinely
absent outer-join side has null provenance. Every present side must have its own
basis. Combined basis is `mixed` when the two recorded rules differ. Existing
numeric deltas retain their archival subtraction for downstream compatibility;
`same_basis` is false unless both sides exist and have the same rule. Deltas and
category labels describe the old count classification only; they do not prove
that servicing or data arrival caused a difference across rules. The inspection
helper `build_diff` retains its legacy arithmetic; guarded writes occur in `main`.

## Worked example

The offline `test_frozen_dc_metadata.py` fixture supplies these synthetic inputs:

| Vintage | Drilling days | Completion days | Separate PND days | Basis | Coverage |
| --- | --- | --- | --- | --- | --- |
| Frozen | 3 | 2 | unknown | Archived hybrid rule | historical coverage unknown |
| Candidate | 3 | 4 | 1 | Synthetic activity rule | WAR covered |

The method is metadata validation, not interval reconstruction: verify the
workbook digest, load the original counts, and attach each side's own labels.
The independent arithmetic differences are `3 - 3 = 0` drilling days and
`4 - 2 = 2` completion days. These archival differences remain unchanged.
Since the bases differ, `same_basis` is false and the combined basis is `mixed`.
These are not changes measured on one rule. Historical PND
stays null; candidate PND remains 1. Historical coverage remains unknown; it is
not copied from the candidate. Tests also exercise absent/mismatched metadata,
unsupported policies, missing candidate labels and genuinely absent sides,
checking original workbook and prior publication bytes after rejection.

## Known limits and follow-up

The archived algorithm has known counting and input-selection defects and lacks
a retained execution manifest. Whole-population reproduction, measured historical
PND and coverage, fresh candidate extraction, and downstream report regeneration
remain separate work. Generated publications and the frozen workbook are not
changed by adding this metadata.
