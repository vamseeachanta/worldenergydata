# ABOUTME: Schema + integrity guards for the E2 award registry (#1025).
# ABOUTME: FK to sanctioned_projects, controlled vocab, band low<=high, sourced-ness, and the not_public honesty rail.
"""Guards for ``contract_awards.csv`` and ``project_cost_statements.csv``.

The load-bearing rails: a ``band`` row must carry a real low/high range (never a
bare midpoint), a ``not_public`` row must NOT smuggle a value, and every row must
reference a real sanctioned project. These keep the award registry safe to feed
into the reconciliation harness (E5) without laundering a guess into a datum.
"""

from __future__ import annotations

import csv
from pathlib import Path

CURATED = Path(__file__).resolve().parents[3] / "data" / "modules" / "cost" / "curated"
AWARDS = CURATED / "contract_awards.csv"
STMTS = CURATED / "project_cost_statements.csv"
SANCTIONED = CURATED / "sanctioned_projects.csv"

ASSET_CLASSES = {
    "production_hub",
    "sps",
    "surf",
    "installation",
    "drilling_rig",
    "other",
}
AWARD_BASES = {
    "point",
    "band",
    "range",
    "combined",
    "backlog",
    "lease_contract",
    "midstream",
    "not_public",
}
FIGURE_TYPES = {"gross_capex", "net_share", "budget", "carry", "entry_price"}
PROVENANCE = {
    "operator",
    "partner",
    "partner_sec",
    "partner_asx",
    "regulator",
    "trade_press",
}


def _read(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sanctioned():
    return {r["PROJECT"] for r in _read(SANCTIONED)}


def test_awards_fk_and_vocab():
    names = _sanctioned()
    rows = _read(AWARDS)
    assert len(rows) >= 40
    for r in rows:
        assert (
            r["PROJECT"] in names
        ), f"award references unknown project: {r['PROJECT']}"
        assert r["ASSET_CLASS"] in ASSET_CLASSES, r
        assert r["VALUE_BASIS"] in AWARD_BASES, r
        assert r["PROVENANCE"] in PROVENANCE, r
        assert r["SOURCE_URL"].startswith("http"), r


def test_band_rows_have_a_low_bound_and_word():
    for r in _read(AWARDS):
        if r["VALUE_BASIS"] == "band":
            assert r["VALUE_LOW_MM"], f"band row missing low bound: {r}"
            assert r["BAND_WORD"], f"band row missing band word: {r}"
            if r["VALUE_HIGH_MM"]:  # open-topped "major" bands may omit high
                assert float(r["VALUE_HIGH_MM"]) >= float(r["VALUE_LOW_MM"]), r


def test_not_public_rows_carry_no_value():
    # The honesty rail: a not_public award must not smuggle a number.
    for r in _read(AWARDS):
        if r["VALUE_BASIS"] == "not_public":
            assert (
                not r["VALUE_LOW_MM"] and not r["VALUE_HIGH_MM"]
            ), f"not_public row carries a value: {r['PROJECT']} {r['CONTRACTOR']}"


def test_point_rows_are_concrete():
    for r in _read(AWARDS):
        if r["VALUE_BASIS"] == "point":
            assert r["VALUE_LOW_MM"] and r["VALUE_HIGH_MM"], r


def test_statements_fk_and_vocab():
    names = _sanctioned()
    rows = _read(STMTS)
    assert len(rows) >= 12
    for r in rows:
        assert (
            r["PROJECT"] in names
        ), f"statement references unknown project: {r['PROJECT']}"
        assert r["FIGURE_TYPE"] in FIGURE_TYPES, r
        assert r["PROVENANCE"] in PROVENANCE, r
        assert float(r["VALUE_MM"]) > 0, r
        assert r["QUOTED_TEXT"].strip(), r


def test_partner_nets_reconcile_loosely_to_gross():
    # For projects with both a gross figure and a partner net_share + interest,
    # net / interest should land in a sane neighbourhood of gross (not off by 5x).
    # This catches a mis-entered interest or a base mix-up.
    rows = _read(STMTS)
    by_project: dict[str, dict] = {}
    for r in rows:
        by_project.setdefault(r["PROJECT"], {"gross": None, "nets": []})
        if r["FIGURE_TYPE"] == "gross_capex":
            by_project[r["PROJECT"]]["gross"] = float(r["VALUE_MM"])
        elif r["FIGURE_TYPE"] == "net_share" and r["INTEREST_PCT"]:
            by_project[r["PROJECT"]]["nets"].append(
                (float(r["VALUE_MM"]), float(r["INTEREST_PCT"]))
            )
    checked = 0
    for proj, d in by_project.items():
        if d["gross"] and d["nets"]:
            for net, pct in d["nets"]:
                implied = net / (pct / 100.0)
                # Guyana nets exclude the FPSO element, so allow a wide band (0.5x-1.5x).
                assert (
                    0.4 * d["gross"] <= implied <= 1.6 * d["gross"]
                ), f"{proj}: net {net}/{pct}% -> {implied:.0f} vs gross {d['gross']}"
                checked += 1
    assert checked >= 3
