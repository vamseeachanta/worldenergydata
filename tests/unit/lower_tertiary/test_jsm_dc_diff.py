"""Unit tests for the Jack St Malo D&C over-count diagnostic (#846)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from tests.test_markers import unit

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "lower_tertiary" / "build_jsm_dc_diff.py"
BUILD_PAGES_PATH = PROJECT_ROOT / "scripts" / "build_pages.py"
REPORT_PATH = PROJECT_ROOT / "reports" / "lower_tertiary" / "jsm_dc_diff.html"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_jsm_dc_diff", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unit
def test_per_bore_diff_classifies_completion_only_delta():
    mod = _load_module()
    frozen = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608174001000", "608174002000"],
            "SURF_LEASE_NUM": ["G21245", "G18753"],
            "DRILLING_DAYS": [100, 120],
            "COMPLETION_DAYS": [50, 80],
        }
    )
    candidate = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608174001000", "608174002000"],
            "SURF_LEASE_NUM": ["G21245", "G18753"],
            "DRILLING_DAYS": [100, 120],
            "COMPLETION_DAYS": [50, 110],
        }
    )

    diff = mod.build_per_bore_diff(frozen, candidate)

    row = diff.set_index("api_well_number").loc["608174002000"]
    assert row["drill_delta"] == 0
    assert row["compl_delta"] == 30
    assert row["screening_status"] == "COMPL_DELTA"


@unit
def test_diff_summary_reproduces_headline_totals():
    mod = _load_module()
    diff = pd.DataFrame(
        {
            "api_well_number": ["a", "b"],
            "drill_frozen": [2940, 9],
            "compl_frozen": [3800, 64],
            "drill_cand": [3000, 65],
            "compl_cand": [3900, 82],
            "screening_status": ["BOTH", "BOTH"],
        }
    )

    summary = mod.summarize_diff(diff)

    assert summary == {
        "frozen_bores": 2,
        "candidate_bores": 2,
        "frozen_drilling_days": 2949,
        "frozen_completion_days": 3864,
        "frozen_dc_days": 6813,
        "candidate_drilling_days": 3065,
        "candidate_completion_days": 3982,
        "candidate_dc_days": 7047,
        "drilling_delta": 116,
        "completion_delta": 118,
        "dc_delta": 234,
    }


@unit
def test_sensitivity_annotation_disqualifies_anchor_or_buckskin_regressions():
    mod = _load_module()
    sensitivity = pd.DataFrame(
        {
            "rule": ["current", "current", "bad_anchor", "bad_anchor"],
            "development": ["Anchor", "Buckskin", "Anchor", "Buckskin"],
            "drilling_days": [821, 25, 820, 25],
            "completion_days": [1004, 2031, 1004, 2031],
            "d_and_c_days": [1825, 2056, 1824, 2056],
        }
    )

    annotated = mod.annotate_rule_sensitivity(sensitivity)
    verdicts = annotated.drop_duplicates("rule").set_index("rule")

    assert bool(verdicts.loc["current", "qualified_rule"]) is True
    assert bool(verdicts.loc["bad_anchor", "qualified_rule"]) is False
    assert "Anchor moved from 821/1004" in verdicts.loc["bad_anchor", "disqualifier"]


@unit
def test_build_pages_publishes_jsm_diagnostic_report(tmp_path):
    spec = importlib.util.spec_from_file_location("build_pages", BUILD_PAGES_PATH)
    build_pages = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_pages)
    build_pages.PUBLIC = tmp_path
    build_pages.ASSETS = tmp_path / "assets"

    build_pages.build_lower_tertiary({})

    published = tmp_path / "jsm-dc-diff.html"
    assert published.read_text(encoding="utf-8") == REPORT_PATH.read_text(
        encoding="utf-8"
    )
