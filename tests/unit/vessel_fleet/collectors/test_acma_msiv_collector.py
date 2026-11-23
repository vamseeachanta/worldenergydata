"""Tests for the ACMA MSIV markdown collector.

Uses inline markdown -- no off-repo dependency, so these run in CI without
the client share mounted. Also asserts the collector ignores the
cost / scoring / recommendation tables (confidentiality guard).
"""

from __future__ import annotations

import pytest

from worldenergydata.vessel_fleet.collectors import acma_msiv_collector as ac

_MATRIX_MD = """# MSIV Vessel Specifications Matrix

## Vessel Comparison Matrix

| Vessel Name | Type | LOA (m) | Beam (m) | Draft (m) | Main Crane (MT) | Aux Crane (MT) | DP Class | Accommodation | Shallow Water Rating |
|-------------|------|---------|----------|-----------|-----------------|----------------|----------|---------------|---------------------|
| Sleipnir | Semi-sub | 220 | 102 | 10.5/26 | 2×10,000 | - | DP3 | 400 | Excellent |
| DB-30 | Derrick Barge | 126 | 37 | 3.7 | 1,200 | - | Anchored | 150 | Excellent |
| Seven Borealis | Pipelay | 180 | 32 | 6.5 | 400 | 100 | DP2 | 140 | Excellent |

## Regional Availability & Mobilization

| Vessel Name | Primary Region | Typical Mobilization (days) | Estimated Mob Cost (USD) |
|-------------|----------------|----------------------------|-------------------------|
| Sleipnir | North Sea | 7-21 | $1M-4M |

## Top 5 Vessel Recommendations

### 1. Subsea 7 Seven Borealis (Score: 8.45)
"""


class TestParseMsivMatrix:
    def test_extracts_all_spec_rows(self):
        recs = ac.parse_msiv_matrix(_MATRIX_MD)
        names = {r["VESSEL_NAME"] for r in recs}
        assert names == {"Sleipnir", "DB-30", "Seven Borealis"}

    def test_dimensions_and_dp(self):
        recs = {r["VESSEL_NAME"]: r for r in ac.parse_msiv_matrix(_MATRIX_MD)}
        sl = recs["Sleipnir"]
        assert sl["LOA_M"] == 220.0
        assert sl["BEAM_M"] == 102.0
        # transit draft taken from "10.5/26"
        assert sl["DRAFT_M"] == 10.5
        assert sl["DP_CLASS"] == 3
        assert sl["QUARTERS_CAPACITY"] == 400
        assert sl["DATA_SOURCE"] == ac.DATA_SOURCE_MSIV

    def test_crane_multiplier_stripped(self):
        recs = {r["VESSEL_NAME"]: r for r in ac.parse_msiv_matrix(_MATRIX_MD)}
        # "2×10,000" -> per-crane 10000
        assert recs["Sleipnir"]["MAIN_CRANE_CAPACITY_T"] == 10000.0
        # "1,200" plain
        assert recs["DB-30"]["MAIN_CRANE_CAPACITY_T"] == 1200.0

    def test_anchored_dp_is_none(self):
        recs = {r["VESSEL_NAME"]: r for r in ac.parse_msiv_matrix(_MATRIX_MD)}
        assert recs["DB-30"]["DP_CLASS"] is None

    def test_aux_crane(self):
        recs = {r["VESSEL_NAME"]: r for r in ac.parse_msiv_matrix(_MATRIX_MD)}
        assert recs["Seven Borealis"]["AUX_CRANE_CAPACITY_T"] == 100.0
        assert recs["DB-30"]["AUX_CRANE_CAPACITY_T"] is None

    def test_no_cost_or_score_fields_leak(self):
        # No record should carry mobilization, cost, or score data.
        recs = ac.parse_msiv_matrix(_MATRIX_MD)
        for r in recs:
            joined = " ".join(str(v).lower() for v in r.values() if v is not None)
            assert "$" not in joined
            assert "score" not in joined
            assert "mob" not in joined

    def test_empty_text(self):
        assert ac.parse_msiv_matrix("no tables here") == []


class TestCollectMsivVessels:
    def test_env_unset_returns_empty(self, monkeypatch):
        monkeypatch.delenv(ac.ACMA_ENV_VAR, raising=False)
        assert ac.collect_msiv_vessels() == []

    def test_missing_dir_returns_empty(self, tmp_path):
        assert ac.collect_msiv_vessels(tmp_path / "nope") == []

    def test_reads_matrix_file(self, tmp_path):
        (tmp_path / "vessel-specifications-matrix.md").write_text(
            _MATRIX_MD, encoding="utf-8"
        )
        recs = ac.collect_msiv_vessels(tmp_path)
        assert len(recs) == 3
