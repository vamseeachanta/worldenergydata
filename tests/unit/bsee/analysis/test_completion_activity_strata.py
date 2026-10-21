"""Independent counting examples for the area and operator-class extension."""

import csv
import importlib
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pytest
from bs4 import BeautifulSoup

FIXTURES = Path("tests/fixtures/bsee/completion_intervention")
MODULE = "worldenergydata.bsee.analysis.completion_intervention"
analyse = importlib.import_module(MODULE + ".activity").analyse
report = importlib.import_module(MODULE + ".report")


def tables():
    return {
        p.stem: pd.read_csv(p, dtype=str).fillna("") for p in FIXTURES.glob("*.csv")
    }


def example():
    """Hand calculation: three EOR rows, two for API A and one without an API.

    The two A rows are W in 2010 and C in 2011, both in area AA. The last
    row has an invalid date and blank code/area. Each cell therefore contains
    one record; the A cells each contain one well, the missing-API cell none.
    Summing records gives three; summing cell well counts gives two, although
    there is only one distinct API overall. Counts must never imply additivity
    of distinct wells. All identifiers and class labels here are synthetic.
    """
    t = tables()
    eor = t["mv_eor_mainquery"].iloc[:3].copy()
    eor["SN_EOR"] = ["1", "2", "3"]
    eor["API_WELL_NUMBER"] = ["123456789012", "123456789012", ""]
    eor["EOR_OPERATION_CD"] = ["W", "C", ""]
    eor["BOREHOLE_STAT_DT"] = ["1/1/2010", "1/1/2011", "invalid"]
    eor["BOTM_AREA_CODE"] = ["AA", "AA", ""]
    t["mv_eor_mainquery"] = eor
    t["mv_eor_completions"] = t["mv_eor_completions"].iloc[:0].copy()
    return t


def classification():
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": ["123456789012"],
            "OPERATOR_CLASS": ["class A"],
            "SOURCE": ["Synthetic classification supplied for the hand example."],
        }
    )


def test_area_counts_and_unknowns_without_operator_input():
    """The three cells and unknown counts follow example() by enumeration."""
    result = analyse(example())
    assert result["activity_strata"]["eor"] == [
        {
            "year": "2010",
            "area": "AA",
            "operator_class": "unknown",
            "code": "W",
            "records": 1,
            "wells": 1,
        },
        {
            "year": "2011",
            "area": "AA",
            "operator_class": "unknown",
            "code": "C",
            "records": 1,
            "wells": 1,
        },
        {
            "year": "unknown",
            "area": "unknown",
            "operator_class": "unknown",
            "code": "unknown",
            "records": 1,
            "wells": 0,
        },
    ]
    assert result["operator_classification"]["status"] == "NOT_EVALUATED"
    assert result["quality"]["eor_unknown_area"] == 1
    assert result["quality"]["eor_unknown_operator_class"] == 3


def test_supplied_classification_and_provenance():
    """API A maps to class A for two rows; the missing API stays unknown."""
    result = analyse(example(), operator_classes=classification())
    rows = result["activity_strata"]["eor"]
    assert [r["operator_class"] for r in rows] == ["class A", "class A", "unknown"]
    assert result["quality"]["eor_unknown_operator_class"] == 1
    assert result["operator_classification"] == {
        "status": "SUPPLIED",
        "sources": classification()["SOURCE"].tolist(),
        "basis": "Caller-supplied API12 snapshot classes; historical attribution is not established.",
    }


@pytest.mark.parametrize("dataset", ["war", "eor", "completion"])
def test_all_strata_reconcile_and_do_not_mutate_inputs(dataset):
    """A partition counts every row once; totals equal the existing summary."""
    t = tables()
    original = {k: v.copy(deep=True) for k, v in t.items()}
    result = analyse(t)
    rows = result["activity_strata"][dataset]
    assert sum(r["records"] for r in rows) == result["summary"][dataset + "_records"]
    assert all(r["wells"] <= r["records"] for r in rows)
    for key in t:
        pd.testing.assert_frame_equal(t[key], original[key])


