"""Verify the published lease cohorts and rebuild from pinned inputs when present."""

import csv
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pandas as pd
import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/exploration_leasing"
OUTPUT = EXAMPLE / "output"
FIGURE_TABLES = (
    "current_status",
    "exploration",
    "exploration_site_depth",
    "first_production",
    "issuance",
)
TREND_TABLES = (
    "issuance_trend",
    "spud_share_trend",
    "spud_years_trend",
    "crude_trend",
    "status_trend",
)
EXPECTED_FILES = {
    "figures.json",
    *(f"{table}.{ext}" for table in TREND_TABLES for ext in ("svg", "csv")),
    *(
        f"{table}.{suffix}"
        for table in FIGURE_TABLES
        for suffix in ("csv", "svg", "png")
    ),
    "coverage.csv",
    "lease_match_bounds.csv",
    "record_counts.csv",
    "checks.txt",
    "numbers.json",
}
YEARLY_FILES = {
    "annual_trends.csv",
    "lease_counts.csv",
    "figures.json",
    *(
        f"figure-{number}.{ext}"
        for number in (
            "1a",
            "1b",
            "2",
            "a2a",
            "a2b",
            "a2c",
            "a3a",
            "a3b",
            "a3c",
            "a4a",
            "a4b",
            "a4c",
            "a4d",
            "a5",
        )
        for ext in ("svg", "html")
    ),
}
BOUND_BANDS = {
    "Under 100 m": "Under 100 m",
    "100 to 500 m": "100 to 500 m",
    "500 to 1,500 m": "500 to 1,500 m",
    "1,500 m and deeper": "1,500 m and deeper",
    "All": "All bands",
}
BANDS = set(BOUND_BANDS.values()) | {"Unknown"}
VARIANTS = (
    "original rule",
    "a any type bottom",
    "b any type surface",
    "c bottom or surface",
    "d type E bottom or surface",
    "e any spud date",
)


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    names = {
        "analysis": "lease_analysis",
        "bore": "bore_basis",
        "lease": "lease_basis",
        "oil": "oil_basis",
        "bounds": "bound_check",
        "derive": "derive",
    }
    # Other examples also use top-level modules named derive and source_inputs.
    for name in ("source_inputs", *names.values()):
        monkeypatch.delitem(sys.modules, name, raising=False)
    loaded = SimpleNamespace(
        **{key: importlib.import_module(name) for key, name in names.items()}
    )
    yield loaded
    for name in ("source_inputs", *names.values()):
        sys.modules.pop(name, None)


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def group_rows(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    assert groups
    return groups


def check_headlines(folder):
    headlines = json.loads((folder / "numbers.json").read_bytes(), parse_float=Decimal)
    assert headlines
    tables = {path.name: read_rows(path) for path in folder.glob("*.csv")}
    for name, spec in headlines.items():
        matches = [
            row
            for row in tables[spec["table"]]
            if all(row[key] == value for key, value in spec["filter"].items())
        ]
        assert len(matches) == 1, name
        cell = matches[0][spec["column"]]
        expected = spec["value"]
        if isinstance(expected, (int, Decimal)):
            assert Decimal(cell) == expected, name
        elif expected is None:
            assert cell == "", name
        else:
            assert cell == expected, name


def test_headlines_match_unique_csv_rows():
    check_headlines(OUTPUT)


def test_published_output_inventory_and_checks():
    assert {path.name for path in OUTPUT.iterdir()} == EXPECTED_FILES | {"yearly"}
    assert {p.name for p in (OUTPUT / "yearly").iterdir()} == YEARLY_FILES
    assert all((OUTPUT / name).is_file() for name in EXPECTED_FILES)
    lines = (OUTPUT / "checks.txt").read_text(encoding="utf-8").splitlines()
    yearly_checks = {
        f"PASS  Yearly {name} meets chart standard items 5 and 7"
        for name in YEARLY_FILES
        if name.endswith(".svg")
    }
    assert yearly_checks <= set(lines)
    assert len(lines) == len(set(lines)) == 20 + len(yearly_checks)
    assert all(line.startswith("PASS  ") for line in lines)


def test_changed_csv_cell_fails_headline_check(tmp_path):
    shutil.copy(OUTPUT / "numbers.json", tmp_path)
    for path in OUTPUT.glob("*.csv"):
        shutil.copy(path, tmp_path)
    target = tmp_path / "issuance.csv"
    rows = read_rows(target)
    (pooled,) = [
        row
        for row in rows
        if row["issue_year"] == "All years" and row["depth_band"] == "All bands"
    ]
    pooled["leases"] = str(int(pooled["leases"]) + 1)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(AssertionError, match="issued_total"):
        check_headlines(tmp_path)


def check_margin(rows, column, categories, pooled_value, fields):
    assert Counter(row[column] for row in rows) == Counter(categories)
    (pooled,) = [row for row in rows if row[column] == pooled_value]
    for field in fields:
        assert int(pooled[field]) == sum(
            int(row[field]) for row in rows if row[column] != pooled_value
        ), (pooled, field)


@pytest.mark.parametrize(
    "table,keys,fields,last_year",
    [
        ("issuance", ["issue_year"], ["leases"], 2026),
        (
            "current_status",
            ["issue_year", "status_code"],
            ["leases", "cohort_leases"],
            2026,
        ),
        (
            "exploration",
            ["issue_year"],
            [
                "leases",
                "explored_leases",
                "exploration_wells",
                "leases_with_any_e_bore",
                "explored_within_five_years",
                "open_without_observed_event",
                "timed_leases",
            ],
            2020,
        ),
        ("exploration_site_depth", [], ["timed_leases"], None),
        (
            "first_production",
            ["period", "event"],
            [
                "leases",
                "observed_leases",
                "without_observed_event",
                "open_without_observed_event",
                "timed_leases",
                "pre_effective_leases",
                "term_leases",
                "over_term_leases",
            ],
            None,
        ),
    ],
)
def test_additive_margins(table, keys, fields, last_year):
    rows = read_rows(OUTPUT / f"{table}.csv")
    for group in group_rows(rows, keys).values():
        check_margin(group, "depth_band", BANDS, "All bands", fields)
    if last_year:
        years = {str(year) for year in range(2005, last_year + 1)} | {"All years"}
        year_keys = ["depth_band", *(key for key in keys if key != "issue_year")]
        for group in group_rows(rows, year_keys).values():
            check_margin(group, "issue_year", years, "All years", fields)


def test_site_bands_use_individual_durations_and_retain_flagged_depths(
    modules, tmp_path
):
    leases = pd.DataFrame(
        {"lease_id": list("ABCDEFG"), "effective_date": pd.Timestamp("2010-01-01")}
    )
    source = tmp_path / "bores.zip"
    with ZipFile(source, "w") as archive:
        records = [
            "API_WELL_NUMBER,BOTM_LEASE_NUMBER,WELL_TYPE_CODE,WELL_SPUD_DATE,"
            "REGION_CODE,WATER_DEPTH,BOREHOLE_STAT_CD"
        ]
        for i, (lease, day, feet) in enumerate(
            zip(
                "ABCDEFG",
                [2, 6, 8, 12, 14, 20, 24],
                [100, 100, 400, 1800, 5000, 0, 100],
            )
        ):
            records.append(f"{i:010}00,{lease},E,01/{day:02}/2010,G,{feet},")
        # The final well has two initial bores on opposite sides of a band edge.
        records.append("000000000601,G,E,01/24/2010,G,5000,")
        archive.writestr(modules.bore.MEMBER, "\n".join(records) + "\n")
    _, wells, bore_audit, _ = modules.bore.read_bores(source, leases, "2010-02-01")
    table, site_audit, durations = modules.bore.site_spud_table(
        leases, wells, modules.analysis.depth_band, modules.analysis.BANDS
    )
    expected = {
        "Under 100 m": (2, 2, 3, 4),
        "100 to 500 m": (1, 7, 7, 7),
        "500 to 1,500 m": (1, 11, 11, 11),
        "1,500 m and deeper": (1, 13, 13, 13),
        "Unknown": (2, 20, 21, 22),
        "All bands": (7, 6, 11, 16),
    }
    for row in table.itertuples():
        assert (
            row.timed_leases,
            row.days_to_spud_p25,
            row.days_to_spud_median,
            row.days_to_spud_p75,
        ) == expected[row.depth_band]
    assert bore_audit[0]["flags"] == {"nonpositive_depth_nulled": 1}
    assert site_audit[-1]["flags"] == {
        "missing_site_depth": 1,
        "ambiguous_site_band": 1,
    }
    assert site_audit[-1]["read"] == site_audit[-1]["kept"] == 7
    assert site_audit[-1]["drops"] == {}
    modules.analysis.validate_site_quantiles(table, durations)
    for index in table.index:
        corrupt = table.copy()
        corrupt.loc[index, "days_to_spud_median"] += 1
        with pytest.raises(ValueError, match="Quartiles disagree"):
            modules.analysis.validate_site_quantiles(corrupt, durations)


def test_depth_comparison_strips_ids_and_logs_missing_depth(modules, tmp_path):
    leases = pd.DataFrame(
        {
            "lease_id": ["NA", "001", "absent"],
            "lease_depth_m": [30.48] * 3,
            "block_max_depth_ft": [100] * 3,
        }
    )
    source = tmp_path / "depths.zip"
    with ZipFile(source, "w") as archive:
        archive.writestr(
            "ProductionRawData/mv_production_waterdepth.txt",
            "LEASE_NUMBER,MAX_WTR_DPTH\n NA ,30\n 001 , \noutside,2\n",
        )
    counts, audits = modules.analysis.compare_native_depths(leases, source)
    assert counts == {"compared_block_depths": 1, "depths_within_one_metre": 1}
    selected, compared = audits
    assert (selected["read"], selected["kept"]) == (3, 2)
    assert (compared["read"], compared["kept"]) == (2, 1)
    assert compared["drops"] == {"missing_comparison_depth": 1}


def test_audit_rejects_miswired_stages(modules):
    audit = modules.analysis.read_table(OUTPUT, "record_counts")
    modules.analysis.validate_audit(audit)
    timed = audit.stage.eq("Timed crude oil leases")
    assert timed.sum() == 1
    for upstream in ["", "Distinct observed any hydrocarbon leases"]:
        miswired = audit.copy()
        miswired.loc[timed, "upstream_stage"] = upstream
        with pytest.raises(ValueError, match="upstream"):
            modules.analysis.validate_audit(miswired)
    # Both sides of the stage balance still hold, but one input row vanished
    # between the distinct observed leases and the timing filter.
    audit.loc[timed, ["rows_read", "rows_kept"]] -= 1
    with pytest.raises(ValueError, match="continuity"):
        modules.analysis.validate_audit(audit)


def test_record_counts_reconcile_with_drop_reasons():
    rows = read_rows(OUTPUT / "record_counts.csv")
    assert rows and len({row["stage"] for row in rows}) == len(rows)
    for row in rows:
        reasons = [
            int(value) for name, value in row.items() if name.startswith("drop__")
        ]
        assert reasons and min(reasons) >= 0, row
        assert int(row["rows_dropped"]) == sum(reasons), row
        assert int(row["rows_read"]) == int(row["rows_kept"]) + sum(reasons), row


def test_status_shares_use_issue_year_and_depth_band_cohort():
    keys = ("issue_year", "depth_band")
    status = group_rows(read_rows(OUTPUT / "current_status.csv"), keys)
    issuance = group_rows(read_rows(OUTPUT / "issuance.csv"), keys)
    assert status.keys() == issuance.keys()
    codes = {row["status_code"] for rows in status.values() for row in rows}
    for cohort, rows in status.items():
        (issued,) = issuance[cohort]
        leases = int(issued["leases"])
        assert Counter(row["status_code"] for row in rows) == Counter(codes), cohort
        assert sum(int(row["leases"]) for row in rows) == leases, cohort
        for row in rows:
            assert int(row["cohort_leases"]) == leases, row
            if leases:
                expected = 100 * int(row["leases"]) / leases
                assert float(row["share_pct"]) == pytest.approx(
                    expected, abs=1e-12
                ), row
            else:
                assert row["share_pct"] == "", row
        if leases:
            assert sum(float(r["share_pct"]) for r in rows) == pytest.approx(
                100, abs=1e-12
            )


def test_lease_match_bounds_reconcile_with_exploration():
    rows = read_rows(OUTPUT / "lease_match_bounds.csv")
    exploration = group_rows(
        read_rows(OUTPUT / "exploration.csv"), ("issue_year", "depth_band")
    )
    cohorts = {"2005 to 2020": "All years", "2005": "2005"}
    groups = group_rows(rows, ("cohort", "band"))
    assert set(groups) == {(year, band) for year in cohorts for band in BOUND_BANDS}
    for (year, band), group in groups.items():
        (source,) = exploration[cohorts[year], BOUND_BANDS[band]]
        leases = int(source["leases"])
        assert Counter(r["variant"] for r in group) == Counter(VARIANTS)
        by_variant = {r["variant"]: int(r["matched_leases"]) for r in group}
        original, bottom, surface, either, exploratory, any_date = (
            by_variant[v] for v in VARIANTS
        )
        assert original == int(source["explored_leases"])
        any_e_bottom = int(source["leases_with_any_e_bore"])
        assert (
            0 <= original <= any_e_bottom <= exploratory <= either <= any_date <= leases
        )
        assert any_e_bottom <= bottom <= either
        assert 0 <= surface <= either <= bottom + surface
        for row in group:
            assert int(row["leases"]) == leases, row
            assert (
                row["share_pct"] == f"{100 * int(row['matched_leases']) / leases:.2f}"
            ), row
        if year == "2005 to 2020" and band == "All":
            assert (leases, original, exploratory, either, any_date) == (
                7126,
                432,
                477,
                546,
                587,
            )
    for group in group_rows(rows, ("cohort", "variant")).values():
        check_margin(
            group, "band", set(BOUND_BANDS), "All", ("leases", "matched_leases")
        )


def check_readme_results(readme, numbers):
    """Compare the article's displayed precision and matching rules to saved headlines."""
    values = {key: claim["value"] for key, claim in numbers.items()}
    cohort = values["exploration.all.leases"]
    section = readme.split("*Table 1.", 1)[0]
    rows = [
        line.strip("|").split("|")
        for line in section.splitlines()
        if line.startswith("|")
    ]
    header, _, *body = [[cell.strip() for cell in row] for row in rows]
    assert header == ["Matching rule", "Matched leases", f"Share of {cohort:,} (%)"]
    matches = [
        (
            "Original type E spud on the bottom lease (published rule)",
            "exploration.all.explored_leases",
            "exploration.all.share_pct",
        ),
        (
            "Any dated type E bore, bottom lease",
            "exploration.all.leases_with_any_e_bore",
            "exploration.all.any_e_bore_share_pct",
        ),
        (
            "Any dated type E bore, bottom or surface lease (variant d)",
            "bounds.d.matched_leases",
            "bounds.d.share_pct",
        ),
        (
            "Any dated bore of any type, bottom or surface lease (variant c)",
            "bounds.c.matched_leases",
            "bounds.c.share_pct",
        ),
        (
            "Any listing of any type at either endpoint, including earlier and undated listings (variant e)",
            "bounds.e.matched_leases",
            "bounds.e.share_pct",
        ),
    ]
    assert body == [
        [label, f"{values[count]:,}", f"{values[share]:.2f}"]
        for label, count, share in matches
    ], "Table 1"
    coverage = {
        key.removeprefix("coverage."): n
        for key, n in values.items()
        if key.startswith("coverage.")
    }

    def calendar_date(key):
        day = date.fromisoformat(coverage[key])
        return f"{day:%B} {day.day}, {day.year}"

    def calendar_month(key):
        return date.fromisoformat(coverage[key] + "-01").strftime("%B %Y")

    # The article spells out small counts in prose. Keep numeric tokens at word
    # boundaries so that a changed observation cannot match a substring.
    words = dict(
        zip("none one two three four five six seven eight nine".split(), range(10))
    )

    def numeric_text(sentence):
        return re.sub(
            r"\b(" + "|".join(words) + r")\b",
            lambda match: str(words[match[0].lower()]),
            sentence,
            flags=re.I,
        )

    spud = values["exploration.all.explored_leases"]
    assert values["issued_2025"] == 0 and "The 2025 effective cohort is empty" in readme
    first_of_month = "Every lease in this cohort took effect on the first of a month"
    assert first_of_month in readme
    assert f"PASS  {first_of_month}" in (OUTPUT / "checks.txt").read_text().splitlines()
    undated = values[
        "audit.LSETAPE effective Gulf lease cohort.drop__missing_effective_date"
    ]
    fragments = [
        f"follows {values['issued_total']:,} federal Gulf leases",
        f"Of {cohort:,} leases effective from 2005 through 2020, {spud:,} ({values['exploration.all.share_pct']:.2f}%)",
        f"Among the {values['bounds.c.matched_leases']:,} leases with a dated match of any type, "
        f"{values['bounds.a.matched_leases']:,} have a bottom match, "
        f"{values['bounds.b.matched_leases']:,} a surface match and {coverage['bounds_both_endpoints']:,} both",
        f"Of the {coverage['bounds_additional_any_date']:,} additional leases counted when both date requirements are removed, "
        f"{coverage['bounds_earlier_only']:,} have only earlier spuds and {coverage['bounds_undated_only']:,} have only undated listings",
        f"first cohort date is {calendar_date('first_effective_date')} and the last is {calendar_date('last_effective_date')}",
        f"{coverage['no_sale_number']} leases lack a sale number",
        f"The tape has {undated:,} undated records",
        f"on the {calendar_date('tape_file_date')} tape",
        f"latest observed Gulf spud was {calendar_date('last_gulf_spud')}",
        f"detail spans {calendar_month('first_source_month')} through {calendar_month('last_source_month')}",
        f"all {coverage['depths_within_one_metre']:,} block maxima agree within one metre",
        f"{coverage['straddling_ranges']:,} ranges cross a band boundary",
        f"Across all {spud:,} matched leases, the median is {values['exploration.all.days_to_spud_median']:,} days "
        f"and the middle half spans {values['exploration.all.days_to_spud_p25']:,} to {values['exploration.all.days_to_spud_p75']:,} days",
        f"those same {values['well_site.all.timed_leases']:,} first events",
        f"APD ({coverage['undated_e_APD']}), AST ({coverage['undated_e_AST']}) and CNL ({coverage['undated_e_CNL']})",
        f"{coverage['pre_effective_e_bores_2005_2026']:,} E bores predate effectiveness",
        f"{coverage['tied_first_spud_conflicting_cohort_lease_api10s']} well touches a cohort lease with conflicting bottom leases",
        f"{coverage['production_before_effective_month']} first hydrocarbon months and "
        f"{coverage['oil_before_effective_month']} first crude months predate the effective month",
        f"Only {coverage['last_source_month_rows']:,} records appear in the final month",
        f"First hydrocarbon was reported within five years for {values['hydrocarbon.all.timed_leases']:,} of {cohort:,} leases "
        f"({values['hydrocarbon.all.share_pct']:.2f}%). Their median wait was {values['hydrocarbon.all.months_median']:,} months "
        f"({values['hydrocarbon.all.median_years']:.1f} years)",
        f"First crude was reported within five years for {values['oil.all.timed_leases']:,} of {cohort:,} leases "
        f"({values['oil.all.share_pct']:.2f}%). Their median wait was {values['oil.all.months_median']:,} months",
        f"ordered suspension dates on {coverage['suspensions_with_ordered_dates']:,} cohort leases",
        f"{coverage['continuous_date_without_positive_month']} leases have a date of first continuous commercial production",
        f"{coverage['positive_month_without_continuous_date']} have a positive month without that tape date",
        f"{coverage['owner_status_C']:,} current and {coverage['owner_status_T']} terminated assignment rows",
        f"{coverage['termination_dates_present']} has a termination date, and "
        f"{coverage['missing_assignment_effective_dates']:,} lack an effective assignment date",
    ]
    prose = numeric_text(" ".join(readme.split()))
    for fragment in fragments:
        pattern = r"(?<![\w.,])" + re.escape(numeric_text(fragment)) + r"(?!\w)"
        assert re.search(pattern, prose), fragment


def test_readme_table_and_prose_resolve_to_headlines():
    check_readme_results(
        (EXAMPLE / "README.md").read_text(encoding="utf-8"),
        json.loads((OUTPUT / "numbers.json").read_bytes()),
    )


@pytest.mark.parametrize(
    "original,changed,reason",
    [
        ("| 477 | 6.69 |", "| 477 | 6.68 |", "Table 1"),
        ("416 both", "415 both", "416 both"),
        ("23 have only undated", "22 have only undated", "23 have only undated"),
    ],
)
def test_changed_article_number_fails_check(original, changed, reason):
    readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    assert readme.count(original) == 1
    with pytest.raises(AssertionError, match=reason):
        check_readme_results(
            readme.replace(original, changed),
            json.loads((OUTPUT / "numbers.json").read_bytes()),
        )


def read_pins():
    return json.loads((EXAMPLE / "source_pins.json").read_bytes())["sources"]


def test_readme_matches_archive_pins():
    pins = read_pins()
    names = {
        "BoreholeRawData.zip",
        "lsetapefixed.zip",
        "ProductionRawData.zip",
        "LeaseOwnerRawData.zip",
    }
    assert Counter(p["name"] for p in pins) == Counter(names)
    expected = [(p["name"], p["url"], p["last_modified"], p["sha256"]) for p in pins]
    readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    documented = re.findall(
        r"^\| \[([^\]]+\.zip)\]\((https://www\.data\.bsee\.gov/[^)]+)\) "
        r"\| ([^|]+?) \| `([0-9a-f]{64})` \|$",
        readme,
        re.MULTILINE,
    )
    assert sorted(documented) == sorted(expected)
    dates = {p["name"]: date.fromisoformat(p["collection_end_utc"][:10]) for p in pins}
    bore = dates.pop("BoreholeRawData.zip")
    (leases,) = set(dates.values())
    assert f"borehole collection cutoff was {bore:%B} {bore.day}, {bore.year}" in readme
    assert (
        f"well snapshot was collected {bore:%B} {bore.day}, {bore.year} UTC and "
        f"the leasing and production snapshots {leases:%B} {leases.day}, {leases.year} UTC"
    ) in readme


def test_wrong_archive_reports_both_digests(tmp_path):
    pins = read_pins()
    content = b"synthetic file with incorrect digest\n"
    for pin in pins:
        (tmp_path / pin["name"]).write_bytes(content)
    output = tmp_path / "output"
    output.mkdir()
    previous = output / "checks.txt"
    previous.write_bytes(b"previous build\n")
    for marker in ("numbers.json", "lease_match_bounds.csv"):
        (output / marker).touch()
    run = subprocess.run(
        [
            sys.executable,
            "-S",
            str(EXAMPLE / "derive.py"),
            "--data-dir",
            str(tmp_path),
            "--output-dir",
            str(output),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert run.returncode != 0
    message = run.stdout + run.stderr
    assert hashlib.sha256(content).hexdigest() in message, message
    assert any(p["name"] in message and p["sha256"] in message for p in pins), message
    assert {p.name for p in output.iterdir()} == {
        "checks.txt",
        "numbers.json",
        "lease_match_bounds.csv",
    }
    assert previous.read_bytes() == b"previous build\n"


def test_owner_fields_strip_only_outer_whitespace(modules, tmp_path):
    repo = EXAMPLE.parents[2]
    layout = json.loads((repo / modules.lease.OWNER_SCHEMA).read_bytes())
    spec = next(
        m for m in layout["members"] if m["name"].startswith("LeaseOwnerRawData/")
    )
    header = next(csv.reader([spec["header"].strip()]))
    records = [
        {
            "LEASE_NUMBER": " G001 ",
            "ASGN_STATUS_CODE": " C ",
            "MMS_COMPANY_NUM": " 001 ",
            "ASSGN_TERM_DATE": " ",
            "ASSGN_EFF_DATE": " ",
        },
        {
            "LEASE_NUMBER": "G001",
            "ASGN_STATUS_CODE": "C",
            "MMS_COMPANY_NUM": "001",
            "ASSGN_EFF_DATE": "1/1/2010",
        },
        {"LEASE_NUMBER": "G 001", "ASGN_STATUS_CODE": "C", "MMS_COMPANY_NUM": "2"},
    ]
    content = StringIO()
    writer = csv.DictWriter(content, fieldnames=header)
    writer.writeheader()
    writer.writerows(records)
    path = tmp_path / "owners.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr(spec["name"], content.getvalue())
    owners, _, meta = modules.lease.read_owners(
        path, pd.DataFrame({"lease_id": ["G001"]}), repo
    )
    assert owners.company_id.tolist() == ["001", "001"]
    assert meta["cohort_current_companies"] == 1
    assert meta["source_status_counts"] == {"C": 3}
    assert meta["termination_dates_present"] == 0
    assert meta["missing_assignment_effective_dates"] == 2


def test_swap_replaces_whole_output_and_keeps_old_tree_until_success(
    modules, tmp_path, monkeypatch
):
    staging = tmp_path / "staged"
    staging.mkdir()
    (staging / "new.csv").write_text("new")
    output = tmp_path / "published"
    modules.derive.install_output(staging, output)
    assert (output / "new.csv").read_text() == "new"
    (output / "checks.txt").touch()
    (output / "numbers.json").touch()
    (output / "lease_match_bounds.csv").touch()
    staging.mkdir()
    (staging / "rebuilt.csv").write_text("rebuilt")
    if sys.platform not in ("linux", "darwin"):
        with pytest.raises(OSError, match="fresh --output-dir"):
            modules.derive.install_output(staging, output)
        assert (output / "new.csv").read_text() == "new"
        return
    with monkeypatch.context() as m:
        m.setattr(modules.derive.ctypes, "CDLL", lambda *a, **kw: SimpleNamespace())
        with pytest.raises(OSError, match="fresh --output-dir"):
            modules.derive.install_output(staging, output)
    assert (output / "new.csv").read_text() == "new"
    assert (staging / "rebuilt.csv").read_text() == "rebuilt"
    modules.derive.install_output(staging, output)
    assert [p.name for p in output.iterdir()] == ["rebuilt.csv"]
    assert (staging / "new.csv").read_text() == "new"
    with pytest.raises((ValueError, OSError)):
        modules.derive.install_output(staging, output)
    assert (output / "rebuilt.csv").read_text() == "rebuilt"


def test_chart_notes_and_public_punctuation():
    notes = {}
    for name in FIGURE_TABLES:
        root = ET.fromstring((OUTPUT / f"{name}.svg").read_bytes())
        notes[name] = " ".join(
            node.text or "" for node in root.iter("{http://www.w3.org/2000/svg}text")
        )
    for content in [
        *notes.values(),
        (EXAMPLE / "README.md").read_text(encoding="utf-8"),
    ]:
        assert not re.search(r"[\u2013\u2014]", content)
    assert "2026 is partial, to the latest effective month" in notes["issuance"]
    assert "2005 to 2020" in notes["first_production"]
    assert "first 60 reporting months" in notes["first_production"]
    assert "Years since lease effective date" in notes["exploration"]
    assert "Years from lease effective date" in notes["exploration_site_depth"]
    for name in ("exploration", "exploration_site_depth"):
        assert "observed" in notes[name] and "biased low" in notes[name]


@pytest.mark.skipif(
    not os.environ.get("BSEE_EXP_DATA_DIR"), reason="pinned archives were not supplied"
)
def test_regeneration_is_byte_identical(tmp_path, monkeypatch):
    archives = Path(os.environ["BSEE_EXP_DATA_DIR"]).resolve()
    monkeypatch.setenv("BSEE_EXP_DATA_DIR", str(archives))
    # Retain the UTF-8 table labels even when the process locale is ASCII.
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("PYTHONUTF8", "0")
    monkeypatch.setenv("PYTHONCOERCECLOCALE", "0")
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(variable, raising=False)
    output, repeat = tmp_path / "output", tmp_path / "repeat"
    for directory in (output, repeat):
        subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                str(EXAMPLE / "derive.py"),
                "--output-dir",
                str(directory),
            ],
            cwd=tmp_path,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert {path.name for path in directory.iterdir()} == EXPECTED_FILES | {
            "yearly"
        }
        assert {p.name for p in (directory / "yearly").iterdir()} == YEARLY_FILES
    for name in sorted(YEARLY_FILES):
        fresh = (output / "yearly" / name).read_bytes()
        assert fresh == (OUTPUT / "yearly" / name).read_bytes(), name
        assert fresh == (repeat / "yearly" / name).read_bytes(), name
    for name in sorted(EXPECTED_FILES):
        assert (output / name).read_bytes() == (OUTPUT / name).read_bytes(), name


def test_calendar_month_lag_and_primary_term_boundary(modules):
    effective = pd.Timestamp("2010-05-01")
    event_dates = pd.to_datetime(
        ["2015-05-01", "2015-04-01", "2010-05-01", "2010-04-01"]
    )
    frame = pd.DataFrame(
        {
            "depth_band": [
                "Under 100 m",
                "100 to 500 m",
                "500 to 1,500 m",
                "1,500 m and deeper",
            ],
            "status_code": "PROD",
            "effective_date": effective,
            "primary_term_years": [5, 5, 5, 5],
            "first_production_month": event_dates,
            "first_oil_month": event_dates,
        }
    )
    assert modules.analysis.month_lag(
        frame.effective_date, frame.first_oil_month
    ).tolist() == [60, 59, 0, -1]
    result = (
        modules.analysis.production_table(frame, last_source_month="2026-10")
        .query('period == "2005 to 2020"')
        .set_index(["depth_band", "event"])
    )
    for event in ("Crude oil", "Any hydrocarbon"):
        anniversary = result.loc["Under 100 m", event]
        last_in_term = result.loc["100 to 500 m", event]
        assert anniversary.after_window_leases == 1
        assert anniversary.timed_leases == 0
        assert pd.isna(anniversary.primary_term_pct_median)
        assert last_in_term.over_term_leases == 0
        assert last_in_term.primary_term_pct_median == pytest.approx(98.33333333333333)
        pooled = result.loc["All bands", event]
        assert (
            pooled.observed_leases,
            pooled.timed_leases,
            pooled.pre_effective_leases,
        ) == (4, 2, 1)
        assert (pooled.months_p25, pooled.months_median, pooled.months_p75) == (
            14.75,
            29.5,
            44.25,
        )

    # A shorter original term can expire within the five-year observation window.
    frame["primary_term_years"] = 4
    frame["first_oil_month"] = pd.to_datetime(["2014-05-01", "2014-04-01", None, None])
    table = modules.analysis.production_table(frame, last_source_month="2026-10")
    pooled = table.query(
        'period == "2005 to 2020" and event == "Crude oil" and depth_band == "All bands"'
    ).iloc[0]
    assert pooled.over_term_leases == 1


def test_open_leases_counted_separately_for_each_production_event(modules):
    frame = pd.DataFrame(
        {
            "status_code": [
                "PRIMRY",
                "SOP",
                "OPERNS",
                "PROD",
                "UNIT",
                "EXPIR",
                "RELINQ",
                "TERMIN",
                "CANCEL",
            ],
            "depth_band": "Under 100 m",
            "effective_date": pd.Timestamp("2010-01-01"),
            "primary_term_years": 5,
            "first_oil_month": pd.to_datetime([None] * 9),
            "first_production_month": pd.to_datetime(
                [None] * 3 + ["2011-01-01"] + [None] * 5
            ),
        }
    )
    result = (
        modules.analysis.production_table(frame, last_source_month="2026-10")
        .query('period == "2005 to 2020"')
        .set_index(["depth_band", "event"])
    )
    crude = result.loc["All bands", "Crude oil"]
    hydrocarbon = result.loc["All bands", "Any hydrocarbon"]
    assert (crude.without_observed_event, crude.open_without_observed_event) == (9, 5)
    assert (
        hydrocarbon.without_observed_event,
        hydrocarbon.open_without_observed_event,
    ) == (8, 4)
    assert (
        crude.primry_sop_operns_without_event,
        crude.prod_without_event,
        crude.unit_without_event,
    ) == (3, 1, 1)
    assert (
        hydrocarbon.primry_sop_operns_without_event,
        hydrocarbon.prod_without_event,
        hydrocarbon.unit_without_event,
    ) == (3, 0, 1)
    assert hydrocarbon.months_median == 12
    frame.loc[0, "status_code"] = "UNCLASSIFIED"
    with pytest.raises(ValueError, match="UNCLASSIFIED"):
        modules.analysis.production_table(frame, last_source_month="2026-10")


def test_exploration_rates_include_every_lease_and_fifth_anniversary(modules):
    frame = pd.DataFrame(
        {
            "effective_date": pd.Timestamp("2010-05-01"),
            "issue_year": 2010,
            "depth_band": "Under 100 m",
            "status_code": ["EXPIR", "PRIMRY", "SOP", "RELINQ"],
            "exploration_spud": pd.to_datetime(
                ["2015-05-01", "2015-05-02", None, None]
            ),
            "exploration_wells": [2, 1, 0, 0],
            "any_e_bore_spud": pd.to_datetime(
                ["2015-05-01", "2015-05-02", "2017-01-01", None]
            ),
            "has_any_e_bore": [True, True, True, False],
        }
    )
    row = (
        modules.analysis.exploration_table(frame)
        .set_index(["issue_year", "depth_band"])
        .loc["2010", "Under 100 m"]
    )
    assert row.leases == 4 and row.exploration_wells == 3
    assert row.explored_leases == row.timed_leases == 2
    assert row.explored_within_five_years == 1
    assert (row.share_pct, row.five_year_share_pct, row.any_e_bore_share_pct) == (
        50,
        25,
        75,
    )
    assert row.days_to_spud_median == 1826.5
    assert row.open_without_observed_event == 1
    assert (
        row.primry_sop_operns_without_event,
        row.prod_without_event,
        row.unit_without_event,
    ) == (1, 0, 0)


def test_block_depth_thresholds_enter_the_deeper_band(modules):
    depths = pd.Series([0, 99.9, 100, 499.9, 500, 1499.9, 1500, None])
    assert modules.analysis.depth_band(depths).tolist() == [
        "Under 100 m",
        "Under 100 m",
        "100 to 500 m",
        "100 to 500 m",
        "500 to 1,500 m",
        "500 to 1,500 m",
        "1,500 m and deeper",
        "Unknown",
    ]


def test_status_denominator_changes_with_year_and_band(modules):
    leases = pd.DataFrame(
        {
            "issue_year": [2010, 2010, 2010, 2011],
            "depth_band": [
                "Under 100 m",
                "Under 100 m",
                "1,500 m and deeper",
                "Under 100 m",
            ],
            "status_code": ["PROD", "RELINQ", "RELINQ", "PROD"],
            "status_label": [
                "Production",
                "Relinquished",
                "Relinquished",
                "Production",
            ],
        }
    )
    status = modules.analysis.status_table(leases).set_index(
        ["issue_year", "depth_band", "status_code"]
    )
    for key, expected in [
        (("2010", "Under 100 m", "PROD"), (1, 2, 50)),
        (("2010", "1,500 m and deeper", "PROD"), (0, 1, 0)),
        (("2011", "Under 100 m", "PROD"), (1, 1, 100)),
        (("All years", "Under 100 m", "PROD"), (2, 3, 200 / 3)),
    ]:
        row = status.loc[key]
        assert (row.leases, row.cohort_leases, row.share_pct) == pytest.approx(expected)
    assert pd.isna(status.loc[("2011", "1,500 m and deeper", "PROD"), "share_pct"])


def test_spuds_match_earliest_dated_well_on_eligible_bottom_lease(modules, tmp_path):
    # The first well is listed out of date order and changes bottom lease.
    # Its later branch reaches B for the any-E sensitivity only.
    records = [
        ("000000000101", "B", "B", "05/04/2010"),
        ("000000000100", "A", "A", "05/02/2010"),
        ("000000000200", "A", "A", "05/01/2010"),
        ("000000000300", "PRE", "PRE", "04/30/2010"),
        ("000000000400", "OUTSIDE", "SURF", "05/03/2010"),
    ]
    raw = pd.DataFrame(
        records,
        columns=[
            "API_WELL_NUMBER",
            "BOTM_LEASE_NUMBER",
            "SURF_LEASE_NUMBER",
            "WELL_SPUD_DATE",
        ],
    )
    raw = raw.assign(
        WELL_TYPE_CODE="E", REGION_CODE="G", WATER_DEPTH=100, BOREHOLE_STAT_CD="COM"
    )
    archive = tmp_path / "bores.zip"
    with ZipFile(archive, "w") as stream:
        stream.writestr(modules.bore.MEMBER, raw.to_csv(index=False))
    leases = pd.DataFrame(
        {
            "lease_id": ["A", "B", "PRE", "SURF"],
            "effective_date": pd.Timestamp("2010-05-01"),
        }
    )
    counts, wells, _, _ = modules.bore.read_bores(archive, leases, "2020-01-01")
    counts = counts.set_index("lease_id")
    assert wells.set_index("api10").lease_id.to_dict() == {
        "0000000001": "A",
        "0000000002": "A",
    }
    assert counts.exploration_wells.to_dict() == {"A": 2, "B": 0, "PRE": 0, "SURF": 0}
    assert counts.loc["A", "exploration_spud"] == pd.Timestamp("2010-05-01")
    assert counts.loc[["B", "PRE", "SURF"], "exploration_spud"].isna().all()
    assert counts.has_any_e_bore.to_dict() == {
        "A": True,
        "B": True,
        "PRE": False,
        "SURF": False,
    }


def test_saved_exploration_rates_and_samples():
    issuance = group_rows(
        read_rows(OUTPUT / "issuance.csv"), ("issue_year", "depth_band")
    )
    for row in read_rows(OUTPUT / "exploration.csv"):
        n = int(row["leases"])
        year, band = row["issue_year"], row["depth_band"]
        if year == "All years":
            n_issued = sum(
                int(rows[0]["leases"])
                for (y, b), rows in issuance.items()
                if b == band and y != "All years" and int(y) <= 2020
            )
        else:
            n_issued = int(issuance[year, band][0]["leases"])
        assert n == n_issued
        assert row["timed_leases"] == row["explored_leases"]
        assert (
            0
            <= int(row["open_without_observed_event"])
            <= n - int(row["explored_leases"])
        )
        for numerator, percentage in [
            ("explored_leases", "share_pct"),
            ("leases_with_any_e_bore", "any_e_bore_share_pct"),
            ("explored_within_five_years", "five_year_share_pct"),
        ]:
            if n:
                assert float(row[percentage]) == pytest.approx(
                    100 * int(row[numerator]) / n
                )
            else:
                assert row[percentage] == ""


def test_saved_production_counts_reconcile():
    for row in read_rows(OUTPUT / "first_production.csv"):
        (
            observed,
            unobserved,
            timed,
            pre_effective,
            with_term,
            past_term,
            censored,
            leases,
        ) = (
            int(row[key])
            for key in (
                "observed_leases",
                "without_observed_event",
                "timed_leases",
                "pre_effective_leases",
                "term_leases",
                "over_term_leases",
                "open_without_observed_event",
                "leases",
            )
        )
        assert observed + unobserved == leases
        assert timed + pre_effective + int(row["after_window_leases"]) == observed
        assert 0 <= past_term <= with_term <= timed
        assert 0 <= censored <= unobserved


def test_production_ledger_times_only_ordered_events_and_valid_terms(modules):
    months = pd.to_datetime(["2010-01-01", "2010-06-01", "2011-02-01", None])
    frame = pd.DataFrame(
        {
            "effective_date": pd.Timestamp("2010-03-01"),
            "status_code": "PRIMRY",
            "depth_band": "Under 100 m",
            "primary_term_years": [5, 0, 5, 5],
            "first_production_month": months,
            "first_oil_month": months,
        }
    )
    audits = []
    modules.analysis.production_table(frame, audits, last_source_month="2026-10")
    stages = {row["stage"]: row for row in audits}
    for event in ("crude oil", "any hydrocarbon"):
        ordered = stages[f"Timed {event} leases"]
        assert (ordered["read"], ordered["kept"], ordered["drops"]) == (
            3,
            2,
            {"pre_effective_event": 1, "after_window": 0},
        )
        with_term = stages[f"Timed {event} leases with positive primary term"]
        assert (with_term["read"], with_term["kept"], with_term["drops"]) == (
            2,
            1,
            {"missing_or_nonpositive_primary_term": 1},
        )


def test_positive_production_by_fluid_and_earliest_month(modules, tmp_path):
    path = tmp_path / "production.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            modules.oil.MEMBER,
            "LEASE_NUMBER,PROD_YEAR,PROD_MONTH,LEASE_OIL_PROD,LEASE_CONDN_PROD,"
            "LEASE_GWG_PROD,LEASE_OWG_PROD,LEASE_WTR_PROD\n"
            " A ,2012,8,1,0,0,0,0\nA,2011,12,1,0,0,0,0\n"
            "A,2011,3,0,2,0,0,0\nB,2011,1,0,0,3,0,0\n"
            "C,2011,2,0,0,0,4,0\nD,2011,1,0,0,0,0,10\n"
            "E,2011,2,0,0,0,0,0\nF,2011,4,0,1,0,0,0\n",
        )
    leases = pd.DataFrame(
        dict(lease_id=list("ABCDEFG"), effective_date=pd.Timestamp("2010-01-01"))
    )
    dates, audits, _ = modules.oil.read_production(path, leases)
    dates = dates.set_index("lease_id")
    assert dates.first_oil_month.dropna().to_dict() == {"A": pd.Timestamp("2011-12-01")}
    assert dates.first_production_month.dropna().dt.strftime("%Y-%m").to_dict() == {
        "A": "2011-03",
        "B": "2011-01",
        "C": "2011-02",
        "F": "2011-04",
    }
    assert set(dates.index) == set("ABCDEFG")
    stages = {r["stage"]: (r["read"], r["kept"]) for r in audits}
    assert stages["Distinct observed crude oil leases"] == (2, 1)
    assert stages["Distinct observed any hydrocarbon leases"] == (6, 4)


def write_tape(path, modules, entries):
    layout = json.loads((EXAMPLE.parents[2] / modules.lease.LEASE_SCHEMA).read_bytes())[
        "tables"
    ]["lease"]
    fields = {f["name"]: f for f in layout["fields"]}
    rows = []
    for number, area, effective, low, high in entries:
        row = [" "] * max(f["start"] - 1 + f["length"] for f in fields.values())
        for name, value in {
            "Lease Number": number,
            "MMS Planning Area Code": area,
            "Lease Effective Date": effective,
            "Lease Status Code": "PRIMRY",
            "Block Low Water Depth": low,
            "Block Max Water Depth": high,
        }.items():
            start = fields[name]["start"] - 1
            row[start : start + len(value)] = value
        rows.append("".join(row))
    with ZipFile(path, "w") as archive:
        archive.writestr(layout["member"], "\n".join(rows) + "\n")


def test_lease_tape_filters_and_depth_units(modules, tmp_path):
    path = tmp_path / "leases.zip"
    write_tape(
        path,
        modules,
        [
            ("G00001", "CGM", "20050101", "100", "400"),
            ("00002", "WGM", "20261001", "100", "200"),
            ("00003", "PAC", "20100101", "100", "400"),
            ("G00004", "EGM", "20041201", "100", "400"),
            ("G00005", "EGM", "", "100", "400"),
            ("G00006", "EGM", "20270101", "100", "400"),
        ],
    )
    leases, (audit,), meta = modules.lease.read_leases(path, EXAMPLE.parents[2])
    assert leases.lease_id.tolist() == ["G00001", "00002"]
    assert leases.issue_year.tolist() == [2005, 2026]
    assert leases.lease_depth_m.tolist() == pytest.approx([121.92, 60.96])
    assert leases.block_range_crosses_band.tolist() == [True, False]
    assert meta["straddling_ranges"] == 1
    assert audit["drops"] == dict(
        missing_effective_date=1, effective_year_outside_2005_2026=2, outside_gulf=1
    )


def test_calculate_bounds_from_tape_and_bore_endpoints(modules, tmp_path):
    bounds = modules.bounds
    ids = [f"G0000{i}" for i in range(1, 10)]
    write_tape(
        tmp_path / bounds.TAPE,
        modules,
        [(lease, "CGM", "20100101", "100", "200") for lease in ids],
    )
    a, b, c, d, e, f, g, h, i = ids
    records = [
        ("000000000100", a, a, "E", "01/02/2010"),
        ("000000000101", b, c, "E", "01/03/2010"),
        ("000000000200", d, "", "D", "01/02/2010"),
        ("000000000300", e, "", "D", "12/31/2009"),
        ("000000000400", f, g, "E", ""),
        ("000000000500", g, "", "D", "12/31/2009"),
        ("000000000600", h, "", "D", "01/02/2010"),
        ("000000000700", i, "", "E", ""),
    ]
    with ZipFile(tmp_path / bounds.BORE, "w") as archive:
        archive.writestr(
            modules.bore.MEMBER,
            pd.DataFrame(
                records,
                columns=[
                    "API_WELL_NUMBER",
                    "BOTM_LEASE_NUMBER",
                    "SURF_LEASE_NUMBER",
                    "WELL_TYPE_CODE",
                    "WELL_SPUD_DATE",
                ],
            )
            .assign(REGION_CODE="G")
            .to_csv(index=False),
        )
    reference = tmp_path / "exploration.csv"
    rows = []
    for year in [*map(str, range(2005, 2021)), "All years"]:
        for band in [*modules.analysis.BANDS, "All bands"]:
            hit = year in ("2010", "All years") and band in (
                modules.analysis.BANDS[0],
                "All bands",
            )
            rows.append(
                dict(
                    issue_year=year,
                    depth_band=band,
                    leases=9 * hit,
                    explored_leases=int(hit),
                    leases_with_any_e_bore=2 * hit,
                )
            )
    pd.DataFrame(rows).to_csv(reference, index=False)
    counts = bounds.calculate_bounds(
        tmp_path,
        {bounds.BORE: {"collection_end_utc": "2026-11-23T00:00:00Z"}},
        reference,
    )
    pooled = counts["All years", "All bands"]
    assert [
        pooled[k]
        for k in (
            "original",
            "a",
            "b",
            "c",
            "d",
            "e",
            "overlap",
            "extra",
            "earlier_only",
            "missing_only",
            "both",
        )
    ] == [1, 4, 2, 5, 3, 9, 1, 4, 1, 2, 1]


def test_production_table_limits_cohort_and_has_equal_followup(modules):
    effective = pd.to_datetime(["2005-01-01"] * 4 + ["2020-12-01", "2021-01-01"])
    events = pd.to_datetime(
        ["2005-01-01", "2009-12-01", "2010-01-01", None, "2025-11-01", "2021-01-01"]
    )
    frame = pd.DataFrame(
        dict(
            effective_date=effective,
            depth_band=modules.analysis.BANDS[0],
            first_oil_month=events,
            first_production_month=events,
            primary_term_years=5,
            status_code="PROD",
        )
    )
    table = modules.analysis.production_table(frame, last_source_month="2026-10")
    assert set(table["eligible_effective_years"]) == {"2005 to 2020"}
    oil = table[
        table.event.eq("Crude oil") & table.depth_band.eq("All bands")
    ].set_index("period")
    assert set(oil.index) == {
        "2005 to 2009",
        "2010 to 2014",
        "2015 to 2019",
        "2020 only",
        "2005 to 2020",
    }
    pooled = oil.loc["2005 to 2020"]
    assert (
        pooled.leases,
        pooled.timed_leases,
        pooled.after_window_leases,
        pooled.share_pct,
        pooled.months_median,
    ) == (5, 3, 1, 60, 59)
    assert pd.isna(oil.loc["2010 to 2014", "share_pct"])
    assert oil.loc["2020 only", "months_median"] == 59
    with pytest.raises(ValueError, match="follow.up"):
        modules.analysis.production_table(frame, last_source_month="2025-10")
    frame.loc[0, "effective_date"] += pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="mid.month"):
        modules.analysis.production_table(frame, last_source_month="2026-10")


