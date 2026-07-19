"""Approval-lineage tests that start without local historical refs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from worldenergydata.cost.timeseries.portfolio_schema import (
    DECISION_PATH,
    PUBLISHED_TRUST_REF,
    REVIEWED_TRUST_REF,
    validate_owner_decision,
)

ROOT = Path(__file__).resolve().parents[3]


def test_depth_one_main_clone_hydrates_only_named_approval_refs(
    tmp_path: Path,
) -> None:
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", "main", remote, clone],
        check=True,
        capture_output=True,
    )
    shutil.copy2(ROOT / DECISION_PATH, clone / DECISION_PATH)

    validate_owner_decision(clone)

    refs = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/codex/approval"],
        cwd=clone,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert refs == [PUBLISHED_TRUST_REF, REVIEWED_TRUST_REF]