def test_completion_area_uses_only_unambiguous_borehole_metadata():
    """Two completion rows: A has areas AA and BB, B only CC.

    Hand result: one unknown-area row and one CC row, each one record/well.
    Duplicate CC metadata contributes no additional completion records.
    """
    t = tables()
    t["mv_boreholes_all"] = pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "123456789012",
                "123456789012",
                "123456789013",
                "123456789013",
            ],
            "BOTM_AREA_CODE": ["AA", "BB", "CC", "CC"],
        }
    )
    comp = t["mv_api_wellcomps_all"].iloc[:2].copy()
    comp["API_WELL_NUMBER"] = ["123456789012", "123456789013"]
    t["mv_api_wellcomps_all"] = comp
    result = analyse(t)
    assert result["quality"]["conflicting_borehole_area_apis"] == 1
    assert result["quality"]["completion_unknown_area"] == 1
    assert sorted(r["area"] for r in result["activity_strata"]["completion"]) == [
        "CC",
        "unknown",
    ]


def test_missing_area_columns_remain_unknown():
    """Removing every area field puts every source row in unknown area."""
    t = {
        k: v.drop(columns="BOTM_AREA_CODE", errors="ignore")
        for k, v in tables().items()
    }
    result = analyse(t)
    for dataset in ["war", "eor", "completion"]:
        assert (
            result["quality"][dataset + "_unknown_area"]
            == result["summary"][dataset + "_records"]
        )


@pytest.mark.parametrize(
    "column,value",
    [("API_WELL_NUMBER", "invalid"), ("OPERATOR_CLASS", ""), ("SOURCE", " ")],
)
def test_invalid_classification_is_rejected(column, value):
    c = classification()
    c.loc[0, column] = value
    with pytest.raises(ValueError, match="classification"):
        analyse(example(), operator_classes=c)


def test_conflicting_classification_rejected_and_exact_duplicates_safe():
    """Two identical mapping rows still assign one class to each record."""
    c = pd.concat([classification(), classification()], ignore_index=True)
    result = analyse(example(), operator_classes=c)
    assert sum(r["records"] for r in result["activity_strata"]["eor"]) == 3
    c.loc[1, "OPERATOR_CLASS"] = "class B"
    with pytest.raises(ValueError, match="conflicting.*classification"):
        analyse(example(), operator_classes=c)


def test_classification_normalisation_and_evidence_order():
    """Two sources for A's one class assign its two EOR records only once.

    A float-form API and an integer-form API identify the same synthetic well;
    expected evidence is the sorted two-element source set, independent of
    input order. Unmatched evidence does not create additional source records.
    """
    c = pd.concat([classification(), classification()], ignore_index=True)
    c.loc[0, "API_WELL_NUMBER"] = "123456789012.0"
    c.loc[0, "SOURCE"] = "Second synthetic source."
    first = analyse(example(), operator_classes=c)
    second = analyse(example(), operator_classes=c.iloc[::-1])
    assert first == second
    assert first["operator_classification"]["sources"] == sorted(c["SOURCE"])
    assert [r["records"] for r in first["activity_strata"]["eor"]] == [1, 1, 1]


def test_classification_missing_columns_rejected():
    with pytest.raises(ValueError, match="classification"):
        analyse(example(), operator_classes=classification().drop(columns="SOURCE"))


def test_empty_sources_and_empty_classification():
    """No source rows gives no strata and zero missing records, not a rate."""
    t = {k: v.iloc[:0].copy() for k, v in tables().items()}
    result = analyse(t, operator_classes=classification().iloc[:0])
    assert result["activity_strata"] == {"war": [], "eor": [], "completion": []}
    assert result["operator_classification"]["status"] == "NOT_EVALUATED"
    assert result["quality"]["completion_unknown_area"] == 0


