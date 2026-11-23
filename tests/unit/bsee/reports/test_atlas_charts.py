"""Unit tests for atlas_charts pure data-prep + figure builders."""

import numpy as np
import pandas as pd

from tests.test_markers import unit


def _frame():
    """Synthetic per-field frame covering filter edge cases.

    - deep_keep: material, >=3 wells, has WD, Lower Tertiary -> kept
    - shelf_keep: material, >=3 wells, has WD, not LT -> kept
    - tiny_oil: CUM_OIL < 1 -> dropped
    - few_wells: WELL_COUNT < 3 -> dropped
    - no_wd: WATER_DEPTH_AVG null -> dropped
    """
    return pd.DataFrame(
        {
            "FIELD_CODE": ["1", "2", "3", "4", "5"],
            "FIELD_NAME": ["deep_keep", "shelf_keep", "tiny_oil", "few_wells", "no_wd"],
            "GEOLOGICAL_ERA": [
                "Paleocene",
                "Miocene",
                "Miocene",
                "Eocene",
                "Pliocene",
            ],
            "IS_LOWER_TERTIARY": [True, False, False, True, False],
            "WATER_DEPTH_AVG": [7000.0, 400.0, 5000.0, 6000.0, np.nan],
            "WELL_COUNT": [12, 20, 8, 2, 10],
            "CUM_OIL_MMBBL": [200.0, 150.0, 0.5, 50.0, 80.0],
            "CUM_GAS_BCF": [100.0, 90.0, 1.0, 30.0, 40.0],
            "PEAK_OIL_BOPD": [50000.0, 40000.0, 1000.0, 9000.0, 20000.0],
            "REC_PER_WELL_MMBBL": [16.6, 7.5, 0.06, 25.0, 8.0],
            "AVG_BOPD_PER_WELL": [11000.0, 3000.0, 100.0, 9000.0, 4000.0],
            "DOMINANT_OPERATOR": ["A", "B", "C", "A", "B"],
        }
    )


@unit
class TestAccessScatterFrame:
    def test_filters_applied(self):
        from worldenergydata.bsee.reports.atlas_charts import access_scatter_frame

        out = access_scatter_frame(_frame())
        names = set(out["FIELD_NAME"])
        assert names == {"deep_keep", "shelf_keep"}

    def test_drops_count(self):
        from worldenergydata.bsee.reports.atlas_charts import access_scatter_frame

        df = _frame()
        out = access_scatter_frame(df)
        assert len(out) == 2
        # 5 total, 3 dropped (tiny_oil, few_wells, no_wd)
        assert len(df) - len(out) == 3

    def test_handles_missing_columns(self):
        from worldenergydata.bsee.reports.atlas_charts import access_scatter_frame

        out = access_scatter_frame(pd.DataFrame({"FIELD_CODE": ["1"]}))
        assert out.empty

    def test_empty(self):
        from worldenergydata.bsee.reports.atlas_charts import access_scatter_frame

        out = access_scatter_frame(pd.DataFrame())
        assert out.empty


