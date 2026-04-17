"""Tests for Alaska field-level production breakdown."""

import pandas as pd
import pytest

from worldenergydata.eia_us.production.alaska_production import (
    ALASKA_FIELDS,
    AlaskaFieldRecord,
    AlaskaProductionLoader,
)


def make_mock_alaska_response(field: str, n_months: int = 12):
    """Mock Alaska field production data."""
    records = []
    base_rate = {"Prudhoe Bay": 300_000, "Kuparuk": 100_000, "Point Thomson": 10_000}
    rate = base_rate.get(field, 50_000)
    for i in range(n_months):
        year = 2023 + i // 12
        month = (i % 12) + 1
        records.append(
            {
                "period": f"{year}-{month:02d}",
                "field": field,
                "crude_bopd": rate - i * 500,
                "ngl_bopd": rate * 0.05,
            }
        )
    return records


class TestAlaskaFields:
    def test_prudhoe_bay_in_fields(self):
        assert "Prudhoe Bay" in ALASKA_FIELDS

    def test_kuparuk_in_fields(self):
        assert "Kuparuk" in ALASKA_FIELDS

    def test_point_thomson_in_fields(self):
        assert "Point Thomson" in ALASKA_FIELDS

    def test_at_least_3_fields(self):
        assert len(ALASKA_FIELDS) >= 3


class TestAlaskaFieldRecord:
    def test_record_has_required_attributes(self):
        rec = AlaskaFieldRecord(
            period="2024-01",
            field="Prudhoe Bay",
            crude_bopd=290_000.0,
            ngl_bopd=15_000.0,
        )
        assert rec.field == "Prudhoe Bay"
        assert rec.crude_bopd == pytest.approx(290_000.0)
        assert rec.ngl_bopd == pytest.approx(15_000.0)

    def test_record_total_liquids(self):
        rec = AlaskaFieldRecord(
            period="2024-01",
            field="Kuparuk",
            crude_bopd=100_000.0,
            ngl_bopd=5_000.0,
        )
        assert rec.total_liquids_bopd == pytest.approx(105_000.0)


class TestAlaskaProductionLoader:
    @pytest.fixture
    def loader(self):
        return AlaskaProductionLoader()

    def test_load_returns_dataframe(self, loader):
        raw = make_mock_alaska_response("Prudhoe Bay", 12)
        df = loader.load(raw)
        assert isinstance(df, pd.DataFrame)

    def test_load_has_required_columns(self, loader):
        raw = make_mock_alaska_response("Prudhoe Bay", 6)
        df = loader.load(raw)
        for col in ["period", "field", "crude_bopd", "ngl_bopd"]:
            assert col in df.columns

    def test_load_empty_returns_empty_dataframe(self, loader):
        df = loader.load([])
        assert df.empty

    def test_load_three_fields(self, loader):
        all_records = []
        for field in ["Prudhoe Bay", "Kuparuk", "Point Thomson"]:
            all_records.extend(make_mock_alaska_response(field, 6))
        df = loader.load(all_records)
        fields_found = df["field"].unique()
        assert "Prudhoe Bay" in fields_found
        assert "Kuparuk" in fields_found
        assert "Point Thomson" in fields_found

    def test_prudhoe_bay_largest_producer(self, loader):
        all_records = []
        for field in ["Prudhoe Bay", "Kuparuk", "Point Thomson"]:
            all_records.extend(make_mock_alaska_response(field, 12))
        df = loader.load(all_records)
        totals = df.groupby("field")["crude_bopd"].sum()
        assert totals["Prudhoe Bay"] > totals["Kuparuk"]
        assert totals["Kuparuk"] > totals["Point Thomson"]

    def test_filter_field(self, loader):
        all_records = []
        for field in ["Prudhoe Bay", "Kuparuk"]:
            all_records.extend(make_mock_alaska_response(field, 6))
        df = loader.load(all_records)
        filtered = loader.filter_field(df, "Prudhoe Bay")
        assert all(filtered["field"] == "Prudhoe Bay")

    def test_crude_bopd_non_negative(self, loader):
        raw = make_mock_alaska_response("Prudhoe Bay", 12)
        df = loader.load(raw)
        assert all(df["crude_bopd"] >= 0)
