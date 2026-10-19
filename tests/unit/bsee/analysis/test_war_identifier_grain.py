"""Identifier-grain contracts for the WAR engine.

Source: MMS NTL 2009-G33 (2009), attachment pp. 2-4: API-10 is the
well family, API-12 adds the WB code, and the producing interval is separate.
https://www.bsee.gov/sites/bsee.gov/files/notices-to-lessees-ntl/notices-to-lessees/09-g33.pdf
Identifiers and dates below are synthetic unless a committed source is named.
"""

import csv
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.war_rig_days import (
    normalize_api12,
    rig_days_by_bore,
    rig_days_by_well,
)

BORE = "012345678900"
BYPASS = "012345678901"


def war_rows(*rows):
    return pd.DataFrame(
        rows,
        columns=[
            "API_WELL_NUMBER",
            "WAR_START_DT",
            "WAR_END_DT",
            "WELL_ACTIVITY_CD",
        ],
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (BORE, BORE),
        (f"  {BORE}  ", BORE),
        (f"{BORE}.0", BORE),
        (123456789012, "123456789012"),
        (123456789012.0, "123456789012"),
    ],
)
def test_normalization_preserves_full_bore_key_and_index(value, expected):
    """Hand split: 01 + 234 + 56789 + 00; no leading zero is discarded."""
    source = pd.Series([value], index=["row"], name="API_WELL_NUMBER")
    result = normalize_api12(source)
    assert result.to_dict() == {"row": expected}
    assert result.name == source.name


@pytest.mark.parametrize(
    "value",
    [
        "0123456789",  # Family only, no WB code: NTL attachment pp. 2-3.
        "01234567890001",  # API-14 is not a BSEE wellbore key.
        "",
        "   ",
        None,
        float("nan"),
        pd.NA,
        "01-234-56789-00",
        "０１２３４５６７８９００",
        "012345678900.5",
        "1.23456789012e11",
        "01234567890A",
    ],
)
def test_rejects_keys_that_cannot_establish_bore_grain(value):
    """Format rejection, not a regulatory validity check of assigned codes."""
    with pytest.raises(ValueError, match="12 ASCII digits"):
        normalize_api12([value])


def test_empty_identifier_column_is_valid():
    assert normalize_api12([]).empty


@pytest.mark.parametrize("aggregate", [rig_days_by_bore, rig_days_by_well])
@pytest.mark.parametrize("bad_key", ["0123456789", "01234567890001", None])
def test_aggregation_rejects_bad_war_keys(aggregate, bad_key):
    with pytest.raises(ValueError, match="12 ASCII digits"):
        aggregate(war_rows((bad_key, "2024-01-01", "2024-01-07", "DRL")))


@pytest.mark.parametrize("aggregate", [rig_days_by_bore, rig_days_by_well])
def test_population_keys_are_validated_even_without_war_rows(aggregate):
    with pytest.raises(ValueError, match="12 ASCII digits"):
        aggregate(war_rows(), population=["0123456789"])


def test_error_reports_count_without_echoing_source_values():
    with pytest.raises(ValueError, match="2 invalid") as error:
        normalize_api12([BORE, "untrusted-input", None])
    assert "untrusted-input" not in str(error.value)


def test_committed_population_has_distinct_bore_and_family_counts():
    """Expected 253 bores / 140 families: decision record Table 4.

    Source: docs/data-sources/bsee/analysis/well-identifier-grain.md,
    evidence date 2026-10-12. Only the api12 column is consumed; repeated
    publication rows do not create additional bores. This is a reproducibility
    check of that extract, not an independent census of the raw tables.
    """
    root = Path(__file__).resolve().parents[4]
    with (root / "reports/lower_tertiary/data/dc_vintage_diff.csv").open() as stream:
        identifiers = [row["api12"] for row in csv.DictReader(stream)]
    bores = normalize_api12(identifiers)
    assert bores.nunique() == 253
    # First ten digits identify the family: NTL attachment pp. 2-3.
    assert bores.str[:10].nunique() == 140


def test_overlapping_bores_emit_union_and_additive_days_separately():
    """Hand count: days 1..7 and 5..11 give 7 + 7 = 14 bore-days.

    Family union is days 1..11 = 11 days; overlap is days 5..7 = 3 days.
    WB 01 may be a bypass, not necessarily a geologic sidetrack (NTL p. 3).
    Inclusive calendar days follow the existing WAR engine convention.
    """
    war = war_rows(
        (BORE, "2024-01-01", "2024-01-07", "DRL"),
        (BYPASS, "2024-01-05", "2024-01-11", "DRL"),
    )
    bores = rig_days_by_bore(war)
    family = rig_days_by_well(war).squeeze()
    assert set(bores["api12"]) == {BORE, BYPASS}
    assert set(bores["api10"]) == {"0123456789"}
    assert set(bores["bore_suffix"]) == {"00", "01"}
    assert family["n_bores"] == 2
    assert family["drilling_days_additive"] == 14
    assert family["drilling_days"] == 11
    assert family["overlap_days"] == 3


@pytest.mark.parametrize("aggregate", [rig_days_by_bore, rig_days_by_well])
def test_reentry_keeps_bore_identity_and_excludes_idle_years(aggregate):
    """Hand count: Jan 1..7 in each of two years = 7 + 7 = 14 days.

    A duplicate first interval models repeated reporting contexts and adds
    no day; the intervening year is not rig activity. This verifies interval
    union, not assignment of a new regulatory WB code or episode detection.
    """
    result = aggregate(
        war_rows(
            (BORE, "2020-01-01", "2020-01-07", "DRL"),
            (BORE, "2020-01-01", "2020-01-07", "DRL"),
            (BORE, "2022-01-01", "2022-01-07", "DRL"),
        )
    )
    assert len(result) == 1
    assert result.squeeze()["drilling_days"] == 14
