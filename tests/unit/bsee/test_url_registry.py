"""Unit tests for the BSEE dataset URL registry."""

import pytest

from worldenergydata.bsee.data.refresh.url_registry import (
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


def test_total_expected_bins_is_130():
    total = sum(len(spec.expected_bins) for spec in get_all_specs())
    assert total == 130


def test_all_urls_use_bsee_base():
    for spec in get_all_specs():
        assert spec.zip_url.startswith(
            BSEE_BASE_URL
        ), f"{spec.bin_dir}: url {spec.zip_url!r} does not start with {BSEE_BASE_URL}"


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
