"""Tests for common schema and adapter interface."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterInterface,
    AdapterResult,
    DataAvailability,
    DomainStatus,
    SourceMetadata,
)


class TestDomainStatus:
    def test_available(self):
        ds = DomainStatus(status="available", notes="Full coverage")
        assert ds.status == "available"
        assert ds.notes == "Full coverage"

    def test_default_notes(self):
        ds = DomainStatus(status="unavailable")
        assert ds.notes == ""

    def test_frozen(self):
        ds = DomainStatus(status="available")
        with pytest.raises(AttributeError):
            ds.status = "unavailable"  # type: ignore[misc]


class TestDataAvailability:
    def test_defaults_to_unavailable(self):
        da = DataAvailability(
            source_id="test",
            source_name="Test Source",
            jurisdiction="Test",
        )
        assert da.wellbore.status == "unavailable"
        assert da.production.status == "unavailable"

    def test_mixed_availability(self):
        da = DataAvailability(
            source_id="test",
            source_name="Test Source",
            jurisdiction="Test",
            wellbore=DomainStatus("available", "full"),
            production=DomainStatus("partial", "totals only"),
        )
        assert da.wellbore.status == "available"
        assert da.production.status == "partial"
        assert da.casing.status == "unavailable"


class TestSourceMetadata:
    def test_creation(self):
        sm = SourceMetadata(
            source_id="bsee",
            source_name="BSEE",
            jurisdiction="US Federal Offshore",
            api_base_url="https://example.com",
            update_cadence="monthly",
        )
        assert sm.source_id == "bsee"
        assert sm.update_cadence == "monthly"


class TestAdapterResult:
    def test_defaults_to_empty_dataframes(self):
        result = AdapterResult(
            source=SourceMetadata("test", "Test", "Test"),
            field_code="001",
            field_name="TEST_FIELD",
            leases=("L001", "L002"),
        )
        assert result.wellbore_summary.empty
        assert result.production.empty
        assert result.warnings == []

    def test_with_data(self):
        prod = pd.DataFrame({"date": ["2025-01"], "oil_m3": [100.0]})
        result = AdapterResult(
            source=SourceMetadata("test", "Test", "Test"),
            field_code="001",
            field_name="TEST_FIELD",
            leases=("L001",),
            production=prod,
        )
        assert len(result.production) == 1
        assert result.production["oil_m3"].iloc[0] == 100.0

    def test_warnings_mutable(self):
        result = AdapterResult(
            source=SourceMetadata("test", "Test", "Test"),
            field_code="001",
            field_name="TEST",
            leases=(),
        )
        result.warnings.append("Casing data unavailable for this source")
        assert len(result.warnings) == 1


class StubAdapter(AdapterInterface):
    """Minimal concrete adapter for testing the interface."""

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        return AdapterResult(
            source=self.get_metadata(),
            field_code="STUB",
            field_name=query.upper(),
            leases=("S001",),
            well_count=5,
        )

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata("stub", "Stub Source", "Test Land")

    def get_availability(self) -> DataAvailability:
        return DataAvailability(
            source_id="stub",
            source_name="Stub Source",
            jurisdiction="Test Land",
            wellbore=DomainStatus("available"),
            production=DomainStatus("partial"),
        )


class TestAdapterInterface:
    def test_adapt_returns_result(self):
        adapter = StubAdapter()
        result = adapter.adapt("test_field")
        assert result.field_name == "TEST_FIELD"
        assert result.well_count == 5

    def test_available_domains(self):
        adapter = StubAdapter()
        domains = adapter.available_domains()
        assert "wellbore" in domains
        assert "production" in domains
        assert "casing" not in domains

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            AdapterInterface()  # type: ignore[abstract]
