"""Numeric and sequencing contracts using synthetic, explicitly unitized inputs."""

import math

import numpy as np
import pytest

from worldenergydata.drilling import BatchDrillingEconomics, DrillCampaign, DrillingSite


def site(well_id="W1", **changes):
    values = dict(
        well_id=well_id,
        field_name="Synthetic field",
        location_coords=(0.0, 0.0),
        water_depth_ft=0.0,
        planned_md_ft=8000.0,
        well_type="development",
    )
    values.update(changes)
    return DrillingSite(**values)


def campaign(**changes):
    values = dict(
        campaign_id="C1",
        rig_name="Synthetic rig",
        rig_day_rate_usd=10.0,
        mobilization_cost_usd=100.0,
        wells=[site("W1"), site("W2")],
        learning_curve_factor=0.5,
    )
    values.update(changes)
    return DrillCampaign(**values)


NONFINITE = [float("nan"), float("inf"), -float("inf")]
NONNUMERIC = [True, False, np.bool_(True), np.bool_(False), "1", "1 day", None]


@pytest.mark.parametrize("field", ["water_depth_ft", "planned_md_ft"])
@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC + [-1.0])
def test_site_rejects_invalid_depth(field, value):
    with pytest.raises(ValueError, match=field):
        site(**{field: value})


@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC)
@pytest.mark.parametrize("coordinate", [0, 1])
def test_site_rejects_invalid_coordinate(coordinate, value):
    coords = [0.0, 0.0]
    coords[coordinate] = value
    with pytest.raises(ValueError, match="location_coords"):
        site(location_coords=coords)


@pytest.mark.parametrize(
    "coords", [(90.1, 0), (-90.1, 0), (0, 180.1), (0, -180.1), (0,), (0, 0, 0)]
)
def test_coordinate_bounds_and_arity(coords):
    with pytest.raises(ValueError, match="location_coords"):
        site(location_coords=coords)


def test_geometry_boundaries_and_positive_depth():
    for coords in [(-90, -180), (90, 180)]:
        assert site(location_coords=coords).location_coords == coords
    assert site(water_depth_ft=0).water_depth_ft == 0
    with pytest.raises(ValueError, match="planned_md_ft"):
        site(planned_md_ft=0)


@pytest.mark.parametrize(
    "field", ["rig_day_rate_usd", "mobilization_cost_usd", "learning_curve_factor"]
)
@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC + [-1.0])
def test_campaign_rejects_invalid_financial_number(field, value):
    with pytest.raises(ValueError, match=field):
        campaign(**{field: value})


@pytest.mark.parametrize(
    "changes",
    [
        dict(rig_day_rate_usd=0),
        dict(learning_curve_factor=0),
        dict(learning_curve_factor=1.1),
    ],
)
def test_campaign_positive_rate_and_factor_bounds(changes):
    with pytest.raises(ValueError):
        campaign(**changes)


def test_zero_mobilization_and_no_learning_are_valid():
    model = campaign(mobilization_cost_usd=0, learning_curve_factor=1)
    assert BatchDrillingEconomics().campaign_total_cost(model, 20) == 400


@pytest.mark.parametrize("sequence", [[], ["W2", "W1"]])
def test_sequence_preserves_all_wells_exactly_once(sequence):
    model = campaign(sequence=sequence)
    ordered = model.ordered_wells()
    assert [well.well_id for well in ordered] == (sequence or ["W1", "W2"])
    assert len(ordered) == len(model.wells) == 2
    assert ordered is not model.wells


@pytest.mark.parametrize(
    "sequence",
    [
        ["W1", "W1"],
        ["W1"],
        ["W1", "unknown"],
        ["W1", "W2", "unknown"],
        ["W2", "W1", "W2"],
    ],
)
def test_sequence_rejects_duplicate_unknown_and_omitted_identifiers(sequence):
    with pytest.raises(ValueError, match="sequence"):
        campaign(sequence=sequence)


def test_campaign_rejects_duplicate_well_identifiers():
    with pytest.raises(ValueError, match="well_id"):
        campaign(wells=[site("W1"), site("W1")])


@pytest.mark.parametrize("well_id", ["", " ", "\t"])
def test_blank_well_identifier_is_rejected(well_id):
    with pytest.raises(ValueError, match="well_id"):
        site(well_id)


def test_empty_campaign_is_rejected():
    with pytest.raises(ValueError, match="wells"):
        campaign(wells=[])


@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC + [-1, 0])
def test_direct_duration_requires_positive_finite_days(value):
    with pytest.raises(ValueError, match="base_time_days"):
        BatchDrillingEconomics().learning_curve_time(
            base_time_days=value, well_position=1
        )


