"""Tests for Brazilian fiscal regime models (concession + PSA)."""

import pytest

from worldenergydata.brazil_anp.analysis.field_economics import (
    ConcessionRegime,
    FiscalResult,
    ParticipationSchedule,
    PSARegime,
    calculate_psa_government_take,
    calculate_royalties_concession,
    calculate_special_participation,
)


class TestConcessionRoyalties:
    def test_minimum_royalty_rate(self):
        result = calculate_royalties_concession(
            gross_revenue=1_000_000.0, production_rate_bpd=500.0
        )
        assert result >= 1_000_000.0 * 0.05

    def test_maximum_royalty_rate(self):
        result = calculate_royalties_concession(
            gross_revenue=1_000_000.0, production_rate_bpd=100_000.0
        )
        assert result <= 1_000_000.0 * 0.15

    def test_sliding_scale(self):
        low = calculate_royalties_concession(
            gross_revenue=1_000_000.0, production_rate_bpd=1_000.0
        )
        high = calculate_royalties_concession(
            gross_revenue=1_000_000.0, production_rate_bpd=50_000.0
        )
        assert high > low

    def test_zero_revenue(self):
        result = calculate_royalties_concession(
            gross_revenue=0.0, production_rate_bpd=10_000.0
        )
        assert result == 0.0


class TestSpecialParticipation:
    """Synthetic marginal bands; no statutory thresholds are assumed.

    Hand calculation: the first 100 units are untaxed, the remainder is
    multiplied by the supplied fraction 0.2. Thus 150 gives 10, 200 gives 20,
    and a nonpositive revenue gives zero. Inputs use the same quarterly basis.
    """

    @pytest.mark.parametrize(
        "revenue, expected", [(0, 0), (100, 0), (150, 10), (200, 20)]
    )
    def test_explicit_marginal_bands(self, revenue, expected):
        schedule = ParticipationSchedule(
            currency="TEST",
            period="quarter",
            bands=((100, 0), (float("inf"), 0.2)),
            source="Synthetic hand calculation in TestSpecialParticipation",
        )
        assert (
            calculate_special_participation(
                revenue, schedule=schedule, currency="TEST", period="quarter"
            )
            == expected
        )


class TestConcessionRegime:
    @pytest.fixture
    def regime(self):
        return ConcessionRegime()

    @pytest.fixture
    def basis(self):
        # Synthetic no-participation case: every revenue unit times zero.
        return {
            "currency": "TEST",
            "period": "quarter",
            "participation_schedule": ParticipationSchedule(
                currency="TEST",
                period="quarter",
                bands=((float("inf"), 0),),
                source="Synthetic zero-participation arithmetic fixture",
            ),
        }

    def test_calculate_returns_fiscal_result(self, regime, basis):
        result = regime.calculate(
            **basis,
            gross_revenue=100_000_000.0,
            opex=30_000_000.0,
            capex=20_000_000.0,
            production_rate_bpd=20_000.0,
        )
        assert isinstance(result, FiscalResult)

    def test_royalties_present(self, regime, basis):
        result = regime.calculate(
            **basis,
            gross_revenue=100_000_000.0,
            opex=30_000_000.0,
            capex=20_000_000.0,
            production_rate_bpd=20_000.0,
        )
        assert result.royalties > 0.0

    def test_corporate_tax_34_percent(self, regime, basis):
        result = regime.calculate(
            **basis,
            gross_revenue=100_000_000.0,
            opex=30_000_000.0,
            capex=20_000_000.0,
            production_rate_bpd=20_000.0,
        )
        assert result.corporate_tax_rate == pytest.approx(0.34, abs=0.01)

    def test_net_income_positive_for_profitable_field(self, regime, basis):
        result = regime.calculate(
            **basis,
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=10_000_000.0,
            production_rate_bpd=20_000.0,
        )
        assert result.net_income > 0.0

    def test_government_take_reasonable(self, regime, basis):
        result = regime.calculate(
            **basis,
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=10_000_000.0,
            production_rate_bpd=20_000.0,
        )
        gov_take_pct = result.total_government_take / 100_000_000.0
        assert 0.30 < gov_take_pct < 0.80


