"""Tests for PipelineSpecLookup — API 5L pipe schedule matching."""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.spec_lookup import PipelineSpecLookup


@pytest.fixture
def sample_schedule_data(tmp_path):
    """Minimal pipe schedule CSV for unit tests."""
    rows = [
        # nps, od_mm, od_in, schedule, wt_mm, wt_in, weight_kgm, grade_range, standard, domain_hint
        (
            10.0,
            273.05,
            10.750,
            "STD",
            9.27,
            0.365,
            60.31,
            "X52-X80",
            "API 5L",
            "infield_pipeline",
        ),
        (
            10.0,
            273.05,
            10.750,
            "XS",
            12.70,
            0.500,
            81.55,
            "X52-X80",
            "API 5L",
            "infield_pipeline",
        ),
        (
            12.0,
            323.85,
            12.750,
            "STD",
            9.53,
            0.375,
            73.78,
            "X52-X80",
            "API 5L",
            "infield_pipeline",
        ),
        (
            20.0,
            508.00,
            20.000,
            "STD",
            9.53,
            0.375,
            116.33,
            "X52-X80",
            "API 5L",
            "export_pipeline",
        ),
        (
            21.0,
            533.40,
            21.000,
            "RISER_BORE_HW",
            25.40,
            1.000,
            321.70,
            "X65-X80",
            "API 5L / API STD 16F",
            "offshore_riser_bore",
        ),  # noqa: E501
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "nps_in",
            "od_mm",
            "od_in",
            "schedule",
            "wt_mm",
            "wt_in",
            "weight_kgm",
            "grade_range",
            "standard",
            "domain_hint",
        ],
    )
    csv_path = tmp_path / "api_5l_pipe_schedule.csv"
    df.to_csv(csv_path, index=False)
    return tmp_path


class TestPipelineSpecLookupBasics:
    def test_load_returns_dataframe(self, sample_schedule_data):
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        df = lookup.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_missing_data_returns_empty(self, tmp_path):
        lookup = PipelineSpecLookup(data_dir=tmp_path / "nonexistent")
        df = lookup.load()
        assert df.empty

    def test_caches_on_second_load(self, sample_schedule_data):
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        df1 = lookup.load()
        df2 = lookup.load()
        assert df1 is df2

    def test_get_all_nps_sizes(self, sample_schedule_data):
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        sizes = lookup.get_all_nps_sizes()
        assert 10.0 in sizes
        assert 21.0 in sizes

    def test_nps_summary(self, sample_schedule_data):
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        summary = lookup.nps_summary()
        assert "STD" in summary[10.0]
        assert "XS" in summary[10.0]

    def test_get_by_nps(self, sample_schedule_data):
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.get_by_nps(10.0)
        assert len(result) == 2
        assert all(result["nps_in"] == 10.0)


class TestPipelineSpecLookupMatchOdWt:
    def test_match_10_75in_od_exact(self, sample_schedule_data):
        """0.27305m OD → NPS 10 exact OD match."""
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.27305, 0.00927)
        assert result is not None
        assert result["nps_in"] == 10.0
        assert result["schedule"] == "STD"

    def test_match_10_75in_od_approximate(self, sample_schedule_data):
        """0.2731m (common OrcaFlex value) → NPS 10 within 3mm tolerance."""
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.2731, 0.012)
        assert result is not None
        assert result["nps_in"] == 10.0

    def test_match_xs_schedule_by_wt(self, sample_schedule_data):
        """Same OD, different WT → selects XS based on WT proximity."""
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.27305, 0.01270)  # XS wall thickness
        assert result is not None
        assert result["nps_in"] == 10.0
        assert result["schedule"] == "XS"

    def test_match_21in_riser_bore(self, sample_schedule_data):
        """0.5334m OD (21\" riser bore) → NPS 21 RISER_BORE_HW entry."""
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.5334, 0.025)
        assert result is not None
        assert result["nps_in"] == 21.0
        assert "offshore_riser_bore" in result["domain_hint"]

    def test_no_match_far_od(self, sample_schedule_data):
        """OD far from all table entries → None."""
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.100, 0.010)  # 100mm OD — not in table
        assert result is None

    def test_result_has_required_keys(self, sample_schedule_data):
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.27305, 0.00927)
        assert result is not None
        for key in (
            "nps_in",
            "od_mm",
            "schedule",
            "wt_mm",
            "grade_range",
            "standard",
            "source",
        ):
            assert key in result, f"Missing key: {key}"

    def test_result_source_attribution(self, sample_schedule_data):
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.27305, 0.00927)
        assert result is not None
        assert "PipelineSpecLookup" in result["source"]

    def test_match_od_only_zero_wt(self, sample_schedule_data):
        """wt_m=0 → match by OD only, returns first entry."""
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.27305, 0.0)
        assert result is not None
        assert result["nps_in"] == 10.0

    def test_grade_range_is_list(self, sample_schedule_data):
        lookup = PipelineSpecLookup(data_dir=sample_schedule_data)
        result = lookup.match_od_wt(0.27305, 0.00927)
        assert result is not None
        assert isinstance(result["grade_range"], list)

    def test_empty_data_returns_none(self, tmp_path):
        lookup = PipelineSpecLookup(data_dir=tmp_path / "empty")
        result = lookup.match_od_wt(0.27305, 0.00927)
        assert result is None


class TestPipelineSpecLookupIntegration:
    """Integration tests against the live api_5l_pipe_schedule.csv."""

    def test_curated_csv_covers_nps_4_to_36(self):
        lookup = PipelineSpecLookup()
        sizes = lookup.get_all_nps_sizes()
        assert 4.0 in sizes, 'NPS 4" missing from table'
        assert 36.0 in sizes, 'NPS 36" missing from table'
        assert len(sizes) >= 14, f"Expected ≥14 NPS sizes, got {len(sizes)}"

    def test_curated_match_10_75in_od(self):
        """Standard OrcaFlex pipeline OD: 0.2731m (10.75\")."""
        lookup = PipelineSpecLookup()
        result = lookup.match_od_wt(0.2731, 0.012)
        assert result is not None
        assert result["nps_in"] == 10.0

    def test_curated_match_21in_riser_bore(self):
        """Acceptance criterion: 0.5334m → NPS 21 riser bore entry."""
        lookup = PipelineSpecLookup()
        result = lookup.match_od_wt(0.5334, 0.025)
        assert result is not None
        assert result["nps_in"] == 21.0

    def test_curated_csv_has_std_xs_schedules(self):
        lookup = PipelineSpecLookup()
        summary = lookup.nps_summary()
        # Every NPS should have at least STD or XS
        for nps, schedules in summary.items():
            assert len(schedules) >= 1, f'NPS {nps}" has no schedules'

    def test_curated_csv_has_sufficient_rows(self):
        lookup = PipelineSpecLookup()
        df = lookup.load()
        assert len(df) >= 30, f"Expected ≥30 rows, got {len(df)}"

    def test_import_from_bsee_pipeline(self):
        """Verify the public import path works."""
        from worldenergydata.bsee.pipeline import PipelineSpecLookup as PSL

        lookup = PSL()
        assert lookup is not None
