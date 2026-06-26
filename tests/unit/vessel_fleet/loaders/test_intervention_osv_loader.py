# ABOUTME: Tests for the OSV/MPSV + intervention vendor fleet roster loader (#593).
# ABOUTME: Covers a synthetic YAML fixture plus one assertion pass over the real roster.

from __future__ import annotations

import textwrap

from worldenergydata.vessel_fleet.loaders.intervention_osv_loader import (
    load_intervention_osv_roster,
    summarize_intervention_osv_roster,
)


def _write_roster(tmp_path, body: str):
    path = tmp_path / "roster.yml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_load_synthetic_roster_returns_vessels(tmp_path):
    path = _write_roster(
        tmp_path,
        """
        provenance:
          confidence: medium
        vessels:
          - vessel_name: Synthetic Semi
            owner: Test Vendor
            vessel_type: heavy_intervention_semi
            water_depth_rating_m: 3000
            dp_class: DP3
            gom_resident: true
          - vessel_name: Synthetic Monohull
            owner: Test Vendor
            vessel_type: rlwi_monohull
            water_depth_rating_m: null
            dp_class: null
            gom_resident: false
        """,
    )
    vessels = load_intervention_osv_roster(path=path)
    assert len(vessels) == 2
    assert vessels[0]["vessel_name"] == "Synthetic Semi"
    # Unknown specs must survive as None, never be coerced/guessed.
    assert vessels[1]["water_depth_rating_m"] is None
    assert vessels[1]["dp_class"] is None


def test_missing_file_returns_empty(tmp_path):
    vessels = load_intervention_osv_roster(path=tmp_path / "nope.yml")
    assert vessels == []


def test_summary_counts_synthetic(tmp_path):
    path = _write_roster(
        tmp_path,
        """
        vessels:
          - {vessel_name: A, vessel_type: mpsv, gom_resident: true}
          - {vessel_name: B, vessel_type: mpsv, gom_resident: false}
          - {vessel_name: C, vessel_type: rlwi_monohull, gom_resident: null}
        """,
    )
    summary = summarize_intervention_osv_roster(path=path)
    assert summary["total"] == 3
    assert summary["by_vessel_type"]["mpsv"] == 2
    assert summary["by_vessel_type"]["rlwi_monohull"] == 1
    assert summary["by_gom_resident"]["true"] == 1
    assert summary["by_gom_resident"]["false"] == 1
    assert summary["by_gom_resident"]["unknown"] == 1


def test_real_roster_loads_and_summarizes():
    """One assertion pass over the committed package-data roster."""
    vessels = load_intervention_osv_roster()
    assert len(vessels) == 29

    names = {v["vessel_name"] for v in vessels}
    assert "Q4000" in names
    assert "Ocean Evolution" in names
    assert "AKOFS Seafarer" in names

    # Every row carries a citation + confidence; no spec is silently guessed.
    for vessel in vessels:
        assert vessel.get("source_url"), vessel["vessel_name"]
        assert vessel.get("confidence"), vessel["vessel_name"]
        assert "vessel_type" in vessel

    summary = summarize_intervention_osv_roster(vessels)
    assert summary["total"] == 29
    # Helix Q-series semis are present.
    assert summary["by_vessel_type"]["heavy_intervention_semi"] == 3
    # GoM-resident + non-resident + unknown partition the whole roster.
    gom = summary["by_gom_resident"]
    assert gom["true"] + gom["false"] + gom["unknown"] == 29
    assert gom["true"] >= 1