def test_report_and_products_include_strata(tmp_path):
    """Stored counts equal the three hand-enumerated EOR records in example()."""
    result = analyse(example(), operator_classes=classification())
    revision = {
        "revision": "1",
        "history": [
            {
                "revision": "1",
                "date": "2026-10-19",
                "change": "Synthetic counting example.",
            }
        ],
    }
    page = report.render_report(result, revision)
    assert 'id="activity-strata"' in page
    assert "Area and operator-class record counts" in page
    assert "Synthetic classification supplied for the hand example." in page
    assert "Distinct well counts are not additive across cells" in page
    section = BeautifulSoup(page, "html.parser").find(id="activity-strata")
    assert len(section.select('svg[aria-label$="supplied operator class."]')) == 3
    report.write_products(result, revision, tmp_path)
    compact = json.loads((tmp_path / "results.json").read_text())
    assert compact["activity_strata"] == result["activity_strata"]
    assert compact["operator_classification"] == result["operator_classification"]


def test_delivered_chart_matches_fixture_counts():
    """The delivered chart section must reproduce the pinned fixture partition."""
    result = analyse(tables())
    revision = {
        "revision": "1",
        "history": [{"revision": "1", "date": "2026-10-19", "change": "Example."}],
    }
    expected = report.render_report(result, revision)
    delivered = Path(
        "docs/modules/bsee/analysis/completion_intervention/area_operator_example.html"
    ).read_text()
    marker = '<section id="activity-strata">'
    assert delivered.split(marker)[1].split("</section>")[0] == (
        expected.split(marker)[1].split("</section>")[0]
    )


def test_operator_labels_and_sources_are_escaped():
    """Source and class text are evidence strings, never executable markup."""
    c = classification()
    c.loc[0, "OPERATOR_CLASS"] = '<img src="outside">'
    c.loc[0, "SOURCE"] = "<script>outside</script>"
    result = analyse(example(), operator_classes=c)
    revision = {
        "revision": "1",
        "history": [{"revision": "1", "date": "2026-10-19", "change": "Example."}],
    }
    page = report.render_report(result, revision)
    assert "<img " not in page and "<script>" not in page
    assert "&lt;img" in page and "&lt;script&gt;" in page


def fixture_area_tallies():
    """Count CSV records directly; API sets resolve completion areas only."""
    raw = {}
    for path in FIXTURES.glob("*.csv"):
        with path.open(newline="", encoding="utf-8") as stream:
            raw[path.stem] = list(csv.DictReader(stream))
    areas = defaultdict(set)
    for row in raw["mv_boreholes_all"]:
        api = row["API_WELL_NUMBER"].strip().removesuffix(".0")
        area = row["BOTM_AREA_CODE"].strip()
        if len(api) == 12 and api.isdigit() and area:
            areas[api].add(area)
    counts = {}
    for source, member in [
        ("war", "mv_war_main"),
        ("eor", "mv_eor_mainquery"),
        ("completion", "mv_api_wellcomps_all"),
    ]:
        tally = Counter()
        for row in raw[member]:
            if source == "completion":
                api = row["API_WELL_NUMBER"].strip().removesuffix(".0")
                choices = areas[api]
                area = next(iter(choices)) if len(choices) == 1 else "unknown"
            else:
                area = row["BOTM_AREA_CODE"].strip() or "unknown"
            tally[area] += 1
        counts[source] = tally
    return counts


