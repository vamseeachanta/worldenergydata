"""Frozen schema primitives for the portfolio cost-map v2 contract."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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
REVIEWED_PLAN_REF = "refs/heads/chore/1040-plan-hotfix"
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


def _require_sha256(value: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("SHA-256 must be lowercase 64-hex")
    return value


class ApprovalEvidence(BaseModel):
    """Traceable record of the explicit human approval gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    approver: Literal["user"]
    approval_quote: str
    approved_at: datetime
    issue_url: str
    issue_comment_url: str
    approved_plan_path: str
    reviewed_plan_commit: str
    reviewed_plan_ref: str
    reviewed_plan_sha256: str
    published_plan_commit: str
    published_plan_sha256: str

    @field_validator("approved_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("approved_at must be UTC")
        return value

    @field_validator("reviewed_plan_commit", "published_plan_commit")
    @classmethod
    def _require_commit(cls, value: str) -> str:
        if re.fullmatch(r"[0-9a-f]{40}", value) is None:
            raise ValueError("commit must be full 40-hex")
        return value

    @field_validator("reviewed_plan_sha256", "published_plan_sha256")
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


class ProjectSourceBinding(BaseModel):
    """Stable curated key bound to one canonical project source row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_project_key: str
    locator_json: str
    locator_sha256: str
    source_row_sha256: str
    active: bool

    @field_validator("source_project_key")
    @classmethod
    def _require_source_key(cls, value: str) -> str:
        if re.fullmatch(r"src-prj-(?:000001|[0-9a-f]{32})", value) is None:
            raise ValueError("invalid source project key")
        return value

    @field_validator("locator_sha256", "source_row_sha256")
    @classmethod
    def _require_hash(cls, value: str) -> str:
        return _require_sha256(value)


class ProjectIdentity(BaseModel):
    """Persistent project identity independent of mutable source content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str
    source_project_key: str
    display_label: str
    state: Literal["active", "tombstoned"]
    active: bool
    aliases_json: str
    validation_group_id: str
    created_source_sha256: str
    migration_note: str
    no_reuse: bool

    @field_validator("project_id")
    @classmethod
    def _require_project_id(cls, value: str) -> str:
        if re.fullmatch(r"prj-(?:000001|[0-9a-f]{32})", value) is None:
            raise ValueError("invalid project ID")
        return value

    @field_validator("source_project_key")
    @classmethod
    def _require_source_key(cls, value: str) -> str:
        return ProjectSourceBinding._require_source_key(value)

    @field_validator("created_source_sha256")
    @classmethod
    def _require_hash(cls, value: str) -> str:
        return _require_sha256(value)

    @field_validator("aliases_json")
    @classmethod
    def _require_canonical_aliases(cls, value: str) -> str:
        aliases = json.loads(value)
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) for alias in aliases
        ):
            raise ValueError("aliases_json must encode a string array")
        if json.dumps(aliases, ensure_ascii=False, separators=(",", ":")) != value:
            raise ValueError("aliases_json must use canonical JSON")
        return value

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "ProjectIdentity":
        if self.active != (self.state == "active"):
            raise ValueError("project state and active flag disagree")
        if not self.no_reuse or not self.display_label or not self.validation_group_id:
            raise ValueError("project identity requires no-reuse and nonempty labels")
        return self


class AwardSourceBinding(BaseModel):
    """Stable curated key bound to one canonical award source row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_award_key: str
    locator_json: str
    locator_sha256: str
    source_row_sha256: str
    active: bool

    @field_validator("source_award_key")
    @classmethod
    def _require_source_key(cls, value: str) -> str:
        if re.fullmatch(r"src-awd-(?:00000[12]|[0-9a-f]{32})", value) is None:
            raise ValueError("invalid source award key")
        return value

    @field_validator("locator_sha256", "source_row_sha256")
    @classmethod
    def _require_hash(cls, value: str) -> str:
        return _require_sha256(value)


class AwardIdentity(BaseModel):
    """Persistent award identity linked to one persistent project."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    award_id: str
    source_award_key: str
    project_id: str
    display_label: str
    state: Literal["active", "tombstoned"]
    active: bool
    aliases_json: str
    validation_group_id: str
    created_source_sha256: str
    migration_note: str
    no_reuse: bool

    @field_validator("award_id")
    @classmethod
    def _require_award_id(cls, value: str) -> str:
        if re.fullmatch(r"awd-(?:00000[12]|[0-9a-f]{32})", value) is None:
            raise ValueError("invalid award ID")
        return value

    @field_validator("source_award_key")
    @classmethod
    def _require_source_key(cls, value: str) -> str:
        return AwardSourceBinding._require_source_key(value)

    @field_validator("project_id")
    @classmethod
    def _require_project_id(cls, value: str) -> str:
        return ProjectIdentity._require_project_id(value)

    @field_validator("created_source_sha256")
    @classmethod
    def _require_hash(cls, value: str) -> str:
        return _require_sha256(value)

    @field_validator("aliases_json")
    @classmethod
    def _require_canonical_aliases(cls, value: str) -> str:
        return ProjectIdentity._require_canonical_aliases(value)

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "AwardIdentity":
        if self.active != (self.state == "active"):
            raise ValueError("award state and active flag disagree")
        if not self.no_reuse or not self.display_label or not self.validation_group_id:
            raise ValueError("award identity requires no-reuse and nonempty labels")
        return self


