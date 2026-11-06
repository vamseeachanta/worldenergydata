"""Independent synthetic checks for the issue-416/419 aggregate contract.

Counts below are hand enumerations, not outputs copied from the implementation.
No production incident records are used. Five is the publication floor from the
2026-05-18 issue-416 plan, Operator Aggregation Contract, rule 2.
"""

import json
from dataclasses import asdict
from datetime import date

import pytest

from worldenergydata.bsee.analysis.intervention.hse_patterns import (
    assess_patterns,
    atlantic_season,
)


def period(**changes):
    row = {
        "BUS_ASC_NAME": "synthetic identity",
        "BOTM_LEASE_NUM": "synthetic lease",
        "WAR_START_DT": "2024-01-01",
        "WAR_END_DT": "2024-12-31",
        "vendor_type": "wireline",
    }
    return row | changes


def event(index, **changes):
    row = {
        "incident_id": f"synthetic-{index}",
        "source": "BSEE",
        "record_kind": "incident",
        "operator": "SYNTHETIC IDENTITY",
        "lease_number": "synthetic lease",
        "incident_date": "2024-06-01",
        "activity_code": "PERS",
    }
    return row | changes


def balanced_events():
    """Three activities, each with five June and five January incidents.

    By enumeration: PERS=PSAFE=CRANE=10; hurricane=15, non_hurricane=15;
    wireline=30. These are descriptive counts, with no exposure denominator.
    """
    return [
        event(f"{activity}-{day}-{i}", activity_code=activity, incident_date=day)
        for activity in ("PERS", "PSAFE", "CRANE")
        for day in ("2024-06-01", "2024-01-01")
        for i in range(5)
    ]


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2024, 5, 31), "non_hurricane"),
        (date(2024, 6, 1), "hurricane"),
        (date(2024, 11, 30), "hurricane"),
        (date(2024, 12, 1), "non_hurricane"),
        (date(2024, 2, 29), "non_hurricane"),
    ],
)
def test_season_boundaries(day, expected):
    """NHC Tropical Cyclone Climatology (accessed 2026-10-22): Jun 1-Nov 30."""
    assert atlantic_season(day) == expected


def test_empty_inputs_remain_not_evaluated():
    """An empty inventory supplies no evidence for any of the four patterns."""
    result = assess_patterns([], [])
    assert [p.pattern for p in result.patterns] == ["p5", "p6", "p7", "p8"]
    assert all(p.status == "NOT_EVALUATED" for p in result.patterns)
    assert all(p.cells == () for p in result.patterns)
    assert all(p.statistic is None and p.p_value is None for p in result.patterns)


def test_balanced_counts_and_audit_trace():
    """Hand enumeration is in balanced_events; every incident maps to window 0.

    Three bins of ten and two of fifteen satisfy the five-incident floor.
    Missing inference and denominators still prohibit a pattern claim.
    """
    result = assess_patterns(balanced_events(), [period()])
    p5, p6, p7, p8 = result.patterns
    assert p5.cells == (("PERS", 10), ("PSAFE", 10), ("CRANE", 10))
    assert p6.cells == (("hurricane", 15), ("non_hurricane", 15))
    assert p7.cells == ()
    assert p8.cells == (("wireline", 30),)
    assert result.matched_pairs == tuple((i, 0) for i in range(30))
    assert all(p.status == "NOT_EVALUATED" for p in result.patterns)
    assert "exposure_denominator_required" in p6.reasons
    assert "rig_age_and_rig_exposure_required" in p7.reasons
    assert "statistical_sanity_not_evaluated" in p5.reasons


@pytest.mark.parametrize("count", [0, 1, 4])
def test_sparse_cells_withhold_entire_table(count):
    """PERS=5, PSAFE=5, CRANE=count: a sparse cell hides all cells and margins.

    Zero is also below the issue-419 floor. Withholding the entire table avoids
    reconstructing one hidden cell from the remaining counts and a total.
    """
    rows = [
        event(f"{code}-{i}", activity_code=code)
        for code, n in (("PERS", 5), ("PSAFE", 5), ("CRANE", count))
        for i in range(n)
    ]
    result = assess_patterns(rows, [period()])
    assert result.patterns[0].cells == ()
    assert "small_cell_table_withheld" in result.patterns[0].reasons
    # The public projection also withholds other tables when any table is sparse,
    # preventing reconstruction through totals in overlapping pattern cuts.
    public = result.public_summary()
    assert all(p["cells"] == [] for p in public["patterns"])
    assert "matched_pairs" not in public
    assert "join_counts" not in public


