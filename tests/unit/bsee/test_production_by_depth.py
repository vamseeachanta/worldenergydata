"""Synthetic calculation cases and independent readback of the BSEE article evidence."""

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/production_by_depth"
OUTPUT = EXAMPLE / "output"
BANDS = {"<100 m", "100–<500 m", "500–<1,500 m", "≥1,500 m"}
TABLE_BANDS = {
    "Under 100": "under100",
    "100 to under 500": "100_500",
    "500 to under 1,500": "500_1500",
    "1,500 and deeper": "1500plus",
    "All assigned depths": "all",
}


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def select(rows, filters):
    return [row for row in rows if all(row[k] == str(v) for k, v in filters.items())]


def check_headlines(folder):
    numbers = json.loads((folder / "numbers.json").read_text(encoding="utf-8"))
    tables = {path.name: read_rows(path) for path in folder.glob("*.csv")}
    coverage = numbers["coverage_source"]
    assert coverage["operation"] == "max(month)"
    months = select(tables[coverage["table"]], coverage["filter"])
    last_month = max(row["month"] for row in months)
    assert numbers["coverage_through"] == last_month == "2026-09"
    headlines = numbers["headlines"]
    assert {h["operation"] for h in headlines.values()} == {
        "row",
        "mean",
        "ratio",
        "sum",
    }
    for slug in TABLE_BANDS.values():
        for measure in ("Post-completion WAR", "Intervention approval"):
            for age in (0, 1, 5, 10, 20):
                key = f"{slug}/{measure}/{age}"
                assert (
                    "share_among_completion_observed" in headlines[key]["fields"]
                ), key

    for key, spec in headlines.items():
        if spec["table"] == "record_counts.csv":
            assert spec["filter"]["disposition"] in {"read", "kept", "dropped"}, key
        table = tables[spec["table"]]
        rows = select(table, spec["filter"])
        operation = spec["operation"]
        if operation == "sum":
            # The full period has one annual observation per band per year.
            assert sorted(int(r["year"]) for r in rows) == list(range(2005, 2027)), key
        elif operation == "mean":
            year = spec["filter"]["year"]
            end = int(last_month[-2:]) if year == 2026 else 12
            assert sorted(r["month"] for r in rows) == [
                f"{year}-{m:02d}" for m in range(1, end + 1)
            ], key
        else:
            assert len(rows) == 1, key

        if operation == "ratio":
            denominator = select(table, spec["denominator_filter"])
            assert len(denominator) == 1, key

        fields = spec["fields"]
        assert set(fields) == set(spec["values"]), key
        for field in fields:
            # CSV numeric cells and JSON use the same decimal representation.
            values = [json.loads(r[field]) if r[field] else None for r in rows]
            if operation == "sum":
                value = sum(values)
            elif operation == "mean":
                value = sum(values) / len(values)
            elif operation == "ratio":
                value = values[0] / json.loads(denominator[0][field])
            else:
                value = values[0]
            assert value == spec["values"][field], f"{key} {field}"


def test_all_headlines_match_csvs():
    check_headlines(OUTPUT)


def test_changed_csv_cell_breaks_headline(tmp_path):
    shutil.copy(OUTPUT / "numbers.json", tmp_path)
    for path in OUTPUT.glob("*.csv"):
        shutil.copy(path, tmp_path)
    path = tmp_path / "annual_wells.csv"
    rows = read_rows(path)
    (row,) = select(rows, {"year": 2005, "band": "<100 m"})
    row["oil_bbl"] = str(int(row["oil_bbl"]) + 1)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(AssertionError, match=r"under100/year/2005 oil_bbl"):
        check_headlines(tmp_path)


