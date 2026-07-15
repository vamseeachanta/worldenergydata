# ABOUTME: Schema + integrity guards for the E4 cost-revision-trails table (#1027).
# ABOUTME: Enforces FK to sanctioned_projects, vocab, currency consistency, and the trade_press honesty rail.
"""Guards for ``data/modules/cost/curated/cost_revision_trails.csv``.

These are honesty rails, not analytics: a trail point must reference a real
project (when flagged in-set), use a known kind/provenance, carry a source and
a quote, and — the load-bearing one — a ``trade_press`` point must be
``low`` confidence so a trade-derived outturn is never laundered into a
disclosed figure.
"""

from __future__ import annotations

import csv
from pathlib import Path

CURATED = Path(__file__).resolve().parents[3] / "data" / "modules" / "cost" / "curated"
TRAILS = CURATED / "cost_revision_trails.csv"
SANCTIONED = CURATED / "sanctioned_projects.csv"

KINDS = {
    "sanction_estimate",
    "revised_estimate",
    "spend_to_date",
    "final_forecast",
    "final_outturn",
}
PROVENANCE = {"operator", "partner_sec", "partner_asx", "regulator", "trade_press"}
CONFIDENCE = {"high", "medium", "low"}
CURRENCIES = {"USD", "NOK", "DKK", "AUD", "GBP", "BRL", "EUR"}


def _rows():
    with open(TRAILS, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sanctioned_names():
    with open(SANCTIONED, newline="", encoding="utf-8") as fh:
        return {r["PROJECT"] for r in csv.DictReader(fh)}


def test_nonempty_and_multipoint():
    rows = _rows()
    assert len(rows) >= 30
    by_project: dict[str, int] = {}
    for r in rows:
        by_project[r["PROJECT"]] = by_project.get(r["PROJECT"], 0) + 1
    # a trail is only meaningful with >= 2 points; most projects should qualify
    multi = [p for p, n in by_project.items() if n >= 2]
    assert len(multi) >= 10


def test_controlled_vocabularies():
    for r in _rows():
        assert r["KIND"] in KINDS, r
        assert r["PROVENANCE"] in PROVENANCE, r
        assert r["CONFIDENCE"] in CONFIDENCE, r
        assert r["CURRENCY"] in CURRENCIES, r


def test_fk_to_sanctioned_projects():
    names = _sanctioned_names()
    for r in _rows():
        if r["IN_SANCTIONED_SET"] == "True":
            assert (
                r["PROJECT"] in names
            ), f"in-set row references unknown project: {r['PROJECT']}"
        else:
            assert (
                r["PROJECT"] not in names
            ), f"row flagged out-of-set but project IS in sanctioned_projects: {r['PROJECT']}"


def test_every_point_is_sourced():
    for r in _rows():
        assert r["SOURCE_TITLE"].strip(), r
        assert r["SOURCE_URL"].strip().startswith("http"), r
        assert r["QUOTED_TEXT"].strip(), r
        assert float(r["VALUE_MM"]) > 0, r


def test_trade_press_points_are_low_confidence():
    # The honesty rail: a trade-derived figure must never masquerade as disclosed.
    for r in _rows():
        if r["PROVENANCE"] == "trade_press":
            assert (
                r["CONFIDENCE"] == "low"
            ), f"trade_press point must be low-confidence: {r['PROJECT']} {r['STATEMENT_DATE']}"


def test_currency_consistent_overruns_are_computable():
    # At least a few projects must have a same-currency sanction + final pair,
    # so an overrun can actually be computed (the whole point of the table).
    rows = _rows()
    pairs = 0
    by_key: dict[tuple[str, str], dict[str, float]] = {}
    for r in rows:
        by_key.setdefault((r["PROJECT"], r["CURRENCY"]), {})
        by_key[(r["PROJECT"], r["CURRENCY"])].setdefault(
            r["KIND"], float(r["VALUE_MM"])
        )
    for kinds in by_key.values():
        if "sanction_estimate" in kinds and (
            "final_outturn" in kinds or "final_forecast" in kinds
        ):
            pairs += 1
    assert pairs >= 5
