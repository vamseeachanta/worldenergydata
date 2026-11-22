"""Lease-panel identities must round-trip through a temporary registry.

Fixture source: all labels, lease/block numbers, water depths and the ingest
issue number below are invented synthetic test inputs, not acquisition facts.
Expected identities and row counts follow the explicitly declared fixture lists.
"""

from __future__ import annotations

import pytest
import yaml

from worldenergydata.common.fields_registry import load_fields
from worldenergydata.field_development.landman import build_landman

# Synthetic enrichment is deliberately absent for the second alpha lease.
ENRICHMENT = {
    "G00011": {
        "lease_name": "Synthetic alpha lease",
        "water_depth_ft": 1200,
        "dev_system": "synthetic_alpha_system",
    },
    "G00021": {
        "lease_name": "Synthetic beta lease",
        "water_depth_ft": 2400,
        "dev_system": "synthetic_beta_system",
    },
}
SYNTHETIC_INGEST_ISSUE = 1


@pytest.fixture(
    params=[
        pytest.param(("G00011", "G00012", "G00021"), id="canonical"),
        pytest.param(("G 00011", "G 00012", "G 00021"), id="spaced"),
        pytest.param(("OCS-G 00011", "OCS-G 00012", "OCS-G 00021"), id="prefixed"),
        pytest.param(("g00011", "g00012", "g00021"), id="lowercase"),
    ]
)
def registry_case(tmp_path, request):
    alpha_enriched, alpha_unenriched, beta_enriched = request.param
    declared_leases = {
        "alpha": [alpha_enriched, alpha_unenriched],
        "beta": [beta_enriched],
    }
    fields = [
        {
            "canonical_id": "alpha",
            "display_name": "Synthetic alpha",
            "bsee": {
                "leases": declared_leases["alpha"],
                "area_blocks": ["AA101", "AA102", "AA103"],
            },
            "bsee_block_note": "Unpaired synthetic field-level blocks",
        },
        {
            "canonical_id": "beta",
            "display_name": "Synthetic beta",
            "bsee": {
                "leases": declared_leases["beta"],
                "area_blocks": ["BB201"],
            },
        },
    ]
    path = tmp_path / "fields.yml"
    path.write_text(yaml.safe_dump({"fields": fields}), encoding="utf-8")
    return load_fields(path), declared_leases


def _panel_for(registry, canonical_id):
    field = registry.by_id(canonical_id)
    assert field is not None
    return build_landman(
        {},
        list(field.leases),
        list(field.area_blocks),
        ENRICHMENT,
        SYNTHETIC_INGEST_ISSUE,
        field.bsee_block_note,
    )


def test_panel_leases_roundtrip_to_declared_field(registry_case):
    registry, declared_leases = registry_case
    # Expected ids are fixture declarations, independent of builder output.
    for expected_id in ("alpha", "beta"):
        panel = _panel_for(registry, expected_id)
        assert [row["lease_num"] for row in panel["leases"]] == declared_leases[
            expected_id
        ]
        assert panel["n_leases"] == len(declared_leases[expected_id])
        for row in panel["leases"]:
            assert registry.by_lease(row["lease_num"]) == expected_id

    # The canonical enrichment keys join even when panel leases use variants.
    for expected_id, expected_enrichment in (
        ("alpha", ENRICHMENT["G00011"]),
        ("beta", ENRICHMENT["G00021"]),
    ):
        enriched, *_ = _panel_for(registry, expected_id)["leases"]
        for attr, expected_value in expected_enrichment.items():
            assert enriched[attr] == expected_value


def test_unknown_lease_is_unresolved(registry_case):
    registry, _ = registry_case
    # Synthetic identifiers deliberately absent from both declared fields.
    unknown_leases = ["G00999", "G 00999", "OCS-G 00999", "g00999"]
    panel = build_landman({}, unknown_leases, [], {}, SYNTHETIC_INGEST_ISSUE)
    assert [row["lease_num"] for row in panel["leases"]] == unknown_leases
    for row in panel["leases"]:
        assert registry.by_lease(row["lease_num"]) is None


def test_unenriched_lease_retains_identity(registry_case):
    registry, declared_leases = registry_case
    _, unenriched_lease = declared_leases["alpha"]
    panel = _panel_for(registry, "alpha")
    unmatched = [row for row in panel["leases"] if row["lease_num"] == unenriched_lease]
    assert unmatched == [
        {
            "lease_num": unenriched_lease,
            "lease_name": None,
            "water_depth_ft": None,
            "dev_system": None,
        }
    ]
    assert registry.by_lease(unenriched_lease) == "alpha"
    # Deferred status is represented by the panel's pending list, not a fact.
    for attr in (
        "status",
        "effective_date",
        "expiration_date",
        "lease_type",
        "per_lease_working_interest",
        "operator_of_record_history",
    ):
        assert attr in panel["pending"]
        assert all(attr not in row for row in panel["leases"])


def test_unpaired_blocks_remain_at_field_level(registry_case):
    registry, _ = registry_case
    panel = _panel_for(registry, "alpha")
    assert panel["blocks"] == ["AA101", "AA102", "AA103"]
    assert panel["block_note"] == "Unpaired synthetic field-level blocks"
    assert "per_lease_block" in panel["pending"]
    for row in panel["leases"]:
        assert "block" not in row
        assert "blocks" not in row
        assert "area_blocks" not in row
        assert "per_lease_block" not in row
