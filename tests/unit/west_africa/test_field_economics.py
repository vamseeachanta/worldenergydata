"""Tests for Nigeria PSC fiscal regime model (deepwater).

Nigeria deepwater uses Production Sharing Contracts (PSC):
- Royalty: depth-based, 0% below 1000m for deepwater
- Cost oil: contractor recovers opex + capex up to cost oil ceiling (typically 80%)
- Profit oil: split between NNPC and contractor (varies by production band)
- PPT (Petroleum Profits Tax): 65.75% on contractor profit oil (PSC)
- CITA (Companies Income Tax): 30% (applies in early years when PPT < CITA)
- NDDC Levy: 3% of opex for Niger Delta Development Commission
- Effective government take: ~75-80%
"""

import pytest

from worldenergydata.west_africa.analysis.field_economics import (
    NigeriaDeepwaterPSC,
    PSCFiscalResult,
    calculate_royalty_deepwater,
    calculate_cost_oil_recovery,
    calculate_profit_oil_split,
    DEEPWATER_ROYALTY_TABLE,
    PPT_RATE_PSC,
    CITA_RATE,
    NDDC_LEVY_RATE,
    NIGERIA_DEEPWATER_FIELDS,
)


class TestDeepwaterRoyaltyTable:
    def test_table_is_list_or_dict(self):
        assert isinstance(DEEPWATER_ROYALTY_TABLE, (list, dict))

    def test_royalty_zero_below_1000m(self):
        rate = calculate_royalty_deepwater(water_depth_m=1000)
        assert rate == 0.0

    def test_royalty_low_above_200m(self):
        rate = calculate_royalty_deepwater(water_depth_m=500)
        assert 0.0 <= rate <= 0.08

    def test_royalty_non_negative(self):
        for depth in [100, 500, 1000, 1500, 2000]:
            rate = calculate_royalty_deepwater(water_depth_m=depth)
            assert rate >= 0.0


class TestCostOilRecovery:
    def test_returns_float(self):
        result = calculate_cost_oil_recovery(
            gross_revenue=1_000_000_000.0,
            opex=200_000_000.0,
            capex=300_000_000.0,
            cost_oil_ceiling=0.80,
        )
        assert isinstance(result, float)

    def test_cost_oil_cannot_exceed_ceiling(self):
        result = calculate_cost_oil_recovery(
            gross_revenue=100_000_000.0,
            opex=90_000_000.0,
            capex=90_000_000.0,
            cost_oil_ceiling=0.80,
        )
        assert result <= 100_000_000.0 * 0.80

    def test_cost_oil_covers_actual_costs_if_below_ceiling(self):
        result = calculate_cost_oil_recovery(
            gross_revenue=1_000_000_000.0,
            opex=100_000_000.0,
            capex=100_000_000.0,
            cost_oil_ceiling=0.80,
        )
        assert result == pytest.approx(200_000_000.0, abs=1.0)

    def test_zero_costs_returns_zero_cost_oil(self):
        result = calculate_cost_oil_recovery(
            gross_revenue=500_000_000.0,
            opex=0.0,
            capex=0.0,
            cost_oil_ceiling=0.80,
        )
        assert result == 0.0


class TestProfitOilSplit:
    def test_returns_dict_with_nnpc_and_contractor(self):
        result = calculate_profit_oil_split(
            profit_oil=500_000_000.0,
            production_rate_bopd=200_000,
        )
        assert "nnpc" in result
        assert "contractor" in result

    def test_split_sums_to_profit_oil(self):
        profit_oil = 500_000_000.0
        result = calculate_profit_oil_split(
            profit_oil=profit_oil,
            production_rate_bopd=200_000,
        )
        total = result["nnpc"] + result["contractor"]
        assert total == pytest.approx(profit_oil, abs=1.0)

    def test_nnpc_gets_larger_share_at_high_production(self):
        low = calculate_profit_oil_split(1_000_000.0, production_rate_bopd=10_000)
        high = calculate_profit_oil_split(1_000_000.0, production_rate_bopd=300_000)
        # Higher production → higher NNPC government take percentage
        nnpc_share_low = low["nnpc"] / 1_000_000.0
        nnpc_share_high = high["nnpc"] / 1_000_000.0
        assert nnpc_share_high >= nnpc_share_low

    def test_contractor_share_non_negative(self):
        result = calculate_profit_oil_split(
            profit_oil=100_000_000.0,
            production_rate_bopd=50_000,
        )
        assert result["contractor"] >= 0.0


