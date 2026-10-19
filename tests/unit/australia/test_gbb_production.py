"""Synthetic AEMO schema tests; no publisher records or engineering inputs.

All numbers are invented parser tokens. Expected values are literal readings of
those tokens, not production estimates. There are no conversion coefficients,
acceptance tolerances or economic equations in this slice.
"""

import hashlib
from datetime import date
from decimal import Decimal

import pytest

from worldenergydata.australia.gbb_production import inspect_gbb_csv

# AEMO GasBBActualFlowStorageLast31.CSV header, observed 2026-10-19:
# https://nemweb.com.au/Reports/Current/GBB/GasBBActualFlowStorageLast31.CSV
HEADER = (
    "GasDate,FacilityName,FacilityId,FacilityType,Demand,Supply,TransferIn,"
    "TransferOut,HeldInStorage,CushionGasStorage,State,LocationName,LocationId,"
    "LastUpdated"
)
ROW = (
    "2026/01/31,Synthetic facility,101,PROD,0.000,12.345,0.000,0.000,,,"
    "SA,Synthetic location,201,2026/02/01 08:00:00"
)


def _raw(*rows):
    return (HEADER + "\r\n" + "\r\n".join(rows) + "\r\n").encode()


def _inspect(raw):
    # Test-only resource budgets; not engineering acceptance limits.
    return inspect_gbb_csv(raw, max_bytes=max(1, len(raw)), max_rows=10)


def test_values_are_preserved_without_unit_or_volume_inference():
    report = _inspect(_raw(ROW))
    record = report.records[0]
    assert record.gas_date == date(2026, 1, 31)
    assert record.facility_id == "101"
    assert record.location_id == "201"
    assert record.facility_name == "Synthetic facility"
    assert record.facility_type == "PROD"
    assert record.state == "SA"
    assert record.location_name == "Synthetic location"
    assert record.last_updated.isoformat() == "2026-02-01T08:00:00"
    assert record.supply == Decimal("12.345")
    assert record.demand == Decimal("0.000")
    assert record.held_in_storage is None
    assert record.cushion_gas_storage is None
    assert report.units is None
    assert report.date_range == (date(2026, 1, 31), date(2026, 1, 31))


def test_digest_covers_exact_source_bytes_and_readiness_is_explicit():
    raw = _raw(ROW)
    report = _inspect(raw)
    assert report.source_sha256 == hashlib.sha256(raw).hexdigest()
    assert report.source_size_bytes == len(raw)
    assert report.economics_status == "NOT_EVALUATED"
    assert {check.name for check in report.economics_checks} == {
        "source_units",
        "reuse_rights",
        "field_allocation",
        "gas_volume_conversion",
    }
    assert all(check.status == "NOT_EVALUATED" for check in report.economics_checks)
    assert all(check.reason for check in report.economics_checks)


def test_locations_are_not_collapsed_into_facility_production():
    other = ROW.replace(",201,", ",202,").replace("12.345", "7.000")
    report = _inspect(_raw(ROW, other))
    # Independent reading: two locations, two values; no sum is a field volume.
    assert [r.supply for r in report.records] == [Decimal("12.345"), Decimal("7.000")]


def test_dates_are_sorted_for_coverage_without_reordering_source_records():
    earlier = ROW.replace("2026/01/31", "2026/01/30")
    report = _inspect(_raw(ROW, earlier))
    assert report.date_range == (date(2026, 1, 30), date(2026, 1, 31))
    assert report.records[0].gas_date == date(2026, 1, 31)


def test_blank_supply_is_unknown_and_zero_supply_is_a_value():
    report = _inspect(_raw(ROW.replace("12.345", "")))
    assert report.records[0].supply is None
    report = _inspect(_raw(ROW.replace("12.345", "0.000")))
    assert report.records[0].supply == Decimal("0.000")


