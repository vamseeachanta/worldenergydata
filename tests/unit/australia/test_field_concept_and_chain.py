"""Australia FieldConcept + screening-only reference-chain tests (#721)."""

from worldenergydata.australia.field_concept import build_australia_field_concept
from worldenergydata.australia.metadata.field_metadata_loader import (
    AustraliaFieldMetadataLoader,
)
from worldenergydata.australia.reference_chain import run_australia_reference_chain
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    dev_system_from_water_depth_m,
)
from worldenergydata.production.unified.adapters.australia_adapter import (
    AustraliaAdapter,
)


def _kingfish_meta():
    return AustraliaFieldMetadataLoader().field_meta("Kingfish")


def test_metadata_fixture_is_cc_by_licensed():
    metadata = AustraliaFieldMetadataLoader().metadata()
    assert metadata["license"] == "CC-BY-4.0"
    assert "attribution" in metadata


def test_field_concept_from_datavic_metadata():
    concept = build_australia_field_concept(_kingfish_meta())
    assert concept.name == "Kingfish"
    assert concept.region == "australia"
    assert concept.water_depth_m == 78.0


def test_shallow_gippsland_field_classifies_dry_not_subsea():
    # The #721 dev_system caveat: offshore != subsea. Kingfish ~78 m -> ~256 ft
    # -> below the 500 ft dry cutoff -> "dry".
    assert dev_system_from_water_depth_m(78.0) == "dry"


def test_screening_only_chain_runs_recommend_and_flags_no_production():
    result = run_australia_reference_chain(
        adapter=AustraliaAdapter(),
        field_meta=_kingfish_meta(),
        field_name="Kingfish",
    )

    # concept screening IS the real deliverable
    assert [r.concept_type for r in result["ranked_concepts"]]
    # dev_system derived from depth, not hardcoded
    assert result["dev_system"] == "dry"
    # production honesty labels
    assert result["production_available"] is False
    assert (
        result["concept_screening_label"] == "fieldconcept_screening_only_no_production"
    )
    assert result["economics_label"] == "no_production_source_placeholder"
    # no production -> zero-month, zero-revenue cashflow
    assert result["pre_tax_metrics"]["months"] == 0
    assert result["pre_tax_metrics"]["gross_revenue_usd"] == 0.0


def test_chain_is_deterministic():
    first = run_australia_reference_chain(
        adapter=AustraliaAdapter(), field_meta=_kingfish_meta(), field_name="Kingfish"
    )
    second = run_australia_reference_chain(
        adapter=AustraliaAdapter(), field_meta=_kingfish_meta(), field_name="Kingfish"
    )
    assert [r.concept_type for r in first["ranked_concepts"]] == [
        r.concept_type for r in second["ranked_concepts"]
    ]
