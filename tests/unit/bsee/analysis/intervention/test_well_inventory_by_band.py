# ABOUTME: Unit tests for the well-inventory-by-band module (worldenergydata #583).
# ABOUTME: Pure-function band classification + aggregation on synthetic frames; real-data run is skip-if-missing.

"""Unit tests for worldenergydata.bsee.analysis.intervention.well_inventory_by_band."""

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
    MODU_SERVICING_BANDS,
    band_counts,
    build_inventory,
    classify_modu_band,
    reconcile,
    subsea_inventory_by_band,
    well_population_by_band,
)

_REAL_REGISTRY = Path(
    "/mnt/ace/worldenergydata/data/modules/bsee/bin/permstruc/mv_subsea_boreholes.bin"
)


class TestClassifyModuBand:
    @pytest.mark.parametrize(
        "depth_ft,expected",
        [
            (0, "shelf_lt_500"),
            (499.9, "shelf_lt_500"),
            (500, "band_500_3000"),  # lower edge is inclusive into the next band
            (2999, "band_500_3000"),
            (3000, "band_3000_5000"),
            (4999, "band_3000_5000"),
            (5000, "band_5000_10000"),
            (9999, "band_5000_10000"),
            (10000, "band_gt_10000"),
            (15000, "band_gt_10000"),
        ],
    )
    def test_edges(self, depth_ft, expected):
        assert classify_modu_band(depth_ft) == expected

    def test_missing_and_invalid_return_none(self):
        assert classify_modu_band(None) is None
        assert classify_modu_band(float("nan")) is None
        assert classify_modu_band("not-a-number") is None
        assert classify_modu_band(-10) is None


class TestBandCounts:
    def test_counts_and_unknown_bucket(self):
        depths = [100, 600, 1500, 3500, 4999, 6000, 9000, 12000, None, float("nan")]
        counts = band_counts(depths)
        assert counts["shelf_lt_500"] == 1
        assert counts["band_500_3000"] == 2
        assert counts["band_3000_5000"] == 2
        assert counts["band_5000_10000"] == 2
        assert counts["band_gt_10000"] == 1
        assert counts["unknown"] == 2
        # all real depths accounted for
        assert sum(counts.values()) == len(depths)

    def test_ordered_keys_present_even_when_zero(self):
        counts = band_counts([6000])
        assert list(counts.keys())[: len(BAND_LABELS)] == list(BAND_LABELS.keys())
        assert counts["shelf_lt_500"] == 0


class TestAggregation:
    def test_subsea_inventory_counts_and_stats(self):
        reg = pd.DataFrame({"WATER_DEPTH": [1055, 2000, 4609, 4000, 9627]})
        inv = subsea_inventory_by_band(reg)
        assert inv["counts"]["band_500_3000"] == 2
        assert inv["counts"]["band_3000_5000"] == 2
        assert inv["counts"]["band_5000_10000"] == 1
        assert inv["stats"]["min_ft"] == 1055.0
        assert inv["stats"]["max_ft"] == 9627.0
        assert inv["stats"]["median_ft"] == 4000.0
        assert inv["stats"]["count"] == 5

    def test_population_and_reconcile_share(self):
        reg = pd.DataFrame({"WATER_DEPTH": [4000, 4500]})  # 2 subsea in 3k-5k
        wells = pd.DataFrame({"WATER_DEPTH": [4000, 4500, 4800, 4900]})  # 4 total
        inv = subsea_inventory_by_band(reg)
        pop = well_population_by_band(wells)
        rec = reconcile(inv, pop)
        band = rec["band_3000_5000"]
        assert band["subsea_wells_on_record"] == 2
        assert band["total_wells_in_band"] == 4
        assert band["subsea_share"] == 0.5
        assert band["modu_servicing"] is True
        # shelf band is not MODU-servicing
        assert rec["shelf_lt_500"]["modu_servicing"] is False

    def test_reconcile_handles_empty_band(self):
        inv = subsea_inventory_by_band(pd.DataFrame({"WATER_DEPTH": [4000]}))
        rec = reconcile(inv, well_population_by_band(pd.DataFrame({"WATER_DEPTH": [4000]})))
        assert rec["shelf_lt_500"]["subsea_share"] is None  # no wells -> None, not div0


class TestModuServicingBands:
    def test_shelf_excluded(self):
        assert "shelf_lt_500" not in MODU_SERVICING_BANDS
        assert "band_5000_10000" in MODU_SERVICING_BANDS


@pytest.mark.skipif(
    not _REAL_REGISTRY.exists(),
    reason="BSEE subsea-borehole registry not available (no /mnt/ace data)",
)
class TestRealData:
    def test_known_on_record_band_counts(self):
        # Regression lock on the 2026-06-25 on-record figures.
        data_dir = _REAL_REGISTRY.parents[2]  # .../modules/bsee
        result = build_inventory(data_dir=data_dir, include_population=False)
        bands = result["bands"]
        assert bands["band_500_3000"]["subsea_wells_on_record"] == 114
        assert bands["band_3000_5000"]["subsea_wells_on_record"] == 209
        assert bands["band_5000_10000"]["subsea_wells_on_record"] == 270
        assert result["subsea_total"] == 593
        assert bands["shelf_lt_500"]["subsea_wells_on_record"] == 0
