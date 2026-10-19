"""Sourced technical vocabulary with editorial role and artifact mappings.

Sources establish tool capabilities and terminology, not hiring demand. Role
families, keyword aliases and proposed evidence artifacts are curated research
aids. Their presence does not assert proficiency or a completed demonstration.
No engineering coefficients, acceptance limits or suitability scores are used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    """Public documentation supporting technical vocabulary."""

    id: str
    title: str
    url: str
    section: str
    edition: str


@dataclass(frozen=True)
class Skill:
    """Technical concept with curated literal aliases, not a proficiency test."""

    id: str
    title: str
    keywords: tuple[str, ...]
    source_id: str


@dataclass(frozen=True)
class Artifact:
    """Proposed evidence to build; a catalog entry is not completion evidence."""

    id: str
    description: str
    skill_ids: tuple[str, ...]


@dataclass(frozen=True)
class Role:
    """Editorial role family mapped to technical skills and proposed evidence."""

    id: str
    title: str
    skill_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]


@dataclass(frozen=True)
class SkillHit:
    """Observed aliases of a skill, ordered as in the catalog."""

    skill_id: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class RoleMatch:
    """Literal text evidence for a role family, without a ranking or score."""

    role_id: str
    hits: tuple[SkillHit, ...]


# Editions and sections were read from the linked public documentation.
# Unversioned web documentation was retrieved on 2026-10-19.
SOURCES = (
    Source(
        "openroad",
        "OpenROAD documentation",
        "https://openroad.readthedocs.io/en/latest/",
        "Introduction; OpenROAD application and flow",
        "Unversioned web documentation, retrieved 2026-10-19",
    ),
    Source(
        "openlane",
        "OpenLane documentation: Using PDKs",
        "https://openlane2.readthedocs.io/en/latest/usage/about_pdks.html",
        "Using PDKs; Specifying your PDK",
        "Unversioned web documentation, retrieved 2026-10-19",
    ),
    Source(
        "klayout_python",
        "KLayout documentation: Programming Python scripts",
        "https://www.klayout.de/doc-qt5/programming/python.html",
        "Python macros and the database API",
        "Unversioned web documentation, retrieved 2026-10-19",
    ),
    Source(
        "klayout_drc",
        "KLayout documentation: Design Rule Checks (DRC) Basics",
        "https://www.klayout.de/doc-qt5/manual/drc_basic.html",
        "Basic scripts; width and space checks; report database",
        "Unversioned web documentation, retrieved 2026-10-19",
    ),
    Source(
        "elmer_models",
        "Elmer Models Manual",
        "https://www.nic.funet.fi/pub/sci/physics/elmer/doc/ElmerModelsManual.pdf",
        "Heat Equation; Linear Elasticity, introduction and theory",
        "January 20, 2026; software version 26.1",
    ),
)

# Each source_id identifies the supporting document above. Aliases are editorial
# search terms, not published requirements for any particular job or process.
SKILLS = (
    Skill(
        "digital_flow",
        "Digital physical implementation",
        ("rtl to gds", "rtl to gdsii", "openroad", "openlane"),
        "openroad",
    ),
    Skill(
        "process_design_kit",
        "Process design kit configuration",
        ("pdk", "process design kit"),
        "openlane",
    ),
    Skill(
        "layout_scripting",
        "Scripted layout database automation",
        ("klayout", "python scripting", "layout automation"),
        "klayout_python",
    ),
    Skill(
        "design_rules",
        "Geometric design rule checking",
        ("drc", "design rule check", "design rule checking"),
        "klayout_drc",
    ),
    Skill(
        "heat_transfer",
        "Finite element heat transfer",
        ("heat transfer", "heat equation", "thermal simulation"),
        "elmer_models",
    ),
    Skill(
        "linear_elasticity",
        "Linear elastic solid mechanics",
        ("linear elasticity", "solid mechanics", "elastic deformation"),
        "elmer_models",
    ),
    Skill(
        "thermal_stress",
        "Thermomechanical stress",
        ("thermal stress", "thermal stresses", "thermomechanical"),
        "elmer_models",
    ),
)

ARTIFACTS = (
    Artifact(
        "rtl_to_gds_report",
        "Reproducible digital flow with PDK provenance and timing/area reports",
        ("digital_flow", "process_design_kit"),
    ),
    Artifact(
        "layout_round_trip",
        "Parameterized layout export/import with geometry invariants and metadata",
        ("layout_scripting", "process_design_kit"),
    ),
    Artifact(
        "design_rule_report",
        "Scripted geometric rule report with documented process-rule provenance",
        ("design_rules", "process_design_kit"),
    ),
    Artifact(
        "thermal_benchmark",
        "Package heat-transfer case with sourced properties and mesh convergence",
        ("heat_transfer",),
    ),
    Artifact(
        "thermomechanical_benchmark",
        "Package elastic/thermal-stress case with boundary conditions and reference",
        ("linear_elasticity", "thermal_stress"),
    ),
)

ROLES = (
    Role(
        "physical_design",
        "ASIC physical design",
        ("digital_flow", "process_design_kit"),
        ("rtl_to_gds_report",),
    ),
    Role(
        "layout_automation",
        "CAD/layout automation",
        ("layout_scripting", "process_design_kit"),
        ("layout_round_trip",),
    ),
    Role(
        "physical_verification",
        "Physical design rule verification",
        ("design_rules", "process_design_kit"),
        ("design_rule_report",),
    ),
    Role(
        "packaging_thermal",
        "Packaging thermal simulation",
        ("heat_transfer",),
        ("thermal_benchmark",),
    ),
    Role(
        "packaging_mechanical",
        "Packaging thermomechanical simulation",
        ("linear_elasticity", "thermal_stress"),
        ("thermomechanical_benchmark",),
    ),
)


def _tokens(text: str) -> str:
    """Treat punctuation and whitespace as separators for ASCII technical terms."""
    return " " + " ".join(re.findall(r"[a-z0-9]+", text.casefold())) + " "


def match_roles(text: str) -> tuple[RoleMatch, ...]:
    """Return all role families having any complete keyword phrase in text.

    Results follow catalog order. Evidence retains every matching alias once,
    regardless of repetitions. Case, whitespace and punctuation are normalized;
    substrings inside tokens do not match. No stemming, semantic inference or
    negation handling is performed. Generic terms may match unrelated domains.
    The caller must review context before drawing any career or portfolio claim.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    normalized = _tokens(text)
    hits = {}
    for skill in SKILLS:
        keywords = tuple(
            keyword for keyword in skill.keywords if _tokens(keyword) in normalized
        )
        if keywords:
            hits[skill.id] = SkillHit(skill.id, keywords)
    matches = []
    for role in ROLES:
        role_hits = tuple(
            hits[skill_id] for skill_id in role.skill_ids if skill_id in hits
        )
        if role_hits:
            matches.append(RoleMatch(role.id, role_hits))
    return tuple(matches)
