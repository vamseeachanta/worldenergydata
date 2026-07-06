# ABOUTME: TDD suite for per-well economics (issue #849) — rig-day proxy cost,
# ABOUTME: benchmark revenue verbatim, coverage matrix with honest degradation.

from pathlib import Path

import pytest

from worldenergydata.bsee.analysis.cost.models import WaterDepthBand
from worldenergydata.bsee.analysis.cost.regional_loader import RegionalCostLoader
from worldenergydata.field_development import well_economics as we

REPO = Path(__file__).resolve().parents[3]

FIXTURE_DAY_RATES = """
metadata:
  version: "0.0-test"
  hpht_premium_factor: 1.30
regions:
  gom:
    drilling:
      deep:
        2020: 100000
        2022: 120000
        2025: 175000
        confidence: medium
    completion:
      deep:
        2020: 80000
        2025: 125000
        confidence: medium
"""


@pytest.fixture()
def rates_dir(tmp_path):
    d = tmp_path / "cost_data"
    d.mkdir()
    (d / "day_rates.yml").write_text(FIXTURE_DAY_RATES)
    return d


@pytest.fixture()
def loader(rates_dir):
    return RegionalCostLoader(config_dir=rates_dir)


CFG = {
    "region": "gom",
    "hpht_fields": {"big_foot": False},
    "clean_revenue_flags": [""],
    "producing_statuses": ["producing"],
}

FIELD_CTX = {"id": "big_foot", "water_depth_ft": 5200}

A004 = {
    "api": "608124006001",
    "slot": "A004",
    "field_id": "big_foot",
    "spud_date": "2019-03-10",
    "td_date": "2019-03-25",
    "drilling_rig_days": 15,
    "completion_rig_days": 156,
    "first_oil": "2019-06-01",
    "status": "producing",
}

A008 = {
    "api": "608124006800",
    "slot": "A008",
    "field_id": "big_foot",
    "spud_date": "2013-01-22",
    "td_date": "2021-12-02",
    "drilling_rig_days": 118,
    "completion_rig_days": 164,
    "first_oil": "2022-07-01",
    "status": "producing",
}


# 1 — exact unit arithmetic USD -> $MM


def test_cost_units_exact(loader, rates_dir):
    econ = we.compute_well_economics(
        A004,
        FIELD_CTX,
        revenue=(2324.5, ""),
        loader=loader,
        rates_dir=rates_dir,
        cfg=CFG,
    )
    # drilling: 2019 clamps to 2020 rate 100k -> 15 d = 1.5 MUSD… NO:
    # 15 * 100_000 = 1_500_000 USD; completion vintage = first-oil year 2019
    # -> clamps to 2020 rate 80k -> 156 * 80_000 = 12_480_000 USD
    assert econ.drill_cost_usd == 1_500_000
    assert econ.completion_cost_usd == 12_480_000
    assert econ.construction_cost_usd == 13_980_000
    js = econ.to_json()
    assert js["construction_cost_mm_usd"] == 13.98
    assert "construction_cost_usd" not in js  # serialized in $MM only


# 2 — rig-days only; benchmark calendar days cannot reach the cost path


def test_cost_uses_rig_days_never_benchmark_calendar(loader, rates_dir):
    econ = we.compute_well_economics(
        A008,
        FIELD_CTX,
        revenue=(359.1, ""),
        loader=loader,
        rates_dir=rates_dir,
        cfg=CFG,
    )
    # 118 rig-days (NOT the ~3,400-day calendar span 2013→2021)
    drill_cell = next(c for c in econ.rate_cells if c.activity == "drilling")
    assert econ.drill_cost_usd == 118 * drill_cell.usd_per_day
    # structural guard: compute takes a (mm, flag) tuple, never a bench row dict
    with pytest.raises(TypeError):
        we.compute_well_economics(
            A008,
            FIELD_CTX,
            revenue={"drilling_days": 3400, "est_revenue_mm": 359.1},  # type: ignore
            loader=loader,
            rates_dir=rates_dir,
            cfg=CFG,
        )


# 3 — rate year: exact in range, clamped below range (derived from YAML, not literals)


def test_rate_year_exact_in_range_and_clamped_below(loader, rates_dir):
    lo, hi = we.rate_db_year_range(rates_dir)
    assert (lo, hi) == (2020, 2025)
    well_2022 = dict(A004, spud_date="2022-06-01", first_oil="2022-09-01")
    econ = we.compute_well_economics(
        well_2022,
        FIELD_CTX,
        revenue=(1.0, ""),
        loader=loader,
        rates_dir=rates_dir,
        cfg=CFG,
    )
    drill_cell = next(c for c in econ.rate_cells if c.activity == "drilling")
    assert drill_cell.rate_status == "exact"
    assert drill_cell.usd_per_day == 120000
    econ_old = we.compute_well_economics(
        A008,
        FIELD_CTX,
        revenue=(359.1, ""),
        loader=loader,
        rates_dir=rates_dir,
        cfg=CFG,
    )
    old_drill = next(c for c in econ_old.rate_cells if c.activity == "drilling")
    assert old_drill.rate_status == "clamped"  # spud 2013 < 2020
    assert old_drill.year_used == lo


