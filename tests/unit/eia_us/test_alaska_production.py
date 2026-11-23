"""Alaska record-transform tests using synthetic labels and generated rates.

These fixtures do not represent measured field production.
"""

import pandas as pd
import pytest

from worldenergydata.eia_us.production.alaska_production import (
    ALASKA_FIELDS,
    AlaskaFieldRecord,
    AlaskaProductionLoader,
)


def make_mock_alaska_response(field: str, n_months: int = 12):
    """Generate synthetic monthly rates, not measured field production."""
    records = []
    base_rate = {
        "Synthetic Field A": 300_000,
        "Synthetic Field B": 100_000,
        "Synthetic Field C": 10_000,
    }
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
    def test_synthetic_field_a_in_fields(self):
        assert "Synthetic Field A" in ALASKA_FIELDS

    def test_synthetic_field_b_in_fields(self):
        assert "Synthetic Field B" in ALASKA_FIELDS

    def test_synthetic_field_c_in_fields(self):
        assert "Synthetic Field C" in ALASKA_FIELDS

    def test_at_least_3_fields(self):
        assert len(ALASKA_FIELDS) >= 3


class TestAlaskaFieldRecord:
    def test_record_has_required_attributes(self):
        rec = AlaskaFieldRecord(
            period="2024-01",
            field="Synthetic Field A",
            crude_bopd=290_000.0,
            ngl_bopd=15_000.0,
        )
        assert rec.field == "Synthetic Field A"
        assert rec.crude_bopd == pytest.approx(290_000.0)
        assert rec.ngl_bopd == pytest.approx(15_000.0)

    def test_record_total_liquids(self):
        rec = AlaskaFieldRecord(
            period="2024-01",
            field="Synthetic Field B",
            crude_bopd=100_000.0,
            ngl_bopd=5_000.0,
        )
        assert rec.total_liquids_bopd == pytest.approx(105_000.0)


class TestAlaskaProductionLoader:
    @pytest.fixture
    def loader(self):
        return AlaskaProductionLoader()

    def test_load_returns_dataframe(self, loader):
        raw = make_mock_alaska_response("Synthetic Field A", 12)
        df = loader.load(raw)
        assert isinstance(df, pd.DataFrame)

    def test_load_has_required_columns(self, loader):
        raw = make_mock_alaska_response("Synthetic Field A", 6)
        df = loader.load(raw)
        for col in ["period", "field", "crude_bopd", "ngl_bopd"]:
            assert col in df.columns

    def test_load_empty_returns_empty_dataframe(self, loader):
        df = loader.load([])
        assert df.empty

    def test_load_three_fields(self, loader):
        all_records = []
        for field in ["Synthetic Field A", "Synthetic Field B", "Synthetic Field C"]:
            all_records.extend(make_mock_alaska_response(field, 6))
        df = loader.load(all_records)
        fields_found = df["field"].unique()
        assert "Synthetic Field A" in fields_found
        assert "Synthetic Field B" in fields_found
        assert "Synthetic Field C" in fields_found

    def test_synthetic_rate_ordering(self, loader):
        all_records = []
        for field in ["Synthetic Field A", "Synthetic Field B", "Synthetic Field C"]:
            all_records.extend(make_mock_alaska_response(field, 12))
        df = loader.load(all_records)
        totals = df.groupby("field")["crude_bopd"].sum()
        assert totals["Synthetic Field A"] > totals["Synthetic Field B"]
        assert totals["Synthetic Field B"] > totals["Synthetic Field C"]

    def test_filter_field(self, loader):
        all_records = []
        for field in ["Synthetic Field A", "Synthetic Field B"]:
            all_records.extend(make_mock_alaska_response(field, 6))
        df = loader.load(all_records)
        filtered = loader.filter_field(df, "Synthetic Field A")
        assert len(filtered) == 6
        assert all(filtered["field"] == "Synthetic Field A")

    def test_crude_bopd_non_negative(self, loader):
        raw = make_mock_alaska_response("Synthetic Field A", 12)
        df = loader.load(raw)
        assert all(df["crude_bopd"] >= 0)

    @pytest.mark.parametrize(
        "field,crude_rates,ngl_rate,crude_sum,ngl_sum",
        [
            (
                "Synthetic Field A",
                [300_000.0, 299_500.0],
                15_000.0,
                599_500.0,
                30_000.0,
            ),
            ("Synthetic Field B", [100_000.0, 99_500.0], 5_000.0, 199_500.0, 10_000.0),
            ("Synthetic Field C", [10_000.0, 9_500.0], 500.0, 19_500.0, 1_000.0),
        ],
    )
    def test_synthetic_catalogue_preserves_record_transforms(
        self, loader, field, crude_rates, ngl_rate, crude_sum, ngl_sum
    ):
        """Synthetic rates exercise transforms; sums of rates are not volumes."""
        assert field in ALASKA_FIELDS
        df = loader.load(make_mock_alaska_response(field, 2))
        expected = pd.DataFrame(
            {
                "period": ["2023-01", "2023-02"],
                "field": [field, field],
                "crude_bopd": crude_rates,
                "ngl_bopd": [ngl_rate, ngl_rate],
            }
        )
        pd.testing.assert_frame_equal(df, expected)
        mixed = pd.concat(
            [df, loader.load(make_mock_alaska_response("Synthetic Other Field", 1))]
        )
        pd.testing.assert_frame_equal(loader.filter_field(mixed, field), expected)
        pd.testing.assert_frame_equal(
            loader.filter_period(df, "2023-02"), expected.iloc[1:]
        )
        assert loader.annual_total(df).to_dict("records") == [
            {"field": field, "year": 2023, "crude_bopd": crude_sum, "ngl_bopd": ngl_sum}
        ]
        assert loader.to_records(df) == [
            AlaskaFieldRecord("2023-01", field, crude_rates[0], ngl_rate),
            AlaskaFieldRecord("2023-02", field, crude_rates[1], ngl_rate),
        ]
