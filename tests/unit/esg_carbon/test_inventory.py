"""Independent arithmetic on synthetic Climate TRACE schema observations."""

from dataclasses import replace
from datetime import date

import pytest

from worldenergydata.esg_carbon import read_climate_trace_csv

from .test_climate_trace import HEADER, ROW, write_inventory


def test_lookup_filters_without_combining_gases(tmp_path):
    rows = ROW + ROW.replace(",co2,12.5,", ",ch4,2.5,")
    rows += ROW.replace("synthetic-1", "synthetic-2").replace("USA", "CAN")
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    assert len(inventory.select(source_id="synthetic-1")) == 2
    assert len(inventory.select(iso3_country="CAN", gas="co2")) == 1
    assert inventory.select(source_id="absent") == ()
    assert len(inventory.records) == 3


def test_total_is_sum_of_same_basis_observations(tmp_path):
    """Hand calculation: 12.5 + 2.5 = 15.0 tonnes CO2, same period and sector."""
    rows = ROW + ROW.replace("synthetic-1", "synthetic-2").replace(",12.5,", ",2.5,")
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    total = inventory.summarize()
    assert total.total_tonnes == pytest.approx(15.0)
    assert total.known_subtotal_tonnes == pytest.approx(15.0)
    assert total.record_count == 2
    assert total.missing_count == 0
    assert total.status == "COMPLETE"
    assert total.gas == "co2"


def test_missing_observation_prevents_complete_total(tmp_path):
    """Hand calculation: known subtotal = 12.5; 12.5 + unknown is unknown."""
    rows = ROW + ROW.replace("synthetic-1", "synthetic-2").replace(",12.5,", ",null,")
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    total = inventory.summarize()
    assert total.total_tonnes is None
    assert total.known_subtotal_tonnes == 12.5
    assert total.missing_count == 1
    assert total.status == "INCOMPLETE"


def test_empty_selection_is_not_a_zero_total(tmp_path):
    inventory = read_climate_trace_csv(write_inventory(tmp_path), edition="x")
    total = inventory.summarize(source_id="absent")
    assert total.total_tonnes is None
    assert total.status == "NOT_EVALUATED"
    assert total.record_count == 0


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (",co2,", ",co2e_100gwp,"),
        ("2024-01-01", "2024-02-01"),
        ("2024-12-31", "2024-11-30"),
        ("annual", "monthly"),
        ("USA", "CAN"),
        ("oil-and-gas-production-and-transport", "oil-and-gas-refining"),
        ("fossil-fuel-operations", "synthetic-sector"),
    ],
)
def test_mixed_basis_cannot_be_summed(tmp_path, old, new):
    rows = ROW + ROW.replace("synthetic-1", "synthetic-2").replace(old, new)
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    with pytest.raises(ValueError, match="basis"):
        inventory.summarize()


def test_duplicate_source_periods_cannot_be_double_counted(tmp_path):
    rows = ROW + ROW.replace("2024-01-01", "2024-02-01")
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    with pytest.raises(ValueError):
        inventory.summarize()


@pytest.mark.parametrize(
    ("mass", "status", "expected"), [("null", "INCOMPLETE", None), ("0", "COMPLETE", 0)]
)
def test_all_missing_and_reported_zero_have_different_totals(
    tmp_path, mass, status, expected
):
    """Missing + missing is unknown; zero + zero is zero, by hand arithmetic."""
    rows = (ROW + ROW.replace("synthetic-1", "synthetic-2")).replace(
        ",12.5,", f",{mass},"
    )
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    summary = inventory.summarize()
    assert summary.status == status
    assert summary.total_tonnes == expected
    assert summary.edition == inventory.edition
    assert summary.sha256 == inventory.sha256


