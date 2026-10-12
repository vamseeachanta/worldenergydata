"""Repository-only comparison pins; synthetic dates below are test inputs."""

import csv
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[4]
NOTES = REPO / "docs/data-sources/bsee/analysis/rig_days"
WEEKLY = REPO / "docs/modules/bsee/analysis/rig_days"


def comparison_module():
    from worldenergydata.bsee.analysis import ratified_day_basis_comparison

    return ratified_day_basis_comparison


def test_note_breakdown_is_reconciled_without_relabelling_pnd():
    """summary.md:18: DRL151 + COM87 + PND49 + TA21 = 308.

    Full locator: docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md:18.
    Weekly CSV rows 2-46 give DRL 4 + 21*7 =151, COM13*7=91,
    PND7*7=49, TA7+7+3=17; total 308. The note differs COM+4/TA-4.
    PND is unknown in analysis/data/war_activity_codes.yml:135-160,
    so its 49 days are not a suspension assertion (DSI is suspension).
    """
    module = comparison_module()
    records = pd.read_csv(
        WEEKLY / "war_data_608124009500.csv", dtype=str, encoding="utf-8"
    )
    result = module.count_ratified_days(records)
    assert result["drilling_days"] == 151
    assert result["completion_days"] == 91  # Note:87; whole COM weeks retained.
    assert result["temporarily_abandoned_days"] == 17  # Note:21; TA7+7+3.
    assert result["pnd_days"] == 49
    assert result["suspended_days"] == 0  # No DSI-coded record in this fixture.
    assert result["total_days"] == 308


def synthetic_records():
    """DRL Jan1-7, COM Jan5-11 overlap3; duplicate DRL adds nothing.

    DSI Jan15-21, TA Jan22-28, PND Jan29-Feb4 each7; gap Jan12-14=3.
    Whole-week categories sum35, union total32, cross-code excess3.
    An activity start Jan5 within the COM week does not split either week.
    """
    spans = [
        ("2020-01-01", "2020-01-07", "DRL"),
        ("2020-01-05", "2020-01-11", "COM"),
        ("2020-01-15", "2020-01-21", "DSI"),
        ("2020-01-22", "2020-01-28", "TA"),
        ("2020-01-29", "2020-02-04", "PND"),
        ("2020-01-01", "2020-01-07", "DRL"),
    ]
    return pd.DataFrame(
        [
            dict(
                API_WELL_NUMBER="synthetic",
                WAR_START_DT=start,
                WAR_END_DT=end,
                WELL_ACTIVITY_CD=code,
                WELL_ACTV_START_DT="2020-01-05",
            )
            for start, end, code in spans
        ]
    )


def test_synthetic_union_boundary_gap_and_duplicate():
    result = comparison_module().count_ratified_days(synthetic_records())
    for metric in ["drilling", "completion", "suspended", "temporarily_abandoned"]:
        assert result[f"{metric}_days"] == 7
    assert result["other_days_by_code"] == {"PND": 7}
    assert result["pnd_days"] == 7
    assert result["total_days"] == 32
    assert result["gap_count"] == 1
    assert result["duplicate_count"] == 1
    assert result["cross_code_excess_days"] == 3


def test_absent_code_stays_null_and_multiple_wells_are_rejected():
    module = comparison_module()
    records = synthetic_records().iloc[[2]].copy()
    result = module.count_ratified_days(records)
    assert result["drilling_days"] is None
    assert result["completion_days"] is None
    assert result["suspended_days"] == 7
    records = pd.concat([records, records.assign(API_WELL_NUMBER="second")])
    with pytest.raises(ValueError):
        module.count_ratified_days(records)


def test_interim_preferred_formula_and_missing_dates():
    """Synthetic Jan1 spud, Jan7 TD, Jan11 last: drilling7, completion5.

    Inclusive formulas: rig_days_summary.md:25 and preferred method3 at :33.
    """
    module = comparison_module()
    assert module.count_interim_days("2020-01-01", "2020-01-07", "2020-01-11") == (
        7,
        5,
    )
    assert module.count_interim_days(None, "2020-01-07", "2020-01-11") == (None, 5)
    assert module.count_interim_days("2020-01-08", "2020-01-07", "2020-01-06") == (
        None,
        None,
    )


