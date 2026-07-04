"""Norway SODIR reference-chain tests (#716)."""

import math

import pandas as pd
import pytest

from worldenergydata.common.units import OilUnits
from worldenergydata.fdas.adapters.contract import FDAS_PRODUCTION_COLUMNS
from worldenergydata.production.unified.adapters.sodir_adapter import SodirAdapter
from worldenergydata.sodir.reference_chain import (
    build_norway_field_concept,
    run_norway_reference_chain,
)


class FixtureMonthlyLoader:
    def load_field_production(self, field_name):
        return pd.DataFrame(
            [
                {
                    "field_name": field_name,
                    "year": 2024,
                    "month": 1,
                    "oil_sm3": 1000.0,
                    "gas_sm3": 2_000_000.0,
                    "ngl_sm3": 0.0,
                    "condensate_sm3": 10.0,
                    "water_injected_sm3": 999_999.0,
                    "oil_bbl": 1000.0 * OilUnits.SM3_TO_BBL,
                    "gas_mcf": 70_629.4,
                },
                {
                    "field_name": field_name,
                    "year": 2024,
                    "month": 2,
                    "oil_sm3": 900.0,
                    "gas_sm3": 1_900_000.0,
                    "ngl_sm3": 0.0,
                    "condensate_sm3": 8.0,
                    "water_injected_sm3": 888_888.0,
                    "oil_bbl": 900.0 * OilUnits.SM3_TO_BBL,
                    "gas_mcf": 67_097.93,
                },
            ]
        )


def _processed_field_meta():
    return {
        "field_name": "JOHAN SVERDRUP",
        "operator": "Equinor",
        "water_depth_m": 110.0,
        "production_start_year": 2019,
        "recoverable_oil_mmbbl": 2700.0,
        "recoverable_gas_bcf": 600.0,
        "source": "SODIR",
    }


def test_norway_field_meta_mapping_consumes_processed_field_keys():
    concept = build_norway_field_concept(_processed_field_meta())

    assert concept.name == "JOHAN SVERDRUP"
    assert concept.operator == "Equinor"
    assert concept.region == "norway"
    assert concept.water_depth_m == 110.0
    assert concept.year_first_oil == 2019
    assert concept.recoverable_reserves_mmboe == pytest.approx(2800.0)
    assert concept.data_source == "SODIR"


def test_sparse_norway_concept_screen_is_deterministic():
    concept = build_norway_field_concept(_processed_field_meta())

    first = run_norway_reference_chain(
        adapter=SodirAdapter(loader=FixtureMonthlyLoader()),
        field_meta=_processed_field_meta(),
        field_name="JOHAN SVERDRUP",
        start="2024-01",
        end="2024-02",
    )
    second = run_norway_reference_chain(
        adapter=SodirAdapter(loader=FixtureMonthlyLoader()),
        field_meta=_processed_field_meta(),
        field_name="JOHAN SVERDRUP",
        start="2024-01",
        end="2024-02",
    )

    assert first["field_concept"] == concept
    assert [r.concept_type for r in first["ranked_concepts"]]
    assert [r.concept_type for r in first["ranked_concepts"]] == [
        r.concept_type for r in second["ranked_concepts"]
    ]


def test_reference_chain_returns_labeled_finite_pre_tax_metrics():
    result = run_norway_reference_chain(
        adapter=SodirAdapter(loader=FixtureMonthlyLoader()),
        field_meta=_processed_field_meta(),
        field_name="JOHAN SVERDRUP",
        start="2024-01",
        end="2024-02",
        oil_price_usd_bbl=75.0,
    )

    assert result["economics_label"] == "chain_plumbing_pre_tax"
    assert list(result["fdas_production"].columns) == list(FDAS_PRODUCTION_COLUMNS)
    assert result["pre_tax_metrics"]["months"] >= 2
    assert math.isfinite(result["pre_tax_metrics"]["gross_revenue_usd"])
    assert math.isfinite(result["pre_tax_metrics"]["net_cashflow_usd"])
    assert result["pre_tax_metrics"]["gross_revenue_usd"] > 0.0
    assert result["ranked_concepts"]
