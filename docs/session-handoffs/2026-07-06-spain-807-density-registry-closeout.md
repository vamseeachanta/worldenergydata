# worldenergydata #807 Density Registry Handoff

Date: 2026-07-06

## Current State

- Issue: https://github.com/vamseeachanta/worldenergydata/issues/807 is OPEN and remains `status:plan-approved`.
- Do not close #807 yet: strict source gaps remain for fields without accepted conversion-grade density/API evidence.
- Latest implementation PR: https://github.com/vamseeachanta/worldenergydata/pull/885 is MERGED to `main`.
- Latest merge commit: `4ae506fa3f00dc7a6456e89bd008a3efa7d256c2`.
- #809 Spain CORES scheduler work is complete and should not be redone.

## What Landed In This Continuation

Three evidence-retention slices were merged to `main`:

- https://github.com/vamseeachanta/worldenergydata/pull/881 retained Ayoluengo as an evidence-only source lead.
- https://github.com/vamseeachanta/worldenergydata/pull/884 retained Albatros and Gaviota as OGJ evidence-only source leads.
- https://github.com/vamseeachanta/worldenergydata/pull/885 retained Viura (1) as an evidence-only condensate-cut source lead.

The current registry keeps those fields fail-closed:

- `accepted_for_conversion=false`
- `bbl_per_tonne=null`
- no API/density factor accepted for conversion
- still listed in `source_gap_fields`

## Source Treatment

The accepted rule for this slice was conservative: retain source leads when they are useful for future research, but do not convert tonnes to barrels unless the source provides a defensible density/API or direct tonnes-to-barrels basis.

Evidence-only sources now retained:

- Ayoluengo: BOE-style public evidence retained as a broad API/source lead, not a conversion factor.
- Albatros and Gaviota: OGJ production-survey API leads retained as industry technical article evidence, not conversion factors.
- Viura (1): Prospex/H&P research note records a minor condensate cut of `3.5 stb/mmcf`, but condensate cut is not crude density/API and is not a tonnes-to-barrels basis.

## Verification Evidence

Local verification for the latest Viura slice before PR #885:

- TDD RED: the targeted test failed with `KeyError: 'viura1'` before the registry entry.
- Adjacent Spain pytest selection: 89 passed.
- `git diff --check origin/main...HEAD` passed.
- Density registry parsed with `python -m json.tool`.
- `black --check` and `isort --check-only` passed on the touched test file.
- `scripts/legal/legal-sanity-scan.sh` reported no files to scan after commit.
- Focused Bandit on the touched test file passed.

GitHub CI for PR #885 passed before merge:

- PR Validation checks passed.
- Lint passed.
- Type Check passed.
- Security Scan passed.
- Documentation passed.
- Build Package passed.
- Test (PR gate) passed.
- Domain unit-spain and aggregate domain checks passed.
- GitGuardian Security Checks passed.

## Issue Trace

Implemented issue comments were posted on #807:

- https://github.com/vamseeachanta/worldenergydata/issues/807#issuecomment-4900128612
- https://github.com/vamseeachanta/worldenergydata/issues/807#issuecomment-4900150050

## Cleanup State

Task-scoped scratch files were removed:

- `/tmp/prospex-viura-2025-10-22.pdf`
- `/tmp/prospex-viura-2025-10-22.txt`
- `/tmp/worldenergydata-crude-density-factors-viura.jsoncheck`

Expected unrelated residue left untouched:

- Existing stash in `/mnt/local-analysis/worldenergydata`: `stash@{0}: On main: wed stale pre-reorg dirty tree (recoverable) 2026-06-26`.
- Existing cleanup trash: `/mnt/local-analysis/.cleanup-trash/20260616-095709`.
- Existing local squash-merged branches with deleted remotes, including `feature/spain-807-viura-condensate-lead`; do not force-delete without operator approval.

## Recommended Next Step

Continue #807 by searching for conversion-grade direct-source evidence for the remaining strict source gaps:

- `Albatros`
- `Ayoluengo`
- `Gaviota`
- `Viura (1)`

Only accept a conversion factor when a direct source provides density/API or an auditable tonnes-to-barrels basis. Otherwise, keep the field fail-closed and retain the best source lead as non-conversion evidence.

Before the next implementation slice:

- Check active PRs and parallel work.
- Confirm #807 remains the approved issue.
- Keep TDD red/green discipline.
- Run adversarial source-policy and behavior review.
- Run targeted tests, legal/security scan, and CI.
- Comment on #807 for every implemented slice.
