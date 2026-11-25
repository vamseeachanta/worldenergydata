"""Check the published BSEE abandonment counts and reproduce the pinned build."""

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
import pytest
from PIL import Image

from examples.bsee.plug_abandonment_by_depth import charts, derive, eor

EXAMPLE = (
    Path(__file__).resolve().parents[3] / "examples/bsee/plug_abandonment_by_depth"
)
OUTPUT = EXAMPLE / "output"
SERIES = (
    "Under 100 m",
    "100 to under 500 m",
    "500 to under 1,500 m",
    "1,500 m and deeper",
)
LABELS = (
    "Under 100 m",
    "100 to 500 m",
    "500 to 1,500 m",
    "1,500 m and deeper",
    "No reported depth",
)
BANDS = (*SERIES, "No depth", "All depths")
EARLIER = (
    "0 to 200 m",
    "201 to 400 m",
    "401 to 800 m",
    "801 to 1,000 m",
    "Deeper than 1,000 m",
)
CODES = ("PA", "TA", "COM", "Other")
FIGURES = ("pa_per_year_by_band", "status_share_by_band", "ta_age_by_band")
TABLES = ("status_by_band.csv", "ta_by_band.csv", "pa_pace_by_band.csv")
EXPECTED = {
    *TABLES,
    "checks.txt",
    "numbers.json",
    "r4-reproduction.csv",
    "pa_per_year_by_band.csv",
    *(f"{figure}.{ext}" for figure in FIGURES for ext in ("png", "svg")),
}


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def check_headlines(folder):
    index = json.loads((folder / "numbers.json").read_bytes(), parse_float=Decimal)
    tables = {name: read_rows(folder / name) for name in TABLES}
    seen = set()
    for entry in index["headlines"]:
        name, key, field = entry["table"], entry["filter"], entry["field"]
        identity = (name, tuple(sorted(key.items())), field)
        assert identity not in seen, identity
        seen.add(identity)
        matches = [
            row for row in tables[name] if all(row[k] == str(v) for k, v in key.items())
        ]
        assert len(matches) == 1, identity
        cell = matches[0][field]
        assert (Decimal(cell) if cell else None) == entry["value"], identity
    assert len(seen) == 270


def test_headlines_match_unique_csv_rows():
    check_headlines(OUTPUT)


def test_changed_csv_cell_fails_headline_check(tmp_path):
    for name in (*TABLES, "numbers.json"):
        shutil.copyfile(OUTPUT / name, tmp_path / name)
    target = tmp_path / "status_by_band.csv"
    rows = read_rows(target)
    rows[0]["wells"] = str(int(rows[0]["wells"]) + 1)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(AssertionError, match="wells"):
        check_headlines(tmp_path)


def check_band_totals(rows, fields):
    assert Counter(row["band"] for row in rows) == Counter(BANDS)
    band_rows = [row for row in rows if row["band"] != "All depths"]
    (all_depths,) = [row for row in rows if row["band"] == "All depths"]
    for field in fields:
        assert sum(int(row[field]) for row in band_rows) == int(
            all_depths[field]
        ), field
    return all_depths


def test_stock_and_age_conservation():
    stock = read_rows(OUTPUT / "status_by_band.csv")
    all_depths = check_band_totals(
        stock,
        [
            "wells",
            *CODES,
            *(f"pa_in_{year}s" for year in (1990, 2000, 2010, 2020)),
            *(
                f"{code}_depth_{direction}_5pct"
                for code in ("PA", "TA")
                for direction in ("minus", "plus")
            ),
        ],
    )
    assert [int(all_depths[k]) for k in ("wells", *CODES)] == [
        37513,
        30684,
        2896,
        3579,
        354,
    ]
    for row in stock:
        assert sum(int(row[code]) for code in CODES) == int(row["wells"]), row["band"]
    ages = read_rows(OUTPUT / "ta_by_band.csv")
    check_band_totals(ages, ["ta_count", "ta_ge_10_years", "ta_since_2023"])
    assert {r["band"]: r["ta_count"] for r in ages} == {
        r["band"]: r["TA"] for r in stock
    }


