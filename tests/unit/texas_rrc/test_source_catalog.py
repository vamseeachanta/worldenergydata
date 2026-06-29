"""Tests for the Texas RRC source catalog and storage contract."""

from pathlib import Path

import pytest


REQUIRED_SOURCE_IDS = {
    "production_pdq",
    "wellbore_query",
    "drilling_permits",
    "completion_data",
    "directional_surveys",
    "well_gis_layers",
    "pipeline_gis_layers",
    "field_lease_operator",
    "rrc_ewa_lease_query_validation",
    "patchops_rrc_validation",
}

REQUIRED_SOURCE_FIELDS = {
    "source_url",
    "format",
    "refresh_cadence",
    "raw_path",
    "normalized_path",
    "curated_path",
    "availability_status",
    "source_of_record",
    "caveats",
}


def test_source_catalog_declares_required_lifecycle_sources():
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    catalog = load_source_catalog()

    assert REQUIRED_SOURCE_IDS.issubset(catalog)


def test_source_catalog_entries_have_required_contract_fields():
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    catalog = load_source_catalog()

    for source_id in REQUIRED_SOURCE_IDS:
        entry = catalog[source_id]
        assert REQUIRED_SOURCE_FIELDS.issubset(entry)
        assert entry["source_url"]
        assert entry["format"]
        assert entry["refresh_cadence"]
        assert entry["availability_status"] in {
            "available",
            "partial",
            "validation_only",
        }
        assert isinstance(entry["source_of_record"], bool)
        assert entry["caveats"]


def test_source_catalog_paths_stay_under_texas_rrc_ace_root():
    from worldenergydata.texas_rrc.source_catalog import (
        SOURCE_CATALOG_ROOT,
        load_source_catalog,
    )

    catalog = load_source_catalog()

    assert SOURCE_CATALOG_ROOT == Path(
        "/mnt/ace/worldenergydata/data/modules/texas_rrc"
    )
    for entry in catalog.values():
        for field in ("raw_path", "normalized_path", "curated_path"):
            path = Path(entry[field])
            assert path.is_absolute()
            assert path.is_relative_to(SOURCE_CATALOG_ROOT)


def test_source_catalog_rejects_paths_outside_texas_rrc_ace_root():
    from worldenergydata.texas_rrc.source_catalog import validate_source_catalog

    invalid_catalog = {
        "bad_source": {
            "source_url": "https://www.rrc.texas.gov/",
            "format": "csv",
            "refresh_cadence": "nightly",
            "raw_path": "/tmp/raw",
            "normalized_path": "/mnt/ace/worldenergydata/data/modules/texas_rrc/normalized/bad",
            "curated_path": "/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/bad",
            "availability_status": "available",
            "source_of_record": True,
            "caveats": "test fixture",
        }
    }

    with pytest.raises(ValueError, match="must stay under"):
        validate_source_catalog(invalid_catalog)


def test_source_catalog_marks_imaged_and_partial_lifecycle_sources():
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    catalog = load_source_catalog()

    assert catalog["directional_surveys"]["availability_status"] == "partial"
    assert "PDF" in catalog["directional_surveys"]["caveats"]
    assert catalog["completion_data"]["availability_status"] == "partial"
    assert "forms" in catalog["completion_data"]["caveats"].lower()


def test_patchops_is_validation_surface_not_source_of_record():
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    catalog = load_source_catalog()
    patchops = catalog["patchops_rrc_validation"]

    assert patchops["availability_status"] == "validation_only"
    assert patchops["source_of_record"] is False
    assert set(patchops["validates"]) == {
        "wellbore_query",
        "production_pdq",
        "pipeline_gis_layers",
    }


def test_rrc_ewa_lease_query_is_validation_surface_not_copied_scraper_code():
    from worldenergydata.texas_rrc.source_catalog import load_source_catalog

    catalog = load_source_catalog()
    ewa = catalog["rrc_ewa_lease_query_validation"]

    assert ewa["availability_status"] == "validation_only"
    assert ewa["source_of_record"] is False
    assert set(ewa["validates"]) == {
        "wellbore_query",
        "production_pdq",
    }
    assert "derrickturk/rrc-scraper" in ewa["reference_url"]
    assert "do not copy code" in ewa["caveats"]


def test_source_catalog_docs_exist_and_label_partial_sources():
    source_doc = Path("docs/data-sources/onshore/texas-rrc/source-catalog.md")
    storage_doc = Path("docs/data-sources/onshore/texas-rrc/storage-contract.md")

    assert source_doc.exists()
    assert storage_doc.exists()

    source_text = source_doc.read_text(encoding="utf-8")
    storage_text = storage_doc.read_text(encoding="utf-8")

    assert "directional surveys" in source_text.lower()
    assert "PDF" in source_text
    assert "PatchOps" in source_text
    assert "RRC EWA" in source_text
    assert "/mnt/ace/worldenergydata/data/modules/texas_rrc" in storage_text