# 4 — completion vintage fallback hierarchy: first-oil year, then TD year


def test_vintage_fallback_hierarchy(loader, rates_dir):
    econ = we.compute_well_economics(
        A008,
        FIELD_CTX,
        revenue=(359.1, ""),
        loader=loader,
        rates_dir=rates_dir,
        cfg=CFG,
    )
    compl = next(c for c in econ.rate_cells if c.activity == "completion")
    assert compl.year_requested == 2022  # first oil 2022-07, NOT TD year 2021
    assert compl.vintage_fallback == "first_oil_year"
    no_fo = dict(A008, first_oil=None)
    econ2 = we.compute_well_economics(
        no_fo, FIELD_CTX, revenue=None, loader=loader, rates_dir=rates_dir, cfg=CFG
    )
    compl2 = next(c for c in econ2.rate_cells if c.activity == "completion")
    assert compl2.year_requested == 2021  # TD year fallback
    assert compl2.vintage_fallback == "td_year_early_biased"


# 5 — ft->m banding via the existing classifier; boundary pinned in both units


def test_depth_band_ft_to_m_boundaries():
    assert we.water_depth_band_from_ft(5200) == WaterDepthBand.DEEP  # 1585 m
    # shallow/mid boundary is 300 m = 984.25 ft (the YAML's "~1,000 ft" is
    # approximate): 984 ft = 299.9 m SHALLOW; 1,000 ft = 304.8 m is MID
    assert we.water_depth_band_from_ft(984) == WaterDepthBand.SHALLOW
    assert we.water_depth_band_from_ft(1000) == WaterDepthBand.MID
    # mid/deep boundary is 1,524 m = 5,000.0 ft exactly; <=1524 m is MID
    assert we.water_depth_band_from_ft(5000) == WaterDepthBand.MID  # 1524.0 m
    assert we.water_depth_band_from_ft(5001) == WaterDepthBand.DEEP  # 1524.3 m
    assert we.water_depth_band_from_ft(4999) == WaterDepthBand.MID
    assert we.water_depth_band_from_ft(10001) == WaterDepthBand.ULTRA_DEEP
    # the trap this pins: feet fed into the metres classifier would misprice
    from worldenergydata.bsee.analysis.cost.models import classify_water_depth_band

    assert classify_water_depth_band(5200) == WaterDepthBand.ULTRA_DEEP  # wrong-unit
    assert we.water_depth_band_from_ft(5200) != classify_water_depth_band(5200)


# 6 — loader contract against the real class + fixture YAML


def test_loader_contract_against_real_class(loader):
    from worldenergydata.bsee.analysis.cost.models import ActivityType

    rate = loader.get_day_rate("gom", WaterDepthBand.DEEP, ActivityType.DRILLING, 2022)
    assert rate == 120000.0
    assert (
        loader.get_day_rate(
            "gom", WaterDepthBand.DEEP, ActivityType.DRILLING, 2022, hpht=True
        )
        == 120000.0 * 1.30
    )


# 7 — golden join against the REAL benchmark CSV (string keys, all 5 tracer wells)


def test_golden_join_real_benchmark_csv():
    csv_path = (
        REPO / "reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv"
    )
    revmap = we.load_revenue_map(csv_path)
    expected = {
        "608124006001": 2324.5,
        "608124006603": 1576.2,
        "608124006200": 910.3,
        "608124006800": 359.1,
        "608124006302": 103.4,
    }
    for api, mm in expected.items():
        rev = revmap.get(api)
        assert rev is not None, f"missing benchmark row for {api}"
        assert rev[0] == mm
        assert rev[1] == ""  # clean flag


# 8 — coverage matrix


