# ABOUTME: Tests for the /mnt/ace fleet loader (heavy-lift CSV snapshots +
# ABOUTME: MSIV markdown DB ingestion into the vessel-fleet schema, issue #595.
"""Tests for ``mnt_ace_fleet_loader``.

CI-safe: synthetic CSV/markdown fixtures written to ``tmp_path`` exercise the
normalisation, reconciliation, and markdown-table parsing. One skip-if-missing
test runs against the real off-repo data under ``/mnt/ace``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from worldenergydata.vessel_fleet.loaders import mnt_ace_fleet_loader as ld

_HEAVY_LIFT_HEADER = (
    "contractor,vessel_name,vessel_type,operating_region,loa_ft,beam_ft,"
    "draft_ft,deck_capacity_t,classification,crane_model,"
    "primary_lift_capacity_t,primary_lift_radius_ft,secondary_lift_capacity_t,"
    "secondary_lift_radius_ft,max_hook_height_ft,mooring_system,dp_class,"
    "notes,needs_review,imo_number,current_owner,current_status,status_year,"
    "renamed_to,source_url,archival_year"
)

# 2010 snapshot has only the original (pre-enrichment) columns.
_HEAVY_LIFT_2010_HEADER = (
    "contractor,vessel_name,vessel_type,operating_region,loa_ft,beam_ft,"
    "draft_ft,deck_capacity_t,classification,crane_model,"
    "primary_lift_capacity_t,primary_lift_radius_ft,secondary_lift_capacity_t,"
    "secondary_lift_radius_ft,max_hook_height_ft,mooring_system,dp_class,"
    "notes,needs_review"
)

_MSIV_MARKDOWN = """# MSIV Vessel Specifications Matrix

> Created: 2025-08-07
> Project: REDACTED - Confidential Client Research

## Vessel Comparison Matrix

| Vessel Name | Type | LOA (m) | Beam (m) | Draft (m) | Main Crane (MT) | \
Aux Crane (MT) | DP Class | Accommodation | Shallow Water Rating |
|---|---|---|---|---|---|---|---|---|---|
| Sleipnir | Semi-sub | 220 | 102 | 10.5/26 | 2x10,000 | - | DP3 | 400 | \
Excellent |
| Seven Borealis | Pipelay | 180 | 32 | 6.5 | 400 | 100 | DP2 | 140 | \
Excellent |
| DB-30 | Derrick Barge | 126 | 37 | 3.7 | 1,200 | - | Anchored | 150 | \
Excellent |

## Regional Availability & Mobilization

