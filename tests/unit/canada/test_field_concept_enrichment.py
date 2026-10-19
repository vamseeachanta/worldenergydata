"""Synthetic enrichment arithmetic plus compatibility with existing defaults."""

import copy

import pytest

from worldenergydata.canada.development_wells import DevelopmentWell
from worldenergydata.canada.field_concept import (
    CANADA_WATER_DEPTH_M,
    build_canada_field_concept,
    canada_field_to_concept,
    enrich_canada_field_metadata,
)

BUILDERS = (canada_field_to_concept, build_canada_field_concept)


def records(field_name="synthetic-field"):
    """Synthetic depths 10 and 30 m -> (10+30)/2 = 20 m; null is excluded.

    Median definition: Python 3.11 Library Reference (retrieved 2026), statistics.median,
    https://docs.python.org/3.11/library/statistics.html#statistics.median.
    """
    return [
        DevelopmentWell(
            uwi=f"synthetic-{index}",
            field_name=field_name,
            water_depth_m=depth,
            depth_unit="m",
            depth_datum="synthetic-datum",
            source="synthetic:offline",
        )
        for index, depth in enumerate((10.0, 30.0, None))
    ]


@pytest.mark.parametrize("build", BUILDERS)
def test_opt_in_uses_generator_and_preserves_input(build):
    meta = {"field": "synthetic-field", "source": "synthetic:metadata"}
    before = copy.deepcopy(meta)
    concept = build(meta, wells=iter(records()))
    assert meta == before
    assert concept.water_depth_m == 20.0
    assert concept.region == "canada"
    assert concept.name == "synthetic-field"
    assert "water_depth_m=measured_median" in concept.data_source
    assert "development_wells_sha256=" in concept.data_source


@pytest.mark.parametrize("build", BUILDERS)
def test_omitted_wells_preserve_legacy_outputs(build):
    for name, depth in CANADA_WATER_DEPTH_M.items():
        concept = build({"field_name": name})
        assert concept.water_depth_m == depth
        assert concept.data_source == "cnloer"
    assert build({"field_name": "synthetic-field"}).water_depth_m is None
    assert (
        build({"field_name": "synthetic-field", "water_depth_m": 7.0}).water_depth_m
        == 7.0
    )


@pytest.mark.parametrize("build", BUILDERS)
def test_measured_median_overrides_provided_depth(build):
    """Synthetic linked median is 20 m, overriding the supplied 7 m metadata."""
    assert (
        build(
            {"field_name": "synthetic-field", "water_depth_m": 7.0}, wells=records()
        ).water_depth_m
        == 20.0
    )


@pytest.mark.parametrize("build", BUILDERS)
def test_no_usable_wells_preserve_existing_defaults(build):
    for name, depth in CANADA_WATER_DEPTH_M.items():
        result = build({"field_name": name}, wells=[])
        assert result.water_depth_m == depth
        assert "water_depth_m=default" in result.data_source


@pytest.mark.parametrize("build", BUILDERS)
def test_null_wells_preserve_provided_depth_without_claiming_measurement(build):
    result = build(
        {"field_name": "synthetic-field", "water_depth_m": 7.0},
        wells=[records()[-1]],
    )
    assert result.water_depth_m == 7.0
    assert "water_depth_m=provided" in result.data_source


@pytest.mark.parametrize("build", BUILDERS)
def test_missing_remains_missing(build):
    result = build({"field_name": "synthetic-field"}, wells=[])
    assert result.water_depth_m is None
    assert "water_depth_m=missing" in result.data_source


def test_metadata_sidecar_is_reproducible_and_complete():
    meta = {"field_name": "synthetic-field"}
    enriched = enrich_canada_field_metadata(meta, records())
    assert meta == {"field_name": "synthetic-field"}
    evidence = enriched["water_depth_provenance"]
    assert evidence["origin"] == "measured_median"
    assert evidence["depth_datum"] == "synthetic-datum"
    assert evidence["contributing_uwis"] == ["synthetic-0", "synthetic-1"]
    assert evidence["sources"] == ["synthetic:offline"]
    assert evidence["linked_well_count"] == 3
    assert evidence["manifest"]["record_count"] == 3
    assert evidence["measurement_status"] == "NOT_EVALUATED"
    assert enriched == enrich_canada_field_metadata(meta, reversed(records()))


@pytest.mark.parametrize("build", BUILDERS)
def test_no_implicit_field_linkage(build):
    result = build({"field_name": "another-synthetic-field"}, wells=records())
    assert result.water_depth_m is None


def test_default_sidecar_is_not_measured():
    name, expected = next(iter(CANADA_WATER_DEPTH_M.items()))
    result = enrich_canada_field_metadata({"field_name": name}, [])
    assert result["water_depth_m"] == expected
    evidence = result["water_depth_provenance"]
    assert evidence["origin"] == "default"
    assert evidence["measurement_status"] == "NOT_EVALUATED"
    assert evidence["contributing_uwis"] == []


@pytest.mark.parametrize("build", BUILDERS)
def test_concept_exposes_unverified_measurement_status(build):
    result = build({"field_name": "synthetic-field"}, wells=records())
    assert "measurement_status=NOT_EVALUATED" in result.data_source


def test_enrichment_performs_no_network_or_file_io(monkeypatch):
    import builtins
    import io
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError("offline enrichment attempted external access")

    inputs = records()
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", refuse)
        patch.setattr(io, "open", refuse)
        patch.setattr(socket.socket, "connect", refuse)
        patch.setattr(socket, "create_connection", refuse)
        result = build_canada_field_concept(
            {"field_name": "synthetic-field"}, wells=inputs
        )
    assert result.water_depth_m == 20.0
