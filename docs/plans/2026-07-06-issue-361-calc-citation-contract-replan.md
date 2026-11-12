# Calculation citation adoption plan

This plan supersedes `2026-05-04-issue-361-calc-citation-contract.md`.
It condenses the approved replacement plan recorded on #361 on 6 July 2026.

## First change: shared citation foundation

Add `worldenergydata.citations` to the core distribution, preserving the pilot's
frozen `Citation`, `CitedValue`, routing fields and error types. Validate required
strings and canonical `wikis/` paths at construction. At resolution, require the
page's `code_id`, `publisher` and `revision` to match exactly. Errors carry the
citation's `code_id`. The section locator remains a human assertion.

Resolve the wiki root in this order: explicit override, `LLM_WIKI_PATH`, then a
bounded search for a sibling `llm-wiki` clone. Support standalone `wikis/` and
overlay `knowledge/wikis/` layouts. Reject invalid explicit configuration instead
of falling back. Preserve canonical clone validation, path redaction and the
resolution-state cache, without deprecated aliases or machine-specific paths.

Include the package in core's setuptools discovery. Add hermetic tests and four
synthetic metadata pages for royalty terms, depth breakpoints, price sources and
NPV methodology. Tests precede implementation and demonstrate fail-closed
metadata checks, path guards, resolver precedence and namespace packaging.
Run existing artifact-ownership tests before and after the change, plus direct
file checks. Live-wiki tests belong with the later registry change.

## Subsequent changes

1. Add the four reviewed standards pages to the wiki through a separate change.
   Metadata uses revision `2026-07` and publishers `BOEM`, `WorldEnergyData`,
   `EIA/FRED` and `WorldEnergyData`, respectively. Merge those pages before
   enabling calculation consumers where the wiki resolves locally.
2. Add registry templates and validated getters. A missing configured page fails
   closed; an unavailable wiki root permits standalone use with a one-time
   `UserWarning` and explicit validation status.
3. Attach sidecars to fiscal royalty terms, depth breakpoints, price sources and
   NPV methodology. Preserve deck rates and existing numeric outputs.
4. Add summary citation keys, workflow assertions and the notebook panel.
   Verify fiscal parity, durable workflows, canonical invocations and live
   resolution after the wiki pages are available.

## Limits

This first change emits no calculation sidecars and adds no registry or live-wiki
dependency. It introduces no engineering constants and changes no calculations.
Pipe schedules and incident taxonomy remain future work. Sliding royalties,
after-tax seams, other reporting surfaces and remote wiki search are outside
this change. No dependency or lock-file update is required.
