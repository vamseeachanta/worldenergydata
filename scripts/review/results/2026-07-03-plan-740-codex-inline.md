# Codex Inline Plan Review - Issue #740

**Artifact reviewed:** `docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md`
**Review date:** 2026-07-03
**Reviewer:** Codex inline
**Stance:** adversarial defect-hunting; default non-APPROVE until source, scope, and verification defects are resolved.

## Verdict

APPROVE for user review.

## Findings

### Finding 1 - Source ambiguity between OCC completion data and OTC production

**Severity:** resolved before approval

The plan could have conflated OCC completion pressure data with Oklahoma
production data. That would have created an implementation path that cannot be
completed from the OCC source page alone, because the official OCC page points
production users to Oklahoma Tax Commission.

**Resolution:** The plan now scopes #740 to structured OCC completion pressure
observations only. It explicitly excludes OTC production bulk acquisition and
requires documentation of the production limitation.

### Finding 2 - False Panhandle validation risk

**Severity:** resolved before approval

The Oklahoma slice could have been judged against West Panhandle / Guymon-
Hugoton analog recovery even though the structured OCC base workbook is
2010-present and does not include imaged Form 1016 back-pressure history.

**Resolution:** The plan now adds Oklahoma only as a participation-gated source.
It explicitly defers pre-2010 legacy interpretation and Form 1016 OCR to future
issues.

### Finding 3 - Heavy data could leak into git

**Severity:** resolved before approval

The official workbook is roughly 76 MB, which would be inappropriate for the
repository and could also create CI churn.

**Resolution:** The plan requires raw, normalized, and curated heavy artifacts
under `/mnt/ace/worldenergydata/data/modules/oklahoma_occ/` only. Git will carry
loaders, tests, config, and docs.

### Finding 4 - Schema drift and XLSX parser fragility

**Severity:** resolved before approval

The OCC data dictionary and workbook can change independently. A permissive
parser would silently produce wrong pressure/depth mappings.

**Resolution:** The plan requires dictionary download/hash provenance, required
column validation, fail-closed behavior, alias tests, and quality metadata for
missing pressure/depth rows.

## Residual Risk

The live workbook field names and worksheet shape will only be fully confirmed
during implementation when the 76 MB workbook is downloaded and parsed. The plan
contains the correct control: fail closed with a clear schema error and update
tests/docs from the observed official workbook shape.

## Gate Recommendation

Move [#740](https://github.com/vamseeachanta/worldenergydata/issues/740) to
`status:plan-review` after this plan is committed and pushed. Implementation
must wait for explicit user approval.
