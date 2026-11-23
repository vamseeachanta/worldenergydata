"""
Tests for WellProductionDashboard extension of DashboardBuilder.

Tests the integration with verification system and well-specific functionality.
"""

from datetime import datetime, timedelta
from pathlib import Path
from shutil import copyfile
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.well_data_verification import VerificationResult
from worldenergydata.bsee.analysis.well_data_verification.audit import AuditLogger
from worldenergydata.bsee.reports.comprehensive.visualizations.dashboard_builder import (
    ChartConfig,
    DashboardBuilder,
    DashboardConfig,
)
from worldenergydata.well_production_dashboard.export_manager import (
    ExportConfiguration,
    ExportResult,
)

# Import the modules we're testing
from worldenergydata.well_production_dashboard.well_production import (
    FieldAggregator,
    WellDashboardConfig,
    WellMetrics,
    WellProductionDashboard,
)


@pytest.fixture(autouse=True)
def temporary_chunk_cache(monkeypatch, tmp_path):
    """Keep real data-loader caches within each test's temporary directory."""
    from worldenergydata.bsee.data.cache import ChunkManager

    def create_chunk_manager(cache_dir=None):
        return ChunkManager(cache_dir if cache_dir is not None else tmp_path / "chunks")

    for module in ("enhanced.data_refresh_chunked", "refresh.data_refresh_enhanced"):
        monkeypatch.setattr(
            f"worldenergydata.bsee.data.{module}.ChunkManager", create_chunk_manager
        )


@pytest.fixture(scope="session")
def audit_database_template(tmp_path_factory):
    """Build the real audit schema once; each test receives an isolated copy."""
    path = tmp_path_factory.mktemp("audit-template") / "audit.sqlite"
    audit = AuditLogger(path)
    audit.database.close()
    return path


