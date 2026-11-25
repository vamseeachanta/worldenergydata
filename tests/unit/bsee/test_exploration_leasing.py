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
EXPECTED_FILES = {
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
BOUND_BANDS = {
    "Under 100 m": "<100 m",
    "100 to 500 m": "100–<500 m",
    "500 to 1,500 m": "500–<1,500 m",
    "1,500 m and deeper": "≥1,500 m",
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
    assert {path.name for path in OUTPUT.iterdir()} == EXPECTED_FILES
    assert all((OUTPUT / name).is_file() for name in EXPECTED_FILES)
    lines = (OUTPUT / "checks.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(set(lines)) == 18
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
            ["event"],
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
        "<100 m": (2, 2, 3, 4),
        "100–<500 m": (1, 7, 7, 7),
        "500–<1,500 m": (1, 11, 11, 11),
        "≥1,500 m": (1, 13, 13, 13),
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
        f"Among {values['hydrocarbon.all.timed_leases']:,} leases with ordered hydrocarbon dates, "
        f"the median is {values['hydrocarbon.all.months_median']:,} months",
        f"Among {values['oil.all.timed_leases']:,} with ordered crude dates, it is {values['oil.all.months_median']:,} months",
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
    )
    assert run.returncode != 0
    message = run.stdout + run.stderr
    assert hashlib.sha256(content).hexdigest() in message, message
    assert any(p["name"] in message and p["sha256"] in message for p in pins), message
    assert list(output.iterdir()) == [previous]
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
    assert "provisional" in notes["first_production"]
    assert "2005 to 2026 leases" in notes["first_production"]
    for name in ("exploration", "exploration_site_depth", "first_production"):
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
    output = tmp_path / "output"
    subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            str(EXAMPLE / "derive.py"),
            "--output-dir",
            str(output),
        ],
        cwd=tmp_path,
        check=True,
    )
    assert {path.name for path in output.iterdir()} == EXPECTED_FILES
    for name in sorted(EXPECTED_FILES):
        assert (output / name).read_bytes() == (OUTPUT / name).read_bytes(), name


def test_calendar_month_lag_and_primary_term_boundary(modules):
    effective = pd.Timestamp("2010-05-01")
    event_dates = pd.to_datetime(
        ["2015-05-01", "2015-04-01", "2010-05-01", "2010-04-01"]
    )
    frame = pd.DataFrame(
        {
            "depth_band": ["<100 m", "100–<500 m", "500–<1,500 m", "≥1,500 m"],
            "status_code": "PROD",
            "effective_date": effective,
            "primary_term_years": 5,
            "first_production_month": event_dates,
            "first_oil_month": event_dates,
        }
    )
    assert modules.analysis.month_lag(
        frame.effective_date, frame.first_oil_month
    ).tolist() == [60, 59, 0, -1]
    result = modules.analysis.production_table(frame).set_index(["depth_band", "event"])
    for event in ("Crude oil", "Any hydrocarbon"):
        anniversary = result.loc["<100 m", event]
        last_in_term = result.loc["100–<500 m", event]
        assert anniversary.over_term_leases == 1
        assert anniversary.primary_term_pct_median == 100
        assert last_in_term.over_term_leases == 0
        assert last_in_term.primary_term_pct_median == pytest.approx(98.33333333333333)
        pooled = result.loc["All bands", event]
        assert (
            pooled.observed_leases,
            pooled.timed_leases,
            pooled.pre_effective_leases,
        ) == (4, 3, 1)
        assert (pooled.months_p25, pooled.months_median, pooled.months_p75) == (
            29.5,
            59,
            59.5,
        )


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
            "depth_band": "<100 m",
            "effective_date": pd.Timestamp("2010-01-01"),
            "primary_term_years": 5,
            "first_oil_month": pd.to_datetime([None] * 9),
            "first_production_month": pd.to_datetime(
                [None] * 3 + ["2011-01-01"] + [None] * 5
            ),
        }
    )
    result = modules.analysis.production_table(frame).set_index(["depth_band", "event"])
    crude = result.loc["All bands", "Crude oil"]
    hydrocarbon = result.loc["All bands", "Any hydrocarbon"]
    assert (crude.without_observed_event, crude.open_without_observed_event) == (9, 5)
    assert (
        hydrocarbon.without_observed_event,
        hydrocarbon.open_without_observed_event,
    ) == (8, 4)
    assert hydrocarbon.months_median == 12
    frame.loc[0, "status_code"] = "UNCLASSIFIED"
    with pytest.raises(ValueError, match="UNCLASSIFIED"):
        modules.analysis.production_table(frame)


def test_exploration_rates_include_every_lease_and_fifth_anniversary(modules):
    frame = pd.DataFrame(
        {
            "effective_date": pd.Timestamp("2010-05-01"),
            "issue_year": 2010,
            "depth_band": "<100 m",
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
        .loc["2010", "<100 m"]
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


def test_block_depth_thresholds_enter_the_deeper_band(modules):
    depths = pd.Series([0, 99.9, 100, 499.9, 500, 1499.9, 1500, None])
    assert modules.analysis.depth_band(depths).tolist() == [
        "<100 m",
        "<100 m",
        "100–<500 m",
        "100–<500 m",
        "500–<1,500 m",
        "500–<1,500 m",
        "≥1,500 m",
        "Unknown",
    ]


def test_status_denominator_changes_with_year_and_band(modules):
    leases = pd.DataFrame(
        {
            "issue_year": [2010, 2010, 2010, 2011],
            "depth_band": ["<100 m", "<100 m", "≥1,500 m", "<100 m"],
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
        (("2010", "<100 m", "PROD"), (1, 2, 50)),
        (("2010", "≥1,500 m", "PROD"), (0, 1, 0)),
        (("2011", "<100 m", "PROD"), (1, 1, 100)),
        (("All years", "<100 m", "PROD"), (2, 3, 200 / 3)),
    ]:
        row = status.loc[key]
        assert (row.leases, row.cohort_leases, row.share_pct) == pytest.approx(expected)
    assert pd.isna(status.loc[("2011", "≥1,500 m", "PROD"), "share_pct"])


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
        assert timed + pre_effective == observed
        assert 0 <= past_term <= with_term <= timed
        assert 0 <= censored <= unobserved


def test_production_ledger_times_only_ordered_events_and_valid_terms(modules):
    months = pd.to_datetime(["2010-01-01", "2010-06-01", "2011-02-01", None])
    frame = pd.DataFrame(
        {
            "effective_date": pd.Timestamp("2010-03-01"),
            "status_code": "PRIMRY",
            "depth_band": "<100 m",
            "primary_term_years": [5, 0, 5, 5],
            "first_production_month": months,
            "first_oil_month": months,
        }
    )
    audits = []
    modules.analysis.production_table(frame, audits)
    stages = {row["stage"]: row for row in audits}
    for event in ("crude oil", "any hydrocarbon"):
        ordered = stages[f"Timed {event} leases"]
        assert (ordered["read"], ordered["kept"], ordered["drops"]) == (
            3,
            2,
            {"pre_effective_event": 1},
        )
        with_term = stages[f"Timed {event} leases with positive primary term"]
        assert (with_term["read"], with_term["kept"], with_term["drops"]) == (
            2,
            1,
            {"missing_or_nonpositive_primary_term": 1},
        )
