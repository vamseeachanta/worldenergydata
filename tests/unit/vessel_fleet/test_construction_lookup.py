"""Offline lookup contracts; accepted facts come from the shipped evidence bundle."""

import copy

import pytest

from worldenergydata.vessel_fleet import construction_evidence as ce


@pytest.fixture
def bundle():
    return ce.load_evidence()


def test_imo_lookup_returns_the_accepted_record_with_provenance(bundle):
    """Expected identity is the exact accepted fact, independently selected here."""
    expected = next(row for row in bundle["vessels"] if row["imo"])
    result = ce.find_by_imo(expected["imo"]["value"], bundle=bundle)
    assert result == expected
    assert result["imo"]["source_id"]
    assert result["identity_status"] == expected["identity_status"]
    assert result["hull_model"] == expected["hull_model"]


def test_imo_lookup_returns_a_detached_record(bundle):
    expected = next(row for row in bundle["vessels"] if row["imo"])
    result = ce.find_by_imo(expected["imo"]["value"], bundle=bundle)
    result["imo"]["value"] = "changed"
    result["candidates"].append({"value": "changed"})
    assert result != expected
    assert ce.find_by_imo(expected["imo"]["value"], bundle=bundle) == expected


def test_candidate_imo_is_not_an_accepted_identity(bundle):
    """Moving an accepted fact to candidates removes it from accepted lookup."""
    expected = next(row for row in bundle["vessels"] if row["imo"])
    imo = copy.deepcopy(expected["imo"])
    expected["candidates"].append(imo)
    expected["imo"] = None
    expected["identity_status"] = "partial"
    assert ce.find_by_imo(imo["value"], bundle=bundle) is None


@pytest.mark.parametrize(
    "value",
    [None, True, 1234567, "", "123456", "12345678", "IMO 1234567", "１２３４５６７"],
)
def test_imo_lookup_rejects_malformed_identifiers(value, bundle):
    # Synthetic format cases exercise the existing seven-ASCII-digit contract
    # in construction_evidence._validate_vessel; no registry identity is asserted.
    with pytest.raises(ValueError, match="IMO"):
        ce.find_by_imo(value, bundle=bundle)


def test_imo_lookup_validates_the_evidence_before_returning(bundle):
    expected = next(row for row in bundle["vessels"] if row["imo"])
    bundle["vessels"][0]["provenance"] = ""
    with pytest.raises(ValueError, match="provenance"):
        ce.find_by_imo(expected["imo"]["value"], bundle=bundle)


def test_imo_lookup_uses_the_packaged_bundle_by_default(bundle):
    expected = next(row for row in bundle["vessels"] if row["imo"])
    assert ce.find_by_imo(expected["imo"]["value"]) == expected


@pytest.fixture
def crane_bundle(bundle):
    """Synthetic inputs: 100 t on [10, 20] m and 60 t at exactly 30 m.

    These are comparison fixtures, not vessel specifications. The independent
    hand calculation is interval membership followed by capacity >= demand.
    For example 10 <= 15 <= 20 and 100 >= 100; 100 < 101; 25 is in neither
    [10, 20] nor {30}. No interpolation can establish capacity at 25 m.
    """
    template = copy.deepcopy(bundle["cranes"][0])
    template.update(
        crane="synthetic main hoist",
        mode="synthetic revolving configuration",
        capacity_t=100,
        radius_kind="interval",
        radius_min_m=10,
        radius_max_m=20,
        locator="Synthetic comparison fixture; see crane_bundle docstring",
        value_quote="100 t on [10, 20] m (synthetic test input)",
    )
    point = {
        **template,
        "capacity_t": 60,
        "radius_kind": "point",
        "radius_min_m": 30,
        "radius_max_m": 30,
        "value_quote": "60 t at 30 m (synthetic test input)",
    }
    bundle["cranes"] = [template, point]
    return bundle


def screen(bundle, radius_m=15, minimum_capacity_t=100, **changes):
    rating = bundle["cranes"][0]
    arguments = {
        "vessel_name": rating["vessel_name"],
        "crane": rating["crane"],
        "mode": rating["mode"],
        "radius_m": radius_m,
        "minimum_capacity_t": minimum_capacity_t,
        "bundle": bundle,
        **changes,
    }
    return ce.screen_crane(**arguments)


