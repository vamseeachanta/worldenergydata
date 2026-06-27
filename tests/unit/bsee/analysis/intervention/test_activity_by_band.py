# ABOUTME: Unit tests for activity_by_band — intervention SERVICE-TYPE activity by water-depth band (#627).
# ABOUTME: CI-safe synthetic-frame tests for the pure aggregations plus a skip-if-missing real-data smoke test.

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.activity_by_band import (
    build_activity_by_band,
    classify_service_type,
    light_vs_heavy_by_band,
    load_war,
    service_rollup,
    service_type_by_band,
    summarize,
)

_REAL_WAR = Path("/mnt/ace/worldenergydata/data/modules/bsee/bin/war/mv_war_main.bin")


def _frame() -> pd.DataFrame:
    """Synthetic WAR frame: every band, multiple service types, null depth, placeholder."""
    return pd.DataFrame(
        {
            "WATER_DEPTH": [
                300.0,  # shelf_lt_500   -- platform_rig (heavy)
                1500.0,  # band_500_3000 -- wireline (light)
                1500.0,  # band_500_3000 -- wireline, same well (dedup)
                1500.0,  # band_500_3000 -- coil_tubing (light), new well
                4000.0,  # band_3000_5000 -- drillship (heavy)
                6000.0,  # band_5000_10000 -- placeholder -> unknown (other)
                12000.0,  # band_gt_10000 -- workover (heavy)
                900.0,  # band_500_3000 -- pumping (other)
                None,  # null depth -> excluded
                None,
            ],
            "API_WELL_NUMBER": [
                "608101000",
                "608102000",
                "608102000",  # duplicate well within wireline/band
                "608103000",
                "608104000",
                "608105000",
                "608106000",
                "608107000",
                "608109000",
                "608109000",
            ],
            "RIG_NAME": [
                "H&P 100",  # platform_rig
                "SUPERIOR /WL 1",  # wireline_unit
                "SUPERIOR /WL 1",  # same asset
                "HALLIBURTON /CT 2",  # coil_tubing_unit
                "DEEPWATER THALASSA",  # drillship
                "* NON RIG UNIT OPERATION",  # placeholder -> unknown
                "BIG WORKOVER RIG",  # workover_rig
                "ACE PUMP UNIT",  # pumping_unit
                "ENSCO 8500",  # null depth, not bucketed
                None,
            ],
            "WAR_START_DT": [
                "1/2/2018",
                "3/5/2019",
                "4/6/2019",
                "7/8/2020",
                "9/9/2021",
                "2/2/2022",
                "5/5/2023",
                "6/6/2023",
                "8/8/2024",
                None,
            ],
        }
    )


def test_classify_service_type():
    assert classify_service_type("SUPERIOR /WL 1") == "wireline_unit"
    assert classify_service_type("HALLIBURTON /CT 2") == "coil_tubing_unit"
    assert classify_service_type("BIG WORKOVER RIG") == "workover_rig"
    assert classify_service_type("DEEPWATER THALASSA") == "drillship"
    # null / placeholder -> unknown
    assert classify_service_type(None) == "unknown"
    assert classify_service_type("* NON RIG UNIT OPERATION") == "unknown"


def test_service_rollup_mapping():
    assert service_rollup("wireline_unit") == "light"
    assert service_rollup("support_vessel") == "light"
    assert service_rollup("workover_rig") == "heavy"
    assert service_rollup("drillship") == "heavy"
    assert service_rollup("semi_submersible") == "heavy"
    # pumping and unknown are explicitly 'other', never light/heavy
    assert service_rollup("pumping_unit") == "other"
    assert service_rollup("unknown") == "other"


def test_service_type_by_band_matrix():
    matrix = service_type_by_band(_frame())
    # Only service types with a depth-stamped record appear, in display order.
    assert list(matrix.keys()) == [
        "wireline_unit",
        "coil_tubing_unit",
        "pumping_unit",
        "workover_rig",
        "drillship",
        "platform_rig",
        "unknown",
    ]
    # wireline in band_500_3000: 2 records, 1 distinct well (dedup).
    wl = matrix["wireline_unit"]
    assert wl["rollup"] == "light"
    cell = wl["bands"]["band_500_3000"]
    assert cell["war_records"] == 2
    assert cell["distinct_wells"] == 1
    assert cell["modu_servicing"] is True
    assert cell["is_floor"] is True
    # wireline has no shelf activity.
    assert wl["bands"]["shelf_lt_500"]["war_records"] == 0
    # per-service total spans only its rows.
    assert wl["total"]["war_records"] == 2
    assert wl["total"]["distinct_wells"] == 1

    # platform_rig lands on the shelf and is heavy.
    pr = matrix["platform_rig"]
    assert pr["rollup"] == "heavy"
    assert pr["bands"]["shelf_lt_500"]["war_records"] == 1


