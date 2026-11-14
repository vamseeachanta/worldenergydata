# ABOUTME: Routing guard for the reproducible EDA report replay contract.
# ABOUTME: Each EDA script or example artifact must select tests/unit/eda.

"""EDA contract routes in scripts/ci/select_test_targets.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))

from select_test_targets import select, select_fast, to_matrix  # noqa: E402

EDA_CONTRACT_PATHS = [
    "scripts/eda/report.py",
    "docs/examples/eda/README.md",
    "docs/examples/eda/manifest.json",
    "docs/examples/eda/report.md",
]


@pytest.mark.parametrize("fast", [False, True])
@pytest.mark.parametrize("path", EDA_CONTRACT_PATHS)
def test_eda_contract_paths_select_unit_eda(path, fast):
    result = (select_fast if fast else select)([path], REPO_ROOT)
    assert result["scope"] == "modules"
    assert result["xdist"].count("tests/unit/eda") == 1
    matrix = to_matrix([path], REPO_ROOT, fast=fast)
    assert any(
        shard["name"] == "unit-eda" and shard["targets"] == "tests/unit/eda"
        for shard in matrix["include"]
    )
