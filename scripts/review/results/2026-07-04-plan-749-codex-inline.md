# Codex Inline Plan Review: Issue #749 Colorado ECMC pressure-source discovery

**Plan:** `docs/plans/2026-07-04-issue-749-colorado-ecmc-pressure-source-discovery.md`
**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/749
**Reviewer:** Codex inline
**Date:** 2026-07-04
**Posture:** adversarial defect hunt; default non-approval unless source, scope, and interpretation risks are controlled

## Verdict

APPROVE for `status:plan-review`.

This is approval to publish the plan for user review, not approval to implement.
Implementation still requires explicit user approval and `status:plan-approved`.

## Findings Checked

### Finding 1: Plan could accidentally authorize a statewide COGIS scrape

**Risk:** The issue asks for official pressure-bearing source discovery. A broad
FacilityDetail scrape across roughly statewide wells would be a materially
different load and should not be authorized by a discovery plan.

**Disposition:** Controlled. The plan requires a hard sample list, a
`max_requests` cap, a throttle, manifesting, and no statewide iteration mode.
The acceptance criteria require a follow-up issue before any production ingest.

### Finding 2: Pressure semantics could mix incompatible pressure types

**Risk:** FacilityDetail pages contain initial-test data, treatment pressures,
COA/Form 17 conditions, and links to MIT/bradenhead lanes. Treating all pressure
numbers as reservoir or screen evidence would create false Colorado signals.

**Disposition:** Controlled. The plan carries an explicit interpretation table:
initial-test casing/tubing pressure remains only a candidate; treatment
pressure, Form 17/bradenhead, and MIT/Form 21 pressure are excluded unless a
later approved issue changes the contract.

### Finding 3: The plan could over-claim direct-source completeness

**Risk:** The official download catalog proves bulk source existence, but no bulk
Form 5A/initial-test table has been identified. A plan that claims bulk source
availability would be misleading.

**Disposition:** Controlled. The plan states that FacilityDetail/Form 5A is a
candidate official source and that the decision may be automated ingest or ECMC
data request. It does not claim a bulk Form 5A download exists.

### Finding 4: Parser fragility could hide source drift

**Risk:** Public HTML endpoints can change without schema versioning. A brittle
parser could silently misread pressure rows.

**Disposition:** Controlled enough for discovery. The plan requires fixture
tests, structured HTML parsing, source URL lineage, parser row counts, and a
fail-closed decision report. Production-scale resilience is deferred to a
follow-up ingest issue if the endpoint proves viable.

### Finding 5: `/mnt/ace` output could become untracked residue

**Risk:** Live source-scout data belongs under `/mnt/ace`, but the closeout must
not imply repository artifacts include raw HTML samples.

**Disposition:** Controlled. The plan separates repo docs/tests from `/mnt/ace`
raw/parsed/report outputs and requires manifesting.

## Required Review-State Checks

- The GitHub issue should move from `status:needs-plan` to
  `status:plan-review` only after the plan artifact is committed/pushed.
- No `status:plan-approved` label should be applied by the agent.
- Implementation should not begin until the user explicitly approves
  [#749](https://github.com/vamseeachanta/worldenergydata/issues/749).
