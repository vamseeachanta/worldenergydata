"""Offline transport tests; synthetic pages independently define expected rows."""

from unittest.mock import Mock

import pytest

from worldenergydata.ukcs.metadata_client import NSTAFieldMetadataClient


def page(rows, more=False):
    response = Mock()
    response.json.return_value = {
        "features": [{"attributes": row} for row in rows],
        "exceededTransferLimit": more,
    }
    return response


def test_short_page_advances_by_received_rows_and_escapes_names():
    """Hand count: one field row, then one + one well rows; offsets 0, 1.

    Requested size is deliberately larger than the first returned well page.
    Median(100, 140) = 120 m; no row may be skipped by adding requested size.
    """
    session = Mock()
    session.get.side_effect = [
        page([{"OBJECTID": 1, "FIELDNAME": "EXAMPLE'S", "CURR_OPER": "Operator"}]),
        page([{"OBJECTID": 11, "TARGETFLD": "EXAMPLE'S", "WATDEP_M": 100}], True),
        page([{"OBJECTID": 12, "TARGETFLD": "EXAMPLE'S", "WATDEP_M": 140}]),
    ]
    meta = NSTAFieldMetadataClient(session=session).load_field_metadata("Example's")
    assert meta["operator"] == "Operator"
    assert meta["water_depth_m"] == 120
    calls = session.get.call_args_list
    assert calls[0].kwargs["params"]["where"] == "UPPER(FIELDNAME) = 'EXAMPLE''S'"
    assert calls[1].kwargs["params"]["where"] == "UPPER(TARGETFLD) = 'EXAMPLE''S'"
    assert [c.kwargs["params"]["resultOffset"] for c in calls] == [0, 0, 1]
    assert all(c.kwargs["params"]["orderByFields"] == "OBJECTID ASC" for c in calls)
    assert meta["retrieved_at"].endswith("+00:00")


@pytest.mark.parametrize(
    "payload",
    [
        {"error": {"code": 400}},
        {},
        {"features": [{"attributes": None}]},
        {"features": [], "exceededTransferLimit": True},
        {"features": [{"attributes": {"FIELDNAME": "EXAMPLE"}}]},
    ],
)
def test_error_or_incomplete_payload_fails_closed(payload):
    session = Mock()
    session.get.return_value.json.return_value = payload
    with pytest.raises(ValueError, match="NSTA"):
        NSTAFieldMetadataClient(session=session).load_field_metadata("EXAMPLE")


def test_repeated_page_is_rejected():
    session = Mock()
    repeated = page([{"OBJECTID": 1, "FIELDNAME": "EXAMPLE"}], True)
    session.get.side_effect = [repeated, repeated]
    with pytest.raises(ValueError, match="repeated"):
        NSTAFieldMetadataClient(session=session).load_field_metadata("EXAMPLE")


def test_http_failure_propagates():
    session = Mock()
    session.get.return_value.raise_for_status.side_effect = RuntimeError("HTTP error")
    with pytest.raises(RuntimeError, match="HTTP error"):
        NSTAFieldMetadataClient(session=session).load_field_metadata("EXAMPLE")


def test_fields_only_does_not_fetch_wells():
    session = Mock()
    session.get.return_value = page([])
    meta = NSTAFieldMetadataClient(session=session).load_field_metadata(
        "EXAMPLE", include_wells=False
    )
    assert session.get.call_count == 1
    assert meta["water_depth_m"] is None


def test_observed_field_depth_does_not_require_well_requests():
    """Synthetic field depth 80 m is copied directly, without aggregation."""
    session = Mock()
    session.get.return_value = page(
        [{"OBJECTID": 1, "FIELDNAME": "EXAMPLE", "DEPTH_M": "80"}]
    )
    meta = NSTAFieldMetadataClient(session=session).load_field_metadata("EXAMPLE")
    assert meta["water_depth_m"] == 80
    session.get.assert_called_once()


@pytest.mark.parametrize("name", [None, "", "  "])
def test_invalid_name_never_makes_a_request(name):
    session = Mock()
    with pytest.raises(ValueError, match="field_name"):
        NSTAFieldMetadataClient(session=session).load_field_metadata(name)
    session.get.assert_not_called()
