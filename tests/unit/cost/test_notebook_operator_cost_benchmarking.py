"""Execute the actual notebook source without modifying committed outputs."""

import json
import os
import subprocess
import sys
from pathlib import Path
from runpy import run_path

import pandas as pd


def test_notebook_exposes_tabular_views_with_citations(tmp_path, monkeypatch):
    """Notebook readers can inspect the reported series and its evidence."""
    root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("OPERATOR_COST_REPORT_OUT", str(tmp_path))
    notebook = run_path(str(root / "notebooks/gtm/operator_cost_benchmarking.py"))

    annual = notebook["operator_frame"]
    cohorts = notebook["cohort_frame"]
    outliers = notebook["outlier_frame"]
    citations = notebook["citations_frame"]
    for view in (annual, cohorts, outliers, citations):
        assert isinstance(view, pd.DataFrame)
    assert set(annual["operator"]) == {"Chevron", "Shell", "BP"}
    assert len(annual) == len(citations) == 12
    chevron = annual.loc[
        (annual["operator"] == "Chevron") & (annual["fiscal_year"] == 2023)
    ].iloc[0]
    assert chevron["reported_capex_usd_mm"] == 15829
    assert chevron["yoy_delta_usd_mm"] == 3855
    assert pd.isna(chevron["normalized_yoy_pct"])
    assert cohorts["region"].nunique() >= 2
    pd.testing.assert_frame_equal(cohorts, pd.DataFrame(notebook["facts"]["cohorts"]))
    assert outliers.to_dict("records") == notebook["facts"]["outliers"]
    for row, citation in zip(
        notebook["facts"]["operator_rows"], citations.to_dict("records"), strict=True
    ):
        assert citation == {
            "operator": row["operator"],
            "fiscal_year": row["fiscal_year"],
            **row["provenance"],
        }


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
