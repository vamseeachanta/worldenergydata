"""Characterisation contracts using public-source projections and edge cases."""

import hashlib
import importlib
import json
from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path("tests/fixtures/bsee/completion_intervention")
MODULE = "worldenergydata.bsee.analysis.completion_intervention"


def activity():
    return importlib.import_module(MODULE + ".activity")


def report():
    return importlib.import_module(MODULE + ".report")


def tables():
    return {
        p.stem: pd.read_csv(p, dtype=str).fillna("") for p in FIXTURES.glob("*.csv")
    }


def revision():
    return {
        "revision": "1",
        "history": [
            {
                "revision": "1",
                "date": "2026-10-14",
                "change": "Initial characterisation with explicit coverage limits.",
            }
        ],
    }


def scenario():
    """Modify source projections to isolate counts; these are synthetic cases."""
    t = tables()
    e = t["mv_eor_mainquery"].iloc[:3].copy()
    e["SN_EOR"] = ["1", "2", "3"]
    e["API_WELL_NUMBER"] = ["177114156300", "177114156300", "608074031400"]
    e["EOR_OPERATION_CD"] = ["W", "W", "C"]
    e["BOREHOLE_STAT_DT"] = ["1/1/2010", "1/1/2011", "1/1/2011"]
    t["mv_eor_mainquery"] = e
    t["mv_eor_completions"] = t["mv_eor_completions"].iloc[:0].copy()
    return t


def test_fixture_digests_and_source_rows():
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    for name, item in manifest["files"].items():
        assert (
            hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == item["sha256"]
        )
        assert len(pd.read_csv(FIXTURES / name)) == item["rows"]
        assert item["source_url"].startswith("https://www.data.bsee.gov/")


def test_source_counts_reconcile_without_join_multiplication():
    t = tables()
    result = activity().analyse(t)
    assert result["summary"]["eor_records"] == len(t["mv_eor_mainquery"])
    assert result["summary"]["completion_records"] == len(t["mv_api_wellcomps_all"])
    assert sum(r["records"] for r in result["eor_by_year_type"]) == len(
        t["mv_eor_mainquery"]
    )


def test_workover_counts_include_recorded_zero_wells():
    result = activity().analyse(scenario())
    wells = {r["api12"]: r for r in result["per_well"]}
    assert wells["177114156300"]["workover_records"] == 2
    assert wells["608074031400"]["workover_records"] == 0
    assert result["summary"]["workover_records_per_recorded_well"] == 1


def test_unknown_codes_remain_raw_and_unqualified():
    t = scenario()
    t["mv_war_main_prop"].loc[0, "WELL_ACTIVITY_CD"] = "NEW"
    r = activity().analyse(t)
    vocab = {x["code"]: x for x in r["war_vocabulary"]}
    assert vocab["NEW"]["provenance"] == "unknown"
    assert vocab["NEW"]["label"] is None
    assert vocab["WO"]["label"] is None


def test_identical_duplicates_are_counted_once():
    t = scenario()
    t["mv_eor_mainquery"] = pd.concat(
        [t["mv_eor_mainquery"], t["mv_eor_mainquery"].iloc[:1]]
    )
    r = activity().analyse(t)
    assert r["summary"]["eor_records"] == 3
    assert r["quality"]["eor_duplicate_rows_removed"] == 1


@pytest.mark.parametrize(
    "name,key", [("mv_war_main", "SN_WAR"), ("mv_eor_mainquery", "SN_EOR")]
)
def test_conflicting_report_keys_rejected(name, key):
    t = tables()
    conflict = t[name].iloc[:1].copy()
    conflict["API_WELL_NUMBER"] = "177114156300"
    if conflict["API_WELL_NUMBER"].iloc[0] == t[name]["API_WELL_NUMBER"].iloc[0]:
        conflict["API_WELL_NUMBER"] = "608074031400"
    t[name] = pd.concat([t[name], conflict])
    with pytest.raises(ValueError, match="conflicting"):
        activity().analyse(t)


def test_conflicting_property_codes_rejected():
    t = tables()
    conflict = t["mv_war_main_prop"].iloc[:1].copy()
    conflict["WELL_ACTIVITY_CD"] = "NEW"
    t["mv_war_main_prop"] = pd.concat([t["mv_war_main_prop"], conflict])
    with pytest.raises(ValueError, match="conflicting"):
        activity().analyse(t)


def test_missing_api_is_not_a_well_or_a_true_zero():
    t = scenario()
    t["mv_eor_mainquery"].loc[t["mv_eor_mainquery"].index[0], "API_WELL_NUMBER"] = ""
    r = activity().analyse(t)
    assert r["quality"]["eor_missing_api"] == 1
    assert all(x["api12"] for x in r["per_well"])