@pytest.mark.parametrize(
    "table,keys,fields",
    [
        (
            "monthly_production",
            ("month",),
            ("monthly_producing_wells", "oil_bbl", "gas_mcf"),
        ),
        ("annual_wells", ("year",), ("producing_wells", "oil_bbl", "gas_mcf")),
        (
            "completion_lag",
            ("population",),
            ("wells", "pre_completion_wells", "same_month_wells"),
        ),
        ("decline", ("completion_type", "age_month"), ("baseline_wells", "wells")),
        (
            "interventions",
            ("measure", "age_year"),
            (
                "eligible_wells",
                "event_wells",
                "completion_observed_wells",
                "pre_origin_event_wells",
            ),
        ),
        (
            "article_summary",
            (),
            (
                "distinct_producing_wells",
                "producing_well_months",
                "cohort_completions",
                "ever_produced_wells",
                "produced_in_or_after_c_month_wells",
                "supported_starts",
                "war_by_cutoff_wells",
                "permit_by_cutoff_wells",
            ),
        ),
    ],
)
def test_depth_bands_conserve_additive_fields(table, keys, fields):
    groups = defaultdict(list)
    for row in read_rows(OUTPUT / f"{table}.csv"):
        groups[tuple(row[k] for k in keys)].append(row)
    assert groups
    for group, rows in groups.items():
        assert Counter(row["band"] for row in rows) == Counter(BANDS | {"All"}), group
        (pooled,) = select(rows, {"band": "All"})
        for field in fields:
            total = sum(int(r[field]) for r in rows if r["band"] != "All")
            assert int(pooled[field]) == total, (group, field)


def test_record_counts_conserve_rows_and_reported_volumes():
    stages = defaultdict(list)
    for row in read_rows(OUTPUT / "record_counts.csv"):
        stages[row["stage"]].append(row)
    archives = [pin["name"] for pin in load_pins() if pin["name"].startswith("ogora")]
    assert {f"OGOR depth join / {name}" for name in archives} <= stages.keys()
    for stage, rows in stages.items():
        by_reason = {(row["disposition"], row["reason"]) for row in rows}
        assert len(by_reason) == len(rows), stage
        (source,) = select(rows, {"disposition": "read"})
        (kept,) = select(rows, {"disposition": "kept"})
        dropped = select(rows, {"disposition": "dropped"})
        flagged = select(rows, {"disposition": "flagged"})
        assert 2 + len(dropped) + len(flagged) == len(rows), stage
        assert sum(int(r["rows"]) for r in flagged) <= int(kept["rows"]), stage
        assert all(int(row["rows"]) >= 0 for row in rows), stage
        for field in ("rows", "oil_bbl", "gas_mcf"):
            if not source[field]:
                assert all(row[field] == "" for row in rows), (stage, field)
                continue
            accounted = sum(json.loads(row[field]) for row in [kept, *dropped])
            assert accounted == json.loads(source[field]), (stage, field)


def load_pins():
    return json.loads((EXAMPLE / "source_pins.json").read_text(encoding="utf-8"))[
        "sources"
    ]


def test_readme_matches_source_pins():
    pins = load_pins()
    names = [pin["name"] for pin in pins]
    assert len(names) == len(set(names))
    required = {
        "BoreholeRawData.zip",
        "eWellAPMRawData.zip",
        "eWellEORRawData.zip",
        "eWellWARRawData.zip",
        "LeaseOwnerRawData.zip",
        "ProductionRawData.zip",
        "lsetapefixed.zip",
        "ogoradelimit.zip",
        *(f"ogora{year}delimit.zip" for year in range(2005, 2026)),
    }
    assert set(names) == required
    expected = [(p["name"], p["url"], p["last_modified"], p["sha256"]) for p in pins]
    readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    documented = re.findall(
        r"^\| \[([^\]]+\.zip)\]\((https://[^)]+)\) \| ([^|]+?) \| `([0-9a-f]{64})` \|",
        readme,
        re.MULTILINE,
    )
    assert sorted(documented) == sorted(expected)


