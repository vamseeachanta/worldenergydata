"""Synthetic contract tests; no data feed or financial calculation is required."""

from copy import deepcopy

import pytest

from worldenergydata.common.fields_registry import load_fields
from worldenergydata.field_development.landman import PENDING_ATTRS, build_landman


def lens_availability(*args, **kwargs):
    from worldenergydata.field_development.lens_availability import lens_availability

    return lens_availability(*args, **kwargs)


@pytest.fixture
def registry(tmp_path):
    path = tmp_path / "fields.yml"
    path.write_text(
        "fields:\n"
        "  - canonical_id: offshore_sample\n"
        "    display_name: Offshore sample\n"
        "    region: offshore\n"
        "  - canonical_id: onshore_sample\n"
        "    display_name: Onshore sample\n"
        "    region: onshore\n",
        encoding="utf-8",
    )
    return load_fields(path)


def payload():
    return {
        "id": "offshore_sample",
        "performance": {
            "economics_status": "surfaced",
            "economics_basis": "life_to_date_pretax_npv_at_10pct",
            "npv_mm": -20.0,
            "breakeven_wti": 50.0,
            "sens_mm_per_dollar": 2.0,
        },
        "risk": {
            "hpht": {
                "severity": "within",
                "basis": "reservoir",
                "pressure_psi": 10000,
                "equip_rating_psi": 20000,
                "exceedance_pct": -50,
            },
            "decommissioning_status": "withheld_pending_redistribution_review",
            "decommissioning": {"cost_musd": 80.0},
        },
        "landman": build_landman({}, ["G00001"], ["AA001"], {}, 950),
    }


def project(registry, value):
    return lens_availability("offshore_sample", value, registry=registry)


def test_identity_fails_closed(registry):
    with pytest.raises(ValueError, match="canonical"):
        lens_availability("unknown", payload(), registry=registry)
    for bad in ({}, {"id": "onshore_sample"}, {"id": "Offshore sample"}):
        with pytest.raises(ValueError, match="identity"):
            project(registry, bad)


@pytest.mark.parametrize("field_id", ["offshore_sample", "onshore_sample"])
def test_absent_payload_preserves_registry_identity_and_region(registry, field_id):
    result = lens_availability(field_id, None, registry=registry)
    assert list(result) == ["economics", "underwriting", "landman"]
    for record in result.values():
        assert record["canonical_id"] == field_id
        assert record["region"] == registry.by_id(field_id).region
        assert record["status"] == "unavailable"
        assert record["reason"] == "absent_payload"
        assert record["missing_dimensions"]
        assert record["source_contract"]


def test_independent_lenses_are_immutable_and_copy_no_results(registry):
    value = payload()
    before = deepcopy(value)
    result = project(registry, value)
    assert [r["status"] for r in result.values()] == ["available", "partial", "partial"]
    parts = result["underwriting"]["subpanels"]
    assert parts["hpht"]["status"] == "available"
    assert parts["decommissioning"]["status"] == "withheld"
    assert result["landman"]["missing_dimensions"] == PENDING_ATTRS
    assert "npv_mm" not in repr(result) and "cost_musd" not in repr(result)
    assert value == before and result == project(registry, value)
    result["landman"]["missing_dimensions"].clear()
    assert value == before and PENDING_ATTRS


@pytest.mark.parametrize("status", ["withheld", "early_life", "future", None])
def test_economics_status_precedes_populated_stale_numbers(registry, status):
    value = payload()
    value["performance"]["economics_status"] = status
    record = project(registry, value)["economics"]
    assert record["status"] == ("withheld" if status == "withheld" else "unavailable")
    assert record["reason"] == "source_status"


