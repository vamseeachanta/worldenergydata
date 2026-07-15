# ABOUTME: Behavioural tests for the E5 reconciliation harness (#1028) against the live curated tables.
# ABOUTME: Locks the A1-relevant findings: no above-band anchor, GranMorgu SURF in-band, FPSO-exclusion reconciliation.
"""Tests for ``worldenergydata.cost.timeseries.reconciliation``.

These assert the *findings*, not just the plumbing: the reconciliation is only
useful if it reproduces the cross-checks the A1 decision rests on. If a future
data edit breaks one of these, that is a signal to re-examine the prior — which
is the point.
"""

from __future__ import annotations

from pathlib import Path

from worldenergydata.cost.timeseries.reconciliation import (
    compute_coverage,
    compute_outturn,
    compute_partner_checks,
    compute_stage_anchors,
    reconcile,
)

CURATED = Path(__file__).resolve().parents[3] / "data" / "modules" / "cost" / "curated"


def test_lease_and_midstream_excluded_from_coverage():
    # Barossa's BW Opal ($4.6bn lease) and Kaskida's Enbridge ($700MM midstream)
    # must NOT inflate coverage. Barossa coverage should stay well under 100%.
    cov = {c.project: c for c in compute_coverage(CURATED)}
    assert "Barossa" in cov
    assert cov["Barossa"].coverage_low_pct < 60, "lease value leaked into coverage"
    # Kaskida: Enbridge midstream excluded -> coverage stays modest
    assert cov["Kaskida"].coverage_low_pct < 30


def test_top_coverage_is_well_documented():
    cov = compute_coverage(CURATED)
    by = {c.project: c for c in cov}
    # The best-documented projects clear 45% of gross in valued awards.
    assert cov[0].coverage_low_pct >= 45
    # GranMorgu remains a strong anchor (Saipem's explicit $1.9bn SURF drives it).
    assert by["GranMorgu (Block 58)"].coverage_low_pct >= 40
    # Kaombo (E3) is now among the best-covered — Saipem FPSO + Technip/Heerema SURF.
    assert by["Kaombo"].coverage_low_pct >= 45


def test_no_award_anchor_exceeds_its_prior_band():
    # The A1 headline: nothing contradicts the priors by being too big.
    anchors = compute_stage_anchors(CURATED)
    above = [a for a in anchors if a.verdict == "above_band"]
    assert above == [], f"unexpected above-band anchors: {above}"


def test_granmorgu_surf_is_full_scope_and_in_band():
    # Saipem's explicit $1.9bn SURF is the strongest corroboration of a prior.
    anchors = compute_stage_anchors(CURATED)
    g = [
        a for a in anchors if a.project == "GranMorgu (Block 58)" and a.stage == "surf"
    ]
    assert len(g) == 1
    assert g[0].is_lower_bound is False, "explicit SURF EPCI should not be a floor"
    assert g[0].verdict == "in_band"


def test_fpso_buyouts_are_flagged_as_floors():
    anchors = compute_stage_anchors(CURATED)
    hosts = [a for a in anchors if a.stage == "host"]
    assert hosts, "expected host-stage anchors from FPSO buyouts"
    assert all(
        a.is_lower_bound for a in hosts
    ), "FPSO buyout host anchors must be floors"


def test_yellowtail_partner_reconciles_below_gross_via_fpso_exclusion():
    checks = {(c.project, c.company): c for c in compute_partner_checks(CURATED)}
    y = checks[("Yellowtail", "Hess")]
    # $2.3bn / 30% = $7.67bn, vs $10bn gross => ratio ~0.77 (FPSO excluded)
    assert 0.70 <= y.ratio <= 0.85
    assert "excludes" in y.note


def test_outturn_spread_spans_under_and_over():
    outs = {o.project: o for o in compute_outturn(CURATED)}
    assert outs["Kraken"].multiplier < 1.0  # came in under
    assert (
        outs["Johan Sverdrup Phase 1"].multiplier < 0.75
    )  # NOK, biggest under-run (~33% under)
    assert outs["Gorgon (incl. Jansz-Io)"].multiplier > 1.4  # ran well over
    assert (
        outs["Martin Linge (ex-Hild)"].multiplier >= 2.0
    )  # NOK, worst overrun (PDO 31.5 -> 63bn)


def test_reconcile_rollup_is_populated():
    rec = reconcile(CURATED)
    assert len(rec.coverage) >= 8
    assert len(rec.partner_checks) >= 5
    assert len(rec.stage_anchors) >= 15
    assert len(rec.outturn) >= 7
