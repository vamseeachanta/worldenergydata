# ABOUTME: Unit tests for intervention_demand — intervention rig-days + per-well rate by water-depth band (#630).
# ABOUTME: CI-safe synthetic-frame tests for the pure aggregations plus a skip-if-missing real-data smoke test.

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.intervention_demand import (
    _record_rig_days,
    build_demand,
    demand_by_band,
    duration_coverage,
    load_war,
    rig_days_by_band_year,
    summarize,
)

_REAL_WAR = Path("/mnt/ace/worldenergydata/data/modules/bsee/bin/war/mv_war_main.bin")


def _frame() -> pd.DataFrame:
    """Synthetic WAR frame exercising bands, durations, end-null floor, depth-null."""
    return pd.DataFrame(
        {
            "WATER_DEPTH": [
                1500.0,  # band_500_3000, well A
                1500.0,  # band_500_3000, well A again (same well, 2nd record)
                1500.0,  # band_500_3000, well B
                4000.0,  # band_3000_5000, well C, end MISSING -> floor 1 day
                6000.0,  # band_5000_10000, well D
                None,  # depth-null -> excluded from bands
            ],
            "API_WELL_NUMBER": [
                "608102000",  # A
                "608102000",  # A (duplicate well within band)
                "608103000",  # B
                "608104000",  # C
                "608105000",  # D
                "608109000",  # depth-null
            ],
            "WAR_START_DT": [
                "1/1/2019 12:01:00 AM",  # 5-day span (1->5 inclusive)
                "6/1/2019",  # 1-day span (same start/end day)
                "1/10/2020",  # 3-day span
                "3/1/2021",  # end missing -> floor 1
                "5/1/2021",  # 10-day span
                "7/1/2022",  # depth-null, ignored
            ],
            "WAR_END_DT": [
                "1/5/2019 11:59:00 PM",
                "6/1/2019 11:59:00 PM",
                "1/12/2020 11:59:00 PM",
                None,
                "5/10/2021 11:59:00 PM",
                "7/2/2022",
            ],
        }
    )


def test_record_rig_days_inclusive_and_floor():
    # 1->5 inclusive = 5 days, not a floor.
    days, floored = _record_rig_days("1/1/2019", "1/5/2019")
    assert days == 5 and floored is False
    # same day = 1 day inclusive.
    days, floored = _record_rig_days("6/1/2019", "6/1/2019")
    assert days == 1 and floored is False
    # missing end -> 1-day floor.
    days, floored = _record_rig_days("3/1/2021", None)
    assert days == 1 and floored is True
    # negative span (data error) -> 1-day floor.
    days, floored = _record_rig_days("3/5/2021", "3/1/2021")
    assert days == 1 and floored is True


def test_duration_coverage_reports_floor():
    cov = duration_coverage(_frame())
    assert cov["records_total"] == 6
    assert cov["records_with_water_depth"] == 5
    assert cov["records_missing_water_depth"] == 1
    assert cov["depth_coverage_fraction"] == round(5 / 6, 4)
    assert cov["records_with_end_date"] == 5  # one end is null
    assert cov["records_missing_end_date"] == 1
    assert cov["is_floor"] is True


def test_rig_days_by_band_year():
    by = rig_days_by_band_year(_frame())
    # band_500_3000: 2019 -> 5 + 1 = 6 days; 2020 -> 3 days.
    assert by["band_500_3000"] == {2019: 6, 2020: 3}
    # band_3000_5000: 2021 -> floor 1 day (end missing).
    assert by["band_3000_5000"] == {2021: 1}
    # band_5000_10000: 2021 -> 10 days.
    assert by["band_5000_10000"] == {2021: 10}
    # shelf + gt_10000 untouched.
    assert by["shelf_lt_500"] == {}
    assert by["band_gt_10000"] == {}


def test_demand_by_band_aggregation_and_rate():
    bands = demand_by_band(_frame())
    assert list(bands.keys()) == [
        "shelf_lt_500",
        "band_500_3000",
        "band_3000_5000",
        "band_5000_10000",
        "band_gt_10000",
    ]
    b = bands["band_500_3000"]
    assert b["intervention_rig_days_by_year"] == {2019: 6, 2020: 3}
    assert b["total_rig_days_floor"] == 9
    assert b["distinct_wells"] == 2  # wells A and B
    assert b["interventions"] == 3  # three records
    assert b["interventions_per_well"] == round(3 / 2, 3)
    assert b["modu_servicing"] is True
    assert b["is_floor"] is True

    floor_band = bands["band_3000_5000"]
    assert floor_band["total_rig_days_floor"] == 1  # end-missing floor
    assert floor_band["distinct_wells"] == 1
    assert floor_band["interventions_per_well"] == 1.0


def test_depth_null_rows_excluded_from_bands():
    bands = demand_by_band(_frame())
    total_interventions = sum(b["interventions"] for b in bands.values())
    # 5 depth-stamped rows land in bands; the 1 depth-null row does not.
    assert total_interventions == 5


def test_summarize_structure_and_caveats():
    result = summarize(_frame())
    assert set(result) >= {
        "depth_coverage",
        "bands",
        "totals",
        "caveats",
        "provenance",
    }
    # MODU bands: band_500_3000 (9) + band_3000_5000 (1) + band_5000_10000 (10) = 20.
    assert result["totals"]["modu_band_rig_days_floor"] == 20
    # distinct wells across MODU bands: A,B (band1) + C (band2) + D (band3) = 4.
    assert result["totals"]["modu_band_distinct_wells_floor"] == 4
    assert any("FLOOR" in c for c in result["caveats"])
    assert any("HISTORY" in c for c in result["caveats"])
    assert result["provenance"]["issue"].startswith("worldenergydata#630")


def test_build_demand_writes_yaml(tmp_path):
    import pickle

    import yaml

    war_path = tmp_path / "mv_war_main.bin"
    with open(war_path, "wb") as fh:
        pickle.dump(_frame(), fh)
    out_path = tmp_path / "out" / "intervention_demand.yml"

    result = build_demand(war_path=war_path, out_path=out_path)
    assert out_path.exists()
    loaded = yaml.safe_load(out_path.read_text())
    assert loaded["totals"]["modu_band_rig_days_floor"] == 20
    assert loaded["bands"]["band_500_3000"]["distinct_wells"] == 2
    assert result["depth_coverage"]["records_missing_water_depth"] == 1


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
    assert set(bands) == {
        "shelf_lt_500",
        "band_500_3000",
        "band_3000_5000",
        "band_5000_10000",
        "band_gt_10000",
    }
    # Some deepwater rig-days and a positive per-well rate must be on record.
    deep_rig_days = sum(
        bands[k]["total_rig_days_floor"]
        for k in ("band_3000_5000", "band_5000_10000", "band_gt_10000")
    )
    assert deep_rig_days > 0
    assert all(b["is_floor"] for b in bands.values())
    assert result["totals"]["modu_band_distinct_wells_floor"] > 0
    assert result["totals"]["modu_band_rig_days_floor"] > 0
