"""Execute the actual notebook source without modifying committed outputs."""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_notebook_runs_and_matches_committed_facts(tmp_path):
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "notebooks/gtm/operator_cost_benchmarking.py"],
        cwd=root,
        env={**os.environ, "OPERATOR_COST_REPORT_OUT": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for name in (
        "operator_cost_benchmarking.html",
        "operator_cost_benchmarking_facts.json",
    ):
        assert (tmp_path / name).read_bytes() == (
            root / "reports/gtm" / name
        ).read_bytes()
    facts = json.loads((tmp_path / "operator_cost_benchmarking_facts.json").read_text())
    assert facts["operators_covered"] == 3
    assert len(facts["operator_rows"]) == 12


def test_report_paths_are_classified_by_structure_contract():
    from scripts.maintenance.verify_repo_structure import load_contract, validate_paths

    root = Path(__file__).resolve().parents[3]
    paths = [
        "reports/gtm/README.md",
        "reports/gtm/operator_cost_benchmarking.html",
        "reports/gtm/operator_cost_benchmarking_facts.json",
    ]
    assert (
        validate_paths(paths, load_contract(root / "config/repo_structure.yml")) == []
    )
