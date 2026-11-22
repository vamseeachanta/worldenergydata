"""Interim PND reporting: independent, synthetic calendar-day examples.

Policy source: issue #1065, Action 2 (report with and without PND), and
``docs/data-sources/bsee/data/WELL_ACTIVITY_CD/publication_status.md``,
Interpretation rule and enquiry (2026-10-12). These tests validate scenario
arithmetic, not the unknown meaning of PND. Every duration below is counted
by hand from the stated inclusive dates; no expected value uses the engine.
"""

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.war_pnd_sensitivity import rig_days_pnd_sensitivity

# Synthetic identifiers distinguish two bores of one well and an absent well.
BORE = "111111111100"
SIDETRACK = "111111111101"
ABSENT = "222222222200"
COLUMNS = ["API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT", "WELL_ACTIVITY_CD"]


def war(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def scenarios(frame):
    return frame.set_index("pnd_treatment")


def test_bore_report_always_pairs_the_declared_bases():
    """Jan 1-7 DRL = 7; Jan 8-14 COM = 7; Jan 15-21 PND = 7.

    Excluding PND gives 7 completion days; including it gives 7 + 7 = 14.
    The entire covered date set is Jan 1-21, hence 21 days in either scenario.
    """
    source = war(
        [
            [BORE, "2024-01-01", "2024-01-07", "DRL"],
            [BORE, "2024-01-08", "2024-01-14", "COM"],
            [BORE, "2024-01-15", "2024-01-21", "PND"],
        ]
    )
    original = source.copy(deep=True)
    report = scenarios(rig_days_pnd_sensitivity(source))
    assert report.index.tolist() == ["excluded", "included_in_completion"]
    assert report["completion_days"].tolist() == [7, 14]
    assert report["drilling_days"].tolist() == [7, 7]
    assert report["pnd_days"].tolist() == [7, 7]
    assert report["war_days_total"].tolist() == [21, 21]
    assert report["basis"].tolist() == [
        "DRL_COM(drilling=DRL;completion=COM;days=inclusive)",
        "DRL_COM_PND(drilling=DRL;completion=COM+PND;days=inclusive)",
    ]
    assert report["pnd_definition_status"].eq("unvalidated").all()
    pd.testing.assert_frame_equal(source, original)


def test_overlap_is_a_union_rather_than_adding_pnd_days():
    """COM Jan 1-7 and PND Jan 5-11 overlap on Jan 5, 6, 7.

    Inclusive union = 7 + 7 - 3 = 11; excluded completion = 7.
    Repeating the PND row contributes no additional dates.
    """
    report = scenarios(
        rig_days_pnd_sensitivity(
            war(
                [
                    [BORE, "2024-01-01", "2024-01-07", "COM"],
                    [BORE, "2024-01-05", "2024-01-11", "PND"],
                    [BORE, "2024-01-05", "2024-01-11", "PND"],
                ]
            )
        )
    )
    assert report["completion_days"].tolist() == [7, 11]
    assert report["pnd_days"].tolist() == [7, 7]


def test_pnd_only_keeps_excluded_completion_unknown():
    """Jan 1-7 contains 7 PND dates and no COM dates.

    Exclusion supplies no evidence for completion (null, not measured zero).
    Inclusion credits the same 7 dates under an explicitly unvalidated rule.
    """
    report = scenarios(
        rig_days_pnd_sensitivity(war([[BORE, "2024-01-01", "2024-01-07", "PND"]]))
    )
    assert pd.isna(report.loc["excluded", "completion_days"])
    assert report.loc["excluded", "completion_days_status"] == "no_activity_coded"
    assert report.loc["included_in_completion", "completion_days"] == 7
    assert (
        report.loc["included_in_completion", "completion_days_status"] == "war_covered"
    )
    assert report["drilling_days"].isna().all()


def test_no_pnd_has_identical_completion_in_both_scenarios():
    """COM Jan 1-7 = 7 dates; no PND dates = diagnostic zero."""
    report = rig_days_pnd_sensitivity(war([[BORE, "2024-01-01", "2024-01-07", "COM"]]))
    assert report["completion_days"].tolist() == [7, 7]
    assert report["pnd_days"].tolist() == [0, 0]
    assert report["pnd_definition_status"].eq("unvalidated").all()


@pytest.mark.parametrize("grain", ["bore", "well"])
def test_empty_input_retains_the_report_schema(grain):
    """An empty set has no entities; scenario and day columns still exist."""
    report = rig_days_pnd_sensitivity(war([]), grain=grain)
    assert report.empty
    assert {"basis", "pnd_treatment", "pnd_definition_status", "pnd_days"} <= set(
        report.columns
    )


@pytest.mark.parametrize("grain", ["bore", "well"])
def test_absent_population_stays_null_in_both_scenarios(grain):
    """No reported dates exist for ABSENT; neither scenario measures days."""
    report = rig_days_pnd_sensitivity(war([]), grain=grain, population=[ABSENT])
    assert report["pnd_treatment"].tolist() == ["excluded", "included_in_completion"]
    assert report[["drilling_days", "completion_days", "pnd_days"]].isna().all().all()
    assert report["days_status"].eq("no_war_activity").all()
    assert report["pnd_definition_status"].eq("unvalidated").all()


def test_uncoded_coverage_does_not_become_pnd_or_completion():
    """Jan 1-7 has 7 covered dates, none attributed to any activity code."""
    report = rig_days_pnd_sensitivity(war([[BORE, "2024-01-01", "2024-01-07", None]]))
    assert report["war_days_total"].tolist() == [7, 7]
    assert report["completion_days"].isna().all()
    assert report["days_status"].eq("war_covered_no_activity_code").all()


def test_rejected_intervals_remain_visible():
    """PND Jan 7-1 is reversed and rejected; COM Jan 8-14 has 7 dates.

    Each scenario retains one rejection and 7 completion days, with no PND.
    """
    report = rig_days_pnd_sensitivity(
        war(
            [
                [BORE, "2024-01-07", "2024-01-01", "PND"],
                [BORE, "2024-01-08", "2024-01-14", "COM"],
            ]
        )
    )
    assert report["war_weeks_rejected"].tolist() == [1, 1]
    assert report["completion_days"].tolist() == [7, 7]
    assert report["pnd_days"].tolist() == [0, 0]


def test_well_report_unions_bores_before_crediting_pnd():
    """COM Jan 1-7 on one bore; PND Jan 5-11 on another of the same well.

    Excluded completion = 7. Included completion = Jan 1-11 = 11, while
    per-bore additive completion = 7 + 7 = 14. Reported coverage is 11 dates.
    """
    report = scenarios(
        rig_days_pnd_sensitivity(
            war(
                [
                    [BORE, "2024-01-01", "2024-01-07", "COM"],
                    [SIDETRACK, "2024-01-05", "2024-01-11", "PND"],
                ]
            ),
            grain="well",
        )
    )
    assert report["api10"].eq("1111111111").all()
    assert "api12" not in report.columns
    assert report["completion_days"].tolist() == [7, 11]
    assert report["completion_days_additive"].tolist() == [7, 14]
    assert report["war_days_total"].tolist() == [11, 11]
    assert report["pnd_definition_status"].eq("unvalidated").all()


@pytest.mark.parametrize("grain", ["bore", "well"])
def test_population_restricts_both_scenarios(grain):
    """Only the selected bore's COM Jan 1-7 (7 dates) enters either result.

    PND Jan 8-14 belongs to the unselected bore and cannot affect the union.
    """
    report = rig_days_pnd_sensitivity(
        war(
            [
                [BORE, "2024-01-01", "2024-01-07", "COM"],
                [SIDETRACK, "2024-01-08", "2024-01-14", "PND"],
            ]
        ),
        grain=grain,
        population=[BORE],
    )
    assert report["completion_days"].tolist() == [7, 7]
    assert report["pnd_days"].tolist() == [0, 0]


def test_invalid_grain_is_rejected():
    """A misspelt grain must not silently choose a different aggregation."""
    with pytest.raises(ValueError, match="grain must be 'bore' or 'well'"):
        rig_days_pnd_sensitivity(war([]), grain="boer")


def test_missing_join_columns_are_rejected():
    """An unjoined table cannot supply the activity evidence for either basis."""
    with pytest.raises(ValueError, match="missing required column"):
        rig_days_pnd_sensitivity(pd.DataFrame())
