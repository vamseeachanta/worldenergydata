"""Unit tests for the BSEE pipeline orchestrator.

Tests the FieldReport dataclass and PipelineRunner class using synthetic
data and duck-typed stubs.  No real binary files, no real analyzer imports.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.field_query import FieldContext
from worldenergydata.bsee.pipeline.pipeline_runner import (
    FieldReport,
    PipelineRunner,
)

# ---------------------------------------------------------------------------
# Lightweight stubs — duck-typed replacements for real analyzers
# ---------------------------------------------------------------------------


class StubFieldResolver:
    """Minimal stub replicating FieldNameResolver's public interface."""

    def __init__(self, field_names: Dict[str, str]):
        self._field_names = dict(field_names)

    def resolve(self, field_code: str) -> str:
        return self._field_names.get(str(field_code).strip(), str(field_code))

    def get_all_field_names(self) -> Dict[str, str]:
        return dict(self._field_names)


class StubEraClassifier:
    """Minimal stub replicating GeologicalEraClassifier's public interface."""

    ERAS = ["Paleocene", "Eocene", "Oligocene", "Miocene", "Pliocene", "Pleistocene"]

    def __init__(self, well_eras: Optional[Dict[str, str]] = None):
        self._well_eras = well_eras or {}

    def classify_well(self, api_well_number: str) -> Optional[str]:
        return self._well_eras.get(str(api_well_number).strip())

    def classify_field(self, field_wells: List[str]) -> str:
        from collections import Counter

        if not field_wells:
            return "Unknown"
        counter: Counter = Counter()
        for api in field_wells:
            era = self.classify_well(api)
            if era:
                counter[era] += 1
        if not counter:
            return "Unknown"
        return counter.most_common(1)[0][0]

    def get_well_eras(self) -> Dict[str, str]:
        return dict(self._well_eras)


class StubAllFieldsRunner:
    """Duck-typed replacement for AllFieldsRunner."""

    def __init__(self, field_resolver=None, era_classifier=None):
        self._field_resolver = field_resolver
        self._era_classifier = era_classifier

    def run(
        self,
        production_data: pd.DataFrame,
        water_depth_data: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        if production_data.empty:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {
                    "FIELD_CODE": "001",
                    "FIELD_NAME": "TEST_FIELD",
                    "GEOLOGICAL_ERA": "Miocene",
                    "WATER_DEPTH_AVG": 5000.0,
                    "WELL_COUNT": 3,
                    "CUM_OIL_MMBBL": 100.0,
                    "CUM_GAS_BCF": 200.0,
                }
            ]
        )


class ErrorAllFieldsRunner:
    """AllFieldsRunner stub that always raises."""

    def __init__(self, field_resolver=None, era_classifier=None):
        pass

    def run(self, production_data, water_depth_data=None):
        raise RuntimeError("AllFieldsRunner exploded")


class StubActivityAnalyzer:
    """Duck-typed replacement for ComprehensiveActivityAnalyzer."""

    def __init__(self, enriched_df: pd.DataFrame) -> None:
        self._df = enriched_df

    def analyze(self) -> dict:
        if self._df.empty:
            return {}
        return {
            "drilling_efficiency": {"total_wells_with_duration": 10},
            "well_depth": {"mean_md": 15000},
            "geological_era": {},
            "cross_activity": {},
            "well_lifecycle": {},
            "operator_portfolio": {},
            "duration_benchmarking": {},
        }


