# ABOUTME: Tests for the unified intervention-fleet catalog (#598): asset-class
# ABOUTME: classification + class-level aggregation/reconciliation builder.
"""Tests for ``fleet_catalog``.

CI-safe: classification is pure; the builder runs against tiny synthetic curated
CSVs + a synthetic seed written to ``tmp_path`` (no /mnt/ace or main-checkout
dependency). One skip-if-missing test runs against the real seed + curated dir.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from worldenergydata.vessel_fleet import fleet_catalog as fc


class TestClassifyAssetClass:
    def test_helix_q_name_to_heavy_intervention_semi(self):
        assert fc.classify_asset_class(name="Helix Q4000") == "heavy_intervention_semi"

    def test_drillship_rig_type_to_modu_drillship(self):
        assert (
            fc.classify_asset_class(rig_type="drillship", name="Deepwater X")
            == "modu_drillship"
        )

    def test_island_performer_to_rlwi_monohull(self):
        assert fc.classify_asset_class(name="Island Performer") == "rlwi_monohull"

    def test_lift_boat_rig_type_to_lift_boat(self):
        assert fc.classify_asset_class(rig_type="lift_boat") == "lift_boat"

    def test_semisub_and_jackup_rig_types(self):
        assert fc.classify_asset_class(rig_type="semi_submersible") == "modu_semisub"
        assert fc.classify_asset_class(rig_type="jack_up") == "modu_jackup"

    def test_construction_and_mpsv_vessel_types(self):
        assert (
            fc.classify_asset_class(vessel_type="heavy_lift") == "construction_vessel"
        )
        assert fc.classify_asset_class(vessel_type="mpsv") == "mpsv_osv"

    def test_rlwi_vessel_type_direct(self):
        assert fc.classify_asset_class(vessel_type="rlwi_monohull") == "rlwi_monohull"

    def test_unknown_falls_back_to_other(self):
        assert fc.classify_asset_class(rig_type="snubbing_unit") == "other"
        assert fc.classify_asset_class() == "other"

    def test_name_hint_wins_over_rig_type(self):
        # A Helix Q unit mis-tagged as a semi in the roster still classifies
        # as a heavy intervention semi via the name hint.
        assert (
            fc.classify_asset_class(rig_type="semi_submersible", name="Q5000")
            == "heavy_intervention_semi"
        )


# --- Synthetic fixtures -----------------------------------------------------

_SEED_DOC = {
    "vessels": [
        {
            "name": "Helix Q4000",
            "intervention_class": "heavy",
            "vessel_type": "heavy_intervention_semi",
            "riser_capable": True,
            "water_depth_rating_m": 3048,
            "gom_resident": True,
        },
        {
            "name": "Island Performer",
            "intervention_class": "light",
            "vessel_type": "rlwi_monohull",
            "riser_capable": True,
            "water_depth_rating_m": 2000,
            "gom_resident": True,
        },
        {
            "name": "Skandi Constructor",
            "intervention_class": "light",
            "vessel_type": "rlwi_monohull",
            "riser_capable": True,
            "water_depth_rating_m": 2000,
            "gom_resident": False,
        },
    ]
}

_DRILLING_CSV = (
    "RIG_NAME,RIG_TYPE,WATER_DEPTH_RATING_FT\n"
    "Deepwater A,drillship,12000\n"
    "Jackup B,jack_up,400\n"
    "Semi C,semi_submersible,7500\n"
    "Boat D,lift_boat,200\n"
)

_CONSTRUCTION_CSV = (
    "VESSEL_NAME,VESSEL_TYPE,WATER_DEPTH_RATING_M\n"
    "Layer One,pipelay_vessel,3000\n"
    "MPSV Two,mpsv,2500\n"
)


def _write_fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    curated = tmp_path / "curated"
    curated.mkdir()
    (curated / "drilling_rigs.csv").write_text(_DRILLING_CSV, encoding="utf-8")
    (curated / "construction_vessels.csv").write_text(
        _CONSTRUCTION_CSV, encoding="utf-8"
    )
    seed = tmp_path / "seed.yml"
    seed.write_text(yaml.safe_dump(_SEED_DOC), encoding="utf-8")
    out = tmp_path / "catalog.yml"
    return curated, seed, out


class TestBuildFleetCatalog:
    def test_class_counts_and_structure(self, tmp_path):
        curated, seed, out = _write_fixtures(tmp_path)
        cat = fc.build_fleet_catalog(curated_dir=curated, seed_path=seed, out_path=out)

        by = cat["by_asset_class"]
        # Helix Q4000 (seed) -> heavy intervention semi.
        assert by["heavy_intervention_semi"]["count"] == 1
        # Island Performer + Skandi Constructor (seed) -> 2 RLWI.
        assert by["rlwi_monohull"]["count"] == 2
        assert by["modu_drillship"]["count"] == 1
        assert by["modu_jackup"]["count"] == 1
        assert by["modu_semisub"]["count"] == 1
        assert by["lift_boat"]["count"] == 1
        assert by["construction_vessel"]["count"] == 1
        assert by["mpsv_osv"]["count"] == 1

        # Total = 3 seed + 4 drilling + 2 construction.
        assert cat["totals"]["units_classified"] == 9
        assert cat["totals"]["seed_dedicated_units"] == 3

    def test_named_flagships_from_seed(self, tmp_path):
        curated, seed, out = _write_fixtures(tmp_path)
        cat = fc.build_fleet_catalog(curated_dir=curated, seed_path=seed, out_path=out)
        flagships = cat["by_asset_class"]["rlwi_monohull"]["named_flagship_units"]
        assert "Island Performer" in flagships
        assert "Skandi Constructor" in flagships

    def test_depth_range_present_and_numeric(self, tmp_path):
        curated, seed, out = _write_fixtures(tmp_path)
        cat = fc.build_fleet_catalog(curated_dir=curated, seed_path=seed, out_path=out)
        rng = cat["by_asset_class"]["modu_drillship"]["water_depth_capability_ft"]
        assert rng["min"] == 12000.0
        assert rng["max"] == 12000.0

    def test_gom_resident_summary(self, tmp_path):
        curated, seed, out = _write_fixtures(tmp_path)
        cat = fc.build_fleet_catalog(curated_dir=curated, seed_path=seed, out_path=out)
        gom = cat["gom_resident_dedicated_intervention"]
        # Helix Q4000 + Island Performer are GoM-resident.
        assert gom["count"] == 2
        names = {u["name"] for u in gom["units"]}
        assert names == {"Helix Q4000", "Island Performer"}

    def test_reconciliation_block_and_confidence_labels(self, tmp_path):
        curated, seed, out = _write_fixtures(tmp_path)
        cat = fc.build_fleet_catalog(curated_dir=curated, seed_path=seed, out_path=out)
        recon = cat["reconciliation_to_research"]
        assert "global_rlwi_fleet" in recon
        assert "rigs_rated_20k_psi_worldwide" in recon
        labels = {entry["confidence"] for entry in recon.values()}
        assert labels <= {"on_record", "soft", "projected"}
        assert recon["rigs_rated_20k_psi_worldwide"]["confidence"] == "on_record"
        assert recon["global_rlwi_fleet"]["confidence"] == "soft"

    def test_catalog_written_to_out_path(self, tmp_path):
        curated, seed, out = _write_fixtures(tmp_path)
        fc.build_fleet_catalog(curated_dir=curated, seed_path=seed, out_path=out)
        assert out.is_file()
        reloaded = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert reloaded["catalog"] == "unified_intervention_fleet"

    def test_caveats_present(self, tmp_path):
        curated, seed, out = _write_fixtures(tmp_path)
        cat = fc.build_fleet_catalog(curated_dir=curated, seed_path=seed, out_path=out)
        assert any("599" in c for c in cat["caveats"])


# --- Real-data integration (skipped when off-repo data not mounted) ---------

_REAL_SEED = (
    Path(__file__).resolve().parents[3]
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata"
    / "vessel_fleet/data/intervention_vessels_seed.yml"
)
_REAL_CURATED = Path(
    "/mnt/local-analysis/worldenergydata/data/modules/vessel_fleet/curated"
)


@pytest.mark.skipif(
    not (_REAL_SEED.is_file() and (_REAL_CURATED / "drilling_rigs.csv").is_file()),
    reason="real seed or main-checkout curated dir not available",
)
def test_real_build(tmp_path):
    out = tmp_path / "catalog.yml"
    cat = fc.build_fleet_catalog(
        curated_dir=_REAL_CURATED, seed_path=_REAL_SEED, out_path=out
    )
    assert cat["totals"]["units_classified"] > 2000
    assert cat["by_asset_class"]["heavy_intervention_semi"]["count"] >= 1
    assert cat["by_asset_class"]["rlwi_monohull"]["count"] >= 1