def test_light_vs_heavy_by_band():
    rollup = light_vs_heavy_by_band(_frame())
    assert list(rollup.keys()) == [
        "shelf_lt_500",
        "band_500_3000",
        "band_3000_5000",
        "band_5000_10000",
        "band_gt_10000",
    ]
    # band_500_3000: wireline(2) + coil_tubing(1) = 3 light records; pumping(1) other.
    b = rollup["band_500_3000"]["rollups"]
    assert b["light"]["war_records"] == 3
    assert b["light"]["distinct_wells"] == 2  # 608102000 + 608103000
    assert b["other"]["war_records"] == 1  # pumping
    assert b["heavy"]["war_records"] == 0
    # shelf: platform_rig heavy.
    assert rollup["shelf_lt_500"]["rollups"]["heavy"]["war_records"] == 1
    # gt_10000: workover heavy.
    assert rollup["band_gt_10000"]["rollups"]["heavy"]["war_records"] == 1
    # placeholder in band_5000_10000 -> other (unknown service type).
    assert rollup["band_5000_10000"]["rollups"]["other"]["war_records"] == 1


def test_null_depth_rows_excluded():
    rollup = light_vs_heavy_by_band(_frame())
    total = sum(
        cell["war_records"]
        for band in rollup.values()
        for cell in band["rollups"].values()
    )
    # 8 depth-stamped rows bucketed; the 2 null-depth rows excluded.
    assert total == 8


def test_summarize_structure_and_caveats():
    result = summarize(_frame())
    assert set(result) >= {
        "depth_coverage",
        "service_type_by_band",
        "light_vs_heavy_by_band",
        "totals",
        "rollup_scheme",
        "caveats",
        "provenance",
    }
    assert result["depth_coverage"]["records_total"] == 10
    assert result["depth_coverage"]["records_with_water_depth"] == 8
    # MODU-band rollup floor totals (exclude shelf): light=3, heavy=1(drill)+1(wo)=2, other=1(pump)+1(placeholder)=2.
    modu = result["totals"]["modu_band_records_floor_by_rollup"]
    assert modu["light"] == 3
    assert modu["heavy"] == 2
    assert modu["other"] == 2
    assert any("FLOOR" in c for c in result["caveats"])
    assert any("HISTORY" in c for c in result["caveats"])
    assert result["provenance"]["issue"].startswith("worldenergydata#627")


def test_build_activity_by_band_writes_yaml(tmp_path):
    import pickle

    import yaml

    war_path = tmp_path / "mv_war_main.bin"
    with open(war_path, "wb") as fh:
        pickle.dump(_frame(), fh)
    out_path = tmp_path / "out" / "activity_by_band.yml"

    result = build_activity_by_band(war_path=war_path, out_path=out_path)
    assert out_path.exists()
    loaded = yaml.safe_load(out_path.read_text())
    assert (
        loaded["service_type_by_band"]["wireline_unit"]["bands"]["band_500_3000"][
            "distinct_wells"
        ]
        == 1
    )
    assert result["totals"]["modu_band_records_floor_by_rollup"]["light"] == 3


@pytest.mark.skipif(
    not _REAL_WAR.exists(), reason="real BSEE WAR bin not present (/mnt/ace)"
)
def test_real_data_sane_structure():
    war = load_war(war_path=_REAL_WAR)
    assert len(war) > 100_000
    result = summarize(war)

    cov = result["depth_coverage"]
    assert cov["records_total"] == len(war)
    # The defining property: depth coverage is sparse (floor regime).
    assert 0.0 < cov["depth_coverage_fraction"] < 0.2

    matrix = result["service_type_by_band"]
    assert len(matrix) > 0
    # Every cell is FLOOR-labelled and bands are the canonical five.
    canonical = [
        "shelf_lt_500",
        "band_500_3000",
        "band_3000_5000",
        "band_5000_10000",
        "band_gt_10000",
    ]
    for svc in matrix.values():
        assert list(svc["bands"].keys()) == canonical
        assert all(cell["is_floor"] for cell in svc["bands"].values())
        assert svc["rollup"] in ("light", "heavy", "other")

    rollup = result["totals"]["modu_band_records_floor_by_rollup"]
    assert sum(rollup.values()) > 0
