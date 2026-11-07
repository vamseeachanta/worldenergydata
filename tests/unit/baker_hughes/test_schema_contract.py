"""Schema drift regressions using synthetic workbooks, not source qualification."""

from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.baker_hughes.loader import load_pivot_table, load_summary
from worldenergydata.baker_hughes.report import generate_report

OPTIONAL_COLUMNS = [
    "Country",
    "StateProvince",
    "County",
    "BasinName",
    "DrillFor",
    "Location",
    "Trajectory",
    "WellType",
]


@pytest.fixture
def pivot_frame():
    return pd.DataFrame(
        {
            "PublishDate": ["2026-01-01", "2026-01-08"],
            "Country": ["A", "B"],
            "StateProvince": ["X", "Y"],
            "County": ["C", "D"],
            "BasinName": ["M", "N"],
            "DrillFor": ["Oil", "Gas"],
            "Location": ["Land", "Land"],
            "Trajectory": ["Vertical", "Vertical"],
            "WellType": ["Development", "Development"],
            "WellDepth": [10, 20],
            "WaterDepth": ["", ""],
            "RigCount": [1, 2],
        }
    )


def workbook(tmp_path, frame, sheet):
    path = tmp_path / "synthetic.xlsx"
    frame.to_excel(path, sheet_name=sheet, index=False)
    return path


@pytest.mark.parametrize("column", ["PublishDate", "RigCount"])
def test_pivot_missing_required_column_is_schema_error(tmp_path, pivot_frame, column):
    path = workbook(tmp_path, pivot_frame.drop(columns=column), "Pivot Table")
    with pytest.raises(ValueError, match=rf"pivot schema.*missing.*{column}"):
        load_pivot_table(path, depth_unit="ft")


@pytest.mark.parametrize("column", OPTIONAL_COLUMNS)
def test_missing_optional_pivot_column_is_reported(tmp_path, pivot_frame, column):
    path = workbook(tmp_path, pivot_frame.drop(columns=column), "Pivot Table")
    result = load_pivot_table(path, depth_unit="ft")
    assert len(result) == 2
    assert result.attrs["schema_validation"] == {
        "status": "incomplete",
        "missing_columns": [column],
        "extra_columns": [],
    }
    report = generate_report(result, "pivot")
    assert report["completeness"]["status"] == "incomplete"
    assert report["completeness"]["schema"] == result.attrs["schema_validation"]


@pytest.mark.parametrize("column", ["Notes", "date", "rig_count", "well_depth_ft"])
def test_extra_pivot_columns_are_rejected(tmp_path, pivot_frame, column):
    pivot_frame[column] = "unexpected"
    path = workbook(tmp_path, pivot_frame, "Pivot Table")
    with pytest.raises(ValueError, match=rf"pivot schema.*unexpected.*{column}"):
        load_pivot_table(path, depth_unit="ft")


@pytest.mark.parametrize(
    "filters",
    [
        {"country": "absent"},
        {"basin": "absent"},
        {"country": "a"},
        {"country": "A", "basin": "N"},
    ],
)
def test_unmatched_exact_filters_are_errors(tmp_path, pivot_frame, filters):
    path = workbook(tmp_path, pivot_frame, "Pivot Table")
    with pytest.raises(ValueError, match=r"(country|basin).*matched no records"):
        load_pivot_table(path, depth_unit="ft", **filters)


@pytest.mark.parametrize(
    "column,field", [("Country", "country"), ("BasinName", "basin")]
)
def test_filter_on_absent_dimension_is_error(tmp_path, pivot_frame, column, field):
    path = workbook(tmp_path, pivot_frame.drop(columns=column), "Pivot Table")
    with pytest.raises(ValueError, match=rf"{field}.*missing.*column"):
        load_pivot_table(path, depth_unit="ft", **{field: "A"})