def test_annual_pa_conservation_including_unreported_depth():
    annual = read_rows(OUTPUT / "pa_per_year_by_band.csv")
    assert list(annual[0]) == ["year", *LABELS]
    assert [int(row["year"]) for row in annual] == list(range(1960, 2026))
    assert any(int(row["No reported depth"]) for row in annual)

    # The ledger records independent well counts for all 66 years. The pace
    # table also supplies band-specific counts and pooled totals from 2005.
    checks = (OUTPUT / "checks.txt").read_text(encoding="utf-8")
    records = re.findall(
        r"^PASS \| Figure 3 annual PA conservation (\d+) \| band sum \d+, all-depth latest-status PA (\d+)",
        checks,
        re.MULTILINE,
    )
    assert Counter(year for year, _ in records) == Counter(
        row["year"] for row in annual
    )
    totals = dict(records)
    pace = read_rows(OUTPUT / "pa_pace_by_band.csv")
    assert {int(row["year"]) for row in pace} == set(range(2005, 2026))
    for row in annual:
        year = row["year"]
        total = sum(int(row[label]) for label in LABELS)
        assert total == int(totals[year]), year
        if int(year) < 2005:
            continue
        period = [p for p in pace if p["year"] == year]
        pooled = check_band_totals(
            period,
            [
                "pa_wells",
                "eor_pa_wells",
                "eor_ta_wells",
                "pa_2021_2025",
                "pa_2016_2025",
                "ta_plus_com",
            ],
        )
        assert total == int(pooled["pa_wells"]), year
        by_band = {p["band"]: p["pa_wells"] for p in period}
        for band, label in zip(BANDS[:-1], LABELS, strict=True):
            assert row[label] == by_band[band], (year, band)


def test_inventory_and_record_counts():
    assert {p.name for p in OUTPUT.iterdir()} == EXPECTED
    assert all((OUTPUT / name).is_file() for name in EXPECTED)
    checks = (OUTPUT / "checks.txt").read_text(encoding="utf-8").splitlines()
    counts = {}
    for line in checks:
        verdict, stage, detail = line.split(" | ", 2)
        assert verdict == "PASS", stage
        if detail.startswith("read "):
            match = re.fullmatch(r"read (\d+) = kept (\d+) \+ dropped (\d+)", detail)
            assert match, line
            read, kept, dropped = map(int, match.groups())
            assert read == kept + dropped, stage
            assert stage not in counts
            counts[stage] = (read, kept, dropped)
    assert len(counts) == 204
    assert counts["wells with a non-CNL bore"] == (38291, 37529, 762)
    assert counts["remaining wells with any dated spud"] == (37529, 37513, 16)


def test_earlier_comparisons_match_at_printed_precision():
    rows = read_rows(OUTPUT / "r4-reproduction.csv")
    assert (
        len(rows) == len({(r["source"], r["band"], r["metric"]) for r in rows}) == 114
    )
    for row in rows:
        computed = round(
            Decimal(row["computed_unrounded"]), int(row["published_decimals"])
        )
        assert (
            computed == Decimal(row["computed_value"]) == Decimal(row["r4_value"])
        ), row
        assert Decimal(row["difference"]) == 0 and row["disposition"] == "match", row


def read_pins():
    return json.loads((EXAMPLE / "source_pins.json").read_bytes())["sources"]


def test_readme_matches_archive_pins():
    pins = read_pins()
    assert Counter(p["name"] for p in pins) == Counter(
        ("BoreholeRawData.zip", "eWellEORRawData.zip")
    )
    expected = [(p["name"], p["url"], p["last_modified"], p["sha256"]) for p in pins]
    readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    documented = re.findall(
        r"^\| \[([^\]]+\.zip)\]\((https://www\.data\.bsee\.gov/[^)]+)\) "
        r"\| ([^|]+?) \| `([0-9a-f]{64})` \|$",
        readme,
        re.MULTILINE,
    )
    assert sorted(documented) == sorted(expected)
    members = re.findall(
        r"^\| `([^`]+\.txt)` \| `([0-9a-f]{64})` \|$", readme, re.MULTILINE
    )
    assert sorted(members) == sorted(
        (pin["member"]["name"], pin["member"]["sha256"]) for pin in pins
    )