class TestPSAGovernmentTake:
    def test_fixed_royalty_15_percent(self):
        result = calculate_psa_government_take(
            gross_revenue=100_000_000.0,
            cost_oil=30_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result["royalties"] == pytest.approx(15_000_000.0)

    def test_profit_oil_split(self):
        result = calculate_psa_government_take(
            gross_revenue=100_000_000.0,
            cost_oil=30_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result["government_profit_oil"] > 0.0

    def test_petrobras_minimum_30_percent(self):
        result = calculate_psa_government_take(
            gross_revenue=100_000_000.0,
            cost_oil=30_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result["petrobras_share"] >= 0.30


class TestPSARegime:
    @pytest.fixture
    def regime(self):
        return PSARegime()

    def test_calculate_returns_fiscal_result(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert isinstance(result, FiscalResult)

    def test_no_special_participation(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result.special_participation == 0.0

    def test_royalties_at_15_percent(self, regime):
        result = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.50,
        )
        assert result.royalties == pytest.approx(15_000_000.0)

    def test_higher_gov_share_more_take(self, regime):
        low = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.30,
        )
        high = regime.calculate(
            gross_revenue=100_000_000.0,
            opex=20_000_000.0,
            capex=15_000_000.0,
            profit_oil_gov_share=0.70,
        )
        assert high.total_government_take > low.total_government_take


def test_royalty_scale_is_marked_illustrative():
    from worldenergydata.brazil_anp.analysis import field_economics

    assert getattr(field_economics, "ROYALTY_SCALE_IS_ILLUSTRATIVE", False) is True
    assert "illustrative" in field_economics.__doc__.lower()
    assert "illustrative" in calculate_royalties_concession.__doc__.lower()
    assert "illustrative" in ConcessionRegime.__doc__.lower()


def test_royalty_scale_documentation_is_qualified():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    readme = (root / "packages/worldenergydata-brazil_anp/README.md").read_text(
        encoding="utf-8"
    )
    assert "illustrative" in readme.lower()
    assert "ROYALTY_SCALE_IS_ILLUSTRATIVE" in readme
    assert "art. 12" in readme
    assert "2026-10-12" in readme


def test_shipped_fiscal_decks_exclude_scale_regression_pin(monkeypatch):
    """Pin: shipped decks and production builders already exclude these bands."""
    import inspect
    from importlib import resources

    import yaml

    from worldenergydata.brazil_anp.analysis import field_economics
    from worldenergydata.fdas.fiscal import (
        available_countries,
        get_fiscal_terms,
        schema,
        terms,
        validate_deck,
    )

    def reject_reference(*args, **kwargs):
        raise AssertionError("A shipped deck read the illustrative royalty scale")

    class UnreadableScale:
        __iter__ = reject_reference
        __getitem__ = reject_reference
        __len__ = reject_reference

    monkeypatch.setattr(field_economics, "ROYALTY_SCALE", UnreadableScale())
    monkeypatch.setattr(
        field_economics, "calculate_royalties_concession", reject_reference
    )
    countries = available_countries()
    assert countries == ["norway", "uk", "us_gom"]
    decks = resources.files("worldenergydata.fdas.fiscal.decks")
    for country in countries:
        raw = yaml.safe_load(decks.joinpath(country + ".yml").read_text())
        loaded = get_fiscal_terms(country)
        assert validate_deck(raw) == loaded
        assert loaded.royalty.model in {"flat", "none"}
        assert loaded.royalty.bands == ()
    for builder in (schema, terms):
        source = inspect.getsource(builder)
        assert "ROYALTY_SCALE" not in source
        assert "brazil_anp" not in source


def test_royalty_band_values_and_boundaries_regression_pin():
    """Pin: values follow field_economics.ROYALTY_SCALE, not a legal table."""
    from worldenergydata.brazil_anp.analysis.field_economics import ROYALTY_SCALE

    assert ROYALTY_SCALE == [
        (5_000, 0.05),
        (15_000, 0.075),
        (30_000, 0.10),
        (50_000, 0.125),
        (float("inf"), 0.15),
    ]
    for rate_bpd, royalty_rate in (
        (0, 0.05),
        (5_000, 0.05),
        (5_001, 0.075),
        (15_000, 0.075),
        (15_001, 0.10),
        (30_000, 0.10),
        (30_001, 0.125),
        (50_000, 0.125),
        (50_001, 0.15),
        (100_000, 0.15),
    ):
        assert calculate_royalties_concession(1_000_000, rate_bpd) == (
            1_000_000 * royalty_rate
        )
        assert calculate_royalties_concession(0, rate_bpd) == 0
