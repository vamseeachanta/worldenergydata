"""Synthetic, offline checks for the public interventions example.

The report-generation tests copy the delivered output tables to a temporary
directory; they never read raw archives or the network.
"""

import json
import shutil
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import yaml

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/interventions_by_depth"
sys.path.insert(0, str(EXAMPLE))
from count_interventions import (
    BANDS,
    attach_depth,
    band_from_feet,
    classify_operation,
    dedupe_permits,
    full_year_average,
    gulf_only,
    normalize_api,
    rate_per_100,
    standing_wells,
)
from estimate_costs import estimate, event_cost


@pytest.mark.parametrize(
    "metres,expected",
    [(0, 0), (99.999, 0), (100, 1), (499.999, 1), (500, 2), (1499.999, 2), (1500, 3)],
)
def test_band_edges(metres, expected):
    assert band_from_feet(metres / 0.3048) == BANDS[expected]


def test_conversion_and_unknown():
    assert band_from_feet(1000) == BANDS[1]
    for value in [None, -1, float("nan"), float("inf")]:
        assert band_from_feet(value) == "no depth"


def test_api_and_fallback():
    assert normalize_api(
        pd.Series([608174087500.0, " 6081740875 ", None])
    ).tolist() == ["608174087500", "6081740875", ""]
    bore = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608174087500", "608174087501"],
            "WATER_DEPTH": [1000, 1000],
        }
    )
    result = attach_depth(
        pd.DataFrame(
            {"API_WELL_NUMBER": ["608174087599", "608174087500", "999999999999"]}
        ),
        bore,
    )
    assert result.band.tolist() == [BANDS[1], BANDS[1], "no depth"]
    assert result.depth_join.tolist() == ["api10", "api12", "missing"]
    bore.loc[1, "WATER_DEPTH"] = 2000
    assert (
        attach_depth(
            pd.DataFrame({"API_WELL_NUMBER": ["608174087599"]}), bore
        ).band.iloc[0]
        == "no depth"
    )


def test_region_precedence():
    bore = pd.DataFrame(
        {"API_WELL_NUMBER": ["608174087500", "301234567800"], "REGION_CODE": ["G", "P"]}
    )
    f = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608174087599", "301234567800", "", ""],
            "SURF_LEASE_NUM": ["", "G12345", "G12345", "P12345"],
        }
    )
    assert gulf_only(f, bore).region.tolist() == ["G", "P", "G", "unknown"]


def test_dedupe_and_conflict():
    f = pd.DataFrame(
        {
            "SN_APM": ["1", "1", "2"],
            "API_WELL_NUMBER": ["a", "a", "b"],
            "ACC_STATUS_DATE": ["1/1/2025"] * 3,
            "APM_OP_CD": ["WORKOVER"] * 3,
        }
    )
    assert len(dedupe_permits(f)) == 2
    f.loc[1, "APM_OP_CD"] = "ENHANCE"
    with pytest.raises(ValueError, match="conflicting"):
        dedupe_permits(f)


@pytest.mark.parametrize(
    "code,subcodes,group",
    [
        ("WORKOVER", set(), "workover and recompletion"),
        ("COMP", {"ZONE"}, "workover and recompletion"),
        ("COMP", {"INITCOMP"}, "initial completion excluded"),
        ("ENHANCE", {"ACIDIZE"}, "production enhancement"),
        ("ABANDON", {"TEMPABAN"}, "temporary abandonment"),
        ("ABANDON", {"PERMABAN", "TEMPABAN"}, "permanent abandonment"),
        ("ABANDON", set(), "abandonment unspecified"),
        ("OTHER", set(), "other well work"),
        ("ABANDON", {"PLUGBACK"}, "new hole excluded"),
        ("SIDETRACK", set(), "new hole excluded"),
        ("BYPASS", set(), "new hole excluded"),
        ("DEEPEN", set(), "new hole excluded"),
    ],
)
def test_mapping(code, subcodes, group):
    assert classify_operation(code, subcodes) == group


def test_new_hole_narratives_and_false_positives():
    assert (
        classify_operation("OTHER", set(), "Deepening of original batch set well")
        == "new hole excluded"
    )
    assert (
        classify_operation(
            "OTHER",
            set(),
            "APM in lieu of Application for Permit to Drill to sidetrack",
        )
        == "new hole excluded"
    )
    assert (
        classify_operation(
            "ABANDON", {"TEMPABAN"}, "TA now, deepen under a subsequent permit"
        )
        == "temporary abandonment"
    )
    assert (
        classify_operation("ENHANCE", set(), "deepen gas lift injection point")
        == "production enhancement"
    )
    assert (
        classify_operation("OTHER", set(), "bypass scale obstruction")
        == "other well work"
    )