@pytest.mark.parametrize("source", ["war", "eor", "completion"])
def test_analysis_example_and_note_match_independent_csv_tally(source):
    """A dropped or misassigned area row must fail every published comparison."""
    expected = fixture_area_tallies()[source]
    rows = analyse(tables())["activity_strata"][source]
    actual = Counter()
    for row in rows:
        actual[row["area"]] += row["records"]
    assert actual == expected
    directory = Path("docs/modules/bsee/analysis/completion_intervention")
    page = BeautifulSoup(
        (directory / "area_operator_example.html").read_text(), "html.parser"
    )
    section = page.find(id="activity-strata")
    heading = section.find("h3", string=source.upper())
    labels = [text.get_text() for text in heading.find_next("svg").find_all("text")]
    assert dict(zip(labels[::2], map(int, labels[1::2]))) == expected
    delivered = Counter()
    for row in heading.find_next("table").select("tbody tr"):
        cells = [cell.get_text() for cell in row.find_all("td")]
        delivered[cells[1]] += int(cells[4])
    assert delivered == expected
    note = (directory / "area_operator_note.md").read_text()
    line = next(
        line for line in note.splitlines() if line.lower().startswith(f"| {source} |")
    )
    assert [int(value.strip()) for value in line.split("|")[2:5]] == [
        sum(expected.values()),
        expected["unknown"],
        sum(expected.values()),
    ]


@pytest.mark.parametrize("empty_mapping", [False, True])
def test_unevaluated_classification_has_no_operator_chart(empty_mapping):
    """Missing evidence must not present an unknown bar as an evaluated class."""
    mapping = classification().iloc[:0] if empty_mapping else None
    result = analyse(example(), operator_classes=mapping)
    basis = result["operator_classification"]["basis"].lower()
    assert "no operator-class mapping supplied" in basis
    assert "caller-supplied" not in basis
    page = report.render_report(
        result,
        {"revision": "1", "history": [{"revision": "1", "date": "2026-10-19"}]},
    )
    section = BeautifulSoup(page, "html.parser").find(id="activity-strata")
    assert not section.select('svg[aria-label$="supplied operator class."]')
    assert section.select('svg[aria-label$="bottom area code."]')
    assert section.find("table") is not None


def test_catalogue_distinguishes_archive_and_member_digests():
    """An archive digest must be labelled separately from its member digest."""
    result = analyse(example())
    result["catalogue"] = [
        {
            "member": "synthetic.csv",
            "url": "https://www.data.bsee.gov/",
            "archive_sha256": "a" * 64,
            "member_sha256": "b" * 64,
        }
    ]
    page = report.render_report(
        result,
        {"revision": "1", "history": [{"revision": "1", "date": "2026-10-19"}]},
    )
    details = BeautifulSoup(page, "html.parser").find(id="catalogue").details
    assert "Archive SHA-256: " + "a" * 64 in details.get_text()
    assert "Member SHA-256: " + "b" * 64 in details.get_text()


def test_fixture_builder_reproduces_example_and_catalogue(tmp_path):
    """The committed command must reproduce every byte and identify its inputs."""
    command = [sys.executable, "scripts/reporting/build_completion_activity_example.py"]
    output = tmp_path / "example.html"
    for _ in range(2):
        run = subprocess.run(
            [*command, "--output", str(output)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert run.returncode == 0, run.stderr
        delivered = Path(
            "docs/modules/bsee/analysis/completion_intervention/area_operator_example.html"
        )
        assert output.read_bytes() == delivered.read_bytes()
    page = BeautifulSoup(output.read_text(), "html.parser")
    assert "fixture example" in page.title.get_text().lower()
    assert "fixture example" in page.h1.get_text().lower()
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    details = page.find(id="catalogue").find_all("details")
    assert len(details) == len(manifest["files"])
    for detail in details:
        item = manifest["files"][detail.summary.get_text()]
        assert "Archive SHA-256: " + item["archive_sha256"] in detail.get_text()
        assert "Member SHA-256: not established" in detail.get_text()
        assert item["sha256"] in detail.find_previous("table").get_text()


def test_fixture_builder_rejects_changed_projection(tmp_path):
    """A tampered fixture must fail before creating an example."""
    fixtures = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixtures)
    projection = fixtures / "mv_war_main.csv"
    projection.write_bytes(projection.read_bytes() + b"\n")
    output = tmp_path / "example.html"
    run = subprocess.run(
        [
            sys.executable,
            "scripts/reporting/build_completion_activity_example.py",
            "--fixtures",
            str(fixtures),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode != 0
    assert "fixture digest mismatch" in run.stderr
    assert not output.exists()
