"""Offline evaluation oracles from opened IEA publications, with no data fixtures.

Sources are IEA (2025), Global Methane Tracker, About this report; its
Documentation, Methane emission estimates, pp. 5-8; and IEA (May 2026),
Methane Tracker Database and Methane Abatement Model, Overview, Data sets,
and Licence (all retrieved 2026-10-19). Exact links accompany the assessment.
No emissions values, conversion factors or numerical tolerances are assumed.
"""

import json
from dataclasses import FrozenInstanceError, asdict

import pytest

from worldenergydata.esg_carbon import (
    FindingStatus,
    IntendedUse,
    Recommendation,
    evaluate_iea_methane_tracker,
)


def test_country_reference_is_conditional():
    """IEA product Overview describes country estimates; no files were opened."""
    result = evaluate_iea_methane_tracker()
    assert result.intended_use is IntendedUse.COUNTRY_REFERENCE
    assert result.recommendation is Recommendation.CONDITIONAL_ADOPTION


@pytest.mark.parametrize(
    ("use", "expected"),
    [
        ("country_reference", Recommendation.CONDITIONAL_ADOPTION),
        ("facility_emissions", Recommendation.UNSUITABLE),
        ("abatement_modelling", Recommendation.DEFERRED),
    ],
)
def test_intended_use_decisions(use, expected):
    """Independent decision table: country scope fits, facility scope does not;
    abatement needs separate model/rights review (product Overview and Licence).
    """
    assert evaluate_iea_methane_tracker(use).recommendation is expected


@pytest.mark.parametrize("use", ["", "operator", "COUNTRY_REFERENCE", None])
def test_unknown_intended_use_is_rejected(use):
    """Unspecified use must not silently acquire a country-reference decision."""
    with pytest.raises(ValueError):
        evaluate_iea_methane_tracker(use)


@pytest.mark.parametrize(
    "key",
    [
        "country_scope",
        "historical_data_announced",
        "report_licence",
        "published_file_listing",
        "modelled_estimates",
    ],
)
def test_opened_publication_findings_are_confirmed(key):
    """Report About, product Data sets and Documentation pp. 5-8 are evidence."""
    checks = {c.key: c for c in evaluate_iea_methane_tracker().checks}
    assert checks[key].status is FindingStatus.CONFIRMED


@pytest.mark.parametrize(
    "key",
    [
        "download_inspection",
        "database_licence",
        "schema_and_units",
        "historical_coverage",
    ],
)
def test_unopened_data_properties_are_not_evaluated(key):
    """A listing or report licence cannot establish properties of unopened CSVs."""
    checks = {c.key: c for c in evaluate_iea_methane_tracker().checks}
    assert checks[key].status is FindingStatus.NOT_EVALUATED


@pytest.mark.parametrize("use", list(IntendedUse))
def test_findings_keep_sources_and_ingestion_gaps_for_every_use(use):
    """Changing use cannot erase unresolved download/licence/unit evidence."""
    result = evaluate_iea_methane_tracker(use)
    source_ids = {s.key for s in result.sources}
    assert len(source_ids) == len(result.sources)
    assert len({c.key for c in result.checks}) == len(result.checks)
    for check in result.checks:
        assert check.source_key in source_ids
        assert check.detail.strip()
    for source in result.sources:
        assert source.url.startswith("https://")
        assert source.section.strip()
        assert source.title.strip()
        assert source.retrieved_on == "2026-10-19"
    unknowns = {c.key for c in result.checks if c.status is FindingStatus.NOT_EVALUATED}
    assert {
        "download_inspection",
        "database_licence",
        "schema_and_units",
        "historical_coverage",
    } <= unknowns


def test_report_licence_is_separate_from_database_licence():
    """2025 report CC BY does not resolve the combined product's mixed terms."""
    checks = {c.key: c for c in evaluate_iea_methane_tracker().checks}
    assert checks["report_licence"].source_key == "report_2025"
    assert checks["database_licence"].source_key == "product_2026"
    assert checks["report_licence"].source_key != checks["database_licence"].source_key


def test_facility_use_has_an_explicit_scope_failure():
    """Country/regional estimates cannot identify an individual facility."""
    checks = evaluate_iea_methane_tracker("facility_emissions").checks
    assert any(
        c.key == "intended_use" and c.status is FindingStatus.UNSUITABLE for c in checks
    )


def test_abatement_is_deferred_without_importing_the_model():
    """Product Licence separates code and datasets; model integration is untested."""
    checks = evaluate_iea_methane_tracker("abatement_modelling").checks
    assert any(
        c.key == "intended_use" and c.status is FindingStatus.NOT_EVALUATED
        for c in checks
    )


def test_assessment_is_immutable_and_serializable():
    """A caller can export the dated evidence without mutating later results."""
    result = evaluate_iea_methane_tracker()
    with pytest.raises(FrozenInstanceError):
        result.recommendation = Recommendation.UNSUITABLE
    with pytest.raises(FrozenInstanceError):
        result.checks[0].detail = "changed"
    assert isinstance(result.checks, tuple)
    assert isinstance(result.sources, tuple)
    exported = json.loads(json.dumps(asdict(result)))
    assert exported["evaluated_on"] == "2026-10-19"
    assert exported["recommendation"] == "conditional_adoption"
    assert exported["checks"][0]["status"] == "CONFIRMED"