@pytest.mark.parametrize(
    "code,subcodes,narrative,group",
    [
        # Future drilling under another permit: the current permit is the TA/PA.
        (
            "ABANDON",
            {"TEMPABAN"},
            "Temporarily abandon now; drill a new sidetrack under a subsequent permit.",
            "temporary abandonment",
        ),
        (
            "ABANDON",
            {"TEMPABAN"},
            "TA well. Future plans: drill sidetrack in 2027.",
            "temporary abandonment",
        ),
        (
            "ABANDON",
            {"TEMPABAN"},
            "TA the wellbore. Will drill a bypass under a separate APD.",
            "temporary abandonment",
        ),
        (
            "ABANDON",
            {"TEMPABAN"},
            "Set plugs; drilling a new sidetrack at a later date.",
            "temporary abandonment",
        ),
        # Negated drilling.
        (
            "ABANDON",
            {"TEMPABAN"},
            "Do not drill a new sidetrack. Temporarily abandon the well.",
            "temporary abandonment",
        ),
        (
            "ABANDON",
            {"PERMABAN"},
            "Permanently abandon; operator will not drill a sidetrack.",
            "permanent abandonment",
        ),
        (
            "ABANDON",
            {"PERMABAN"},
            "Permanently abandon without drilling a bypass.",
            "permanent abandonment",
        ),
        (
            "ABANDON",
            set(),
            "No plans to drill a sidetrack; abandon the wellbore.",
            "abandonment unspecified",
        ),
        # Line-wrapped descriptions keep their negation and future context.
        (
            "ABANDON",
            {"TEMPABAN"},
            "Do not\ndrill a new\nsidetrack.\nTemporarily abandon.",
            "temporary abandonment",
        ),
        (
            "ABANDON",
            {"TEMPABAN"},
            "TA now; drill a new sidetrack under a\nsubsequent permit.",
            "temporary abandonment",
        ),
        ("OTHER", set(), "Deepen under a future permit.", "other well work"),
    ],
)
def test_negated_or_future_drilling_keeps_structured_codes(
    code, subcodes, narrative, group
):
    assert classify_operation(code, subcodes, narrative) == group


@pytest.mark.parametrize(
    "code,subcodes,narrative",
    [
        ("ABANDON", {"TEMPABAN"}, "Abandon lower bore and drill a new sidetrack."),
        ("ABANDON", {"PERMABAN"}, "Plug back; drilling a bypass from 9,800 ft."),
        ("ABANDON", {"TEMPABAN"}, "APM for Sidetrack"),
        ("ENHANCE", set(), "Well was inadvertently sidetrack during milling."),
        # One negated clause does not hide a current one.
        (
            "ABANDON",
            {"TEMPABAN"},
            "Do not drill a bypass. Drill a new sidetrack from 10,000 ft.",
        ),
        ("ABANDON", {"TEMPABAN"}, "Drill a new\nsidetrack from the 9-5/8 in. casing."),
        # Past narration is not deferral.
        (
            "ABANDON",
            {"PERMABAN"},
            "Hole had closed up and we subsequently started drilling a bypass hole.",
        ),
        # Another document filed alongside does not defer the current work.
        ("OTHER", set(), "Reenter and deepen well. Separate paper APD also submitted."),
    ],
)
def test_current_drilling_narratives_remain_excluded(code, subcodes, narrative):
    assert classify_operation(code, subcodes, narrative) == "new hole excluded"


def test_exclusion_basis_names_every_new_hole_route():
    from count_interventions import exclusion_basis

    assert exclusion_basis("ABANDON", {"PLUGBACK"}, "") == "PLUGBACK subcode"
    assert exclusion_basis("SIDETRACK", set(), "") == "primary new-hole code"
    assert (
        exclusion_basis("ABANDON", {"TEMPABAN"}, "Drill a new sidetrack.")
        == "explicit new-hole narrative"
    )
    assert (
        exclusion_basis("ABANDON", {"TEMPABAN"}, "Do not drill a new sidetrack.")
        == "included"
    )
    assert exclusion_basis("COMP", set(), "") == "completion without ZONE"
    assert exclusion_basis("WORKOVER", set(), "") == "included"


