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


@pytest.mark.parametrize(
    "metadata_name, production_name, request_name",
    [
        ("Synthetic Alpha", "SYNTHETIC ALPHA", "Synthetic Alpha"),
        ("Synthetic Alpha", "SYNTHETIC ALPHA", "synthetic alpha"),
        ("Synthetic Alpha", "SYNTHETIC ALPHA", "  SYNTHETIC ALPHA \t"),
        ("Synthetic Gross", "SYNTHETIC GROSS", "Synthetic Gross"),
        ("Synthetic Gross", "SYNTHETIC GROSS", "Synthetic Gro\u00df"),
        ("Synthetic Gro\u00df", "SYNTHETIC GRO\u00df", "Synthetic Gross"),
        ("Synthetic Gro\u00df", "SYNTHETIC GRO\u00df", "  Synthetic Gro\u00df \t"),
    ],
)
def test_enriched_metadata_retains_evidence_without_changing_screen_or_economics(
    metadata_name,
    production_name,
    request_name,
):
    import json

    from worldenergydata.ukcs.field_metadata import read_field_metadata

    class SyntheticLoader:
        def load_field_production(self, field_name):
            normalized = _normalized_nsta_frame().assign(field=production_name)
            return normalized[
                normalized["field"].str.strip().str.casefold()
                == field_name.strip().casefold()
            ].copy()

    requested_fields = []

    class RecordingAdapter:
        def fetch(self, query):
            assert query.regions == ["ukcs"]
            requested_fields.append(query.fields)
            return UkcsAdapter(loader=SyntheticLoader()).fetch(query)

    raw = json.dumps(
        {
            "features": [
                {
                    "attributes": {
                        "FIELDNAME": metadata_name,
                        "OBJECTID": 1,
                        "CURR_OPER": "Synthetic Operator",
                        "STATUS": "Producing",
                        "PROD_DATE": "unparsed startup",
                        "DISC_DATE": "unknown",
                    }
                }
            ]
        }
    ).encode()
    meta = read_field_metadata(
        raw,
        request_name,
        source_url="https://example.invalid/0",
        retrieved_at="2026-11-16T00:00:00Z",
    )
    canonical_name = metadata_name.strip().casefold()
    sparse = {"field_name": canonical_name}

    def run(metadata, name=request_name):
        return run_ukcs_reference_chain(
            adapter=RecordingAdapter(),
            field_meta=metadata,
            field_name=name,
        )

    first, second = run(meta), run(meta)
    original = run(sparse, canonical_name)
    assert meta["metadata_evidence"]["match_status"] == "matched"
    assert len(first["unified_production"]) == 2
    assert first["fdas_production"]["YEAR_MONTH"].tolist() == ["1975-09", "1975-10"]
    assert first["pre_tax_metrics"]["gross_revenue_usd"] > 0.0
    pd.testing.assert_frame_equal(
        first["unified_production"], original["unified_production"]
    )
    pd.testing.assert_frame_equal(first["fdas_production"], original["fdas_production"])
    assert requested_fields == [
        [canonical_name],
        [canonical_name],
        [canonical_name],
    ]
    concept = first["field_concept"]
    assert concept.operator == "Synthetic Operator"
    assert concept.region == "uk"
    assert concept.year_first_oil is None
    assert (
        first["metadata_evidence"]
        == second["metadata_evidence"]
        == meta["metadata_evidence"]
    )
    assert first["metadata_label"] == "metadata_screening_only"
    assert first["metadata_evidence"]["recommendation_ready"] is False
    assert first["metadata_evidence"]["fdp_consent"] == "NOT_EVALUATED"
    assert (
        first["ranked_concepts"]
        == second["ranked_concepts"]
        == original["ranked_concepts"]
    )
    assert first["pre_tax_metrics"] == original["pre_tax_metrics"]
    assert original["metadata_evidence"] is None


@pytest.mark.parametrize("metadata_name", ["Synthetic Beta", "", None, 42])
def test_enriched_metadata_mismatch_fails_before_production_fetch(metadata_name):
    from worldenergydata.ukcs.field_metadata import read_field_metadata

    meta = read_field_metadata(
        b'{"features":[{"attributes":{"FIELDNAME":"Synthetic Beta","OBJECTID":1}}]}',
        "Synthetic Beta",
        source_url="https://example.invalid/0",
        retrieved_at="2026-11-16T00:00:00Z",
    )
    meta["field_name"] = metadata_name

    class UnusedAdapter:
        def fetch(self, query):
            raise AssertionError("production fetch must not run")

    with pytest.raises(ValueError, match="metadata field.*production request"):
        run_ukcs_reference_chain(
            adapter=UnusedAdapter(),
            field_meta=meta,
            field_name="Synthetic Alpha",
        )