@pytest.mark.parametrize("radius", [10, 15, 20])
def test_crane_interval_includes_both_printed_bounds(crane_bundle, radius):
    """Hand calculation: each radius is in [10, 20]; 100 >= 100 t."""
    result = screen(crane_bundle, radius_m=radius)
    assert result["evaluation"] == "MATCH"
    assert result["capacity_t"] == 100
    assert result["matched_ratings"] == crane_bundle["cranes"][:1]
    assert result["vessel"]["provenance"]
    assert result["vessel"]["hull_model"]


def test_crane_below_capacity_preserves_the_printed_rating(crane_bundle):
    """Hand calculation: 15 is in [10, 20], but 100 < 101 t."""
    result = screen(crane_bundle, minimum_capacity_t=101)
    assert result["evaluation"] == "BELOW_CAPACITY"
    assert result["capacity_t"] == 100
    assert result["matched_ratings"] == crane_bundle["cranes"][:1]


def test_crane_point_qualifies_only_at_its_printed_radius(crane_bundle):
    """Hand calculation: 30 == 30 m and 60 >= 60 t."""
    result = screen(crane_bundle, radius_m=30, minimum_capacity_t=60)
    assert result["evaluation"] == "MATCH"
    assert result["capacity_t"] == 60
    assert result["matched_ratings"] == crane_bundle["cranes"][1:]


@pytest.mark.parametrize("radius", [5, 25, 35])
def test_crane_does_not_interpolate_or_extrapolate(crane_bundle, radius):
    """Hand calculation: these radii are outside [10, 20] and unequal to 30."""
    result = screen(crane_bundle, radius_m=radius)
    assert result["evaluation"] == "NOT_EVALUATED"
    assert result["capacity_t"] is None
    assert result["matched_ratings"] == []
    assert (
        result["reason"]
        == "No printed point or bounded interval covers the requested radius"
    )


@pytest.mark.parametrize("radius", [5, 20])
def test_unknown_lower_bound_never_becomes_zero(crane_bundle, radius):
    """A missing lower bound excludes both 5 m and the printed 20 m endpoint.

    The conservative query policy requires a bounded interval or a separate
    point rating, even at the endpoint; no lower bound is inferred as zero.
    """
    rating = crane_bundle["cranes"][0]
    rating.update(radius_kind="up_to", radius_min_m=None)
    result = screen(crane_bundle, radius_m=radius)
    assert result["evaluation"] == "NOT_EVALUATED"
    assert result["capacity_t"] is None
    assert result["matched_ratings"] == []
    assert result["reason"] == (
        "Unknown lower bound for up_to rating; its printed endpoint is also excluded"
    )


@pytest.mark.parametrize("radius", [21, 25])
def test_radius_beyond_up_to_endpoint_is_a_coverage_gap(crane_bundle, radius):
    """Both radii exceed 20 m and differ from the separate printed 30 m point."""
    crane_bundle["cranes"][0].update(radius_kind="up_to", radius_min_m=None)
    result = screen(crane_bundle, radius_m=radius)
    assert result["evaluation"] == "NOT_EVALUATED"
    assert result["reason"] == (
        "No printed point or bounded interval covers the requested radius"
    )


def test_up_to_rating_does_not_exclude_a_separate_printed_point(crane_bundle):
    """The 60 t point at 30 m qualifies independently of the unbounded rating."""
    crane_bundle["cranes"][0].update(radius_kind="up_to", radius_min_m=None)
    result = screen(crane_bundle, radius_m=30, minimum_capacity_t=60)
    assert result["evaluation"] == "MATCH"
    assert result["capacity_t"] == 60
    assert result["matched_ratings"] == crane_bundle["cranes"][1:]


@pytest.mark.parametrize("field", ["crane", "mode"])
def test_other_hoists_and_configurations_never_supply_capacity(crane_bundle, field):
    result = screen(crane_bundle, **{field: "different configuration"})
    assert result["evaluation"] == "NOT_EVALUATED"
    assert result["matched_ratings"] == []
    assert (
        result["reason"] == "No printed rating for the selected hoist and configuration"
    )