def test_committed_csv_recomputes_row_for_row():
    module = comparison_module()
    generated = module.build_comparison(REPO)
    with (NOTES / "ratified_day_basis_comparison.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        committed = list(csv.DictReader(stream))
    assert committed == module.csv_rows(generated)
    assert any(
        row["status"] == "not computed: records not in the repository"
        for row in committed
    )
    # Each published source remains independent even when its values agree.
    sources = {
        row["published_table"] for row in committed if row["api12"] == "608124009500"
    }
    assert len(sources) >= 4


def test_summary_statistics_are_json_serializable():
    import json

    module = comparison_module()
    assert json.loads(
        json.dumps(module.summary_statistics(module.build_comparison(REPO)))
    )


def test_uncoded_week_is_coverage_without_negative_overlap():
    """Synthetic DRL Jan1-7 plus uncoded Jan8-14: total14, unattributed7."""
    records = synthetic_records().iloc[[0]].copy()
    blank = records.assign(
        WAR_START_DT="2020-01-08", WAR_END_DT="2020-01-14", WELL_ACTIVITY_CD=None
    )
    result = comparison_module().count_ratified_days(
        pd.concat([records, blank], ignore_index=True)
    )
    assert result["total_days"] == 14
    assert result["unattributed_days"] == 7
    assert result["cross_code_excess_days"] == 0


def test_malformed_and_reversed_bounds_follow_existing_preparation():
    """Synthetic valid Jan1-7 plus one missing bound and one reversed row.

    The valid union is7, one reversed interval is rejected, the unparseable
    endpoint is excluded by existing preparation rather than repaired.
    """
    base = synthetic_records().iloc[[0]].copy()
    bad = base.assign(WAR_START_DT="unparseable")
    reverse = base.assign(WAR_START_DT="2020-01-08", WAR_END_DT="2020-01-07")
    result = comparison_module().count_ratified_days(
        pd.concat([base, bad, reverse], ignore_index=True)
    )
    assert result["total_days"] == 7
    assert result["rejected_records"] == 1


@pytest.mark.parametrize("code", [" NAN ", "none", ""])
def test_textual_missing_codes_follow_existing_normalization(code):
    """Synthetic Jan8-14 missing-code sentinel is7 unattributed days."""
    base = synthetic_records().iloc[[0]].copy()
    blank = base.assign(
        WAR_START_DT="2020-01-08", WAR_END_DT="2020-01-14", WELL_ACTIVITY_CD=code
    )
    result = comparison_module().count_ratified_days(
        pd.concat([base, blank], ignore_index=True)
    )
    assert result["unattributed_days"] == 7
    assert result["cross_code_excess_days"] == 0


@pytest.mark.parametrize(
    "api,drilling,completion",
    [("608124009500", 155, 152), ("608124003301", 37, 173)],
)
def test_milestone_reproduces_each_published_source(api, drilling, completion):
    """Committed workbook Sheet1 and export rows, keyed by API_WELL_NUMBER.

    Dates and weekly intervals reproduce the four review expectations;
    source row locators are retained in build_comparison output.
    """
    module = comparison_module()
    rows = module.build_comparison(REPO)
    for source in (module.EXPORT.as_posix(), module.WORKBOOK.as_posix() + ":Sheet1"):
        row = next(
            r for r in rows if r["api12"] == api and r["published_table"] == source
        )
        assert (
            row["milestone_drilling_days"] == drilling == row["published_drilling_days"]
        )
        assert (
            row["milestone_completion_days"]
            == completion
            == row["published_completion_days"]
        )
        assert row["milestone_drilling_difference_days"] == 0
        assert row["milestone_completion_difference_days"] == 0


def test_milestone_union_clips_td_and_keeps_uncoded_days():
    """Synthetic TD Jan7: Jan7-11=5, Jan15-Feb4=21; gap Jan12-14 excluded.

    Duplicate and overlapping weeks add no days; an uncoded Jan8-14
    bridges the gap, increasing completion from26 to29. DRL remains7.
    """
    module = comparison_module()
    records = synthetic_records()
    result = module.count_milestone_days(records, "2020-01-01", "2020-01-07")
    assert result["milestone_drilling_days"] == 6
    assert result["milestone_completion_days"] == 26
    assert result["milestone_completion_days_by_code"] == {
        "DRL": 1,
        "COM": 5,
        "DSI": 7,
        "TA": 7,
        "PND": 7,
    }
    blank = records.iloc[[0]].assign(
        WAR_START_DT="2020-01-08", WAR_END_DT="2020-01-14", WELL_ACTIVITY_CD=None
    )
    result = module.count_milestone_days(
        pd.concat([records, blank]), "2020-01-01", "2020-01-07"
    )
    assert result["milestone_completion_days"] == 29
    assert module.count_ratified_days(records)["drilling_days"] == 7


def test_milestone_missing_dates_stay_unavailable():
    module = comparison_module()
    for spud, td in [(None, "2020-01-07"), ("2020-01-01", None), (None, None)]:
        result = module.count_milestone_days(synthetic_records(), spud, td)
        assert result["milestone_drilling_days"] is None
        assert result["milestone_completion_days"] is None
        assert result["milestone_status"] == "not computed: dates not published"

    unavailable = [
        r
        for r in module.build_comparison(REPO)
        if r["coverage"] == "absent"
        and module._date(r["spud_date"]) is None
        and module._date(r["total_depth_date"]) is None
    ]
    assert unavailable
    assert all(
        r["milestone_status"] == "not computed: dates not published"
        for r in unavailable
    )


def test_zero_without_dates_is_not_published_by_rule():
    module = comparison_module()
    frame = pd.DataFrame(
        [
            {"api": "synthetic", "d": 0, "c": 0},
            {"api": "dated", "d": 0, "c": 0, "WELL_SPUD_DATE": "2020-01-01"},
            {"api": "nonzero", "d": 7, "c": 0},
        ]
    )
    rows = module._publication_rows(frame, "synthetic", "api", "d", "c")
    assert rows[0]["published_drilling_days"] is None
    assert rows[0]["published_completion_days"] is None
    assert rows[0]["published_drilling_status"] == "not published"
    assert rows[1]["published_drilling_days"] == 0
    assert rows[2]["published_drilling_days"] == 7
    assert rows[2]["published_completion_days"] is None
    workbook = next(
        r
        for r in module.build_comparison(REPO)
        if r["api12"] == "608124014001" and r["published_table"].endswith(":Sheet1")
    )
    for rule in ("ratified", "interim", "milestone"):
        assert workbook[f"{rule}_drilling_difference_days"] is None
        assert workbook[f"{rule}_completion_difference_days"] is None


def test_activity_code_columns_keep_suspension_and_abandonment_separate():
    result = comparison_module().count_ratified_days(synthetic_records())
    for code in ("DRL", "COM", "DSI", "TA", "PND"):
        assert result[f"activity_code_{code}_days"] == 7
    assert result["suspended_days"] == result["activity_code_DSI_days"]
    assert result["temporarily_abandoned_days"] == result["activity_code_TA_days"]


def test_new_csv_columns_append_and_statistics_keep_three_bases_paired():
    module = comparison_module()
    rows = module.build_comparison(REPO)
    keys = list(module.csv_rows(rows)[0])
    assert keys.index("weekly_source") < keys.index("milestone_completion_days")
    stats = module.summary_statistics(rows)
    groups = {(s["published_table"], s["coverage"], s["metric"]) for s in stats}
    for source, coverage, metric in groups:
        paired = [
            s
            for s in stats
            if (s["published_table"], s["coverage"], s["metric"])
            == (source, coverage, metric)
        ]
        assert {s["rule"] for s in paired} == {"ratified", "interim", "milestone"}
        assert len({s["wells"] for s in paired}) == 1