@pytest.mark.parametrize("state_header", ["State", "state"])
@pytest.mark.parametrize("date_header", ["2026-01-01", datetime(2026, 1, 1)])
def test_summary_selects_state_by_name_not_position(
    tmp_path, state_header, date_header
):
    frame = pd.DataFrame({date_header: [4, 5], state_header: ["X", "Y"]})
    result = load_summary(workbook(tmp_path, frame, "Rigs by State"))
    assert result.state.tolist() == ["X", "Y"]
    assert result.rig_count.tolist() == [4, 5]
    assert result.date.tolist() == [pd.Timestamp("2026-01-01")] * 2
    assert result.attrs["schema_validation"] == {
        "status": "complete",
        "missing_columns": [],
        "extra_columns": [],
    }


@pytest.mark.parametrize("identifier", ["Region", "Unnamed: 0", "STATE"])
def test_summary_rejects_unknown_identifier(tmp_path, identifier):
    frame = pd.DataFrame({identifier: ["X"], "2026-01-01": [1]})
    with pytest.raises(ValueError, match=r"summary schema.*State"):
        load_summary(workbook(tmp_path, frame, "Rigs by State"))


def test_summary_rejects_ambiguous_identifier(tmp_path):
    frame = pd.DataFrame({"State": ["X"], "state": ["Y"], "2026-01-01": [1]})
    with pytest.raises(ValueError, match=r"summary schema.*State"):
        load_summary(workbook(tmp_path, frame, "Rigs by State"))


@pytest.mark.parametrize(
    "header",
    [
        "Notes",
        "13/02/2026",
        "2026-02-30",
        "2026-1-1",
        46023,
        None,
        "NaT",
        "2026-01-01T00:00:00Z",
        datetime(2026, 1, 1, 12),
    ],
)
def test_summary_rejects_non_date_headers(tmp_path, header):
    frame = pd.DataFrame({"State": ["X"], header: [1]})
    with pytest.raises(ValueError, match=r"summary schema.*date"):
        load_summary(workbook(tmp_path, frame, "Rigs by State"))


def test_summary_extra_column_cannot_be_silently_dropped(tmp_path):
    frame = pd.DataFrame({"State": ["X"], "2026-01-01": [1], "Notes": ["metadata"]})
    with pytest.raises(ValueError, match=r"summary schema.*Notes"):
        load_summary(workbook(tmp_path, frame, "Rigs by State"))


def test_summary_requires_date_columns(tmp_path):
    frame = pd.DataFrame({"State": ["X"]})
    with pytest.raises(ValueError, match=r"summary schema.*date"):
        load_summary(workbook(tmp_path, frame, "Rigs by State"))


def test_summary_rejects_duplicate_calendar_dates(tmp_path):
    frame = pd.DataFrame({"State": ["X"], "2026-01-01": [1], datetime(2026, 1, 1): [2]})
    with pytest.raises(ValueError, match=r"summary schema.*duplicate.*date"):
        load_summary(workbook(tmp_path, frame, "Rigs by State"))


@pytest.mark.parametrize("kind", ["pivot", "summary"])
def test_empty_workbooks_keep_schema_and_report_incomplete(tmp_path, pivot_frame, kind):
    if kind == "pivot":
        frame, sheet = pivot_frame.iloc[:0], "Pivot Table"
        result = load_pivot_table(workbook(tmp_path, frame, sheet), depth_unit="ft")
    else:
        frame = pd.DataFrame(columns=["State", "2026-01-01"])
        result = load_summary(workbook(tmp_path, frame, "Rigs by State"))
    assert result.empty
    assert result.attrs["schema_validation"]["status"] == "complete"
    report = generate_report(result, kind)
    assert report["completeness"]["status"] == "incomplete"
    assert report["completeness"]["date_range"]["reason"] == "empty_input"


@pytest.mark.parametrize("kind", ["pivot", "summary"])
def test_headerless_workbooks_are_schema_errors(tmp_path, kind):
    sheet = "Pivot Table" if kind == "pivot" else "Rigs by State"
    path = workbook(tmp_path, pd.DataFrame(), sheet)
    with pytest.raises(ValueError, match=rf"{kind} schema"):
        (
            load_pivot_table(path, depth_unit="ft")
            if kind == "pivot"
            else load_summary(path)
        )


