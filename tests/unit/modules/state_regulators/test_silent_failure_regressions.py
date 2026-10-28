"""Independent hand checks for the remaining issue #1301 failure paths.

All identifiers and counts below are discrete synthetic examples, not physical
acceptance limits. Existing fixtures provide schema and parser-format evidence.
"""

from pathlib import Path

import pandas as pd
import pytest

from tests.unit.modules.state_regulators.test_colorado_ecmc_observations import (
    SETTINGS,
    _production_rows,
    _wells,
)
from worldenergydata.modules.state_regulators.colorado_ecmc import (
    facility_detail,
    facility_detail_ingest,
    facility_detail_pipeline,
    parsers,
    pipeline,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.normalization import (
    clean_int,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.source_discovery import (
    build_facility_detail_url,
)
from worldenergydata.modules.state_regulators.kansas_kgs import parsers as ks
from worldenergydata.modules.state_regulators.kansas_kgs import pipeline as ks_pipeline
from worldenergydata.modules.state_regulators.oklahoma_occ import parsers as ok

FIXTURE = Path("tests/fixtures/colorado_ecmc/facility_detail_12339345_excerpt.html")


def test_sf4_unknown_sidetrack_is_not_invented():
    """The fixture contains a wellbore label but no qualified API12 mapping.

    Expected API12 is missing; appending zeroes would invent that mapping.
    """
    parsed = facility_detail.parse_facility_detail_html(FIXTURE.read_text())
    assert parsed["api12"].isna().all()
    assert parsed["api12_status"].eq("NOT_EVALUATED").all()
    assert parsed["wellbore"].notna().all()


def test_sf4_distinct_wellbore_contexts_preserved():
    """Two literal wellbore blocks carry different labels; neither may use the other."""
    blocks = []
    for label in ["01", "02"]:
        blocks.append(
            f'<div class="accordion"><div class="accordion-head">Wellbore #{label}</div>'
            '<div class="accordion2"><table><tr><td>Initial Test Data</td></tr>'
            "<tr><td>Test Type</td><td>Measure</td></tr>"
            "<tr><td>CASING_PRESS</td><td>1</td></tr></table></div></div>"
        )
    parsed = facility_detail.parse_facility_detail_html("".join(blocks))
    assert parsed["wellbore"].tolist() == ["01", "02"]


def test_sf4_ambiguous_source_rows_are_rejected():
    """Two different facilities sharing one request fragment cannot select a winner."""
    row = {
        "API": "12300001",
        "API_County": "123",
        "API_Seq": "00001",
        "API_Label": "05-123-00001",
        "Facil_Id": "1",
        "Field_Name": "field",
        "Max_MD": None,
        "Max_TVD": None,
    }
    wells = pd.DataFrame([row, {**row, "Facil_Id": "2"}])
    with pytest.raises(ValueError, match="ambiguous"):
        facility_detail_ingest.build_facility_detail_source_list(
            wells, {"allow_full_source_list": True}
        )


def test_sf4_discovery_does_not_discard_sidetrack():
    """A nonzero suffix cannot be represented by a county/sequence-only URL."""
    with pytest.raises(ValueError, match="sidetrack"):
        build_facility_detail_url("051230000101")


def production_case():
    return _production_rows(
        [
            {
                "api12": "051233249800",
                "api10": "0512332498",
                "facility_id": "420193",
                "report_year": 2025,
                "report_month": 1,
                "test_date": "2025-01-31",
                "formation_code": "formation",
                "gas_pressure_tubing_psig": 1,
            }
        ]
    )


def test_sf5_formation_does_not_become_field():
    """A missing field stays missing; a formation is a different named attribute."""
    wells = _wells()
    wells["field"] = pd.NA
    observations = parsers.build_pressure_observations(
        production_case(), wells, SETTINGS
    )
    assert observations["field"].isna().all()
    assert observations["formation_code"].eq("formation").all()


def test_sf6_missing_duplicate_evidence_is_not_zero():
    """Erasing provenance makes the count unknown, not an observed zero."""
    production, wells = production_case(), _wells()
    observations = parsers.build_pressure_observations(production, wells, SETTINGS)
    observations.attrs.clear()
    quality = parsers.build_quality_stats(production, wells, observations, SETTINGS)
    assert quality["dropped_duplicate_pressure_observation_count"] is None
    assert "duplicate_count_NOT_EVALUATED" in quality["source_warnings"]


def test_sf7_empty_workbook_warns(tmp_path):
    """A workbook without rows has no header and yields no observations: one warning."""
    from openpyxl import Workbook

    path = tmp_path / "empty.xlsx"
    Workbook().save(path)
    completions = ok.read_completion_workbook(path)
    settings = {
        "depth_priority": [],
        "atmospheric_psi": 0,
        "test_type": "test",
        "gradient_method": "test",
    }
    observations = ok.build_pressure_observations(completions, settings)
    quality = ok.build_quality_stats(completions, observations, settings)
    assert quality["source_warnings"] == ["no_usable_pressure_observations"]


def test_sf8_unknown_source_type_rejected_before_download():
    """One misspelled configured type is an error, not a silently skipped source."""
    config = {"sources": {"production": {"source_type": "production_cvs"}}}
    with pytest.raises(ValueError, match="source_type"):
        pipeline.configured_sources(config)


def test_sf9_kansas_decode_is_strict(tmp_path):
    """The byte FF is invalid UTF-8; replacement would silently alter the record."""
    path = tmp_path / "invalid.csv"
    path.write_bytes(b"header\n\xff")
    with pytest.raises(UnicodeDecodeError):
        ks.read_proration_pressures(path)


def test_sf9_facility_decode_is_strict(tmp_path):
    """Invalid UTF-8 must fail before a corrupted page becomes a parsed record."""
    path = tmp_path / "invalid.html"
    path.write_bytes(b"<html>\xff</html>")
    with pytest.raises(UnicodeDecodeError):
        facility_detail_pipeline.parse_facility_detail_pages(
            {"fetched": [{"raw_path": str(path)}]}
        )


def test_sf10_bad_date_is_reported(tmp_path):
    """'bad-date' is nonblank and cannot match DD-Mon-YYYY: one invalid PERMIT."""
    path = tmp_path / "wells.csv"
    row = {column: "" for column in ks.WELLS_NUMERIC + ks.WELLS_DATES}
    row["PERMIT"] = "bad-date"
    pd.DataFrame([row]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="PERMIT.*1"):
        ks.read_wells_master(path)


@pytest.mark.parametrize("value", ["15-123-00001", "1512300001"])
def test_sf11_county_handles_both_api_formats(value):
    """Remove separators: state 15, county 123, sequence 00001; county is 123."""
    assert ks_pipeline._county_code(value) == "123"


@pytest.mark.parametrize("value", ["bad", "15-12-00001", None])
def test_sf11_malformed_county_rejected(value):
    """Malformed identifiers do not establish a county code."""
    with pytest.raises(ValueError, match="Kansas API"):
        ks_pipeline._county_code(value)


def test_sf12_missing_api_never_inherits_null_key_well():
    """Two null keys do not identify the same well: no curated observation."""
    production, wells = production_case(), _wells()
    production[["api12", "api10", "facility_id"]] = pd.NA
    wells[["api12", "api10", "facility_id"]] = pd.NA
    observations = parsers.build_pressure_observations(production, wells, SETTINGS)
    assert observations.empty
    quality = parsers.build_quality_stats(production, wells, observations, SETTINGS)
    assert quality["rejected_missing_api_count"] == 1


@pytest.mark.parametrize("value", ["-1", "1234", "1.5"])
def test_sf12_invalid_api_parts_rejected(value):
    """A three-digit part cannot be negative, four digits, or fractional."""
    assert clean_int(value, 3) is None
