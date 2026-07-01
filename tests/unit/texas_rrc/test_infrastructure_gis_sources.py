"""Tests for loading official Texas RRC GIS shapefile ZIPs."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
import shapefile


def _zip_shapefile(base: Path, zip_path: Path) -> None:
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for suffix in (".shp", ".shx", ".dbf"):
            archive.write(base.with_suffix(suffix), base.with_suffix(suffix).name)


def _write_well_zip(root: Path) -> Path:
    base = root / "well001"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POINT)
    writer.field("API", "C")
    writer.field("CNTY_FIPS", "C")
    writer.point(-102.0, 31.0)
    writer.record("42-001-00001-00-00", "1")
    writer.point(-95.5, 31.9)
    writer.record("00130641", "")
    writer.close()
    zip_path = root / "well001.zip"
    _zip_shapefile(base, zip_path)
    return zip_path


def _write_pipeline_zip(root: Path) -> Path:
    base = root / "pipeline001"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POLYLINE)
    writer.field("T4PERMIT", "C")
    writer.field("CNTY_FIPS", "C")
    writer.line([[(-102.0, 30.9), (-102.0, 31.2)]])
    writer.record("T4-12345", "001")
    writer.close()
    zip_path = root / "pipeline001.zip"
    _zip_shapefile(base, zip_path)
    return zip_path


def test_load_well_gis_records_normalizes_api_and_preserves_source(tmp_path):
    from worldenergydata.texas_rrc.infrastructure.gis_sources import (
        load_well_gis_records,
    )

    zip_path = _write_well_zip(tmp_path)

    records = load_well_gis_records(tmp_path)

    assert len(records) == 2
    record = records[0]
    assert record.api_number == "42001000010000"
    assert record.county_fips == "001"
    assert record.latitude == 31.0
    assert record.longitude == -102.0
    assert record.source_file == zip_path.name
    assert records[1].api_number == "42001306410000"
    assert records[1].county_fips == "001"


def test_load_pipeline_gis_records_keeps_polyline_coordinates(tmp_path):
    from worldenergydata.texas_rrc.infrastructure.gis_sources import (
        load_pipeline_gis_records,
    )

    zip_path = _write_pipeline_zip(tmp_path)

    records = load_pipeline_gis_records(tmp_path)

    assert len(records) == 1
    record = records[0]
    assert record.pipeline_identifier == "T4-12345"
    assert record.county_fips == "001"
    assert record.coordinates == ((-102.0, 30.9), (-102.0, 31.2))
    assert record.source_file == zip_path.name


def test_load_gis_records_rejects_remote_paths():
    from worldenergydata.texas_rrc.infrastructure.gis_sources import (
        load_well_gis_records,
    )

    with pytest.raises(ValueError, match="local filesystem"):
        load_well_gis_records("https://example.com/wells.zip")


def test_load_gis_records_reports_malformed_zip(tmp_path):
    from worldenergydata.texas_rrc.infrastructure.gis_sources import (
        GisSourceError,
        load_pipeline_gis_records,
    )

    with ZipFile(tmp_path / "pipeline001.zip", "w", compression=ZIP_DEFLATED) as bad:
        bad.writestr("pipeline001.shp", b"not-a-real-shapefile")

    with pytest.raises(GisSourceError, match="missing required shapefile members"):
        load_pipeline_gis_records(tmp_path)


def test_load_gis_inputs_preserves_good_records_when_one_zip_is_malformed(tmp_path):
    from worldenergydata.texas_rrc.infrastructure.gis_sources import load_gis_inputs

    well_root = tmp_path / "raw" / "gis" / "wells"
    pipeline_root = tmp_path / "raw" / "gis" / "pipelines"
    well_root.mkdir(parents=True)
    pipeline_root.mkdir(parents=True)
    _write_well_zip(well_root)
    _write_pipeline_zip(pipeline_root)
    with ZipFile(well_root / "well999.zip", "w", compression=ZIP_DEFLATED) as bad:
        bad.writestr("well999.shp", b"not-a-real-shapefile")

    result = load_gis_inputs(tmp_path)

    assert len(result.well_gis) == 2
    assert len(result.pipeline_gis) == 1
    assert result.source_gaps == ()
    assert len(result.malformed_source_files) == 1
    assert "well999.zip" in result.malformed_source_files[0]


def test_load_gis_records_rejects_unsafe_zip_member_paths(tmp_path):
    from worldenergydata.texas_rrc.infrastructure.gis_sources import (
        GisSourceError,
        load_well_gis_records,
    )

    with ZipFile(tmp_path / "well001.zip", "w", compression=ZIP_DEFLATED) as bad:
        bad.writestr("../well001.shp", b"")
        bad.writestr("well001.shx", b"")
        bad.writestr("well001.dbf", b"")

    with pytest.raises(GisSourceError, match="unsafe ZIP member path"):
        load_well_gis_records(tmp_path)
