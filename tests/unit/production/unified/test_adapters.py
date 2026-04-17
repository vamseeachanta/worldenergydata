"""Tests for all 8 regional production adapters."""

import pandas as pd
import pytest

from worldenergydata.production.unified.adapters.brazil_anp_adapter import (
    BrazilAnpAdapter,
)
from worldenergydata.production.unified.adapters.bsee_adapter import BseeAdapter
from worldenergydata.production.unified.adapters.canada_adapter import CanadaAdapter
from worldenergydata.production.unified.adapters.eia_us_adapter import EiaUsAdapter
from worldenergydata.production.unified.adapters.mexico_cnh_adapter import (
    MexicoCnhAdapter,
)
from worldenergydata.production.unified.adapters.sodir_adapter import SodirAdapter
from worldenergydata.production.unified.adapters.texas_rrc_adapter import (
    TexasRrcAdapter,
)
from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery

_ALL_ADAPTERS = [
    SodirAdapter,
    BseeAdapter,
    BrazilAnpAdapter,
    UkcsAdapter,
    EiaUsAdapter,
    MexicoCnhAdapter,
    TexasRrcAdapter,
    CanadaAdapter,
]


def _default_query(adapter):
    return ProductionQuery(regions=[adapter.region])


class TestAdapterSchemaCompliance:
    """Every adapter must return all STANDARD_COLUMNS."""

    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_fetch_returns_standard_columns(self, AdapterClass):
        adapter = AdapterClass()
        df = adapter.fetch(_default_query(adapter))
        for col in STANDARD_COLUMNS:
            assert col in df.columns, f"{AdapterClass.__name__} missing column '{col}'"

    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_fetch_returns_dataframe(self, AdapterClass):
        adapter = AdapterClass()
        df = adapter.fetch(_default_query(adapter))
        assert isinstance(df, pd.DataFrame)

    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_fetch_returns_nonempty_data(self, AdapterClass):
        adapter = AdapterClass()
        df = adapter.fetch(_default_query(adapter))
        assert not df.empty

    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_region_column_matches_adapter_region(self, AdapterClass):
        adapter = AdapterClass()
        df = adapter.fetch(_default_query(adapter))
        assert (df["region"] == adapter.region).all()

    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_numeric_columns_non_negative(self, AdapterClass):
        adapter = AdapterClass()
        df = adapter.fetch(_default_query(adapter))
        for col in ("oil_bbl", "gas_mcf", "water_bbl", "condensate_bbl"):
            assert (
                df[col] >= 0
            ).all(), f"{AdapterClass.__name__}: negative values in '{col}'"

    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_year_and_month_are_integers(self, AdapterClass):
        adapter = AdapterClass()
        df = adapter.fetch(_default_query(adapter))
        assert df["year"].dtype in (int, "int64", "int32")
        assert df["month"].dtype in (int, "int64", "int32")

    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_month_values_in_range(self, AdapterClass):
        adapter = AdapterClass()
        df = adapter.fetch(_default_query(adapter))
        assert df["month"].between(1, 12).all()


class TestAdapterFieldFiltering:
    def test_sodir_field_filter(self):
        adapter = SodirAdapter()
        q = ProductionQuery(regions=["ncs"], fields=["Edvard Grieg"])
        df = adapter.fetch(q)
        assert set(df["field_name"].unique()) == {"Edvard Grieg"}

    def test_bsee_field_filter(self):
        adapter = BseeAdapter()
        q = ProductionQuery(regions=["gom"], fields=["Atlantis"])
        df = adapter.fetch(q)
        assert set(df["field_name"].unique()) == {"Atlantis"}

    def test_field_filter_case_insensitive(self):
        adapter = SodirAdapter()
        q = ProductionQuery(regions=["ncs"], fields=["edvard grieg"])
        df = adapter.fetch(q)
        assert not df.empty

    def test_unknown_field_returns_empty(self):
        adapter = SodirAdapter()
        q = ProductionQuery(regions=["ncs"], fields=["NonExistent Field XYZ"])
        df = adapter.fetch(q)
        assert df.empty


class TestAdapterDateFiltering:
    def test_sodir_date_filter_start(self):
        adapter = SodirAdapter()
        q = ProductionQuery(regions=["ncs"], start="2020-01")
        df = adapter.fetch(q)
        assert (df["year"] >= 2020).all()

    def test_sodir_date_filter_end(self):
        adapter = SodirAdapter()
        q = ProductionQuery(regions=["ncs"], end="2018-12")
        df = adapter.fetch(q)
        assert (
            (df["year"] < 2019) | ((df["year"] == 2018) & (df["month"] <= 12))
        ).all()

    def test_bsee_date_filter_range(self):
        adapter = BseeAdapter()
        q = ProductionQuery(regions=["gom"], start="2015-01", end="2017-12")
        df = adapter.fetch(q)
        periods = df["year"] * 100 + df["month"]
        assert (periods >= 201501).all()
        assert (periods <= 201712).all()


class TestAdapterMetadata:
    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_available_fields_returns_list(self, AdapterClass):
        adapter = AdapterClass()
        fields = adapter.available_fields()
        assert isinstance(fields, list)
        assert len(fields) > 0

    @pytest.mark.parametrize("AdapterClass", _ALL_ADAPTERS)
    def test_date_range_returns_tuple_of_strings(self, AdapterClass):
        adapter = AdapterClass()
        start, end = adapter.date_range()
        assert isinstance(start, str)
        assert isinstance(end, str)
        assert "-" in start
        assert "-" in end


class TestSpecificAdapterFields:
    def test_sodir_has_expected_fields(self):
        adapter = SodirAdapter()
        fields = adapter.available_fields()
        assert "Edvard Grieg" in fields
        assert "Valhall" in fields
        assert "Ivar Aasen" in fields
        assert "Solveig" in fields

    def test_bsee_has_expected_fields(self):
        adapter = BseeAdapter()
        fields = adapter.available_fields()
        assert "Atlantis" in fields
        assert "Thunder Horse" in fields
        assert "Mars-Ursa" in fields
        assert "Na Kika" in fields

    def test_brazil_has_expected_fields(self):
        adapter = BrazilAnpAdapter()
        fields = adapter.available_fields()
        assert "Lula" in fields
        assert "Búzios" in fields
        assert "Mero" in fields
        assert "Marlim" in fields

    def test_ukcs_has_expected_fields(self):
        adapter = UkcsAdapter()
        fields = adapter.available_fields()
        assert "Forties" in fields
        assert "Buzzard" in fields
        assert "Mariner" in fields
        assert "Clair Ridge" in fields

    def test_canada_has_expected_fields(self):
        adapter = CanadaAdapter()
        fields = adapter.available_fields()
        assert "Hibernia" in fields
        assert "Terra Nova" in fields
        assert "White Rose" in fields
