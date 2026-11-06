"""Report evals: every results.json meets the contract; reader files are graded.

The full well-permit eval needs network access for the BSEE file and is run by
the scheduled report-eval job, not here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EVALS = Path(__file__).resolve().parents[2] / "examples" / "report-evals"
ALL = sorted(p.name for p in EVALS.iterdir() if (p / "results.json").exists())


def _run(folder: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(EVALS / folder / "eval.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", timeout=300)


@pytest.mark.parametrize("folder", ALL)
def test_results_json_meets_contract(folder):
    out = _run(folder, "--validate-only")
    assert out.returncode == 0, out.stdout + out.stderr


def test_compare_grades_reader_file(tmp_path):
    """One correct value with the rest missing is PARTIAL (2); a wrong fixed-basis value is FAIL (1)."""
    good = tmp_path / "good.json"
    good.write_text('{"results": [{"id": "permits_all_2005_2026", "value": 2895}]}', encoding="utf-8")
    assert _run("issue-002-gom-well-permits", "--compare", str(good)).returncode == 2
    bad = tmp_path / "bad.json"
    bad.write_text('{"results": [{"id": "script_self_test_passed", "value": false}]}', encoding="utf-8")
    assert _run("issue-002-gom-well-permits", "--compare", str(bad)).returncode == 1
