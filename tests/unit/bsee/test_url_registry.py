"""Unit tests for the BSEE dataset URL registry."""

import pytest

from worldenergydata.bsee.data.refresh.url_registry import (
    BOEM_BASE_URL,
    BSEE_BASE_URL,
    DatasetSpec,
    get_all_specs,
    get_ogor_a_specs,
    get_regular_specs,
    get_specs_for_dir,
)

EXPECTED_DIRS = {
    "apichanges",
    "apiraw",
    "approvals",
    "assignments",
    "companydetails",
    "decomcost",
    "deepqual",
    "dsptsdelimit",
    "fieldreserves_master",
    "fieldreserves_tables",
    "fmp",
    "historical_production_yearly",
    "incinv",
    "incs",
    "lab",
    "leaseowner",
    "mcpflow",
    "nonrequired",
    "ocsprod",
    "offshorestats",
    "osfr",
    "permstruc",
    "pipeloc",
    "platstruc",
    "production_plan_area",
    "production_raw",
    "rowdesc",
    "royaltyref",
    "scanneddocs",
    "serialreg",
    "Well_APD_Default",
}


def test_all_specs_cover_all_stub_directories():
    actual_dirs = {spec.bin_dir for spec in get_all_specs()}
    assert actual_dirs == EXPECTED_DIRS


def test_total_expected_bins_is_134():
    total = sum(len(spec.expected_bins) for spec in get_all_specs())
    assert total == 134


def test_all_urls_use_official_federal_bases():
    # BSEE for the classic raw-data mirror; BOEM for the FieldReserves
    # program artifacts (#847). Any other host is a registry defect.
    allowed = (BSEE_BASE_URL, BOEM_BASE_URL)
    for spec in get_all_specs():
        assert spec.zip_url.startswith(
            allowed
        ), f"{spec.bin_dir}: url {spec.zip_url!r} not under {allowed}"


def test_fieldreserves_specs_registered():
    tables = get_specs_for_dir("fieldreserves_tables")
    assert len(tables) == 1
    assert tables[0].zip_url.startswith(BOEM_BASE_URL)
    assert "%20" in tables[0].zip_url  # spaces in the upstream filename
    assert set(tables[0].expected_bins) == {
        "2023_tables_xlsx_public__2023_table_4_final.bin",
        "2023_tables_xlsx_public__2023_table_5_final.bin",
        "2023_tables_xlsx_public__hist_2023.bin",
    }
    master = get_specs_for_dir("fieldreserves_master")
    assert len(master) == 1
    assert master[0].zip_url.startswith(BOEM_BASE_URL)
    assert master[0].expected_bins == ["mastdatadelimit.bin"]


def test_ogor_a_specs_count():
    ogor_a = get_ogor_a_specs()
    assert (
        len(ogor_a) == 30
    ), f"Expected 30 OGOR-A specs (1996-2024 + current), got {len(ogor_a)}"


def test_regular_specs_have_no_ogor_a():
    for spec in get_regular_specs():
        assert (
            spec.is_ogor_a is False
        ), f"Regular spec {spec.bin_dir!r} has is_ogor_a=True"


def test_get_specs_for_dir():
    platstruc = get_specs_for_dir("platstruc")
    assert len(platstruc) == 1

    yearly = get_specs_for_dir("historical_production_yearly")
    assert len(yearly) == 30


def test_no_duplicate_expected_bins():
    seen: dict[str, str] = {}
    for spec in get_all_specs():
        for bin_name in spec.expected_bins:
            key = f"{spec.bin_dir}/{bin_name}"
            if bin_name in seen and seen[bin_name] != spec.bin_dir:
                pytest.fail(
                    f"Bin {bin_name!r} appears in both {seen[bin_name]!r} and {spec.bin_dir!r}"
                )
            seen[bin_name] = spec.bin_dir