def test_crane_label_case_mismatch_is_not_a_radius_gap(bundle):
    """An exact printed bound is covered; changing the hoist label loses selection."""
    rating = next(r for r in bundle["cranes"] if r["radius_kind"] == "interval")
    assert rating["crane"].upper() != rating["crane"]
    result = ce.screen_crane(
        rating["vessel_name"],
        crane=rating["crane"].upper(),
        mode=rating["mode"],
        radius_m=rating["radius_min_m"],
        minimum_capacity_t=rating["capacity_t"],
        bundle=bundle,
    )
    assert result["evaluation"] == "NOT_EVALUATED"
    assert result["capacity_t"] is None
    assert result["matched_ratings"] == []
    assert (
        result["reason"] == "No printed rating for the selected hoist and configuration"
    )


def test_conflicting_overlapping_ratings_remain_not_evaluated(crane_bundle):
    """Hand calculation: both intervals contain 15, but 100 != 90 t."""
    other = {
        **crane_bundle["cranes"][0],
        "radius_min_m": 15,
        "radius_max_m": 25,
        "capacity_t": 90,
        "value_quote": "90 t on [15, 25] m (synthetic test input)",
    }
    crane_bundle["cranes"].append(other)
    result = screen(crane_bundle)
    assert result["evaluation"] == "NOT_EVALUATED"
    assert result["capacity_t"] is None
    assert len(result["matched_ratings"]) == 2
    assert "conflict" in result["reason"].lower()


def test_agreeing_overlapping_ratings_retain_all_provenance(crane_bundle):
    """Hand calculation: both intervals contain 15 and each states 100 t."""
    other = {**crane_bundle["cranes"][0], "radius_min_m": 15, "radius_max_m": 25}
    crane_bundle["cranes"].append(other)
    result = screen(crane_bundle)
    assert result["evaluation"] == "MATCH"
    assert result["capacity_t"] == 100
    assert result["matched_ratings"] == [crane_bundle["cranes"][0], other]


def test_crane_result_is_detached_and_keeps_source_metadata(crane_bundle):
    result = screen(crane_bundle)
    citation = result["matched_ratings"][0]
    assert (
        result["sources"][citation["source_id"]]
        == crane_bundle["sources"][citation["source_id"]]
    )
    result["vessel"]["hull_model"] = "changed"
    citation["capacity_t"] = 0
    result["sources"].clear()
    assert screen(crane_bundle)["evaluation"] == "MATCH"


def test_unknown_vessel_is_an_input_error(crane_bundle):
    with pytest.raises(ValueError, match="vessel"):
        screen(crane_bundle, vessel_name="synthetic absent identity")


@pytest.mark.parametrize("value", [-1, 0, float("inf"), float("nan"), True, "15", None])
def test_crane_rejects_invalid_radius(crane_bundle, value):
    with pytest.raises(ValueError, match="radius"):
        screen(crane_bundle, radius_m=value)


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan"), True, "100", None])
def test_crane_rejects_invalid_demand(crane_bundle, value):
    with pytest.raises(ValueError, match="capacity"):
        screen(crane_bundle, minimum_capacity_t=value)


@pytest.mark.parametrize("field", ["vessel_name", "crane", "mode"])
@pytest.mark.parametrize("value", ["", " ", None, True])
def test_crane_requires_explicit_configuration(crane_bundle, field, value):
    with pytest.raises(ValueError):
        screen(crane_bundle, **{field: value})


def test_crane_missing_ratings_remain_not_evaluated(crane_bundle):
    rating = crane_bundle["cranes"][0]
    crane_bundle["cranes"] = []
    result = ce.screen_crane(
        rating["vessel_name"],
        crane=rating["crane"],
        mode=rating["mode"],
        radius_m=15,
        minimum_capacity_t=100,
        bundle=crane_bundle,
    )
    assert result["evaluation"] == "NOT_EVALUATED"
    assert (
        result["reason"] == "No printed rating for the selected hoist and configuration"
    )


def test_crane_validates_evidence_before_screening(crane_bundle):
    crane_bundle["vessels"][0]["provenance"] = ""
    with pytest.raises(ValueError, match="provenance"):
        screen(crane_bundle)


def test_crane_uses_packaged_evidence_by_default(bundle):
    """A printed interval includes its lower bound, and its capacity equals itself.

    Inputs and expected rating are selected directly from the committed table;
    source_id, locator and value_quote identify the published expected value.
    """
    rating = next(r for r in bundle["cranes"] if r["radius_kind"] == "interval")
    result = ce.screen_crane(
        rating["vessel_name"],
        crane=rating["crane"],
        mode=rating["mode"],
        radius_m=rating["radius_min_m"],
        minimum_capacity_t=rating["capacity_t"],
    )
    assert result["evaluation"] == "MATCH"
    assert result["matched_ratings"] == [rating]


