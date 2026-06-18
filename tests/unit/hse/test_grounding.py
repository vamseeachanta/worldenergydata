# ABOUTME: Tests for worldenergydata.hse.grounding — failure-mode incident grounding.
# ABOUTME: Fixture-backed; no NFS share or network dependency in CI.

"""Tests for the HSE incident-grounding query (#487).

Uses a small committed BSEE fixture so CI needs neither the ace-linux-1 share
nor network. Verifies: mode filtering, 2-latest + 2-severe selection, severity
ranking, vintage stamp computed from data, per-mode source routing, and the
Operator Aggregation Contract (no operator names in output).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from worldenergydata.hse.grounding import (
    FAILURE_MODES,
    ground,
    load_bsee,
    severity_of,
)

FIXTURE = Path(__file__).parent / "fixtures" / "bsee_incinv_sample.txt"


def _g():
    return ground("mooring_fatigue", bsee_path=FIXTURE)


def test_mode_filter_excludes_non_mooring():
    incidents = load_bsee(FAILURE_MODES["mooring_fatigue"], FIXTURE)
    descs = " ".join(i.description for i in incidents)
    # the fixture's "Dropped Object" and bare "Fire" rows must not match
    assert "Dropped Object" not in descs
    assert all("Fire" != i.description for i in incidents)
    # all five mooring/anchor/capsize rows match
    assert len(incidents) == 5


def test_latest_two_are_newest_by_date():
    g = _g()
    assert [i.date for i in g.latest] == ["2020-01-29", "2006-12-24"]


def test_most_severe_two_are_highest_rank_and_disjoint_from_latest():
    g = _g()
    latest_dates = {i.date for i in g.latest}
    assert all(i.date not in latest_dates for i in g.most_severe)
    # both capsize rows are catastrophic (rank 90), beating anchor-contact/minor
    assert [i.severity for i in g.most_severe] == ["catastrophic", "catastrophic"]
    assert {i.date for i in g.most_severe} == {"2005-09-23", "2002-10-03"}


def test_severity_ranking():
    assert severity_of("Fatality")[1] == "fatality"
    assert severity_of("Pollution - Capsized")[1] == "catastrophic"
    assert severity_of("Incident >$25K - Mooring line")[1] == "property_>$25k"


def test_vintage_stamp_computed_from_data_not_mtime():
    g = _g()
    # newest DATE_OCCURRED in the fixture is 2020-01-29
    assert "current to 2020-01-29" in g.vintage_note
    assert "current to 2020-01-29" in g.render_card()


def test_per_mode_source_routing_offshore_is_bsee_only():
    g = _g()
    assert g.source_counts["BSEE"] == 5
    assert "not routed" in str(g.source_counts["OSHA"])
    assert "not routed" in str(g.source_counts["EPA_TRI"])


def test_no_operator_names_in_output():
    # Operator Aggregation Contract (#423): lease blocks + dates only.
    g = _g()
    blob = g.render_card().lower()
    for banned in ("chevron", "shell", "apache", "bp", "exxon", "operator"):
        assert banned not in blob


def test_card_and_dict_shapes():
    g = _g()
    d = g.to_dict()
    assert len(d["latest_2"]) == 2 and len(d["most_severe_2"]) == 2
    assert d["latest_2"][0]["location"] == "MC 437 G33733"
    assert "Real-world precedent" in g.render_card()


def test_unknown_mode_raises():
    with pytest.raises(KeyError):
        ground("does_not_exist", bsee_path=FIXTURE)
