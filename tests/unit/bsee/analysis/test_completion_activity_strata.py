"""Independent counting examples for the area and operator-class extension."""

import importlib
import json
from pathlib import Path

import pandas as pd
import pytest

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