def test_negative_source_token_is_preserved_without_engineering_interpretation():
    assert _inspect(_raw(ROW.replace("12.345", "-1.250"))).records[0].supply == Decimal(
        "-1.250"
    )


def test_empty_report_is_distinct_from_missing_header():
    report = _inspect(_raw())
    assert report.records == ()
    assert report.date_range == (None, None)
    with pytest.raises(ValueError, match="header"):
        _inspect(b"")


def test_bom_and_reordered_columns_are_supported():
    columns = HEADER.split(",")
    values = ROW.split(",")
    raw = (
        "\ufeff" + ",".join(reversed(columns)) + "\n" + ",".join(reversed(values))
    ).encode()
    assert _inspect(raw).records[0].supply == Decimal("12.345")


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "oops"])
def test_invalid_amounts_fail_instead_of_becoming_zero(token):
    with pytest.raises(ValueError, match="Supply"):
        _inspect(_raw(ROW.replace("12.345", token)))


@pytest.mark.parametrize(
    "old,new",
    [
        ("2026/01/31", "2026/02/30"),
        ("2026/01/31", "2026-01-31"),
        ("2026/02/01 08:00:00", "bad timestamp"),
        (",101,", ",abc,"),
        (",201,", ",,"),
        ("Synthetic facility", ""),
        (",PROD,", ",,"),
    ],
)
def test_invalid_identity_or_date_fails(old, new):
    with pytest.raises(ValueError):
        _inspect(_raw(ROW.replace(old, new)))


@pytest.mark.parametrize(
    "raw",
    [
        _raw(ROW).replace(b"Supply", b"Unknown"),
        _raw(ROW).replace(b"Demand", b"Supply"),
        _raw(ROW + ",extra"),
        _raw(ROW.rsplit(",", 1)[0]),
        _raw(ROW) + b"\xff",
        _raw(ROW, ROW),
    ],
)
def test_schema_drift_malformed_rows_and_duplicate_keys_fail(raw):
    with pytest.raises(ValueError):
        _inspect(raw)


def test_limits_fail_without_returning_a_partial_report():
    raw = _raw(ROW)
    with pytest.raises(ValueError, match="byte"):
        inspect_gbb_csv(raw, max_bytes=len(raw) - 1, max_rows=1)
    with pytest.raises(ValueError, match="row"):
        inspect_gbb_csv(raw, max_bytes=len(raw), max_rows=0)
    raw = _raw(ROW, ROW.replace(",201,", ",202,"))
    with pytest.raises(ValueError, match="row"):
        inspect_gbb_csv(raw, max_bytes=len(raw), max_rows=1)


@pytest.mark.parametrize("budget", [True, -1, 1.5])
def test_resource_budgets_require_positive_integers(budget):
    with pytest.raises(ValueError):
        inspect_gbb_csv(_raw(ROW), max_bytes=budget, max_rows=1)
    with pytest.raises(ValueError):
        inspect_gbb_csv(_raw(ROW), max_bytes=1000, max_rows=budget)


def test_quoted_names_are_parsed_as_one_field():
    raw = _raw(ROW.replace("Synthetic facility", '"Synthetic, facility"'))
    assert _inspect(raw).records[0].facility_name == "Synthetic, facility"


def test_unterminated_csv_quote_is_rejected():
    with pytest.raises(ValueError, match="CSV"):
        _inspect(_raw('"unterminated'))


def test_different_revision_of_same_key_requires_explicit_resolution():
    revised = ROW.replace("2026/02/01 08:00:00", "2026/02/02 08:00:00")
    with pytest.raises(ValueError, match="duplicate"):
        _inspect(_raw(ROW, revised))


def test_leading_zero_identifiers_are_preserved_as_source_text():
    raw = _raw(ROW.replace(",101,", ",00101,").replace(",201,", ",00201,"))
    record = _inspect(raw).records[0]
    assert record.facility_id == "00101"
    assert record.location_id == "00201"
