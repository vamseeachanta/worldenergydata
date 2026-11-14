"""Staging and provenance preservation for the BSEE ingest transaction."""

from datetime import date

import pytest

from scripts.ingest import bsee_binary_ingest as ingest
from tests.bsee_ingest_support import workspace, write_zip


def test_catalog_serialization_failure_preserves_existing_outputs(
    workspace, monkeypatch
):
    source, project, current = workspace
    write_zip(
        source,
        "bin/borehole/BoreholeRawData.zip",
        {
            "mv_boreholes_all.txt": "API_WELL_NUMBER,WELL_NAME\n001234567890,Alpha\n",
        },
    )
    target = project / "data/modules/bsee/borehole/20261113.csv"
    target.parent.mkdir(parents=True)
    target.write_text("original\n")
    catalog = project / "data/catalog.yaml"
    before = catalog.read_bytes()

    def fail_dump(*args, **kwargs):
        raise RuntimeError("serialization failed")

    monkeypatch.setattr(ingest.yaml, "safe_dump", fail_dump)
    with pytest.raises(RuntimeError, match="serialization failed"):
        ingest.ingest(source, project, current, ["borehole"], date(2026, 11, 13))
    assert catalog.read_bytes() == before
    assert target.read_text() == "original\n"
    assert not list((project / "data").glob("bsee-ingest-*"))


def test_changed_source_does_not_receive_a_stale_provenance_digest(
    workspace, monkeypatch
):
    source, project, current = workspace
    path = source / "bin/war/table.csv"
    path.parent.mkdir(parents=True)
    path.write_text("SN_WAR,REMARK\n001,original\n")
    original = path.read_bytes()
    before = ingest.digest(path)
    catalog = project / "data/catalog.yaml"
    catalog_before = catalog.read_bytes()
    real_tables = ingest.tables

    def changing_tables(path, *args):
        yield from real_tables(path, *args)
        path.write_text("SN_WAR,REMARK\n001,changed\n")

    monkeypatch.setattr(ingest, "tables", changing_tables)
    try:
        with pytest.raises(ValueError, match="Source changed while being read"):
            ingest.ingest(source, project, current, ["war"], date(2026, 11, 13))
        tampered = ingest.digest(path)
        assert tampered != before
        assert catalog.read_bytes() == catalog_before
        assert not (project / "data/modules/bsee").exists()
    finally:
        path.write_bytes(original)
    assert ingest.digest(path) == before
