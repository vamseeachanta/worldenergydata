"""Tests for multi-source query dispatcher and cross-source benchmarking.

Covers MultiSourceQuery (register, query, query_all, error handling,
availability matrix) and CrossSourceBenchmark (compare_production,
compare_wellbore_counts, compare_drilling_activity, summary, edge cases).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.adapters.benchmarking import (
    CrossSourceBenchmark,
)
from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterInterface,
    AdapterResult,
    DataAvailability,
    DomainStatus,
    SourceMetadata,
)
from worldenergydata.bsee.pipeline.adapters.multi_source_query import (
    MultiSourceQuery,
)

# ---------------------------------------------------------------------------
# Stub adapters
# ---------------------------------------------------------------------------


class StubBSEE(AdapterInterface):
    """Simulates BSEE with production + wellbore + drilling data."""

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        return AdapterResult(
            source=self.get_metadata(),
            field_code="GC001",
            field_name=query.upper(),
            leases=("G00001", "G00002"),
            well_count=12,
            wellbore_summary=pd.DataFrame(
                {
                    "well_id": ["W1", "W2", "W3"],
                    "status": ["producing", "plugged", "producing"],
                    "depth_m": [3000, 2500, 4000],
                }
            ),
            drilling_activities=pd.DataFrame(
                {
                    "well_id": ["W1", "W2"],
                    "spud_date": ["2020-01-15", "2021-06-01"],
                    "duration_days": [45, 60],
                }
            ),
            production=pd.DataFrame(
                {
                    "date": ["2024-01", "2024-02"],
                    "oil_m3": [1500.0, 1400.0],
                    "gas_m3": [500000.0, 480000.0],
                }
            ),
            casing_strings=pd.DataFrame(
                {
                    "well_id": ["W1"],
                    "casing_od_mm": [339.7],
                    "grade": ["L80"],
                }
            ),
        )

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata("bsee", "BSEE", "US Federal Offshore")

    def get_availability(self) -> DataAvailability:
        return DataAvailability(
            source_id="bsee",
            source_name="BSEE",
            jurisdiction="US Federal Offshore",
            wellbore=DomainStatus("available"),
            drilling_completion=DomainStatus("available"),
            production=DomainStatus("available"),
            casing=DomainStatus("available"),
        )


class StubSODIR(AdapterInterface):
    """Simulates SODIR with production + wellbore, no casing."""

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        return AdapterResult(
            source=self.get_metadata(),
            field_code="NPD42",
            field_name=query.upper(),
            leases=("PL001",),
            well_count=8,
            wellbore_summary=pd.DataFrame(
                {
                    "well_id": ["N1", "N2"],
                    "status": ["producing", "producing"],
                    "depth_m": [2800, 3100],
                }
            ),
            production=pd.DataFrame(
                {
                    "date": ["2024-01", "2024-02"],
                    "oil_m3": [2000.0, 1900.0],
                    "gas_m3": [300000.0, 290000.0],
                }
            ),
        )

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata("sodir", "Sodir", "Norwegian Continental Shelf")

    def get_availability(self) -> DataAvailability:
        return DataAvailability(
            source_id="sodir",
            source_name="Sodir",
            jurisdiction="Norwegian Continental Shelf",
            wellbore=DomainStatus("available"),
            production=DomainStatus("partial", "field-level only"),
        )


class StubEmpty(AdapterInterface):
    """Simulates a source with no data (all empty DataFrames)."""

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        return AdapterResult(
            source=self.get_metadata(),
            field_code="",
            field_name=query.upper(),
            leases=(),
            well_count=0,
        )

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata("empty", "Empty Source", "Nowhere")

    def get_availability(self) -> DataAvailability:
        return DataAvailability(
            source_id="empty",
            source_name="Empty Source",
            jurisdiction="Nowhere",
        )


class StubFailing(AdapterInterface):
    """Adapter that always raises on adapt()."""

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        raise RuntimeError(f"Simulated failure for '{query}'")

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata("fail", "Failing Source", "Error Land")

    def get_availability(self) -> DataAvailability:
        return DataAvailability(
            source_id="fail",
            source_name="Failing Source",
            jurisdiction="Error Land",
        )


# ---------------------------------------------------------------------------
# MultiSourceQuery tests
# ---------------------------------------------------------------------------


class TestMultiSourceQueryRegistration:
    def test_empty_by_default(self):
        msq = MultiSourceQuery()
        assert msq.available_sources() == []

    def test_register_single(self):
        msq = MultiSourceQuery()
        msq.register("bsee", StubBSEE())
        assert msq.available_sources() == ["bsee"]

    def test_register_multiple(self):
        msq = MultiSourceQuery()
        msq.register("bsee", StubBSEE())
        msq.register("sodir", StubSODIR())
        assert msq.available_sources() == ["bsee", "sodir"]

    def test_register_replaces_existing(self):
        msq = MultiSourceQuery()
        msq.register("bsee", StubBSEE())
        msq.register("bsee", StubSODIR())  # replace with different adapter
        result = msq.query("field_x", sources=["bsee"])
        # Should use the replaced adapter (SODIR stub)
        assert result["bsee"].source.source_id == "sodir"

    def test_init_with_adapters_dict(self):
        msq = MultiSourceQuery({"a": StubBSEE(), "b": StubSODIR()})
        assert msq.available_sources() == ["a", "b"]


class TestMultiSourceQueryDispatch:
    def test_query_single_source(self):
        msq = MultiSourceQuery({"bsee": StubBSEE()})
        results = msq.query("Thunder Horse", sources=["bsee"])
        assert len(results) == 1
        assert results["bsee"].field_name == "THUNDER HORSE"
        assert results["bsee"].well_count == 12

    def test_query_all_registered(self):
        msq = MultiSourceQuery(
            {
                "bsee": StubBSEE(),
                "sodir": StubSODIR(),
            }
        )
        results = msq.query("test_field")
        assert set(results.keys()) == {"bsee", "sodir"}

    def test_query_all_convenience(self):
        msq = MultiSourceQuery(
            {
                "bsee": StubBSEE(),
                "sodir": StubSODIR(),
            }
        )
        results = msq.query_all("test_field")
        assert len(results) == 2

    def test_query_subset(self):
        msq = MultiSourceQuery(
            {
                "bsee": StubBSEE(),
                "sodir": StubSODIR(),
                "empty": StubEmpty(),
            }
        )
        results = msq.query("field_x", sources=["bsee", "sodir"])
        assert set(results.keys()) == {"bsee", "sodir"}

    def test_query_unknown_source_ignored(self):
        msq = MultiSourceQuery({"bsee": StubBSEE()})
        results = msq.query("field_x", sources=["bsee", "nonexistent"])
        assert set(results.keys()) == {"bsee"}

    def test_query_empty_sources_list(self):
        msq = MultiSourceQuery({"bsee": StubBSEE()})
        results = msq.query("field_x", sources=[])
        assert results == {}

    def test_query_forwards_kwargs(self):
        class KwargsCapture(StubBSEE):
            captured: dict = {}

            def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
                KwargsCapture.captured = kwargs
                return super().adapt(query, **kwargs)

        msq = MultiSourceQuery({"cap": KwargsCapture()})
        msq.query("field_x", sources=["cap"], district=7, year=2024)
        assert KwargsCapture.captured == {"district": 7, "year": 2024}


class TestMultiSourceQueryErrorHandling:
    def test_failing_adapter_omitted(self):
        msq = MultiSourceQuery(
            {
                "bsee": StubBSEE(),
                "fail": StubFailing(),
            }
        )
        results = msq.query("field_x")
        assert "bsee" in results
        assert "fail" not in results

    def test_all_failing_returns_empty(self):
        msq = MultiSourceQuery({"fail": StubFailing()})
        results = msq.query("field_x")
        assert results == {}

    def test_failing_does_not_affect_others(self):
        msq = MultiSourceQuery(
            {
                "bsee": StubBSEE(),
                "fail": StubFailing(),
                "sodir": StubSODIR(),
            }
        )
        results = msq.query("field_x")
        assert len(results) == 2
        assert results["bsee"].well_count == 12
        assert results["sodir"].well_count == 8


class TestMultiSourceQueryAvailability:
    def test_availability_matrix_structure(self):
        msq = MultiSourceQuery(
            {
                "bsee": StubBSEE(),
                "sodir": StubSODIR(),
            }
        )
        matrix = msq.source_availability_matrix()
        # 2 sources x 6 domains = 12 rows
        assert len(matrix) == 12
        assert all(
            k in matrix[0]
            for k in ("source_id", "source_name", "domain", "status", "notes")
        )

    def test_availability_matrix_empty_registry(self):
        msq = MultiSourceQuery()
        assert msq.source_availability_matrix() == []

    def test_availability_matrix_reflects_adapter(self):
        msq = MultiSourceQuery({"sodir": StubSODIR()})
        matrix = msq.source_availability_matrix()
        prod_row = [r for r in matrix if r["domain"] == "production"][0]
        assert prod_row["status"] == "partial"
        assert prod_row["notes"] == "field-level only"


# ---------------------------------------------------------------------------
# CrossSourceBenchmark tests
# ---------------------------------------------------------------------------


def _make_results() -> dict[str, AdapterResult]:
    """Build a two-source result dict for benchmark tests."""
    msq = MultiSourceQuery(
        {
            "bsee": StubBSEE(),
            "sodir": StubSODIR(),
        }
    )
    return msq.query_all("test_field")


class TestBenchmarkProduction:
    def test_compare_production_merges_sources(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.compare_production()
        assert "source" in df.columns
        assert set(df["source"].unique()) == {"bsee", "sodir"}

    def test_compare_production_row_count(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.compare_production()
        # BSEE: 2 rows, SODIR: 2 rows = 4 total
        assert len(df) == 4

    def test_compare_production_empty_when_no_data(self):
        bench = CrossSourceBenchmark({"empty": StubEmpty().adapt("x")})
        df = bench.compare_production()
        assert df.empty


class TestBenchmarkWellbore:
    def test_compare_wellbore_counts_merges(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.compare_wellbore_counts()
        assert "source" in df.columns
        # BSEE: 3 wells, SODIR: 2 wells = 5 rows
        assert len(df) == 5

    def test_compare_wellbore_counts_empty(self):
        bench = CrossSourceBenchmark({"empty": StubEmpty().adapt("x")})
        df = bench.compare_wellbore_counts()
        assert df.empty


class TestBenchmarkDrilling:
    def test_compare_drilling_activity_merges(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.compare_drilling_activity()
        # Only BSEE has drilling data (2 rows)
        assert len(df) == 2
        assert set(df["source"].unique()) == {"bsee"}

    def test_compare_drilling_activity_empty(self):
        bench = CrossSourceBenchmark({"empty": StubEmpty().adapt("x")})
        df = bench.compare_drilling_activity()
        assert df.empty


class TestBenchmarkSummary:
    def test_summary_row_per_source(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.summary()
        assert len(df) == 2
        assert set(df["source_id"]) == {"bsee", "sodir"}

    def test_summary_columns_present(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.summary()
        expected = {
            "source_id",
            "field_name",
            "well_count",
            "num_available_domains",
            "has_production",
            "has_drilling",
            "has_casing",
        }
        assert expected.issubset(set(df.columns))

    def test_summary_well_counts_correct(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.summary()
        bsee_row = df[df["source_id"] == "bsee"].iloc[0]
        sodir_row = df[df["source_id"] == "sodir"].iloc[0]
        assert bsee_row["well_count"] == 12
        assert sodir_row["well_count"] == 8

    def test_summary_domain_availability(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.summary()
        bsee_row = df[df["source_id"] == "bsee"].iloc[0]
        sodir_row = df[df["source_id"] == "sodir"].iloc[0]
        # BSEE has: wellbore, drilling, production, casing = 4
        assert bsee_row["num_available_domains"] == 4
        # SODIR has: wellbore, production = 2
        assert sodir_row["num_available_domains"] == 2

    def test_summary_boolean_flags(self):
        bench = CrossSourceBenchmark(_make_results())
        df = bench.summary()
        bsee_row = df[df["source_id"] == "bsee"].iloc[0]
        sodir_row = df[df["source_id"] == "sodir"].iloc[0]
        assert bsee_row["has_production"] == True  # noqa: E712
        assert bsee_row["has_drilling"] == True  # noqa: E712
        assert bsee_row["has_casing"] == True  # noqa: E712
        assert sodir_row["has_production"] == True  # noqa: E712
        assert sodir_row["has_drilling"] == False  # noqa: E712
        assert sodir_row["has_casing"] == False  # noqa: E712

    def test_summary_empty_results(self):
        bench = CrossSourceBenchmark({})
        df = bench.summary()
        assert df.empty
        assert "source_id" in df.columns

    def test_summary_single_source_with_no_data(self):
        bench = CrossSourceBenchmark({"empty": StubEmpty().adapt("x")})
        df = bench.summary()
        assert len(df) == 1
        row = df.iloc[0]
        assert row["well_count"] == 0
        assert row["num_available_domains"] == 0
        assert row["has_production"] == False  # noqa: E712