def test_standing_wells_at_start_of_year():
    b = pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "608000000100",
                "608000000101",
                "608000000200",
                "608000000300",
                "608000000400",
            ],
            "WELL_NAME_SUFFIX": [
                "ST00BP00",
                "ST01BP00",
                "ST00BP00",
                "ST00BP00",
                "ST00BP00",
            ],
            "WELL_SPUD_DATE": [
                "1/1/2020",
                "1/1/2020",
                "1/1/2026",
                "1/1/2020",
                "1/1/2020",
            ],
            "BOREHOLE_STAT_CD": ["COM", "COM", "COM", "PA", "PA"],
            "BOREHOLE_STAT_DT": ["1/1/2020"] * 3 + ["12/31/2025", "1/1/2026"],
            "WATER_DEPTH": [100] * 5,
            "REGION_CODE": ["G"] * 5,
        }
    )
    assert standing_wells(b, [2025]).standing_wells.sum() == 3
    assert standing_wells(b, [2026]).standing_wells.sum() == 2


def test_rate_zero_is_missing():
    assert rate_per_100(5, 20) == 25
    assert pd.isna(rate_per_100(5, 0))


def test_inventory_duplicate_original_suffix_and_snapshot_cutoff():
    b = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["608000000100", "608000000170", "608000000200"],
            "WELL_NAME_SUFFIX": ["ST00BP00"] * 3,
            "WELL_SPUD_DATE": ["1/1/2020", "1/1/2021", "12/1/2026"],
            "BOREHOLE_STAT_CD": ["COM"] * 3,
            "BOREHOLE_STAT_DT": [""] * 3,
            "WATER_DEPTH": [100] * 3,
            "REGION_CODE": ["G"] * 3,
        }
    )
    assert standing_wells(b, [2026], as_of="2026-11-12").standing_wells.sum() == 1


def test_cost_and_mobilisation():
    assert event_cost(100, 5, 200) == 700
    assert [
        event_cost(r, d, m) for r, d, m in [(100, 2, 0), (200, 3, 10), (300, 4, 20)]
    ] == [200, 610, 1220]
    with pytest.raises(ValueError):
        event_cost(-1, 5, 0)


def test_partial_never_in_average():
    f = pd.DataFrame({"year": [2024, 2025, 2026], "count": [10, 20, 1000]})
    assert full_year_average(f, "count", 2025) == 15


def well_bores(statuses, status_dates, spuds=None):
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [f"6080000001{i:02d}" for i in range(len(statuses))],
            "WELL_NAME_SUFFIX": ["ST00BP00"] + ["ST01BP00"] * (len(statuses) - 1),
            "WELL_SPUD_DATE": spuds or ["2020-01-01"] * len(statuses),
            "BOREHOLE_STAT_CD": statuses,
            "BOREHOLE_STAT_DT": status_dates,
            "WATER_DEPTH": [100] * len(statuses),
            "REGION_CODE": ["G"] * len(statuses),
        }
    )


def test_superseded_original_with_abandoned_sidetrack():
    b = well_bores(["ST", "PA"], ["2021-01-01", "2025-06-01"])
    assert standing_wells(b, [2025]).standing_wells.sum() == 1
    assert standing_wells(b, [2026]).standing_wells.sum() == 0
    assert standing_wells(b, [2025], at="year_end").standing_wells.sum() == 0


def test_superseded_original_with_live_sidetrack():
    b = well_bores(["ST", "COM"], ["2021-01-01", "2022-01-01"])
    assert standing_wells(b, [2026]).standing_wells.sum() == 1


def test_cancelled_bore_ignored_in_status_and_first_spud():
    b = well_bores(["CNL", "PA"], ["", "2025-06-01"], ["2000-01-01", "2020-01-01"])
    assert standing_wells(b, [2010]).standing_wells.sum() == 0
    assert standing_wells(b, [2026]).standing_wells.sum() == 0
    assert standing_wells(b.iloc[:1], [2025]).standing_wells.sum() == 0


@pytest.mark.parametrize(
    "statuses, dates_", [(["ST", "BP"], ["", ""]), (["ST", "PA"], ["2021-01-01", ""])]
)
def test_unresolved_terminal_status_kept_and_counted(statuses, dates_):
    f = standing_wells(well_bores(statuses, dates_), [2026])
    assert f.standing_wells.sum() == 1
    assert f.assumed_standing.sum() == 1


