"""Identifier-grain checks for BSEE data; synthetic examples are hand-counted.

Format source: NTL 2009-G33, attachment pp. 3-5 (2009), API Well Number and
Producing Interval Code. Widths are structural rules, not measured thresholds.
"""

import csv
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis import war_rig_days
from worldenergydata.bsee.analysis.war_rig_days import (
    normalize_api12,
    rig_days_by_bore,
    rig_days_by_well,
)
from worldenergydata.bsee.analysis.well_identifier_grain import (
    normalize_bsee_api12,
    summarize_bore_population,
)

# Synthetic identifiers: one family with two bores, and another with one bore.
BORE = "608120000100"
BYPASS_OR_SIDETRACK = "608120000101"
OTHER_FAMILY = "608120000200"


@pytest.mark.parametrize(
    "value", [BORE, f" {BORE} ", int(BORE), float(BORE), f"{BORE}.00"]
)
def test_normalization_preserves_the_full_bore_key(value):
    """Hand check: removing whitespace/numeric tails leaves the same digits."""
    assert normalize_bsee_api12(value) == BORE
    assert normalize_api12([value]).tolist() == [BORE]


@pytest.mark.parametrize(
    "value",
    [
        BORE[:10],
        BORE + "01",
        None,
        pd.NA,
        float("nan"),
        "",
        True,
        "60812-0000100",
        "60812000010",
        "608120000100.5",
        "6.081200001e11",
        "６０８１２００００１００",
    ],
)
def test_ambiguous_or_missing_identifiers_are_rejected(value):
    """NTL 2009-G33 p. 3 requires the complete numeric wellbore key."""
    with pytest.raises(ValueError, match="API-12"):
        normalize_bsee_api12(value)
    with pytest.raises(ValueError, match="API-12"):
        normalize_api12([value])


def test_leading_zero_is_preserved_and_never_invented():
    """Hand check: a string retains its first zero; numeric loss is ambiguous."""
    assert normalize_bsee_api12("010010000100") == "010010000100"
    assert normalize_api12(["010010000100"]).tolist() == ["010010000100"]
    with pytest.raises(ValueError, match="API-12"):
        normalize_bsee_api12(10010000100)


def test_series_normalization_preserves_row_alignment():
    """Nonconsecutive input labels must continue to identify the same rows."""
    values = pd.Series([float(BORE), BYPASS_OR_SIDETRACK], index=[4, 9])
    assert normalize_api12(values).to_dict() == {4: BORE, 9: BYPASS_OR_SIDETRACK}


def test_batch_normalization_does_not_dispatch_each_row_to_the_scalar_helper(
    monkeypatch,
):
    """Full-feed validation must use a batch path rather than Python per row."""

    def scalar_call(value):
        pytest.fail("Batch normalization dispatched a row to the scalar helper")

    monkeypatch.setattr(
        war_rig_days, "normalize_bsee_api12", scalar_call, raising=False
    )
    values = pd.Series([f" {BORE}.00 ", float(OTHER_FAMILY)], index=[9, 9])
    assert normalize_api12(values).tolist() == [BORE, OTHER_FAMILY]
    assert normalize_api12(values).index.tolist() == [9, 9]


@pytest.mark.parametrize(
    "value",
    [
        None,
        pd.NA,
        float("nan"),
        float("inf"),
        True,
        BORE[:10],
        BORE + "01",
        "１２３４５６７８９０１２",
    ],
)
def test_batch_normalization_rejects_an_invalid_row_among_valid_rows(value):
    """A single invalid key invalidates the entire batch, even at a duplicate index."""
    values = pd.Series([BORE, value, OTHER_FAMILY], index=[4, 4, 9])
    with pytest.raises(ValueError, match="API-12"):
        normalize_api12(values)


def test_empty_batch_preserves_its_index():
    """An empty source has no keys to validate and keeps its index metadata."""
    values = pd.Series([], index=pd.Index([], name="source_row"), dtype=object)
    result = normalize_api12(values)
    assert result.empty
    assert result.index.equals(values.index)
    assert result.index.name == "source_row"


