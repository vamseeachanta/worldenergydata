"""Tests for the WO-Article reconciliation in the completion-days report.

The completion report (``scripts/completion/build_completion_report.py``)
publishes, alongside the observational drilling/completion-days table, a
verification surface that reconciles the live worldenergydata (WED) extract
against the frozen "WO Article, end of 2025" benchmark (World Oil Lower-Tertiary
series, Table 1 — BSEE-derived summary thru Nov 2025).

These tests pin the reconciliation arithmetic to the frozen reference workbook
so the published benchmark cannot silently drift. Numbers are grounded in the
committed workbook (217 wellbore records; 11,124 drilling + 11,354 completion =
22,478 D&C days), NOT recomputed here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "completion"
    / "build_completion_report.py"
)


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("completion_gen_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def recon(gen):
    return gen.compute_reconciliation(gen._load())


def _by_dev(recon):
    return {r["dev"]: r for r in recon["rows"]}


# Expected WED (live extract) per-development D&C days, grouped to WO developments.
_WED_DC = {
    "Anchor": (15, 1825),
    "Big Foot": (38, 3033),
    "Cascade Chinook": (14, 2467),
    "Jack St Malo": (73, 6813),
    "Julia": (9, 1687),
    "Kaskida": (7, 841),
    "North Platte": (14, 971),
    "Shenandoah": (23, 1989),
    "Stones": (22, 2602),
    "Tiber": (2, 250),
}


def test_wo_reference_shape(gen):
    wo = gen.WO_ARTICLE_END_2025
    assert len(wo) == 10
    assert "Buckskin" in wo  # in WO, absent from WED
    assert "Big Foot" not in wo  # in WED, excluded from WO comparison set
    assert wo["Anchor"]["bores"] == 17 and wo["Anchor"]["d_and_c"] == 1825
    assert sum(v["bores"] for v in wo.values()) == 211
    assert sum(v["d_and_c"] for v in wo.values()) == 21944


@pytest.mark.parametrize("dev,expected", _WED_DC.items())
def test_wed_per_development_totals(recon, dev, expected):
    row = _by_dev(recon)[dev]
    assert (row["wed_bores"], row["wed_dc"]) == expected


def test_wed_grand_totals(recon):
    t = recon["wed_total"]
    assert t["drill"] == 11124
    assert t["comp"] == 11354
    assert t["dc"] == 22478
    assert t["bores"] == 217


def test_union_covers_eleven_developments(recon):
    devs = {r["dev"] for r in recon["rows"]}
    assert "Big Foot" in devs and "Buckskin" in devs
    assert len(devs) == 11


def test_buckskin_is_wo_only(recon):
    r = _by_dev(recon)["Buckskin"]
    assert r["status"] == "wo_only"
    assert r["wed_bores"] is None and r["wed_dc"] is None
    assert r["wo_bores"] == 24 and r["wo_dc"] == 2004


def test_big_foot_is_wed_only(recon):
    r = _by_dev(recon)["Big Foot"]
    assert r["status"] == "wed_only"
    assert r["wo_bores"] is None and r["wo_dc"] is None
    assert r["wed_dc"] == 3033


def test_exact_matches_flagged(recon):
    by = _by_dev(recon)
    for dev in ("Cascade Chinook", "Julia", "Kaskida", "Tiber"):
        assert by[dev]["status"] == "match", dev
        assert by[dev]["delta_dc"] == 0, dev


def test_day_deltas_flagged_for_investigation(recon):
    by = _by_dev(recon)
    assert by["Shenandoah"]["delta_dc"] == -357
    assert by["Shenandoah"]["status"] == "investigate"
    assert by["Jack St Malo"]["delta_dc"] == -115
    assert by["Stones"]["delta_dc"] == -23


def test_bore_deltas_with_matching_days(recon):
    # Days reconcile exactly but WO carries extra zero-day sidetrack wellbores.
    by = _by_dev(recon)
    assert by["Anchor"]["delta_dc"] == 0 and by["Anchor"]["delta_bores"] == -2
    assert (
        by["North Platte"]["delta_dc"] == 0 and by["North Platte"]["delta_bores"] == -6
    )


def test_verification_html_renders(gen, recon):
    data = gen._load()
    html_out = gen.render_verification(recon, data)
    assert "WO Article, end of 2025" in html_out
    assert "Shenandoah" in html_out
    assert "<table" in html_out
