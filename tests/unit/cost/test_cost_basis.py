"""Tests for examples/costing/cost_basis (costing part 3 r1: project register and bottom-up cost basis).

Hand-worked values are in the comments. The tests read the repository's curated tables and the BSEE extracts in
examples/costing/cost_basis/data.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

EX = Path(__file__).resolve().parents[3] / "examples" / "costing" / "cost_basis"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"cost_basis_{name}", EX / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(EX))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(EX))
    return mod


B = _load("bottom_up")
R = _load("register")


@pytest.fixture(scope="module")
def res():
    return B.build()


def test_anchor_rig_rate_from_award():
    # 830 USD million backlog over 5 years firm: 830e6 / (5 x 365) = 454,794.52 USD/day
    assert B.rig_rate("Anchor")["usd_per_day"] == pytest.approx(454794.52, abs=0.01)


def test_julia_days_per_well():
    # Julia wellbores spudded 2013 to 2017 with days: drilling 116+37+83+138+52+122 = 548,
    # completion 143+173+29+130+96+100 = 671; 1,219 days over 5 distinct wells = 243.8 days per well
    wd = B.well_days("Julia (initial phase)", 2013, 2016)
    assert (wd["drilling_days"], wd["completion_days"], wd["wells"]) == (548, 671, 5)
    assert wd["per_well"] == pytest.approx(243.8, abs=1e-9)


def test_anchor_days_per_well_from_development_start():
    # Chevron 10-K 2021: first development well in December 2021. Wellbores from then: AP001 96+260 = 356,
    # AP002 82+139 = 221, BP003 171+276 = 447; 1,024 days over 3 wells = 341.33 days per well (SB001 of 2019 is left out)
    wd = B.well_days("Anchor", 2019, 2024)
    assert (wd["wells"], wd["drilling_days"] + wd["completion_days"]) == (3, 1024)
    assert wd["per_well"] == pytest.approx(1024 / 3, rel=1e-12)


def test_lwc_frequency():
    # BSEE loss of well control, FY2007 to FY2017: 6+4+3+2+5+4+9+4+3+1+0 = 41; 2017 Q4: 0; CY2018 to CY2023:
    # 1+2+1+4+5+5 = 18; total 59 over 4,748 wellbores spudded = 0.012426 per wellbore
    lwc = B.lwc_frequency()
    assert lwc["events"] == 59
    assert lwc["periods"] == 18  # FY2007 to FY2017, 2017 Q4, CY2018 to CY2023
    assert lwc["per_wellbore"] == pytest.approx(59 / 4748, rel=1e-12)
    assert lwc["per_wellbore"] == pytest.approx(0.012426, abs=1e-6)


def test_sps_rate_median():
    # Per-tree SPS values: 230/12 = 19.17; 750/41 = 18.29; 750/51 = 14.71; 750/44 = 17.05; 750/48 = 15.63 -> median 17.05
    r = B.award_rates()["sps_per_tree"]
    assert r["n"] == 5
    assert r["median"] == pytest.approx(750 / 44, rel=1e-12)


def test_anchor_hull_cost():
    # 22,000 t x (900 USD/t steel in 2020 + 8,000 USD/t fabrication) = 195.8 USD million
    reg = {r["project"]: r for r in R.build()["rows"]}
    e = B.estimate("Anchor", reg, B.inputs(), B.award_rates(), "base")
    assert e["packages"]["hull"] == pytest.approx(195.8, abs=1e-9)


def test_envelope_brackets_base(res):
    for w in res["worked"]:
        assert w["low"] < w["base"]["total"] < w["high"]


def test_register_counts(res):
    c = res["coverage"]
    assert c["projects"] == c["curated"] + c["staged"] + c["trail_only"]
    assert c["curated"] == 80
    assert c["with_package_split"] <= c["with_award_value"] <= c["with_awards"]


def test_cost_update_rows_are_not_projects(res):
    names = {r["project"] for r in R.build()["rows"]}
    assert not any("cost update" in n or "[UPDATE" in n for n in names)


def test_assumed_inputs_carry_a_date():
    for (key, project), r in B.inputs().items():
        if r["BASIS"] == "ASSUMED":
            assert r["CONFIRM_BY"], (key, project)
            assert float(r["LOW"]) <= float(r["VALUE"]) <= float(r["HIGH"]), (key, project)
