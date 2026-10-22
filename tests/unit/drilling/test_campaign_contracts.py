"""Synthetic input-contract examples; bounds are API rules, not calibration.

All numbers here are chosen test inputs. Zero is the sign boundary, minus one
is outside a nonnegative domain, and two exceeds the factor's unit upper bound.
"""

import math

import pytest
from pydantic import ValidationError

from worldenergydata.drilling import (
    BatchDrillingEconomics,
    DrillCampaign,
    DrillingSite,
)


def site_values(well_id="W1"):
    return {
        "well_id": well_id,
        "field_name": "synthetic",
        "location_coords": (0.0, 0.0),
        "water_depth_ft": 0.0,
        "planned_md_ft": 100.0,
        "well_type": "development",
    }


def campaign_values():
    return {
        "campaign_id": "synthetic",
        "rig_name": "synthetic",
        "rig_day_rate_usd": 100.0,
        "mobilization_cost_usd": 300.0,
        "learning_curve_factor": 0.5,
        "wells": [DrillingSite(**site_values(f"W{i}")) for i in (1, 2, 3)],
    }


INVALID_REAL = [math.nan, math.inf, -math.inf, "1", True, None, [], {}]


@pytest.mark.parametrize("field", ["water_depth_ft", "planned_md_ft"])
@pytest.mark.parametrize("value", INVALID_REAL + [-1])
def test_site_depth_contract(field, value):
    with pytest.raises(ValidationError, match=field):
        DrillingSite(**(site_values() | {field: value}))


def test_zero_measured_depth_rejected():
    with pytest.raises(ValidationError, match="planned_md_ft"):
        DrillingSite(**(site_values() | {"planned_md_ft": 0}))


@pytest.mark.parametrize("component", [0, 1])
@pytest.mark.parametrize("value", INVALID_REAL)
def test_coordinate_contract(component, value):
    coords = [0.0, 0.0]
    coords[component] = value
    with pytest.raises(ValidationError, match="location_coords"):
        DrillingSite(**(site_values() | {"location_coords": tuple(coords)}))


@pytest.mark.parametrize(
    "field", ["rig_day_rate_usd", "mobilization_cost_usd", "learning_curve_factor"]
)
@pytest.mark.parametrize("value", INVALID_REAL + [-1])
def test_campaign_real_contract(field, value):
    with pytest.raises(ValidationError, match=field):
        DrillCampaign(**(campaign_values() | {field: value}))


@pytest.mark.parametrize(
    "field,value",
    [
        ("rig_day_rate_usd", 0),
        ("learning_curve_factor", 0),
        ("learning_curve_factor", 2),
    ],
)
def test_campaign_sign_boundaries(field, value):
    with pytest.raises(ValidationError, match=field):
        DrillCampaign(**(campaign_values() | {field: value}))


def test_valid_boundaries():
    values = campaign_values() | {
        "mobilization_cost_usd": 0,
        "learning_curve_factor": 1,
    }
    campaign = DrillCampaign(**values)
    assert campaign.wells[0].water_depth_ft == 0
    assert campaign.learning_curve_factor == 1


@pytest.mark.parametrize("field", ["well_id", "field_name", "well_type", "bore_design"])
@pytest.mark.parametrize("value", [0, None, "", " "])
def test_site_text_contract(field, value):
    with pytest.raises(ValidationError, match=field):
        DrillingSite(**(site_values() | {field: value}))


@pytest.mark.parametrize("field", ["campaign_id", "rig_name"])
@pytest.mark.parametrize("value", [0, None, "", " "])
def test_campaign_text_contract(field, value):
    with pytest.raises(ValidationError, match=field):
        DrillCampaign(**(campaign_values() | {field: value}))


@pytest.mark.parametrize("value", [0, 1, "false", None])
def test_boolean_contract(value):
    with pytest.raises(ValidationError, match="mpd_required"):
        DrillingSite(**(site_values() | {"mpd_required": value}))


# Each entry isolates a direct-call field, including currently unused arguments.
DIRECT_CASES = [
    (
        "learning_curve_time",
        {"base_time_days": 12, "well_position": 1, "lc_factor": 0.5},
        "base_time_days",
        False,
    ),
    (
        "learning_curve_time",
        {"base_time_days": 12, "well_position": 1, "lc_factor": 0.5},
        "well_position",
        False,
    ),
    (
        "learning_curve_time",
        {"base_time_days": 12, "well_position": 1, "lc_factor": 0.5},
        "lc_factor",
        False,
    ),
    ("mobilization_savings", {"mob_cost": 300, "n_wells_batch": 3}, "mob_cost", True),
    (
        "mobilization_savings",
        {"mob_cost": 300, "n_wells_batch": 3},
        "n_wells_batch",
        False,
    ),
    (
        "mobilization_savings",
        {"mob_cost": 300, "n_wells_batch": 3},
        "n_wells_standalone",
        False,
    ),
    (
        "break_even_n_wells",
        {"mob_cost": 300, "day_rate": 100, "base_well_days": 12, "lc_factor": 0.5},
        "mob_cost",
        True,
    ),
    (
        "break_even_n_wells",
        {"mob_cost": 300, "day_rate": 100, "base_well_days": 12, "lc_factor": 0.5},
        "day_rate",
        False,
    ),
    (
        "break_even_n_wells",
        {"mob_cost": 300, "day_rate": 100, "base_well_days": 12, "lc_factor": 0.5},
        "base_well_days",
        False,
    ),
    (
        "break_even_n_wells",
        {"mob_cost": 300, "day_rate": 100, "base_well_days": 12, "lc_factor": 0.5},
        "lc_factor",
        False,
    ),
]