@pytest.mark.parametrize(
    "dimension", ["economics_basis", "npv_mm", "breakeven_wti", "sens_mm_per_dollar"]
)
@pytest.mark.parametrize("bad", [None, "unknown", True, float("nan"), float("inf")])
def test_incomplete_economics_is_unavailable(registry, dimension, bad):
    value = payload()
    value["performance"][dimension] = bad
    record = project(registry, value)["economics"]
    assert record["status"] == "unavailable"
    assert dimension in record["missing_dimensions"]


@pytest.mark.parametrize("npv", [-20.0, 0.0, 20.0])
def test_finite_signed_economics_remains_available(registry, npv):
    value = payload()
    value["performance"]["npv_mm"] = npv
    assert project(registry, value)["economics"]["status"] == "available"


@pytest.mark.parametrize("badge", [None, {}, {"severity": "future"}])
def test_absent_or_unknown_hpht_is_never_low_risk(registry, badge):
    value = payload()
    value["risk"]["hpht"] = badge
    record = project(registry, value)["underwriting"]
    assert record["subpanels"]["hpht"]["status"] == "unavailable"
    assert record["subpanels"]["decommissioning"]["status"] == "withheld"


def test_class_only_hpht_retains_partial_state(registry):
    value = payload()
    value["risk"]["hpht"] = {
        "severity": "class-only",
        "basis": "subsea_system",
        "class": "HPHT",
    }
    assert (
        project(registry, value)["underwriting"]["subpanels"]["hpht"]["status"]
        == "partial"
    )


@pytest.mark.parametrize("status", ["future", None])
def test_unknown_decommissioning_status_is_unavailable(registry, status):
    value = payload()
    value["risk"]["decommissioning_status"] = status
    assert (
        project(registry, value)["underwriting"]["subpanels"]["decommissioning"][
            "status"
        ]
        == "unavailable"
    )


def test_legacy_decommissioning_without_status_retains_source_contract(registry):
    value = payload()
    value["risk"].pop("decommissioning_status")
    value["risk"]["decommissioning"].update(
        basis="facility removal (not well P&A)", confidence="low"
    )
    assert project(registry, value)["underwriting"]["status"] == "available"


@pytest.mark.parametrize("leases", [[], [{}], [{"lease_num": None}]])
def test_no_lease_identifiers_is_unavailable(registry, leases):
    value = payload()
    value["landman"]["leases"] = leases
    assert project(registry, value)["landman"]["status"] == "unavailable"


def test_whole_payload_withholding_precedes_stale_panels(registry):
    value = payload()
    value["status"] = "withheld"
    assert all(r["status"] == "withheld" for r in project(registry, value).values())


@pytest.mark.parametrize("panel", [None, {}, []])
def test_empty_or_malformed_panels_are_explicitly_unavailable(registry, panel):
    value = {
        "id": "offshore_sample",
        "performance": panel,
        "risk": panel,
        "landman": panel,
    }
    records = project(registry, value)
    assert all(record["status"] == "unavailable" for record in records.values())
    assert all(
        record["reason"] and record["missing_dimensions"] for record in records.values()
    )


@pytest.mark.parametrize(
    "dimension", ["basis", "pressure_psi", "equip_rating_psi", "exceedance_pct"]
)
def test_incomplete_hpht_never_claims_comparable_evidence(registry, dimension):
    value = payload()
    value["risk"]["hpht"].pop(dimension)
    assert (
        project(registry, value)["underwriting"]["subpanels"]["hpht"]["status"]
        == "unavailable"
    )


@pytest.mark.parametrize("dimension", ["basis", "confidence", "cost_musd"])
def test_incomplete_legacy_decommissioning_is_unavailable(registry, dimension):
    value = payload()
    value["risk"].pop("decommissioning_status")
    value["risk"]["decommissioning"] = {
        "basis": "facility removal (not well P&A)",
        "confidence": "modeled",
        "cost_musd": 80.0,
    }
    value["risk"]["decommissioning"].pop(dimension)
    assert (
        project(registry, value)["underwriting"]["subpanels"]["decommissioning"][
            "status"
        ]
        == "unavailable"
    )
