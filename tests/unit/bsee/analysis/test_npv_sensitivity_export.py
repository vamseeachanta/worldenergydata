"""Synthetic assumed inputs; numerical tolerances do not quantify valuation risk."""

import csv
from copy import deepcopy

import pandas as pd
import pytest


def export(*args, **kwargs):
    from worldenergydata.bsee.analysis.npv_sensitivity_export import (
        export_npv_sensitivity,
    )

    return export_npv_sensitivity(*args, **kwargs)


@pytest.fixture
def inputs():
    cfg = {
        "economics": {
            "cost": {"CAPEX": 1000.0, "OPEX": 2.0, "discount_rate_annual": 0.12}
        },
        "unrelated": {"keep": [1, 2]},
    }
    table = pd.DataFrame(
        {
            "Month": [202401, 202402, ""],
            "Monthly Oil Production": [100.0, 200.0, ""],
            "Revenue (USD)": ["$1,000.00", "$3,000.00", "$4,000.00"],
        }
    )
    return cfg, table


def run_export(inputs, destination, **kwargs):
    return export(
        *inputs,
        destination,
        field_id="synthetic-field",
        api12="000000000001",
        rates=kwargs.pop("rates", [0.05, 0.10, 0.15]),
        **kwargs,
    )


def test_csv_matches_independent_monthly_reference_and_preserves_inputs(
    inputs, tmp_path
):
    cfg, table = inputs
    original_cfg, original_table = deepcopy(cfg), table.copy(deep=True)
    destination = tmp_path / "sensitivity.csv"
    run_export(inputs, destination)
    with destination.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3
    assert [float(row["discount_rate_annual"]) for row in rows] == [0.05, 0.10, 0.15]
    for row, rate in zip(rows, [0.05, 0.10, 0.15]):
        # Immediate CAPEX and end-of-month receipts, derived without FDAS.
        monthly_rate = (1 + rate) ** (1 / 12) - 1
        expected = -1000 + 800 / (1 + monthly_rate) + 2600 / (1 + monthly_rate) ** 2
        assert float(row["npv"]) == pytest.approx(expected, rel=1e-10, abs=1e-8)
        assert row["field_id"] == "synthetic-field"
        assert row["api12"] == "000000000001"
        assert row["currency"] == "USD"
        assert row["rate_basis"] == "annual effective"
        assert row["cashflow_period"] == "monthly"
        assert row["timing_basis"] == "CAPEX at period 0; receipts at month ends"
        assert row["npv_basis"] == "after OPEX and before royalty"
        assert row["royalty_status"] == "NOT_EVALUATED"
    assert cfg == original_cfg
    pd.testing.assert_frame_equal(table, original_table)
    other = tmp_path / "repeat.csv"
    run_export(inputs, other)
    assert other.read_bytes() == destination.read_bytes()


def test_caller_rate_order_and_valid_boundaries(inputs, tmp_path):
    rates = [1.0, 0.0, -0.5]
    destination = tmp_path / "ordered.csv"
    run_export(inputs, destination, rates=iter(rates))
    with destination.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [float(row["discount_rate_annual"]) for row in rows] == rates


@pytest.mark.parametrize(
    "rates", [[], [float("nan")], [float("inf")], [-1], [-1.1], [1.1], [0.1, 0.1]]
)
def test_invalid_rates_leave_no_output(inputs, tmp_path, rates):
    destination = tmp_path / "invalid.csv"
    with pytest.raises(ValueError):
        run_export(inputs, destination, rates=rates)
    assert not destination.exists()


