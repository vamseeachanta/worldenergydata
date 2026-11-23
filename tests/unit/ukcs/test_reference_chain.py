"""UKCS NSTA reference-chain tests (#717)."""

import math

import pandas as pd
import pytest

from worldenergydata.fdas.adapters.contract import FDAS_PRODUCTION_COLUMNS
from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter
from worldenergydata.ukcs.production.field_production import UKCSFieldProductionLoader
from worldenergydata.ukcs.reference_chain import (
    build_uk_field_concept,
    run_ukcs_reference_chain,
)


class FixtureNstaLoader:
    def load_field_production(self, field_name):
        normalized = _normalized_nsta_frame()
        return normalized[normalized["field"] == field_name.upper().strip()].copy()

    def load_all_production(self):
        return _normalized_nsta_frame()


def _normalized_nsta_frame():
    raw = pd.DataFrame(
        [
            {
                "FIELDNAME": "FORTIES",
                "PERIODYR": 1975,
                "PERIODMNTH": 9,
                "OILPRODMAS": 1000.0,
                "AGASPROKSM": 25.0,
                "DGASPROKSM": 5.0,
                "WATPRODVOL": 100.0,
            },
            {
                "FIELDNAME": "FORTIES",
                "PERIODYR": 1975,
                "PERIODMNTH": 10,
                "OILPRODMAS": 1100.0,
                "AGASPROKSM": 28.0,
                "DGASPROKSM": 6.0,
                "WATPRODVOL": 120.0,
            },
        ]
    )
    return UKCSFieldProductionLoader().load(raw)


def _field_meta():
    return {
        "field_name": "FORTIES",
        "water_depth_m": 128.0,
        "source": "NSTA",
    }


def test_uk_field_meta_mapping_builds_sparse_concept():
    concept = build_uk_field_concept(_field_meta())

    assert concept.name == "Forties"
    assert concept.region == "uk"
    assert concept.water_depth_m == 128.0
    assert concept.data_source == "NSTA"


def test_sparse_uk_concept_screen_is_deterministic():
    first = run_ukcs_reference_chain(
        adapter=UkcsAdapter(loader=FixtureNstaLoader()),
        field_meta=_field_meta(),
        field_name="Forties",
        start="1975-09",
        end="1975-10",
    )
    second = run_ukcs_reference_chain(
        adapter=UkcsAdapter(loader=FixtureNstaLoader()),
        field_meta=_field_meta(),
        field_name="Forties",
        start="1975-09",
        end="1975-10",
    )

    assert first["field_concept"] == build_uk_field_concept(_field_meta())
    assert [r.concept_type for r in first["ranked_concepts"]]
    assert [r.concept_type for r in first["ranked_concepts"]] == [
        r.concept_type for r in second["ranked_concepts"]
    ]


def test_reference_chain_returns_labeled_finite_pre_tax_metrics_and_zero_royalty():
    result = run_ukcs_reference_chain(
        adapter=UkcsAdapter(loader=FixtureNstaLoader()),
        field_meta=_field_meta(),
        field_name="Forties",
        start="1975-09",
        end="1975-10",
        oil_price_usd_bbl=75.0,
    )

    assert result["economics_label"] == "chain_plumbing_pre_tax"
    assert list(result["fdas_production"].columns) == list(FDAS_PRODUCTION_COLUMNS)
    assert result["pre_tax_metrics"]["months"] >= 2
    assert result["pre_tax_metrics"]["royalty_usd"] == pytest.approx(0.0)
    assert result["pre_tax_metrics"]["gross_revenue_usd"] > 0.0
    assert math.isfinite(result["pre_tax_metrics"]["gross_revenue_usd"])
    assert math.isfinite(result["pre_tax_metrics"]["net_cashflow_usd"])
    assert result["ranked_concepts"]
