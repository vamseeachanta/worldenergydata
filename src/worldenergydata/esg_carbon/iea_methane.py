"""Dated IEA Methane Tracker evaluation, without downloading or ingesting data.

The evidence snapshot distinguishes the 2025 report from the current combined
product page. Its findings apply to the opened publications, not to the contents
or rights of unopened data files. No network calls or numerical models run here.
See docs/data-sources/iea-methane-tracker-evaluation.md for the evidence boundary.
"""

from dataclasses import dataclass
from enum import Enum


class IntendedUse(str, Enum):
    COUNTRY_REFERENCE = "country_reference"
    FACILITY_EMISSIONS = "facility_emissions"
    ABATEMENT_MODELLING = "abatement_modelling"


class Recommendation(str, Enum):
    CONDITIONAL_ADOPTION = "conditional_adoption"
    UNSUITABLE = "unsuitable"
    DEFERRED = "deferred"


class FindingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    NOT_EVALUATED = "NOT_EVALUATED"
    UNSUITABLE = "UNSUITABLE"


@dataclass(frozen=True)
class SourceEvidence:
    """An opened publication and the section supporting a finding."""

    key: str
    title: str
    url: str
    section: str
    retrieved_on: str


@dataclass(frozen=True)
class Finding:
    key: str
    status: FindingStatus
    detail: str
    source_key: str


@dataclass(frozen=True)
class Assessment:
    """A publication assessment; conditional adoption is not ingestion approval."""

    intended_use: IntendedUse
    recommendation: Recommendation
    checks: tuple[Finding, ...]
    sources: tuple[SourceEvidence, ...]
    evaluated_on: str


# Observation date for the public pages/PDF opened for this evaluation.
# The report's About section identifies its edition; the product's Schedule
# identifies the current release. Editions are not emissions observation years.
_EVALUATED_ON = "2026-10-19"
_SOURCES = (
    SourceEvidence(
        "report_2025",
        "IEA (2025), Global Methane Tracker 2025",
        "https://www.iea.org/reports/global-methane-tracker-2025",
        "About this report; Published; Licence",
        _EVALUATED_ON,
    ),
    SourceEvidence(
        "documentation_2025",
        "IEA (2025), Global Methane Tracker Documentation, 2025 version",
        "https://iea.blob.core.windows.net/assets/"
        "451af9a0-8736-40dc-b843-69275d6fdb07/"
        "GlobalMethaneTracker2025Documentation.pdf",
        "Methane emission estimates; Upstream and downstream oil and gas, pp. 5-8",
        _EVALUATED_ON,
    ),
    SourceEvidence(
        "product_2026",
        "IEA, Methane Tracker Database and Methane Abatement Model (May 2026)",
        "https://www.iea.org/data-and-statistics/data-product/"
        "methane-tracker-database-and-methane-abatement-model",
        "Overview; Data sets; Schedule; Licence; Download sign-in notice",
        _EVALUATED_ON,
    ),
)

# Every finding cites an opened source above. CONFIRMED describes a statement
# in a publication; it never means that an advertised CSV was inspected.
_FINDINGS = (
    Finding(
        "country_scope",
        FindingStatus.CONFIRMED,
        "The product describes country and regional methane estimates; use as "
        "a national reference alongside separately sourced inventories.",
        "product_2026",
    ),
    Finding(
        "historical_data_announced",
        FindingStatus.CONFIRMED,
        "The report announces country-level historical emissions data; the "
        "available year ranges and completeness of the files remain uninspected.",
        "report_2025",
    ),
    Finding(
        "report_licence",
        FindingStatus.CONFIRMED,
        "The report page identifies CC BY 4.0 for the report. This finding "
        "does not assign a licence to database files or model code.",
        "report_2025",
    ),
    Finding(
        "published_file_listing",
        FindingStatus.CONFIRMED,
        "The current product lists Global methane emissions 2025 and Oil and "
        "gas methane emissions 2025 as CSV downloads in its database section.",
        "product_2026",
    ),
    Finding(
        "modelled_estimates",
        FindingStatus.CONFIRMED,
        "The documentation describes country-specific emission intensities "
        "applied to activity data, informed by measurements and satellite data. "
        "These are estimates, not direct measurements of every facility.",
        "documentation_2025",
    ),
    Finding(
        "download_inspection",
        FindingStatus.NOT_EVALUATED,
        "The product displays a sign-in requirement. No account was used and "
        "no published CSV was downloaded or inspected.",
        "product_2026",
    ),
    Finding(
        "database_licence",
        FindingStatus.NOT_EVALUATED,
        "The combined product advertises GPL v3.0 for code and CC BY SA 4.0 "
        "for datasets; its Licence paragraph describes model datasets. "
        "Confirm terms and attribution for each emissions download before reuse; "
        "do not inherit the report licence.",
        "product_2026",
    ),
    Finding(
        "schema_and_units",
        FindingStatus.NOT_EVALUATED,
        "CSV column names, methane mass units, missing-value conventions and "
        "country identifiers require inspection of published files. No schema "
        "or conversion factors are inferred from the explorer's backing service.",
        "product_2026",
    ),
    Finding(
        "historical_coverage",
        FindingStatus.NOT_EVALUATED,
        "The report's historical-data announcement does not establish which "
        "countries, segments or years occur in each published file.",
        "report_2025",
    ),
)


def evaluate_iea_methane_tracker(
    intended_use: IntendedUse | str = IntendedUse.COUNTRY_REFERENCE,
) -> Assessment:
    """Return the fixed, dated source evaluation for a supported intended use.

    Accepts an IntendedUse or its exact string value; unknown values raise
    ValueError. This offline snapshot does not refresh source evidence or accept
    caller assertions as proof that the unresolved ingestion checks have passed.
    """
    use = IntendedUse(intended_use)
    checks = _FINDINGS
    if use is IntendedUse.COUNTRY_REFERENCE:
        recommendation = Recommendation.CONDITIONAL_ADOPTION
    elif use is IntendedUse.FACILITY_EMISSIONS:
        recommendation = Recommendation.UNSUITABLE
        checks += (
            Finding(
                "intended_use",
                FindingStatus.UNSUITABLE,
                "Country and regional estimates cannot supply individual "
                "facility or operator emissions; use a facility-grain source.",
                "product_2026",
            ),
        )
    else:
        recommendation = Recommendation.DEFERRED
        checks += (
            Finding(
                "intended_use",
                FindingStatus.NOT_EVALUATED,
                "The abatement model needs a separate code and dataset rights "
                "review, input review and validation. It was not imported or run.",
                "product_2026",
            ),
        )
    return Assessment(use, recommendation, checks, _SOURCES, _EVALUATED_ON)
