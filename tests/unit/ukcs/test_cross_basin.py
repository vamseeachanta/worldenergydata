"""Tests for cross-basin comparison: UKCS vs NCS vs GoM."""

import pytest

from worldenergydata.ukcs.analysis.cross_basin_example import (
    CrossBasinComparator,
    BasinProfile,
    ComparisonResult,
    MOCK_FORTIES_PROFILE,
    MOCK_EDVARD_GRIEG_PROFILE,
    MOCK_GOM_FIELD_PROFILE,
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
