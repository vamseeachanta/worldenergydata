"""#716 Norway chain slice — SodirAdapter real path + FieldConcept normalizer + wiring.

Self-contained (no repo conftest/data); run:
  .venv/bin/python -m pytest tests/unit/sodir/test_norway_716.py --noconftest -o addopts="" -q
"""

from datetime import datetime

import numpy as np
import pandas as pd

from worldenergydata.fdas.adapters.contract import (
    FDAS_PRODUCTION_COLUMNS,
    to_fdas_production,
)
from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.production.unified.adapters.sodir_adapter import SodirAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery
from worldenergydata.sodir.field_concept import sodir_field_to_concept


class _FakeLoader:
    """Duck-typed MonthlyProductionLoader: returns loader-output columns."""

    def __init__(self, df):
        self._df = df

    def load_all_production(self):
        return self._df


def _loader_frame():
    # MonthlyProductionLoader output schema (already Sm3→bbl for oil/gas).
    return pd.DataFrame(
        [
            # field_name, year, month, oil_sm3, gas_sm3, ngl_sm3, condensate_sm3,
            # water_injected_sm3, oil_bbl, gas_mcf
            ("TROLL", 2024, 1, 1e6, 1e9, 0.0, 5000.0, 9e5, 6_289_810.0, 35_314.7),
            ("TROLL", 2024, 2, 9e5, 9e8, 0.0, 4500.0, 8e5, 5_660_829.0, 31_783.2),
        ],
        columns=[
            "field_name",
            "year",
            "month",
            "oil_sm3",
            "gas_sm3",
            "ngl_sm3",
            "condensate_sm3",
            "water_injected_sm3",
            "oil_bbl",
            "gas_mcf",
        ],
    )


# --- SodirAdapter real path (B1 transform) ---------------------------------


def test_real_loader_path_emits_standard_columns():
    adapter = SodirAdapter(loader=_FakeLoader(_loader_frame()))
    df = adapter.fetch(ProductionQuery(regions=["ncs"]))
    assert list(df.columns) == list(STANDARD_COLUMNS)
    assert (df["region"] == "ncs").all()
    assert (df["source"] == "sodir").all()
    assert (df["field_name"] == "TROLL").all()


def test_water_bbl_is_nan_not_injection():
    adapter = SodirAdapter(loader=_FakeLoader(_loader_frame()))
    df = adapter.fetch(ProductionQuery(regions=["ncs"]))
    # water_injected_sm3 must NOT leak into water_bbl (injection != production)
    assert df["water_bbl"].isna().all()


def test_condensate_converted_from_sm3():
    adapter = SodirAdapter(loader=_FakeLoader(_loader_frame()))
    df = adapter.fetch(ProductionQuery(regions=["ncs"]))
    # 5000 Sm3 * SM3_TO_BBL (~6.2898) ≈ 31449 bbl, not 5000 and not 0
    assert df["condensate_bbl"].iloc[0] > 5000
    assert (df["condensate_bbl"] > 0).all()


def test_mock_default_still_works_when_no_loader():
    adapter = SodirAdapter()  # no loader -> synthetic benchmark (keeps suite non-empty)
    df = adapter.fetch(ProductionQuery(regions=["ncs"]))
    assert len(df) > 0
    assert "Edvard Grieg" in set(df["field_name"])


# --- Norway FieldConcept normalizer (F2 FieldMetaMapping consumer) ----------


def _processed_field():
    return {
        "field_name": "Troll",
        "operator": "Equinor",
        "main_area": "NORTH SEA",
        "water_depth_m": 340.0,
        "production_start_year": 1996,
        "recoverable_oil_mmbbl": 800.0,
        "recoverable_gas_bcf": 60.0,
    }


def test_sodir_field_to_concept_builds_valid_concept():
    fc = sodir_field_to_concept(_processed_field())
    assert fc.name == "Troll"
    assert fc.operator == "Equinor"
    assert fc.region == "norway"  # constant, NOT sea-area (M1)
    assert fc.water_depth_m == 340.0
    assert fc.year_first_oil == 1996
    # reserves: 800 MMbbl oil + 60 Bcf/6 = 810 MMboe (M2)
    assert fc.recoverable_reserves_mmboe == 810.0


def test_reserves_none_when_both_absent():
    p = _processed_field()
    p["recoverable_oil_mmbbl"] = None
    p["recoverable_gas_bcf"] = None
    fc = sodir_field_to_concept(p)
    assert fc.recoverable_reserves_mmboe is None


# --- chain wiring: fetch -> to_fdas_production -> cashflow; concept -> screen -


def test_chain_slice_runs_and_returns_finite_metrics():
    adapter = SodirAdapter(loader=_FakeLoader(_loader_frame()))
    unified = adapter.fetch(ProductionQuery(regions=["ncs"]))
    fdas_prod = to_fdas_production(unified)
    assert list(fdas_prod.columns) == list(FDAS_PRODUCTION_COLUMNS)

    # pre-tax plumbing only (NOT a published Norway NPV — 78% regime, B3)
    engine = CashflowEngine(AssumptionsManager(), dev_system="subsea15")
    cashflows = engine.generate_monthly_cashflow(
        fdas_prod,
        {"drilling_monthly": {}},
        {"2024-01": 75.0, "2024-02": 76.0},
        datetime(2024, 1, 1),
    )
    assert cashflows
    assert all(np.isfinite(cf.net_cashflow_usd) for cf in cashflows)


def test_concept_screening_returns_ranked_list():
    from worldenergydata.field_development.recommendation import recommend

    fc = sodir_field_to_concept(_processed_field())
    scored = recommend(fc)
    assert isinstance(scored, list) and len(scored) > 0
