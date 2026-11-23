"""Tests for EITI government revenue and company payment data."""

from unittest.mock import MagicMock, patch

import pytest

from worldenergydata.west_africa.eiti.payment_data import (
    PaymentDataLoader,
    PaymentRecord,
    aggregate_by_company,
    aggregate_by_payment_type,
    cross_validate_nuprc_eiti,
)

SAMPLE_PAYMENTS = [
    PaymentRecord(
        country="Nigeria",
        year=2022,
        company="Shell Nigeria",
        payment_type="royalty",
        amount_usd=1_200_000_000,
    ),
    PaymentRecord(
        country="Nigeria",
        year=2022,
        company="Shell Nigeria",
        payment_type="corporate_tax",
        amount_usd=800_000_000,
    ),
    PaymentRecord(
        country="Nigeria",
        year=2022,
        company="TotalEnergies Nigeria",
        payment_type="royalty",
        amount_usd=950_000_000,
    ),
    PaymentRecord(
        country="Nigeria",
        year=2021,
        company="Shell Nigeria",
        payment_type="royalty",
        amount_usd=1_100_000_000,
    ),
]


class TestPaymentRecord:
    def test_record_creation(self):
        r = PaymentRecord(
            country="Nigeria",
            year=2022,
            company="Shell Nigeria",
            payment_type="royalty",
            amount_usd=1_200_000_000,
        )
        assert r.country == "Nigeria"
        assert r.amount_usd == 1_200_000_000

    def test_amount_non_negative(self):
        with pytest.raises(ValueError):
            PaymentRecord(
                country="Nigeria",
                year=2022,
                company="NNPC",
                payment_type="royalty",
                amount_usd=-500,
            )

    def test_payment_type_string(self):
        r = PaymentRecord(
            country="Nigeria",
            year=2022,
            company="NNPC",
            payment_type="profit_oil",
            amount_usd=0,
        )
        assert isinstance(r.payment_type, str)


class TestAggregateByCompany:
    def test_returns_dict(self):
        result = aggregate_by_company(SAMPLE_PAYMENTS)
        assert isinstance(result, dict)

    def test_shell_total_sums_both_types(self):
        result = aggregate_by_company(SAMPLE_PAYMENTS, year=2022)
        assert result["Shell Nigeria"] == pytest.approx(
            1_200_000_000 + 800_000_000, abs=1
        )

    def test_total_includes_all_companies(self):
        result = aggregate_by_company(SAMPLE_PAYMENTS, year=2022)
        assert "Shell Nigeria" in result
        assert "TotalEnergies Nigeria" in result

    def test_empty_returns_empty_dict(self):
        assert aggregate_by_company([]) == {}


class TestAggregateByPaymentType:
    def test_returns_dict(self):
        result = aggregate_by_payment_type(SAMPLE_PAYMENTS)
        assert isinstance(result, dict)

    def test_royalty_sum_correct(self):
        result = aggregate_by_payment_type(SAMPLE_PAYMENTS, year=2022)
        expected = 1_200_000_000 + 950_000_000
        assert result["royalty"] == pytest.approx(expected, abs=1)

    def test_empty_returns_empty_dict(self):
        assert aggregate_by_payment_type([]) == {}


class TestCrossValidateNuprcEiti:
    def test_returns_dict(self):
        nuprc_total_kbd = 1_300.0  # Nigeria total production kbd
        eiti_total_bbl = 474_100_000  # ~1300 kbd for one year
        result = cross_validate_nuprc_eiti(
            nuprc_total_kbd=nuprc_total_kbd,
            eiti_total_bbl=eiti_total_bbl,
            year=2022,
        )
        assert isinstance(result, dict)

    def test_returns_discrepancy_key(self):
        result = cross_validate_nuprc_eiti(
            nuprc_total_kbd=1_300.0,
            eiti_total_bbl=474_100_000,
            year=2022,
        )
        assert "discrepancy_pct" in result

    def test_identical_sources_zero_discrepancy(self):
        # 1300 kbd * 365 days = 474,500,000 bbl
        kbd = 1_300.0
        bbl = kbd * 1000 * 365
        result = cross_validate_nuprc_eiti(
            nuprc_total_kbd=kbd,
            eiti_total_bbl=bbl,
            year=2022,
        )
        assert abs(result["discrepancy_pct"]) < 1.0


class TestPaymentDataLoader:
    @patch("worldenergydata.west_africa.eiti.payment_data.EitiApiClient")
    def test_loader_init(self, mock_cls):
        loader = PaymentDataLoader()
        assert loader is not None

    @patch("worldenergydata.west_africa.eiti.payment_data.EitiApiClient")
    def test_load_returns_list(self, mock_cls):
        mock_client = MagicMock()
        mock_client.get_payment_data.return_value = [
            {
                "country": "Nigeria",
                "year": 2022,
                "company": "Shell Nigeria",
                "payment_type": "royalty",
                "amount_usd": 1_200_000_000,
            }
        ]
        mock_cls.return_value = mock_client

        loader = PaymentDataLoader()
        result = loader.load(country="Nigeria", year=2022)
        assert isinstance(result, list)
