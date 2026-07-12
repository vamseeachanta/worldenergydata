"""Contract tests for the Lower Tertiary field-performance sidecar
(reports/lower_tertiary/lifecycle/_performance.json).

These guard the machine-readable per-field performance contract that the
life-cycle poster builder consumes: keyed by canonical id (a subset of the
`_facts.json` ids), exactly the seven producing fields, required keys present
and numeric-or-null typed, and the emitter deterministic + non-destructive to
the committed comparison markdown.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.test_markers import unit  # noqa: E402

PERF_PATH = (
    PROJECT_ROOT / "reports" / "lower_tertiary" / "lifecycle" / "_performance.json"
)
FACTS_PATH = PROJECT_ROOT / "reports" / "lower_tertiary" / "lifecycle" / "_facts.json"
MD_PATH = (
    PROJECT_ROOT / "reports" / "lower_tertiary" / "lt_field_performance_comparison.md"
)
EMITTER_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "lower_tertiary"
    / "build_field_performance_comparison.py"
)

PRODUCING_IDS = {
    "jack_st_malo",
    "stones",
    "big_foot",
    "julia",
    "cascade_chinook",
    "shenandoah",
    "anchor",
}

REQUIRED_KEYS = {
    "display",
    "wells",
    "cum_oil_mmbbl",
    "eur_mmbbl",
    "avg_uptime_pct",
    "avg_decline_pct_yr",
    "interventions",
    "npv_mm",
    "breakeven_wti",
    "sens_mm_per_dollar",
    # Economics honesty gate (#971): the joined economics is a life-to-date
    # (not full-cycle) NPV; every field declares its basis + surfacing status.
    "economics_basis",
    "economics_status",
    # Curated reserves (#973): eur_mmbbl is now published/booked recoverable
    # reserves (not the ~2-6.6x-inflated decline-fit sum); each declares source.
    "eur_source",
    "eur_confidence",
}

# Curated recoverable EUR (MMbbl) from config/lt_field_reserves.yml (#973).
# null where no credible public recoverable figure exists (must show pending).
CURATED_EUR = {
    "jack_st_malo": 500,
    "stones": 250,
    "big_foot": 200,
    "anchor": 440,
    "shenandoah": 332,
    "julia": None,
    "cascade_chinook": None,
}

# Above this life-to-date breakeven ($/bbl) the metric is not client-credible
# and is withheld (economics_status == "early_life"). Mirrors the emitter const.
SURFACED_BREAKEVEN_CEILING = 150.0
ECONOMICS_BASIS = "life_to_date_pretax_npv_at_10pct"

# Data-driven expectation (#971): only these two fields have produced enough of
# their EUR and clear the breakeven ceiling to surface a credible life-to-date
# number; the other five are withheld as early-life. Regression guard.
SURFACED_IDS = {"jack_st_malo", "julia"}

NUMERIC_OR_NULL = (
    "wells",
    "cum_oil_mmbbl",
    "eur_mmbbl",
    "avg_uptime_pct",
    "avg_decline_pct_yr",
    "interventions",
    "npv_mm",
    "breakeven_wti",
    "sens_mm_per_dollar",
)


def _load_perf():
    return json.loads(PERF_PATH.read_text())["fields"]


def _facts_ids():
    return {rec["id"] for rec in json.loads(FACTS_PATH.read_text())}


def _load_emitter():
    spec = importlib.util.spec_from_file_location(
        "build_field_performance_comparison", EMITTER_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unit
def test_keys_are_facts_members():
    facts = _facts_ids()
    for fid in _load_perf():
        assert fid in facts, f"{fid} not a member of _facts.json id set"


@unit
def test_exactly_seven_producing_fields():
    assert set(_load_perf()) == PRODUCING_IDS


@unit
def test_required_keys_and_types():
    for fid, rec in _load_perf().items():
        missing = REQUIRED_KEYS - set(rec)
        assert not missing, f"{fid} missing keys: {missing}"
        assert isinstance(rec["display"], str)
        for key in NUMERIC_OR_NULL:
            val = rec[key]
            assert val is None or isinstance(
                val, (int, float)
            ), f"{fid}.{key} not None-or-number: {val!r}"


@unit
def test_jack_st_malo_anchor_values():
    # Values must trace to the committed comparison table.
    jsm = _load_perf()["jack_st_malo"]
    assert jsm["display"] == "Jack St Malo"
    assert jsm["wells"] == 24
    assert jsm["cum_oil_mmbbl"] == 438.8
    assert jsm["eur_mmbbl"] == 500  # curated (Chevron 500+), not decline-fit 1117
    assert jsm["npv_mm"] == -804.5
    assert jsm["breakeven_wti"] == 79.0
    assert jsm["sens_mm_per_dollar"] == 52.3


@unit
def test_economics_basis_and_status_present():
    # Every field declares the life-to-date basis and a valid surfacing status.
    for fid, rec in _load_perf().items():
        assert rec["economics_basis"] == ECONOMICS_BASIS, fid
        assert rec["economics_status"] in {
            "surfaced",
            "early_life",
            "unavailable",
        }, f"{fid}: bad status {rec['economics_status']!r}"


@unit
def test_surfaced_breakeven_under_ceiling():
    # The sanity gate: a SURFACED (non-null) breakeven must be client-credible.
    # NB gate the *surfaced/labeled* value — a life-to-date NPV is legitimately
    # negative, so a "producing => positive NPV" gate would be wrong (#971).
    for fid, rec in _load_perf().items():
        if rec["economics_status"] != "surfaced":
            continue
        be = rec["breakeven_wti"]
        assert be is not None, f"{fid}: surfaced but breakeven is null"
        assert be <= SURFACED_BREAKEVEN_CEILING, (
            f"{fid}: surfaced breakeven {be} exceeds ceiling "
            f"{SURFACED_BREAKEVEN_CEILING}"
        )


@unit
def test_early_life_fields_are_suppressed():
    # Early-life fields withhold every economics *level* (npv, breakeven, and
    # the sensitivity derived from the same suppressed NPV) as null.
    for fid, rec in _load_perf().items():
        if rec["economics_status"] != "early_life":
            continue
        for key in ("npv_mm", "breakeven_wti", "sens_mm_per_dollar"):
            assert rec[key] is None, f"{fid}.{key} should be null when early_life"


@unit
def test_surfaced_set_is_exactly_expected():
    perf = _load_perf()
    surfaced = {
        fid for fid, rec in perf.items() if rec["economics_status"] == "surfaced"
    }
    assert surfaced == SURFACED_IDS, f"surfaced set drifted: {surfaced}"


@unit
def test_jack_st_malo_surfaces_with_status():
    jsm = _load_perf()["jack_st_malo"]
    assert jsm["economics_status"] == "surfaced"
    assert jsm["npv_mm"] == -804.5
    assert jsm["breakeven_wti"] == 79.0


@unit
def test_eur_is_curated_reserves():
    # eur_mmbbl must be the curated published reserve, not the inflated
    # decline-fit sum (#973). null where no credible public figure exists.
    perf = _load_perf()
    for fid, expected in CURATED_EUR.items():
        assert perf[fid]["eur_mmbbl"] == expected, (
            f"{fid}: eur_mmbbl {perf[fid]['eur_mmbbl']} != curated {expected}"
        )
        # Provenance is mandatory for a client-facing reserve number.
        assert perf[fid]["eur_source"], f"{fid}: missing eur_source"
        conf = perf[fid]["eur_confidence"]
        if expected is None:
            assert conf == "none", f"{fid}: pending EUR must be confidence=none"
        else:
            assert conf in {"high", "med_high"}, f"{fid}: weak confidence {conf}"


@unit
def test_null_eur_field_gated_on_breakeven_only():
    # When curated EUR is null the cum/eur fraction can't be evaluated, so the
    # gate falls back to the breakeven ceiling alone: Julia ($95) surfaces,
    # Cascade/Chinook ($338) is withheld (#973).
    perf = _load_perf()
    assert perf["julia"]["eur_mmbbl"] is None
    assert perf["julia"]["economics_status"] == "surfaced"
    assert perf["cascade_chinook"]["eur_mmbbl"] is None
    assert perf["cascade_chinook"]["economics_status"] == "early_life"


@unit
def test_no_inflated_declinefit_eur_leaks():
    # The audited-inflated decline-fit sums must not appear as eur anywhere.
    inflated = {1117, 1324, 1577, 998, 509, 256, 92}
    for fid, rec in _load_perf().items():
        assert rec["eur_mmbbl"] not in inflated, (
            f"{fid}: decline-fit EUR {rec['eur_mmbbl']} leaked"
        )


@unit
def test_emitter_is_deterministic():
    mod = _load_emitter()
    assert mod.build_contract() == mod.build_contract()
    # And byte-identical to what is committed on disk.
    assert mod.build_contract() == PERF_PATH.read_text()


@unit
def test_emitter_leaves_markdown_byte_identical():
    mod = _load_emitter()
    assert mod.build() == MD_PATH.read_text()