def test_wrong_archive_reports_both_digests(tmp_path, monkeypatch):
    pins = read_pins()
    content = b"synthetic file with incorrect digest\n"
    for pin in pins:
        (tmp_path / pin["name"]).write_bytes(content)
    destination = tmp_path / "output"
    destination.mkdir()
    previous = destination / "checks.txt"
    previous.write_bytes(b"previous build\n")
    # The CLI flag takes precedence over the environment setting.
    monkeypatch.setenv("BSEE_W1_DATA_DIR", str(tmp_path / "absent"))
    result = subprocess.run(
        [
            sys.executable,
            str(EXAMPLE / "derive.py"),
            "--data-dir",
            str(tmp_path),
            "--output",
            str(destination),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    message = result.stdout + result.stderr
    assert hashlib.sha256(content).hexdigest() in message, message
    assert any(p["name"] in message and p["sha256"] in message for p in pins), message
    assert list(destination.iterdir()) == [previous]
    assert previous.read_bytes() == b"previous build\n"


@pytest.mark.skipif(
    not os.environ.get("BSEE_W1_DATA_DIR"), reason="pinned BSEE ZIPs were not supplied"
)
def test_regeneration_is_byte_identical(tmp_path, monkeypatch):
    archives = Path(os.environ["BSEE_W1_DATA_DIR"]).resolve()
    monkeypatch.setenv("BSEE_W1_DATA_DIR", str(archives))
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(variable, raising=False)
    destination = tmp_path / "output"
    subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--python",
            "3.11.15",
            str(EXAMPLE / "derive.py"),
            "--output",
            str(destination),
        ],
        cwd=tmp_path,
        check=True,
    )
    assert {p.name for p in destination.iterdir()} == EXPECTED
    for name in sorted(EXPECTED):
        assert (destination / name).read_bytes() == (OUTPUT / name).read_bytes(), name


def test_latest_bore_keeps_its_status_and_depth():
    columns = [
        "API_WELL_NUMBER",
        "REGION_CODE",
        "BOREHOLE_STAT_CD",
        "BOREHOLE_STAT_DT",
        "WELL_SPUD_DATE",
        "WATER_DEPTH",
    ]
    raw = pd.DataFrame(
        [
            # The unspudded, cancelled bore can supply the latest status.
            ("000000000100", "G", "COM", "1/1/2000", "1/1/1999", "200"),
            ("000000000101", "G", "CNL", "1/1/2010", None, "500"),
            ("000000000200", "G", "CNL", "1/1/2001", "1/1/2000", "70"),
            ("000000000201", "G", "CNL", "1/1/2011", None, "71"),
            ("000000000300", "G", "PA", "1/1/2002", None, "400"),
            ("000000000400", "P", "PA", "1/1/2003", "1/1/2001", "100"),
            # The last tied row wins even with a smaller API suffix and depth.
            ("000000000509", "G", "COM", "3/1/2020", "2/1/1999", "800"),
            ("000000000501", "G", "TA", "3/1/2020", "1/1/1999", "700"),
            ("000000000508", "G", "PA", "12/1/2019", "3/1/1999", "900"),
            ("000000000510", "G", "DRL", None, "4/1/2020", "999"),
            ("000000000600", "G", "PA", "1/1/2004", "1/1/2000", "0"),
            ("000000000601", "G", "ST", "1/1/2002", "1/1/1999", "20"),
            ("000000000700", "G", "TA", "1/1/2005", "1/1/2001", None),
        ],
        columns=columns,
    )
    wells = derive.select_wells(raw, derive.Audit()).set_index("well")
    assert Counter(wells.index) == Counter(
        ("0000000001", "0000000005", "0000000006", "0000000007")
    )
    assert wells.at["0000000001", "status"] == "Other"
    assert wells.at["0000000001", "depth_m"] == pytest.approx(152.4)
    assert wells.at["0000000005", "status"] == "TA"
    assert wells.at["0000000005", "status_date"] == pd.Timestamp("2020-03-01")
    assert wells.at["0000000005", "depth_m"] == pytest.approx(213.36)
    assert wells.loc[["0000000006", "0000000007"], "depth_m"].isna().all()


@pytest.mark.parametrize(
    "scheme,bands,depths,indices",
    [
        (
            "r4",
            EARLIER,
            [199.99, 200, 200.01, 400, 400.01, 800, 800.01, 1000, 1000.01],
            [0, 0, 1, 1, 2, 2, 3, 3, 4],
        ),
        (
            "series",
            SERIES,
            [0.1, 99.99, 100, 499.99, 500, 1499.99, 1500, 1500.01],
            [0, 0, 1, 1, 2, 2, 3, 3],
        ),
    ],
)
def test_continuous_metre_edges(scheme, bands, depths, indices):
    actual = derive.assign_bands(pd.Series([*depths, 0, None]), scheme)
    assert list(actual) == [*(bands[i] for i in indices), "No depth", "No depth"]