@pytest.mark.parametrize("kind", ["cwd", "unrelated", "symlink"])
def test_destination_rejected_before_build(modules, tmp_path, monkeypatch, kind):
    data = tmp_path / "inputs"
    data.mkdir()
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    dest = Path(".") if kind == "cwd" else Path(kind)
    if kind == "unrelated":
        dest.mkdir()
        (dest / "keep").touch()
    if kind == "symlink":
        dest.symlink_to(tmp_path / "missing", target_is_directory=True)
    monkeypatch.setattr(
        sys, "argv", ["derive", "--data-dir", str(data), "--output-dir", str(dest)]
    )
    monkeypatch.setattr(
        modules.derive,
        "staged_build",
        lambda parent: pytest.fail("started build"),
    )
    with pytest.raises((ValueError, SystemExit)):
        modules.derive.main()


def test_writer_manifest_and_trend_cells():
    manifest = json.loads((OUTPUT / "figures.json").read_bytes())
    assert len(manifest) == 5
    for fig in manifest:
        rows = read_rows(OUTPUT / fig["csv"])
        root = ET.fromstring((OUTPUT / fig["svg"]).read_bytes())
        labels = set(root.itertext())
        assert fig["record_types"] and fig["question"].endswith("?")
        assert 3 <= len(fig["bullets"]) <= 4
        for bullet in fig["bullets"]:
            assert bullet["text"] and bullet["cells"]
            source_rows = read_rows(OUTPUT / bullet["csv"]) if "csv" in bullet else rows
            for cell in bullet["cells"]:
                matches = [
                    r
                    for r in source_rows
                    if all(r[k] == v for k, v in cell["filter"].items())
                ]
                assert len(matches) == 1
                assert (
                    format(float(matches[0][cell["column"]]), cell["format"])
                    in bullet["text"]
                )
        if fig["csv"] in (
            "spud_share_trend.csv",
            "spud_years_trend.csv",
            "crude_trend.csv",
        ):
            assert {r["period"] for r in rows} == {
                "2005 to 2009",
                "2010 to 2014",
                "2015 to 2019",
            }
            assert "2020 to 2024" not in labels
        else:
            assert "2025 to 2026 (partial)" in labels