def test_invalid_dates_are_counted_in_unknown_year():
    t = scenario()
    t["mv_eor_mainquery"].loc[
        t["mv_eor_mainquery"].index[0], "BOREHOLE_STAT_DT"
    ] = "invalid"
    r = activity().analyse(t)
    assert r["quality"]["eor_unknown_year"] == 1
    assert (
        sum(x["records"] for x in r["eor_by_year_type"] if x["year"] == "unknown") == 1
    )


def test_empty_denominator_is_null():
    t = tables()
    t["mv_eor_mainquery"] = t["mv_eor_mainquery"].iloc[:0].copy()
    r = activity().analyse(t)
    assert r["summary"]["workover_records_per_recorded_well"] is None
    assert r["outliers"]["well_thresholds"] is None


def test_band_and_era_boundaries_and_unknown_values():
    p = activity().Parameters()
    assert activity().depth_band(1000, p) == "1000-3000 ft"
    assert activity().depth_band(-1, p) == "unknown"
    assert activity().depth_band(None, p) == "unknown"
    assert activity().calendar_era(2010, p) == "2010-2019"
    assert activity().calendar_era(None, p) == "unknown"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"depth_edges": (1000, 500)},
        {"outlier_quantiles": (0.9, 0.1)},
        {"era_edges": (2010, 2010)},
    ],
)
def test_invalid_parameters_rejected(kwargs):
    with pytest.raises(ValueError):
        activity().Parameters(**kwargs)


def test_strict_quantile_flags_and_ties():
    assert activity().outlier_flags([0, 0, 0, 10], (0.05, 0.95))["flags"] == [
        "",
        "",
        "",
        "high",
    ]
    assert activity().outlier_flags([0, 0], (0.05, 0.95))["flags"] == ["", ""]
    assert activity().outlier_flags([0, 10, 10, 10], (0.05, 0.95))["flags"][0] == "low"


def test_unmatched_completions_retained_with_unknown_strata():
    t = tables()
    t["mv_eor_completions"].loc[0, "SN_EOR_FK"] = "absent"
    r = activity().analyse(t)
    assert r["quality"]["eor_completion_missing_parent"] == 1
    assert sum(x["records"] for x in r["eor_completion_strata"]) == len(
        t["mv_eor_completions"]
    )


def test_completion_dates_are_not_replaced_by_borehole_dates():
    t = tables()
    t["mv_api_wellcomps_all"]["COMPLETION_DATE"] = "1/1/1990"
    r = activity().analyse(t)
    assert all(x["era"] == "before 2000" for x in r["completion_strata"])
    assert r["method"]["completion_era_basis"] == "API Lookup COMPLETION_DATE"


def test_completion_design_types_are_explicitly_unavailable():
    r = activity().analyse(tables())
    assert r["completion_design_types"] is None
    assert any("design" in x for x in r["limits"])


def test_field_conflicts_are_unknown_not_first_match():
    t = scenario()
    t["mv_api_list_all"] = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["177114156300"] * 2,
            "BOTM_FLD_NAME_CD": ["AA100", "AA101"],
        }
    )
    r = activity().analyse(t)
    well = next(x for x in r["per_well"] if x["api12"] == "177114156300")
    assert well["field"] == "unknown"
    assert r["quality"]["conflicting_field_apis"] == 1


def test_war_only_wells_have_separate_record_frequencies():
    t = scenario()
    t["mv_war_main"].loc[0, "API_WELL_NUMBER"] = "177114115000"
    r = activity().analyse(t)
    assert sum(x["war_records"] for x in r["war_per_well"]) == len(t["mv_war_main"])
    assert "177114115000" in {x["api12"] for x in r["war_per_well"]}
    assert "177114115000" not in {x["api12"] for x in r["per_well"]}


def test_missing_essential_activity_column_is_rejected():
    t = tables()
    t["mv_war_main_prop"] = t["mv_war_main_prop"].drop(columns="WELL_ACTIVITY_CD")
    with pytest.raises(ValueError, match="essential"):
        activity().analyse(t)


def test_metadata_conflicts_do_not_pick_a_field_or_depth():
    t = scenario()
    b = t["mv_boreholes_all"].iloc[:2].copy()
    b["API_WELL_NUMBER"] = "177114156300"
    b["WATER_DEPTH"] = [100, 5000]
    t["mv_boreholes_all"] = b
    r = activity().analyse(t)
    assert r["quality"]["conflicting_borehole_depth_apis"] == 1


def test_no_duration_rate_or_production_correlations():
    r = activity().analyse(tables())
    assert "correlations" not in r
    assert "1063" in " ".join(r["limits"])
    assert (
        r["method"]["frequency_basis"]
        == "records per recorded API12; no exposure-time denominator"
    )


def test_row_order_does_not_change_results():
    t = tables()
    shuffled = {k: v.iloc[::-1].reset_index(drop=True) for k, v in t.items()}
    assert activity().analyse(t) == activity().analyse(shuffled)


