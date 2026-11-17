"""Tests for examples/costing/megaproject_inflation (article "Offshore mega-project cost inflation over time", r2).

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
P = _load("projects")


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


# ---------------------------------------------------------------- r2: project-level view from the curated records
def test_project_rules_hand_values():
    # final over sanction, harness rule: first sanction estimate, final outturn preferred over a final forecast
    trails = [
        {"PROJECT": "A", "CURRENCY": "NOK", "KIND": "sanction_estimate", "VALUE_MM": "120", "STATEMENT_DATE": "2015-02",
         "PROVENANCE": "operator", "CONFIDENCE": "high", "SOURCE_TITLE": "s", "SOURCE_URL": "https://www.equinor.com/a"},
        {"PROJECT": "A", "CURRENCY": "NOK", "KIND": "final_forecast", "VALUE_MM": "100", "STATEMENT_DATE": "2018",
         "PROVENANCE": "operator", "CONFIDENCE": "high", "SOURCE_TITLE": "s", "SOURCE_URL": "u"},
        {"PROJECT": "A", "CURRENCY": "NOK", "KIND": "final_outturn", "VALUE_MM": "90", "STATEMENT_DATE": "2019-10",
         "PROVENANCE": "trade_press", "CONFIDENCE": "low", "SOURCE_TITLE": "s", "SOURCE_URL": "u"},
    ]
    o = P.outturn(trails)
    assert len(o) == 1
    # 90 / 120 - 1 = -0.25 -> -25 %; the outturn (2019) wins over the forecast (2018)
    assert o[0]["change_pct"] == pytest.approx(-25.0) and o[0]["final_year"] == 2019
    assert o[0]["sanction_primary"] and not o[0]["final_primary"]       # trade press, low: ASSUMED
    # market escalation over the project's own years, 2000 to 2002 inclusive (n = 3):
    # 0.25 * 1 + 0.5 * 1.1 + 0.25 * 1.21 - 1 = 0.1025
    idx = {2000: 100.0, 2001: 110.0, 2002: 121.0}
    assert P.market_escalation(idx, 2000, 2002, f.window_escalation) == pytest.approx(0.1025, abs=1e-12)


def test_award_coverage_counts_capital_values_at_low_bound():
    san = [{"PROJECT": "A", "OPERATOR": "o", "FID_YEAR": "2012", "SANCTIONED_CAPEX_USD_MM": "4000",
            "SOURCE_PRIORITY": "press_release", "SOURCE_TITLE": "t", "SOURCE_URL": "u"}]
    aw = [{"PROJECT": "A", "VALUE_BASIS": b, "VALUE_LOW_MM": lo, "VALUE_HIGH_MM": hi, "SOURCE_URL": url}
          for b, lo, hi, url in (("point", "500", "500", "https://www.saipem.com/x"),
                                 ("band", "300", "500", "https://www.offshore-energy.biz/y"),
                                 ("lease_contract", "4600", "4600", "https://www.saipem.com/z"),
                                 ("not_public", "", "", "https://www.saipem.com/w"))]
    c = P.coverage(san, aw)[0]
    # (500 + 300) / 4000 = 20 %; the lease value and the unpublished award are left out; the band is a press source
    assert c["awards_low_mm"] == 800 and c["awards_high_mm"] == 1000 and c["share_low_pct"] == pytest.approx(20.0)
    assert (c["n_awards"], c["n_valued"], c["n_comparable"], c["n_not_public"]) == (4, 3, 2, 1)
    assert not c["awards_primary"]


def test_project_published_numbers(results):
    # consistency check against the curated tables (hashes in project_sources.csv); hand checks in the comments
    pj = results["projects"]
    k, sm = pj["counts"], pj["summary"]
    assert (k["awards"], k["valued"], k["projects"], k["projects_valued"]) == (110, 59, 29, 27)
    assert (k["valued_primary"], k["valued_secondary"]) == (26, 33)
    assert sm["n_cov"] == 28 and sm["share_median"] == pytest.approx(12.08, abs=0.01)
    ml = next(c for c in pj["coverage"] if c["project"].startswith("Martin Linge"))
    assert ml["share_low_pct"] == pytest.approx(100 * 2600 / 4200)          # 61.90 %
    out = {o["project"]: o for o in pj["outturn"]}
    assert sm["n_out"] == 13 and sm["n_comp"] == 11 and sm["n_comp_assumed"] == 10 and sm["n_out_forecast"] == 3
    assert out["Johan Sverdrup Phase 1"]["change_pct"] == pytest.approx(100 * (83000 / 123000 - 1))   # -32.52 %
    assert out["Martin Linge (ex-Hild)"]["change_pct"] == pytest.approx(100.0)                         # 63000 / 31500
    assert out["Goliat"]["change_pct"] == pytest.approx(100 * (50000 / 28000 - 1))                      # +78.57 %
    assert not out["Goliat"]["final_primary"]
    # the repository's qualifiers: Mariner's two figures are both "more than" (not computable); Big Foot's cited article
    # states no final cost (not computable); Peregrino's final is "within" 3,000 (at most -14.29 %, and its words name
    # another original estimate, so ASSUMED); Johan Sverdrup's sanction value is derived (83 + 40), so ASSUMED
    assert not out["Mariner"]["computable"] and not out["Big Foot"]["computable"]
    assert out["Peregrino Phase 2"]["bound"] == "at most" and not out["Peregrino Phase 2"]["final_primary"]
    assert out["Peregrino Phase 2"]["change_pct"] == pytest.approx(100 * (3000 / 3500 - 1))          # -14.29 %
    assert out["Johan Sverdrup Phase 1"]["sanction_qualifier"] == "derived"
    assert out["Gorgon (incl. Jansz-Io)"]["final_qualifier"] == "exact"           # "Chevron-derived" is not a derived value
    assert out["Martin Linge (ex-Hild)"]["final_basis"] == "2021 NOK"
    assert out["Kraken"]["sanction_primary"] and out["Kraken"]["final_primary"]
    assert (pj["boom"]["n"], pj["boom"]["above"], pj["bust"]["n"], pj["bust"]["below"]) == (7, 5, 2, 2)
    assert pj["market_bb_min"] == pytest.approx(-5.0, abs=0.05) and pj["market_bb_max"] == pytest.approx(11.3, abs=0.05)


def test_r2_page_opens_on_the_subject(tmp_path, monkeypatch):
    # owner, 17 Nov 2026 (note 3 on r1): the introduction never says who asked
    b = _load("build_article")
    monkeypatch.setattr(b, "OUT", tmp_path)
    page, errs, facts, _ = b.build("0" * 40, "17 Nov 2026, 00:00 UTC")
    assert not errs
    assert "asked our team" not in page and "Version r2" in page
    assert facts["body_words"] <= 800 and facts["infographic_numbers"] <= 8