def test_population_counts_distinct_bores_and_families():
    """Hand count: A00, A01, B00, duplicate A00 => 3 bores, 2 families.

    Family A has two bores; B has one. The two unique WB codes are 00 and 01.
    A nonzero WB code cannot distinguish bypasses from geologic sidetracks
    (NTL 2009-G33 p. 3).
    """
    summary = summarize_bore_population([BORE, BYPASS_OR_SIDETRACK, OTHER_FAMILY, BORE])
    assert summary == {
        "bore_count": 3,
        "well_family_count": 2,
        "family_size_histogram": {1: 1, 2: 1},
        "wellbore_codes": ["00", "01"],
    }


def test_empty_population_has_no_bores_or_families():
    """Hand count of an empty set is zero for each counting unit."""
    assert summarize_bore_population([]) == {
        "bore_count": 0,
        "well_family_count": 0,
        "family_size_histogram": {},
        "wellbore_codes": [],
    }


def test_population_does_not_truncate_an_event_key():
    """An extra event suffix must not manufacture a BSEE bore or completion."""
    with pytest.raises(ValueError, match="API-12"):
        summarize_bore_population([BORE, BORE + "01"])


def test_committed_population_matches_the_documented_family_distribution():
    """Reproducibility pin from issue #1081 and the grain decision record.

    Independent arithmetic on the reported family-size histogram:
    84 + 28 + 12 + 8 + 5 + 1 + 2 = 140 families;
    84*1 + 28*2 + 12*3 + 8*4 + 5*5 + 1*6 + 2*7 = 253 bores.
    This checks the committed extract, not completeness of the raw BSEE feed.
    """
    root = Path(__file__).resolve().parents[4]
    with (root / "reports/lower_tertiary/data/dc_vintage_diff.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        summary = summarize_bore_population(
            row["api12"] for row in csv.DictReader(stream)
        )
    assert summary["bore_count"] == 253
    assert summary["well_family_count"] == 140
    assert summary["family_size_histogram"] == {
        1: 84,
        2: 28,
        3: 12,
        4: 8,
        5: 5,
        6: 1,
        7: 2,
    }
    assert summary["wellbore_codes"] == ["00", "01", "02", "03", "04", "05", "06"]


@pytest.mark.parametrize("aggregate", [rig_days_by_bore, rig_days_by_well])
@pytest.mark.parametrize("invalid", [BORE[:10], BORE + "01", None])
def test_war_aggregation_refuses_ambiguous_grain(aggregate, invalid):
    """An invalid source key must fail even when a population filters it out."""
    war = _war([[invalid, "2024-01-01", "2024-01-07", "DRL"]])
    with pytest.raises(ValueError, match="API-12"):
        aggregate(war, population=[BORE])


@pytest.mark.parametrize("aggregate", [rig_days_by_bore, rig_days_by_well])
@pytest.mark.parametrize("invalid", [BORE[:10], BORE + "01", None])
def test_population_refuses_ambiguous_grain(aggregate, invalid):
    """A malformed requested bore is an input error, not absent WAR coverage."""
    with pytest.raises(ValueError, match="API-12"):
        aggregate(_war([]), population=[invalid])


def _war(rows):
    return pd.DataFrame(
        rows,
        columns=["API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT", "WELL_ACTIVITY_CD"],
    )


def test_reentry_and_shared_weeks_keep_bore_and_family_measures_distinct():
    """Independent inclusive-calendar arithmetic, not values from the engine.

    Bore A00: Jan 1-7 plus Jan 22-28 = 7+7 = 14; its idle gap is excluded.
    Bore A01: Jan 5-11 = 7. Family union = Jan 1-11 plus Jan 22-28 = 18.
    Bore sum = 21; overlap Jan 5-7 = 3. A recompletion interval would not
    receive another copy of these bore days (NTL 2009-G33 pp. 3-5).
    """
    war = _war(
        [
            [BORE, "2024-01-01", "2024-01-07", "DRL"],
            [BORE, "2024-01-22", "2024-01-28", "DRL"],
            [BYPASS_OR_SIDETRACK, "2024-01-05", "2024-01-11", "DRL"],
        ]
    )
    bores = rig_days_by_bore(war).set_index("api12")
    assert bores.loc[BORE, "drilling_days"] == 14
    assert bores.loc[BYPASS_OR_SIDETRACK, "drilling_days"] == 7
    family = rig_days_by_well(war).squeeze()
    assert family["api10"] == BORE[:10]
    assert family["n_bores"] == 2
    assert family["drilling_days"] == 18
    assert family["drilling_days_additive"] == 21
    assert family["overlap_days"] == 3
