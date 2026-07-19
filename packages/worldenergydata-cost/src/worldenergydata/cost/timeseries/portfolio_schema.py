"""Frozen schema primitives for the portfolio cost-map v2 contract."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

DECISION_PATH = Path("data/modules/cost/curated/portfolio_reuse_decision.v2.json")
APPROVAL_MARKER = Path(".planning/plan-approved/1040.md")
APPROVED_PLAN_PATH = (
    "docs/plans/2026-07-19-issue-1040-required-assets-award-coverage-replan.html"
)
APPROVED_PLAN_COMMIT = "5ba42c170099fb5632ccbf054ef974f1f1d429da"
APPROVED_PLAN_SHA256 = (
    "c1d7a43004f1eb18f054fa9bd82642f0141a15b593f7ca0deecd039de1274f91"
)
APPROVED_AT = datetime(2026, 7, 19, 11, 54, 1, tzinfo=timezone.utc)
APPROVAL_QUOTE = (
    "Approved: #1040 revised plan at 5ba42c1; authorize taxonomy, accounting, "
    "and portfolio reuse; keep allocation scenarios deferred; proceed with PR1 "
    "TDD implementation."
)
ISSUE_URL = "https://github.com/vamseeachanta/worldenergydata/issues/1040"
COMMENT_URL = ISSUE_URL + "#issuecomment-5015609061"


class ApprovalEvidence(BaseModel):
    """Traceable record of the explicit human approval gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    approver: Literal["user"]
    approval_quote: str
    approved_at: datetime
    issue_url: str
    issue_comment_url: str
    approved_plan_path: str
    approved_plan_commit: str
    approved_plan_sha256: str

    @field_validator("approved_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("approved_at must be UTC")
        return value

    @field_validator("approved_plan_commit")
    @classmethod
    def _require_commit(cls, value: str) -> str:
        if re.fullmatch(r"[0-9a-f]{40}", value) is None:
            raise ValueError("commit must be full 40-hex")
        return value

    @field_validator("approved_plan_sha256")
    @classmethod
    def _require_sha256(cls, value: str) -> str:
        if re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("plan SHA-256 must be full 64-hex")
        return value


class PortfolioReuseDecision(BaseModel):
    """Independent owner decisions; scenario reuse remains deferred."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["portfolio-reuse-decision.v2"]
    taxonomy: Literal["approved", "deferred", "rejected"]
    accounting: Literal["approved", "deferred", "rejected"]
    portfolio_reuse: Literal["approved", "deferred", "rejected"]
    allocation_scenarios: Literal["approved", "deferred", "rejected"]
    approval: ApprovalEvidence


def _validate_exact_evidence(decision: PortfolioReuseDecision) -> None:
    expected = {
        "approval_quote": APPROVAL_QUOTE,
        "issue_url": ISSUE_URL,
        "issue_comment_url": COMMENT_URL,
        "approved_plan_path": APPROVED_PLAN_PATH,
        "approved_plan_commit": APPROVED_PLAN_COMMIT,
        "approved_plan_sha256": APPROVED_PLAN_SHA256,
    }
    for field, value in expected.items():
        if getattr(decision.approval, field) != value:
            raise ValueError(f"approval evidence mismatch: {field}")
    if decision.approval.approved_at != APPROVED_AT:
        raise ValueError("approval evidence mismatch: approved_at")


def validate_owner_decision(root: Path) -> PortfolioReuseDecision:
    """Validate the checked-in decision and its local approval marker."""

    payload = json.loads((root / DECISION_PATH).read_text(encoding="utf-8"))
    decision = PortfolioReuseDecision.model_validate(payload)
    _validate_exact_evidence(decision)
    if (
        decision.taxonomy,
        decision.accounting,
        decision.portfolio_reuse,
        decision.allocation_scenarios,
    ) != ("approved", "approved", "approved", "deferred"):
        raise ValueError("owner decision does not match approved scope")
    marker = (root / APPROVAL_MARKER).read_text(encoding="utf-8")
    for evidence in (APPROVAL_QUOTE, APPROVED_PLAN_COMMIT, ISSUE_URL):
        if evidence not in marker:
            raise ValueError("approval marker does not match owner decision")
    return decision