def test_report_summary_numbers_equal_analysis_output():
    from html.parser import HTMLParser

    class Metrics(HTMLParser):
        def __init__(self):
            super().__init__()
            self.metrics = {}

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if "data-metric" in a:
                self.metrics[a["data-metric"]] = a["data-value"]

    r = activity().analyse(tables())
    parser = Metrics()
    parser.feed(report().render_report(r, revision()))
    assert parser.metrics == {
        k: report().format_value(v) for k, v in r["summary"].items()
    }


def test_revision_history_immediately_follows_summary():
    page = report().render_report(activity().analyse(tables()), revision())
    assert (
        page.index('id="summary"')
        < page.index('id="revision-history"')
        < page.index('id="method"')
    )
    assert 'data-revision="1"' in page
    bad = revision()
    bad["revision"] = "2"
    with pytest.raises(ValueError, match="revision"):
        report().render_report(activity().analyse(tables()), bad)


def test_report_escape_and_self_containment():
    r = activity().analyse(tables())
    r["limits"].append('<img src="outside" onerror="bad">')
    page = report().render_report(r, revision())
    assert "&lt;img" in page
    assert "<script src=" not in page and "<link " not in page
    assert "<img " not in page


def test_two_builds_and_manifest_bytes(tmp_path):
    r = activity().analyse(tables())
    a, b = tmp_path / "a", tmp_path / "b"
    report().write_products(r, revision(), a)
    report().write_products(r, revision(), b)
    assert sorted(p.name for p in a.iterdir()) == sorted(p.name for p in b.iterdir())
    for p in a.iterdir():
        assert p.read_bytes() == (b / p.name).read_bytes()
    manifest = json.loads((a / "manifest.json").read_text())
    for item in manifest["outputs"]:
        assert (
            hashlib.sha256((a / item["file"]).read_bytes()).hexdigest()
            == item["sha256"]
        )


def test_selective_archive_reader_reuses_existing_processor(tmp_path):
    import zipfile

    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(
            "public/mv_war_main.txt", (FIXTURES / "mv_war_main.csv").read_bytes()
        )
        z.writestr("public/not_requested.txt", b"unused\n1\n")
    loaded = activity().read_archive(archive, ["mv_war_main"])
    assert list(loaded) == ["mv_war_main"]
    assert len(loaded["mv_war_main"]) == len(tables()["mv_war_main"])


def test_criteria_digest_and_time_are_checked():
    good = {
        "criteria_sha256": "digest",
        "criteria_recorded_at": "2026-10-14T00:00:00Z",
        "first_run_started_at": "2026-10-14T00:00:01Z",
    }
    report().validate_run_record(good, "digest")
    with pytest.raises(ValueError, match="digest"):
        report().validate_run_record(good, "different")
    bad = {**good, "first_run_started_at": "2026-10-13T23:59:59Z"}
    with pytest.raises(ValueError, match="precede"):
        report().validate_run_record(bad, "digest")


def test_builder_rejects_import_digest_mismatch(tmp_path):
    builder = importlib.import_module("scripts.reporting.build_completion_intervention")
    source = tmp_path / "input.zip"
    source.write_bytes(b"different source bytes")
    with pytest.raises(ValueError, match="import digest mismatch"):
        builder.load_source(
            {"file": "input.zip", "sha256": "expected", "members": []}, tmp_path
        )


def test_delivered_report_manifest_revision_and_criteria():
    root = Path("docs/modules/bsee/analysis/completion_intervention")
    manifest = json.loads((root / "manifest.json").read_text())
    for item in manifest["outputs"]:
        assert report().digest(root / item["file"]) == item["sha256"]
        assert (root / item["file"]).stat().st_size == item["size_bytes"]
    criteria_path = Path("config/analysis/bsee/completion_intervention.json")
    criteria = json.loads(criteria_path.read_text())
    assert criteria["dataset"] == "worldenergydata"
    assert manifest["provenance"]["dataset"] == criteria["dataset"]
    assert (
        manifest["revision"]
        == criteria["report"]["revision"]
        == criteria["report"]["history"][-1]["revision"]
    )
    report().validate_run_record(
        manifest["provenance"]["run_record"], report().digest(criteria_path)
    )
    result = json.loads((root / "results.json").read_text())
    assert result["summary"] == manifest["summary"]
    assert (
        f'data-revision="{manifest["revision"]}"' in (root / "report.html").read_text()
    )


def test_completion_strata_sidecar_preserves_every_record(tmp_path):
    import csv

    r = activity().analyse(tables())
    report().write_products(r, revision(), tmp_path)
    compact = json.loads((tmp_path / "results.json").read_text())
    with (tmp_path / compact["completion_strata_file"]).open() as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [{k: str(v) for k, v in x.items()} for x in r["completion_strata"]]
    assert sum(int(x["records"]) for x in rows) == r["summary"]["completion_records"]
