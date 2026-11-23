# Codex Inline Code Review: Issue #749 Colorado ECMC pressure-source discovery

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/749
**Branch:** `feat/colorado-ecmc-source-discovery-749`
**Reviewer:** Codex inline
**Date:** 2026-07-04
**Posture:** adversarial defect hunt; default non-approval unless source,
scope, interpretation, and refresh-output risks are controlled.

## Dispatch Note

This runtime exposed a subagent tool after tool discovery, but that tool's
contract says not to spawn subagents unless the user explicitly asks for
subagents, delegation, or parallel agent work. The code-stage review was
therefore performed inline and this fallback is recorded here.

## Verdict

APPROVE for merge after verification remains green.

## Review Findings

### Finding 1: A generic "Formation Details" page title could be parsed as a formation code

**Risk:** FacilityDetail pages include a section title like "Wellbore And
Formation Details". A naive `Formation\s+...` regex could classify the
formation code as `Details`, corrupting pressure-source context and downstream
field/formation grouping.

**Disposition:** Fixed. A regression fixture now includes the misleading title,
and `facility_detail.py` anchors formation-code extraction on the actual
FacilityDetail formation header:
`Formation {code} Formation Classification`.

### Finding 2: Pressure semantics could leak treatment or integrity pressures into the screen

**Risk:** The source page contains treatment pressure fields and links to
MIT/Form 21 and bradenhead/Form 17 lanes. Mixing these with initial-test casing
or tubing pressure would create false underpressured-screen evidence.

**Disposition:** Controlled. `classify_facility_detail_pressures` marks only
Initial Test Data `CASING_PRESS` and `TUBING_PRESS` as candidate pressure
observations, keeps `underpressured_screen_eligible=False`, and excludes
formation-treatment and integrity lanes. Tests cover all three branches.

### Finding 3: The scout could drift from source discovery into an unapproved statewide crawl

**Risk:** A working FacilityDetail parser could be misused as a statewide scrape
without an approved source-list, throttle, retry/resume policy, or coverage
accounting.

**Disposition:** Controlled for [#749](https://github.com/vamseeachanta/worldenergydata/issues/749).
The config has one `sample_apis` entry, `max_requests: 1`, and a request delay.
The production ingest has been split into follow-up
[#751](https://github.com/vamseeachanta/worldenergydata/issues/751).

### Finding 4: Live output could be unverifiable local residue

**Risk:** Source discovery needs `/mnt/ace` evidence, but raw HTML and parsed
heavy artifacts should not be committed to the repo or left without provenance.

**Disposition:** Controlled. The live run writes raw HTML, parsed JSON/parquet,
and manifest/report JSON under
`/mnt/ace/worldenergydata/data/modules/colorado_ecmc/source_discovery/`.
The repo carries only config, parser/scout code, tests, and docs.

### Finding 5: Interpreter mismatch can break parquet output

**Risk:** The shell's Miniforge `python` is Python 3.13 without `pyarrow`, so
running the scout with `python -m ...` fails at parquet writing. The repo's
pytest/runtime path uses `/usr/bin/python3` 3.12 with `pyarrow`.

**Disposition:** Documented operational caveat, not a code blocker for this
repo. The live source-discovery run was verified with `/usr/bin/python3`, which
matches the test environment. This is consistent with existing Colorado and
Oklahoma pipelines that also write parquet.

## Verification Evidence

- RED: new tests failed initially with missing `facility_detail` and
  `source_discovery` modules.
- REGRESSION RED: fixture with "Formation Details" failed with
  `formation_code == Details`.
- GREEN: focused Colorado source-discovery and existing Colorado tests passed
  after implementation.
- Live scout: one official ECMC FacilityDetail request wrote `/mnt/ace` outputs
  with `parsed_row_count: 11` and `candidate_pressure_count: 2`.