@pytest.mark.parametrize("method,arguments,field,zero_allowed", DIRECT_CASES)
@pytest.mark.parametrize("value", INVALID_REAL + [-1, 0])
def test_direct_numeric_contract(method, arguments, field, zero_allowed, value):
    if zero_allowed and value == 0 and not isinstance(value, bool):
        return
    with pytest.raises(ValidationError, match=field):
        getattr(BatchDrillingEconomics(), method)(**(arguments | {field: value}))


@pytest.mark.parametrize(
    "field", ["well_position", "n_wells_batch", "n_wells_standalone"]
)
@pytest.mark.parametrize("value", [1.0, 1.5])
def test_counts_require_integers(field, value):
    method, args, _, _ = next(row for row in DIRECT_CASES if row[2] == field)
    with pytest.raises(ValidationError, match=field):
        getattr(BatchDrillingEconomics(), method)(**(args | {field: value}))


@pytest.mark.parametrize("sequence", [[], ["W3", "W1", "W2"]])
def test_complete_sequence(sequence):
    campaign = DrillCampaign(**(campaign_values() | {"sequence": sequence}))
    assert [w.well_id for w in campaign.ordered_wells()] == (
        sequence or ["W1", "W2", "W3"]
    )


@pytest.mark.parametrize(
    "sequence,message",
    [
        (["W1", "W1", "W3"], "duplicate.*W1"),
        (["W1", "W2", "unknown"], "unknown.*unknown"),
        (["W1", "W2"], "omitted.*W3"),
    ],
)
def test_incomplete_sequence_rejected(sequence, message):
    with pytest.raises(ValidationError, match=message) as caught:
        DrillCampaign(**(campaign_values() | {"sequence": sequence}))
    assert caught.value.errors()[0]["loc"] == ("sequence",)


def test_duplicate_well_id_rejected():
    values = campaign_values()
    values["wells"][2] = values["wells"][0]
    with pytest.raises(ValidationError, match="wells.*duplicate.*W1"):
        DrillCampaign(**values)


@pytest.mark.parametrize("all_excluded", [False, True])
def test_empty_campaign_rejected(all_excluded):
    values = campaign_values()
    if all_excluded:
        excluded_ids = {"W1", "W2", "W3"}
        values["wells"] = [w for w in values["wells"] if w.well_id not in excluded_ids]
    else:
        values["wells"] = []
    with pytest.raises(ValidationError, match="wells.*at least one"):
        DrillCampaign(**values)


@pytest.mark.parametrize("method", ["campaign_total_cost", "batch_vs_standalone_npv"])
@pytest.mark.parametrize("mutation", ["empty", "nonfinite", "sequence"])
def test_direct_campaign_revalidates_mutation(method, mutation):
    campaign = DrillCampaign(**campaign_values())
    if mutation == "empty":
        campaign.wells.clear()
    elif mutation == "nonfinite":
        campaign.wells[0].__dict__["planned_md_ft"] = math.nan
    else:
        campaign.sequence.append("unknown")
    with pytest.raises(ValidationError, match="campaign"):
        getattr(BatchDrillingEconomics(), method)(campaign, base_days_per_well=12)


@pytest.mark.parametrize("method", ["campaign_total_cost", "batch_vs_standalone_npv"])
@pytest.mark.parametrize("value", INVALID_REAL + [-1, 0])
def test_direct_campaign_duration(method, value):
    with pytest.raises(ValidationError, match="base_days_per_well"):
        getattr(BatchDrillingEconomics(), method)(
            DrillCampaign(**campaign_values()), base_days_per_well=value
        )


@pytest.mark.parametrize("method", ["learning_curve_time", "break_even_n_wells"])
def test_direct_factor_upper_bound(method):
    args = {"lc_factor": 2}
    if method == "learning_curve_time":
        args.update(base_time_days=12, well_position=1)
    else:
        args.update(mob_cost=300, day_rate=100, base_well_days=12)
    with pytest.raises(ValidationError, match="lc_factor"):
        getattr(BatchDrillingEconomics(), method)(**args)


@pytest.mark.parametrize(
    "field", ["water_depth_ft", "planned_md_ft", "location_coords"]
)
def test_required_site_numeric_fields(field):
    values = site_values()
    values.pop(field)
    with pytest.raises(ValidationError, match=field):
        DrillingSite(**values)


@pytest.mark.parametrize(
    "field", ["rig_day_rate_usd", "mobilization_cost_usd", "learning_curve_factor"]
)
def test_required_campaign_numeric_fields(field):
    values = campaign_values()
    values.pop(field)
    with pytest.raises(ValidationError, match=field):
        DrillCampaign(**values)
