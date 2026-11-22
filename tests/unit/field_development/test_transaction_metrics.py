"""Synthetic hand calculations and refusal cases for transaction ratios."""

import pytest

from worldenergydata.field_development.transaction_package import valuation_metrics


def observation(value, unit, basis="synthetic", subject="synthetic portfolio"):
    """Synthetic fixture values are defined by each test's hand calculation."""
    return {
        "value": value,
        "unit": unit,
        "basis": basis,
        "subject": subject,
        "as_of": "2026-01-01",
        "citation": {"source_id": "hand-calculation", "locator": "test docstring"},
    }


def test_metrics_independent_hand_calculation():
    """USD 120 / 8 boe = USD 15/boe; USD 120 / 4 boe/d = USD 30/(boe/d).

    These are invented exact arithmetic inputs, not public transaction facts.
    No conversion, discount rate, or working-interest factor is assumed.
    """
    result = valuation_metrics(
        observation(120, "USD"),
        observation(8, "boe"),
        observation(4, "boe/d"),
    )
    assert result["usd_per_boe"]["value"] == 15
    assert result["usd_per_flowing_boe_day"]["value"] == 30
    assert result["usd_per_boe"]["status"] == "EVALUATED"


@pytest.mark.parametrize("value", [-1, "NaN", "Infinity", True])
def test_invalid_values_refused(value):
    with pytest.raises(ValueError):
        valuation_metrics(
            observation(value, "USD"), observation(8, "boe"), observation(4, "boe/d")
        )


@pytest.mark.parametrize("identity", ["basis", "subject"])
def test_cross_basis_or_subject_ratios_refused(identity):
    denominator = observation(8, "boe")
    denominator[identity] = "different"
    with pytest.raises(ValueError, match="Mixed"):
        valuation_metrics(observation(120, "USD"), denominator, observation(4, "boe/d"))


def test_missing_denominator_is_not_zero_or_a_failed_transaction():
    """An unavailable reserve input does not suppress the independent 120/4 ratio."""
    missing = {"value": None, "unit": "boe", "reason": "Reserve evidence unavailable"}
    result = valuation_metrics(
        observation(120, "USD"), missing, observation(4, "boe/d")
    )
    assert result["usd_per_boe"]["status"] == "NOT_EVALUATED"
    assert result["usd_per_boe"]["value"] is None
    assert result["usd_per_flowing_boe_day"]["value"] == 30


def test_zero_production_does_not_divide():
    result = valuation_metrics(
        observation(120, "USD"), observation(8, "boe"), observation(0, "boe/d")
    )
    assert result["usd_per_flowing_boe_day"]["status"] == "NOT_EVALUATED"


def test_bare_source_identifier_is_insufficient():
    amount = observation(120, "USD")
    amount["citation"] = {"source_id": "hand-calculation"}
    with pytest.raises(ValueError, match="citation"):
        valuation_metrics(amount, observation(8, "boe"), observation(4, "boe/d"))


@pytest.mark.parametrize(
    "bounds",
    [
        [],
        [1],
        [1, 2, 3],
        [2, 1],
        [None, 2],
        [True, 2],
        [-1, 2],
        ["NaN", 2],
        [1, "Infinity"],
    ],
)
def test_invalid_consideration_ranges_are_refused(bounds):
    amount = observation(None, "USD")
    amount["range"] = bounds
    with pytest.raises(ValueError):
        valuation_metrics(amount, observation(8, "boe"), observation(4, "boe/d"))


@pytest.mark.parametrize("ranged", [False, True])
def test_non_finite_ratio_cannot_receive_an_evaluated_status(ranged):
    amount = observation("1e1000", "USD")
    if ranged:
        amount.update(value=None, range=["1e1000", "2e1000"])
    with pytest.raises(ValueError, match="finite"):
        valuation_metrics(amount, observation(8, "boe"), observation(4, "boe/d"))