@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC + [-1, 0, 1.0, 1.5])
@pytest.mark.parametrize(
    "argument", ["well_position", "n_wells_batch", "n_wells_standalone"]
)
def test_direct_counts_are_positive_integers(argument, value):
    calc = BatchDrillingEconomics()
    with pytest.raises(ValueError, match=argument):
        if argument == "well_position":
            calc.learning_curve_time(20, well_position=value)
        else:
            args = dict(n_wells_batch=2, n_wells_standalone=1)
            args[argument] = value
            calc.mobilization_savings(100, **args)


@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC + [-1, 0, 1.1])
@pytest.mark.parametrize("method", ["learning_curve_time", "break_even_n_wells"])
def test_direct_learning_factor_is_checked_even_at_first_position(method, value):
    args = [20, 1] if method == "learning_curve_time" else [100, 10, 20]
    with pytest.raises(ValueError, match="lc_factor"):
        getattr(BatchDrillingEconomics(), method)(*args, lc_factor=value)


@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC + [-1])
@pytest.mark.parametrize("method", ["mobilization_savings", "break_even_n_wells"])
def test_direct_mobilization_is_nonnegative_finite_usd(method, value):
    args = dict(mob_cost=value)
    if method == "mobilization_savings":
        args["n_wells_batch"] = 2
    else:
        args.update(day_rate=10, base_well_days=20)
    with pytest.raises(ValueError, match="mob_cost"):
        getattr(BatchDrillingEconomics(), method)(**args)


@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC + [-1, 0])
@pytest.mark.parametrize("argument", ["day_rate", "base_well_days"])
def test_break_even_rate_and_duration_are_positive_finite(argument, value):
    args = dict(mob_cost=100, day_rate=10, base_well_days=20)
    args[argument] = value
    with pytest.raises(ValueError, match=argument):
        BatchDrillingEconomics().break_even_n_wells(**args)


@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC + [-1, 0])
def test_campaign_cost_requires_positive_finite_days(value):
    with pytest.raises(ValueError, match="base_days_per_well"):
        BatchDrillingEconomics().campaign_total_cost(
            campaign(), base_days_per_well=value
        )


@pytest.mark.parametrize("value", NONFINITE + NONNUMERIC)
def test_ignored_discount_rate_still_requires_a_finite_number(value):
    with pytest.raises(ValueError, match="discount_rate"):
        BatchDrillingEconomics().batch_vs_standalone_npv(
            campaign(), discount_rate=value
        )


def test_hand_calculated_units_and_ignored_compatibility_arguments():
    calc = BatchDrillingEconomics()
    model = campaign()
    # Synthetic 20 days, then 10 days; 100 USD + 10 USD/day * 30 days.
    assert calc.learning_curve_time(20, 2, 0.5) == 10
    assert calc.mobilization_savings(100, 2, 7) == 50
    assert calc.mobilization_savings(0, 2) == 0
    assert calc.campaign_total_cost(model, 20) == 400
    # Depth heuristic's floor gives 30 days, then 15; standalone = 2*(100+300).
    expected = dict(batch_npv=550, standalone_npv=800, batch_savings=250)
    assert calc.batch_vs_standalone_npv(model, -0.1) == expected
    assert calc.batch_vs_standalone_npv(model, 0) == expected
    assert calc.break_even_n_wells(0, 10, 20, 1) == 1
    assert calc.break_even_n_wells(100, 10, 20, 1) == 2
    assert calc.learning_curve_time(20, 2, 1) == 20


def test_numpy_real_numbers_and_integer_counts_are_accepted():
    calc = BatchDrillingEconomics()
    model = campaign(rig_day_rate_usd=np.float32(10))
    assert calc.learning_curve_time(np.float64(20), np.int64(2), np.float32(0.5)) == 10
    assert calc.mobilization_savings(np.int64(100), np.int32(2)) == 50
    assert calc.campaign_total_cost(model, np.float32(20)) == 400
    assert site(planned_md_ft=np.int64(8000)).planned_md_ft == 8000


def test_identifiers_are_exact_case_sensitive_and_not_trimmed():
    ids = ["A", "a", "A "]
    model = campaign(wells=[site(well_id) for well_id in ids], sequence=ids[::-1])
    assert [well.well_id for well in model.ordered_wells()] == ids[::-1]


@pytest.mark.parametrize("sequence", [[], ["W2", "W1"]])
def test_ordered_wells_preserves_site_identity(sequence):
    model = campaign(sequence=sequence)
    originals = {well.well_id: well for well in model.wells}
    for well in model.ordered_wells():
        assert well is originals[well.well_id]


