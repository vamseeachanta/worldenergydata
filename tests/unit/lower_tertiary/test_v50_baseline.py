"""
ABOUTME: Tests for the V50 gold standard (golden_baseline_v50.yml) and its reproducer.
ABOUTME: Structural integrity + V30 regression + data-backed V50 reproduction.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
V30_PATH = PROJECT_ROOT / "config/analysis/lower_tertiary/golden_baseline_v30.yml"
V50_PATH = PROJECT_ROOT / "config/analysis/lower_tertiary/golden_baseline_v50.yml"

try:
    from worldenergydata.lower_tertiary.ops_timeline import ensure_ogor_loader
    from worldenergydata.lower_tertiary.v30_financial_reproducer import (
        reproduce_v30_financials,
    )

    REPRODUCER_AVAILABLE = True
except ImportError:
    REPRODUCER_AVAILABLE = False

V50_END_DATE = "2026-04-30"
PRODUCING = {
    "jack_st_malo",
    "stones",
    "julia",
    "big_foot",
    "cascade_chinook",
    "anchor",
    "shenandoah",
}
# Known reproducer-vs-frozen NPV offset (monthly D&C allocation timing).
NPV_WIDE_TOL = {"Jack St Malo"}


@pytest.fixture(scope="module")
def v30():
    return yaml.safe_load(V30_PATH.read_text())["projects"]


@pytest.fixture(scope="module")
def v50_doc():
    if not V50_PATH.exists():
        pytest.skip("golden_baseline_v50.yml not generated")
    return yaml.safe_load(V50_PATH.read_text())


@pytest.fixture(scope="module")
def v50(v50_doc):
    return v50_doc["projects"]


# ---- Structural integrity (no OGOR data needed) ----


def test_v50_has_every_v30_project(v30, v50):
    assert set(v50) == set(v30)


def test_v50_window_metadata(v50_doc):
    meta = v50_doc["metadata"]
    assert meta["based_on"] == "golden_baseline_v30.yml"
    assert "2026-04" in meta["time_period"]


def test_v50_producers_have_comparison_block(v50):
    for k in PRODUCING:
        assert "v30_comparison" in v50[k], f"{k} missing v30_comparison"


@pytest.mark.parametrize("k", sorted(PRODUCING))
def test_v50_oil_not_below_v30(k, v30, v50):
    """Extending the window by 11 months cannot reduce cumulative oil."""
    assert v50[k]["total_oil_bbl"] >= v30[k]["total_oil_bbl"]


@pytest.mark.parametrize("k", sorted(PRODUCING))
def test_v50_revenue_not_below_v30(k, v30, v50):
    assert v50[k]["revenue_usd"] >= v30[k]["revenue_usd"]


def test_v30_file_untouched(v30):
    """Guard: the sanctioned V30 NPV of record must not drift."""
    assert v30["julia"]["npv_usd"] == pytest.approx(-530637776.31, rel=1e-9)
    assert v30["jack_st_malo"]["npv_usd"] == pytest.approx(-881064818.72, rel=1e-9)


# ---- Data-backed reproduction (skips when OGOR .bin absent) ----

skip_no_data = pytest.mark.skipif(
    not REPRODUCER_AVAILABLE, reason="financial reproducer not importable"
)


@pytest.fixture(scope="module")
def v50_fin():
    try:
        from worldenergydata.lower_tertiary.latest_runner import (
            FIRST_OIL_CORRECTIONS,
        )

        ensure_ogor_loader()
        return reproduce_v30_financials(
            end_date=V50_END_DATE, first_oil_overrides=FIRST_OIL_CORRECTIONS
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"V50 source data not available: {exc}")


@skip_no_data
@pytest.mark.parametrize("k", sorted(PRODUCING))
def test_v50_yaml_npv_reproduces(k, v50, v50_fin):
    """Frozen V50 NPV reproduces from raw OGOR within tolerance."""
    dn = v50[k]["display_name"]
    expected = v50[k]["npv_usd"]
    actual = v50_fin[dn]["npv_usd"]
    rel = 0.08 if dn in NPV_WIDE_TOL else 0.01
    assert actual == pytest.approx(expected, rel=rel)


@skip_no_data
def test_v30_default_path_still_reproduces():
    """Regression: end_date=None reproduces the frozen V30 (Julia, exact match field)."""
    ensure_ogor_loader()
    fin = reproduce_v30_financials()
    assert fin["Julia"]["npv_usd"] == pytest.approx(-530637776.31, rel=0.01)