@pytest.mark.parametrize("key", ["CAPEX", "OPEX", "discount_rate_annual"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_economics_leave_no_output(inputs, tmp_path, key, value):
    inputs[0]["economics"]["cost"][key] = value
    destination = tmp_path / "invalid.csv"
    with pytest.raises(ValueError):
        run_export(inputs, destination)
    assert not destination.exists()


@pytest.mark.parametrize("key", ["CAPEX", "OPEX"])
def test_economic_inputs_are_explicit(inputs, tmp_path, key):
    del inputs[0]["economics"]["cost"][key]
    destination = tmp_path / "missing.csv"
    with pytest.raises(ValueError):
        run_export(inputs, destination)
    assert not destination.exists()


@pytest.mark.parametrize("column", ["Revenue (USD)", "Monthly Oil Production"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), "", "invalid"])
def test_bad_operating_rows_are_not_silently_zeroed(inputs, tmp_path, column, value):
    inputs[1][column] = inputs[1][column].astype(object)
    inputs[1].loc[0, column] = value
    destination = tmp_path / "invalid.csv"
    with pytest.raises(ValueError):
        run_export(inputs, destination)
    assert not destination.exists()


def test_empty_operating_table_is_rejected(inputs, tmp_path):
    destination = tmp_path / "empty.csv"
    with pytest.raises(ValueError):
        run_export((inputs[0], inputs[1].iloc[2:]), destination)
    assert not destination.exists()


def test_production_text_must_match_scalar_numeric_parser(inputs, tmp_path):
    # float() accepts underscores, but pandas would silently coerce this to zero
    # in the scalar API. The export must reject that inconsistent interpretation.
    inputs[1].loc[0, "Monthly Oil Production"] = "1_000"
    destination = tmp_path / "invalid-production.csv"
    with pytest.raises(ValueError):
        run_export(inputs, destination)
    assert not destination.exists()


def test_identifiers_are_required(inputs, tmp_path):
    destination = tmp_path / "missing.csv"
    with pytest.raises(ValueError):
        export(*inputs, destination, field_id="", api12="", rates=[0.1])
    assert not destination.exists()


def test_existing_destination_is_preserved(inputs, tmp_path):
    destination = tmp_path / "existing.csv"
    destination.write_text("existing result\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_export(inputs, destination)
    assert destination.read_text(encoding="utf-8") == "existing result\n"


def test_each_rate_uses_isolated_configuration_and_cited_api(
    inputs, tmp_path, monkeypatch
):
    from worldenergydata.bsee.analysis.production_api12 import ProductionAPI12Analysis

    original = deepcopy(inputs[0])
    seen = []

    def calculate(self, cfg, table, **kwargs):
        rate = cfg["economics"]["cost"]["discount_rate_annual"]
        expected = deepcopy(original)
        expected["economics"]["cost"]["discount_rate_annual"] = rate
        assert cfg == expected
        assert kwargs == {"period": "monthly"}
        seen.append(rate)
        cfg["unrelated"]["keep"].append(3)
        table.loc[0, "Revenue (USD)"] = "changed"
        return {"npv": 1.0, "royalty_status": "NOT_EVALUATED"}

    monkeypatch.setattr(
        ProductionAPI12Analysis, "calculate_npv_with_citations", calculate
    )
    run_export(inputs, tmp_path / "delegated.csv")
    assert seen == [0.05, 0.10, 0.15]
    assert inputs[0] == original
    assert inputs[1].loc[0, "Revenue (USD)"] == "$1,000.00"


def test_failed_later_calculation_writes_nothing(inputs, tmp_path, monkeypatch):
    from worldenergydata.bsee.analysis.production_api12 import ProductionAPI12Analysis

    def calculate(self, cfg, table, **kwargs):
        if cfg["economics"]["cost"]["discount_rate_annual"] == 0.10:
            raise ValueError("calculation failed")
        return {"npv": 1.0, "royalty_status": "NOT_EVALUATED"}

    monkeypatch.setattr(
        ProductionAPI12Analysis, "calculate_npv_with_citations", calculate
    )
    destination = tmp_path / "failed.csv"
    with pytest.raises(ValueError):
        run_export(inputs, destination)
    assert not destination.exists()
