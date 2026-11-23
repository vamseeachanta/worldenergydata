"""Tests for Texas RRC lifecycle API key normalization."""

import pytest

from worldenergydata.texas_rrc.lifecycle.keys import (
    derive_api10,
    normalize_api14,
    split_api14,
)


@pytest.mark.parametrize(
    ("raw_api", "expected"),
    [
        ("00100001", "42001000010000"),
        ("42-001-00001", "42001000010000"),
        ("4200100001", "42001000010000"),
        ("420010000100", "42001000010000"),
        ("42001000010102", "42001000010102"),
    ],
)
def test_normalize_api14_accepts_common_rrc_api_shapes(raw_api, expected):
    assert normalize_api14(raw_api) == expected


@pytest.mark.parametrize(
    "raw_api",
    [
        "4300100001",
        "420010001",
        "not-an-api",
        "",
        None,
    ],
)
def test_normalize_api14_rejects_invalid_or_non_texas_values(raw_api):
    assert normalize_api14(raw_api) is None


def test_split_api14_returns_join_segments():
    assert split_api14("42001000010102") == {
        "api10": "4200100001",
        "county_code": "001",
        "well_unique_number": "00001",
        "sidetrack_code": "01",
        "completion_code": "02",
    }


def test_derive_api10_returns_base_join_key():
    assert derive_api10("42001000010102") == "4200100001"
    assert derive_api10(None) is None