def test_first_production_eligibility_and_hydrocarbon_citations():
    for name in ("first_production.csv", "crude_trend.csv"):
        assert {r["eligible_effective_years"] for r in read_rows(OUTPUT / name)} == {
            "2005 to 2020"
        }
    figures = json.loads((OUTPUT / "figures.json").read_bytes())
    (crude,) = [fig for fig in figures if fig["csv"] == "crude_trend.csv"]
    assert "leases effective from 2005 to 2020" in crude["note"].lower()
    (hydrocarbon,) = [
        b for b in crude["bullets"] if b.get("csv") == "first_production.csv"
    ]
    assert "within five years" in hydrocarbon["text"].lower()
    assert {cell["column"] for cell in hydrocarbon["cells"]} == {
        "timed_leases",
        "leases",
        "share_pct",
        "median_years",
        "months_median",
    }
    assert all(
        cell["filter"]
        == {
            "period": "2005 to 2020",
            "depth_band": "All bands",
            "event": "Any hydrocarbon",
        }
        for cell in hydrocarbon["cells"]
    )


@pytest.mark.parametrize("stem", ["spud_share_trend", "spud_years_trend"])
def test_spud_svg_notes_keep_observation_windows(stem):
    root = ET.fromstring((OUTPUT / f"{stem}.svg").read_bytes())
    labels = " ".join(t.strip() for t in root.itertext() if t.strip())
    assert "November 2026" in labels and "fifth anniversary" in labels
    assert "365.25" not in labels
    if stem == "spud_share_trend":
        assert "Timing uses" not in labels