class TestWellProductionDashboard:
    """Test suite for WellProductionDashboard class."""

    @pytest.mark.parametrize("identifier", [" TEST-001 ", "", None, 1, True])
    def test_direct_rejected_identity_stops_before_assessment(
        self, dashboard, sample_well_data, identifier
    ):
        data = sample_well_data.assign(well_id=identifier)
        with patch.object(
            dashboard._verification,
            "assess",
            return_value={"status": "verified", "quality_score": 1.0},
        ) as assess:
            result = dashboard.verify_well_data(data)
        assert result["status"] == "error"
        assert result["quality_score"] is None
        assess.assert_not_called()

    @pytest.fixture
    def sample_well_data(self):
        """Generate sample well production data."""
        dates = pd.date_range(
            start="2023-01-01", end="2023-12-31", freq=pd.offsets.MonthEnd()
        )
        return pd.DataFrame(
            {
                "date": dates,
                "well_id": "TEST-001",
                "oil_production": np.random.uniform(1000, 5000, len(dates)),
                "gas_production": np.random.uniform(500, 2000, len(dates)),
                "water_production": np.random.uniform(100, 500, len(dates)),
                "operating_days": np.random.uniform(25, 31, len(dates)),
                "revenue": np.random.uniform(50000, 200000, len(dates)),
                "opex": np.random.uniform(10000, 50000, len(dates)),
                "verification_status": "verified",
                "quality_score": np.random.uniform(0.8, 1.0, len(dates)),
            }
        )

    @pytest.fixture
    def dashboard_config(self, tmp_path, audit_database_template):
        """Create dashboard configuration."""
        audit_path = tmp_path / "audit.sqlite"
        copyfile(audit_database_template, audit_path)
        return WellDashboardConfig(
            title="Test Well Production Dashboard",
            enable_verification=True,
            enable_real_time=False,
            cache_ttl=300,
            audit_db_path=audit_path.as_posix(),
        )

    @pytest.fixture
    def dashboard(self, dashboard_config):
        """Create WellProductionDashboard instance."""
        return WellProductionDashboard(config=dashboard_config)

    def test_dashboard_initialization(self, dashboard, dashboard_config):
        """Test dashboard initializes correctly."""
        assert dashboard is not None
        assert dashboard.config == dashboard_config
        assert isinstance(dashboard, DashboardBuilder)
        assert dashboard.verification_enabled == True
        assert dashboard.cache_ttl == 300

    def test_extends_dashboard_builder(self, dashboard):
        """Test that WellProductionDashboard extends DashboardBuilder."""
        # Check inheritance
        assert isinstance(dashboard, DashboardBuilder)

        # Check that base methods are available
        assert hasattr(dashboard, "add_chart")
        assert hasattr(dashboard, "add_filter")
        assert callable(dashboard.create_production_dashboard)
        assert callable(dashboard.create_realtime_dashboard)

    def test_load_well_data(self, dashboard, sample_well_data):
        """Test loading well production data."""
        dashboard.load_well_data(sample_well_data)

        assert dashboard.well_data is not None
        assert len(dashboard.well_data) == len(sample_well_data)
        assert "well_id" in dashboard.well_data.columns
        assert "verification_status" in dashboard.well_data.columns

    def test_verification_integration(self, dashboard, sample_well_data):
        """Test integration with verification system."""
        quality = VerificationResult()
        quality.metadata["quality_score"] = 0.95
        with (
            patch.object(
                dashboard.verification_workflow, "validate", return_value=(True, [])
            ) as validate,
            patch.object(
                dashboard.quality_framework, "run_quality_checks", return_value=quality
            ) as check,
        ):
            result = dashboard.verify_well_data(sample_well_data)
        assert result["status"] == "verified"
        assert result["quality_score"] == 0.95
        validate.assert_called_once()
        check.assert_called_once()
        trail = dashboard.get_audit_trail("TEST-001")
        assert trail.iloc[0]["details"]["quality_score"] == 0.95

    def test_create_production_chart(self, dashboard, sample_well_data):
        """Test creation of production charts."""
        dashboard.load_well_data(sample_well_data)
        chart = dashboard.create_production_chart("TEST-001")

        assert chart is not None
        assert chart.chart_type == "production_timeline"
        assert chart.title == "Production Timeline - TEST-001"
        assert chart.data_source == "well_data"

    def test_create_economic_metrics(self, dashboard, sample_well_data):
        """Test creation of economic metrics display."""
        dashboard.load_well_data(sample_well_data)
        metrics = dashboard.create_economic_metrics("TEST-001")

        assert metrics is not None
        assert "npv" in metrics
        assert "total_revenue" in metrics
        assert "total_opex" in metrics
        assert "profit_margin" in metrics

    def test_quality_indicators(self, dashboard, sample_well_data):
        """Display a genuine assessed score and its current quality criterion."""
        dashboard.load_well_data(sample_well_data)
        assert dashboard.get_quality_indicators("TEST-001") == {
            "status": "unverified",
            "quality_score": None,
            "indicator_color": "gray",
            "quality_threshold": dashboard.quality_threshold,
            "reason": "Current observations and quality criterion require verification",
        }
        quality = VerificationResult()
        quality.metadata["quality_score"] = 0.95
        with patch.object(
            dashboard.quality_framework, "run_quality_checks", return_value=quality
        ):
            assert dashboard.verify_well_data(sample_well_data)["status"] == "verified"
        indicators = dashboard.get_quality_indicators("TEST-001")
        assert indicators["status"] == "verified"
        assert indicators["quality_score"] == 0.95
        assert indicators["quality_threshold"] == dashboard.quality_threshold
        assert indicators["indicator_color"] == "green"

    def test_field_aggregation(self, dashboard):
        """Test field-level aggregation."""
        # Create sample data for multiple wells
        field_data = pd.DataFrame(
            {
                "well_id": ["W1", "W2", "W3"] * 12,
                "date": pd.date_range(
                    "2023-01-01", periods=36, freq=pd.offsets.MonthEnd()
                ),
                "oil_production": np.random.uniform(1000, 5000, 36),
                "gas_production": np.random.uniform(500, 2000, 36),
                "water_production": np.full(36, 100.0),
                "field": "TestField",
            }
        )

        aggregator = FieldAggregator()
        result = aggregator.aggregate_field_data(field_data, "TestField")

        assert result is not None
        assert "total_oil" in result.columns
        assert "total_gas" in result.columns
        assert "well_count" in result

    def test_decline_curve_analysis(self, dashboard, sample_well_data):
        """Test decline curve analysis component."""
        dashboard.load_well_data(sample_well_data)
        decline_analysis = dashboard.create_decline_curve("TEST-001")

        assert decline_analysis is not None
        assert "decline_rate" in decline_analysis
        assert "forecast" in decline_analysis
        assert "confidence_interval" in decline_analysis

    def test_authentication_setup(self, dashboard):
        """Test authentication setup when the optional authenticator is absent."""
        with (
            patch.dict("sys.modules", {"worldenergydata.bsee.auth": None}),
            patch(
                "worldenergydata.well_production_dashboard.well_production.MockAuthenticator"
            ) as mock_auth,
        ):
            mock_instance = Mock()
            mock_instance.is_authenticated.return_value = True
            mock_auth.return_value = mock_instance

            dashboard.setup_authentication()

            assert dashboard.authenticator is not None
            assert dashboard.is_authenticated() == True
            mock_auth.assert_called_once_with()

    def test_cache_functionality(self, dashboard, sample_well_data):
        """Test caching functionality."""
        dashboard.load_well_data(sample_well_data)

        # First call should cache
        chart1 = dashboard.create_production_chart("TEST-001", use_cache=True)

        # Second call should use cache
        chart2 = dashboard.create_production_chart("TEST-001", use_cache=True)

        assert chart1 == chart2
        assert dashboard.cache_hits > 0

    def test_real_time_updates(self, dashboard):
        """An unavailable optional transport must not be reported as active."""
        with patch.dict(
            "sys.modules", {"worldenergydata.well_production_dashboard.websocket": None}
        ):
            with pytest.raises(ImportError, match="WebSocket support"):
                dashboard.enable_real_time_updates(interval=5000)
        assert dashboard.real_time_enabled is False
        assert dashboard.websocket_handler is None

    def test_export_functionality(self, dashboard, sample_well_data, tmp_path):
        """Test export delegation using the current result-record interface."""
        dashboard.load_well_data(sample_well_data)
        assert dashboard.verify_data_quality()["status"] == "verified"
        output_path = (tmp_path / "dashboard").as_posix()
        pdf_config = ExportConfiguration(formats=["pdf"])
        excel_config = ExportConfiguration(formats=["excel"])
        pdf_export = ExportResult(
            success=True, format="pdf", file_path=f"{output_path}.pdf"
        )
        excel_export = ExportResult(
            success=True, format="excel", file_path=f"{output_path}.xlsx"
        )
        with patch(
            "worldenergydata.well_production_dashboard.well_production.WellDashboardExportManager",
            autospec=True,
        ) as mock_exporter:
            mock_instance = mock_exporter.return_value
            mock_instance.export_batch.side_effect = [[pdf_export], [excel_export]]
            pdf_result = dashboard.export_dashboard(output_path, pdf_config)
            excel_result = dashboard.export_dashboard(output_path, excel_config)

            assert pdf_result == [pdf_export]
            assert excel_result == [excel_export]
            assert pdf_result[0].success
            assert excel_result[0].success
            calls = mock_instance.export_batch.call_args_list
            assert len(calls) == 2
            assert calls[0].args[1:] == (output_path, pdf_config)
            assert calls[1].args[1:] == (output_path, excel_config)
            metadata = calls[0].args[0]["verification_metadata"]
            assert metadata.quality_score >= dashboard.quality_threshold
            assert metadata.audit_trail_id
            assert len(calls[0].args[0]["well_data"]) == len(sample_well_data)
            mock_exporter.assert_called_once_with()

    def test_filter_functionality(self, dashboard, sample_well_data):
        """Test filtering capabilities."""
        dashboard.load_well_data(sample_well_data)

        # Add filters
        dashboard.configure_filter("date_range", ["2023-01-01", "2023-06-30"])
        dashboard.configure_filter("min_quality_score", 0.9)

        filtered_data = dashboard.apply_filters()

        assert len(filtered_data) < len(sample_well_data)
        assert all(filtered_data["quality_score"] >= 0.9)

    def test_api_endpoints(self, dashboard):
        """Test API endpoint configuration."""
        endpoints = dashboard.get_api_endpoints()

        assert "/api/wells" in endpoints
        assert "/api/wells/{well_id}" in endpoints
        assert "/api/dashboard/data" in endpoints
        assert "/api/dashboard/export" in endpoints

    def test_cli_interface(self):
        """Test CLI interface creation."""
        from worldenergydata.well_production_dashboard.cli import DashboardCLI

        cli = DashboardCLI()

        assert cli is not None
        assert hasattr(cli, "run")
        assert hasattr(cli, "configure")
        assert hasattr(cli, "export")

    def test_yaml_configuration(self, tmp_path):
        """Test YAML-based configuration."""
        config_path = tmp_path / "dashboard_config.yml"
        config_content = """
        dashboard:
          title: Production Dashboard
          enable_verification: true
          cache_ttl: 600
        wells:
          - id: W1
          - id: W2
        filters:
          date_range:
            start: 2023-01-01
            end: 2023-12-31
        """
        config_path.write_text(config_content, encoding="utf-8", newline="\n")

        dashboard = WellProductionDashboard.from_yaml(str(config_path))

        assert dashboard.config.title == "Production Dashboard"
        assert dashboard.config.enable_verification == True
        assert dashboard.config.cache_ttl == 600

    def test_performance_metrics(self, dashboard, sample_well_data):
        """Test performance metrics tracking."""
        import time

        dashboard.load_well_data(sample_well_data)

        start_time = time.time()
        dashboard.create_production_chart("TEST-001")
        end_time = time.time()

        metrics = dashboard.get_performance_metrics()

        assert "render_time" in metrics
        assert "memory_usage" in metrics
        assert "cache_hit_rate" in metrics
        assert metrics["render_time"] < 3.0  # Should render in less than 3 seconds

    def test_error_handling(self, dashboard):
        """Test error handling for invalid data."""
        invalid_data = pd.DataFrame({"invalid": [1, 2, 3]})

        with pytest.raises(ValueError) as exc_info:
            dashboard.load_well_data(invalid_data)

        assert "Missing required columns" in str(exc_info.value)

    def test_audit_trail_integration(self, dashboard, sample_well_data):
        """Test audit trail integration from verification system."""
        dashboard.load_well_data(sample_well_data)

        audit_trail = dashboard.get_audit_trail("TEST-001")

        assert audit_trail is not None
        assert "timestamp" in audit_trail.columns
        assert "action" in audit_trail.columns
        assert "user" in audit_trail.columns
        assert "details" in audit_trail.columns

    def test_verification_requires_audit_storage(self, sample_well_data):
        """Missing persistence must leave a stated, unverified disposition."""
        dashboard = WellProductionDashboard(
            WellDashboardConfig(title="Audit configuration", enable_verification=True)
        )
        result = dashboard.verify_well_data(sample_well_data)
        assert result["status"] == "unverified"
        assert result["quality_score"] is None
        assert "audit" in result["reason"].lower()

    def test_reload_invalidates_verification(
        self, dashboard, sample_well_data, tmp_path
    ):
        dashboard.load_well_data(sample_well_data)
        assert dashboard.verify_data_quality()["status"] == "verified"
        assert dashboard.get_quality_indicators("TEST-001")["status"] == "verified"
        dashboard.load_well_data(sample_well_data.assign(oil_production=100.0))
        assert dashboard.get_quality_indicators("TEST-001")["status"] == "unverified"
        with pytest.raises(ValueError, match="verified"):
            dashboard.export_dashboard((tmp_path / "dashboard").as_posix())

    def test_failed_reverification_clears_prior_status(
        self, dashboard, sample_well_data, tmp_path
    ):
        dashboard.load_well_data(sample_well_data)
        assert dashboard.verify_data_quality()["status"] == "verified"
        invalid = sample_well_data.copy()
        invalid.loc[0, "oil_production"] = np.inf
        result = dashboard.verify_well_data(invalid)
        assert result["status"] != "verified"
        assert result["quality_score"] is None
        assert dashboard.get_quality_indicators("TEST-001")["status"] != "verified"
        with pytest.raises(ValueError, match="verified"):
            dashboard.export_dashboard((tmp_path / "dashboard").as_posix())

    @pytest.mark.parametrize("score", [None, np.nan, np.inf, -0.1, 1.1, True])
    def test_invalid_quality_score_is_not_verified(
        self, dashboard, sample_well_data, score, tmp_path
    ):
        dashboard.load_well_data(sample_well_data)
        assert dashboard.verify_data_quality()["status"] == "verified"
        quality = VerificationResult()
        quality.metadata["quality_score"] = score
        with patch.object(
            dashboard.quality_framework, "run_quality_checks", return_value=quality
        ):
            result = dashboard.verify_well_data(sample_well_data)
        assert result["status"] != "verified"
        assert result["quality_score"] is None
        assert dashboard.get_quality_indicators("TEST-001")["status"] != "verified"
        with pytest.raises(ValueError, match="verified"):
            dashboard.export_dashboard((tmp_path / "dashboard").as_posix())

    def test_missing_requested_well_fails_aggregate(self, dashboard, sample_well_data):
        dashboard.load_well_data(sample_well_data)
        result = dashboard.verify_data_quality(["TEST-001", "MISSING"])
        assert result["status"] != "verified"
        assert result["quality_score"] is None
        assert result["results"]["MISSING"]["status"] == "missing"

    def test_audit_failure_does_not_publish_verified_state(
        self, dashboard, sample_well_data, tmp_path
    ):
        dashboard.load_well_data(sample_well_data)
        assert dashboard.verify_data_quality()["status"] == "verified"
        with patch.object(dashboard.audit_logger, "log_event", side_effect=OSError):
            result = dashboard.verify_well_data(sample_well_data)
        assert result["status"] == "error"
        assert result["quality_score"] is None
        assert dashboard.get_quality_indicators("TEST-001")["status"] != "verified"
        with pytest.raises(ValueError, match="verified"):
            dashboard.export_dashboard((tmp_path / "dashboard").as_posix())

    def test_audit_history_filters_before_applying_a_limit(self, dashboard):
        from worldenergydata.bsee.analysis.well_data_verification.audit.database import (
            AuditEvent,
        )

        events = [
            AuditEvent(
                event_type="verification",
                user_id="dashboard",
                details={"well_id": "OTHER"},
            )
            for _ in range(101)
        ]
        target = AuditEvent(
            event_type="verification",
            user_id="dashboard",
            timestamp=datetime(2020, 1, 1),
            details={"well_id": "TEST-001"},
        )
        with patch.object(dashboard.audit_logger.database, "query") as query:
            query.return_value = []
            dashboard.audit_logger.query_events(limit=None)
            assert "LIMIT" not in query.call_args.args[0]
        with patch.object(
            dashboard.audit_logger, "query_events", return_value=events + [target]
        ) as read:
            trail = dashboard.get_audit_trail("TEST-001")
        assert len(trail) == 1
        assert trail.iloc[0]["details"]["well_id"] == "TEST-001"
        assert read.call_args.kwargs["limit"] is None

    def test_export_requires_successful_verification(
        self, dashboard, sample_well_data, tmp_path
    ):
        dashboard.load_well_data(sample_well_data)
        with pytest.raises(ValueError, match="verified"):
            dashboard.export_dashboard((tmp_path / "dashboard").as_posix())

    def test_indicator_current_criterion(self, dashboard, sample_well_data, tmp_path):
        dashboard.load_well_data(sample_well_data)
        quality = VerificationResult()
        quality.metadata["quality_score"] = 0.95
        with patch.object(
            dashboard.quality_framework, "run_quality_checks", return_value=quality
        ):
            assert dashboard.verify_well_data(sample_well_data)["status"] == "verified"
        dashboard.quality_threshold = 0.96
        indicator = dashboard.get_quality_indicators("TEST-001")
        assert indicator["quality_threshold"] == 0.96
        assert indicator["status"] != "verified"
        assert indicator["quality_score"] is None
        with pytest.raises(ValueError, match="verified"):
            dashboard.export_dashboard((tmp_path / "dashboard").as_posix())
        assert dashboard.verify_data_quality()["status"] == "verified"

    @pytest.mark.parametrize("change", ["volume", "date", "rows"])
    def test_export_rejects_different_observations(
        self, dashboard, sample_well_data, tmp_path, change
    ):
        dashboard.load_well_data(sample_well_data)
        other = sample_well_data.copy()
        if change == "volume":
            other["oil_production"] += 1.0
        elif change == "date":
            other["date"] += timedelta(days=1)
        else:
            other = other.iloc[:-1].copy()
        assert dashboard.verify_well_data(other)["status"] == "verified"
        with patch(
            "worldenergydata.well_production_dashboard.well_production.WellDashboardExportManager",
            autospec=True,
        ) as manager:
            manager.return_value.export_batch.return_value = []
            with pytest.raises(ValueError, match="observations"):
                dashboard.export_dashboard((tmp_path / "dashboard").as_posix())
            manager.return_value.export_batch.assert_not_called()

    @pytest.mark.parametrize("identifier", [None, "", " ", 1, True])
    def test_load_rejects_missing_identifiers(
        self, dashboard, sample_well_data, identifier
    ):
        data = sample_well_data.copy()
        data.loc[0, "well_id"] = identifier
        with pytest.raises(ValueError, match="identif"):
            dashboard.load_well_data(data)

    def test_load_rejects_partial_requested_scope(self, dashboard, sample_well_data):
        with (
            patch.object(dashboard.cache_manager, "get_well_data", return_value=None),
            patch.object(
                dashboard.query_optimizer,
                "get_dashboard_data_optimized",
                return_value={"wells": {"TEST-001": sample_well_data}},
            ),
        ):
            with pytest.raises(ValueError, match="Requested"):
                dashboard.load_well_data(well_ids=["TEST-001", "MISSING"])

    def test_load_accepts_complete_requested_scope(self, dashboard, sample_well_data):
        other = sample_well_data.assign(well_id="TEST-002")
        with (
            patch.object(dashboard.cache_manager, "get_well_data", return_value=None),
            patch.object(
                dashboard.query_optimizer,
                "get_dashboard_data_optimized",
                return_value={
                    "wells": {"TEST-001": sample_well_data, "TEST-002": other}
                },
            ),
        ):
            dashboard.load_well_data(well_ids=["TEST-001", "TEST-002"])
        assert set(dashboard.well_data["well_id"]) == {"TEST-001", "TEST-002"}

    def test_loaded_snapshot_does_not_alias_mutable_input(
        self, dashboard, sample_well_data
    ):
        data = sample_well_data.assign(
            note=[["initial"] for _ in range(len(sample_well_data))]
        )
        dashboard.load_well_data(data)
        data.at[0, "note"].append("changed")
        assert dashboard.get_well_data("TEST-001").at[0, "note"] == ["initial"]

    def test_readback_failure_clears_genuine_prior_verification(
        self, dashboard, sample_well_data, tmp_path
    ):
        dashboard.load_well_data(sample_well_data)
        assert dashboard.verify_data_quality()["status"] == "verified"
        with patch.object(dashboard.audit_logger.database, "query", return_value=[]):
            result = dashboard.verify_well_data(sample_well_data)
        assert result["status"] == "error"
        assert result["quality_score"] is None
        assert dashboard.get_quality_indicators("TEST-001")["status"] != "verified"
        with pytest.raises(ValueError, match="verified"):
            dashboard.export_dashboard((tmp_path / "dashboard").as_posix())