def test_age_quartiles_and_pace_on_four_wells():
    wells = pd.DataFrame(
        {
            "well": list("abcd"),
            "status": ["TA", "TA", "PA", "PA"],
            "status_date": pd.to_datetime(
                ["2022-11-23", "2014-11-23", "2025-01-01", "2016-01-01"]
            ),
            "depth_m": [50, 75, 95.5, 101],
        }
    )
    events = pd.DataFrame([("c", 2025, "PA")], columns=["well", "year", "status"])
    audit = derive.Audit()
    stock, ages, pace = derive.summarize(wells, events, "series", audit)
    shallow = stock.set_index("band").loc[SERIES[0]]
    assert (shallow.PA, shallow.PA_depth_minus_5pct, shallow.PA_depth_plus_5pct) == (
        1,
        2,
        0,
    )
    # The two shallow TA wells have exactly 4 and 12 years in status.
    age = ages.set_index("band").loc[SERIES[0]]
    assert (age.q25_years, age.median_years, age.q75_years, age.ta_ge_10_years) == (
        6,
        8,
        10,
        1,
    )
    total = pace.set_index(["band", "year"]).loc[("All depths", 2025)]
    assert (total.pa_2021_2025, total.pa_2016_2025) == (1, 2)
    assert total.pa_per_year_2021_2025 == total.pa_per_year_2016_2025 == 0.2
    assert total.ta_backlog_years_2021_2025 == 10
    assert all(line.startswith("PASS |") for line in audit.lines)


def test_annual_series_uses_the_same_population_before_and_after_2005(monkeypatch):
    monkeypatch.setitem(sys.modules, "charts", charts)
    years = [1959, 1960, 1960, 2004, 2005, 2025, 2026]
    wells = pd.DataFrame(
        {
            "well": list("abcdefg"),
            "status": ["PA", "PA", "TA", "PA", "PA", "PA", "PA"],
            "status_date": pd.to_datetime([f"{year}-01-01" for year in years]),
            "depth_m": [None, None, 10, 500, 100, 1500, None],
        }
    )
    expected = {
        (2005, SERIES[1]),
        (2025, SERIES[3]),
        (2005, "All depths"),
        (2025, "All depths"),
    }
    pace = pd.DataFrame(
        [
            (year, band, int((year, band) in expected))
            for year in range(2005, 2026)
            for band in BANDS
        ],
        columns=["year", "band", "pa_wells"],
    ).sample(frac=1, random_state=1)
    table = derive.figure3_table(wells, pace)
    assert list(table.index) == list(range(1960, 2026))
    assert list(table.columns) == list(LABELS)
    assert table.loc[[1960, 2004, 2005, 2025]].values.tolist() == [
        [0, 0, 0, 0, 1],
        [0, 0, 1, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 0, 1, 0],
    ]
    assert table.sum().sum() == 4
    known = derive.figure3_table(wells[wells.well.ne("b")], pace)
    assert list(known.columns) == list(LABELS[:-1])
    incomplete = pace.drop(pace.query("year == 2006 and band == 'No depth'").index)
    with pytest.raises(ValueError):
        derive.figure3_table(wells, incomplete)
    shifted = pace.copy()
    shifted.loc[(shifted.year == 2005) & (shifted.band == SERIES[0]), "pa_wells"] = 1
    shifted.loc[(shifted.year == 2005) & (shifted.band == SERIES[1]), "pa_wells"] = 0
    with pytest.raises(ValueError):
        derive.figure3_table(wells, shifted)


