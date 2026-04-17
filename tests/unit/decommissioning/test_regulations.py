# ABOUTME: Unit tests for the decommissioning regulatory database.
# ABOUTME: Covers all four regions, field validation, query functions, and summary DataFrame.

"""Unit tests for worldenergydata.decommissioning.regulations."""

import pandas as pd
import pytest

from worldenergydata.decommissioning.regulations import (
    DECOMMISSIONING_REGULATIONS,
    DecommissioningRegulation,
    get_lead_time,
    get_regulations,
    regulatory_summary,
)

_ALL_REGIONS = ("gom", "ukcs", "ncs", "brazil")
_REQUIRED_FIELDS = (
    "region",
    "regulatory_body",
    "requirement_type",
    "lead_time_months",
    "key_threshold",
    "reference_doc",
)


# ---------------------------------------------------------------------------
# Built-in database sanity checks
# ---------------------------------------------------------------------------


def test_regulations_list_is_not_empty():
    assert len(DECOMMISSIONING_REGULATIONS) > 0


def test_all_four_regions_have_regulations():
    regions_present = {r.region for r in DECOMMISSIONING_REGULATIONS}
    for region in _ALL_REGIONS:
        assert region in regions_present, f"No regulations found for region: {region}"


def test_each_regulation_has_required_fields():
    for reg in DECOMMISSIONING_REGULATIONS:
        for attr in _REQUIRED_FIELDS:
            value = getattr(reg, attr)
            assert value is not None and value != "", (
                f"Regulation for {reg.region}/{reg.requirement_type} "
                f"missing required field: {attr}"
            )


def test_lead_time_months_are_positive():
    for reg in DECOMMISSIONING_REGULATIONS:
        assert reg.lead_time_months > 0, (
            f"lead_time_months must be positive for "
            f"{reg.region}/{reg.requirement_type}"
        )


def test_regulatory_body_strings_are_non_empty():
    for reg in DECOMMISSIONING_REGULATIONS:
        assert reg.regulatory_body.strip() != ""


# ---------------------------------------------------------------------------
# get_regulations()
# ---------------------------------------------------------------------------


def test_get_regulations_gom_non_empty():
    regs = get_regulations("gom")
    assert len(regs) > 0


def test_get_regulations_ukcs_non_empty():
    regs = get_regulations("ukcs")
    assert len(regs) > 0


def test_get_regulations_ncs_non_empty():
    regs = get_regulations("ncs")
    assert len(regs) > 0


def test_get_regulations_brazil_non_empty():
    regs = get_regulations("brazil")
    assert len(regs) > 0


def test_get_regulations_returns_only_requested_region():
    regs = get_regulations("gom")
    assert all(r.region == "gom" for r in regs)


def test_get_regulations_unknown_region_returns_empty():
    regs = get_regulations("mars")
    assert regs == []


def test_get_regulations_case_insensitive():
    upper = get_regulations("GOM")
    lower = get_regulations("gom")
    assert len(upper) == len(lower)


# ---------------------------------------------------------------------------
# get_lead_time()
# ---------------------------------------------------------------------------


def test_get_lead_time_returns_positive_int():
    lt = get_lead_time("ukcs", "structure_removal")
    assert isinstance(lt, int)
    assert lt > 0


def test_get_lead_time_gom_well_plugging():
    lt = get_lead_time("gom", "well_plugging")
    assert lt > 0


def test_get_lead_time_unknown_returns_zero():
    lt = get_lead_time("ukcs", "nonexistent_requirement")
    assert lt == 0


def test_get_lead_time_case_insensitive():
    lt1 = get_lead_time("GOM", "WELL_PLUGGING")
    lt2 = get_lead_time("gom", "well_plugging")
    assert lt1 == lt2


# ---------------------------------------------------------------------------
# regulatory_summary()
# ---------------------------------------------------------------------------


def test_regulatory_summary_returns_dataframe():
    df = regulatory_summary()
    assert isinstance(df, pd.DataFrame)


def test_regulatory_summary_has_all_regions():
    df = regulatory_summary()
    regions = set(df["region"].tolist())
    for region in _ALL_REGIONS:
        assert region in regions


def test_regulatory_summary_expected_columns():
    df = regulatory_summary()
    for col in ("region", "regulatory_body", "requirement_type", "lead_time_months"):
        assert col in df.columns


def test_regulatory_summary_row_count_matches_database():
    df = regulatory_summary()
    assert len(df) == len(DECOMMISSIONING_REGULATIONS)


# ---------------------------------------------------------------------------
# Content-specific checks
# ---------------------------------------------------------------------------


def test_bsee_covers_well_plugging():
    regs = get_regulations("gom")
    types = {r.requirement_type for r in regs}
    assert "well_plugging" in types


def test_bsee_covers_structure_removal():
    regs = get_regulations("gom")
    types = {r.requirement_type for r in regs}
    assert "structure_removal" in types


def test_ospar_reference_in_ukcs():
    regs = get_regulations("ukcs")
    refs = " ".join(r.reference_doc + " " + r.key_threshold for r in regs)
    assert "OSPAR" in refs


def test_dataclass_instantiation():
    reg = DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="well_plugging",
        lead_time_months=6,
        key_threshold="Test threshold",
        reference_doc="Test Ref",
    )
    assert reg.region == "gom"
    assert reg.notes == ""


def test_ncs_has_psa_body():
    regs = get_regulations("ncs")
    bodies = {r.regulatory_body for r in regs}
    assert "PSA" in bodies


def test_brazil_has_anp_body():
    regs = get_regulations("brazil")
    bodies = {r.regulatory_body for r in regs}
    assert "ANP" in bodies