def test_saved_quartiles_and_mature_issuance():
    issued = read_rows(OUTPUT / "issuance.csv")
    period_years = {
        "2005 to 2009": range(2005, 2010),
        "2010 to 2014": range(2010, 2015),
        "2015 to 2019": range(2015, 2020),
        "2020 only": [2020],
        "2005 to 2020": range(2005, 2021),
    }
    for table, samples in [
        (
            "first_production",
            [("months", "timed_leases"), ("primary_term_pct", "term_leases")],
        ),
        (
            "exploration",
            [
                ("days_to_spud", "timed_leases"),
                ("days_to_any_e_bore", "leases_with_any_e_bore"),
            ],
        ),
        ("exploration_site_depth", [("days_to_spud", "timed_leases")]),
    ]:
        for row in read_rows(OUTPUT / f"{table}.csv"):
            if table == "first_production":
                assert int(row["leases"]) == sum(
                    int(r["leases"])
                    for r in issued
                    if r["depth_band"] == row["depth_band"]
                    and r["issue_year"].isdigit()
                    and int(r["issue_year"]) in period_years[row["period"]]
                )
            if table != "exploration_site_depth":
                assert int(row["open_without_observed_event"]) == sum(
                    int(row[k])
                    for k in [
                        "primry_sop_operns_without_event",
                        "prod_without_event",
                        "unit_without_event",
                    ]
                )
            for prefix, n in samples:
                q = [row[f"{prefix}_{k}"] for k in ("p25", "median", "p75")]
                if int(row[n]):
                    assert list(map(float, q)) == sorted(map(float, q))
                else:
                    assert q == ["", "", ""]


