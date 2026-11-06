"""Authority expectations: issue 1325 (2026), Labels, and the HSE data audit.

The audit's International Offshore Safety table explicitly marks UK HSE
offshore statistics as not acquired. Enforcement notices are a separate source.
"""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = "data/modules/hse/offshore/source_registry.json"


def test_contract_identifies_existing_authorities_and_registry():
    contract = json.loads(
        (ROOT / "data/source-refresh-acceptance-contract.json").read_text()
    )
    row = next(row for row in contract["sources"] if row["module_id"] == "hse")
    assert row["source_authority"] == "BSEE; OSHA; EPA (existing datasets)"
    assert row["uk_hse_offshore_statistics_status"] == "not_acquired"
    assert "offshore/statistics.htm" not in row["source_url_or_api"]
    assert row["source_registry"] == REGISTRY


def test_manifest_exposes_authorities_and_acquisition_gap():
    manifest = yaml.safe_load((ROOT / "module-manifest.yaml").read_text())
    row = next(row for row in manifest["modules"] if row["id"] == "hse")
    assert row["source_authorities"] == ["BSEE", "OSHA", "EPA"]
    assert row["uk_hse_offshore_statistics_status"] == "not_acquired"
    assert row["source_registry"] == REGISTRY


def test_schema_resolves_the_same_registry_and_authorities():
    schema_file = ROOT / "data/modules/hse/schema.yaml"
    schema = yaml.safe_load(schema_file.read_text())
    assert schema["actual_authorities"] == ["BSEE", "OSHA", "EPA"]
    assert schema["uk_hse_offshore_statistics_status"] == "not_acquired"
    assert (schema_file.parent / schema["source_registry"]).resolve() == ROOT / REGISTRY


def test_documented_correction_matches_the_actual_contract():
    """Issue 1325 (2026), Current state gives the before; audit gives authorities.

    Compare each documented answer field with the real contract so the worked
    example cannot silently describe a different row from the shipped input.
    """
    text = (ROOT / "docs/hse/source-registry.md").read_text()
    before, after = [
        json.loads(block)
        for block in re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    ]
    assert before["source_authority"] == "UK Health and Safety Executive"
    assert (
        before["source_url_or_api"] == "https://www.hse.gov.uk/offshore/statistics.htm"
    )
    contract = json.loads(
        (ROOT / "data/source-refresh-acceptance-contract.json").read_text()
    )
    row = next(row for row in contract["sources"] if row["module_id"] == "hse")
    assert after == {key: row[key] for key in after}
