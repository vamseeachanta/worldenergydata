# ABOUTME: Unit tests for war_vessel_crossref — WAR -> intervention-vessel cross-reference by water-depth band (#597).
# ABOUTME: CI-safe synthetic-frame tests for the pure aggregations plus a skip-if-missing real-data smoke test.

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.war_vessel_crossref import (
    asset_class_mix_by_band,
    build_crossref,
    crossref_by_band,
    deepwater_activity_by_year,
    depth_coverage,
    load_war,
    summarize,
)

_REAL_WAR = Path("/mnt/ace/worldenergydata/data/modules/bsee/bin/war/mv_war_main.bin")


def _frame() -> pd.DataFrame:
    """Synthetic WAR frame exercising every band + null depth + placeholder rig."""
    return pd.DataFrame(
        {
            "WATER_DEPTH": [
                300.0,  # shelf_lt_500
                1500.0,  # band_500_3000
                1500.0,  # band_500_3000 (same well, second record)
                4000.0,  # band_3000_5000
                6000.0,  # band_5000_10000
                12000.0,  # band_gt_10000
                None,  # unknown -> excluded from bands
                None,
            ],
            "API_WELL_NUMBER": [
                "608101000",
                "608102000",
                "608102000",  # duplicate well within band
                "608103000",
                "608104000",
                "608105000",
                "608109000",
                "608109000",
            ],
            "RIG_NAME": [
                "H&P 100",  # platform_rig, shelf
                "DEEPWATER THALASSA",  # drillship
                "DEEPWATER THALASSA",  # same asset, dedup
                "OCEAN BLACKHORNET",  # semi_submersible
                "* NON RIG UNIT OPERATION",  # placeholder -> excluded
                "WEST NEPTUNE",  # drillship
                "ENSCO 8500",  # null depth, not bucketed
                None,
            ],
            "WAR_START_DT": [
                "1/2/2018 12:01:00 AM",
                "3/5/2019",
                "4/6/2019",
                "7/8/2020",
                "9/9/2021 12:01:00 AM",
                "2/2/2022",
                "5/5/2023",
                None,
            ],
        }
    )


def test_depth_coverage_reports_floor():
    cov = depth_coverage(_frame())
    assert cov["records_total"] == 8
    assert cov["records_with_water_depth"] == 6
    assert cov["records_missing_water_depth"] == 2
    assert cov["depth_coverage_fraction"] == round(6 / 8, 4)
    assert cov["is_floor"] is True


def test_crossref_by_band_counts():
    bands = crossref_by_band(_frame())
    # All five bands present and ordered.
    assert list(bands.keys()) == [
        "shelf_lt_500",
        "band_500_3000",
        "band_3000_5000",
        "band_5000_10000",
        "band_gt_10000",
    ]
    b = bands["band_500_3000"]
    assert b["war_records"] == 2  # two records
    assert b["distinct_wells"] == 1  # same well twice
    assert b["distinct_assets"] == 1  # same asset twice
    assert b["modu_servicing"] is True
    assert b["is_floor"] is True

    shelf = bands["shelf_lt_500"]
    assert shelf["war_records"] == 1
    assert shelf["modu_servicing"] is False


def test_crossref_excludes_placeholder_assets():
    bands = crossref_by_band(_frame())
    # band_5000_10000 row uses the NON RIG UNIT placeholder -> 0 distinct assets.
    deep = bands["band_5000_10000"]
    assert deep["war_records"] == 1
    assert deep["distinct_assets"] == 0


def test_null_depth_rows_not_bucketed():
    bands = crossref_by_band(_frame())
    total_records_in_bands = sum(b["war_records"] for b in bands.values())
    # 6 depth-stamped rows land in bands; the 2 null-depth rows do not.
    assert total_records_in_bands == 6


def test_asset_class_mix_by_band():
    mix = asset_class_mix_by_band(_frame())
    # band_500_3000 -> single drillship.
    assert mix["band_500_3000"]["asset_class_counts"] == {"drillship": 1}
    # shelf -> platform_rig (H&P).
    assert mix["shelf_lt_500"]["asset_class_counts"].get("platform_rig") == 1
    # gt_10000 -> WEST NEPTUNE drillship.
    assert mix["band_gt_10000"]["asset_class_counts"].get("drillship") == 1
    # placeholder excluded -> empty mix for that band.
    assert mix["band_5000_10000"]["distinct_assets"] == 0
    assert mix["band_500_3000"]["is_floor"] is True


def test_deepwater_activity_by_year():
    activity = deepwater_activity_by_year(_frame())
    # MODU-servicing band rows: 2019,2019 (band_500_3000), 2020, 2021, 2022.
    assert activity == {2019: 2, 2020: 1, 2021: 1, 2022: 1}
    # shelf 2018 record excluded (not a MODU-servicing band).
    assert 2018 not in activity


def test_summarize_structure_and_caveats():
    result = summarize(_frame())
    assert set(result) >= {
        "depth_coverage",
        "bands",
        "asset_class_mix",
        "deepwater_activity_history_by_year",
        "totals",
        "caveats",
        "provenance",
    }
    assert result["totals"]["modu_band_records_floor"] == 5
    assert result["totals"]["modu_band_distinct_wells_floor"] == 4
    assert any("FLOOR" in c for c in result["caveats"])
    assert any("HISTORY" in c for c in result["caveats"])
    assert result["provenance"]["issue"].startswith("worldenergydata#597")


def test_build_crossref_writes_yaml(tmp_path):
    import pickle

    import yaml

    war_path = tmp_path / "mv_war_main.bin"
    with open(war_path, "wb") as fh:
        pickle.dump(_frame(), fh)
    out_path = tmp_path / "out" / "war_vessel_crossref.yml"

    result = build_crossref(war_path=war_path, out_path=out_path)
    assert out_path.exists()
    loaded = yaml.safe_load(out_path.read_text())
    assert loaded["totals"]["modu_band_records_floor"] == 5
    assert loaded["bands"]["band_500_3000"]["distinct_wells"] == 1
    assert result["depth_coverage"]["records_missing_water_depth"] == 2


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
    assert cov["records_with_water_depth"] > 0

    bands = result["bands"]
    assert set(bands) == set(
        [
            "shelf_lt_500",
            "band_500_3000",
            "band_3000_5000",
            "band_5000_10000",
            "band_gt_10000",
        ]
    )
    # Some deepwater activity must be on record.
    deep_records = sum(
        bands[k]["war_records"]
        for k in ("band_3000_5000", "band_5000_10000", "band_gt_10000")
    )
    assert deep_records > 0
    assert all(b["is_floor"] for b in bands.values())
    assert result["totals"]["modu_band_distinct_wells_floor"] > 0
