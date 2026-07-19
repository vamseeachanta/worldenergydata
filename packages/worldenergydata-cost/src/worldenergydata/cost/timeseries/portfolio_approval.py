"""Immutable owner-approval constants for the portfolio v2 contract."""

from datetime import datetime, timezone
from pathlib import Path

DECISION_PATH = Path("data/modules/cost/curated/portfolio_reuse_decision.v2.json")
APPROVAL_MARKER = Path(".planning/plan-approved/1040.md")
APPROVED_PLAN_PATH = (
    "docs/plans/2026-07-19-issue-1040-required-assets-award-coverage-replan.html"
)
REVIEWED_PLAN_COMMIT = "5ba42c170099fb5632ccbf054ef974f1f1d429da"
REVIEWED_PLAN_SHA256 = (
    "c1d7a43004f1eb18f054fa9bd82642f0141a15b593f7ca0deecd039de1274f91"
)
PUBLISHED_PLAN_COMMIT = "e8feae4e8f01d99aff95ded09216b6a8efc7b186"
PUBLISHED_PLAN_SHA256 = (
    "9a0eb6dba27bcc58f2b82af991d482b0651a702174a5f4cad0bd93915ec5e5f9"
)
REVIEWED_PLAN_REF = "refs/pull/1052/head"
REVIEWED_TRUST_REF = "refs/codex/approval/1040-reviewed"
PUBLISHED_TRUST_REF = "refs/codex/approval/1040-main"
APPROVAL_MARKER_SHA256 = (
    "31c608d00af652668721295ca4bdaf4425210e45551f44beffc9f96c39444488"
)
APPROVED_AT = datetime(2026, 7, 19, 11, 54, 1, tzinfo=timezone.utc)
APPROVAL_QUOTE = (
    "Approved: #1040 revised plan at 5ba42c1; authorize taxonomy, accounting, "
    "and portfolio reuse; keep allocation scenarios deferred; proceed with PR1 "
    "TDD implementation."
)
ISSUE_URL = "https://github.com/vamseeachanta/worldenergydata/issues/1040"
COMMENT_URL = ISSUE_URL + "#issuecomment-5015609061"
APPROVAL_MARKER_TEXT = (
    "Approved by: user\n"
    f'Approval: "{APPROVAL_QUOTE}"\n'
    "Recorded by: Codex on the user's explicit instruction\n"
    "Date: 2026-07-19\n"
    f"Approved plan commit: {REVIEWED_PLAN_COMMIT}\n"
    f"Issue: {ISSUE_URL}\n"
)
