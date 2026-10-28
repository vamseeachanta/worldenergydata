"""Independent hand calculations for the local republication audit.

All dates, identifiers and day counts in synthetic fixtures are test inputs,
not operating assumptions or acceptance limits.
"""

import csv
import hashlib
import json
from pathlib import Path

import pytest
from lower_tertiary import build_dc_republication_audit as audit

REPO = Path(__file__).resolve().parents[3]


def write_csv(path, rows, columns=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def inputs(tmp_path):
    """Jan1 spud, Jan8 TD; DRL Jan1-7, PND Jan8-14, COM Jan22-28.

    Milestone: D=8-1=7, C=7+7=14 (Jan15-21 gap excluded), D&C=21.
    Activity: DRL=7, COM=7, PND=7, union=21; D&C=14.
    Interim: D=8, C=28-8+1=21, D&C=29 (TD counted in both).
    Published test inputs D=6, C=10, D&C=16 give deltas +5,-2,+13.
    A second bore has missing records and legacy zero placeholders.
    """
    root = tmp_path / "repository"
    rows = [
        {
            "LEASE_NAME": "synthetic",
            "API_WELL_NUMBER": "100000000001",
            "WELL_SPUD_DATE": "01/01/2020",
            "TOTAL_DEPTH_DATE": "01/08/2020",
            "DRILLING_DAYS": "6",
            "COMPLETION_DAYS": "10",
        },
        {
            "LEASE_NAME": "synthetic",
            "API_WELL_NUMBER": "100000000002",
            "WELL_SPUD_DATE": "",
            "TOTAL_DEPTH_DATE": "",
            "DRILLING_DAYS": "0",
            "COMPLETION_DAYS": "0",
        },
    ]
    write_csv(root / audit.SOURCE, rows)
    weekly = [
        {
            "API_WELL_NUMBER": rows[0]["API_WELL_NUMBER"],
            "WAR_START_DT": start,
            "WAR_END_DT": end,
            "WELL_ACTIVITY_CD": code,
        }
        for start, end, code in [
            ("2020-01-01", "2020-01-07", "DRL"),
            ("2020-01-08", "2020-01-14", "PND"),
            ("2020-01-22", "2020-01-28", "COM"),
        ]
    ]
    write_csv(root / audit.WEEKLY / "war_data_synthetic.csv", weekly)
    write_csv(root / audit.SAMPLE, [], columns=list(weekly[0]))
    return root, rows, weekly


def test_three_methods_and_change_are_kept_side_by_side(inputs):
    """Fixture docstring derives all expected values independently."""
    result = audit.build_audit(inputs[0])
    bore = result["bores"][0]
    assert bore["before"] == {"drilling_days": 6, "completion_days": 10, "dc_days": 16}
    expected = {
        "milestone": (7, 14, 21, 5),
        "activity_code": (7, 7, 14, -2),
        "interim": (8, 21, 29, 13),
    }
    for method, (drill, complete, total, delta) in expected.items():
        comparison = bore["methods"][method]
        assert comparison["after"] == {
            "drilling_days": drill,
            "completion_days": complete,
            "dc_days": total,
        }
        assert comparison["delta"]["dc_days"] == delta
        assert comparison["basis"]
    assert bore["activity_breakdown"]["pnd_days"] == 7
    assert bore["activity_breakdown"]["total_days"] == 21
    assert bore["activity_breakdown"]["gap_count"] == 1


def test_missing_records_do_not_become_zero_or_full_field_totals(inputs):
    """Only one of two bores is paired: 16 -> 21, delta5; no field delta."""
    result = audit.build_audit(inputs[0])
    missing = result["bores"][1]
    assert missing["coverage"] == "absent"
    assert missing["before"]["dc_days"] == 0  # Preserve the displayed snapshot.
    assert missing["before_basis"] == "unlabelled legacy output"
    for method in missing["methods"].values():
        assert set(method["after"].values()) == {None}
        assert set(method["delta"].values()) == {None}
    field = result["developments"][0]
    assert field["before"]["dc_days"] == 16
    assert field["coverage"] == {"absent": 1, "per-well history": 1}
    milestone = field["methods"]["milestone"]
    assert milestone["after"] is None
    assert milestone["delta"] is None
    paired = milestone["paired_by_coverage"]["per-well history"]["dc_days"]
    assert paired == {"bores": 1, "before": 16, "after": 21, "delta": 5}


def test_no_records_no_numeric_pair(inputs):
    root, rows, _weekly = inputs
    write_csv(root / audit.SOURCE, rows[1:])
    result = audit.build_audit(root)
    for method in result["developments"][0]["methods"].values():
        assert method["paired_by_coverage"] == {}
    assert result["publication"]["status"] == "NOT_EVALUATED"


def test_legacy_placeholder_is_not_a_numeric_comparison(inputs):
    """A known COM Jan22-28=7 cannot turn an undated zero into a measurement."""
    root, _, weekly = inputs
    write_csv(
        root / audit.SAMPLE,
        [dict(weekly[-1], API_WELL_NUMBER="100000000002")],
    )
    result = audit.build_audit(root)
    bore = result["bores"][1]
    assert bore["before"]["completion_days"] == 0
    assert bore["methods"]["activity_code"]["after"]["completion_days"] == 7
    assert bore["methods"]["activity_code"]["delta"]["completion_days"] is None
    paired = result["developments"][0]["methods"]["activity_code"]["paired_by_coverage"]
    assert paired["sparse operational sample"]["completion_days"]["bores"] == 0


def test_sparse_samples_are_separated_from_per_well_histories(inputs):
    """Sample COM Feb1-7=7; it must not enter the history's 16->21 pair."""
    root, rows, weekly = inputs
    rows[1].update(WELL_SPUD_DATE="01/01/2020", TOTAL_DEPTH_DATE="01/08/2020")
    write_csv(root / audit.SOURCE, rows)
    write_csv(
        root / audit.SAMPLE,
        [
            dict(
                weekly[-1],
                API_WELL_NUMBER=rows[1]["API_WELL_NUMBER"],
                WAR_START_DT="2020-02-01",
                WAR_END_DT="2020-02-07",
            )
        ],
    )
    result = audit.build_audit(root)
    pairs = result["developments"][0]["methods"]["milestone"]["paired_by_coverage"]
    assert pairs["per-well history"]["dc_days"]["bores"] == 1
    assert pairs["sparse operational sample"]["completion_days"]["after"] == 7
    assert result["publication"]["status"] == "NOT_EVALUATED"


def test_missing_code_and_missing_dates_stay_null(inputs):
    """DRL-only weeks give no COM measurement; missing TD denies milestones."""
    root, rows, weekly = inputs
    rows[0]["TOTAL_DEPTH_DATE"] = ""
    write_csv(root / audit.SOURCE, rows)
    write_csv(root / audit.WEEKLY / "war_data_synthetic.csv", weekly[:1])
    bore = audit.build_audit(root)["bores"][0]
    assert bore["methods"]["milestone"]["after"]["dc_days"] is None
    assert bore["methods"]["activity_code"]["after"]["drilling_days"] == 7
    assert bore["methods"]["activity_code"]["after"]["completion_days"] is None
    assert bore["methods"]["activity_code"]["after"]["dc_days"] is None


def test_same_day_milestone_is_a_measured_zero(inputs):
    """Jan1 minus Jan1=0 drilling; all three reported weeks total21."""
    root, rows, _ = inputs
    rows[0]["TOTAL_DEPTH_DATE"] = rows[0]["WELL_SPUD_DATE"]
    write_csv(root / audit.SOURCE, rows)
    method = audit.build_audit(root)["bores"][0]["methods"]["milestone"]
    assert method["after"] == {"drilling_days": 0, "completion_days": 21, "dc_days": 21}


@pytest.mark.parametrize("invalid", ["-1", "1.5", "nan", "inf", "invalid"])
def test_invalid_published_counts_fail_closed(inputs, invalid):
    root, rows, _ = inputs
    rows[0]["DRILLING_DAYS"] = invalid
    write_csv(root / audit.SOURCE, rows)
    with pytest.raises(ValueError, match="day count"):
        audit.build_audit(root)


@pytest.mark.parametrize("problem", ["duplicate", "missing_api", "missing_lease"])
def test_population_identity_is_required(inputs, problem):
    root, rows, _ = inputs
    if problem == "duplicate":
        rows.append(rows[0])
    elif problem == "missing_api":
        rows[0]["API_WELL_NUMBER"] = ""
    else:
        rows[0]["LEASE_NAME"] = ""
    write_csv(root / audit.SOURCE, rows)
    with pytest.raises(ValueError, match="population"):
        audit.build_audit(root)


def test_invalid_weekly_intervals_are_not_reported_as_zero(inputs):
    root, _, weekly = inputs
    weekly[0]["WAR_END_DT"] = "2019-12-31"
    write_csv(root / audit.WEEKLY / "war_data_synthetic.csv", weekly[:1])
    bore = audit.build_audit(root)["bores"][0]
    assert bore["status"] == "NOT_EVALUATED"
    assert "usable" in bore["reason"]
    for method in bore["methods"].values():
        assert method["after"]["dc_days"] is None


def test_grouping_reuses_listing_development_mapping(inputs, monkeypatch):
    root, rows, _ = inputs
    rows[1]["LEASE_NAME"] = "other synthetic lease"
    write_csv(root / audit.SOURCE, rows)
    monkeypatch.setattr(audit, "DEV_OF_LEASE", {"other synthetic lease": "synthetic"})
    assert len(audit.build_audit(root)["developments"]) == 1


def test_input_digests_track_source_bytes(inputs):
    root, _, _ = inputs
    result = audit.build_audit(root)
    assert {item["path"] for item in result["inputs"]} == {
        audit.SOURCE.as_posix(),
        audit.SAMPLE.as_posix(),
        (audit.WEEKLY / "war_data_synthetic.csv").as_posix(),
    }
    for item in result["inputs"]:
        assert not Path(item["path"]).is_absolute()
        assert (
            item["sha256"]
            == hashlib.sha256((root / item["path"]).read_bytes()).hexdigest()
        )


def test_cli_is_deterministic_and_writes_only_requested_output(inputs, tmp_path):
    root, _, _ = inputs
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    output = tmp_path / "audit.json"
    args = ["--root", str(root), "--output", str(output)]
    assert audit.main(args) == 0
    first = output.read_bytes()
    assert audit.main(args) == 0
    assert output.read_bytes() == first
    assert {p: p.read_bytes() for p in before} == before
    result = json.loads(first)
    assert result["default_basis"] == "milestone"
    for check in ("publication", "npv_impact", "surface_agreement"):
        assert result[check]["status"] == "NOT_EVALUATED"


def test_cli_refuses_output_within_repository(inputs):
    root, _, _ = inputs
    with pytest.raises(SystemExit):
        audit.main(["--root", str(root), "--output", str(root / "audit.json")])
    assert not (root / "audit.json").exists()


def test_committed_reference_and_population_are_audited_without_republishing():
    """Repository reference: rig_days_summary.md:18 totals151+87+49+21=308.

    Summary source: docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md,
    2025-06-02, "Summary and Way Forward". Held intervals: rows2-46 of
    docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv.
    The held CSV instead allocates COM13*7=91, TA7+7+3=17; DRL4+21*7=151.
    Milestone note dates: Jul24-Dec26=7+31+30+31+30+26=155 days;
    post-TD PND44 + TA17 + COM91=152. No new day-rate or NPV is assumed.
    Population and missing coverage are counted independently from CSV keys.
    """
    result = audit.build_audit(REPO)
    bore = next(b for b in result["bores"] if b["api12"] == "608124009500")
    assert bore["activity_breakdown"]["drilling_days"] == 151
    assert bore["activity_breakdown"]["total_days"] == 308
    assert bore["methods"]["milestone"]["after"] == {
        "drilling_days": 155,
        "completion_days": 152,
        "dc_days": 307,
    }
    with (REPO / audit.SOURCE).open(encoding="utf-8", newline="") as stream:
        published = list(csv.DictReader(stream))
    assert {b["api12"] for b in result["bores"]} == {
        row["API_WELL_NUMBER"] for row in published
    }
    assert sum(d["bores"] for d in result["developments"]) == len(published)
    assert result["publication"]["status"] == "NOT_EVALUATED"


def test_review_shows_all_methods_paired_counts_and_unavailable_field_totals(inputs):
    """Fixture: paired D&C16 -> milestone21 (+5), activity14 (-2), interim29 (+13).

    The second bore is absent, so no replacement total or NPV delta is known.
    """
    result = audit.build_audit(inputs[0])
    report = audit.render_markdown(result, revision_date="2026-10-21")
    assert "## Revision history" in report
    assert report.index("## Revision history") < report.index("## Publication")
    assert "| synthetic | 2 | 6 | 10 | 16 | NOT_EVALUATED |" in report
    for method, after, delta in [
        ("milestone", 21, "+5"),
        ("activity_code", 14, "-2"),
        ("interim", 29, "+13"),
    ]:
        assert (
            f"| synthetic | {method} | per-well history | dc_days | 1 | 16 | {after} | {delta} |"
            in report
        )
    assert "| synthetic | NOT_EVALUATED |" in report
    assert "100000000002" in report  # Absent weekly input is actionable.
    assert "Paired subtotals are not replacement development totals" in report
    assert "unlabelled legacy output" in report
    assert audit.WAR_METHODOLOGY.strip() in report
    assert all(d["npv_impact"]["delta_usd"] is None for d in result["developments"])


def test_review_escapes_source_text_in_tables(inputs):
    root, rows, _ = inputs
    rows[0]["LEASE_NAME"] = "synthetic | <script>"
    write_csv(root / audit.SOURCE, rows)
    report = audit.render_markdown(audit.build_audit(root), revision_date="2026-10-21")
    assert "synthetic &#124; &lt;script&gt;" in report
    assert "<script>" not in report


def test_cli_can_write_deterministic_review_outside_repository(inputs, tmp_path):
    root, _, _ = inputs
    output, review = tmp_path / "audit.json", tmp_path / "review.md"
    args = [
        "--root",
        str(root),
        "--output",
        str(output),
        "--markdown-output",
        str(review),
        "--report-date",
        "2026-10-21",
    ]
    assert audit.main(args) == 0
    first = (output.read_bytes(), review.read_bytes())
    assert audit.main(args) == 0
    assert (output.read_bytes(), review.read_bytes()) == first


@pytest.mark.parametrize("problem", ["inside", "same", "missing_date", "invalid_date"])
def test_cli_checks_every_destination_and_date_before_writing(
    inputs, tmp_path, problem
):
    root, _, _ = inputs
    output = tmp_path / "audit.json"
    review = root / "review.md" if problem == "inside" else tmp_path / "review.md"
    if problem == "same":
        review = output
    args = [
        "--root",
        str(root),
        "--output",
        str(output),
        "--markdown-output",
        str(review),
    ]
    if problem != "missing_date":
        args.extend(
            ["--report-date", "bad-date" if problem == "invalid_date" else "2026-10-21"]
        )
    with pytest.raises(SystemExit):
        audit.main(args)
    assert not output.exists()
    assert not review.exists()


def test_review_retains_explicit_before_basis_and_per_development_financial_gap(inputs):
    root, rows, _ = inputs
    rows[0]["BASIS"] = "synthetic source basis"
    rows[1]["BASIS"] = "synthetic source basis"
    write_csv(root / audit.SOURCE, rows)
    result = audit.build_audit(root)
    report = audit.render_markdown(result, revision_date="2026-10-21")
    assert "| NOT_EVALUATED | synthetic source basis |" in report
    assert result["developments"][0]["npv_impact"] == {
        "status": "NOT_EVALUATED",
        "delta_usd": None,
        "reason": audit.NPV_REASON,
    }
