"""Country contract tests with independently calculated synthetic volumes."""

import pytest

from worldenergydata.mexico_cnh.bulk import load_production_workbook
from worldenergydata.mexico_cnh.production import SenerProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery

from .test_bulk_production import workbook


def test_adapter_filters_and_requires_water_for_fdas(tmp_path):
    """February oil=2*1000*29=58000; supplied water is explicitly synthetic."""
    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    adapter = SenerProductionAdapter(observed)
    frame = adapter.fetch(ProductionQuery(regions=["mexico"], fields=["EXAMPLE"]))
    assert frame.iloc[0].oil_bbl == 58000
    assert adapter.available_fields() == ["EXAMPLE"]
    assert adapter.date_range() == ("2024-02", "2024-02")
    with pytest.raises(ValueError, match="water"):
        adapter.fdas_inputs()
    water = {("EXAMPLE", 2024, 2): 7.0}
    bundle = adapter.fdas_inputs(water_bbl=water)
    assert bundle.production.iloc[0].MONTHLY_WATER_BBL == 7
    assert bundle.production.iloc[0].MONTHLY_OIL_BBL == 58000
    assert bundle.metadata["sha256"] == observed.sha256
    assert adapter.fetch(ProductionQuery(regions=["mexico"], fields=["ABSENT"])).empty


def test_collection_uses_local_workbook(tmp_path):
    from worldenergydata.mexico_cnh.data.mexico_cnh_data import MexicoCNHData

    path = workbook(tmp_path / "source.xlsx")
    _cfg, result = MexicoCNHData().router(
        {
            "data_types": ["production"],
            "continue_on_error": False,
            "production_bulk": {"workbook": str(path)},
        }
    )
    assert result["production"][0]["oil_bbl"] == 58000
    assert (
        result["production"][0]["source_sha256"]
        == load_production_workbook(path).sha256
    )


def test_report_does_not_claim_economics_or_screening(tmp_path):
    from worldenergydata.mexico_cnh.chain import run_chain

    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    result = run_chain(observed)
    assert result.checks["production"] == "PASS"
    assert result.checks["fdas_inputs"] == "NOT_EVALUATED"
    assert result.checks["economics"] == "NOT_EVALUATED"
    assert result.checks["concept_screening"] == "NOT_EVALUATED"
    assert "Revision history" in result.html
    assert observed.sha256 in result.html
    assert "water" in result.html
    assert result.fdas is None
    supplied = run_chain(observed, water_bbl={("EXAMPLE", 2024, 2): 7})
    assert supplied.checks["fdas_inputs"] == "PASS"
    assert supplied.checks["economics"] == "NOT_EVALUATED"
    assert supplied.fdas.production.iloc[0].MONTHLY_GAS_MCF == 87000


@pytest.mark.parametrize("water", [-1, float("nan"), float("inf")])
def test_invalid_water_cannot_qualify_fdas(tmp_path, water):
    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    with pytest.raises(ValueError, match="finite"):
        SenerProductionAdapter(observed).fdas_inputs(
            water_bbl={("EXAMPLE", 2024, 2): water}
        )


def test_adapter_honors_dates_and_regions(tmp_path):
    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    adapter = SenerProductionAdapter(observed)
    assert adapter.fetch(ProductionQuery(regions=["mexico"], start="2024-03")).empty
    assert adapter.fetch(ProductionQuery(regions=["mexico"], end="2024-01")).empty
    assert adapter.fetch(ProductionQuery(regions=["other"])).empty
    assert (
        len(
            adapter.fetch(
                ProductionQuery(
                    regions=["mexico"],
                    fields=["example"],
                    start="2024-02",
                    end="2024-02",
                )
            )
        )
        == 1
    )


def test_ambiguous_field_identity_is_reported_and_can_be_scoped(tmp_path):
    """Same field label in two basins is never treated as one development."""
    from dataclasses import replace

    import pandas as pd

    from worldenergydata.mexico_cnh.chain import run_chain

    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    other = observed.production.copy()
    other["basin"] = "Other basin"
    ambiguous = replace(observed, production=pd.concat([observed.production, other]))
    report = run_chain(ambiguous)
    assert report.checks["fdas_inputs"] == "NOT_EVALUATED"
    assert "ambiguous" in report.html
    scoped = SenerProductionAdapter(ambiguous, basin="Basin", location="Terrestre")
    assert len(scoped.fetch(ProductionQuery(regions=["mexico"]))) == 1
    assert (
        scoped.fdas_inputs(water_bbl={("EXAMPLE", 2024, 2): 7}).metadata["basin"]
        == "Basin"
    )


def test_worked_example_runs_and_checks_its_answer(tmp_path):
    import runpy
    from pathlib import Path

    example = (
        Path(__file__).resolve().parents[3] / "examples/mexico_cnh/production_chain.py"
    )
    namespace = runpy.run_path(str(example))
    answer = namespace["worked_example"](tmp_path)
    assert answer == {"oil_bbl": 58000, "gas_mcf": 87000, "condensate_bbl": 29000}
    assert "NOT_EVALUATED" in (tmp_path / "analysis.html").read_text()


def test_boolean_water_is_not_a_measurement(tmp_path):
    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    with pytest.raises(ValueError, match="water"):
        SenerProductionAdapter(observed).fdas_inputs(
            water_bbl={("EXAMPLE", 2024, 2): False}
        )


@pytest.mark.parametrize("liquids_only", [False, True])
def test_fetch_preserves_unknown_operator_contributions(tmp_path, liquids_only):
    """One known operator never masks another operator's missing measurement."""
    from openpyxl import load_workbook

    path = workbook(tmp_path / "source.xlsx")
    book = load_workbook(path)
    liquid = book["Aceite y condensado"]
    other = [cell.value for cell in liquid[4]]
    other[4], other[6] = "OTHER", None
    liquid.append(other)
    gas = book["Gas Natural"]
    if liquids_only:
        gas.delete_rows(3)
    else:
        other = [cell.value for cell in gas[3]]
        other[4], other[5] = "OTHER", None
        gas.append(other)
    book.save(path)
    book.close()
    observed = load_production_workbook(path)
    frame = SenerProductionAdapter(observed).fetch(ProductionQuery(regions=["mexico"]))
    assert len(frame) == 1
    assert frame[["oil_bbl", "gas_mcf", "water_bbl"]].isna().all().all()
    assert frame.iloc[0].condensate_bbl == 58000


@pytest.mark.parametrize("water", ["7", None, complex(7, 1)])
def test_non_numeric_water_is_rejected(tmp_path, water):
    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    with pytest.raises(ValueError, match="water.*numeric"):
        SenerProductionAdapter(observed).fdas_inputs(
            water_bbl={("EXAMPLE", 2024, 2): water}
        )


@pytest.mark.parametrize("water", [-1, float("nan"), "7", None])
def test_evaluated_fdas_failure_is_reported(tmp_path, water):
    from worldenergydata.mexico_cnh.chain import run_chain

    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    result = run_chain(observed, water_bbl={("EXAMPLE", 2024, 2): water})
    assert result.checks["fdas_inputs"] == "FAIL"
    assert result.fdas is None
    assert "FAIL" in result.html


def test_missing_supplied_water_is_a_failed_check(tmp_path):
    from worldenergydata.mexico_cnh.chain import run_chain

    observed = load_production_workbook(workbook(tmp_path / "source.xlsx"))
    assert run_chain(observed, water_bbl={}).checks["fdas_inputs"] == "FAIL"
