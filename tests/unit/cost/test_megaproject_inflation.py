"""Tests for examples/costing/megaproject_inflation (article "Offshore mega-project cost inflation over time", r1).

Hand-worked values are given in the comments; the last tests are consistency checks of the published numbers against
the saved public data.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

EX = Path(__file__).resolve().parents[3] / "examples" / "costing" / "megaproject_inflation"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"megaproject_{name}", EX / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(EX))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(EX))
    return mod


f = _load("inflation")


def test_spend_profile_hand_values():
    # n = 2: sin(pi/4) = sin(3pi/4), so each year takes 0.5
    assert f.spend_profile(2) == pytest.approx([0.5, 0.5])
    # n = 3: sin(pi/6) = 0.5, sin(pi/2) = 1, sin(5pi/6) = 0.5; sum 2 -> 0.25, 0.5, 0.25
    assert f.spend_profile(3) == pytest.approx([0.25, 0.5, 0.25])
    assert sum(f.spend_profile(8)) == pytest.approx(1.0)


def test_window_escalation_hand_value():
    # index 100, 110, 121; n = 2 from 2000: 0.5 * 100/100 + 0.5 * 110/100 - 1 = 0.05
    idx = {2000: 100.0, 2001: 110.0, 2002: 121.0}
    assert f.window_escalation(idx, 2000, 2) == pytest.approx(0.05, abs=1e-12)
    # n = 3 from 2000: 0.25 * 1 + 0.5 * 1.1 + 0.25 * 1.21 - 1 = 0.1025
    assert f.window_escalation(idx, 2000, 3) == pytest.approx(0.1025, abs=1e-12)
    # only windows that fit inside the data are returned
    assert set(f.escalation_by_fid(idx, 2, last_year=2002)) == {2000, 2001}


def test_cagr_real_and_change_hand_values():
    # 100 -> 121 over two years: 10 % a year
    assert f.cagr({2000: 100.0, 2002: 121.0}, 2000, 2002) == pytest.approx(0.10, abs=1e-12)
    # index 200 against CPI 125 (both 2000 = 100): 160
    assert f.real({2025: 200.0}, {2025: 125.0})[2025] == pytest.approx(160.0)
    assert f.change({"a": 80.0, "b": 100.0}, "a", "b") == pytest.approx(0.25)


def test_percentile_matches_linear_rule():
    # positions (n - 1) p: p50 of 1..4 sits halfway between 2 and 3; p90 at 2.7 -> 3 + 0.7 = 3.7
    assert f.percentile([4, 1, 3, 2], 50) == pytest.approx(2.5)
    assert f.percentile([4, 1, 3, 2], 90) == pytest.approx(3.7)
    with pytest.raises(ValueError):
        f.percentile([], 50)


def test_blend_weights_must_sum_to_one():
    reb = {"a": {2000: 100.0, 2001: 120.0}, "b": {2000: 100.0, 2001: 80.0}}
    assert f.blend(reb, {"a": 0.5, "b": 0.5})[2001] == pytest.approx(100.0)
    with pytest.raises(ValueError):
        f.blend(reb, {"a": 0.6, "b": 0.6})
    assert sum(f.BLEND_WEIGHTS.values()) == pytest.approx(1.0)


def test_annual_means_counts_eleven_months():
    eleven = {f"2025-{m:02d}": 1.0 for m in range(1, 13) if m != 10}
    ten = {f"2026-{m:02d}": 2.0 for m in range(1, 11)}
    out = f.annual_means({**eleven, **ten})
    assert out == {2025: 1.0}


def test_quoted_index_quarters():
    pts = f.read_ucci_quoted(EX.parents[2] / "data" / "modules" / "cost" / "curated" / "cost_component_timeseries.csv")
    q = {p["quarter"]: p["value"] for p in pts}
    assert len(pts) == 13
    assert q["2008Q3"] == 230.0
    assert q["2006Q4"] == 167.0       # "6 months ending 31 Oct 2006"
    assert all(p["url"].startswith("https://") for p in pts)


@pytest.fixture(scope="module")
def results():
    b = _load("build_article")
    return b.compute(b.load())        # load() fails if a saved file does not match its SHA-256


def test_published_numbers(results):
    # consistency check: the values quoted in the article and in PROMPT.md
    assert results["index"]["cpi"]["rise_pct"] == pytest.approx(87.0, abs=0.05)
    assert results["index"]["blend"]["real_cagr_pct"] == pytest.approx(0.79, abs=0.005)
    assert results["esc"]["blend_real_8"]["p50"] == pytest.approx(0.7, abs=0.05)
    assert results["esc"]["blend_real_8"]["p90"] == pytest.approx(22.8, abs=0.05)
    assert results["ucci"]["boom_gap_min"] == pytest.approx(20.5, abs=0.05)
    assert results["ucci"]["boom_gap_max"] == pytest.approx(24.7, abs=0.05)


def test_escalation_windows_cover_full_years_only(results):
    e8 = results["esc"]["blend_real_8"]
    assert e8["fid_first"] == 1997 and e8["fid_last"] == 2018
    assert e8["n_windows"] == 22


def test_set_aside_quarter_left_out(results, tmp_path, monkeypatch):
    # the 2013 Q3 value (229) is set aside: out of Figure 3, Table A5 and every number built on them, while its
    # reference keeps its number (18) and Appendix A names it
    b = _load("build_article")
    monkeypatch.setattr(b, "OUT", tmp_path)        # the build writes its figures here, not into out/
    U = results["ucci"]
    assert [u["quarter"] for u in U["set_aside"]] == ["2013Q3"] and U["set_aside"][0]["value"] == 229.0
    assert "2013Q3" not in {u["quarter"] for u in U["points"]}
    assert len(U["points"]) == 12 and U["boom_n"] == 7
    assert (U["boom_first"], U["boom_last"]) == (2008, 2012)
    assert U["boom_under_max"] == pytest.approx(-17.0, abs=0.05)       # was -15.8 with 2013 Q3; from the unrounded blend
    assert U["boom_two_min"] == pytest.approx(1.0, abs=0.05)           # was -5.1 with 2013 Q3
    d = b.load()
    rf = b.refs(d, results)
    oft = next(r for r in rf if r["url"] == U["set_aside"][0]["url"])
    assert oft["n"] == 18
    page, errs, _, _ = b.build("0" * 40, "17 Nov 2026, 00:00 UTC")
    assert not errs
    assert "2013 Q3 value (229, reference 18) set aside until its source is read again." in page
    assert "<td>2013Q3</td>" not in page