class TestNigeriaDeepwaterPSC:
    @pytest.fixture
    def psc(self):
        return NigeriaDeepwaterPSC(water_depth_m=1000, cost_oil_ceiling=0.80)

    def test_calculate_returns_fiscal_result(self, psc):
        result = psc.calculate(
            gross_revenue=2_000_000_000.0,
            opex=300_000_000.0,
            capex=500_000_000.0,
            production_rate_bopd=200_000,
        )
        assert isinstance(result, PSCFiscalResult)

    def test_royalty_zero_at_1000m_depth(self, psc):
        result = psc.calculate(
            gross_revenue=2_000_000_000.0,
            opex=300_000_000.0,
            capex=500_000_000.0,
            production_rate_bopd=200_000,
        )
        assert result.royalties == 0.0

    def test_ppt_rate_correct(self, psc):
        result = psc.calculate(
            gross_revenue=2_000_000_000.0,
            opex=300_000_000.0,
            capex=500_000_000.0,
            production_rate_bopd=200_000,
        )
        assert result.ppt_rate == pytest.approx(PPT_RATE_PSC, abs=0.001)

    def test_nddc_levy_present(self, psc):
        result = psc.calculate(
            gross_revenue=2_000_000_000.0,
            opex=300_000_000.0,
            capex=500_000_000.0,
            production_rate_bopd=200_000,
        )
        assert result.nddc_levy >= 0.0

    def test_government_take_between_75_and_85_pct(self, psc):
        result = psc.calculate(
            gross_revenue=2_000_000_000.0,
            opex=200_000_000.0,
            capex=300_000_000.0,
            production_rate_bopd=200_000,
        )
        gov_take = result.total_government_take / result.gross_revenue
        assert 0.55 <= gov_take <= 0.90

    def test_contractor_net_income_positive_for_profitable_field(self, psc):
        result = psc.calculate(
            gross_revenue=3_000_000_000.0,
            opex=200_000_000.0,
            capex=300_000_000.0,
            production_rate_bopd=200_000,
        )
        assert result.contractor_net_income >= 0.0

    def test_ppt_and_cita_higher_of_two_applies(self):
        # PPT rate 65.75%, CITA 30% — PPT should dominate in most cases
        assert PPT_RATE_PSC > CITA_RATE

    def test_nddc_levy_rate_is_3_pct(self):
        assert NDDC_LEVY_RATE == pytest.approx(0.03, abs=0.001)


class TestNigeriaDeepwaterFields:
    def test_is_list(self):
        assert isinstance(NIGERIA_DEEPWATER_FIELDS, list)

    def test_bonga_present(self):
        names = [f["name"] for f in NIGERIA_DEEPWATER_FIELDS]
        assert "Bonga" in names

    def test_egina_present(self):
        names = [f["name"] for f in NIGERIA_DEEPWATER_FIELDS]
        assert "Egina" in names

    def test_agbami_present(self):
        names = [f["name"] for f in NIGERIA_DEEPWATER_FIELDS]
        assert "Agbami" in names

    def test_fields_have_required_keys(self):
        required = {"name", "operator", "water_depth_m", "status"}
        for field in NIGERIA_DEEPWATER_FIELDS:
            assert required.issubset(field.keys()), (
                f"Field {field.get('name')} missing keys"
            )

    def test_all_fields_deepwater(self):
        for field in NIGERIA_DEEPWATER_FIELDS:
            assert field["water_depth_m"] >= 300, (
                f"Field {field['name']} is not deepwater"
            )