class RequirementIdentity(BaseModel):
    """Persistent requirement identity seeded from the v1 pilot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    requirement_id: str
    source_requirement_key: str
    project_id: str
    work_package_slug: str
    locator_json: str
    locator_sha256: str
    state: Literal["active", "tombstoned"]
    active: bool
    validation_group_id: str
    no_reuse: bool
    migration_note: str

    @field_validator("requirement_id")
    @classmethod
    def _require_requirement_id(cls, value: str) -> str:
        if re.fullmatch(r"req-[0-9]{6}", value) is None:
            raise ValueError("invalid requirement ID")
        return value

    @field_validator("source_requirement_key")
    @classmethod
    def _require_source_key(cls, value: str) -> str:
        if re.fullmatch(r"src-req-[0-9]{6}", value) is None:
            raise ValueError("invalid source requirement key")
        return value

    @field_validator("project_id")
    @classmethod
    def _require_project_id(cls, value: str) -> str:
        return ProjectIdentity._require_project_id(value)

    @field_validator("locator_sha256")
    @classmethod
    def _require_hash(cls, value: str) -> str:
        return _require_sha256(value)

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "RequirementIdentity":
        if self.active != (self.state == "active"):
            raise ValueError("requirement state and active flag disagree")
        if (
            not self.no_reuse
            or not self.work_package_slug
            or not self.validation_group_id
        ):
            raise ValueError(
                "requirement identity requires no-reuse and nonempty labels"
            )
        return self


def _validate_exact_evidence(decision: PortfolioReuseDecision) -> None:
    expected = {
        "approval_quote": APPROVAL_QUOTE,
        "issue_url": ISSUE_URL,
        "issue_comment_url": COMMENT_URL,
        "approved_plan_path": APPROVED_PLAN_PATH,
        "reviewed_plan_commit": REVIEWED_PLAN_COMMIT,
        "reviewed_plan_ref": REVIEWED_PLAN_REF,
        "reviewed_plan_sha256": REVIEWED_PLAN_SHA256,
        "published_plan_commit": PUBLISHED_PLAN_COMMIT,
        "published_plan_sha256": PUBLISHED_PLAN_SHA256,
    }
    for field, value in expected.items():
        if getattr(decision.approval, field) != value:
            raise ValueError(f"approval evidence mismatch: {field}")
    if decision.approval.approved_at != APPROVED_AT:
        raise ValueError("approval evidence mismatch: approved_at")


def _git(root: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", *arguments], cwd=root, check=True, capture_output=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("approved plan history unavailable") from error


def _validate_plan_blobs(root: Path, approval: ApprovalEvidence) -> None:
    reviewed_ref = (
        f"refs/remotes/origin/{approval.reviewed_plan_ref.removeprefix('refs/heads/')}"
    )
    _git(root, "cat-file", "-e", f"{approval.reviewed_plan_commit}^{{commit}}")
    _git(
        root, "merge-base", "--is-ancestor", approval.reviewed_plan_commit, reviewed_ref
    )
    reviewed = _git(
        root, "show", f"{approval.reviewed_plan_commit}:{approval.approved_plan_path}"
    )
    if sha256(reviewed).hexdigest() != approval.reviewed_plan_sha256:
        raise ValueError("reviewed plan blob hash mismatch")

    published = approval.published_plan_commit
    _git(root, "cat-file", "-e", f"{published}^{{commit}}")
    _git(root, "merge-base", "--is-ancestor", published, "HEAD")
    blob = _git(root, "show", f"{published}:{approval.approved_plan_path}")
    marker = _git(root, "show", f"{published}:{APPROVAL_MARKER}")
    if sha256(blob).hexdigest() != approval.published_plan_sha256:
        raise ValueError("published plan blob hash mismatch")
    if sha256(marker).hexdigest() != APPROVAL_MARKER_SHA256:
        raise ValueError("published approval marker hash mismatch")


def validate_decision_evidence(payload: object, marker: str) -> PortfolioReuseDecision:
    """Validate exact approval fields without claiming external authorship proof."""

    decision = PortfolioReuseDecision.model_validate(payload)
    _validate_exact_evidence(decision)
    if marker != APPROVAL_MARKER_TEXT:
        raise ValueError("approval marker does not exactly match owner decision")
    return decision


def validate_owner_decision(root: Path) -> PortfolioReuseDecision:
    """Validate the checked-in decision and its local approval marker."""

    payload = json.loads((root / DECISION_PATH).read_text(encoding="utf-8"))
    marker = (root / APPROVAL_MARKER).read_text(encoding="utf-8")
    decision = validate_decision_evidence(payload, marker)
    if (
        decision.taxonomy,
        decision.accounting,
        decision.portfolio_reuse,
        decision.allocation_scenarios,
    ) != ("approved", "approved", "approved", "deferred"):
        raise ValueError("owner decision does not match approved scope")
    _validate_plan_blobs(root, decision.approval)
    return decision
