"""Tests for CNH and ANP skeleton adapters.

Both adapters return empty DataFrames and document the gaps with
detailed warnings, serving as placeholders until real data pipelines
are built.
"""

from __future__ import annotations

import pytest

from worldenergydata.bsee.pipeline.adapters.anp_adapter import ANPAdapter
from worldenergydata.bsee.pipeline.adapters.cnh_adapter import CNHAdapter
from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterResult,
    DataAvailability,
    SourceMetadata,
)


# -----------------------------------------------------------------------
# CNH adapter tests
# -----------------------------------------------------------------------

class TestCNHAdapterAdapt:
    """Test CNHAdapter.adapt() returns correct empty results."""

    def test_returns_adapter_result(self):
        result = CNHAdapter().adapt("cantarell")
        assert isinstance(result, AdapterResult)

    def test_all_dataframes_empty(self):
        result = CNHAdapter().adapt("ku_maloob_zaap")
        assert result.wellbore_summary.empty
        assert result.well_paths.empty
        assert result.casing_strings.empty
        assert result.drilling_activities.empty
        assert result.completion_activities.empty
        assert result.intervention_activities.empty
        assert result.production.empty

    def test_well_count_is_zero(self):
        result = CNHAdapter().adapt("cantarell")
        assert result.well_count == 0

    def test_leases_empty(self):
        result = CNHAdapter().adapt("cantarell")
        assert result.leases == ()

    def test_field_code_from_query(self):
        result = CNHAdapter().adapt("cantarell")
        assert result.field_code == "cantarell"
        assert result.field_name == "cantarell"

    def test_warnings_non_empty(self):
        result = CNHAdapter().adapt("cantarell")
        assert len(result.warnings) >= 7
        assert any("stub" in w.lower() for w in result.warnings)

    def test_region_kwarg_accepted(self):
        result = CNHAdapter().adapt("test", region="sureste")
        # No extra warning for valid region
        assert not any("Unrecognised region" in w for w in result.warnings)

    def test_invalid_region_adds_warning(self):
        result = CNHAdapter().adapt("test", region="invalid_region")
        assert any("Unrecognised region" in w for w in result.warnings)

    def test_contract_round_kwarg_accepted(self):
        result = CNHAdapter().adapt("test", contract_round="R01")
        assert not any("Unrecognised contract" in w for w in result.warnings)

    def test_invalid_contract_round_adds_warning(self):
        result = CNHAdapter().adapt("test", contract_round="R99")
        assert any("Unrecognised contract round" in w for w in result.warnings)


class TestCNHAdapterMetadata:
    """Test CNHAdapter.get_metadata()."""

    def test_returns_source_metadata(self):
        meta = CNHAdapter().get_metadata()
        assert isinstance(meta, SourceMetadata)

    def test_source_id(self):
        meta = CNHAdapter().get_metadata()
        assert meta.source_id == "cnh"

    def test_sih_url_in_api_base(self):
        meta = CNHAdapter().get_metadata()
        assert "sih.hidrocarburos.gob.mx" in meta.api_base_url

    def test_jurisdiction(self):
        meta = CNHAdapter().get_metadata()
        assert "Mexican" in meta.jurisdiction


class TestCNHAdapterAvailability:
    """Test CNHAdapter.get_availability() and available_domains()."""

    def test_returns_data_availability(self):
        avail = CNHAdapter().get_availability()
        assert isinstance(avail, DataAvailability)

    def test_source_id_matches(self):
        avail = CNHAdapter().get_availability()
        assert avail.source_id == "cnh"

    def test_available_domains_partial_only(self):
        domains = CNHAdapter().available_domains()
        # CNH has drilling_completion=partial and production=partial
        assert "drilling_completion" in domains
        assert "production" in domains
        # Fully unavailable domains excluded
        assert "casing" not in domains
        assert "well_path" not in domains


# -----------------------------------------------------------------------
# ANP adapter tests
# -----------------------------------------------------------------------

class TestANPAdapterAdapt:
    """Test ANPAdapter.adapt() returns correct empty results."""

    def test_returns_adapter_result(self):
        result = ANPAdapter().adapt("lula")
        assert isinstance(result, AdapterResult)

    def test_all_dataframes_empty(self):
        result = ANPAdapter().adapt("buzios")
        assert result.wellbore_summary.empty
        assert result.well_paths.empty
        assert result.casing_strings.empty
        assert result.drilling_activities.empty
        assert result.completion_activities.empty
        assert result.intervention_activities.empty
        assert result.production.empty

    def test_well_count_is_zero(self):
        result = ANPAdapter().adapt("lula")
        assert result.well_count == 0

    def test_leases_empty(self):
        result = ANPAdapter().adapt("lula")
        assert result.leases == ()

    def test_field_code_from_query(self):
        result = ANPAdapter().adapt("buzios")
        assert result.field_code == "buzios"
        assert result.field_name == "buzios"

    def test_warnings_non_empty(self):
        result = ANPAdapter().adapt("lula")
        assert len(result.warnings) >= 7
        assert any("no brazil_anp module" in w.lower() for w in result.warnings)

    def test_warnings_reference_open_data_portal(self):
        result = ANPAdapter().adapt("lula")
        assert any("gov.br/anp" in w for w in result.warnings)


class TestANPAdapterMetadata:
    """Test ANPAdapter.get_metadata()."""

    def test_returns_source_metadata(self):
        meta = ANPAdapter().get_metadata()
        assert isinstance(meta, SourceMetadata)

    def test_source_id(self):
        meta = ANPAdapter().get_metadata()
        assert meta.source_id == "anp"

    def test_anp_url_in_api_base(self):
        meta = ANPAdapter().get_metadata()
        assert "gov.br/anp" in meta.api_base_url

    def test_jurisdiction(self):
        meta = ANPAdapter().get_metadata()
        assert "Brazilian" in meta.jurisdiction

    def test_pre_salt_mentioned(self):
        meta = ANPAdapter().get_metadata()
        assert "pre-salt" in meta.jurisdiction


class TestANPAdapterAvailability:
    """Test ANPAdapter.get_availability() and available_domains()."""

    def test_returns_data_availability(self):
        avail = ANPAdapter().get_availability()
        assert isinstance(avail, DataAvailability)

    def test_source_id_matches(self):
        avail = ANPAdapter().get_availability()
        assert avail.source_id == "anp"

    def test_all_domains_unavailable(self):
        domains = ANPAdapter().available_domains()
        assert domains == []

    def test_every_domain_is_unavailable(self):
        avail = ANPAdapter().get_availability()
        for domain in (
            "wellbore", "well_path", "casing",
            "drilling_completion", "intervention", "production",
        ):
            assert getattr(avail, domain).status == "unavailable"
