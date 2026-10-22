"""Keep current metocean route documentation aligned with the audited sources.

These are documentation checks, not numerical qualification of the backend.
Expected methods and caveats come from metocean-stats v.1.2.0, extreme.py
L13-L137 and L610-L766, and the local wrappers cited in each test.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = (
    ROOT
    / "packages/worldenergydata-metocean/src/worldenergydata/metocean/docs/agent-pack.md"
)


def section(heading):
    """Read one numbered section, excluding historical entries elsewhere."""
    return PACK.read_text(encoding="utf-8").split(heading, 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("heading", ["## 3. Method", "## 9. Dependencies"])
def test_extreme_selection_is_scoped_per_route(heading):
    """Selection: upstream extreme.py L42 and L106; callers: eva.py L101/L165."""
    text = section(heading)
    assert "`return_levels_pot` selects extremes with `pyextremes.get_extremes`" in text
    assert "`return_levels_annual_max` selects calendar-year maxima with pandas" in text
    assert "`idxmax`" in text
    assert "`scipy.stats`" in text
    assert "extreme.py#L13-L137" in text
    assert "statistics/eva.py:L100-L174" in text
    assert "routes called by this module delegate extreme selection to" not in text


@pytest.mark.parametrize("heading", ["## 3. Method", "## 9. Dependencies"])
def test_contours_cite_the_routes_actually_called(heading):
    """Native aux_funcs.py L121-L175 curves have constant joint density."""
    text = section(heading)
    assert "`joint_distribution_Hs_Tp`" in text
    assert "constant-density" in text
    assert "NOT_EVALUATED" in text
    assert "heuristic fallback is removed" in text
    assert "aux_funcs.py#L121-L175" in text
    assert "CMA/contours.py" not in text
    assert "extreme.py#L610-L766" in text


def test_annual_maxima_caveats_are_explicit():
    """Upstream extreme.py L106-L137: no full-year filter; 1 -> 1.6; GEV/GUM.

    The periods are literal upstream behavior, not acceptance limits or
    independently qualified return-level results. No calculation is asserted.
    """
    text = section("## 6. Known failure")
    assert "partial years" in text
    assert "1-year" in text and "1.6 years" in text
    assert "`GEV` and `GUM` only" in text
    assert "extreme.py#L106-L137" in text


def test_lesson_log_identifies_the_superseded_delegation_claim():
    """Historical entries stay intact; the current correction names both routes."""
    text = section("## 7. Lessons")
    assert "Historical entries" in text
    assert "supersedes" in text
    assert "#1354" in text
    assert "`pyextremes.get_extremes`" in text
    assert "`idxmax`" in text
    assert "`virocon` directly" in text


def test_joint_model_parameters_and_supported_methods():
    """Upstream extreme.py L731-L766 defines conditional moments, not Hs shape."""
    text = section("## 9. Dependencies")
    assert "mu(Hs) = a1 + a2" in text
    assert "variance" in text and "b1 + b2" in text
    assert "Tp first" in text
    assert "Weibull 2P Hs marginal via" not in text
    assert "`lonowe()`" in text
