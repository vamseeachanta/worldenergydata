"""Canada C-NLOER reference-chain tests (#719)."""

import math

import pandas as pd
import pytest

from worldenergydata.canada.development_wells import DevelopmentWell
from worldenergydata.canada.field_concept import (
    CANADA_FIELD_CONCEPT,
    build_canada_field_concept,
    resolve_canada_dev_system,
)
from worldenergydata.canada.reference_chain import run_canada_reference_chain
from worldenergydata.fdas.adapters.contract import FDAS_PRODUCTION_COLUMNS
from worldenergydata.fdas.core.config import DEFAULT_ASSUMPTIONS, AssumptionsManager
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
    # Hibernia is explicitly a GBS dry-tree field, independent of its depth.
    assert result["dev_system"] == "dry"
    assert result["pre_tax_metrics"]["dev_system_source"] == "field_concept_override"
    assert result["dev_system_source"] == "field_concept_override"
    assert list(result["fdas_production"].columns) == list(FDAS_PRODUCTION_COLUMNS)
    assert list(result["fdas_production"]["YEAR_MONTH"]) == ["2024-01", "2024-02"]
    assert result["pre_tax_metrics"]["gross_revenue_usd"] > 0.0
    assert math.isfinite(result["pre_tax_metrics"]["net_cashflow_usd"])


@pytest.fixture(params=[0.0, 17.0], ids=["default-capex", "changed-capex"])
def host_assumptions(request, monkeypatch):
    """Exercise exact CAPEX oracles against both default and changed decks."""
    manager = AssumptionsManager()
    manager.assumptions["HOST_CAPEX_MM"] += request.param
    monkeypatch.setattr(
        "worldenergydata.canada.reference_chain.AssumptionsManager", lambda: manager
    )
    return manager


def test_reference_chain_terra_nova_is_fpso_subsea_override(host_assumptions):
    result = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta={
            "field_name": "Terra Nova",
            "operator": "Suncor",
            "source": "cnloer",
        },
        field_name="Terra Nova",
        start="2024-01",
        end="2024-02",
        oil_price_usd_bbl=75.0,
    )

    assert result["dev_system"] == "subsea15"
    assert result["dev_system_source"] == "field_concept_override"
    metrics = result["pre_tax_metrics"]
    assert metrics["dev_system_source"] == "field_concept_override"
    assert metrics["gross_revenue_usd"] > 0.0
    assert math.isfinite(metrics["net_cashflow_usd"])
    # Synthetic 7,350,000 bbl at 75 USD/bbl; subsea15 uses the existing
    # generic 0.188 royalty fraction and the supplied host CAPEX assumptions.
    assert metrics["gross_revenue_usd"] == pytest.approx(551_250_000.0)
    assert metrics["royalty_usd"] == pytest.approx(103_635_000.0)
    # Known engine defect: MM inputs are emitted without conversion in the
    # USD-labelled metric. Compare the supplied deck, not a hard-coded defect.
    assert metrics["host_capex_usd"] == pytest.approx(
        host_assumptions.get("subsea15", "HOST_CAPEX_MM")
    )
    assert result["field_concept"].water_depth_m == 95.0
    assert result["field_concept"].concept_type is None


@pytest.mark.parametrize(
    "field_name, dev_system, royalty_usd",
    [
        ("White Rose", "subsea15", 103_635_000.0),
        ("North Amethyst", "subsea15", 103_635_000.0),
        ("Hebron", "dry", 68_906_250.0),
    ],
)
def test_reference_chain_uses_explicit_field_economics(
    field_name, dev_system, royalty_usd, host_assumptions
):
    result = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta={"field_name": field_name, "source": "cnloer"},
        field_name=field_name,
    )

    assert result["dev_system"] == dev_system
    assert result["dev_system_source"] == "field_concept_override"
    metrics = result["pre_tax_metrics"]
    assert metrics["dev_system_source"] == "field_concept_override"
    assert metrics["royalty_usd"] == pytest.approx(royalty_usd)
    # Native host CAPEX is still in MM despite the existing metric's name.
    assert metrics["host_capex_usd"] == pytest.approx(
        host_assumptions.get(dev_system, "HOST_CAPEX_MM")
    )
    assert result["field_concept"].concept_type is None


