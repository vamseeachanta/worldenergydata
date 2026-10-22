"""Tests for cross-basin comparison: UKCS vs NCS vs GoM."""

import pytest

from worldenergydata.ukcs.analysis.cross_basin_example import (
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


@pytest.mark.parametrize("selector", ["UKCS", "unknown", ""])
@pytest.mark.parametrize("production", [[1.0], []])
def test_unknown_fiscal_selector_is_refused(selector, production):
    """Issue 1284: selector validation must precede even an empty monthly loop."""
    profile = BasinProfile(
        "Synthetic", "synthetic", production, 10.0, 0.0, 2.0, selector
    )
    with pytest.raises(ValueError, match="fiscal"):
        CrossBasinComparator().compare(profile)


def test_negative_month_is_retained(monkeypatch):
    """Hand sum: pre-tax [8,16,8] minus tax [3,20,1] = [5,-4,7].

    Cumulative undiscounted cashflow is [5,1,8], so NPV is 8, formerly 12.
    All numbers are synthetic inputs; no fiscal coefficient is assumed.
    """
    comparator = CrossBasinComparator(discount_rate=0.0)
    taxes = [3.0, 20.0, 1.0]
    monkeypatch.setattr(comparator, "_apply_fiscal", lambda *args: taxes[args[-1] - 1])
    profile = BasinProfile(
        "Synthetic", "synthetic", [1.0, 2.0, 1.0], 10.0, 0.0, 2.0, "ukcs"
    )
    assert comparator._compute(profile)[0] == 8.0


def test_pre_tax_loss_is_retained(monkeypatch):
    """Hand sum with no tax: (2-5)*1 + (2-5)*2 = -3-6 = -9 USD."""
    comparator = CrossBasinComparator(discount_rate=0.0)
    monkeypatch.setattr(comparator, "_apply_fiscal", lambda *args: 0.0)
    profile = BasinProfile("Synthetic", "synthetic", [1.0, 2.0], 2.0, 0.0, 5.0, "ukcs")
    assert comparator._compute(profile)[0] == -9.0


def test_government_take_diagnostic_is_not_clipped(monkeypatch):
    """Synthetic tax 12 / pre-tax profit (10-2) = 1.5; net cashflow is -4."""
    comparator = CrossBasinComparator(discount_rate=0.0)
    monkeypatch.setattr(comparator, "_apply_fiscal", lambda *args: 12.0)
    profile = BasinProfile("Synthetic", "synthetic", [1.0], 10.0, 0.0, 2.0, "ukcs")
    assert comparator._compute(profile) == (-4.0, 1.5)