def test_crane_zero_demand_still_requires_printed_coverage(crane_bundle):
    """Hand calculation: 100 >= 0 at 15 m; 25 m still has no printed rating."""
    assert screen(crane_bundle, minimum_capacity_t=0)["evaluation"] == "MATCH"
    assert (
        screen(crane_bundle, radius_m=25, minimum_capacity_t=0)["evaluation"]
        == "NOT_EVALUATED"
    )


@pytest.fixture
def lay_bundle(bundle):
    """Synthetic inputs: holding 600 t, lay tension 800 t, another method 900 t.

    Hand calculation for a 700 t request: 600 < 700 <= 800. The 900 t rating
    has a different method and cannot satisfy an s-lay query. These are query
    fixtures, not sourced specifications; source metadata supplies structure.
    """
    row = next(row for row in bundle["vessels"] if row["pipelay"])
    template = copy.deepcopy(row["pipelay"][0])
    for vessel in bundle["vessels"]:
        vessel["pipelay"] = []
    template.update(
        method="s-lay",
        tension_t=600,
        rating_basis="holding (synthetic)",
        value_quote="600 t holding (synthetic test input)",
        locator="Synthetic comparison fixture; see lay_bundle docstring",
    )
    row["pipelay"] = [
        template,
        {
            **template,
            "tension_t": 800,
            "rating_basis": "lay tension (synthetic)",
            "value_quote": "800 t lay tension (synthetic test input)",
        },
        {
            **template,
            "method": "j-lay",
            "tension_t": 900,
            "value_quote": "900 t holding (synthetic test input)",
        },
    ]
    return bundle


def test_pipelay_query_does_not_substitute_another_tension_basis(lay_bundle):
    """Hand calculation: holding 600 < demand 700; lay tension 800 >= 700."""
    assert (
        ce.find_pipelay(
            "s-lay", 700, rating_basis="holding (synthetic)", bundle=lay_bundle
        )
        == []
    )
    result = ce.find_pipelay(
        "s-lay", 700, rating_basis="lay tension (synthetic)", bundle=lay_bundle
    )
    assert len(result) == 1
    assert result[0]["matched_capability"]["tension_t"] == 800


def test_pipelay_basis_filter_searches_beyond_the_first_matching_capacity(lay_bundle):
    """Hand calculation: both 600 and 800 >= 500, only the latter has lay basis."""
    result = ce.find_pipelay(
        "s-lay", 500, rating_basis="lay tension (synthetic)", bundle=lay_bundle
    )
    assert len(result) == 1
    assert result[0]["matched_capability"]["rating_basis"] == "lay tension (synthetic)"
    assert result[0]["matched_capability"]["value_quote"]


def test_pipelay_basis_filter_preserves_the_inclusive_threshold(lay_bundle):
    """Hand calculation: holding 600 >= demand 600, equality qualifies."""
    assert ce.find_pipelay(
        "s-lay", 600, rating_basis="holding (synthetic)", bundle=lay_bundle
    )


def test_pipelay_basis_is_an_exact_label_without_inferred_equivalences(lay_bundle):
    assert (
        ce.find_pipelay("s-lay", 500, rating_basis="holding", bundle=lay_bundle) == []
    )
    assert (
        ce.find_pipelay(
            "s-lay", 500, rating_basis="HOLDING (SYNTHETIC)", bundle=lay_bundle
        )
        == []
    )


def test_pipelay_unqualified_lookup_preserves_existing_behaviour(lay_bundle):
    """Hand calculation: unqualified s-lay demand 700 is met by the 800 t row."""
    expected = next(row for row in lay_bundle["vessels"] if row["pipelay"])
    result = ce.find_pipelay("s-lay", 700, bundle=lay_bundle)
    assert len(result) == 1
    assert result[0]["vessel_name"] == expected["vessel_name"]
    assert result[0]["matched_capability"]["rating_basis"] == "lay tension (synthetic)"


@pytest.mark.parametrize("value", ["", " ", True, 0, []])
def test_pipelay_basis_filter_rejects_invalid_labels(lay_bundle, value):
    with pytest.raises(ValueError, match="basis"):
        ce.find_pipelay("s-lay", 500, rating_basis=value, bundle=lay_bundle)