def test_all_terminal_bores_must_be_abandoned_and_dates_inclusive():
    b = well_bores(["ST", "PA", "PA"], ["2020-01-01", "2024-01-01", "2026-01-01"])
    assert standing_wells(b, [2025]).standing_wells.sum() == 1
    assert standing_wells(b, [2026]).standing_wells.sum() == 0


def test_unit_type_mapping():
    from count_interventions import unit_category

    assert unit_category("DS", "DRILLSHIP", "1") == "drillship / semisubmersible"
    assert unit_category("SD", "SEMI", "2") == "drillship / semisubmersible"
    assert unit_category("CT", "COILED TUBING", "3") == "coiled tubing"
    assert unit_category("SB", "SNUBBING", "4") == "hydraulic workover / snubbing"
    assert unit_category("NR", "NON RIG PA", "5") == "non-rig operation (recorded)"
    assert unit_category("", "", "") == "none named"
    assert unit_category("UNKNOWN", "UNKNOWN RIG", "6") == "other"
    assert unit_category("", "", "999") == "other"


@pytest.mark.parametrize(
    "scenario_id,case,expected",
    [
        ("platform_casing_work", "low_usd", 554454),  # 68,424 x 7 + 75,486 = 554,454
        ("platform_rigless_pa", "low_usd", 269076),  # 64,530 x 3 + 75,486 = 269,076
        ("subsea_work", "low_usd", 4722200),  # 674,600 x 7 + 0 = 4,722,200
        ("deep_platform_pa", "high_usd", 1374570),  # Table 8-4, 5,000 ft
    ],
)
def test_real_cost_literals_from_yaml(scenario_id, case, expected):
    basis = yaml.safe_load((EXAMPLE / "cost_basis.yml").read_text(encoding="utf-8"))
    assert estimate(basis).set_index("scenario_id").loc[scenario_id, case] == expected


def test_deep_platform_work_is_unpriced():
    basis = yaml.safe_load((EXAMPLE / "cost_basis.yml").read_text(encoding="utf-8"))
    row = estimate(basis).set_index("scenario_id").loc["deep_platform_work"]
    assert pd.isna(row.low_usd)
    assert row.pricing_method == "not priced"


STEMS = [
    "01_approved_interventions",
    "02_rates_per_standing_well",
    "03_cost_per_event",
    "04_unit_types_by_depth",
    "05_well_life",
    "06_well_life_stages",
]


@pytest.fixture
def output_copy(tmp_path):
    out = tmp_path / "output"
    shutil.copytree(EXAMPLE / "output", out)
    return out


def summary_of(out):
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", [f"{s}{x}" for s in STEMS for x in (".png", ".svg")])
def test_verifier_requires_every_chart_before_writing_a_receipt(output_copy, name):
    import verify_outputs

    (output_copy / "verification.json").unlink()
    (output_copy / name).unlink()
    with pytest.raises(AssertionError, match="missing chart"):
        verify_outputs.verify(output_copy)
    assert not (output_copy / "verification.json").exists()


def test_verifier_passes_on_the_delivered_outputs(output_copy):
    import verify_outputs

    (output_copy / "verification.json").unlink()
    verify_outputs.verify(output_copy)
    receipt = json.loads((output_copy / "verification.json").read_text())
    assert len(receipt["checks"]) == 15


def test_note_headline_follows_consistent_aggregates(output_copy, tmp_path):
    import write_results_note

    last = summary_of(output_copy)["last_full_year"]
    rates = pd.read_csv(output_copy / "rates.csv")
    work = rates.year.eq(last) & rates.family.eq("well work")
    before = int(rates.loc[work, "permits"].sum())
    abandonment = int(
        rates.loc[rates.year.eq(last) & rates.family.eq("abandonment"), "permits"].sum()
    )
    rates.loc[work & rates.band.eq(BANDS[0]), "permits"] += 100
    rates.to_csv(output_copy / "rates.csv", index=False)
    mapping = pd.read_csv(output_copy / "code_mapping.csv")
    row = mapping.primary_code.eq("WORKOVER") & mapping.group.eq(
        "workover and recompletion"
    )
    mapping.loc[row, "last_full_year_permits"] += 100
    mapping.to_csv(output_copy / "code_mapping.csv", index=False)
    readme = tmp_path / "README.md"
    write_results_note.main(out=output_copy, readme=readme)
    text = readme.read_text(encoding="utf-8")
    assert (
        f"In {last}, **{before + 100:,} well-work approvals + {abandonment:,} "
        f"abandonment approvals = {before + 100 + abandonment:,} events**"
    ) in text
    assert f"{before:,} well-work approvals" not in text
    assert "31 Oct" not in text


