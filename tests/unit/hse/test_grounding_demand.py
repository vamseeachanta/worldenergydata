# ABOUTME: Tests for worldenergydata.hse.grounding_demand — request logging + gap rollup.
# ABOUTME: Fixture-backed; no NFS share or network dependency in CI.

"""Tests for the grounding demand signal (#491)."""

from __future__ import annotations

from pathlib import Path

import pytest

from worldenergydata.hse.grounding_demand import (
    ground_and_log,
    load_demand,
    record_demand,
    render_rollup_md,
    rollup,
)

FIXTURE = Path(__file__).parent / "fixtures" / "bsee_incinv_sample.txt"


def test_record_and_load_roundtrip(tmp_path):
    log = tmp_path / "demand.jsonl"
    record_demand(
        "mooring_fatigue", covered=True, n_incidents=6, when="2026-06-19", log_path=log
    )
    record_demand(
        "riser_viv",
        covered=False,
        n_incidents=0,
        reason="unknown_mode",
        when="2026-06-19",
        log_path=log,
    )
    recs = load_demand(log)
    assert len(recs) == 2
    assert recs[0]["failure_mode"] == "mooring_fatigue" and recs[0]["covered"] is True
    assert recs[1]["reason"] == "unknown_mode"


def test_ground_and_log_hit_for_known_mode(tmp_path):
    log = tmp_path / "demand.jsonl"
    g = ground_and_log(
        "mooring_fatigue", when="2026-06-19", log_path=log, bsee_path=FIXTURE
    )
    assert g.failure_mode.startswith("Mooring")
    rec = load_demand(log)[0]
    assert rec["covered"] is True and rec["n_incidents"] >= 4


def test_ground_and_log_gap_for_unknown_mode(tmp_path):
    log = tmp_path / "demand.jsonl"
    with pytest.raises(KeyError):
        ground_and_log(
            "riser_viv_fatigue", when="2026-06-19", log_path=log, bsee_path=FIXTURE
        )
    rec = load_demand(log)[0]
    assert rec["failure_mode"] == "riser_viv_fatigue"
    assert rec["covered"] is False and rec["reason"] == "unknown_mode"


def test_rollup_ranks_gaps_by_request_count(tmp_path):
    log = tmp_path / "demand.jsonl"
    # riser_viv requested 3x (unknown), subsea_landslide 1x (unknown), mooring covered
    for _ in range(3):
        record_demand(
            "riser_viv",
            covered=False,
            n_incidents=0,
            reason="unknown_mode",
            when="2026-06-19",
            log_path=log,
        )
    record_demand(
        "subsea_landslide",
        covered=False,
        n_incidents=0,
        reason="unknown_mode",
        when="2026-06-19",
        log_path=log,
    )
    record_demand(
        "mooring_fatigue", covered=True, n_incidents=6, when="2026-06-19", log_path=log
    )

    roll = rollup(load_demand(log))
    assert roll["total_requests"] == 5
    gap_modes = [g["failure_mode"] for g in roll["gaps"]]
    assert gap_modes[0] == "riser_viv"  # most-requested gap ranks first
    assert "subsea_landslide" in gap_modes
    assert [c["failure_mode"] for c in roll["covered"]] == ["mooring_fatigue"]


def test_thin_corpus_counts_as_gap(tmp_path):
    log = tmp_path / "demand.jsonl"
    # a known mode that only ever matched 2 incidents -> thin, still a gap
    record_demand(
        "dropped_object",
        covered=False,
        n_incidents=2,
        reason="thin_corpus",
        when="2026-06-19",
        log_path=log,
    )
    roll = rollup(load_demand(log))
    statuses = {g["failure_mode"]: g["status"] for g in roll["gaps"]}
    assert statuses["dropped_object"] == "thin"


def test_render_rollup_md_flags_gaps():
    roll = rollup(
        [
            {
                "failure_mode": "riser_viv",
                "covered": False,
                "n_incidents": 0,
                "reason": "unknown_mode",
            },
            {
                "failure_mode": "mooring_fatigue",
                "covered": True,
                "n_incidents": 6,
                "reason": "",
            },
        ]
    )
    md = render_rollup_md(roll)
    assert "Coverage gaps — build next" in md
    assert "riser_viv" in md
    assert "next coverage to build" in md