def test_spud_trends_reconcile_snapshot_and_equal_window():
    share = read_rows(OUTPUT / "spud_share_trend.csv")
    timing = read_rows(OUTPUT / "spud_years_trend.csv")
    annual = read_rows(OUTPUT / "exploration.csv")
    for a, b in zip(share, timing, strict=True):
        assert (a["period"], a["band"], a["group"]) == (
            b["period"],
            b["band"],
            b["group"],
        )
        first, last = (int(y) for y in a["period"].split(" to "))
        cohort = [
            r
            for r in annual
            if r["issue_year"].isdigit()
            and first <= int(r["issue_year"]) <= last
            and r["depth_band"] == a["band"]
        ]
        field = {
            "Observed by file date": "explored_leases",
            "Within five years": "explored_within_five_years",
        }[a["group"]]
        events = sum(int(r[field]) for r in cohort)
        n = sum(int(r["leases"]) for r in cohort)
        assert (int(a["leases"]), int(a["spud_leases"])) == (n, events)
        assert float(a["value"]) == pytest.approx(100 * events / n)
        if events:
            assert float(b["value"]) == pytest.approx(float(b["median_years"]))
            if a["group"] == "Within five years":
                assert 0 <= float(b["value"]) <= 5.01
        else:
            assert b["value"] == ""
    assert {r["group"] for r in share} == {"Observed by file date", "Within five years"}


