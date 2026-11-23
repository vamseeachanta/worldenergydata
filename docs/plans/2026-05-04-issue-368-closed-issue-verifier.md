# Plan: Issue #368 — Periodic verifier for recently-closed issues

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/368
**Status:** plan-review
**Tier:** T2 (lightweight script + cron wiring)

## Context
Issue #298 was closed claiming symlink wiring was done, but 9.5 GB of data remained
unreachable. This issue adds a verification script that checks machine-checkable claims
in recently-closed issues.

## Plan

### Task 1 — Write `scripts/hygiene/verify_closed_issues.py`
```python
# Uses gh CLI via subprocess to list issues closed in the last 30 days
# For each issue:
#   - Check if a .planning/plan-approved/NNN.md exists (plan was approved)
#   - Check if an issue comment contains "Implemented in commit" (was implemented)
#   - For file-existence claims (patterns: "X.py", "X.md"), test -f in repo
# Outputs: verified, unverified, or unchecked per issue
# Writes STDOUT summary + JSON to docs/ops/closed-issue-verification-YYYY-MM-DD.json
```

### Task 2 — Add GitHub Actions workflow (optional, defer to separate issue)
Document that this script can be wired to a weekly cron workflow, but scope for this
issue is just the script itself.

### Task 3 — Run once on recently-closed issues
```bash
python3 scripts/hygiene/verify_closed_issues.py --days 30 --repo vamseeachanta/worldenergydata
```
Review and document any unchecked claims from the last 30 days.

### Task 4 — Test the script
`tests/unit/hygiene/test_verify_closed_issues.py`:
- Mock gh CLI output with 3 sample issues (verified, unverified, unchecked)
- Assert output JSON has correct structure
- Assert no subprocess calls in unit mode (use mock)

## Acceptance Criteria
- `scripts/hygiene/verify_closed_issues.py` exists and runs without error
- Outputs summary of recently-closed issues with verification status
- At least a smoke test exists