| Vessel Name | Primary Region | Estimated Mob Cost (USD) |
|---|---|---|
| Sleipnir | North Sea | $1M-4M |
"""


def _write(tmp_path: Path, name: str, header: str, rows: list[str]) -> None:
    (tmp_path / name).write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


class TestLoadHeavyLiftCsvs:
    def test_missing_dir_returns_empty(self, tmp_path):
        assert ld.load_heavy_lift_csvs(tmp_path / "nope") == []

    def test_current_snapshot_normalised(self, tmp_path):
        _write(
            tmp_path,
            ld.HEAVY_LIFT_CURRENT_FILE,
            _HEAVY_LIFT_HEADER,
            [
                "BIGLIFT,HAPPY BUCCANEER,Heavylift,WW,479,93,,,DNV,,675.0,,"
                "2755.0,,300.0,8 Point,DP2,,False,8300389,BigLift,scrapped,"
                "2024,,https://x,2010"
            ],
        )
        out = ld.load_heavy_lift_csvs(tmp_path)
        assert len(out) == 1
        rec = out[0]
        assert rec["VESSEL_NAME"] == "HAPPY BUCCANEER"
        assert rec["VESSEL_CATEGORY"] == "construction"
        assert rec["VESSEL_TYPE"] == "heavy_lift"
        assert rec["IMO_NUMBER"] == "8300389"
        assert rec["DATA_SOURCE"] == ld.DATA_SOURCE_HEAVY_LIFT_CURRENT
        # COLLECTION_DATE comes from status_year
        assert rec["COLLECTION_DATE"] == "2024"
        # ft -> m conversion
        assert rec["LOA_M"] == round(479 * 0.3048, 1)
        assert rec["DP_CLASS"] == 2
        assert rec["MAIN_CRANE_CAPACITY_T"] == 675.0

    def test_current_collection_date_falls_back(self, tmp_path):
        # status_year blank -> "current"
        _write(
            tmp_path,
            ld.HEAVY_LIFT_CURRENT_FILE,
            _HEAVY_LIFT_HEADER,
            [
                "C,VESSEL X,Heavylift,WW,100,30,,,,,500.0,,,,,,,,False,,Owner,"
                "active,,,https://z,2010"
            ],
        )
        out = ld.load_heavy_lift_csvs(tmp_path)
        assert out[0]["COLLECTION_DATE"] == "current"

    def test_legacy_only_vessel_kept_with_2010_provenance(self, tmp_path):
        _write(
            tmp_path,
            ld.HEAVY_LIFT_CURRENT_FILE,
            _HEAVY_LIFT_HEADER,
            [
                "C,CURRENT ONLY,Heavylift,WW,100,30,,,,,500.0,,,,,,,,False,,O,"
                "active,2024,,https://z,2010"
            ],
        )
        _write(
            tmp_path,
            ld.HEAVY_LIFT_2010_FILE,
            _HEAVY_LIFT_2010_HEADER,
            ["C,LEGACY ONLY,Stiff Leg,GOM,200,70,14,,ABS,,700.0,,,,,,,,False"],
        )
        out = ld.load_heavy_lift_csvs(tmp_path)
        by_name = {r["VESSEL_NAME"]: r for r in out}
        assert set(by_name) == {"CURRENT ONLY", "LEGACY ONLY"}
        assert by_name["LEGACY ONLY"]["DATA_SOURCE"] == (ld.DATA_SOURCE_HEAVY_LIFT_2010)
        assert by_name["LEGACY ONLY"]["COLLECTION_DATE"] == "2010"

    def test_reconcile_fills_missing_spec_from_2010(self, tmp_path):
        # Current row has no draft; 2010 row supplies it. Match on name.
        _write(
            tmp_path,
            ld.HEAVY_LIFT_CURRENT_FILE,
            _HEAVY_LIFT_HEADER,
            [
                "C,SHARED,Heavylift,WW,479,93,,,,,675.0,,,,,,,,False,8300389,"
                "Owner,active,2024,,https://x,2010"
            ],
        )
        _write(
            tmp_path,
            ld.HEAVY_LIFT_2010_FILE,
            _HEAVY_LIFT_2010_HEADER,
            ["C,SHARED,Heavylift,WW,479,93,20,,ABS,,675.0,,,,,,,,False"],
        )
        out = ld.load_heavy_lift_csvs(tmp_path)
        assert len(out) == 1
        rec = out[0]
        # current is authoritative for provenance
        assert rec["DATA_SOURCE"] == ld.DATA_SOURCE_HEAVY_LIFT_CURRENT
        # draft filled forward from the 2010 snapshot
        assert rec["DRAFT_M"] == round(20 * 0.3048, 1)
        # classification filled forward too
        assert rec["CLASSIFICATION_SOCIETY"] == "ABS"


class TestParseMsivMarkdown:
    def test_parses_only_spec_matrix(self, tmp_path):
        path = tmp_path / "vessel-specifications-matrix.md"
        path.write_text(_MSIV_MARKDOWN, encoding="utf-8")
        out = ld.parse_msiv_markdown(path)
        names = {r["VESSEL_NAME"] for r in out}
        assert names == {"Sleipnir", "Seven Borealis", "DB-30"}

    def test_tags_intervention_msiv(self, tmp_path):
        path = tmp_path / "matrix.md"
        path.write_text(_MSIV_MARKDOWN, encoding="utf-8")
        rec = next(
            r for r in ld.parse_msiv_markdown(path) if r["VESSEL_NAME"] == "DB-30"
        )
        assert rec["VESSEL_CATEGORY"] == "intervention"
        assert rec["VESSEL_TYPE"] == "msiv"

    def test_specs_and_collection_date(self, tmp_path):
        path = tmp_path / "matrix.md"
        path.write_text(_MSIV_MARKDOWN, encoding="utf-8")
        rec = next(
            r for r in ld.parse_msiv_markdown(path) if r["VESSEL_NAME"] == "Sleipnir"
        )
        assert rec["LOA_M"] == 220.0
        assert rec["BEAM_M"] == 102.0
        # "2x10,000" -> per-crane SWL 10000
        assert rec["MAIN_CRANE_CAPACITY_T"] == 10000.0
        # draft "10.5/26" -> transit (first)
        assert rec["DRAFT_M"] == 10.5
        assert rec["DP_CLASS"] == 3
        assert rec["QUARTERS_CAPACITY"] == 400
        # provenance date from the "Created:" header line
        assert rec["COLLECTION_DATE"] == "2025-08-07"

    def test_no_client_or_project_identifiers_in_output(self, tmp_path):
        path = tmp_path / "matrix.md"
        path.write_text(_MSIV_MARKDOWN, encoding="utf-8")
        blob = repr(ld.parse_msiv_markdown(path)).upper()
        assert "REDACTED" not in blob
        assert "CONFIDENTIAL" not in blob
        assert "PROJECT" not in blob

    def test_missing_file_returns_empty(self, tmp_path):
        assert ld.parse_msiv_markdown(tmp_path / "nope.md") == []

    def test_prose_only_markdown_yields_empty(self, tmp_path):
        path = tmp_path / "prose.md"
        path.write_text("# Notes\n\nNo tables here.\n", encoding="utf-8")
        assert ld.parse_msiv_markdown(path) == []


class TestParseMsivDir:
    def test_dedups_across_files(self, tmp_path):
        (tmp_path / "a.md").write_text(_MSIV_MARKDOWN, encoding="utf-8")
        (tmp_path / "b.md").write_text(_MSIV_MARKDOWN, encoding="utf-8")
        out = ld.parse_msiv_dir(tmp_path)
        names = [r["VESSEL_NAME"] for r in out]
        assert sorted(names) == ["DB-30", "Seven Borealis", "Sleipnir"]


class TestCombine:
    def test_combines_both_sources(self, tmp_path):
        hl_dir = tmp_path / "hl"
        msiv_dir = tmp_path / "msiv"
        hl_dir.mkdir()
        msiv_dir.mkdir()
        _write(
            hl_dir,
            ld.HEAVY_LIFT_CURRENT_FILE,
            _HEAVY_LIFT_HEADER,
            [
                "C,VESSEL X,Heavylift,WW,100,30,,,,,500.0,,,,,,,,False,,O,"
                "active,2024,,https://z,2010"
            ],
        )
        (msiv_dir / "matrix.md").write_text(_MSIV_MARKDOWN, encoding="utf-8")
        out = ld.combine(heavy_lift_dir=hl_dir, msiv_dir=msiv_dir)
        cats = {r["VESSEL_CATEGORY"] for r in out}
        assert cats == {"construction", "intervention"}
        assert len(out) == 4  # 1 heavy-lift + 3 MSIV

    def test_all_none_returns_empty(self):
        assert ld.combine() == []


# --- Real-data integration (skipped when /mnt/ace is not mounted) -----------

_REAL_HL_DIR = Path("/mnt/ace/frontierdeepwater/data/processed/vessel-fleet")
_REAL_MSIV_DIR = Path("/mnt/ace/acma-projects/B1535/data/vessels/msiv")


@pytest.mark.skipif(
    not (_REAL_HL_DIR.is_dir() and _REAL_MSIV_DIR.is_dir()),
    reason="off-repo /mnt/ace fleet data not mounted",
)
def test_real_mnt_ace_data_combines():
    out = ld.combine(heavy_lift_dir=_REAL_HL_DIR, msiv_dir=_REAL_MSIV_DIR)
    assert out, "expected records from real /mnt/ace fleet data"
    # every record has the required name + provenance
    for rec in out:
        assert rec["VESSEL_NAME"]
        assert rec["DATA_SOURCE"]
    cats = {r["VESSEL_CATEGORY"] for r in out}
    assert "construction" in cats
    assert "intervention" in cats
