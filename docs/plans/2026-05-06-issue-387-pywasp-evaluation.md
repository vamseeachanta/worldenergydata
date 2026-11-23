# Plan: worldenergydata #387 — WRK-688 Evaluate pyWAsP for wind resource assessment

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/387
**Status:** plan-review
**Tier:** T2 (evaluation report + smoke-test environment, no production module)
**Transferred from:** digitalmodel#274 on 2026-05-06 (mis-filed; pyWAsP evaluation belongs in worldenergydata as a Tier-3 wind-resource GTM target — Orsted, Equinor, Dominion CVOW)

## Context

Issue #274 (WRK-688) is an **evaluation** issue, not an implementation: install pyWAsP (DTU Wind Energy / Ørsted Python API for the WAsP wind-flow model), validate the licensing model, smoke-test PyWake (the open-source companion wake model) separately, run at least one worked example (wind climate generalisation OR AEP calculation), and write a go/defer/skip recommendation to `specs/data-sources/pywasp-eval.md` plus update `specs/data-sources/worldenergydata.yaml`.

The deliverable surface lives in **worldenergydata**, not digitalmodel — verified by the issue body's `Repo: ['worldenergydata']` line and the `specs/data-sources/` path convention. The xarray/WindKit alignment with the planned NOAA NDBC metocean module is the integration angle; the wind-energy domain is a Tier-3 GTM target (Orsted, Equinor, Dominion CVOW).

**Stale-flag (mis-filed):** This issue should be in `vamseeachanta/worldenergydata`. The Status field shows `Stage 17: Reclaim (n)` and the WRK ledger shows stages 1–16 done, suggesting the evaluation may have already shipped. Plan must verify-before-execute. Recommend transferring the issue to worldenergydata regardless.

## Plan

### Task 1 — Verify whether the eval has already landed
In the worldenergydata working tree, run `ls specs/data-sources/pywasp-eval.md specs/data-sources/worldenergydata.yaml`. If `pywasp-eval.md` exists with a populated decision section, this issue collapses to a close-as-done — skip to Task 5. If absent or stub-only, proceed to Task 2.

### Task 2 — Stand up the evaluation environment
On `dev-primary`, create a throwaway uv venv (or branch-scoped environment) and run `uv pip install pywasp` and separately `uv pip install py-wake`. Capture: (a) install success/failure, (b) any license-token prompt or runtime check, (c) Python version compatibility. Document license model — pyWAsP's license terms (paid vs. academic) must be in the eval before the integration recommendation can be reasoned about.

### Task 3 — Run one worked example
Pick the simpler of the two: wind-climate generalisation from a sample tab/`.lib` file. Use the example from `https://docs.wasp.dk/pywasp/latest/`. Drive it via a notebook or script and capture (a) input format (xarray Dataset shape), (b) output AEP or generalised wind climate, (c) wall-clock time. If pyWAsP install hits a license wall, fall back to PyWake-only (open source) and document the gap.

### Task 4 — Author the evaluation report
Write `specs/data-sources/pywasp-eval.md` with these sections:
- **License model:** terms, cost, who can use it.
- **WindKit data structures:** xarray compatibility with the planned worldenergydata metocean module — code-level evidence.
- **Worked example output:** screenshots / numerical excerpts.
- **Decision:** integrate (and create implementation WRK) | defer (with trigger conditions) | skip (with rationale).
- **Integration sketch (if "integrate"):** which loader / module / converter would house pyWAsP wrapping, and how it interacts with the Arps decline-curve module (WRK-318) and the metocean NOAA NDBC module.

Update `specs/data-sources/worldenergydata.yaml`'s pyWAsP entry with the eval outcome and the link to the report.

### Task 5 — Close the issue (or follow-on if "integrate")
Post a close comment summarizing the decision. If "integrate", file a fresh worldenergydata issue with the implementation scope and link from the close comment.

## Acceptance Criteria

- [ ] `pip install pywasp` outcome documented (success / license-blocked / failed) on `dev-primary`.
- [ ] PyWake installed and a 5-line smoke test (e.g., import + 2-turbine farm AEP) runs green.
- [ ] At least one worked example from pyWAsP docs reproduced; output captured in the eval report.
- [ ] `specs/data-sources/pywasp-eval.md` exists and contains all five required sections.
- [ ] `specs/data-sources/worldenergydata.yaml` pyWAsP entry updated with the decision.
- [ ] If decision is "integrate", a new implementation issue is filed and linked from #274's close comment.

## Open questions

- pyWAsP's license model is not free; if it is paid-only and dev-primary lacks a token, the evaluation has to terminate at "license requirement assessed: cannot proceed". Confirm with owner whether to provision a token before Task 2 or accept the early-stop outcome.
- Should the evaluation cover xarray-coordinate alignment with the planned NOAA NDBC loader at integration-sketch level only, or do a 1-line proof-of-concept join? The latter is more rigorous; flag for scope decision.
