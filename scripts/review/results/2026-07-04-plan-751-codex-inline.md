# Adversarial Plan Review - Issue #751 - Codex Inline

## Verdict: APPROVE

The revised plan is approval-ready for the user gate. I found no unresolved
MAJOR defect in the current plan. Implementation must still wait for explicit
user approval and `status:plan-approved`.

## Findings

No blocking findings.

Residual non-blocking risks:

- The plan intentionally leaves the screen adapter optional because the expected
  result is `candidate_only`. If implementation chooses to add the adapter, it
  must use the named `colorado_ecmc_form5a_v1` contract and keep
  `config/underpressured_screen.yml` unchanged unless promotion gates pass.
- The production fetch run remains operationally sensitive because it targets a
  live HTML endpoint. The plan addresses this with source-list caps, throttle,
  retry/backoff, resume, User-Agent, and terminal 403/404 handling; those tests
  are load-bearing during implementation.

## Checked Evidence

- Plan section `Task 1`: verified source-list derivation now uses raw ECMC
  `API` or `API_County` + `API_Seq`, validates `API_Label`, derives API10, and
  keeps API12 null unless a verified source exists.
- Plan section `Task 2`: verified the downloader now requires configured
  User-Agent, request delay, retry/backoff, resume behavior, terminal 403/404
  handling, and rendered page identity checks.
- Plan section `Task 3`: verified parser hardening now requires every Initial
  Test Data block to be enumerated and paired to interval/formation/wellbore
  context, with ambiguous blocks excluded and counted.
- Plan section `Task 4`: verified `TUBING_PRESS` is flowing candidate evidence,
  `CASING_PRESS` remains unverified candidate evidence, no Form 5A candidate
  can receive static gas-column correction unless later mapped to
  `WHP_shut_in`, and the expected issue result is `candidate_only`.
- Plan section `TDD Test List`: verified assertion-level RED tests cover source
  identity, downloader status handling, parser drift, multiple test blocks,
  pressure interpretation, and screen-config non-activation.
- Code evidence rechecked locally:
  - `facility_detail.py` currently maps `TUBING_PRESS` to a flowing pressure
    kind and uses first-match Initial Test parsing, matching the risks the plan
    now requires implementation to fix.
  - `screen.py` currently applies static gas-column correction to all `WHP_`
    pressure kinds, making the plan's shut-in-only promotion gate necessary.
  - `observations.py` raises on unsupported schemas, so any optional Form 5A
    adapter must be explicit.
  - `config/underpressured_screen.yml` documents the shut-in-only correction and
    currently has only the existing Colorado production input.

## Residual Risk

The plan is still a plan: implementation must prove the gates with failing
tests first, must not run an unbounded statewide crawl by default, and must not
activate Colorado Form 5A in the underpressured screen without a reviewed
promotion decision.
