"""Per-well life cycle of Gulf of Mexico wells (well_life_cycle.py).

Synthetic fixture counted by hand, plus offline reconciliation of the delivered
life-cycle tables with the published permit counts. No raw archives or network.

Fixture (three wells and one unmatched permit):
  W1 6081740001 development: original spud 1 Mar 2006 (status ST), sidetrack
     spud 1 Jun 2010 (PA 1 Jul 2020), so life is 5,236 days. Permits in the
     window: WORKOVER/WL light 2012, ENHANCE/PF heavy 2014, COMP+ZONE with no
     unit 2015, TEMPABAN 2016, PERMABAN 2020. COMP without ZONE 2006 and
     PLUGBACK 2010 are excluded by the existing classification.
  W2 6081740002 exploration: spud 10 Jan 2008, PA 1 Mar 2008 (51 days);
     PERMABAN/JU 2008 and ABANDON with no subcode 2008 (type not stated).
  W3 6081740003 development: spud 1 May 1990, COM, so standing to the file
     date; WORKOVER/LB light 2005, WORKOVER/HW 2004 (before the window),
     OTHER with an unmatched unit 2025 (not established).
  A cancelled-only well (6081740004) has no dated life and is dropped.
  One WORKOVER 2011 on 6081749999, which has no borehole: not assigned.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/interventions_by_depth"
sys.path.insert(0, str(EXAMPLE))
import well_life_cycle as lc  # noqa: E402
from count_interventions import (  # noqa: E402
    ABANDONMENT,
    UNIT_TYPES,
    WELL_WORK,
    classify_operation,
    report_years,
    well_inventory,
)

WINDOW = list(range(2005, 2027))
FILE_DATE = "2026-11-13"
STAGES = [
    "drilling",
    "sidetrack or bypass",
    "light intervention",
    "heavy intervention",
    "intervention, light or heavy not established",
    "temporary abandonment",
    "abandonment, type not stated",
    "permanent abandonment",
]
RIGS = pd.DataFrame(
    {
        "RIG_ID_NUM": ["R1", "R2", "R3", "R4", "R5"],
        "RIG_TYPE_CODE": ["WL", "PF", "JU", "LB", "HW"],
    }
)


def _bore():
    rows = [
        ("608174000100", "ST00BP00", "03/01/2006", "ST", "06/01/2010", "D"),
        ("608174000101", "ST01BP00", "06/01/2010", "PA", "07/01/2020", "D"),
        ("608174000200", "ST00BP00", "01/10/2008", "PA", "03/01/2008", "E"),
        ("608174000300", "ST00BP00", "05/01/1990", "COM", "05/01/1991", "D"),
        ("608174000400", "ST00BP00", "05/01/1995", "CNL", "05/01/1995", "D"),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "API_WELL_NUMBER",
            "WELL_NAME_SUFFIX",
            "WELL_SPUD_DATE",
            "BOREHOLE_STAT_CD",
            "BOREHOLE_STAT_DT",
            "WELL_TYPE_CODE",
        ],
    )
    frame["REGION_CODE"] = "G"
    frame["WATER_DEPTH"] = "300"
    return frame


def _permits():
    rows = [
        ("1", "608174000100", "05/01/2012", "WORKOVER", {"ZONE"}, "R1"),
        ("2", "608174000100", "05/01/2014", "ENHANCE", set(), "R2"),
        ("3", "608174000101", "05/01/2015", "COMP", {"ZONE"}, ""),
        ("4", "608174000101", "05/01/2016", "ABANDON", {"TEMPABAN"}, "R1"),
        ("5", "608174000101", "05/01/2020", "ABANDON", {"PERMABAN", "TEMPABAN"}, "R1"),
        ("6", "608174000100", "05/01/2006", "COMP", set(), "R2"),
        ("7", "608174000100", "05/01/2010", "ABANDON", {"PLUGBACK"}, "R2"),
        ("8", "608174000200", "02/01/2008", "ABANDON", {"PERMABAN"}, "R3"),
        ("9", "608174000200", "02/15/2008", "ABANDON", set(), "R3"),
        ("10", "608174000300", "05/01/2005", "WORKOVER", set(), "R4"),
        ("11", "608174000300", "05/01/2004", "WORKOVER", set(), "R5"),
        ("12", "608174000300", "05/01/2025", "OTHER", set(), "R404"),
        ("13", "608174999900", "05/01/2011", "WORKOVER", set(), "R1"),
    ]
    frame = pd.DataFrame(
        [r[:4] + (r[5],) for r in rows],
        columns=[
            "SN_APM",
            "API_WELL_NUMBER",
            "ACC_STATUS_DATE",
            "APM_OP_CD",
            "RIG_ID_NUM",
        ],
    )
    frame["group"] = [classify_operation(r[3], r[4]) for r in rows]
    frame["family"] = frame.group.map(
        lambda g: (
            "well work"
            if g in WELL_WORK
            else "abandonment" if g in ABANDONMENT else "excluded"
        )
    )
    frame["year"] = pd.to_datetime(frame.ACC_STATUS_DATE).dt.year
    frame["band"] = "100 to 500 m"
    return frame


def _wells():
    bore = _bore()
    events = lc.permit_events(_permits(), RIGS, WINDOW)
    wells = lc.well_table(
        well_inventory(bore),
        lc.gulf_bores(bore),
        events,
        lc.well_types(bore),
        FILE_DATE,
    )
    return bore, events, wells


@pytest.mark.parametrize(
    "code,weight",
    [
        ("WL", "light"),
        ("CT", "light"),
        ("WI", "light"),
        ("LB", "light"),
        ("NR", "light"),
        ("HW", "heavy"),
        ("SB", "heavy"),
        ("PF", "heavy"),
        ("JU", "heavy"),
        ("DS", "heavy"),
        ("SS", "heavy"),
        ("SD", "heavy"),
        ("SU", "not established"),
        ("BG", "not established"),
        ("", "not established"),
    ],
)
def test_intervention_weight_rule(code, weight):
    assert lc.intervention_weight(code) == weight


def test_weights_keep_the_existing_unit_categories():
    assert not lc.LIGHT_CODES & lc.HEAVY_CODES
    assert lc.LIGHT_CODES | lc.HEAVY_CODES <= set(UNIT_TYPES)
    # Only the merged liftboat / jack-up category is divided, by source code.
    for codes in (lc.LIGHT_CODES, lc.HEAVY_CODES):
        for category in {UNIT_TYPES[c] for c in codes} - {"liftboat / jack-up"}:
            assert {c for c, v in UNIT_TYPES.items() if v == category} <= codes


def test_per_well_counts_match_hand_counts():
    _, _, wells = _wells()
    wells = wells.set_index("api10")
    expected = {
        "6081740001": [1, 1, 1, 1, 1, 1, 0, 1],
        "6081740002": [1, 0, 0, 0, 0, 0, 1, 1],
        "6081740003": [1, 0, 1, 0, 1, 0, 0, 0],
    }
    assert sorted(wells.index) == sorted(expected)
    for api, counts in expected.items():
        assert wells.loc[api, STAGES].tolist() == counts, api


def test_life_years_status_and_type():
    _, _, wells = _wells()
    wells = wells.set_index("api10")
    assert wells.loc["6081740001", "life_years"] == pytest.approx(5236 / 365.25)
    assert wells.loc["6081740001", "status"] == "permanently abandoned"
    assert wells.loc["6081740001", "well_type"] == "development"
    assert wells.loc["6081740002", "life_years"] == pytest.approx(51 / 365.25)
    assert wells.loc["6081740002", "well_type"] == "exploration"
    # 1 May 1990 to 13 Nov 2026: 36 years with 9 leap days, then 196 days.
    assert wells.loc["6081740003", "life_years"] == pytest.approx(
        (36 * 365 + 9 + 196) / 365.25
    )
    assert wells.loc["6081740003", "status"] == "standing"


def test_totals_reconcile_with_permit_counts():
    _, events, wells = _wells()
    published = pd.DataFrame(
        {
            "year": [2015, 2016, 2020, 2008, 2008, 2004],
            "group": [
                "workover and recompletion",
                "temporary abandonment",
                "permanent abandonment",
                "permanent abandonment",
                "abandonment unspecified",
                "workover and recompletion",
            ],
            # Interventions 2005-2026: W1 3, W3 2 and the unmatched permit 1.
            # The 2004 row is outside the window and is not compared.
            "permits": [6, 1, 1, 1, 1, 1],
        }
    )
    table = lc.reconcile(wells, events, published, WINDOW).set_index("stage")
    columns = [
        "published_permits",
        "permits_in_events",
        "assigned_to_dated_wells",
        "not_assigned",
    ]
    assert table.loc["intervention, all", columns].tolist() == [6, 6, 5, 1]
    assert table.loc["permanent abandonment", columns].tolist() == [2, 2, 2, 0]
    assert table.loc["temporary abandonment", columns].tolist() == [1, 1, 1, 0]
    assert table.loc["abandonment, type not stated", columns].tolist() == [1, 1, 1, 0]
    published.loc[0, "permits"] = 7
    with pytest.raises(ValueError, match="do not reconcile"):
        lc.reconcile(wells, events, published, WINDOW)


def test_stage_reach_and_event_ages_by_hand():
    bore, events, wells = _wells()
    groups = lc.cohorts(wells, 2005, 2025)
    assert [int(m.sum()) for m in groups.values()] == [1, 1]
    reach = lc.stage_reach(wells, groups).set_index(["group", "stage"])
    dev = "development wells first drilled 2005-2025"
    assert reach.loc[(dev, "sidetrack or bypass"), "wells"] == 1
    assert reach.loc[(dev, "sidetrack or bypass"), "share_percent"] == 100
    assert reach.loc[(dev, "abandonment, type not stated"), "share_percent"] == 0
    assert (
        reach.loc[(dev, "permanently abandoned (bore status)"), "wells_reaching"] == 1
    )
    exp = "exploration wells first drilled 2005-2025"
    assert reach.loc[(exp, "permanent abandonment"), "events_per_well"] == 1
    ages = lc.event_ages(lc.gulf_bores(bore), events, wells, WINDOW)
    sidetrack = ages[ages.stage.eq("sidetrack or bypass")].age_years.item()
    # 1 Mar 2006 to 1 Jun 2010: 4 years with 1 leap day (2008), then 92 days.
    assert sidetrack == pytest.approx((4 * 365 + 1 + 92) / 365.25)
    summary = lc.age_summary(ages, WINDOW).set_index(["well_type", "stage"])
    assert summary.loc[("all wells", "light intervention"), "events"] == 2


def test_light_heavy_by_year_partitions_well_work():
    _, events, _ = _wells()
    standing = pd.DataFrame({"year": WINDOW, "standing_wells": 100})
    table = lc.weight_by_year(events, standing, WINDOW).set_index(["year", "weight"])
    assert table.loc[(2005, "light"), "approvals"] == 1
    assert table.loc[(2011, "light"), "approvals"] == 1  # unmatched well counted
    assert table.loc[(2025, "not established"), "per_100_standing_wells"] == 1.0
    assert table.approvals.sum() == 6


def test_delivered_tables_reconcile_with_published_counts():
    out = EXAMPLE / "output"
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    window = report_years(summary)
    counts = pd.read_csv(out / "counts_by_year_band_group.csv")
    counts = counts[counts.year.isin(window)]
    checks = pd.read_csv(out / "life_cycle_reconciliation.csv").set_index("stage")
    groups = {
        "temporary abandonment": ["temporary abandonment"],
        "permanent abandonment": ["permanent abandonment"],
        "abandonment, type not stated": ["abandonment unspecified"],
        "intervention, all": [
            "workover and recompletion",
            "production enhancement",
            "other well work",
        ],
    }
    for stage, source in groups.items():
        published = counts.loc[counts.group.isin(source), "permits"].sum()
        row = checks.loc[stage]
        assert row.published_permits == published == row.permits_in_events
        assert row.assigned_to_dated_wells + row.not_assigned == published
    weights = pd.read_csv(out / "intervention_weight_by_year.csv")
    rates = pd.read_csv(out / "rates.csv")
    work = rates[rates.family.eq("well work")].groupby("year").permits.sum()
    assert weights.groupby("year").approvals.sum().reindex(work.index).equals(work)
    reach = pd.read_csv(out / "life_cycle_stage_reach.csv")
    assert (reach.wells_reaching <= reach.wells).all()
    assert (reach.wells_reaching <= reach.events).all()
    hist = pd.read_csv(out / "life_cycle_life_histogram.csv")
    life = json.loads((out / "life_cycle_summary.json").read_text(encoding="utf-8"))
    assert hist.wells.sum() == life["dated_wells"] - life["life_not_established"]
    assert life["permanently_abandoned"] + life["standing"] == life["dated_wells"]


def test_raw_archives_are_verified_before_the_life_cycle_reads_them(tmp_path):
    import count_interventions as ci

    from tests.unit.bsee import interventions_archives as fixture

    data = fixture.build(tmp_path / "2026-11-13")
    out = tmp_path / "output"
    ci.run(data, out)
    lc.run(data, out)
    before = {p.name: p.read_bytes() for p in out.glob("life_cycle_*")}
    # Change a first-spud date after the manifest was written. Both manifests
    # stay equal and the permit totals still reconcile; only the bytes differ.
    fixture.write_borehole(data, first_spud="03/01/2001")
    with pytest.raises(ValueError, match="digest mismatch: BoreholeRawData.zip"):
        lc.run(data, out)
    assert {p.name: p.read_bytes() for p in out.glob("life_cycle_*")} == before


def test_sidetrack_ages_use_the_permit_window():
    bore = _bore()
    # A 1991 sidetrack on W3 lies before the 2005-2026 permit window.
    extra = bore.iloc[[3]].assign(
        API_WELL_NUMBER="608174000301",
        WELL_NAME_SUFFIX="ST01BP00",
        WELL_SPUD_DATE="06/01/1991",
    )
    bore = pd.concat([bore, extra], ignore_index=True)
    bores = lc.gulf_bores(bore)
    events = lc.permit_events(_permits(), RIGS, WINDOW)
    wells = lc.well_table(
        well_inventory(bore), bores, events, lc.well_types(bore), FILE_DATE
    )
    ages = lc.event_ages(bores, events, wells, WINDOW)
    assert ages.date.dt.year.isin(WINDOW).all()
    sidetracks = ages[ages.stage.eq("sidetrack or bypass")]
    assert sidetracks.api10.tolist() == ["6081740001"]
    summary = lc.age_summary(ages, WINDOW).set_index(["well_type", "stage"])
    assert summary.loc[("all wells", "sidetrack or bypass"), "events"] == 1
    assert summary.event_window.eq("2005-2026").all()


def test_age_at_permanent_abandonment_counts_approvals_not_wells():
    """A repeated approval on an abandoned well and an approval on a well that
    still stands both enter the age at permanent-abandonment approval."""
    bore = _bore()
    permits = _permits()
    extra = permits.iloc[[4, 4]].copy()  # PERMABAN on W1
    extra["SN_APM"] = ["14", "15"]
    extra["API_WELL_NUMBER"] = ["608174000101", "608174000300"]
    extra["ACC_STATUS_DATE"] = ["05/01/2021", "05/01/2024"]  # repeat on W1; W3 stands
    extra["year"] = [2021, 2024]
    permits = pd.concat([permits, extra], ignore_index=True)
    bores = lc.gulf_bores(bore)
    events = lc.permit_events(permits, RIGS, WINDOW)
    wells = lc.well_table(
        well_inventory(bore), bores, events, lc.well_types(bore), FILE_DATE
    )
    dev = wells[wells.well_type.eq("development")].set_index("api10")
    assert dev.status.to_dict() == {
        "6081740001": "permanently abandoned",
        "6081740003": "standing",
    }
    ages = lc.event_ages(bores, events, wells, WINDOW)
    pa = ages[ages.well_type.eq("development") & ages.stage.eq("permanent abandonment")]
    assert pa.api10.tolist().count("6081740001") == 2
    assert "6081740003" in pa.api10.tolist()
    summary = lc.age_summary(ages, WINDOW).set_index(["well_type", "stage"])
    row = summary.loc[("development", "permanent abandonment")]
    assert row.events == 3  # three approvals on two wells, one of them standing
    # W1 at 1 May 2020 and 2021 (14.2, 15.2 years); W3 at 1 May 2024 (34.0).
    assert row.median_years == pytest.approx(pa.age_years.median())
    assert 15 < row.median_years < 15.3
