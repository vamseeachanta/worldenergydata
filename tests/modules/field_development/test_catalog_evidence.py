"""Exact-ID projections of the issue 1144 evidence contract, without inference."""

import copy

import catalog_test_support as support
import pytest

api = support.api
inputs = support.inputs


def field(bundle):
    return next(e for e in bundle["entities"] if e["entity_type"] == "field")


def test_entity_projection_retains_source_and_scoped_observation(api, inputs):
    """One selected entity has its one explicit observation and one cited source.

    Expected values are copied from the input objects, without unit conversion.
    No name comparison or depth allocation is part of the method (issue 1144).
    """
    bundle = api.build_integration(*inputs)
    entity = field(bundle)
    reader = api.CatalogEvidence(bundle)
    view = reader.entity(entity["entity_id"])
    assert view["entity"] == entity
    assert [r["record_id"] for r in view["records"]] == [entity["evidence_record_id"]]
    expected = next(
        r
        for r in bundle["evidence"]["field_observations"]
        if r["entity_id"] == entity["origin_entity_id"]
    )
    assert view["records"][0]["observation"] == expected
    assert view["sources"] == bundle["evidence"]["sources"]
    assert view["legacy_groups"] == []  # Pending names cannot establish identity.
    assert (
        view["legacy_catalog_sha256"]
        == bundle["manifest"]["input_hashes"]["legacy_catalog"]
    )


def test_cost_candidate_does_not_allocate_to_same_named_field(api, inputs):
    """The fixture has one development cost; the field receives zero such costs.

    Hand classification uses scope_type=project in the input: it describes the
    development, whereas the separate field observation describes a field.
    """
    bundle = api.build_integration(*inputs)
    link = next(
        r for r in bundle["links"]["records"] if r["table"] == "cost_observations"
    )
    reader = api.CatalogEvidence(bundle)
    development = reader.entity(link["entity_id"])
    cost = next(r for r in development["records"] if r["table"] == "cost_observations")
    assert development["entity"]["entity_type"] == "development"
    assert cost["link_status"] == "candidate"
    assert cost["observation"] == bundle["evidence"]["cost_observations"][0]
    same_name_field = next(
        e
        for e in bundle["entities"]
        if e["entity_type"] == "field"
        and e["primary_name"] == development["entity"]["primary_name"]
    )
    assert not any(
        r["table"] == "cost_observations"
        for r in reader.entity(same_name_field["entity_id"])["records"]
    )


def test_inherited_record_keeps_parent_reference_without_new_cost(api, inputs):
    """One inherited input links one parent; it creates zero independent costs."""
    bundle = api.build_integration(*inputs)
    link = next(
        r for r in bundle["links"]["records"] if r["table"] == "inherited_cost_records"
    )
    view = api.CatalogEvidence(bundle).record(link["record_id"])
    assert view["link_status"] == "parent_reference"
    assert view["observation"] == bundle["evidence"]["inherited_cost_records"][0]
    assert view["parent_references"] == bundle["links"]["parent_references"]
    assert view["entity_id"] is None


def test_projection_is_detached_and_unknown_ids_fail(api, inputs):
    bundle = api.build_integration(*inputs)
    before = copy.deepcopy(bundle)
    reader = api.CatalogEvidence(bundle)
    view = reader.entity(field(bundle)["entity_id"])
    view["entity"]["primary_name"] = "changed"
    view["records"][0]["observation"].clear()
    view["sources"].clear()
    assert bundle == before
    assert reader.entity(field(bundle)["entity_id"])["entity"] == field(bundle)
    with pytest.raises(KeyError):
        reader.entity("unknown")
    with pytest.raises(KeyError):
        reader.record("unknown")


def test_duplicate_records_keep_multiplicity_and_original_date_bound(api, inputs):
    """Two identical milestone inputs give one record with multiplicity two.

    Independent hand count: original one + one identical copy = two; a bound
    remains the input precision rather than becoming an exact event date.
    """
    bundle = api.build_integration(*inputs)
    rows = bundle["evidence"]["milestone_observations"]
    rows.append(copy.deepcopy(rows[0]))
    bundle["links"] = api.build_links(
        bundle["manifest"]["dataset_id"],
        bundle["evidence"],
        bundle["entities"],
        inputs[2],
    )
    link = next(r for r in bundle["links"]["records"] if r["multiplicity"] > 1)
    view = api.CatalogEvidence(bundle).record(link["record_id"])
    assert view["multiplicity"] == 2
    assert view["observation"]["precision"] == "upper_bound_day"
    assert view["observation"]["event_date"] == rows[0]["event_date"]


def test_public_readback_excludes_deferred_evidence(api, inputs, tmp_path):
    draft = api.build_integration(*inputs)
    matrix = support.reviewed_matrix(draft)
    next(r for r in matrix if r["table"] == "cost_observations")[
        "decision"
    ] = "prohibited"
    exported = api.public_export(api.build_integration(*inputs, eligibility=matrix))
    api.write_bundle(exported, tmp_path / "public")
    reader = api.CatalogEvidence(api.read_bundle(tmp_path / "public", public_only=True))
    denied = next(
        r for r in draft["links"]["records"] if r["table"] == "cost_observations"
    )
    with pytest.raises(KeyError):
        reader.record(denied["record_id"])


def test_accepted_identity_returns_all_legacy_groups(api, inputs):
    """The fixture's duplicate legacy rows form one group of multiplicity two.

    A signed synthetic decision permits this group only; unrelated legacy rows
    sharing FIELD_ID remain outside the projection (issue 1144 corrections).
    """
    draft = api.build_integration(*inputs)
    candidate = next(r for r in draft["crosswalk"] if r["match_status"] == "pending")
    # Use the fixture's existing synthetic approval constructor's role value.
    reviewer = support.reviewed_matrix(draft)[0]["reviewer"]
    decision = dict(
        candidate,
        match_status="accepted",
        approved_by=reviewer,
        approval_ref="synthetic identity decision",
    )
    bundle = api.build_integration(*inputs, decisions=[decision])
    view = api.CatalogEvidence(bundle).entity(candidate["entity_id"])
    assert len(view["legacy_groups"]) == 1
    assert view["legacy_groups"][0]["multiplicity"] == 2
    assert view["crosswalk"][0]["match_status"] == "accepted"