@pytest.mark.parametrize(
    "water_depth_m, dev_system, source",
    [
        (80.0, "dry", "depth_classifier"),
        (1170.0, "subsea15", "depth_classifier"),
        (1830.0, "subsea20", "depth_classifier"),
        (None, "subsea15", "missing_depth_default"),
    ],
)
def test_reference_chain_unknown_field_falls_back_to_depth_classifier(
    water_depth_m, dev_system, source
):
    result = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta={
            "field_name": "Bay du Nord",
            "source": "cnloer",
            "water_depth_m": water_depth_m,
        },
        field_name="Bay du Nord",
    )

    assert result["dev_system"] == dev_system
    assert result["dev_system_source"] == source
    assert result["pre_tax_metrics"]["dev_system_source"] == source


@pytest.mark.parametrize(
    "field_name, water_depth_m, dev_system",
    [
        (" HIBERNIA ", 3000.0, "dry"),
        (" hebron ", None, "dry"),
        (" tErRa NoVa ", 95.0, "subsea15"),
        (" WHITE ROSE ", 1.0, "subsea15"),
        (" North Amethyst ", None, "subsea15"),
    ],
)
def test_dev_system_override_normalizes_name_and_takes_precedence(
    field_name, water_depth_m, dev_system
):
    from worldenergydata.canada.field_concept import resolve_canada_dev_system

    assert resolve_canada_dev_system(field_name, water_depth_m) == (
        dev_system,
        "field_concept_override",
    )


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


@pytest.mark.parametrize("field_name", list(CANADA_FIELD_CONCEPT))
def test_field_concept_override_has_checkable_source(field_name):
    source = CANADA_FIELD_CONCEPT[field_name]["source"]
    assert source["title"].strip()
    assert 1980 <= source["year"] <= 2026
    assert source["url"].startswith("https://")


@pytest.mark.parametrize("field_name", ["Hibernia", "Terra Nova", "Bay du Nord"])
def test_reference_chain_discloses_generic_economics(field_name):
    result = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta={"field_name": field_name, "source": "synthetic"},
        field_name=field_name,
    )
    for level in (result, result["pre_tax_metrics"]):
        notes = " ".join(level["economics_limitations"]).lower()
        assert "royalty" in notes and "opex" in notes
        assert "generic bucket defaults" in notes
        assert "not canada fiscal terms" in notes
        assert "host capex" in notes and "mm" in notes and "usd" in notes


@pytest.mark.parametrize("query_name", ["Terra Nova field", "Hibernia"])
def test_reference_chain_rejects_conflicting_field_identity(query_name):
    class NoFetch:
        def fetch(self, query):
            pytest.fail("Conflicting field identity must fail before production fetch")

    with pytest.raises(ValueError, match="field_name.*field_meta"):
        run_canada_reference_chain(
            adapter=NoFetch(),
            field_meta={"field_name": "Terra Nova"},
            field_name=query_name,
        )


def test_reference_chain_accepts_normalized_field_identity():
    result = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta={"field": "  tErRa NoVa  "},
        field_name="Terra Nova",
    )
    assert result["dev_system"] == "subsea15"
    assert result["dev_system_source"] == "field_concept_override"


@pytest.mark.parametrize(
    "key, value",
    [
        ("dev_system", "subesa15"),
        ("dev_system", "default"),
        ("dev_system", "dry"),
        ("concept", "misspelled_concept"),
    ],
)
def test_dev_system_override_rejects_invalid_configuration(monkeypatch, key, value):
    monkeypatch.setitem(CANADA_FIELD_CONCEPT["terra nova"], key, value)
    with pytest.raises(ValueError, match="Invalid Canada field concept"):
        resolve_canada_dev_system("Terra Nova", 95.0)


def test_dev_system_override_tokens_are_engine_buckets():
    for entry in CANADA_FIELD_CONCEPT.values():
        assert entry["dev_system"] in DEFAULT_ASSUMPTIONS["DEV_SYSTEM"]
        assert entry["dev_system"] != "default"


def test_missing_depth_provenance_identifies_default():
    result = run_canada_reference_chain(
        adapter=CanadaAdapter(loader=FixtureCnloerLoader()),
        field_meta={"field_name": "Unknown field"},
        field_name="Unknown field",
    )
    assert result["dev_system"] == "subsea15"
    assert result["dev_system_source"] == "missing_depth_default"
    assert result["pre_tax_metrics"]["dev_system_source"] == "missing_depth_default"
    assert resolve_canada_dev_system("Unknown field", None) == (
        "subsea15",
        "missing_depth_default",
    )


def test_white_rose_bucket_records_extension_scope():
    entry = CANADA_FIELD_CONCEPT["white rose"]
    note = entry["note"].lower()
    assert "west white rose" in note
    assert "fixed wellhead platform" in note
    assert "searose fpso" in note
    assert "bucket" in note
    assert entry["note_source"]["year"] == 2022
    assert entry["note_source"]["url"].startswith("https://")