def test_note_rejects_aggregates_that_do_not_reconcile(output_copy, tmp_path):
    import write_results_note

    last = summary_of(output_copy)["last_full_year"]
    rates = pd.read_csv(output_copy / "rates.csv")
    shallow = rates.year.eq(last) & rates.band.eq(BANDS[0])
    rates.loc[shallow & rates.family.eq("well work"), "permits"] += 100
    rates.to_csv(output_copy / "rates.csv", index=False)
    readme = tmp_path / "README.md"
    with pytest.raises(ValueError, match="reconciliation"):
        write_results_note.main(out=output_copy, readme=readme)
    assert not readme.exists()


def test_note_and_charts_reject_a_changed_year(output_copy, tmp_path):
    import plot_charts
    import write_results_note

    summary = summary_of(output_copy)
    summary["last_full_year"] -= 1
    summary["partial_year"] -= 1
    (output_copy / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    charts = {p.name: p.read_bytes() for p in output_copy.glob("0*")}
    readme = tmp_path / "README.md"
    with pytest.raises(ValueError, match="selects"):
        write_results_note.main(out=output_copy, readme=readme)
    assert not readme.exists()
    with pytest.raises(ValueError, match="selects"):
        plot_charts.plot(output_copy)
    assert {p.name: p.read_bytes() for p in output_copy.glob("0*")} == charts


def synthetic_primary():
    rows = []
    for year, other, workover in [
        (2019, 300, 100),
        (2020, 200, 100),
        (2021, 50, 300),
        (2022, 0, 300),
        (2023, 0, 300),
        (2024, 0, 300),
    ]:
        rows += [(year, "OTHER", other), (year, "WORKOVER", workover)]
    frame = pd.DataFrame(rows, columns=["year", "APM_OP_CD", "approvals"])
    return frame[frame.approvals.gt(0)]


def test_coding_change_text_is_derived_from_the_table():
    from report_text import coding_caption, coding_sentence

    primary = synthetic_primary()
    assert coding_sentence(primary, 2019, 2024) == (
        "Primary OTHER approvals numbered 200–300 per year in 2019–2020, then "
        "50 in 2021 and zero from 2022, while WORKOVER approvals averaged 100 "
        "per year in 2019–2020 and 300 in 2021–2024."
    )
    assert coding_caption(primary, 2019, 2024).startswith(
        "OTHER fell from 200-300/year (2019-2020) to 0 from 2022"
    )


def test_cost_caption_counts_follow_the_selected_year():
    from report_text import permanent_caption

    counts = pd.DataFrame(
        {
            "year": [2023] * 3 + [2024] * 3,
            "group": [
                "temporary abandonment",
                "permanent abandonment",
                "abandonment unspecified",
            ]
            * 2,
            "permits": [1, 2, 3, 10, 20, 30],
        }
    )
    assert "(20 of 60 abandonment approvals in 2024)" in permanent_caption(counts, 2024)
    assert "(2 of 6 abandonment approvals in 2023)" in permanent_caption(counts, 2023)


def test_selection_check_accepts_pooled_periods_and_rejects_other_years():
    from report_text import check_selection

    summary = {"first_full_year": 2005, "last_full_year": 2024}
    assert check_selection(summary, {"t": ["2024", "2020-2024"]}) == 2024
    with pytest.raises(ValueError, match="selects 2024"):
        check_selection(summary, {"t": ["2025", "2021-2025"]})


def test_full_year_bounds_follow_feed_start_and_file_date():
    from count_interventions import full_year_bounds

    approvals = pd.to_datetime(pd.Series(["2004-04-02", "2004-05-01", "2026-11-10"]))
    assert full_year_bounds(approvals, date(2026, 11, 13)) == (2005, 2025)
    january = pd.to_datetime(pd.Series(["2004-01-05"]))
    assert full_year_bounds(january, date(2026, 12, 31)) == (2004, 2026)


def test_download_snapshot_name_is_validated_before_any_request():
    import download_data

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        download_data.main(["--snapshot", "13-11-2026"])