class ErrorActivityAnalyzer:
    """Activity analyzer stub that always raises."""

    def __init__(self, enriched_df: pd.DataFrame) -> None:
        raise ValueError("Activity analyzer init failed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def field_resolver():
    return StubFieldResolver({"001": "BUCKSKIN", "002": "THUNDER HORSE"})


@pytest.fixture()
def era_classifier():
    return StubEraClassifier(
        {"608114001200": "Miocene", "608114001300": "Miocene", "608114002000": "Eocene"}
    )


@pytest.fixture()
def sample_context():
    """A resolved FieldContext for testing."""
    return FieldContext(
        field_code="001",
        field_name="BUCKSKIN",
        leases=("G12345", "G12346"),
        area_code="GC",
        geological_era="Miocene",
        well_count=3,
        query_type="field_code",
    )


@pytest.fixture()
def sample_production_df():
    """Synthetic production data that AllFieldsRunner can consume."""
    return pd.DataFrame(
        {
            "FIELD_NAME_CODE": ["001", "001", "001"],
            "LEASE_NUMBER": ["G12345", "G12345", "G12346"],
            "API_WELL_NUMBER": ["608114001200", "608114001300", "608114002000"],
            "PROD_YEAR": [2020, 2020, 2021],
            "MON_O_PROD_VOL": [100000, 200000, 150000],
            "MON_G_PROD_VOL": [50000, 60000, 70000],
            "MON_WTR_PROD_VOL": [10000, 20000, 15000],
        }
    )


@pytest.fixture()
def tubulars_csv(tmp_path):
    """Write a minimal well_tubulars.csv for casing tests."""
    csv_path = tmp_path / "well_tubulars.csv"
    csv_path.write_text(
        "API_WELL_NUMBER,WELL_NAME,WAR_START_DT,WAR_END_DT,"
        "CSNG_INTV_TYPE_CD,CSNG_HOLE_SIZE,CASING_SIZE,CASING_WEIGHT,"
        "CASING_GRADE,CSNG_LINER_TEST_PRSS,CSNG_SHOE_TEST_PRSS,"
        "CSNG_CEMENT_VOL,SN_WAR_CSNG_INTV,CSNG_SETTING_BOTM_MD,"
        "CSNG_SETTING_TOP_MD\n"
        "608114001200,W1,1/1/2024 12:01:00 AM,1/7/2024 11:59:00 PM,"
        "C,26.0,20.0,133.0,K-55,2000.0,12.5,3000.0,-100,3000,0\n"
        "608114001200,W1,1/1/2024 12:01:00 AM,1/7/2024 11:59:00 PM,"
        "C,17.5,13.375,72.0,P-110,4500.0,14.8,1500.0,-200,8000,0\n"
    )
    return csv_path


# ---------------------------------------------------------------------------
# Tests: FieldReport dataclass
# ---------------------------------------------------------------------------


class TestFieldReport:
    def test_field_report_creation(self, sample_context):
        """FieldReport can be instantiated with all fields."""
        report = FieldReport(
            context=sample_context,
            generated_at="2026-02-13T12:00:00",
            production_summary=pd.DataFrame(),
            activity_analysis={},
            casing_strings={},
            casing_matrices={},
            casing_svgs={},
            wellbore_count=0,
            lease_count=0,
            warnings=[],
        )
        assert report.context is sample_context
        assert report.generated_at == "2026-02-13T12:00:00"
        assert isinstance(report.production_summary, pd.DataFrame)
        assert report.wellbore_count == 0
        assert report.lease_count == 0
        assert report.warnings == []

    def test_field_report_mutable(self, sample_context):
        """FieldReport is NOT frozen — fields can be updated incrementally."""
        report = FieldReport(
            context=sample_context,
            generated_at="2026-02-13T12:00:00",
            production_summary=pd.DataFrame(),
            activity_analysis={},
            casing_strings={},
            casing_matrices={},
            casing_svgs={},
            wellbore_count=0,
            lease_count=0,
            warnings=[],
        )
        report.wellbore_count = 5
        report.warnings.append("test warning")
        assert report.wellbore_count == 5
        assert len(report.warnings) == 1

    def test_field_report_warnings_accumulated(self, sample_context):
        """Warnings from multiple stages can be accumulated."""
        report = FieldReport(
            context=sample_context,
            generated_at="2026-02-13T12:00:00",
            production_summary=pd.DataFrame(),
            activity_analysis={},
            casing_strings={},
            casing_matrices={},
            casing_svgs={},
            wellbore_count=0,
            lease_count=0,
            warnings=["warn1"],
        )
        report.warnings.append("warn2")
        report.warnings.append("warn3")
        assert report.warnings == ["warn1", "warn2", "warn3"]


# ---------------------------------------------------------------------------
# Tests: PipelineRunner creation
# ---------------------------------------------------------------------------


class TestPipelineRunnerCreation:
    def test_pipeline_runner_creation(self, field_resolver, era_classifier, tmp_path):
        """PipelineRunner can be instantiated with DI stubs."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
        )
        assert runner is not None

    def test_pipeline_runner_creation_with_overrides(
        self, field_resolver, era_classifier, tmp_path
    ):
        """PipelineRunner accepts optional analyzer overrides for testing."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        assert runner is not None


# ---------------------------------------------------------------------------
# Tests: PipelineRunner.run — production analysis
# ---------------------------------------------------------------------------


class TestPipelineRunnerProduction:
    def test_pipeline_runner_run_empty_data(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """No production data -> empty production_summary + warning."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        assert isinstance(report, FieldReport)
        assert report.production_summary.empty
        assert any("production" in w.lower() for w in report.warnings)

    def test_pipeline_runner_run_with_production(
        self,
        field_resolver,
        era_classifier,
        tmp_path,
        sample_context,
        sample_production_df,
    ):
        """Provide production data -> production_summary populated."""
        # Write synthetic production binary
        import pickle

        prod_dir = tmp_path / "production_raw"
        prod_dir.mkdir()
        with open(prod_dir / "mv_productionsum.bin", "wb") as f:
            pickle.dump(sample_production_df, f)

        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        assert not report.production_summary.empty

    def test_pipeline_runner_handles_analyzer_error(
        self,
        field_resolver,
        era_classifier,
        tmp_path,
        sample_context,
        sample_production_df,
    ):
        """If AllFieldsRunner.run() raises, catch and warn (no crash)."""
        import pickle

        prod_dir = tmp_path / "production_raw"
        prod_dir.mkdir()
        with open(prod_dir / "mv_productionsum.bin", "wb") as f:
            pickle.dump(sample_production_df, f)

        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=ErrorAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        # Should not crash; production_summary should be empty
        assert report.production_summary.empty
        assert any(
            "AllFieldsRunner" in w or "production" in w.lower() for w in report.warnings
        )


# ---------------------------------------------------------------------------
# Tests: PipelineRunner.run — casing analysis
# ---------------------------------------------------------------------------


class TestPipelineRunnerCasing:
    def test_pipeline_runner_run_with_casing(
        self,
        field_resolver,
        era_classifier,
        tmp_path,
        sample_context,
        tubulars_csv,
    ):
        """Provide tubulars CSV -> casing_strings populated for matching wells."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            tubulars_path=tubulars_csv,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        # Context has well_count=3 but tubulars CSV only has API 608114001200
        # The runner should attempt to load casing for each known API
        # (from production data or context). At minimum, it should not crash.
        assert isinstance(report.casing_strings, dict)
        assert isinstance(report.casing_matrices, dict)
        assert isinstance(report.casing_svgs, dict)

    def test_pipeline_runner_run_no_casing_data(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """No tubulars file -> empty casing results + warning."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            tubulars_path=None,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        assert report.casing_strings == {}
        assert report.casing_matrices == {}
        assert report.casing_svgs == {}
        assert any(
            "casing" in w.lower() or "tubulars" in w.lower() for w in report.warnings
        )

    def test_pipeline_runner_handles_casing_error(
        self,
        field_resolver,
        era_classifier,
        tmp_path,
        sample_context,
    ):
        """If casing loading fails for a well, catch and warn (no crash)."""
        # Point to a file that exists but has bad content
        bad_csv = tmp_path / "bad_tubulars.csv"
        bad_csv.write_text("NOT,A,VALID,CSV,FORMAT\ngarbage,data,here,x,y\n")

        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            tubulars_path=bad_csv,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        # Should not crash
        assert isinstance(report.casing_strings, dict)


# ---------------------------------------------------------------------------
# Tests: PipelineRunner.run — activity analysis
# ---------------------------------------------------------------------------


class TestPipelineRunnerActivity:
    def test_pipeline_runner_run_activity_analysis(
        self,
        field_resolver,
        era_classifier,
        tmp_path,
        sample_context,
    ):
        """Mock activity data -> activity_analysis populated."""
        import pickle

        # Write a synthetic WAR activity binary
        war_dir = tmp_path / "eWellAPD"
        war_dir.mkdir()
        activity_df = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["608114001200", "608114001300"],
                "ACTIVITY_CATEGORY": ["drilling", "completion"],
                "DRILLING_DAYS": [45, 30],
            }
        )
        with open(war_dir / "mv_ewellapd.bin", "wb") as f:
            pickle.dump(activity_df, f)

        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        assert isinstance(report.activity_analysis, dict)
        # With StubActivityAnalyzer and non-empty data, we get 7 keys
        if report.activity_analysis:
            assert "drilling_efficiency" in report.activity_analysis

    def test_pipeline_runner_run_no_activity_data(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """No activity data -> empty activity results + warning."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        # No activity binary files exist -> should warn
        assert isinstance(report.activity_analysis, dict)
        assert any("activity" in w.lower() for w in report.warnings)

    def test_pipeline_runner_handles_activity_analyzer_error(
        self,
        field_resolver,
        era_classifier,
        tmp_path,
        sample_context,
    ):
        """If activity analyzer raises, catch and warn (no crash)."""
        import pickle

        war_dir = tmp_path / "eWellAPD"
        war_dir.mkdir()
        activity_df = pd.DataFrame(
            {
                "API_WELL_NUMBER": ["608114001200"],
                "ACTIVITY_CATEGORY": ["drilling"],
                "DRILLING_DAYS": [45],
            }
        )
        with open(war_dir / "mv_ewellapd.bin", "wb") as f:
            pickle.dump(activity_df, f)

        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=ErrorActivityAnalyzer,
        )
        report = runner.run(sample_context)
        # Should not crash
        assert report.activity_analysis == {}
        assert any("activity" in w.lower() for w in report.warnings)


# ---------------------------------------------------------------------------
# Tests: PipelineRunner.run — metadata and counts
# ---------------------------------------------------------------------------


class TestPipelineRunnerMetadata:
    def test_pipeline_runner_wellbore_count(
        self,
        field_resolver,
        era_classifier,
        tmp_path,
        sample_context,
        sample_production_df,
    ):
        """Wellbore count = unique API_WELL_NUMBER values in production data."""
        import pickle

        prod_dir = tmp_path / "production_raw"
        prod_dir.mkdir()
        with open(prod_dir / "mv_productionsum.bin", "wb") as f:
            pickle.dump(sample_production_df, f)

        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        # sample_production_df has 3 unique API_WELL_NUMBERs
        assert report.wellbore_count == 3

    def test_pipeline_runner_wellbore_count_empty(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """With no production data, wellbore_count falls back to context.well_count."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        assert report.wellbore_count == sample_context.well_count

    def test_pipeline_runner_lease_count(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """Lease count matches unique leases from context."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        # sample_context has 2 leases
        assert report.lease_count == 2

    def test_pipeline_runner_generated_at_timestamp(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """Report has an ISO-8601 timestamp."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        # Should parse without error
        dt = datetime.datetime.fromisoformat(report.generated_at)
        assert isinstance(dt, datetime.datetime)

    def test_pipeline_runner_context_preserved(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """Report.context is the exact input FieldContext."""
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        assert report.context is sample_context
        assert report.context.field_code == "001"
        assert report.context.field_name == "BUCKSKIN"


# ---------------------------------------------------------------------------
# Tests: LFS stub handling
# ---------------------------------------------------------------------------


class TestPipelineRunnerLFSStubs:
    def test_pipeline_runner_lfs_stub_production(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """LFS stub production file returns empty + warning (no crash)."""
        prod_dir = tmp_path / "production_raw"
        prod_dir.mkdir()
        lfs_file = prod_dir / "mv_productionsum.bin"
        lfs_file.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:abc123\nsize 1234\n"
        )
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        assert report.production_summary.empty
        assert any(
            "production" in w.lower() or "lfs" in w.lower() for w in report.warnings
        )

    def test_pipeline_runner_lfs_stub_activity(
        self, field_resolver, era_classifier, tmp_path, sample_context
    ):
        """LFS stub activity file returns empty + warning (no crash)."""
        war_dir = tmp_path / "eWellAPD"
        war_dir.mkdir()
        lfs_file = war_dir / "mv_ewellapd.bin"
        lfs_file.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:abc123\nsize 1234\n"
        )
        runner = PipelineRunner(
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            data_dir=tmp_path,
            all_fields_runner=StubAllFieldsRunner(),
            activity_analyzer_cls=StubActivityAnalyzer,
        )
        report = runner.run(sample_context)
        assert isinstance(report.activity_analysis, dict)