def test_repeated_distinct_and_excluded_reports():
    columns = [
        "API_WELL_NUMBER",
        "EOR_OPERATION_CD",
        "BOREHOLE_STAT_CD",
        "BOREHOLE_STAT_DT",
    ]
    raw = pd.DataFrame(
        [
            ("001234567800", "A", "TA", "11/3/2020"),
            ("001234567801", "A", "TA", "11/3/2020 3:37:17 PM"),
            ("001234567801", "A", "PA", "12/1/2020"),
            ("001234567801", "A", "PA", "1/2/2021"),
            ("001234567801", "C", "PA", "1/2/2022"),
            ("001234567801", "A", "COM", "2/3/2021"),
            ("009999999901", "A", "PA", "1/2/2020"),
            ("001234567801", "A", "TA", None),
        ],
        columns=columns,
    )
    wells = pd.DataFrame({"well": ["0012345678"]})
    audit = derive.Audit()
    counted = eor.eor_counts(raw, wells, audit)
    assert list(counted.columns) == ["well", "year", "status"]
    assert Counter(counted.itertuples(index=False, name=None)) == Counter(
        [
            ("0012345678", 2020, "TA"),
            ("0012345678", 2020, "PA"),
            ("0012345678", 2021, "PA"),
        ]
    )
    # Independently classified exclusions: operation C, ineligible well,
    # status COM, undated report and a duplicate TA report, respectively.
    assert audit.lines == [
        "PASS | EOR abandonment operation | read 8 = kept 7 + dropped 1",
        "PASS | EOR on eligible Gulf well | read 7 = kept 6 + dropped 1",
        "PASS | EOR reached PA or TA | read 6 = kept 5 + dropped 1",
        "PASS | EOR with dated outcome | read 5 = kept 4 + dropped 1",
        "PASS | EOR unique well-year-status | read 4 = kept 3 + dropped 1",
    ]


def test_eor_coverage_requires_same_well_year_and_permanent_status():
    raw = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["001234567800"] * 4,
            "EOR_OPERATION_CD": ["A", "A", "C", "A"],
            "BOREHOLE_STAT_CD": ["COM", "COM", "COM", "PA"],
            "BOREHOLE_STAT_DT": ["1/1/2007", "1/1/2006", "1/1/2007", "1/2/2007"],
        }
    )
    wells = pd.DataFrame(
        {
            "well": ["0012345678", "0012345679", "0012345680", "0012345681"],
            "status": ["PA", "PA", "TA", "PA"],
            "status_date": pd.to_datetime(
                ["2007-01-02", "2007-01-08", "2007-01-02", "2010-01-01"]
            ),
        }
    )
    events = pd.DataFrame(
        [
            ("0012345678", 2007, "PA"),
            ("0012345679", 2006, "PA"),
            ("0012345679", 2007, "TA"),
            ("0012345680", 2007, "PA"),
            ("0012345681", 2010, "PA"),
        ],
        columns=["well", "year", "status"],
    )
    audit = derive.Audit()
    eor.eor_diagnostics(raw, wells, events, audit)
    assert audit.diagnostics["eor_other_2007_2025"] == 1
    assert audit.diagnostics["eor_coverage_2005"] == (0, 0)
    assert audit.diagnostics["eor_coverage_2007"] == (1, 2)
    assert audit.diagnostics["eor_coverage_2010_2025"] == (1, 1)


def test_figures_are_deterministic_editable_and_readable(tmp_path):
    status = pd.read_csv(OUTPUT / "status_by_band.csv")
    ages = pd.read_csv(OUTPUT / "ta_by_band.csv")
    annual = pd.read_csv(OUTPUT / "pa_per_year_by_band.csv", index_col="year")
    with pytest.raises(ValueError):
        charts.render_charts(tmp_path, status.iloc[::-1], ages.iloc[::-1])
    charts.render_charts(tmp_path, status, ages, annual)
    files = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert set(files) == {f"{name}.{ext}" for name in FIGURES for ext in ("png", "svg")}
    charts.render_charts(tmp_path, status, ages, annual)
    for name, payload in files.items():
        path = tmp_path / name
        assert payload == path.read_bytes(), name
        if path.suffix == ".png":
            with Image.open(path) as image:
                assert image.width > 1000 and image.height > 500
                image.verify()
            continue
        root = ElementTree.parse(path).getroot()
        tags = {el.tag.split("}")[-1] for el in root.iter()}
        assert "text" in tags and not tags.intersection(
            {"clipPath", "pattern", "filter", "mask", "image"}
        )
        text = " ".join("".join(el.itertext()) for el in root.findall(".//{*}text"))
        assert not re.search(r"[\u2013\u2014]|to under", text)
        assert all(label in text for label in LABELS[:-1])
        assert "23 Nov 2026" in text
        if path.stem == "pa_per_year_by_band":
            assert "No reported depth" in text
            assert (
                "Gulf of America wells permanently abandoned per year, by water depth"
                in text
            )
        elif path.stem == "ta_age_by_band":
            assert all(f"{age:.1f}" in text for age in ages.median_years.iloc[:4])
        else:
            assert all(f"{share:.1f}%" in text for share in status.PA_pct.iloc[:4])
