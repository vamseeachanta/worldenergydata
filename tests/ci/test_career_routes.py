"""Keep every career packet input under the PR and full contract gates."""

from pathlib import Path

import pytest

from scripts.ci.select_test_targets import to_matrix

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("fast", [False, True])
@pytest.mark.parametrize(
    "changed",
    [
        "scripts/career/build_semiconductor_packet.py",
        "docs/career/semiconductor-packet.json",
        "docs/reports/semiconductor-career-packet.html",
        "tests/career/test_semiconductor_packet.py",
        "tests/ci/test_career_routes.py",
    ],
)
def test_packet_changes_select_contract_tests(changed, fast):
    matrix = to_matrix([changed], ROOT, fast=fast)
    assert matrix["scope"] == "modules"
    targets = [t for shard in matrix["include"] for t in shard["targets"].split()]
    assert targets.count("tests/career/test_semiconductor_packet.py") == 1
