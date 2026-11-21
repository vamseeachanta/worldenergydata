"""Synthetic, offline checks for dated borehole and lease reconciliation."""

from copy import deepcopy

import pytest


def inputs():
    rows = [
        dict(
            api12=f"00000000000{i}",
            bottom_lease=lease,
            field_id=field,
            status_code="NEW",
            surface_lease="G00001",
        )
        for i, lease, field in [
            (1, "OCS-G 00001", "field_a"),
            (2, "G00002", "field_a"),
            (3, "G00003", "field_a"),
            (4, "", "field_a"),
            (5, "G00001", None),
            (6, "G00004", "field_a"),
        ]
    ]
    leases = [dict(lease_num=f"G0000{i}") for i in (1, 3, 4)]
    registry = [
        dict(lease_num="G00001", field_id="field_a", reason=None),
        dict(lease_num="G00003", field_id="field_b", reason=None),
    ]
    provenance = dict(
        source_id="synthetic-boreholes",
        source_sha256="a" * 64,
        source_retrieved_at_utc="2026-10-01T00:00:00+00:00",
        registry_sha256="c" * 64,
    )
    other = dict(
        provenance,
        source_id="synthetic-leases",
        source_sha256="b" * 64,
        source_retrieved_at_utc="2026-10-02T00:00:00+00:00",
    )
    return rows, leases, registry, provenance, other


def run(args):
    from worldenergydata.bsee.borehole_lease_reconciliation import (
        reconcile_borehole_leases,
    )

    rows, leases, registry, boreholes, lease_source = args
    return reconcile_borehole_leases(
        rows,
        leases,
        registry,
        borehole_provenance=boreholes,
        lease_provenance=lease_source,
    )


def test_literal_partition_preservation_and_deterministic_order():
    args = inputs()
    args[0][0]["reason"] = "original_attribution_reason"
    original = deepcopy(args)
    result = run(args)
    assert result["summary"] == {
        "input_boreholes": 6,
        "availability": "records_present",
        "disposition_counts": {
            "agreement": 1,
            "lease_absent_from_snapshot": 1,
            "field_assignment_conflict": 1,
            "missing_identity": 3,
            "registry_basis_unverified": 0,
        },
    }
    records = result["records"]
    assert [r["reason"] for r in records] == [
        "bottom_lease_and_field_agree",
        "lease_absent_from_snapshot",
        "field_assignment_conflict",
        "missing_bottom_lease",
        "missing_borehole_field_id",
        "missing_registry_mapping",
    ]
    assert records[0]["bottom_lease"] == "OCS-G 00001"
    assert records[0]["normalized_bottom_lease"] == "G00001"
    assert records[0]["status_code"] == "NEW"
    assert records[0]["attribution_reason"] == "original_attribution_reason"
    assert records[2]["field_id"] == "field_a"
    assert records[2]["lease_field_id"] == "field_b"
    assert result["registry_basis"] == "matching"
    assert result["different_retrieval_times"] is True
    assert result["provenance"] == {
        "verification": "caller_supplied_not_authenticated",
        "boreholes": args[3],
        "leases": args[4],
    }
    assert sum(result["summary"]["disposition_counts"].values()) == len(records)
    assert args == original
    for collection in args[:3]:
        collection.reverse()
    assert run(args) == result
    result["provenance"]["boreholes"]["source_id"] = "changed"
    result["records"][0]["status_code"] = "changed"
    assert args[3] == original[3]
    assert args[0][-1] == original[0][0]


@pytest.mark.parametrize("digest,basis", [(None, "missing"), ("d" * 64, "different")])
def test_recorded_registry_basis_never_replaced(digest, basis):
    args = inputs()
    args[4]["registry_sha256"] = digest
    result = run(args)
    assert result["registry_basis"] == basis
    assert result["records"][0]["disposition"] == "registry_basis_unverified"
    assert result["records"][0]["reason"] == f"{basis}_registry_basis"
    assert result["records"][2]["disposition"] == "field_assignment_conflict"


def test_missing_digest_key_and_equivalent_timestamp_instants():
    args = inputs()
    del args[3]["registry_sha256"]
    args[4]["source_retrieved_at_utc"] = "2026-09-30T17:00:00-07:00"
    result = run(args)
    assert result["registry_basis"] == "missing"
    assert result["different_retrieval_times"] is False


def test_empty_input_is_explicit():
    args = inputs()
    args[0].clear()
    result = run(args)
    assert result["records"] == []
    assert result["summary"]["availability"] == "empty_input"
    assert result["summary"]["input_boreholes"] == 0
    assert set(result["summary"]["disposition_counts"].values()) == {0}


@pytest.mark.parametrize(
    "index,key,value,message",
    [
        (0, "api12", "000000000001", "Duplicate API12"),
        (1, "lease_num", "OCS-G 00001", "Duplicate normalized lease"),
        (2, "lease_num", "OCS-G 00001", "Duplicate normalized registry lease"),
    ],
)
def test_duplicates_rejected_before_output(index, key, value, message):
    args = inputs()
    args[index].append(dict(args[index][0], **{key: value}))
    with pytest.raises(ValueError, match=message):
        run(args)


@pytest.mark.parametrize("value", [None, "", "1234567890", 123456789012])
def test_invalid_api12_rejected(value):
    args = inputs()
    args[0][0]["api12"] = value
    with pytest.raises(ValueError, match="API12"):
        run(args)


@pytest.mark.parametrize(
    "key,value",
    [
        ("source_id", ""),
        ("source_sha256", "bad"),
        ("source_retrieved_at_utc", "2026-10-01"),
        ("registry_sha256", "bad"),
    ],
)
def test_invalid_provenance_rejected(key, value):
    args = inputs()
    args[4][key] = value
    with pytest.raises(ValueError, match=key):
        run(args)


@pytest.mark.parametrize(
    "mapping",
    [
        dict(field_id=None, reason="unresolved"),
        dict(field_id="field_a", reason="unresolved"),
    ],
)
def test_unresolved_registry_entry_is_not_agreement(mapping):
    args = inputs()
    args[2][0].update(mapping)
    result = run(args)
    assert result["records"][0]["disposition"] == "missing_identity"
    assert result["records"][0]["reason"] == "unresolved_registry_mapping"


@pytest.mark.parametrize("bottom", [None, "", "   "])
def test_no_surface_fallback_and_missing_status_preserved(bottom):
    args = inputs()
    args[0][0].update(bottom_lease=bottom, status_code=None)
    record = run(args)["records"][0]
    assert record["reason"] == "missing_bottom_lease"
    assert record["status_code"] is None
    assert record["surface_lease"] == "G00001"


@pytest.mark.parametrize("index", [0, 1, 2])
def test_nonstring_lease_rejected(index):
    args = inputs()
    args[index][0]["bottom_lease" if index == 0 else "lease_num"] = 1
    with pytest.raises(ValueError, match="Lease identifiers"):
        run(args)


@pytest.mark.parametrize("index", [1, 2])
def test_missing_lease_snapshot_key_rejected(index):
    args = inputs()
    args[index][0].pop("lease_num")
    with pytest.raises(ValueError, match="Missing normalized"):
        run(args)