@pytest.mark.parametrize("all_missing", [False, True])
def test_missing_pivot_dates_reach_report_without_nat_bounds(
    tmp_path, pivot_frame, all_missing
):
    pivot_frame["PublishDate"] = ["", ""] if all_missing else ["2026-01-01", ""]
    result = load_pivot_table(
        workbook(tmp_path, pivot_frame, "Pivot Table"), depth_unit="ft"
    )
    report = generate_report(result, "pivot")
    coverage = report["completeness"]["date_range"]
    assert coverage["status"] == "incomplete"
    assert coverage["missing_count"] == (2 if all_missing else 1)
    assert report["completeness"]["status"] == "incomplete"
    if all_missing:
        assert "date_range" not in report
    else:
        assert report["date_range"] == {"min": "2026-01-01", "max": "2026-01-01"}


@pytest.mark.parametrize(
    "column,output",
    [("Country", "countries"), ("StateProvince", "states"), ("BasinName", "basins")],
)
def test_blank_excel_dimensions_are_incomplete(tmp_path, pivot_frame, column, output):
    pivot_frame.loc[1, column] = ""
    result = load_pivot_table(
        workbook(tmp_path, pivot_frame, "Pivot Table"), depth_unit="ft"
    )
    report = generate_report(result, "pivot")
    assert len(report[output]) == 1
    assert report["completeness"]["dimensions"][output]["missing_count"] == 1
    assert report["completeness"]["status"] == "incomplete"


def test_filtered_pivot_retains_schema_diagnostics(tmp_path, pivot_frame):
    frame = pivot_frame.drop(columns="County")
    path = workbook(tmp_path, frame, "Pivot Table")
    result = load_pivot_table(path, country="A", depth_unit="ft")
    assert result.country.tolist() == ["A"]
    report = generate_report(result, "pivot")
    assert report["completeness"]["schema"]["missing_columns"] == ["County"]
    assert report["completeness"]["status"] == "incomplete"


def test_pivot_preserves_literal_na_dimension(tmp_path, pivot_frame):
    pivot_frame["StateProvince"] = ["NA", "X"]
    result = load_pivot_table(
        workbook(tmp_path, pivot_frame, "Pivot Table"), depth_unit="ft"
    )
    report = generate_report(result, "pivot")
    assert report["states"] == ["NA", "X"]
    assert report["completeness"]["dimensions"]["states"]["status"] == "complete"


def test_filter_on_empty_pivot_is_no_match(tmp_path, pivot_frame):
    path = workbook(tmp_path, pivot_frame.iloc[:0], "Pivot Table")
    with pytest.raises(ValueError, match="country.*matched no records"):
        load_pivot_table(path, depth_unit="ft", country="A")


def test_filter_whitespace_is_exact(tmp_path, pivot_frame):
    path = workbook(tmp_path, pivot_frame, "Pivot Table")
    with pytest.raises(ValueError, match="country.*matched no records"):
        load_pivot_table(path, depth_unit="ft", country="A ")


def test_summary_preserves_literal_na_dimension(tmp_path):
    frame = pd.DataFrame({"State": ["NA", "X"], "2026-01-01": [1, 2]})
    result = load_summary(workbook(tmp_path, frame, "Rigs by State"))
    report = generate_report(result, "summary")
    assert report["states"] == ["NA", "X"]
    assert report["completeness"]["dimensions"]["states"]["status"] == "complete"


def test_summary_month_first_headers_are_explicit(tmp_path):
    """The existing summary fixture uses M/D/YYYY; January 2 precedes January 9."""
    frame = pd.DataFrame({"State": ["X"], "1/2/2026": [4], "2026-01-09": [5]})
    result = load_summary(workbook(tmp_path, frame, "Rigs by State"))
    assert result.date.tolist() == [
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-09"),
    ]
    assert result.rig_count.tolist() == [4, 5]