class TestWellMetrics:
    """Test suite for WellMetrics calculator."""

    def test_npv_calculation(self):
        """Test NPV calculation."""
        cash_flows = [100000, 120000, 140000, 130000, 110000]
        discount_rate = 0.1

        metrics = WellMetrics()
        npv = metrics.calculate_npv(cash_flows, discount_rate)

        assert npv > 0
        assert isinstance(npv, float)

    def test_decline_rate_calculation(self):
        """Test decline rate calculation."""
        production = [5000, 4800, 4600, 4400, 4200, 4000]

        metrics = WellMetrics()
        decline_rate = metrics.calculate_decline_rate(production)

        assert decline_rate > 0
        assert decline_rate < 1

    def test_economic_indicators(self):
        """Test economic indicator calculations."""
        revenue = 1000000
        opex = 300000
        capex = 200000

        metrics = WellMetrics()
        indicators = metrics.calculate_economic_indicators(revenue, opex, capex)

        assert "profit_margin" in indicators
        assert "roi" in indicators
        assert "payback_period" in indicators


class TestFieldAggregator:
    """Test suite for FieldAggregator."""

    def test_field_rollup(self):
        """Test field-level data rollup."""
        well_data = pd.DataFrame(
            {
                "well_id": ["W1", "W2", "W3"] * 4,
                "date": pd.date_range(
                    "2023-01-01", periods=12, freq=pd.offsets.MonthEnd()
                ),
                "oil_production": np.random.uniform(1000, 5000, 12),
                "gas_production": np.random.uniform(500, 2000, 12),
                "water_production": np.full(12, 100.0),
                "field": "TestField",
            }
        )

        aggregator = FieldAggregator()
        result = aggregator.rollup_field_data(well_data, "TestField")

        assert result is not None
        assert len(result) == 12  # Monthly aggregation
        assert "total_production" in result.columns

    def test_comparative_analysis(self):
        """Test comparative analysis between fields."""
        field1_data = pd.DataFrame(
            {
                "field": "Field1",
                "total_production": [10000, 11000, 12000],
                "date": pd.date_range(
                    "2023-01-01", periods=3, freq=pd.offsets.MonthEnd()
                ),
            }
        )

        field2_data = pd.DataFrame(
            {
                "field": "Field2",
                "total_production": [8000, 9000, 10000],
                "date": pd.date_range(
                    "2023-01-01", periods=3, freq=pd.offsets.MonthEnd()
                ),
            }
        )

        aggregator = FieldAggregator()
        comparison = aggregator.compare_fields(field1_data, field2_data)

        assert comparison is not None
        assert "performance_ratio" in comparison
        assert "trend_comparison" in comparison