@pytest.mark.parametrize("sequence", [[], ["W2", "W1"]])
def test_ordered_wells_normalizes_site_subclasses(sequence):
    class SiteSubclass(DrillingSite):
        pass

    model = campaign(sequence=sequence)
    original = SiteSubclass(**model.wells[0].model_dump())
    unchanged = model.wells[1]
    model.wells[0] = original

    ordered = model.ordered_wells()

    assert [well.well_id for well in ordered] == (sequence or ["W1", "W2"])
    by_id = {well.well_id: well for well in ordered}
    assert type(by_id["W1"]) is DrillingSite
    assert by_id["W1"] is not original
    assert by_id["W1"].model_dump() == original.model_dump()
    assert by_id["W2"] is unchanged
    assert model.wells[0] is original
    calc = BatchDrillingEconomics()
    # 100 + 10*(20+10) = 400 USD; heuristic days 30+15 give 550 USD.
    assert calc.campaign_total_cost(model, 20) == 400
    assert calc.batch_vs_standalone_npv(model) == dict(
        batch_npv=550, standalone_npv=800, batch_savings=250
    )


def test_break_even_evaluates_each_position_once(monkeypatch):
    calc = BatchDrillingEconomics()
    duration = calc.learning_curve_time
    positions = []

    def tracked_duration(base_time_days, well_position, lc_factor):
        positions.append(well_position)
        return duration(base_time_days, well_position, lc_factor)

    monkeypatch.setattr(calc, "learning_curve_time", tracked_duration)
    # Zero mobilization and no learning: 10*20*N ties for all 200 sizes.
    assert calc.break_even_n_wells(0, 10, 20, 1) == 1
    assert positions == list(range(1, 201))


@pytest.mark.parametrize("sequence", [[], ["W2", "W1"]])
def test_ordered_wells_normalizes_mutated_mapping_entries(sequence):
    model = campaign(sequence=sequence)
    mapping = model.wells[0].model_dump()
    original_site = model.wells[1]
    model.wells[0] = mapping

    ordered = model.ordered_wells()

    assert all(isinstance(well, DrillingSite) for well in ordered)
    assert [well.well_id for well in ordered] == (sequence or ["W1", "W2"])
    by_id = {well.well_id: well for well in ordered}
    assert by_id["W1"].model_dump() == mapping
    assert by_id["W2"] is original_site
    assert model.wells[0] is mapping
    calc = BatchDrillingEconomics()
    assert calc.campaign_total_cost(model, 20) == 400
    assert calc.batch_vs_standalone_npv(model) == dict(
        batch_npv=550, standalone_npv=800, batch_savings=250
    )


@pytest.mark.parametrize("sequence", [[], ["W2", "W1"]])
@pytest.mark.parametrize("mutation", ["identifier", "coordinates", "depth", "iterator"])
def test_ordered_wells_uses_normalized_snapshot(sequence, mutation):
    model = campaign(sequence=sequence)
    originals = {well.well_id: well for well in model.wells}
    if mutation == "identifier":
        model.wells[0].well_id = b"W1"
    elif mutation == "coordinates":
        model.wells[0].location_coords = (0, 0)
    elif mutation == "depth":
        model.wells[0].water_depth_ft = np.float64(0)
    else:
        model.wells = iter(model.wells)

    ordered = model.ordered_wells()

    assert [well.well_id for well in ordered] == (sequence or ["W1", "W2"])
    by_id = {well.well_id: well for well in ordered}
    assert type(by_id["W1"].well_id) is str
    assert all(type(value) is float for value in by_id["W1"].location_coords)
    assert type(by_id["W1"].water_depth_ft) is float
    assert by_id["W2"] is originals["W2"]
    if mutation == "iterator":
        assert by_id["W1"] is originals["W1"]
    else:
        assert by_id["W1"] is not originals["W1"]
    # Check both cost consumers on the same normalized snapshot.
    normalized = campaign(wells=ordered, sequence=sequence)
    calc = BatchDrillingEconomics()
    assert calc.campaign_total_cost(normalized, 20) == 400
    assert calc.batch_vs_standalone_npv(normalized) == dict(
        batch_npv=550, standalone_npv=800, batch_savings=250
    )


def test_fraction_real_values_are_accepted():
    from fractions import Fraction

    assert site(water_depth_ft=Fraction(1, 2)).water_depth_ft == 0.5
    assert (
        BatchDrillingEconomics().learning_curve_time(Fraction(20), 2, Fraction(1, 2))
        == 10
    )


@pytest.mark.parametrize("sign", [-1, 1])
def test_nonzero_real_inputs_that_underflow_are_rejected(sign):
    from fractions import Fraction

    tiny = Fraction(sign, 10**400)
    with pytest.raises(ValueError):
        site(water_depth_ft=tiny)
    with pytest.raises(ValueError):
        campaign(mobilization_cost_usd=tiny)
    with pytest.raises(ValueError):
        BatchDrillingEconomics().mobilization_savings(tiny, 2)


