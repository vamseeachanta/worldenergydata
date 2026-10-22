"""Independent arithmetic qualification, not drilling calibration.

Source: NASA, Guidelines for Application of Learning/Cost Improvement Curves
(1975), section IV.A-B (printed pp. 6-7), VII.B formulas 1-2 (p. 15).
https://ntrs.nasa.gov/api/citations/19760006882/downloads/19760006882.pdf
Formula 1 gives the power law; defining the factor by doubling gives exponent
log(factor)/log(2). All test inputs below are explicitly synthetic.
"""

import math

import pytest
from pydantic import ValidationError

from worldenergydata.drilling import BatchDrillingEconomics, DrillCampaign, DrillingSite


@pytest.fixture
def campaign():
    """Synthetic three-well campaign, not observed or calibrated field data."""
    return DrillCampaign(
        campaign_id="synthetic",
        rig_name="synthetic",
        rig_day_rate_usd=100,
        mobilization_cost_usd=300,
        learning_curve_factor=1 / math.sqrt(2),
        sequence=["W3", "W1", "W2"],
        wells=[
            DrillingSite(
                well_id=f"W{i}",
                field_name="synthetic",
                location_coords=(0.0, 0.0),
                water_depth_ft=2000,
                planned_md_ft=8000,
                well_type="development",
            )
            for i in (1, 2, 3)
        ],
    )


def test_individual_duration_reference(campaign):
    """NASA (1975), IV.B and VII.B.1-2: individual-unit interpretation.

    Hand calculation: T1=12 days; factor=1/sqrt(2), hence exponent=-1/2.
    Unit times: 12, 12/sqrt(2)=6*sqrt(2), 12/sqrt(3)=4*sqrt(3) days.
    Three-well sum=12+6*sqrt(2)+4*sqrt(3) days.
    At 100 USD/day and one 300 USD mobilization, cost is
    300+100*(12+6*sqrt(2)+4*sqrt(3)) USD. Standalone is
    3*(300+100*12)=4500 USD; savings subtract that batch cost.
    Absolute tolerances: 1e-12 days and 1e-8 USD, rel=0; these accommodate
    binary log/power/summation rounding only, not an engineering error band.
    """
    calc = BatchDrillingEconomics()
    expected = [12, 6 * math.sqrt(2), 4 * math.sqrt(3)]
    durations = [
        calc.learning_curve_time(12, i, campaign.learning_curve_factor)
        for i in (1, 2, 3)
    ]
    assert durations == pytest.approx(expected, rel=0, abs=1e-12)
    total = 300 + 100 * (12 + 6 * math.sqrt(2) + 4 * math.sqrt(3))
    assert calc.campaign_total_cost(campaign, 12) == pytest.approx(
        total, rel=0, abs=1e-8
    )
    comparison = calc.batch_vs_standalone_npv(campaign, base_days_per_well=12)
    assert comparison == pytest.approx(
        {"batch_npv": total, "standalone_npv": 4500, "batch_savings": 4500 - total},
        rel=0,
        abs=1e-8,
    )


def test_cumulative_average_reference(campaign):
    """NASA (1975), IV.A and VII.B.1-2: alternative average interpretation.

    The same synthetic power-law ordinates are averages A(N)=12/sqrt(N).
    Cumulative totals N*A(N) are 12, 12*sqrt(2), 12*sqrt(3) days.
    Marginal units are 12, 12*(sqrt(2)-1), 12*(sqrt(3)-sqrt(2)) days.
    Thus three-well cost would be 300+1200*sqrt(3) USD, not the individual
    sum in test_individual_duration_reference. The production cost API retains
    the individual interpretation; multiplication here explicitly tests the
    alternative reading of its ordinate, not an alternative cost API.
    Tolerances 1e-12 days and 1e-8 USD cover floating-point roundoff only.
    """
    calc = BatchDrillingEconomics()
    averages = [
        calc.learning_curve_time(12, i, campaign.learning_curve_factor)
        for i in (1, 2, 3)
    ]
    totals = [i * value for i, value in enumerate(averages, start=1)]
    assert totals == pytest.approx(
        [12, 12 * math.sqrt(2), 12 * math.sqrt(3)], rel=0, abs=1e-12
    )
    marginal = [totals[0], totals[1] - totals[0], totals[2] - totals[1]]
    assert marginal == pytest.approx(
        [12, 12 * (math.sqrt(2) - 1), 12 * (math.sqrt(3) - math.sqrt(2))],
        rel=0,
        abs=1e-12,
    )
    alternative_cost = 300 + 100 * totals[-1]
    assert alternative_cost == pytest.approx(300 + 1200 * math.sqrt(3), rel=0, abs=1e-8)
    assert alternative_cost < calc.campaign_total_cost(campaign, 12)


