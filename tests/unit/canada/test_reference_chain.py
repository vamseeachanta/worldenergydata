"""Canada C-NLOER reference-chain tests (#719)."""

import math

import pandas as pd

from worldenergydata.canada.development_wells import DevelopmentWell
from worldenergydata.canada.field_concept import build_canada_field_concept
from worldenergydata.canada.reference_chain import run_canada_reference_chain
from worldenergydata.fdas.adapters.contract import FDAS_PRODUCTION_COLUMNS
from worldenergydata.production.unified.adapters.canada_adapter import CanadaAdapter


class FixtureCnloerLoader:
    def load_field_production(self, field_name):
        return pd.DataFrame(
            [
                {
                    "field_name": field_name,
                    "year": 2024,
                    "month": 1,
                    "oil_bbl": 3_800_000.0,
                    "gas_mcf": 1_500_000.0,
                    "water_bbl": 4_200_000.0,
                    "source": "cnloer",
                },
                {
                    "field_name": field_name,
                    "year": 2024,
                    "month": 2,
                    "oil_bbl": 3_550_000.0,
                    "gas_mcf": 1_420_000.0,
                    "water_bbl": 4_300_000.0,
                    "source": "cnloer",
                },
            ]
        )


def _field_meta():
    return {"field_name": "Hibernia", "operator": "ExxonMobil", "source": "cnloer"}


def test_field_concept_uses_representative_water_depth():
    concept = build_canada_field_concept(_field_meta())
    assert concept.name == "Hibernia"
    assert concept.region == "canada"
    assert concept.water_depth_m == 80.0  # Hibernia GBS, shallow


def test_reference_chain_hibernia_is_dry_gbs_and_revenue_positive():
    result = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta=_field_meta(),
        field_name="Hibernia",
        start="2024-01",
        end="2024-02",
        oil_price_usd_bbl=75.0,
    )

    assert result["economics_label"] == "chain_plumbing_pre_tax"
    # Hibernia is a shallow-water GBS dry-tree field → depth classifier "dry"
    assert result["dev_system"] == "dry"
    assert result["pre_tax_metrics"]["dev_system_source"] == "depth_classifier"
    assert list(result["fdas_production"].columns) == list(FDAS_PRODUCTION_COLUMNS)
    assert list(result["fdas_production"]["YEAR_MONTH"]) == ["2024-01", "2024-02"]
    assert result["pre_tax_metrics"]["gross_revenue_usd"] > 0.0
    assert math.isfinite(result["pre_tax_metrics"]["net_cashflow_usd"])


def test_reference_chain_is_deterministic():
    first = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta=_field_meta(),
        field_name="Hibernia",
    )
    second = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta=_field_meta(),
        field_name="Hibernia",
    )
    assert first["field_concept"] == build_canada_field_concept(_field_meta())
    assert [r.concept_type for r in first["ranked_concepts"]] == [
        r.concept_type for r in second["ranked_concepts"]
    ]


def test_reference_chain_accepts_linked_development_wells():
    """Synthetic linked depths [3, 7] => (3 + 7) / 2 = 5 m; two inventory UWIs.

    Source for middle-pair mean: Python statistics.median documentation (2026),
    https://docs.python.org/3/library/statistics.html#statistics.median.
    The existing production fixture is independent of this depth calculation.
    """
    meta = {"field_name": "Example", "source": "synthetic"}
    wells = [
        DevelopmentWell("example-a", "Example", 3, None, None, "synthetic-wells"),
        DevelopmentWell("example-b", "Example", 7, None, None, "synthetic-wells"),
    ]
    result = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta=meta,
        field_name="Example",
        development_wells=iter(wells),
    )
    concept = result["field_concept"]
    assert concept.water_depth_m == 5.0
    assert concept.num_wells == 2
    assert "water_depth=development_wells_median" in concept.data_source
    assert result["ranked_concepts"]
