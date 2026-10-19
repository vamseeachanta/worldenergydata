"""Synthetic text cases checked by manual keyword and role enumeration.

The expected sets below are editorial taxonomy contracts, not measured hiring
statistics or engineering acceptance limits. Each test states its evidence;
no expected value is computed by the matching implementation.
"""

from dataclasses import FrozenInstanceError

import pytest

from worldenergydata.semiconductor.taxonomy import (
    ARTIFACTS,
    ROLES,
    SKILLS,
    SOURCES,
    match_roles,
)


def test_catalog_references_are_complete_and_unique():
    """Every curated entry has an unambiguous source and resolvable references."""
    sources = {source.id: source for source in SOURCES}
    skills = {skill.id: skill for skill in SKILLS}
    artifacts = {artifact.id: artifact for artifact in ARTIFACTS}
    roles = {role.id: role for role in ROLES}
    assert len(sources) == len(SOURCES)
    assert len(skills) == len(SKILLS)
    assert len(artifacts) == len(ARTIFACTS)
    assert len(roles) == len(ROLES)
    for source in SOURCES:
        assert source.title and source.section and source.edition
        assert source.url.startswith("https://")
    for skill in SKILLS:
        assert skill.source_id in sources
        assert skill.keywords and all(skill.keywords)
        assert len(set(skill.keywords)) == len(skill.keywords)
    for artifact in ARTIFACTS:
        assert artifact.description
        assert artifact.skill_ids
        assert set(artifact.skill_ids) <= skills.keys()
    for role in ROLES:
        assert role.title
        assert role.skill_ids and role.artifact_ids
        assert set(role.skill_ids) <= skills.keys()
        assert set(role.artifact_ids) <= artifacts.keys()
        demonstrated = {
            skill_id
            for artifact_id in role.artifact_ids
            for skill_id in artifacts[artifact_id].skill_ids
        }
        assert set(role.skill_ids) <= demonstrated
    assert {skill.source_id for skill in SKILLS} == sources.keys()
    assert {skill_id for role in ROLES for skill_id in role.skill_ids} == skills.keys()


def test_role_to_artifact_contract():
    """Manual portfolio mapping: each role requires its corresponding demo."""
    assert {role.id: role.artifact_ids for role in ROLES} == {
        "physical_design": ("rtl_to_gds_report",),
        "layout_automation": ("layout_round_trip",),
        "physical_verification": ("design_rule_report",),
        "packaging_thermal": ("thermal_benchmark",),
        "packaging_mechanical": ("thermomechanical_benchmark",),
    }


def test_catalog_is_immutable():
    """A caller cannot alter the shared role definitions between scans."""
    role = next(role for role in ROLES if role.id == "physical_design")
    with pytest.raises(FrozenInstanceError):
        role.title = "changed"


def test_explicit_terms_return_all_roles_and_keyword_evidence():
    """Hand enumeration: OpenROAD -> digital flow; Python scripting -> layout.

    The synthetic text contains both exact aliases and no verification or
    simulation alias, so precisely these role and skill pairs must appear.
    """
    matches = match_roles("OpenROAD experience; Python scripting for layouts.")
    assert {match.role_id for match in matches} == {
        "physical_design",
        "layout_automation",
    }
    evidence = {
        match.role_id: {hit.skill_id: hit.keywords for hit in match.hits}
        for match in matches
    }
    assert evidence == {
        "physical_design": {"digital_flow": ("openroad",)},
        "layout_automation": {"layout_scripting": ("python scripting",)},
    }


def test_shared_thermal_stress_evidence_is_not_lost():
    """Heat transfer selects thermal; thermal stress selects mechanical.

    Both are explicit phrases from the synthetic input. Their presence does
    not establish solver experience, suitability or an engineering pass.
    """
    matches = match_roles("Heat transfer and thermal stress analysis")
    assert {match.role_id for match in matches} == {
        "packaging_thermal",
        "packaging_mechanical",
    }
    assert {hit.skill_id: hit.keywords for match in matches for hit in match.hits} == {
        "heat_transfer": ("heat transfer",),
        "thermal_stress": ("thermal stress",),
    }


@pytest.mark.parametrize(
    "text", ["RTL-to-GDS", "rtl_to_gds", "RTL / TO / GDS", "rtl\n to\t gds"]
)
def test_phrase_separators_and_case(text):
    """All synthetic spellings tokenize to the same literal phrase."""
    matches = match_roles(text)
    assert tuple(match.role_id for match in matches) == ("physical_design",)
    assert matches[0].hits[0].keywords == ("rtl to gds",)


@pytest.mark.parametrize(
    "text", ["", "  \t\n", "offshore engineering", "OpenROADmap", "DRCish"]
)
def test_no_keyword_or_substring_match(text):
    """None of these synthetic inputs contains a complete catalog keyword."""
    assert match_roles(text) == ()


def test_repeated_keyword_has_one_evidence_entry():
    """Manual deduplication: DRC occurs repeatedly; it remains one alias."""
    matches = match_roles("DRC, drc, DRC")
    assert tuple(match.role_id for match in matches) == ("physical_verification",)
    assert matches[0].hits[0].keywords == ("drc",)


def test_multiple_aliases_are_preserved_in_catalog_order():
    """OpenROAD and OpenLane are distinct observed aliases of digital flow."""
    matches = match_roles("OpenLane and OpenROAD")
    assert matches[0].hits[0].keywords == ("openroad", "openlane")
    assert matches == match_roles("OpenROAD and OpenLane")


def test_negated_and_generic_terms_remain_literal_evidence():
    """A lexical scan cannot infer negation or semiconductor specialization."""
    matches = match_roles("No DRC required; heat transfer in buildings")
    assert {match.role_id for match in matches} == {
        "physical_verification",
        "packaging_thermal",
    }


@pytest.mark.parametrize("text", [None, b"DRC", ["OpenROAD"]])
def test_non_text_is_rejected(text):
    with pytest.raises(TypeError, match="text must be a string"):
        match_roles(text)