def test_learning_factor_is_required(campaign):
    values = campaign.model_dump()
    values.pop("learning_curve_factor")
    with pytest.raises(ValidationError, match="learning_curve_factor"):
        DrillCampaign(**values)
    with pytest.raises(ValidationError, match="lc_factor"):
        BatchDrillingEconomics().learning_curve_time(12, 1)
    with pytest.raises(ValidationError, match="lc_factor"):
        BatchDrillingEconomics().break_even_n_wells(300, 100, 12)


def test_base_duration_is_required(campaign):
    with pytest.raises(ValidationError, match="base_days_per_well"):
        BatchDrillingEconomics().batch_vs_standalone_npv(campaign)


def test_depth_arithmetic_reference(campaign):
    """Legacy arithmetic, explicitly assumed: MD/a + WD/b + c, floor d.

    Source for the retained form: economics.py::_estimate_base_well_days at
    the pre-change revision, not a public engineering calibration. Synthetic
    assumptions a=400 ft/day, b=2000 ft/day, c=10 days, d=30 days reproduce
    max(8000/400+2000/2000+10,30)=max(31,30)=31 days, not 41 days.
    Changing only d to 40 yields 40 days. These exact integer results use
    exact equality; no tolerance is needed. No coefficient is a default.
    """
    calc = BatchDrillingEconomics()
    inputs = {
        "md_ft_per_day": 400,
        "water_depth_ft_per_day": 2000,
        "fixed_days": 10,
        "minimum_days": 30,
    }
    assert calc._estimate_base_well_days(campaign, **inputs) == 31
    assert (
        calc._estimate_base_well_days(campaign, **(inputs | {"minimum_days": 40})) == 40
    )


@pytest.mark.parametrize(
    "field", ["md_ft_per_day", "water_depth_ft_per_day", "fixed_days", "minimum_days"]
)
def test_depth_coefficients_are_required(campaign, field):
    inputs = {
        "md_ft_per_day": 400,
        "water_depth_ft_per_day": 2000,
        "fixed_days": 10,
        "minimum_days": 30,
    }
    inputs.pop(field)
    with pytest.raises(ValidationError, match=field) as caught:
        BatchDrillingEconomics()._estimate_base_well_days(campaign, **inputs)
    assert any(
        error["loc"] == (field,) and error["type"] == "missing_keyword_only_argument"
        for error in caught.value.errors()
    )


@pytest.mark.parametrize(
    "field", ["md_ft_per_day", "water_depth_ft_per_day", "fixed_days", "minimum_days"]
)
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, -1, True, "1", None])
def test_depth_coefficient_contract(campaign, field, value):
    inputs = {
        "md_ft_per_day": 400,
        "water_depth_ft_per_day": 2000,
        "fixed_days": 10,
        "minimum_days": 30,
    }
    with pytest.raises(ValidationError, match=field) as caught:
        BatchDrillingEconomics()._estimate_base_well_days(
            campaign, **(inputs | {field: value})
        )
    assert caught.value.errors()[0]["type"] in {
        "finite_number",
        "greater_than",
        "greater_than_equal",
        "float_type",
    }


@pytest.mark.parametrize("field", ["md_ft_per_day", "water_depth_ft_per_day"])
def test_zero_depth_denominator_rejected(campaign, field):
    inputs = {
        "md_ft_per_day": 400,
        "water_depth_ft_per_day": 2000,
        "fixed_days": 10,
        "minimum_days": 30,
    }
    with pytest.raises(ValidationError, match=field):
        BatchDrillingEconomics()._estimate_base_well_days(
            campaign, **(inputs | {field: 0})
        )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, -1, True, "0"])
def test_discount_rate_contract(campaign, value):
    with pytest.raises(ValidationError, match="discount_rate"):
        BatchDrillingEconomics().batch_vs_standalone_npv(
            campaign, value, base_days_per_well=12
        )


def test_positional_error_names_field():
    with pytest.raises(ValidationError) as caught:
        BatchDrillingEconomics().learning_curve_time(math.nan, 1, 0.5)
    assert caught.value.errors()[0]["loc"] == ("base_time_days",)
    assert caught.value.errors()[0]["type"] == "finite_number"
