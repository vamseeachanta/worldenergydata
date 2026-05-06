# Plan: Issue #352 — CLI examples smoke-test verification

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/352
**Status:** plan-review
**Tier:** T2 (scripted CLI verification + report)
**Depends on:** #355 (DONE — CLI docs and safety classification)
**Related:** #313, #327, #328 (test infra fixes)

## Context
#355 added safety classifications and documentation. This issue verifies which commands
actually work by running bounded smoke checks and producing a verification report.

## Plan

### Task 1 — Write `scripts/audit/cli_smoke_verify.py`
Runs only `bounded-safe` and `fixture-only` commands (no network, no credentials, no data):
```bash
worldenergydata --help
worldenergydata version
worldenergydata info
worldenergydata fdas --help
worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300]" --discount-rate 0.10
worldenergydata fdas calculate-all --cashflows "[-5000,1000,1500,2000]"
worldenergydata fdas classify 5000
worldenergydata lower-tertiary --help
worldenergydata marine-safety --help
worldenergydata bsee --help
# ... all 16 sub-apps with --help
```
Captures exit code, stdout snippet, and stderr snippet per command.

### Task 2 — Run and produce report
```bash
python3 scripts/audit/cli_smoke_verify.py 2>&1
```
Outputs `docs/reports/cli-smoke-report-YYYY-MM-DD.md`:
```markdown
| Command | Safety | Exit | Status |
|---------|--------|------|--------|
| worldenergydata --help | bounded-safe | 0 | ✅ pass |
```

### Task 3 — Classify failures
For each failed command, classify:
- `import_error`: module import broken (route to #278 or #325)
- `missing_subapp`: sub-app not registered (route to #354)
- `broken_command`: registered but crashes (new bug, file issue)
- `data_required`: failed due to missing local data (expected, note)

### Task 4 — Add bounded-safe smoke test to CI
In `tests/unit/cli/test_cli_smoke.py`, invoke `worldenergydata --help` and `worldenergydata info`
via `subprocess.run` and assert exit code 0. These are the only guaranteed-safe CI commands.

## Acceptance Criteria
- `docs/reports/cli-smoke-report-*.md` generated with all 16 sub-apps covered
- `worldenergydata --help`, `info`, and `version` exit 0 (verified in test)
- Each failure classified and cross-referenced to an open issue