def test_period_spud_median_uses_individual_leases_and_days_in_year(modules):
    from lease_trends import spud_rows

    dates = pd.to_datetime(["2005-01-01"] * 3 + ["2008-01-01"] * 2)
    frame = pd.DataFrame(
        dict(
            effective_date=dates,
            exploration_spud=dates + pd.to_timedelta([0, 1, 15, 365, 2200], unit="D"),
            depth_band="Under 100 m",
        )
    )
    rows = {
        r["group"]: r
        for r in spud_rows(frame)
        if r["period"] == "2005 to 2009" and r["band"] == "Under 100 m"
    }
    assert rows["Observed by file date"]["median_years"] == pytest.approx(15 / 365.25)
    assert rows["Within five years"]["median_years"] == pytest.approx(8 / 365.25)


def test_other_trend_values_match_period_counts_and_window_medians():
    periods = {
        "2005 to 2009": range(2005, 2010),
        "2010 to 2014": range(2010, 2015),
        "2015 to 2019": range(2015, 2020),
        "2020 to 2024": range(2020, 2025),
        "2025 to 2026 (partial)": range(2025, 2027),
    }
    for name, annual_name in [
        ("issuance_trend", "issuance"),
        ("status_trend", "current_status"),
    ]:
        annual = read_rows(OUTPUT / f"{annual_name}.csv")
        for r in read_rows(OUTPUT / f"{name}.csv"):
            years = periods[r["period"]]
            rows = [
                a
                for a in annual
                if a["issue_year"].isdigit()
                and int(a["issue_year"]) in years
                and a["depth_band"] == r["band"]
                and a.get("status_code", "") == r["group"]
            ]
            assert len(rows) == len(years)
            n = sum(int(a["leases"]) for a in rows)
            if name == "issuance_trend":
                assert (int(r["count"]), int(r["years"])) == (n, len(years))
                assert float(r["value"]) == pytest.approx(n / len(years))
            else:
                total = sum(int(a["cohort_leases"]) for a in rows)
                assert (int(r["status_leases"]), int(r["leases"])) == (n, total)
                assert float(r["value"]) == pytest.approx(100 * n / total)
    oil = {
        (r["period"], r["depth_band"]): r
        for r in read_rows(OUTPUT / "first_production.csv")
        if r["event"] == "Crude oil"
    }
    for r in read_rows(OUTPUT / "crude_trend.csv"):
        src = oil[r["period"], r["band"]]
        assert (r["first_crude_leases"], r["leases"]) == (
            src["timed_leases"],
            src["leases"],
        )
        if r["group"] == "Share reaching first crude":
            assert float(r["value"]) == pytest.approx(
                100 * int(src["timed_leases"]) / int(src["leases"])
            )
        elif int(src["timed_leases"]):
            assert float(r["value"]) == pytest.approx(float(src["months_median"]) / 12)
        else:
            assert r["value"] == ""