@unit
class TestRecPerWellByEra:
    def test_cohort_threshold(self):
        from worldenergydata.bsee.reports.atlas_charts import rec_per_well_by_era

        # Build a frame with one era having 3 fields, another with 1.
        df = pd.DataFrame(
            {
                "GEOLOGICAL_ERA": ["Miocene", "Miocene", "Miocene", "Eocene"],
                "REC_PER_WELL_MMBBL": [10.0, 20.0, 30.0, 99.0],
                "IS_LOWER_TERTIARY": [False, False, False, True],
            }
        )
        out = rec_per_well_by_era(df)
        assert list(out["GEOLOGICAL_ERA"]) == ["Miocene"]
        # median of 10,20,30 = 20
        assert out.iloc[0]["MEDIAN_REC_PER_WELL"] == 20.0
        assert out.iloc[0]["FIELD_COUNT"] == 3

    def test_drops_unknown_era(self):
        from worldenergydata.bsee.reports.atlas_charts import rec_per_well_by_era

        df = pd.DataFrame(
            {
                "GEOLOGICAL_ERA": ["Unknown"] * 4,
                "REC_PER_WELL_MMBBL": [1.0, 2.0, 3.0, 4.0],
                "IS_LOWER_TERTIARY": [False] * 4,
            }
        )
        out = rec_per_well_by_era(df)
        assert out.empty

    def test_lt_flag_per_cohort(self):
        from worldenergydata.bsee.reports.atlas_charts import rec_per_well_by_era

        df = pd.DataFrame(
            {
                "GEOLOGICAL_ERA": ["Paleocene"] * 3,
                "REC_PER_WELL_MMBBL": [5.0, 6.0, 7.0],
                "IS_LOWER_TERTIARY": [True, True, True],
            }
        )
        out = rec_per_well_by_era(df)
        assert bool(out.iloc[0]["IS_LOWER_TERTIARY"]) is True

    def test_material_filter_excludes_nonproducing(self):
        from worldenergydata.bsee.reports.atlas_charts import rec_per_well_by_era

        # 3 producing Eocene fields + 3 near-zero exploration Eocene fields.
        # Only the producing ones should drive the median (the paleo era map
        # tags exploration fields, which must not drag the cohort to ~0).
        df = pd.DataFrame(
            {
                "GEOLOGICAL_ERA": ["Eocene"] * 6,
                "REC_PER_WELL_MMBBL": [3.0, 4.0, 5.0, 0.0, 0.0, 0.0],
                "CUM_OIL_MMBBL": [50.0, 60.0, 70.0, 0.0, 0.0, 0.0],
                "WELL_COUNT": [10, 12, 14, 1, 1, 1],
                "IS_LOWER_TERTIARY": [True] * 6,
            }
        )
        out = rec_per_well_by_era(df)
        assert list(out["GEOLOGICAL_ERA"]) == ["Eocene"]
        assert out.iloc[0]["FIELD_COUNT"] == 3  # exploration fields excluded
        assert out.iloc[0]["MEDIAN_REC_PER_WELL"] == 4.0  # median of 3,4,5

    def test_empty(self):
        from worldenergydata.bsee.reports.atlas_charts import rec_per_well_by_era

        assert rec_per_well_by_era(pd.DataFrame()).empty


@unit
class TestWaterDepthSplit:
    def test_split_counts(self):
        from worldenergydata.bsee.reports.atlas_charts import water_depth_split

        out = water_depth_split(_frame())
        # WD present: 7000, 400, 5000, 6000 (no_wd dropped) = 4
        assert out["n_with_depth"] == 4
        # deepwater >1000: 7000,5000,6000 = 3; shelf: 400 = 1
        assert out["n_deepwater"] == 3
        assert out["n_shelf"] == 1

    def test_medians(self):
        from worldenergydata.bsee.reports.atlas_charts import water_depth_split

        out = water_depth_split(_frame())
        assert out["deepwater_median_ft"] == 6000.0
        assert out["shelf_median_ft"] == 400.0

    def test_empty(self):
        from worldenergydata.bsee.reports.atlas_charts import water_depth_split

        out = water_depth_split(pd.DataFrame())
        assert out["n_with_depth"] == 0
        assert out["n_deepwater"] == 0


@unit
class TestFigureBuilders:
    def test_access_scatter_figure(self):
        import plotly.graph_objects as go

        from worldenergydata.bsee.reports.atlas_charts import (
            access_scatter_figure,
            access_scatter_frame,
        )

        sub = access_scatter_frame(_frame())
        fig = access_scatter_figure(sub)
        assert isinstance(fig, go.Figure)

    def test_access_scatter_figure_empty(self):
        import plotly.graph_objects as go

        from worldenergydata.bsee.reports.atlas_charts import access_scatter_figure

        fig = access_scatter_figure(pd.DataFrame())
        assert isinstance(fig, go.Figure)

    def test_rec_per_well_figure(self):
        import plotly.graph_objects as go

        from worldenergydata.bsee.reports.atlas_charts import (
            rec_per_well_by_era,
            rec_per_well_figure,
        )

        df = pd.DataFrame(
            {
                "GEOLOGICAL_ERA": ["Miocene", "Miocene", "Miocene"],
                "REC_PER_WELL_MMBBL": [10.0, 20.0, 30.0],
                "IS_LOWER_TERTIARY": [False, False, False],
            }
        )
        fig = rec_per_well_figure(rec_per_well_by_era(df))
        assert isinstance(fig, go.Figure)

    def test_water_depth_figure(self):
        import plotly.graph_objects as go

        from worldenergydata.bsee.reports.atlas_charts import water_depth_figure

        fig = water_depth_figure(_frame())
        assert isinstance(fig, go.Figure)