def test_learning_duration_that_underflows_is_rejected():
    with pytest.raises(ValueError):
        BatchDrillingEconomics().learning_curve_time(1e-308, 10**308, 0.5)


def test_decimal_and_complex_numbers_are_rejected():
    from decimal import Decimal

    for value in (Decimal("1"), complex(1), np.complex128(1)):
        with pytest.raises(ValueError, match="water_depth_ft"):
            site(water_depth_ft=value)
        with pytest.raises(ValueError):
            BatchDrillingEconomics().learning_curve_time(value, 1)


@pytest.mark.parametrize(
    "argument", ["depth", "base_time_days", "well_position", "n_wells_batch"]
)
def test_unrepresentable_integers_are_rejected(argument):
    value = 10**400
    with pytest.raises(ValueError):
        if argument == "depth":
            site(planned_md_ft=value)
        elif argument == "n_wells_batch":
            BatchDrillingEconomics().mobilization_savings(100, value)
        else:
            args = dict(base_time_days=20, well_position=2)
            args[argument] = value
            BatchDrillingEconomics().learning_curve_time(**args)


def test_mapping_campaign_is_rejected():
    with pytest.raises(ValueError, match="DrillCampaign instance"):
        BatchDrillingEconomics().campaign_total_cost(campaign().model_dump(), 20)


@pytest.mark.parametrize(
    "consumer", ["ordered_wells", "campaign_total_cost", "batch_vs_standalone_npv"]
)
@pytest.mark.parametrize(
    "mutation", ["empty", "sequence", "duplicate", "rate", "depth"]
)
def test_mutated_campaign_is_revalidated_at_consumption(consumer, mutation):
    model = campaign()
    if mutation == "empty":
        model.wells.clear()
    elif mutation == "sequence":
        model.sequence.append("unknown")
    elif mutation == "duplicate":
        model.wells.append(site("W1"))
    elif mutation == "rate":
        model.rig_day_rate_usd = math.inf
    else:
        model.wells[0].planned_md_ft = math.nan
    fields = dict(
        empty="wells",
        sequence="sequence",
        duplicate="well_id",
        rate="rig_day_rate_usd",
        depth="planned_md_ft",
    )
    with pytest.raises(ValueError, match=fields[mutation]):
        if consumer == "ordered_wells":
            model.ordered_wells()
        elif consumer == "campaign_total_cost":
            BatchDrillingEconomics().campaign_total_cost(model, 20)
        else:
            BatchDrillingEconomics().batch_vs_standalone_npv(model)


@pytest.mark.parametrize("constructed", [False, True])
def test_subclasses_and_constructed_instances_are_revalidated(constructed):
    class CampaignSubclass(DrillCampaign):
        pass

    model = campaign()
    if constructed:
        model = DrillCampaign.model_construct(**dict(model.__dict__, wells=[]))
    else:
        model = CampaignSubclass(**model.model_dump())
        model.wells[0] = DrillingSite.model_construct(
            **dict(site().__dict__, water_depth_ft=-1)
        )
    with pytest.raises(ValueError, match="wells" if constructed else "water_depth_ft"):
        BatchDrillingEconomics().campaign_total_cost(model, 20)


@pytest.mark.parametrize("method", ["campaign_total_cost", "batch_vs_standalone_npv"])
def test_duck_typed_campaign_is_rejected(method):
    from types import SimpleNamespace

    fake = SimpleNamespace(**campaign().__dict__)
    args = [fake, 20] if method == "campaign_total_cost" else [fake]
    with pytest.raises(ValueError, match="DrillCampaign instance"):
        getattr(BatchDrillingEconomics(), method)(*args)


def test_overflowing_intermediate_depth_sum_is_rejected():
    model = campaign(
        wells=[site("W1", planned_md_ft=1e308), site("W2", planned_md_ft=1e308)]
    )
    with pytest.raises(ValueError):
        BatchDrillingEconomics().batch_vs_standalone_npv(model)


@pytest.mark.parametrize(
    "method", ["break_even_n_wells", "campaign_total_cost", "batch_vs_standalone_npv"]
)
def test_finite_inputs_that_overflow_cost_are_rejected(method):
    calc = BatchDrillingEconomics()
    with pytest.raises(ValueError):
        if method == "break_even_n_wells":
            calc.break_even_n_wells(100, 1e308, 20)
        else:
            model = campaign(rig_day_rate_usd=1e308)
            if method == "campaign_total_cost":
                calc.campaign_total_cost(model, 20)
            else:
                calc.batch_vs_standalone_npv(model)
