"""Source-audit expectations come from the eight-file inventory in issue #1262.

The attribution is documented in data/modules/metocean/README.md at revision
6737bc76d365a4945993bfae96649676b29e855f. That document names workbook-derived
API RP 2MET material but supplies neither an edition nor publication locators.
No numerical engineering examples or values are used in these metadata tests.
"""

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/modules/metocean"
SIDECAR = "table_sources.json"
# Inventory transcribed from issue #1262, independently of the sidecar.
TABLES = (
    "api_rp2met_gom_extremes_by_region.csv",
    "api_rp2met_hurricane_gom_extremes.csv",
    "api_rp2met_us_zone_100yr_waves.csv",
    "api_rp2met_us_zone_100yr_winds.csv",
    "marine_growth_terminal_thickness.csv",
    "metocean_hs_tp_occurrence.csv",
    "metocean_regional_extremes.csv",
    "metocean_temperature_ranges.csv",
)


def test_source_inventory_covers_the_issue_and_external_tables():
    """Each requested table has exactly one record, including absent CSVs."""
    sources = json.loads((DATA / SIDECAR).read_text())
    schema = yaml.safe_load((DATA / "schema.yaml").read_text())
    metadata = json.loads((DATA / "_metadata.json").read_text())
    assert set(sources["tables"]) == set(TABLES)
    assert set(sources["tables"]) == {
        entry["name"]
        for entry in schema["datasets"]
        if entry.get("distributed") is False
    }
    assert set(sources["tables"]) == {
        entry["name"] for entry in metadata["external_datasets"]
    }


@pytest.mark.parametrize("name", TABLES)
def test_unverified_source_is_explicit_without_inventing_a_locator(name):
    """Repository attribution alone cannot establish an edition or table."""
    record = json.loads((DATA / SIDECAR).read_text())["tables"][name]
    assert record["source_document"] == (
        "API RP 2MET, Derivation of Metocean Design and Operating Conditions"
    )
    assert record["attribution_status"] == "repository_attribution_only"
    assert record["edition"] is None
    assert record["table_or_clause"] is None
    assert record["verification_status"] == "NOT_EVALUATED"
    assert record["reason"].strip()
    assert record["required_evidence"].strip()
    assert record["decision_status"] == "maintainer_decision_required"
    assert record["evidence"] == [
        {
            "path": "data/modules/metocean/README.md",
            "revision": "6737bc76d365a4945993bfae96649676b29e855f",
            "scope": "Workbook-derived attribution only; no edition or locator.",
        }
    ]


@pytest.mark.parametrize("name", TABLES)
def test_schema_and_metadata_resolve_to_the_same_source_record(name):
    """Existing catalogue consumers can discover a specific table's audit."""
    schema = yaml.safe_load((DATA / "schema.yaml").read_text())
    metadata = json.loads((DATA / "_metadata.json").read_text())
    for entries in (schema["datasets"], metadata["external_datasets"]):
        entry = next(item for item in entries if item["name"] == name)
        reference = entry["source_record"]
        assert reference == f"{SIDECAR}#/tables/{name}"
        filename, pointer = reference.split("#")
        resolved = json.loads((DATA / filename).read_text())
        for part in pointer.removeprefix("/").split("/"):
            resolved = resolved[part]
        assert resolved["verification_status"] == "NOT_EVALUATED"


def test_source_audit_is_discoverable_in_the_module_documentation():
    """The sidecar is in the file inventory and its unresolved scope is visible."""
    metadata = json.loads((DATA / "_metadata.json").read_text())
    assert {"name": SIDECAR, "path": SIDECAR} in metadata["files"]
    readme = (DATA / "README.md").read_text()
    assert f"[{SIDECAR}]({SIDECAR})" in readme
    assert "NOT_EVALUATED" in readme
    assert "maintainer decision" in readme
