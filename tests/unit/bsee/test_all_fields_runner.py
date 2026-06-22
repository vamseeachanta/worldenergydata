"""Unit tests for the AllFieldsRunner module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from tests.test_markers import unit


def _make_production_df(field_codes=None):
    """Helper to create sample production data."""
    if field_codes is None:
        field_codes = ["100", "200"]
    rows = []
    for code in field_codes:
        for year in [2020, 2021]:
            rows.append(
                {
                    "FIELD_NAME_CODE": code,
                    "LEASE_NUMBER": f"G{code}01",
                    "API_WELL_NUMBER": f"60805{code}0300",
                    "PROD_YEAR": year,
                    "MON_O_PROD_VOL": 100000.0,
                    "MON_G_PROD_VOL": 500000.0,
                    "MON_WTR_PROD_VOL": 20000.0,
                    "DAYS_ON_PROD": 365,
                    "OPERATOR": "BP",
                }
            )
    return pd.DataFrame(rows)


def _make_water_depth_df():
    """Helper to create sample water depth data."""
    return pd.DataFrame(
        {
            "LEASE_NUMBER": ["G10001", "G20001", "G30001"],
            "MAX_WTR_DPTH": [7000, 3500, 1200],
        }
    )


@unit
class TestAllFieldsRunner:
    """Tests for AllFieldsRunner class."""

    @pytest.fixture
    def mock_resolver(self):
        """Create mock FieldNameResolver."""
        resolver = Mock()
        resolver.resolve.side_effect = lambda code: {
            "100": "Thunder Horse",
            "200": "Mars",
            "300": "Atlantis",
        }.get(code, code)
        resolver.resolve_batch.side_effect = lambda codes: {
            c: resolver.resolve(c) for c in codes
        }
        return resolver

    @pytest.fixture
    def mock_classifier(self):
        """Create mock GeologicalEraClassifier."""
        classifier = Mock()
        classifier.classify_field.side_effect = lambda wells: "Miocene"
        classifier.get_well_eras.return_value = {
            "608051000300": "Miocene",
            "608052000300": "Eocene",
        }
        return classifier

    @pytest.fixture
    def runner(self, mock_resolver, mock_classifier):
        """Create AllFieldsRunner with mocked dependencies."""
        from worldenergydata.bsee.analysis.all_fields_runner import (
            AllFieldsRunner,
        )

        return AllFieldsRunner(
            field_resolver=mock_resolver,
            era_classifier=mock_classifier,
        )

    def test_init(self, mock_resolver, mock_classifier):
        """Test AllFieldsRunner initialization."""
        from worldenergydata.bsee.analysis.all_fields_runner import (
            AllFieldsRunner,
        )

        runner = AllFieldsRunner(
            field_resolver=mock_resolver,
            era_classifier=mock_classifier,
        )
        assert runner._field_resolver is mock_resolver
        assert runner._era_classifier is mock_classifier

    def test_run_with_production_data(self, runner):
        """Test running analysis with valid production data."""
        prod_df = _make_production_df(["100", "200"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "FIELD_CODE" in result.columns
        assert "FIELD_NAME" in result.columns
        assert "GEOLOGICAL_ERA" in result.columns
        assert "CUM_OIL_MMBBL" in result.columns
        assert "CUM_GAS_BCF" in result.columns

    def test_run_empty_production_data(self, runner):
        """Test running with empty production data returns empty result."""
        empty_df = pd.DataFrame(
            columns=[
                "FIELD_NAME_CODE",
                "LEASE_NUMBER",
                "API_WELL_NUMBER",
                "PROD_YEAR",
                "MON_O_PROD_VOL",
                "MON_G_PROD_VOL",
                "MON_WTR_PROD_VOL",
                "DAYS_ON_PROD",
            ]
        )
        water_df = _make_water_depth_df()

        result = runner.run(empty_df, water_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_field_names_resolved(self, runner, mock_resolver):
        """Test that field names are resolved via the resolver."""
        prod_df = _make_production_df(["100"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        assert result.iloc[0]["FIELD_NAME"] == "Thunder Horse"

    def test_geological_era_assigned(self, runner, mock_classifier):
        """Test that geological era is assigned to each field."""
        prod_df = _make_production_df(["100"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        assert result.iloc[0]["GEOLOGICAL_ERA"] == "Miocene"
        mock_classifier.classify_field.assert_called()

    def test_cumulative_production_calculated(self, runner):
        """Test cumulative production is calculated correctly."""
        prod_df = _make_production_df(["100"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        # 2 rows * 100000 barrels = 200000 barrels = 0.2 MMBBL
        cum_oil = result.iloc[0]["CUM_OIL_MMBBL"]
        assert cum_oil == pytest.approx(0.2, rel=0.01)

    def test_well_count_calculated(self, runner):
        """Test well count is calculated per field."""
        prod_df = _make_production_df(["100"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        assert result.iloc[0]["WELL_COUNT"] >= 1

    def test_production_years_tracked(self, runner):
        """Test first and last production years are tracked."""
        prod_df = _make_production_df(["100"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        assert result.iloc[0]["FIRST_PRODUCTION"] == 2020
        assert result.iloc[0]["LAST_PRODUCTION"] == 2021

    def test_water_depth_joined(self, runner):
        """Test water depth is joined from lookup data."""
        prod_df = _make_production_df(["100"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        # Water depth should be populated (may be NaN if no lease match)
        assert "WATER_DEPTH_AVG" in result.columns

    def test_multiple_fields(self, runner):
        """Test analysis with multiple fields."""
        prod_df = _make_production_df(["100", "200", "300"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        assert len(result) == 3
        field_codes = set(result["FIELD_CODE"].tolist())
        assert field_codes == {"100", "200", "300"}

    def test_output_columns_present(self, runner):
        """Test all expected output columns are present."""
        prod_df = _make_production_df(["100"])
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        expected_cols = [
            "FIELD_CODE",
            "FIELD_NAME",
            "GEOLOGICAL_ERA",
            "WATER_DEPTH_AVG",
            "WELL_COUNT",
            "FIRST_PRODUCTION",
            "LAST_PRODUCTION",
            "CUM_OIL_MMBBL",
            "CUM_GAS_BCF",
            "CUM_WATER_MMBBL",
            "PEAK_OIL_BOPD",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_compute_field_production(self, runner):
        """Test _compute_field_production for a single field."""
        prod_df = _make_production_df(["100"])

        result = runner._compute_field_production("100", prod_df)

        assert isinstance(result, dict)
        assert result["FIELD_CODE"] == "100"
        assert "CUM_OIL_MMBBL" in result
        assert "CUM_GAS_BCF" in result
        assert "WELL_COUNT" in result

    def test_sorted_by_cumulative_oil(self, runner):
        """Test output is sorted by cumulative oil descending."""
        # Create data where field 200 has more production
        prod_df = _make_production_df(["100", "200"])
        # Add extra production to field 200
        extra = pd.DataFrame(
            [
                {
                    "FIELD_NAME_CODE": "200",
                    "LEASE_NUMBER": "G20001",
                    "API_WELL_NUMBER": "608052000300",
                    "PROD_YEAR": 2022,
                    "MON_O_PROD_VOL": 500000.0,
                    "MON_G_PROD_VOL": 1000000.0,
                    "MON_WTR_PROD_VOL": 50000.0,
                    "DAYS_ON_PROD": 365,
                }
            ]
        )
        prod_df = pd.concat([prod_df, extra], ignore_index=True)
        water_df = _make_water_depth_df()

        result = runner.run(prod_df, water_df)

        # Field 200 (Mars) should be first (more production)
        assert result.iloc[0]["FIELD_CODE"] == "200"


@unit
class TestBenchmarkingMetrics:
    """Tests for the deterministic benchmarking metrics added to the runner."""

    @pytest.fixture
    def runner(self):
        from worldenergydata.bsee.analysis.all_fields_runner import (
            AllFieldsRunner,
        )

        resolver = Mock()
        resolver.resolve.side_effect = lambda c: c
        classifier = Mock()
        classifier.classify_field.side_effect = lambda w: "Miocene"
        return AllFieldsRunner(resolver, classifier)

    def _multi_well_op_df(self):
        """One field, 3 wells, 2 operators, 2 years."""
        rows = []
        wells = {
            "60805A": ("BP", 600000.0),       # BP dominant
            "60805B": ("BP", 300000.0),
            "60805C": ("Shell", 100000.0),
        }
        for api, (op, oil_per_yr) in wells.items():
            for year in [2020, 2021]:
                rows.append(
                    {
                        "FIELD_NAME_CODE": "100",
                        "LEASE_NUMBER": "G10001",
                        "API_WELL_NUMBER": api,
                        "PROD_YEAR": year,
                        "MON_O_PROD_VOL": oil_per_yr,
                        "MON_G_PROD_VOL": 0.0,
                        "MON_WTR_PROD_VOL": oil_per_yr * 0.5,
                        "DAYS_ON_PROD": 365,
                        "OPERATOR": op,
                    }
                )
        return pd.DataFrame(rows)

    def test_rec_per_well(self, runner):
        df = self._multi_well_op_df()
        row = runner.run(df).iloc[0]
        # cum_oil = (600k+300k+100k)*2yrs = 2,000,000 bbl = 2.0 MMBBL; 3 wells.
        assert row["CUM_OIL_MMBBL"] == pytest.approx(2.0)
        assert row["WELL_COUNT"] == 3
        assert row["REC_PER_WELL_MMBBL"] == pytest.approx(2.0 / 3, rel=1e-3)

    def test_avg_bopd_per_well_via_days(self, runner):
        df = self._multi_well_op_df()
        row = runner.run(df).iloc[0]
        # cum_oil bbl / sum(DAYS_ON_PROD). 6 records * 365 = 2190 days.
        assert row["AVG_BOPD_PER_WELL"] == pytest.approx(2_000_000.0 / 2190, rel=1e-3)

    def test_wor_cum(self, runner):
        df = self._multi_well_op_df()
        row = runner.run(df).iloc[0]
        # water = 0.5 * oil -> WOR = 0.5
        assert row["WOR_CUM"] == pytest.approx(0.5, rel=1e-3)

    def test_operator_share_and_dominant(self, runner):
        df = self._multi_well_op_df()
        row = runner.run(df).iloc[0]
        # BP oil = (600k+300k)*2 = 1.8M of 2.0M total -> 0.9 share.
        assert row["N_OPERATORS"] == 2
        assert row["DOMINANT_OPERATOR"] == "BP"
        assert row["TOP_OPERATOR_SHARE"] == pytest.approx(0.9, rel=1e-3)

    def test_prod_span_yrs(self, runner):
        df = self._multi_well_op_df()
        row = runner.run(df).iloc[0]
        assert row["PROD_SPAN_YRS"] == 2  # 2020..2021 inclusive

    def test_still_producing_via_latest_year(self, runner):
        df = self._multi_well_op_df()  # last prod = 2021
        producing = runner.run(df, latest_year=2021).iloc[0]
        assert bool(producing["STILL_PRODUCING"]) is True
        retired = runner.run(df, latest_year=2025).iloc[0]
        assert bool(retired["STILL_PRODUCING"]) is False

    def test_latest_year_defaults_to_max(self, runner):
        df = self._multi_well_op_df()  # max year 2021
        row = runner.run(df).iloc[0]
        assert bool(row["STILL_PRODUCING"]) is True

    def test_water_depth_from_field_dict(self, runner):
        df = self._multi_well_op_df()
        row = runner.run(df, field_water_depth={"100": 6200.0}).iloc[0]
        assert row["WATER_DEPTH_AVG"] == 6200.0

    def test_field_water_depth_precedence_over_lease(self, runner):
        df = self._multi_well_op_df()
        lease_wd = pd.DataFrame(
            {"LEASE_NUMBER": ["G10001"], "MAX_WTR_DPTH": [1000.0]}
        )
        row = runner.run(
            df, water_depth_data=lease_wd, field_water_depth={"100": 6200.0}
        ).iloc[0]
        assert row["WATER_DEPTH_AVG"] == 6200.0  # field map wins

    def test_field_water_depth_falls_back_to_lease(self, runner):
        df = self._multi_well_op_df()
        lease_wd = pd.DataFrame(
            {"LEASE_NUMBER": ["G10001"], "MAX_WTR_DPTH": [1000.0]}
        )
        # field map has no entry for "100" -> legacy lease path used.
        row = runner.run(
            df, water_depth_data=lease_wd, field_water_depth={"999": 5.0}
        ).iloc[0]
        assert row["WATER_DEPTH_AVG"] == 1000.0

    def test_division_guards_single_year_no_water(self, runner):
        rows = [
            {
                "FIELD_NAME_CODE": "100",
                "LEASE_NUMBER": "G10001",
                "API_WELL_NUMBER": "60805A",
                "PROD_YEAR": 2020,
                "MON_O_PROD_VOL": 0.0,
                "MON_G_PROD_VOL": 0.0,
                "MON_WTR_PROD_VOL": 0.0,
                "DAYS_ON_PROD": 0,
                "OPERATOR": "BP",
            }
        ]
        row = runner.run(pd.DataFrame(rows)).iloc[0]
        # cum_oil == 0 -> guarded metrics are None, not a ZeroDivisionError.
        assert row["WOR_CUM"] is None
        assert row["PEAK_TO_CUM"] is None
        assert row["AVG_BOPD_PER_WELL"] is None

    def test_empty_result_has_new_columns(self, runner):
        empty = pd.DataFrame(
            columns=["FIELD_NAME_CODE", "API_WELL_NUMBER", "PROD_YEAR"]
        )
        result = runner.run(empty)
        for col in [
            "REC_PER_WELL_MMBBL",
            "AVG_BOPD_PER_WELL",
            "PROD_SPAN_YRS",
            "WOR_CUM",
            "PEAK_TO_CUM",
            "N_OPERATORS",
            "TOP_OPERATOR_SHARE",
            "DOMINANT_OPERATOR",
            "STILL_PRODUCING",
        ]:
            assert col in result.columns
