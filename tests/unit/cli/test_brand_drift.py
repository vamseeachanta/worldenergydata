"""Tests for the wed brand-token drift guard (#908 / wh#3401).

Verifies hex normalisation, :root parsing, the declare-navy-then-must-match rule
(non-navy pages exempt), and that the real reports tree is consistent with
reports/capabilities/assets/tokens.css.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_GUARD = _ROOT / "scripts" / "enforcement" / "check_brand_drift.py"


def _load():
    spec = importlib.util.spec_from_file_location("wed_brand_drift", _GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _load()
CANON = {"navy": "#0b3d91", "teal": "#0f8a7e", "ink": "#13233f"}


def test_norm_expands_and_lowercases():
    assert G.norm("#FFF") == "#ffffff"
    assert G.norm("#0B3D91") == "#0b3d91"


def test_root_tokens_parses_first_root():
    toks = G.root_tokens(":root{--navy:#0B3D91;--teal:#0f8a7e}")
    assert toks == {"navy": "#0b3d91", "teal": "#0f8a7e"}


def test_matching_navy_page_has_no_violation():
    pages = {"ok.html": {"navy": "#0b3d91", "teal": "#0f8a7e", "warn": "#b45309"}}
    assert G.find_violations(CANON, pages) == []


def test_drifted_navy_page_is_flagged():
    pages = {"bad.html": {"navy": "#0b2545", "teal": "#0f8a7e"}}
    v = G.find_violations(CANON, pages)
    assert v and v[0][0] == "bad.html" and v[0][1] == "navy"


def test_non_navy_page_is_exempt():
    pages = {"dark.html": {"bg": "#0f1117", "ink": "#e6edf3"}}
    assert G.find_violations(CANON, pages) == []


def test_real_reports_tree_is_consistent():
    assert G.main() == 0