def test_floor_is_inclusive():
    """Five records per activity is allowed by n>=5, exactly at the floor."""
    rows = [
        event(f"{code}-{i}", activity_code=code)
        for code in ("PERS", "PSAFE", "CRANE")
        for i in range(5)
    ]
    assert assess_patterns(rows, [period()]).patterns[0].cells == (
        ("PERS", 5),
        ("PSAFE", 5),
        ("CRANE", 5),
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"source": "OSHA"},
        {"source": None},
        {"record_kind": "violation"},
        {"record_kind": None},
    ],
)
def test_source_and_record_kind_are_required(changes):
    """Thirty unqualified rows give zero matched pairs, never thirty incidents."""
    rows = [row | changes for row in balanced_events()]
    result = assess_patterns(rows, [period()])
    assert result.matched_pairs == ()
    assert result.excluded_rows == tuple(range(30))
    assert all(p.cells == () for p in result.patterns)


@pytest.mark.parametrize("identifier", [None, "", " ", 3, True])
def test_missing_incident_ids_are_rejected(identifier):
    """Missing stable IDs prevent deduplication, so the batch is rejected."""
    with pytest.raises(ValueError, match="incident_id must be nonempty text"):
        assess_patterns([event(0, incident_id=identifier)], [period()])


def test_duplicate_ids_rejected_after_whitespace_normalization():
    """Two copies of one ID cannot supply two independent incident counts."""
    with pytest.raises(ValueError, match="duplicate incident_id"):
        assess_patterns([event(0), event(0, incident_id=" synthetic-0 ")], [period()])


def test_invalid_and_ambiguous_matches_never_enter_tables():
    """Two identical windows make 30 rows ambiguous; a missing key is invalid."""
    rows = balanced_events() + [event("invalid", lease_number=None)]
    result = assess_patterns(rows, [period(), period()])
    assert result.matched_pairs == ()
    assert result.join_counts == {
        "matched": 0,
        "unmatched": 0,
        "invalid_key": 1,
        "ambiguous": 30,
    }
    assert all(p.cells == () for p in result.patterns)


def test_unmatched_is_not_a_non_intervention_control():
    """Thirty incidents outside the supplied span contribute no control cohort."""
    result = assess_patterns(balanced_events(), [period(WAR_END_DT="2023-12-31")])
    assert result.invalid_window_indices == (0,)
    assert result.join_counts["unmatched"] == 30
    assert all(p.cells == () for p in result.patterns)


@pytest.mark.parametrize("activity", [None, "DRILL", "PERS.fall", "free text"])
def test_unqualified_activity_prevents_partial_mix(activity):
    """One unknown classification hides p5 rather than changing its denominator."""
    rows = balanced_events() + [event("unknown", activity_code=activity)]
    p5 = assess_patterns(rows, [period()]).patterns[0]
    assert p5.cells == ()
    assert "activity_classification_required" in p5.reasons


@pytest.mark.parametrize("count", [0, 1, 4])
def test_missing_activity_preserves_sparse_known_cell_suppression(count):
    """PERS=10, PSAFE=10, CRANE=count plus one unclassified incident.

    Season and vendor cells exceed the floor. Missing activity must retain the
    sparse-cell reason so that overlapping public tables are also withheld.
    """
    rows = [row for row in balanced_events() if row["activity_code"] != "CRANE"]
    rows += [event(f"crane-{i}", activity_code="CRANE") for i in range(count)]
    rows += [event("unknown", activity_code=None)]
    result = assess_patterns(rows, [period()])
    p5, p6, _, p8 = result.patterns
    assert p5.cells == ()
    assert "activity_classification_required" in p5.reasons
    assert "small_cell_table_withheld" in p5.reasons
    assert p6.cells == (("hurricane", 11 + count), ("non_hurricane", 10))
    assert p8.cells == (("wireline", 21 + count),)
    assert all(p["cells"] == [] for p in result.public_summary()["patterns"])


