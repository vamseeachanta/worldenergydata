"""Synthetic AEMO schema examples; no publisher rows are redistributed.

Column names and date formats: AEMO GasBBActualFlowStorageLast31.CSV,
header observed 2026-10-19 (source URL in the reader). All quantities below
are invented arithmetic inputs in unqualified report units, not gas volumes.
"""

import csv
from dataclasses import fields, replace
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal, Inexact, localcontext

import pytest

from worldenergydata.australia.production.aemo_gbb import (
    monthly_supply,
    read_actual_flow_csv,
)

HEADER = [
    "GasDate",
    "FacilityName",
    "FacilityId",
    "FacilityType",
    "Demand",
    "Supply",
    "TransferIn",
    "TransferOut",
    "HeldInStorage",
    "CushionGasStorage",
    "State",
    "LocationName",
    "LocationId",
    "LastUpdated",
]


def _row(day="2024/02/01", supply="2.5", **changes):
    """Synthetic identifiers and quantities, not observed facility data."""
    row = dict.fromkeys(HEADER, "")
    row.update(
        GasDate=day,
        FacilityName="Synthetic facility",
        FacilityId="F-A",
        FacilityType="SYNTHETIC",
        Supply=supply,
        LocationName="Synthetic location",
        LocationId="L-A",
        LastUpdated="2024/03/02 12:00:00",
    )
    row.update(changes)
    return row


def _write(tmp_path, rows, header=HEADER):
    path = tmp_path / "actual-flow.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_reads_exact_decimal_supply_and_preserves_facility_location(tmp_path):
    """Decimal text 2.5 is retained exactly; there is no physical conversion."""
    records = read_actual_flow_csv(_write(tmp_path, [_row()]))
    assert len(records) == 1
    record = records[0]
    assert record.gas_date == date(2024, 2, 1)
    assert record.supply == Decimal("2.5")
    assert record.facility_id == "F-A"
    assert record.location_id == "L-A"
    assert record.facility_type == "SYNTHETIC"
    assert record.last_updated.isoformat() == "2024-03-02T12:00:00"


def test_rollup_selects_one_location_and_never_counts_transfer_or_demand(tmp_path):
    """Hand sum: 2.5 + 3.5 = 6; other locations/facilities contribute nothing.

    Demand=99 and TransferIn=100 are independent synthetic report fields and
    must not be added to Supply. February 2024 has 29 days (Gregorian calendar),
    of which 2 are observed and 27 are missing. No full-month extrapolation.
    """
    rows = [
        _row(supply="2.5", Demand="99", TransferIn="100"),
        _row("2024/02/02", "3.5"),
        _row(supply="1000", LocationId="L-B"),
        _row(supply="2000", FacilityId="F-B"),
    ]
    (summary,) = monthly_supply(
        read_actual_flow_csv(_write(tmp_path, rows)),
        facility_id="F-A",
        location_id="L-A",
    )
    assert summary.observed_supply_total == Decimal("6.0")
    assert summary.reported_days == 2
    assert summary.calendar_days == 29
    assert len(summary.missing_dates) == 27
    assert summary.missing_dates[0] == date(2024, 2, 3)
    assert summary.complete is False
    assert summary.unit_status == "NOT_EVALUATED"
    assert summary.reuse_status == "NOT_EVALUATED"
    assert summary.production_status == "NOT_EVALUATED"


def test_complete_month_includes_reported_zero_without_filling_gaps(tmp_path):
    """Hand sum: 28 reported days at 2 + one reported zero = 56 units.

    February 2024 has 29 Gregorian calendar days; a recorded zero is present,
    unlike a missing day. No calorific value or energy unit is assumed.
    """
    rows = [_row(f"2024/02/{day:02d}", "2") for day in range(1, 29)]
    rows.append(_row("2024/02/29", "0"))
    (summary,) = monthly_supply(
        read_actual_flow_csv(_write(tmp_path, rows)),
        facility_id="F-A",
        location_id="L-A",
    )
    assert summary.observed_supply_total == Decimal(56)
    assert summary.complete is True
    assert summary.missing_dates == ()


def test_blank_supply_is_unknown_and_prevents_a_total(tmp_path):
    """One known 2.5 and one unknown supply cannot establish a sum."""
    (summary,) = monthly_supply(
        read_actual_flow_csv(_write(tmp_path, [_row(), _row("2024/02/02", "")])),
        facility_id="F-A",
        location_id="L-A",
    )
    assert summary.observed_supply_total is None
    assert summary.missing_supply_days == 1
    assert summary.reported_days == 2
    assert summary.complete is False


