# ABOUTME: Offline contract tests for the field-development provenance register.
# ABOUTME: Keep publication metadata distinct from engineering qualification.
"""Categorical expectations come from the register's cited code and sources.

No engineering calculation is added, so no numerical worked example applies.
The DEXPI publisher's Specifications page identifies a publication; it does
not qualify this adapter. The pack's U1 records the unresolved clause review.
"""

import json
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "src/worldenergydata/field_development/docs"


@pytest.fixture
def register():
    return json.loads((DOCS / "standards-provenance.json").read_text(encoding="utf-8"))


def test_register_covers_each_requested_claim(register):
    assert register["schema_version"] == "1"
    assert set(register["claims"]) == {
        "liquid_velocity_screen",
        "dexpi_structure",
        "iso_data_integration",
        "symbol_style",
    }


@pytest.mark.parametrize(
    "claim_id",
    [
        "liquid_velocity_screen",
        "dexpi_structure",
        "iso_data_integration",
        "symbol_style",
    ],
)
def test_unverified_applicability_cannot_be_read_as_clearance(register, claim_id):
    claim = register["claims"][claim_id]
    assert claim["applicability_status"] == "UNVERIFIED"
    assert claim["conformity_check"] == "NOT_EVALUATED"
    assert claim["governing_edition"] is None
    assert claim["governing_clause"] is None
    assert claim["remaining_evidence"]
    assert claim["source_id"] in register["sources"]


@pytest.mark.parametrize(
    "claim_id",
    [
        "liquid_velocity_screen",
        "dexpi_structure",
        "iso_data_integration",
        "symbol_style",
    ],
)
def test_code_evidence_resolves_offline(register, claim_id):
    for evidence in register["claims"][claim_id]["code_evidence"]:
        path = ROOT / evidence["path"]
        assert path.is_file()
        assert evidence["anchor"] in path.read_text(encoding="utf-8")


def test_metadata_verification_has_an_open_publisher_locator(register):
    source = register["sources"]["dexpi_pid"]
    assert source["metadata_status"] == "VERIFIED"
    assert source["title"] == "DEXPI P&ID Specification"
    assert source["edition"] == "1.4"
    assert source["url"] == "https://dexpi.org/specifications/"
    assert source["locator"] == "DEXPI P&ID Specification 1.4"
    assert source["access_status"] == "OPENED"
    assert date.fromisoformat(source["checked_on"])
    assert register["claims"]["dexpi_structure"]["applicability_status"] == "UNVERIFIED"


@pytest.mark.parametrize("source_id", ["iso_15926", "isa_symbols", "erosion_basis"])
def test_unverified_sources_do_not_supply_verified_bibliography(register, source_id):
    source = register["sources"][source_id]
    assert source["metadata_status"] == "UNVERIFIED"
    assert source["title"] is None
    assert source["edition"] is None
    assert source["reason"]


def test_sidecar_scope_does_not_promote_heuristics_to_standard_values(register):
    claims = register["claims"]
    erosion = claims["liquid_velocity_screen"]
    assert erosion["basis"] == "CONFIGURABLE_HEURISTIC"
    assert erosion["citation_sidecar"] == "NO_STANDARDS_DERIVATION_ESTABLISHED"
    for claim_id in ("dexpi_structure", "iso_data_integration", "symbol_style"):
        assert claims[claim_id]["citation_sidecar"] == "NOT_A_NUMERIC_CALCULATION"


def test_pack_links_register_and_explanation():
    pack = (DOCS / "agent-pack.md").read_text(encoding="utf-8")
    assert "[standards provenance](standards-provenance.md)" in pack
    explanation = (DOCS / "standards-provenance.md").read_text(encoding="utf-8")
    assert "[machine-readable register](standards-provenance.json)" in explanation
    assert "UNVERIFIED" in explanation
    assert "NOT_EVALUATED" in explanation
