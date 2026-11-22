"""Production-component completeness using synthetic, schema-backed inputs."""

import json
import runpy
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.ukcs.production.field_production import UKCSFieldProductionLoader


@pytest.fixture
def raw_components():
    path = Path(__file__).parents[2] / "fixtures/ukcs/pprs_components.json"
    return pd.DataFrame(json.loads(path.read_text())["records"])


def test_source_volumes_are_mapped_without_mass_or_daily_rate_double_counting(
    raw_components,
):
    """Hand calculation, using rounded shared factors from NIST SP 811 B.8.

    The petroleum barrel and cubic-foot entries give 0.1589873 m3/bbl and
    0.02831685 m3/ft3. Their rounded inverses are 6.2898 and 35.3147.
    Synthetic condensate: 10 m3 * 6.2898 = 62.898 bbl, irrespective of mass
    or daily-rate fields. Gas: (2 + 3) ksm3 * 35.3147 = 176.5735 Mcf.
    Injection: 4 * 35.3147 = 141.2588 Mcf; water 20 * 6.2898 = 125.796 bbl;
    reinjection 5 * 6.2898 = 31.449 bbl; flare 1 * 35.3147 = 35.3147 Mcf.
    """
    row = UKCSFieldProductionLoader().load(raw_components).iloc[0]
    expected = {
        "condensate_bbl": 62.898,
        "gas_mcf": 176.5735,
        "associated_gas_mcf": 70.6294,
        "dry_gas_mcf": 105.9441,
        "gas_injected_mcf": 141.2588,
        "water_injected_bbl": 125.796,
        "water_reinjected_bbl": 31.449,
        "gas_flared_mcf": 35.3147,
        "gas_vented_mcf": 0,
    }
    for name, value in expected.items():
        assert row[name] == pytest.approx(value)
    assert pd.isna(row["ngl_bbl"])


def test_nulls_remain_unknown_and_reported_zeros_remain_zero(raw_components):
    """Null is not a measurement; a synthetic reported zero is exactly zero."""
    result = UKCSFieldProductionLoader().load(raw_components)
    streams = [name for name in result if name.endswith(("_bbl", "_mcf"))]
    for name in streams:
        if name != "associated_gas_mcf":
            assert pd.isna(result.loc[1, name])
        if name != "ngl_bbl":
            assert result.loc[2, name] == 0


@pytest.mark.parametrize("field", ["AGASPROKSM", "DGASPROKSM"])
def test_a_missing_gas_component_does_not_become_zero(raw_components, field):
    """A total cannot be established from only one of its two components."""
    result = UKCSFieldProductionLoader().load(raw_components.drop(columns=field))
    assert result["gas_mcf"].isna().all()


@pytest.mark.parametrize(
    "columns", [["GCONDVOL"], ["GCONDVOL", "GCONDMASS", "GCONDMBD"]]
)
def test_mass_only_or_absent_condensate_is_unknown(raw_components, columns):
    """No density is supplied, so tonnes cannot establish liquid volume."""
    raw = raw_components.drop(columns=columns)
    raw["NGL"] = 100  # Synthetic unrelated label: no verified PPRS NGL mapping.
    result = UKCSFieldProductionLoader().load(raw)
    assert result["condensate_bbl"].isna().all()
    assert result["ngl_bbl"].isna().all()


def test_absent_production_columns_are_unknown(raw_components):
    """Identifiers alone supply no measured stream values."""
    raw = raw_components[["FIELDNAME", "PERIODYR", "PERIODMNTH"]]
    result = UKCSFieldProductionLoader().load(raw)
    assert result.filter(regex="_(bbl|mcf)$").isna().all().all()


@pytest.mark.parametrize(
    "values", [["not reported", "", None], [float("inf"), float("-inf"), None]]
)
def test_invalid_numeric_values_remain_unknown(raw_components, values):
    """Non-numeric and infinite values cannot establish condensate volume."""
    raw_components["GCONDVOL"] = values
    assert (
        UKCSFieldProductionLoader().load(raw_components)["condensate_bbl"].isna().all()
    )


def test_annual_totals_do_not_hide_a_missing_month(raw_components):
    """Known January plus unknown February plus zero March is unknown."""
    loader = UKCSFieldProductionLoader()
    annual = loader.annual_aggregate(loader.load(raw_components))
    for name in ["oil_bbl", "gas_mcf", "water_bbl", "condensate_bbl", "ngl_bbl"]:
        assert pd.isna(annual.loc[0, name])


def test_annual_complete_observed_months_are_summed(raw_components):
    """Hand sum: 62.898 + 0 = 62.898 bbl; not a complete calendar year."""
    loader = UKCSFieldProductionLoader()
    annual = loader.annual_aggregate(loader.load(raw_components.iloc[[0, 2]]))
    assert annual.loc[0, "condensate_bbl"] == pytest.approx(62.898)
    assert annual.loc[0, "gas_vented_mcf"] == 0
    assert pd.isna(annual.loc[0, "ngl_bbl"])


def test_empty_load_and_annual_frames_retain_component_schema():
    loader = UKCSFieldProductionLoader()
    empty = loader.load(pd.DataFrame())
    assert "condensate_bbl" in empty
    assert "ngl_bbl" in loader.annual_aggregate(empty)


def test_legacy_nulls_remain_unknown():
    """Legacy labels identify units, but nulls still supply no measurement."""
    raw = pd.DataFrame(
        {
            "FieldName": ["EXAMPLE"],
            "Year": [2024],
            "Month": [1],
            "OilProduction (Thousand Tonnes)": [None],
            "GasProduction (MMscf)": [None],
            "WaterProduction (Thousand Tonnes)": [None],
        }
    )
    result = UKCSFieldProductionLoader().load(raw)
    assert result[["oil_bbl", "gas_mcf", "water_bbl"]].isna().all().all()


def test_worked_example_reports_inputs_and_unknown_annual_total(capsys):
    """Hand calculation: 10 * 6.2898 rounds to 62.9; 10 plus null is unknown."""
    path = Path(__file__).parents[3] / "examples/ukcs/production_components.py"
    runpy.run_path(str(path), run_name="__main__")
    output = capsys.readouterr().out
    assert "GCONDVOL" in output
    assert "62.9" in output
    assert "Observed-month annual totals" in output
    assert "NaN" in output