@pytest.mark.parametrize("count", [1, 4])
def test_missing_vendor_preserves_sparse_known_cell_suppression(count):
    """Thirty wireline incidents, count pumping incidents, one unknown type.

    Activity and season cells exceed the floor. Missing vendor mapping must
    retain the sparse-cell reason and suppress every overlapping public table.
    """
    rows = balanced_events()
    rows += [event(f"pumping-{i}", lease_number="pumping lease") for i in range(count)]
    rows += [event("unknown", lease_number="unknown lease")]
    windows = [
        period(),
        period(BOTM_LEASE_NUM="pumping lease", vendor_type="pumping"),
        period(BOTM_LEASE_NUM="unknown lease", vendor_type=None),
    ]
    result = assess_patterns(rows, windows)
    p5, p6, _, p8 = result.patterns
    assert p8.cells == ()
    assert "vendor_type_required" in p8.reasons
    assert "small_cell_table_withheld" in p8.reasons
    assert p5.cells == (("PERS", 11 + count), ("PSAFE", 10), ("CRANE", 10))
    assert p6.cells == (("hurricane", 16 + count), ("non_hurricane", 15))
    assert all(p["cells"] == [] for p in result.public_summary()["patterns"])


@pytest.mark.parametrize("vendor", [None, "unapproved name", "WIRELINE", 7])
def test_vendor_names_and_unknown_types_never_echo(vendor):
    """Unqualified vendor type yields no vendor table or input-derived label."""
    result = assess_patterns(balanced_events(), [period(vendor_type=vendor)])
    assert result.patterns[3].cells == ()
    assert "vendor_type_required" in result.patterns[3].reasons
    assert "unapproved name" not in json.dumps(result.public_summary())


def test_vendor_types_are_pool_aggregated_not_operator_buckets():
    """Two identities, 15 incidents each, form one 30-incident vendor-type cell."""
    rows = balanced_events()
    for row in rows[15:]:
        row["operator"] = "second synthetic identity"
    windows = [period(), period(BUS_ASC_NAME="second synthetic identity")]
    result = assess_patterns(rows, windows)
    assert result.patterns[3].cells == (("wireline", 30),)
    public = json.dumps(result.public_summary())
    for forbidden in ("synthetic identity", "synthetic lease", "synthetic-", "15, 1"):
        assert forbidden not in public
    assert "publication_policy_review_required" in public


def test_public_projection_has_only_controlled_fields():
    """Safe 30-row input retains aggregate cells, never audit row indices."""
    result = assess_patterns(balanced_events(), [period()])
    public = result.public_summary()
    assert set(public) == {"patterns", "publication_status"}
    assert public["publication_status"] == "REVIEW_REQUIRED"
    assert public["patterns"][0]["cells"] == [
        ["PERS", 10],
        ["PSAFE", 10],
        ["CRANE", 10],
    ]
    assert all(p["status"] == "NOT_EVALUATED" for p in public["patterns"])


def test_generators_preserve_original_indices_and_inputs():
    """An excluded row at index 0 leaves matched source indices starting at 1."""
    rows = [event("excluded", source="OSHA")] + balanced_events()
    before = [row.copy() for row in rows]
    result = assess_patterns(iter(rows), iter([period()]))
    assert result.matched_pairs == tuple((i, 0) for i in range(1, 31))
    assert result.excluded_rows == (0,)
    assert rows == before
    assert asdict(result)["patterns"][0]["status"] == "NOT_EVALUATED"


def test_worked_example_matches_independent_hand_calculation():
    """The documented 3 activities x 2 dates x 5 incidents fixture has 30 rows.

    Summing independently gives ten for each activity, fifteen for each season
    and thirty for its only vendor type; p7 has no qualified rig-age evidence.
    """
    import runpy
    from pathlib import Path

    root = Path(__file__).resolve().parents[5]
    example = runpy.run_path(str(root / "examples/bsee/intervention_hse_patterns.py"))
    result = example["worked_example"]()
    assert [p["cells"] for p in result["patterns"]] == [
        [["PERS", 10], ["PSAFE", 10], ["CRANE", 10]],
        [["hurricane", 15], ["non_hurricane", 15]],
        [],
        [["wireline", 30]],
    ]
    assert all(p["status"] == "NOT_EVALUATED" for p in result["patterns"])


def test_sparse_vendor_type_withholds_other_public_cuts():
    """One pumping incident plus 30 wireline incidents fails the cell floor.

    Although p5 and p6 each have at least five in every cell, no overlapping
    table or margin may be released beside the withheld sparse vendor table.
    """
    rows = balanced_events() + [event("pump", operator="other synthetic identity")]
    windows = [
        period(),
        period(BUS_ASC_NAME="other synthetic identity", vendor_type="pumping"),
    ]
    result = assess_patterns(rows, windows)
    assert result.patterns[0].cells == (("PERS", 11), ("PSAFE", 10), ("CRANE", 10))
    assert "small_cell_table_withheld" in result.patterns[3].reasons
    assert all(p["cells"] == [] for p in result.public_summary()["patterns"])