def test_filtered_summary_keeps_only_selected_basis(tmp_path):
    """Hand calculation: selecting the CO2 row excludes the CH4 row; total=12.5."""
    rows = ROW + ROW.replace(",co2,", ",ch4,")
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    record = inventory.records[0]
    summary = inventory.summarize(
        gas="co2",
        subsector=record.subsector,
        start_time=record.start_time,
        end_time=record.end_time,
    )
    assert summary.total_tonnes == 12.5
    assert summary.basis == record.basis


def test_finite_observations_cannot_overflow_to_a_complete_total(tmp_path):
    """Synthetic numeric stress: two finite masses exceed the float range."""
    rows = (ROW + ROW.replace("synthetic-1", "synthetic-2")).replace(
        ",12.5,", ",1e308,"
    )
    inventory = read_climate_trace_csv(
        write_inventory(tmp_path, HEADER + rows), edition="x"
    )
    with pytest.raises(ValueError, match="finite"):
        inventory.summarize()


@pytest.mark.parametrize("method", ["select", "summarize"])
@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize("empty", [False, True])
def test_naive_period_filters_are_rejected(tmp_path, method, field, empty):
    inventory = read_climate_trace_csv(write_inventory(tmp_path), edition="x")
    naive = getattr(inventory.records[0], field).replace(tzinfo=None)
    filters = {field: naive}
    if empty:
        filters["source_id"] = "absent"
    with pytest.raises(ValueError, match=rf"{field}.*timezone-aware"):
        getattr(inventory, method)(**filters)


@pytest.mark.parametrize("method", ["select", "summarize"])
@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("value", [date(2024, 1, 1), "2024-01-01T00:00:00Z", 2024])
def test_non_datetime_period_filters_are_rejected(
    tmp_path, method, field, empty, value
):
    inventory = read_climate_trace_csv(write_inventory(tmp_path), edition="x")
    filters = {field: value}
    if empty:
        filters["source_id"] = "absent"
    with pytest.raises(ValueError, match=rf"{field}.*timezone-aware"):
        getattr(inventory, method)(**filters)


@pytest.mark.parametrize("method", ["select", "summarize"])
@pytest.mark.parametrize("horizon", ["100", "20"])
def test_alias_gas_filters_match_canonical_records(tmp_path, method, horizon):
    text = HEADER + ROW.replace(",co2,", f",co2e_{horizon}yr,")
    inventory = read_climate_trace_csv(write_inventory(tmp_path, text), edition="x")
    query = getattr(inventory, method)
    result = query(gas=f"co2e_{horizon}yr")
    assert result == query(gas=f"co2e_{horizon}gwp")
    if method == "select":
        assert len(result) == 1
        assert result[0].gas == f"co2e_{horizon}gwp"
    else:
        assert result.record_count == 1
        assert result.status == "COMPLETE"
        assert result.total_tonnes == 12.5


@pytest.mark.parametrize("method", ["select", "summarize"])
@pytest.mark.parametrize("horizon", ["100", "20"])
def test_direct_records_share_canonical_gas_basis(tmp_path, method, horizon):
    inventory = read_climate_trace_csv(write_inventory(tmp_path), edition="x")
    record = inventory.records[0]
    alias = replace(record, gas=f"co2e_{horizon}yr")
    canonical = replace(record, source_id="synthetic-2", gas=f"co2e_{horizon}gwp")
    other_horizon = "20" if horizon == "100" else "100"
    other = replace(record, gas=f"co2e_{other_horizon}yr")
    inventory = replace(inventory, records=(alias, canonical, other))

    assert alias.gas == f"co2e_{horizon}gwp"
    assert alias.basis == canonical.basis
    assert alias.basis != other.basis
    query = getattr(inventory, method)
    result = query(gas=f"co2e_{horizon}yr")
    assert result == query(gas=f"co2e_{horizon}gwp")
    if method == "select":
        assert result == (alias, canonical)
    else:
        assert result.record_count == 2
        assert result.total_tonnes == 25.0
        assert result.status == "COMPLETE"
        assert result.gas == f"co2e_{horizon}gwp"
    with pytest.raises(ValueError, match="basis"):
        inventory.summarize()
