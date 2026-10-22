"""UKCS NSTA reference-chain tests (#717)."""

import math
from unittest.mock import Mock

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
        drilling_timeline={"drilling_monthly": {"1975-08": 1.0}},
        adapter=UkcsAdapter(loader=FixtureNstaLoader()),
        field_meta=_field_meta(),
        field_name="Forties",
        start="1975-09",
        end="1975-10",
    )
    second = run_ukcs_reference_chain(
        drilling_timeline={"drilling_monthly": {"1975-08": 1.0}},
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
        drilling_timeline={"drilling_monthly": {"1975-08": 1.0}},
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


@pytest.mark.parametrize("timeline", [None, {}, {"drilling_monthly": {}}])
def test_missing_drilling_timeline_is_refused(timeline):
    """Issue 1284: absence of drilling costs is unknown, never established zero."""
    adapter = Mock()
    with pytest.raises(ValueError, match="drilling"):
        run_ukcs_reference_chain(
            adapter=adapter,
            field_meta={},
            field_name="Synthetic",
            drilling_timeline=timeline,
        )
    adapter.fetch.assert_not_called()


def test_empty_production_is_refused():
    """An unmatched field cannot establish first oil or evaluated economics."""
    with pytest.raises(ValueError, match="production is empty"):
        run_ukcs_reference_chain(
            adapter=UkcsAdapter(loader=FixtureNstaLoader()),
            field_meta={},
            field_name="Synthetic",
            drilling_timeline={"drilling_monthly": {"2024-01": 1.0}},
        )


def test_drilling_timeline_reaches_cashflow_engine(monkeypatch):
    """The supplied calendar/day mapping must reach the engine unchanged.

    This checks capital-input wiring, without qualifying inherited cost units.
    """
    from worldenergydata.fdas.analysis.cashflow import CashflowEngine

    captured = []
    original = CashflowEngine.generate_monthly_cashflow

    def capture(self, production, timeline, prices, first_oil):
        captured.append(timeline)
        return original(self, production, timeline, prices, first_oil)

    monkeypatch.setattr(CashflowEngine, "generate_monthly_cashflow", capture)
    timeline = {"drilling_monthly": {"1975-08": 1.0}}
    run_ukcs_reference_chain(
        adapter=UkcsAdapter(loader=FixtureNstaLoader()),
        field_meta=_field_meta(),
        field_name=_field_meta()["field_name"],
        drilling_timeline=timeline,
    )
    assert captured == [timeline]
    assert captured[0] is timeline


@pytest.mark.parametrize(
    "monthly",
    [
        {"bad": 1.0},
        {"2024-01": -1.0},
        {"2024-01": float("nan")},
        {"2024-01": float("inf")},
        {"2024-01": 0.0},
        {"2024-01": True},
    ],
)
def test_invalid_drilling_timeline_is_refused(monthly):
    """Issue 1284 requires a finite positive effort basis, with calendar months."""
    with pytest.raises((TypeError, ValueError), match="drilling_monthly"):
        run_ukcs_reference_chain(
            adapter=Mock(),
            field_meta={},
            field_name="Synthetic",
            drilling_timeline={"drilling_monthly": monthly},
        )
