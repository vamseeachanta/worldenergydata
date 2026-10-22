"""Regression cases for population-scoped public source diagnostics."""

import csv
import io
import json
from datetime import date, timedelta
from http.client import IncompleteRead
from pathlib import Path

import pytest

from tests.unit.bsee.analysis import test_drilling_refresh as fixture_support
from worldenergydata.bsee.analysis.drilling_refresh import (
    NetworkBlocked,
    QualityError,
    analyse,
    fetch,
)

setup_run = fixture_support.setup_run
rewrite_table = fixture_support.rewrite_table


def test_negative_report_key_is_preserved(setup_run):
    for table in ("war", "activity"):
        rewrite_table(setup_run, table, lambda rows: rows[0].update(SN_WAR="-1"))
    rewrite_table(
        setup_run, "war", lambda rows: rows[0].update(WAR_END_DT="12/31/2019")
    )
    result = analyse(setup_run)
    quality = json.loads(
        (Path(setup_run["output_dir"]) / "data_quality.json").read_text(
            encoding="utf-8"
        )
    )
    assert quality["rows"][0]["example_id"] == "-1"
    # Reversed first week contributes no days; the remaining weeks contribute 7 + 7.
    assert result["headlines"]["bore_drilling_days_sum"] == 14


def test_undated_bore_is_not_zero(setup_run):
    rewrite_table(
        setup_run, "boreholes", lambda rows: rows[0].update(WELL_SPUD_DATE="")
    )
    result = analyse(setup_run)
    assert result["headlines"]["calendar_median_days"] == 6
    with (Path(setup_run["output_dir"]) / "calendar.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["calendar_days [day]"] == ""
    assert rows[0]["status [category]"] == "NOT_EVALUATED"


def test_unattributed_week_keeps_bore_coverage(setup_run):
    rewrite_table(setup_run, "activity", lambda rows: rows.pop())
    result = analyse(setup_run)
    assert result["headlines"]["bore_drilling_days_sum"] == 14
    with (Path(setup_run["output_dir"]) / "drilldown.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[1]["drilling_days [day]"] == ""
    assert rows[1]["days_status [category]"] == "war_covered_no_activity_code"


def test_legacy_row_defects_do_not_enter_population_products(setup_run):
    rewrite_table(
        setup_run,
        "war",
        lambda rows: rows.append(
            dict(
                rows[0],
                SN_WAR="-99",
                API_WELL_NUMBER="990000000200",
                WAR_END_DT="12/31/2019",
            )
        ),
    )
    result = analyse(setup_run)
    assert result["headlines"]["calendar_median_days"] == 9.5
    assert result["headlines"]["bore_drilling_days_sum"] == 21
    assert result["headlines"]["activity_code_records"] == 4
    qa = json.loads(
        (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    )
    assert qa["tables"]["war"]["checks"]["reversed_dates"] == 1
    assert qa["population_tables"]["war"]["checks"]["reversed_dates"] == 0
    assert len(qa["bore_quality"]) == 2


@pytest.mark.parametrize("span,expected", [(90, 0), (91, 1)])
def test_plausibility_bound_matches_canonical_exclusive_span(setup_run, span, expected):
    end = (date(2020, 1, 1) + timedelta(days=span)).strftime("%m/%d/%Y")
    rewrite_table(setup_run, "war", lambda rows: rows[0].update(WAR_END_DT=end))
    analyse(setup_run)
    qa = json.loads(
        (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    )
    assert qa["tables"]["war"]["checks"]["implausible_span"] == expected


def test_configured_date_bounds_are_checked(setup_run):
    setup_run["tables"]["war"]["date_min"] = "2021-01-01"
    analyse(setup_run)
    qa = json.loads(
        (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    )
    assert qa["tables"]["war"]["checks"]["out_of_range_dates"] == 8


@pytest.mark.parametrize("failure", ["exception", "short"])
def test_partial_http_body_is_explicit(setup_run, failure):
    setup_run["data_dir"] += "-partial"

    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Length": "100"}

        def read(self, size=-1):
            if failure == "exception":
                raise IncompleteRead(b"partial", 100)
            return super().read(size)

    with pytest.raises(NetworkBlocked, match="(incomplete|Content-Length)"):
        fetch(setup_run, opener=lambda *args, **kwargs: Response(b"short"))
    assert not (Path(setup_run["data_dir"]) / "manifest.json").exists()


def test_invalid_negative_report_key_never_falls_back_to_bore(setup_run):
    rewrite_table(setup_run, "war", lambda rows: rows[0].update(SN_WAR="--1"))
    with pytest.raises(QualityError):
        analyse(setup_run)
    assert not (Path(setup_run["output_dir"]) / "headlines.json").exists()


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"WAR_START_DT": ""}, "missing_dates"),
        ({"WAR_START_DT": "02/30/2020"}, "invalid_dates"),
        ({"WAR_END_DT": "12/31/2019"}, "reversed_dates"),
    ],
)
def test_bad_interval_is_reported_per_bore(setup_run, change, reason):
    rewrite_table(setup_run, "war", lambda rows: rows[0].update(change))
    result = analyse(setup_run)
    assert result["headlines"]["bore_drilling_days_sum"] == 14
    qa = json.loads(
        (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    )
    assert qa["bore_quality"][0]["checks"]["war"][reason] == 1
    assert qa["bore_quality"][1]["checks"]["war"] == {}


def test_negative_activity_defect_uses_report_identifier(setup_run):
    for table in ("war", "activity"):
        rewrite_table(setup_run, table, lambda rows: rows[0].update(SN_WAR="-1"))
    rewrite_table(
        setup_run, "activity", lambda rows: rows[0].update(WELL_ACTIVITY_CD="")
    )
    result = analyse(setup_run)
    quality = json.loads(
        (Path(setup_run["output_dir"]) / "data_quality.json").read_text(
            encoding="utf-8"
        )
    )
    assert quality["rows"][0]["example_id"] == "-1"
    assert result["headlines"]["bore_drilling_days_sum"] == 14


def test_all_calendar_evidence_missing_remains_null(setup_run):
    rewrite_table(
        setup_run,
        "boreholes",
        lambda rows: [
            row.update(WELL_SPUD_DATE="", TOTAL_DEPTH_DATE="") for row in rows
        ],
    )
    assert analyse(setup_run)["headlines"]["calendar_median_days"] is None


def test_missing_population_joins_remain_visible(setup_run):
    rewrite_table(setup_run, "boreholes", lambda rows: rows.pop())
    rewrite_table(setup_run, "war", lambda rows: rows.pop())
    result = analyse(setup_run)
    assert result["headlines"]["calendar_median_days"] == 13
    with (Path(setup_run["output_dir"]) / "drilldown.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[1]["drilling_days [day]"] == ""
    assert rows[1]["days_status [category]"] == "no_war_activity"