def test_months_are_sorted_and_missing_months_are_not_synthesized(tmp_path):
    """One input day per month; April and February totals stay 7 and 2.5."""
    rows = [_row("2024/04/01", "7"), _row()]
    summaries = monthly_supply(
        read_actual_flow_csv(_write(tmp_path, rows)),
        facility_id="F-A",
        location_id="L-A",
    )
    assert [(m.year, m.month) for m in summaries] == [(2024, 2), (2024, 4)]
    assert [m.observed_supply_total for m in summaries] == [Decimal("2.5"), Decimal(7)]


@pytest.mark.parametrize("supply", ["NaN", "Infinity", "-Infinity", "not-a-number"])
def test_rejects_nonfinite_or_malformed_supply(tmp_path, supply):
    with pytest.raises(ValueError, match="Supply"):
        read_actual_flow_csv(_write(tmp_path, [_row(supply=supply)]))


@pytest.mark.parametrize(
    "changes",
    [
        {"GasDate": "2024/02/30"},
        {"GasDate": "2024-02-01"},
        {"LastUpdated": "invalid"},
        {"FacilityId": ""},
        {"LocationId": ""},
        {"FacilityName": " "},
        {"FacilityType": ""},
        {"LocationName": ""},
    ],
)
def test_rejects_missing_identity_or_invalid_date(tmp_path, changes):
    with pytest.raises(ValueError):
        read_actual_flow_csv(_write(tmp_path, [_row(**changes)]))


@pytest.mark.parametrize("updated", ["2024/03/02 12:00:00", "2024/03/03 12:00:00"])
def test_duplicate_day_location_rejected_without_assuming_revision_rules(
    tmp_path, updated
):
    """Two rows with one daily key are ambiguous even with different timestamps."""
    with pytest.raises(ValueError, match="duplicate"):
        read_actual_flow_csv(_write(tmp_path, [_row(), _row(LastUpdated=updated)]))


def test_rollup_rejects_concatenated_overlapping_exports(tmp_path):
    records = read_actual_flow_csv(_write(tmp_path, [_row()]))
    with pytest.raises(ValueError, match="duplicate"):
        monthly_supply(records + records, facility_id="F-A", location_id="L-A")


def test_missing_supply_column_is_not_an_empty_report(tmp_path):
    header = [column for column in HEADER if column != "Supply"]
    row = {column: value for column, value in _row().items() if column in header}
    with pytest.raises(ValueError, match="Supply"):
        read_actual_flow_csv(_write(tmp_path, [row], header))


def test_header_only_is_valid_empty_report(tmp_path):
    records = read_actual_flow_csv(_write(tmp_path, []))
    assert records == ()
    assert monthly_supply(records, facility_id="F-A", location_id="L-A") == ()


def test_missing_selection_is_empty_and_requires_no_name_mapping(tmp_path):
    records = read_actual_flow_csv(_write(tmp_path, [_row()]))
    assert monthly_supply(records, facility_id="F-B", location_id="L-A") == ()


@pytest.mark.parametrize("content", ["", "GasDate,GasDate\n", ",Supply\n"])
def test_rejects_empty_or_ambiguous_header(tmp_path, content):
    path = tmp_path / "invalid.csv"
    path.write_text(content)
    with pytest.raises(ValueError, match="header"):
        read_actual_flow_csv(path)


def test_rejects_ragged_records(tmp_path):
    path = tmp_path / "ragged.csv"
    path.write_text(",".join(HEADER) + "\n2024/02/01,too,few\n")
    with pytest.raises(ValueError, match="column count"):
        read_actual_flow_csv(path)