def test_wrong_zip_fails_with_expected_and_actual_digests(tmp_path):
    pin = load_pins()[0]
    archive = tmp_path / pin["name"]
    content = b"synthetic archive with the wrong digest\n"
    archive.write_bytes(content)
    output = tmp_path / "output"
    output.mkdir()
    previous = output / "checks.txt"
    previous.write_bytes(b"previous build\n")
    result = subprocess.run(
        [
            "uv",
            "run",
            str(EXAMPLE / "derive.py"),
            "--data-dir",
            str(tmp_path),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode != 0
    diagnostic = result.stdout + result.stderr
    for detail in (archive.name, pin["sha256"], hashlib.sha256(content).hexdigest()):
        assert detail in diagnostic, diagnostic
    assert list(output.iterdir()) == [previous]
    assert previous.read_bytes() == b"previous build\n"


@pytest.mark.skipif(
    not os.environ.get("BSEE_PROD_DATA_DIR"),
    reason="the pinned BSEE archives were not supplied",
)
def test_regeneration_is_byte_identical(tmp_path, monkeypatch):
    output = tmp_path / "output"
    data_dir = Path(os.environ["BSEE_PROD_DATA_DIR"]).resolve()
    monkeypatch.setenv("BSEE_PROD_DATA_DIR", str(data_dir))
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(variable, raising=False)
    subprocess.run(
        ["uv", "run", str(EXAMPLE / "derive.py"), "--output-dir", str(output)],
        check=True,
        cwd=tmp_path,
    )
    expected = {file.name for file in OUTPUT.iterdir()}
    assert {file.name for file in output.iterdir()} == expected
    for name in sorted(expected):
        assert (output / name).read_bytes() == (OUTPUT / name).read_bytes(), name


def test_signed_well_months_and_activity(monkeypatch):
    import pandas as pd

    monkeypatch.syspath_prepend(str(EXAMPLE))
    import production

    # The two reversed bookings must contribute their signed volumes only.
    raw = pd.DataFrame(
        [
            ("cancelled", 500, 0, 10),
            ("cancelled", -500, 0, 0),
            ("negative", 100, 0, 10),
            ("negative", -200, 0, 0),
            ("partial", 100, 0, 10),
            ("partial", -20, 0, 0),
            ("gas", 0, 10, 2),
            ("zero_days", 20, 0, 0),
            ("overlap", 20, 0, 5),
            ("overlap", 20, 0, 4),
        ],
        columns=["api10", "oil_bbl", "gas_mcf", "days"],
    ).assign(month=pd.Timestamp("2020-01-01"))
    months = production.collapse_well_months(raw)
    wells = months.set_index("api10")
    assert wells.oil_bbl.to_dict() == {
        "cancelled": 0,
        "negative": -100,
        "partial": 80,
        "gas": 0,
        "zero_days": 20,
        "overlap": 40,
    }
    assert set(wells.index[wells.positive]) == {
        "partial",
        "gas",
        "zero_days",
        "overlap",
    }
    assert wells.rate_status.to_dict() == {
        "cancelled": "no_hydrocarbon_production",
        "negative": "no_hydrocarbon_production",
        "partial": "observed",
        "gas": "observed",
        "zero_days": "invalid_days",
        "overlap": "unresolved_overlap",
    }
    assert wells.oil_rate.dropna().to_dict() == {"partial": 8.0, "gas": 0.0}

    def check(name, condition):
        assert condition, name

    activity, summary = production.build_activity_summary(
        months.assign(band=production.DEPTH_BANDS[0]), check
    )
    assert activity.set_index("band").loc["All", "monthly_producing_wells"] == 4
    pooled = summary.set_index("band").loc["All"]
    assert pooled.distinct_producing_wells == pooled.producing_well_months == 4
    assert pooled.median_well_month_oil_bbl == 30


@pytest.mark.parametrize(
    "last_month,malformed_api",
    [("2026-01-01", False), ("2026-02-01", True)],
    ids=["december-in-prior-archive", "invalid-api12-with-covered-prefix"],
)
def test_recent_source_counts_signed_valid_wells(
    tmp_path, monkeypatch, last_month, malformed_api
):
    from io import StringIO
    from zipfile import ZipFile

    import pandas as pd

    monkeypatch.syspath_prepend(str(EXAMPLE))
    import production

    last = pd.Timestamp(last_month)
    previous = last - pd.DateOffset(months=1)
    api = "0123456789"
    band = production.DEPTH_BANDS[-1]
    lookup = pd.DataFrame({"band": [band]}, index=[api])
    # Supply the expected net volumes and positive flags independently of the parser.
    months = pd.DataFrame(
        {
            "api10": api,
            "month": [previous, last],
            "band": band,
            "positive": [True, False],
            "oil_bbl": [30, 0],
            "gas_mcf": [5, 0],
        }
    )
    raw_rows = [
        (previous, api + "00", 30, 5),
        (last, api + "00", 10, 0),
        (last, api + "01", -10, 0),
    ]
    if malformed_api:
        raw_rows.append((previous, api + "X9", 100, 100))
    archives = defaultdict(list)
    for month, api12, oil, gas in raw_rows:
        name = (
            "ogoradelimit" if month.year == last.year else f"ogora{month.year}delimit"
        )
        row = [""] * 19
        row[2], row[3], row[5], row[6], row[8] = (
            month.strftime("%Y%m"),
            "1",
            oil,
            gas,
            api12,
        )
        archives[name].append(row)
    for name, rows in archives.items():
        content = StringIO(newline="")
        csv.writer(content).writerows(rows)
        path = tmp_path / f"{name}.zip"
        with ZipFile(path, "w") as archive:
            archive.writestr(f"{name}.txt", content.getvalue().encode("latin-1"))
        parsed = production.read_ogor(path)
        assert parsed.api10.isna().sum() == (malformed_api and name == "ogoradelimit")

    def check(name, condition, detail):
        assert condition, (name, detail)

    notes = production.check_recent_source(tmp_path, lookup, months, last, check)
    assert f"{1 + int(malformed_api)} raw rows" in notes[0]
    assert "2 raw rows" in notes[1]


@pytest.fixture
def source_tables(monkeypatch):
    import pandas as pd

    monkeypatch.syspath_prepend(str(EXAMPLE))
    import derive
    import well_sources

    ref, digest = well_sources.reference_module()
    ev = derive.Evidence()
    # The single production well has C reports on two bores. The later one
    # carries a different flag, so earliest effective date and flag must agree.
    well = "600000000100"
    tables = {
        "mv_boreholes_all": [[well, "G", "ST00BP00", "1/1/2005", "100", "COM"]],
        "mv_eor_operationcodes": [["C", "COMPLETION"]],
        "mv_eor_mainquery": [
            ["2", well, "C", "9/29/2026", "COM", "NO"],
            ["1", well[:-2] + "01", "C", "9/28/2026", "COM", "YES"],
            ["0", well, "D", "1/1/2000", "COM", "NO"],
        ],
        "mv_war_main": [
            ["1", well, "9/28/2026 11:30:00 PM"],
            ["2", well, "9/30/2026"],
            ["3", well, "10/1/2026"],
        ],
        "mv_apm_main": [
            ["1", well, "9/28/2026", "WORKOVER"],
            ["2", well, "9/29/2026", "WORKOVER"],
            ["3", well, "10/1/2026", "WORKOVER"],
            ["4", "bad-api", "9/30/2026", "WORKOVER"],
            ["5", "600000099900", "9/30/2026", "WORKOVER"],
        ],
        "mv_apm_suboperations": [["1", "ZONE"]],
        "mv_apm_main_prop": [["1", "Workover"]],
    }

    def read(directory, archive, member, columns, encoding):
        return pd.DataFrame(tables[member], columns=columns)

    monkeypatch.setattr(ref, "read_table", read)
    monkeypatch.setattr(well_sources, "reference_module", lambda: (ref, digest))
    return tables, well_sources, ev


def test_inventory_depth_edges_and_bore_history(source_tables):
    import pandas as pd

    tables, source, ev = source_tables
    bores = []
    for i, metres in enumerate((99.99, 100, 499.99, 500, 1499.99, 1500), 1):
        bores.append(
            [
                f"600000000{i}00",
                "G",
                "ST00BP00",
                "2/1/2005",
                str(metres / 0.3048),
                "COM",
            ]
        )
    bores.extend(
        [
            ["600000000101", "G", "ST01BP00", "12/31/2004", "9999", "CNL"],
            ["600000000201", "G", "ST00BP00", "bad-date", "9999", "CNL"],
            ["600000000301", "G", "ST01BP00", "", "bad-depth", "COM"],
        ]
    )
    tables["mv_boreholes_all"] = bores
    wells, _ = source.load_wells(None, ev.audit, ev.check)
    assert list(wells.band) == [
        "<100 m",
        "100–<500 m",
        "100–<500 m",
        "500–<1,500 m",
        "500–<1,500 m",
        "≥1,500 m",
    ]
    assert wells.first_spud.iloc[0] == pd.Timestamp("2004-12-31")
    assert list(wells.undated_original) == [False, True, False, False, False, False]


def test_inventory_api10_dispositions(source_tables):
    tables, source, ev = source_tables
    tables["mv_boreholes_all"] += [
        ["600000000101", "G", "ST01BP00", "bad-date", "-10", "COM"],
        ["600000000200", "G", "ST00BP00", "bad-date", "inf", "COM"],
        ["600000000201", "G", "ST01BP00", "", "bad-depth", "COM"],
        ["600000000300", "P", "ST00BP00", "", "100", "COM"],
        ["600000000400", "G", "ST00BP00", "", "100", "CNL"],
        ["600000000500", "", "ST00BP00", "", "100", "COM"],
        ["600000000600", "G", "ST00BP00", "", "100", "COM"],
        ["600000000601", "P", "ST01BP00", "", "100", "COM"],
        ["600000000700", "G", "ST00BP00", "1/1/2005", "50", "COM"],
        ["600000000701", "G", "ST01BP00", "", "", "COM"],
    ]
    wells, _ = source.load_wells(None, ev.audit, ev.check)
    assert wells.band.notna().sum() == 2
    inventory = {
        r["reason"]: r["rows"]
        for r in ev.records
        if r["stage"] == "Borehole inventory | assigned depth, API10"
    }
    assert inventory == {
        "input": 7,
        "retained": 2,
        "outside_gulf": 1,
        "unknown_region": 1,
        "ambiguous_region": 1,
        "cancelled_only": 1,
        "unresolved depth": 1,
    }
    quality = [r for r in ev.records if r["stage"].startswith("Borehole quality")]
    assert all(r["disposition"] != "dropped" for r in quality)
    assert all(r["rows"] == 3 for r in quality if r["disposition"] in ("read", "kept"))
    bad = {r["reason"]: r["rows"] for r in quality if r["disposition"] == "flagged"}
    assert bad["nonblank invalid depth on a bore"] == 2
    assert bad["nonblank unparseable spud on a bore"] == 2
    assert [
        r["rows"]
        for r in quality
        if r["reason"] == "blank on a bore, no malformed values"
    ] == [1, 1]


def test_first_events_exclude_completion_day_and_post_cutoff(source_tables):
    import pandas as pd

    tables, source, ev = source_tables
    late = "600000000200"
    tables["mv_boreholes_all"].append([late, "G", "ST00BP00", "1/1/2005", "100", "COM"])
    tables["mv_eor_mainquery"].append(["3", late, "C", "9/1/2026", "COM", "NO"])
    tables["mv_war_main"].append(["4", late, "10/2/2026"])
    tables["mv_apm_main"].append(["6", late, "10/2/2026", "WORKOVER"])
    wells, _ = source.load_wells(None, ev.audit, ev.check)
    well = wells.iloc[0]
    assert well.completion_date == pd.Timestamp("2026-09-28")
    assert well.completion_type == "Subsea"
    assert well.war_date == pd.Timestamp("2026-09-30")
    assert well.permit_date == pd.Timestamp("2026-09-29")
    assert pd.isna(wells.iloc[1].war_date)
    assert pd.isna(wells.iloc[1].permit_date)
    for stage in (
        "eWell WAR rows for observed work",
        "eWell APM approvals for classified well work",
    ):
        dropped = {r["reason"]: r["rows"] for r in ev.records if r["stage"] == stage}
        assert dropped["event on or before completion"] == 1
        assert dropped["event after production cutoff"] == 2
        assert dropped["retained"] == 1


def test_apm_series_separates_malformed_api(source_tables):
    _, source, ev = source_tables
    source.load_wells(None, ev.audit, ev.check)
    counts = {
        r["reason"]: r["rows"]
        for r in ev.records
        if r["stage"] == "eWell APM permits for series classification"
    }
    assert counts["outside eligible Gulf inventory"] == 1
    assert counts["invalid API"] == 1
    assert counts["input"] == 5
    assert counts["retained"] == 3


@pytest.fixture
def derivation(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))
    import derive

    return derive, derive.Evidence()


def test_hand_worked_cohort_examples(derivation):
    derive, _ = derivation
    derive.self_test()


def test_first_months_pre_window_vetoes(derivation):
    import pandas as pd

    derive, ev = derivation
    api = [
        "old spud",
        "old C",
        "undated original",
        "no spud",
        "old reported",
        "boundary",
        "blank report",
        "no timely evidence",
        "timely report",
    ]
    first = pd.Timestamp("2005-01-01")
    old = pd.Timestamp("2004-12-31")
    late = pd.Timestamp("2008-01-01")
    months = pd.DataFrame(
        {
            "api10": api,
            "positive": True,
            "month": first,
            "reported_first": [
                first,
                first,
                first,
                first,
                old,
                first,
                None,
                late,
                first,
            ],
        }
    )
    inventory = pd.DataFrame(
        {
            "api10": api,
            "band": derive.BANDS[0],
            "completion_type": "Subsea",
            "first_spud": [old, first, first, None, first, first, first, late, late],
            "undated_original": [s == "undated original" for s in api],
            "completion_date": [old if s == "old C" else first for s in api],
        }
    )
    starts = derive.first_months(months, inventory, ev.audit, ev.check)
    assert set(starts.loc[starts.start_supported, "api10"]) == {
        "boundary",
        "blank report",
        "timely report",
    }
    rejected = starts.loc[~starts.start_supported, "start_reason"]
    assert len(set(rejected)) == 6
    assert {
        r["reason"]: r["rows"]
        for r in ev.records
        if r["stage"] == "First positive month | API10 start evidence"
        and r["disposition"] == "dropped"
        and r["rows"]
    } == rejected.value_counts().to_dict()


def test_anniversary_horizon_censoring_and_ledger(derivation):
    import pandas as pd

    derive, ev = derivation
    starts = pd.DataFrame(
        {
            "start_supported": [True, True, True, False],
            "first_month": pd.to_datetime(
                ["2020-09-01", "2020-10-01", "2022-09-01", "2010-01-01"]
            ),
            "completion_date": pd.to_datetime(["2020-06-01", "2020-10-20", None, None]),
            "war_date": pd.to_datetime(["2020-08-01", "2022-09-30", None, None]),
            "permit_date": pd.to_datetime(["2022-09-30", None, None, None]),
            "band": derive.BANDS[0],
        }
    )
    frame = derive.intervention_curve(
        starts, pd.Timestamp("2022-09-01"), ev.audit, ev.check
    )
    all_war = frame.query(
        "band == 'All' and measure == 'Post-completion WAR'"
    ).set_index("age_year")
    assert all_war.eligible_wells.to_dict() == {0: 3, 1: 2, 2: 1}
    assert all_war.event_wells.tolist() == [1, 1, 1]
    assert all_war.completion_observed_wells.tolist() == [2, 2, 1]
    assert all_war.pre_origin_event_wells.tolist() == [1, 1, 1]
    approval = frame.query("band == 'All' and measure == 'Intervention approval'")
    assert approval.event_wells.tolist() == [0, 0, 1]
    cohort = {
        r["reason"]: r["rows"]
        for r in ev.records
        if r["stage"] == "Interventions | supported starts, API10"
    }
    assert cohort == {"input": 4, "retained": 3, "unsupported start": 1}
    horizon = {
        r["reason"]: r["rows"]
        for r in ev.records
        if r["stage"] == "Interventions | year 2 anniversary, API10"
    }
    assert horizon == {
        "input": 3,
        "retained": 1,
        "anniversary after production cutoff": 2,
    }


@pytest.mark.parametrize(
    "case", ["unknown snapshot", "empty snapshot", "duplicate archive"]
)
def test_verify_inputs_requires_complete_pin_inventory(
    derivation, tmp_path, monkeypatch, case
):
    derive, ev = derivation
    payload = b"test archive"
    name = "a.zip"
    pin = {
        "name": name,
        "snapshot": "current",
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    manifests = {"current": "manifest digest"}
    pins = {"sources": [pin], "manifest_sha256": manifests.copy()}
    if case == "unknown snapshot":
        pins["sources"].append(dict(pin, snapshot="forgotten", name="b.zip"))
    elif case == "empty snapshot":
        pins["sources"] = []
    else:
        pins["sources"].append(pin.copy())
    raw = json.dumps(pins).encode()
    (tmp_path / "source_pins.json").write_bytes(raw)
    (tmp_path / name).write_bytes(payload)
    monkeypatch.setattr(derive, "ROOT", tmp_path)
    monkeypatch.setattr(derive, "ORIGINAL_MANIFESTS", manifests)
    monkeypatch.setattr(derive, "PUBLIC_PINS_SHA256", hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError, match="(?i)pin|snapshot|duplicate"):
        derive.verify_inputs(tmp_path, ev.check)


def test_decline_and_lag_filter_ledgers(derivation):
    import pandas as pd

    derive, ev = derivation
    starts = pd.DataFrame(
        {
            "api10": ["valid", "gas", "recent", "old", "beyond", "undated"],
            "first_month": pd.to_datetime(
                [
                    "2005-02-01",
                    "2005-01-01",
                    "2021-01-01",
                    "2005-01-01",
                    "2026-01-01",
                    "2005-03-01",
                ]
            ),
            "completion_date": pd.to_datetime(
                [
                    "2005-01-31",
                    "2005-02-01",
                    "2021-01-01",
                    "2004-12-31",
                    "2026-01-01",
                    None,
                ]
            ),
            "start_supported": [True, True, True, False, True, False],
            "start_reason": "observed window covers start",
            "type_at_start": "Subsea",
            "band": derive.BANDS[0],
        }
    )
    months = pd.DataFrame(
        {
            "api10": ["valid"] * 5 + ["gas", "recent"],
            "month": pd.to_datetime(
                [
                    "2005-01-01",
                    "2005-02-01",
                    "2005-03-01",
                    "2010-01-01",
                    "2010-02-01",
                    "2005-01-01",
                    "2021-01-01",
                ]
            ),
            "band": derive.BANDS[0],
            "oil_bbl": [0, 40, 100, 20, 10, 0, 10],
            "oil_rate": [None, 4, 10, 2, 1, 0, 1],
        }
    )
    lag = derive.completion_lags(
        starts[["api10", "band", "completion_date"]], starts, ev.audit, ev.check
    )
    pooled = lag[lag.band.eq("All")].set_index("population")
    assert pooled.wells.to_dict() == {"signed": 3, "ordered": 2}
    assert pooled.median_months.to_dict() == {"signed": 0, "ordered": 0.5}
    decline = derive.decline_curve(months, starts, ev.audit, ev.check)
    curve = decline.query("band == 'All' and completion_type == 'All'").set_index(
        "age_month"
    )
    assert curve.baseline_wells.eq(1).all()
    assert curve.median_relative_rate.dropna().to_dict() == {1: 0.4, 2: 1.0, 60: 0.2}
    expected = {
        "Completion lag | completion window, API10": (6, 3),
        "Decline | start window, supported API10": (4, 2),
        "Decline | calendar ages 1–60, well-months": (6, 4),
        "Decline | baseline eligibility, well-months": (4, 3),
    }
    for stage, (read, kept) in expected.items():
        rows = [r for r in ev.records if r["stage"] == stage]
        assert [(r["disposition"], r["rows"]) for r in rows[:2]] == [
            ("read", read),
            ("kept", kept),
        ], stage


def assert_csv_share(row, field, numerator, denominator):
    count, eligible = int(row[numerator]), int(row[denominator])
    assert 0 <= count <= eligible, row
    if eligible:
        assert float(row[field]) == pytest.approx(count / eligible, rel=1e-14), row
    else:
        assert row[field] == "", row


def test_delivered_event_counts_shares_and_horizons():
    cohorts = defaultdict(list)
    for row in read_rows(OUTPUT / "interventions.csv"):
        assert_csv_share(row, "share", "event_wells", "eligible_wells")
        assert_csv_share(
            row,
            "share_among_completion_observed",
            "event_wells",
            "completion_observed_wells",
        )
        assert (
            0
            <= int(row["pre_origin_event_wells"])
            <= int(row["event_wells"])
            <= int(row["completion_observed_wells"])
            <= int(row["eligible_wells"])
        ), row
        cohorts[row["band"], row["measure"]].append(
            (int(row["age_year"]), int(row["eligible_wells"]))
        )
    assert set(cohorts) == {
        (band, measure)
        for band in BANDS | {"All"}
        for measure in ("Post-completion WAR", "Intervention approval")
    }
    for series in cohorts.values():
        ages, counts = zip(*sorted(series))
        assert ages == tuple(range(max(ages) + 1))
        assert counts == tuple(sorted(counts, reverse=True))


def test_delivered_article_shares():
    rows = read_rows(OUTPUT / "article_summary.csv")
    assert {row["band"] for row in rows} == BANDS | {"All"}
    for row in rows:
        assert_csv_share(
            row,
            "share_produced_in_or_after_c_month",
            "produced_in_or_after_c_month_wells",
            "cohort_completions",
        )
        for source in ("war", "permit"):
            assert_csv_share(
                row,
                f"{source}_by_cutoff_share",
                f"{source}_by_cutoff_wells",
                "supported_starts",
            )


def test_annual_volumes_and_months_roll_up_from_monthly_csv():
    groups = defaultdict(list)
    for row in read_rows(OUTPUT / "monthly_production.csv"):
        year = int(row["month"][:4])
        assert int(row["year"]) == year
        groups[year, row["band"]].append(row)
    annual = read_rows(OUTPUT / "annual_wells.csv")
    expected = {(yr, band) for yr in range(2005, 2027) for band in BANDS | {"All"}}
    assert set(groups) == expected
    assert {(int(r["year"]), r["band"]) for r in annual} == expected
    for row in annual:
        year, band = int(row["year"]), row["band"]
        monthly = groups[year, band]
        count = 9 if year == 2026 else 12
        assert int(row["months_reported"]) == len(monthly) == count, (year, band)
        assert {r["month"] for r in monthly} == {
            f"{year}-{m:02d}" for m in range(1, count + 1)
        }
        for field in ("oil_bbl", "gas_mcf"):
            assert int(row[field]) == sum(int(r[field]) for r in monthly), (row, field)


def test_delivered_decline_and_completion_lag_populations():
    for row in read_rows(OUTPUT / "decline.csv"):
        assert 0 <= int(row["wells"]) <= int(row["baseline_wells"]), row
        assert bool(row["median_relative_rate"]) == (int(row["wells"]) > 0), row

    rows = read_rows(OUTPUT / "completion_lag.csv")
    for band in BANDS | {"All"}:
        (ordered,) = select(rows, {"band": band, "population": "ordered"})
        (signed,) = select(rows, {"band": band, "population": "signed"})
        assert int(ordered["pre_completion_wells"]) == 0
        assert int(ordered["wells"]) + int(signed["pre_completion_wells"]) == int(
            signed["wells"]
        )
        for row in (signed, ordered):
            assert (
                float(row["p25_months"])
                <= float(row["median_months"])
                <= float(row["p75_months"])
            ), row


def test_each_published_check_passes():
    lines = (OUTPUT / "checks.txt").read_text(encoding="utf-8").splitlines()
    assert lines
    assert all(line.startswith("PASS  ") for line in lines), [
        line for line in lines if not line.startswith("PASS  ")
    ]


def test_readme_table_one_matches_headlines():
    text = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    lines = text.split("*Table 1.", 1)[0].splitlines()
    rows = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in lines
        if line.startswith("|")
    ][2:]
    assert [cells[0] for cells in rows] == list(TABLE_BANDS)
    headlines = json.loads((OUTPUT / "numbers.json").read_bytes())["headlines"]
    for label, *cells in rows:
        slug = TABLE_BANDS[label]
        lag = headlines[f"{slug}/lag/ordered"]["values"]
        rate = headlines[f"{slug}/decline/All/60"]["values"]
        war = headlines[f"{slug}/Post-completion WAR/5"]["values"]["share"]
        approval = headlines[f"{slug}/Intervention approval/5"]["values"]["share"]
        assert cells == [
            f"{headlines[f'{slug}/year/2005']['values']['producing_wells']:,}",
            f"{headlines[f'{slug}/year/2025']['values']['producing_wells']:,}",
            f"{lag['median_months']:g} ({lag['p25_months']:g} to {lag['p75_months']:g})",
            f"{100 * rate['median_relative_rate']:.1f} ({rate['wells']:,})",
            f"{100 * war:.1f}",
            f"{100 * approval:.1f}",
        ], label


def test_article_summary_audits_band_and_event_cohorts(derivation):
    import pandas as pd

    derive, ev = derivation
    band = derive.BANDS[0]
    inventory = pd.DataFrame(
        {
            "api10": ["a", "b", "c", "d"],
            "band": [band, None, band, band],
            "completion_date": pd.to_datetime(
                ["2005-01-31", "2005-01-31", None, "2004-01-01"]
            ),
            "war_date": pd.to_datetime(
                ["2005-02-01", "2005-02-02", None, "2004-01-05"]
            ),
            "permit_date": pd.to_datetime(["2006-01-10", None, None, None]),
        }
    )
    starts = inventory.iloc[[0, 3]].assign(
        first_month=pd.Timestamp("2005-01-01"), start_supported=[True, False]
    )
    months = starts.assign(positive=True, month=pd.Timestamp("2005-01-01"))
    period = pd.DataFrame(
        {
            "band": [*derive.BANDS, "All"],
            "distinct_producing_wells": [2, 0, 0, 0, 2],
            "producing_well_months": [2, 0, 0, 0, 2],
        }
    )
    args = (period, inventory, starts, months, pd.Timestamp("2005-12-01"))
    summary = derive.article_summary(*args, check=ev.check, audit=ev.audit).set_index(
        "band"
    )
    assert summary.loc[
        "All", ["cohort_completions", "war_by_cutoff_wells", "permit_by_cutoff_wells"]
    ].tolist() == [1, 1, 0]
    counts = {
        r["reason"]: r["rows"]
        for r in ev.records
        if r["stage"] == "Article summary | assigned band, completion cohort API10"
    }
    assert counts == {"input": 2, "retained": 1, "no assigned Gulf depth band": 1}
