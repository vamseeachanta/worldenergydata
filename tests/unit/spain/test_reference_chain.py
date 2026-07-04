"""Spain CORES reference-chain tests (#763b)."""

import math

import pandas as pd

from worldenergydata.fdas.adapters.contract import FDAS_PRODUCTION_COLUMNS
from worldenergydata.production.unified.adapters.spain_cores_adapter import (
    SpainCoresAdapter,
)
from worldenergydata.spain.field_concept import build_spain_field_concept
from worldenergydata.spain.reference_chain import run_spain_reference_chain


class FixtureCoresLoader:
    def load_field_production(self, field_name):
        frame = pd.DataFrame(
            [
                {
                    "field_name": field_name,
                    "year": 2024,
                    "month": 1,
                    "oil_bbl": 73.3,
                    "gas_mcf": 0.0,
                },
                {
                    "field_name": field_name,
                    "year": 2024,
                    "month": 2,
                    "oil_bbl": 87.96,
                    "gas_mcf": 0.0,
                },
            ]
        )
        return frame


def _field_meta():
    return {
        "field_name": "Ayoluengo",
        "environment": "onshore",
        "source": "CORES",
    }


def test_spain_field_meta_mapping_builds_sparse_onshore_concept():
    concept = build_spain_field_concept(_field_meta())

    assert concept.name == "Ayoluengo"
    assert concept.region == "spain"
    assert concept.water_depth_m == 0.0
    assert concept.data_source == "CORES"


def test_reference_chain_forces_onshore_dry_system_and_mismatch_flag():
    result = run_spain_reference_chain(
        adapter=SpainCoresAdapter(loader=FixtureCoresLoader()),
        field_meta=_field_meta(),
        field_name="Ayoluengo",
        start="2024-01",
        end="2024-02",
        oil_price_usd_bbl=75.0,
    )

    assert result["economics_label"] == "chain_plumbing_pre_tax"
    assert result["dev_system"] == "dry"
    assert result["pre_tax_metrics"]["onshore_model_mismatch"] is True
    assert result["pre_tax_metrics"]["host_capex_usd"] == 0.0
    assert list(result["fdas_production"].columns) == list(FDAS_PRODUCTION_COLUMNS)
    assert list(result["fdas_production"]["YEAR_MONTH"]) == ["2024-01", "2024-02"]
    assert result["pre_tax_metrics"]["gross_revenue_usd"] > 0.0
    assert math.isfinite(result["pre_tax_metrics"]["net_cashflow_usd"])


def test_sparse_spain_concept_screen_is_deterministic_wiring_only():
    first = run_spain_reference_chain(
        adapter=SpainCoresAdapter(loader=FixtureCoresLoader()),
        field_meta=_field_meta(),
        field_name="Ayoluengo",
    )
    second = run_spain_reference_chain(
        adapter=SpainCoresAdapter(loader=FixtureCoresLoader()),
        field_meta=_field_meta(),
        field_name="Ayoluengo",
    )

    assert first["field_concept"] == build_spain_field_concept(_field_meta())
    assert first["concept_screening_label"] == "wiring_only_onshore_sparse_metadata"
    assert [r.concept_type for r in first["ranked_concepts"]]
    assert [r.concept_type for r in first["ranked_concepts"]] == [
        r.concept_type for r in second["ranked_concepts"]
    ]