@pytest.mark.parametrize(
    "supplies, expected",
    [
        (["12.34", "0.005"], "12.345"),
        (["12345678901234567890123456789"], "12345678901234567890123456789"),
        (["999.999", "0.001"], "1000.000"),
        (["0.00012345", "0.00000005"], "0.00012350"),
        (
            [
                "10000000000000000000000000000",
                "0.005",
                "-10000000000000000000000000000",
            ],
            "0.005",
        ),
    ],
)
@pytest.mark.parametrize(
    "precision, emax, emin, rounding, clamp",
    [
        (28, 999999, -999999, ROUND_HALF_EVEN, 0),
        (4, 999999, -999999, ROUND_HALF_EVEN, 0),
        (2, 2, -2, ROUND_DOWN, 1),
    ],
)
@pytest.mark.parametrize("trap_inexact", [False, True])
def test_rollup_is_exact_and_preserves_caller_decimal_context(
    tmp_path, supplies, expected, precision, emax, emin, rounding, clamp, trap_inexact
):
    """Literal base-ten sums include carry, cancellation and a 29-digit reading.

    12345 hundred-millionths + 5 hundred-millionths = 12350 hundred-millionths;
    equal opposite large integers cancel, leaving the literal 0.005 reading.
    Context settings are synthetic arithmetic stress cases, not source limits.
    """
    rows = [
        _row(f"2024/02/{day:02d}", supply)
        for day, supply in enumerate(supplies, start=1)
    ]
    records = read_actual_flow_csv(_write(tmp_path, rows))
    with localcontext() as context:
        context.prec = precision
        context.Emax = emax
        context.Emin = emin
        context.rounding = rounding
        context.clamp = clamp
        context.traps[Inexact] = trap_inexact
        context.clear_flags()
        original = context.copy()
        (summary,) = monthly_supply(records, facility_id="F-A", location_id="L-A")
        assert summary.observed_supply_total == Decimal(expected)
        assert context.prec == original.prec
        assert context.Emax == original.Emax
        assert context.Emin == original.Emin
        assert context.rounding == original.rounding
        assert context.clamp == original.clamp
        assert context.traps == original.traps
        assert context.flags == original.flags


@pytest.mark.parametrize(
    "facility_id, location_id",
    [(" F-A", "L-A"), ("F-A", "L-A \t"), (" F-A ", " L-A ")],
)
def test_selection_strips_whitespace_like_parsed_identifiers(
    tmp_path, facility_id, location_id
):
    records = read_actual_flow_csv(
        _write(tmp_path, [_row(FacilityId=" F-A ", LocationId=" L-A ")])
    )
    (summary,) = monthly_supply(
        records, facility_id=facility_id, location_id=location_id
    )
    assert summary.facility_id == "F-A"
    assert summary.location_id == "L-A"
    assert summary.observed_supply_total == Decimal("2.5")


@pytest.mark.parametrize("selection", ["facility_id", "location_id"])
def test_selection_rejects_blank_identifiers(tmp_path, selection):
    records = read_actual_flow_csv(_write(tmp_path, [_row()]))
    arguments = {"facility_id": "F-A", "location_id": "L-A", selection: " \t"}
    with pytest.raises(ValueError, match="required"):
        monthly_supply(records, **arguments)


@pytest.mark.parametrize("status", ["unit_status", "reuse_status", "production_status"])
def test_qualification_cannot_be_promoted_by_replace(tmp_path, status):
    records = read_actual_flow_csv(_write(tmp_path, [_row()]))
    (summary,) = monthly_supply(records, facility_id="F-A", location_id="L-A")
    with pytest.raises(ValueError, match=status):
        replace(summary, **{status: "QUALIFIED"})
    assert getattr(replace(summary, reported_days=1), status) == "NOT_EVALUATED"


@pytest.mark.parametrize("status", ["unit_status", "reuse_status", "production_status"])
def test_qualification_cannot_be_promoted_in_constructor(tmp_path, status):
    records = read_actual_flow_csv(_write(tmp_path, [_row()]))
    (summary,) = monthly_supply(records, facility_id="F-A", location_id="L-A")
    arguments = {
        field.name: getattr(summary, field.name)
        for field in fields(summary)
        if field.init
    }
    arguments[status] = "QUALIFIED"
    with pytest.raises(TypeError, match=status):
        type(summary)(**arguments)


@pytest.mark.parametrize("supply", ["1_000", "1E+3", "1e-3", "1E+1000000"])
def test_rejects_non_report_decimal_notation(tmp_path, supply):
    with pytest.raises(ValueError, match="Supply"):
        read_actual_flow_csv(_write(tmp_path, [_row(supply=supply)]))


@pytest.mark.parametrize("supply", ["0", "-1.25", "+2.50", "001.250", " 2.5 "])
def test_accepts_signed_fixed_point_supply(tmp_path, supply):
    (record,) = read_actual_flow_csv(_write(tmp_path, [_row(supply=supply)]))
    assert record.supply == Decimal(supply.strip())