def test_coverage_matrix(loader, rates_dir):
    kw = dict(loader=loader, rates_dir=rates_dir, cfg=CFG)
    clean = we.compute_well_economics(A004, FIELD_CTX, revenue=(2324.5, ""), **kw)
    assert clean.coverage_status == "degraded"  # A004 spud 2019 -> clamped rate
    in_range = dict(A004, spud_date="2022-06-01", first_oil="2022-09-01")
    ok = we.compute_well_economics(in_range, FIELD_CTX, revenue=(100.0, ""), **kw)
    assert ok.coverage_status == "indicative"
    assert ok.coverage_ratio == pytest.approx(
        100.0 * 1e6 / ok.construction_cost_usd, rel=1e-6
    )
    flagged = we.compute_well_economics(
        in_range, FIELD_CTX, revenue=(100.0, "partial"), **kw
    )
    assert flagged.coverage_status == "degraded"
    shut_in = we.compute_well_economics(
        dict(in_range, status="shut-in"), FIELD_CTX, revenue=(100.0, ""), **kw
    )
    assert shut_in.coverage_status == "suppressed"
    zero_days = we.compute_well_economics(
        dict(in_range, drilling_rig_days=0, completion_rig_days=0),
        FIELD_CTX,
        revenue=(100.0, ""),
        **kw,
    )
    assert zero_days.coverage_status == "suppressed"
    assert zero_days.construction_cost_usd is None
    no_rev = we.compute_well_economics(in_range, FIELD_CTX, revenue=None, **kw)
    assert no_rev.coverage_status == "suppressed"
    assert no_rev.revenue_mm_usd is None


# 9 — norms chips degradation variants


def test_norms_degradation_variants(tmp_path):
    well = dict(A004, drilling_rig_days=15)
    missing = we.norms_comparison(well, "big_foot", tmp_path / "absent.json")
    assert missing == {"state": "pending"}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert we.norms_comparison(well, "big_foot", bad) == {"state": "pending"}
    partial = tmp_path / "partial.json"
    partial.write_text('{"schema_version": "1.0", "entries": []}')
    assert we.norms_comparison(well, "big_foot", partial) == {"state": "pending"}
    good = tmp_path / "good.json"
    good.write_text(
        """
{"schema_version": "1.0", "entries": [
  {"field_id": "big_foot", "stage": "drill", "metric_id": "drill_days_median",
   "unit": "days", "field_status": "ok",
   "field": {"value": 36.5, "n": 24, "basis": "calendar_days",
             "population": "xlsx_wellbores", "aggregation": "median"},
   "play": {"status": "ok", "method": "leave_one_field_out", "reason": null,
            "metric": {"value": 47.0, "n": 160, "basis": "calendar_days",
                       "population": "xlsx_wellbores", "aggregation": "median"}},
   "country": {"status": "roadmap", "metric": null, "method": null,
               "reason": "x"},
   "delta_play_pct": -22.3, "delta_country_pct": null}
]}
"""
    )
    cmp_ = we.norms_comparison(well, "big_foot", good)
    assert cmp_["state"] == "ok"
    assert cmp_["field_median"] == 36.5
    assert cmp_["play_median"] == 47.0
    assert cmp_["well_vs_field_pct"] == pytest.approx((15 - 36.5) / 36.5 * 100, abs=0.1)


# 10 — no hardcoded monetary literals in the module


def test_no_hardcoded_monetary_literals():
    src = (REPO / "src/worldenergydata/field_development/well_economics.py").read_text()
    import re

    # forbid any 5+ digit numeric literal except the USD->MM divisor
    numerics = set(re.findall(r"(?<![\w.])(\d{5,})(?![\w.])", src)) - {"1_000_000"}
    numerics -= {n for n in numerics if "_" in n}
    assert numerics == set(), f"hardcoded numerics found: {numerics}"
    assert "FT_TO_M = 0.3048" in src


# 11 — hpht is config-gated; mud weight never consulted


def test_hpht_flag_config_gated(loader, rates_dir):
    hot_cfg = dict(CFG, hpht_fields={"big_foot": True})
    well = dict(A004, spud_date="2022-06-01", first_oil="2022-09-01", mud_weight_ppg=99)
    base = we.compute_well_economics(
        well, FIELD_CTX, revenue=None, loader=loader, rates_dir=rates_dir, cfg=CFG
    )
    hot = we.compute_well_economics(
        well, FIELD_CTX, revenue=None, loader=loader, rates_dir=rates_dir, cfg=hot_cfg
    )
    assert hot.drill_cost_usd == pytest.approx(base.drill_cost_usd * 1.30)
    src = (REPO / "src/worldenergydata/field_development/well_economics.py").read_text()
    assert "mud_weight" not in src


# 12 — serialization schema completeness + determinism


def test_economics_schema_and_provenance(loader, rates_dir):
    econ = we.compute_well_economics(
        A004,
        FIELD_CTX,
        revenue=(2324.5, ""),
        loader=loader,
        rates_dir=rates_dir,
        cfg=CFG,
    )
    j1 = econ.to_json()
    j2 = econ.to_json()
    assert j1 == j2
    assert j1["schema_version"] == we.SCHEMA_VERSION
    for cell in j1["rate_cells"]:
        assert {
            "activity",
            "band",
            "year_requested",
            "year_used",
            "usd_per_day",
            "rate_status",
            "vintage_fallback",
            "hpht_applied",
        } <= set(cell)
    assert j1["revenue_source"].startswith("gross")
    assert any("nominal" in n.lower() for n in j1["notes"])  # vintage-mix disclosure
