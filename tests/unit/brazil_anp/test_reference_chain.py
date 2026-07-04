"""Brazil ANP reference-chain runner tests (#718)."""

import numpy as np
import pandas as pd

from worldenergydata.brazil_anp.reference_chain import run_brazil_reference_chain
from worldenergydata.field_development.enums import ConceptType
from worldenergydata.production.unified.adapters.brazil_anp_adapter import (
    BrazilAnpAdapter,
)


class FixtureAnpLoader:
    def load_field_production(self, field_name):
        frame = _field_month_frame()
        return frame[frame["field"] == field_name].copy()


def _field_month_frame():
    return pd.DataFrame(
        [
            {
                "field": "TUPI",
                "date": pd.Timestamp("2024-01-01"),
                "year": 2024,
                "month": 1,
                "oil_bbl": 1000.0,
                "gas_mcf": 200.0,
                "water_bbl": 30.0,
                "condensate_bbl": 10.0,
            },
            {
                "field": "TUPI",
                "date": pd.Timestamp("2024-02-01"),
                "year": 2024,
                "month": 2,
                "oil_bbl": 1100.0,
                "gas_mcf": 210.0,
                "water_bbl": 35.0,
                "condensate_bbl": 11.0,
            },
        ]
    )


def _field_meta():
    return {
        "field_name": "TUPI",
        "operator": "Petrobras",
        "region": "brazil",
        "water_depth_m": 2150.5,
        "well_count": 2,
        "first_oil_date": "2010-10-28",
        "source": "anp_fase_desenvolvimento_producao",
    }


def test_reference_chain_runs_production_fdas_cashflow_and_concept_screening():
    result = run_brazil_reference_chain(
        adapter=BrazilAnpAdapter(loader=FixtureAnpLoader()),
        field_meta=_field_meta(),
        field_name="TUPI",
        oil_price_usd_bbl=75.0,
    )

    assert result["field_name"] == "TUPI"
    assert result["economics_label"] == "chain_plumbing_pre_tax"
    assert list(result["fdas_production"]["YEAR_MONTH"]) == ["2024-01", "2024-02"]
    assert result["field_concept"].region == "brazil"
    assert result["ranked_concepts"][0].concept_type == ConceptType.FPSO
    assert result["pre_tax_metrics"]["months"] == 2
    assert np.isfinite(result["pre_tax_metrics"]["net_cashflow_usd"])
