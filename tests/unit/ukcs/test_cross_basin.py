"""Tests for cross-basin comparison: UKCS vs NCS vs GoM."""

import pytest

from worldenergydata.ukcs.analysis.cross_basin_example import (
    GOM_FEDERAL_TAX_RATE,
    GOM_ROYALTY_RATE,
    MOCK_EDVARD_GRIEG_PROFILE,
    MOCK_FORTIES_PROFILE,
    MOCK_GOM_FIELD_PROFILE,
    BasinProfile,
    ComparisonResult,
    CrossBasinComparator,
)


class TestBasinProfile:
    def test_forties_profile_has_name(self):
        assert MOCK_FORTIES_PROFILE.name == "Forties"

    def test_edvard_grieg_profile_has_name(self):
        assert MOCK_EDVARD_GRIEG_PROFILE.name == "Edvard Grieg"

    def test_gom_profile_has_name(self):
        assert MOCK_GOM_FIELD_PROFILE.name is not None

    def test_profile_has_production_profile(self):
        assert len(MOCK_FORTIES_PROFILE.monthly_production_bbl) > 0

    def test_profile_has_capex(self):
        assert MOCK_FORTIES_PROFILE.capex_mm_usd > 0

    def test_profile_has_opex(self):
        assert MOCK_FORTIES_PROFILE.opex_per_bbl_usd > 0

    def test_profile_has_oil_price(self):
        assert MOCK_FORTIES_PROFILE.oil_price_usd_bbl > 0


class TestCrossBasinComparator:
    @pytest.fixture
    def comparator(self):
        return CrossBasinComparator(discount_rate=0.10)

    def test_compare_returns_result(self, comparator):
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        assert isinstance(result, ComparisonResult)

    def test_compare_has_three_npvs(self, comparator):
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        assert len(result.npv_by_basin) == 3

    def test_compare_all_basin_names_present(self, comparator):
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        names = set(result.npv_by_basin.keys())
        assert "Forties" in names
        assert "Edvard Grieg" in names

    def test_npv_is_float(self, comparator):
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        for name, npv in result.npv_by_basin.items():
            assert isinstance(npv, float), f"{name} NPV not float"

    def test_government_take_by_basin_present(self, comparator):
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        assert len(result.government_take_by_basin) == 3

    def test_government_take_rates_in_valid_range(self, comparator):
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        for basin, rate in result.government_take_by_basin.items():
            assert 0.0 <= rate <= 1.0, f"{basin} gov take {rate:.1%} out of range"

    def test_uk_effective_rate_near_78_percent(self, comparator):
        """UKCS combined RFCT+SC+EPL should approach ~78% effective rate."""
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        uk_rate = result.government_take_by_basin.get("Forties", 0.0)
        assert 0.55 < uk_rate < 0.90

    def test_npv_sensitivity_field_present(self, comparator):
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        assert hasattr(result, "npv_sensitivity")

    def test_summary_string_not_empty(self, comparator):
        result = comparator.compare(
            MOCK_FORTIES_PROFILE,
            MOCK_EDVARD_GRIEG_PROFILE,
            MOCK_GOM_FIELD_PROFILE,
        )
        summary = result.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0


class TestComparatorCashflowContract:
    @pytest.fixture
    def profile(self):
        return BasinProfile(
            name="Synthetic",
            basin="Synthetic",
            monthly_production_bbl=[1.0],
            oil_price_usd_bbl=1.0,
            capex_mm_usd=0.0,
            opex_per_bbl_usd=2.0,
            fiscal_regime="gom",
        )

    @pytest.mark.parametrize("selector", ["unknown", "UKCS"])
    @pytest.mark.parametrize("production", [[], [1.0]])
    @pytest.mark.parametrize(
        "route", ["_apply_fiscal", "_compute", "compare", "_npv_sensitivity"]
    )
    def test_unknown_selector_raises(self, profile, selector, production, route):
        profile.fiscal_regime = selector
        profile.monthly_production_bbl = production
        method = getattr(CrossBasinComparator(), route)

        with pytest.raises(ValueError, match="Unsupported fiscal regime"):
            if route == "_apply_fiscal":
                method(profile, revenue=1.0, opex=2.0, capex_usd=0.0, month=1)
            else:
                method(profile)

    def test_compare_validates_all_selectors_before_computation(
        self, profile, monkeypatch
    ):
        invalid = BasinProfile("Invalid", "Synthetic", [], 1.0, 0.0, 2.0, "unknown")
        comparator = CrossBasinComparator()

        def unexpected_computation(*args):
            pytest.fail("A profile was computed before all selectors were validated")

        monkeypatch.setattr(comparator, "_compute", unexpected_computation)
        with pytest.raises(ValueError, match="Unsupported fiscal regime"):
            comparator.compare(profile, invalid)

    @pytest.mark.parametrize("selector", ["ukcs", "ncs", "gom"])
    def test_supported_selectors_dispatch(self, profile, selector):
        profile.fiscal_regime = selector
        profile.oil_price_usd_bbl = 100.0
        comparator = CrossBasinComparator()

        assert comparator._apply_fiscal(profile, 100.0, 2.0, 0.0, 1) > 0.0
        npv, _ = comparator._compute(profile)
        assert comparator.compare(profile).npv_by_basin[profile.name] == npv

    @pytest.mark.parametrize("opex_per_bbl", [2.0, 0.9])
    def test_loss_month_retains_signed_cashflow(self, profile, opex_per_bbl):
        """One bbl at USD 1 loses money before or after the existing royalty."""
        profile.opex_per_bbl_usd = opex_per_bbl
        comparator = CrossBasinComparator(discount_rate=0.12)
        expected = (1.0 - opex_per_bbl - GOM_ROYALTY_RATE) / 1.01

        assert expected < 0.0
        assert comparator._compute(profile)[0] == pytest.approx(expected)
        assert comparator.compare(profile).npv_by_basin[profile.name] == pytest.approx(
            expected
        )

    def test_price_sensitivity_retains_losses(self, profile):
        comparator = CrossBasinComparator(discount_rate=0.12)
        sensitivity = comparator.compare(profile).npv_sensitivity[profile.name]

        for key, price in (("base", 1.0), ("high_price", 1.1), ("low_price", 0.9)):
            expected = (price - 2.0 - price * GOM_ROYALTY_RATE) / 1.01
            assert sensitivity[key] == pytest.approx(expected)
            assert sensitivity[key] < 0.0

    def test_mixed_months_discount_signed_cashflows_and_charge_capital_once(
        self, profile
    ):
        """A synthetic volume reversal tests arithmetic, not production validity."""
        profile.monthly_production_bbl = [4.0, -1.0]
        profile.oil_price_usd_bbl = 10.0
        profile.capex_mm_usd = 3.0 / 1_000_000.0
        comparator = CrossBasinComparator(discount_rate=0.12)

        first_royalty = 40.0 * GOM_ROYALTY_RATE
        first_tax = (40.0 - first_royalty - 8.0) * GOM_FEDERAL_TAX_RATE
        first_net = 40.0 - 8.0 - first_royalty - first_tax
        second_net = -10.0 - (-2.0) - (-10.0 * GOM_ROYALTY_RATE)
        expected = -3.0 + first_net / 1.01 + second_net / 1.01**2

        assert first_net > 0.0 > second_net
        npv, take = comparator._compute(profile)
        assert npv == pytest.approx(expected)
        result = comparator.compare(profile)
        assert result.npv_by_basin[profile.name] == pytest.approx(expected)
        # Government take retains its existing positive-profit-only aggregation.
        assert take == pytest.approx((first_royalty + first_tax) / (40.0 - 8.0))
