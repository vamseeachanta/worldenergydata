"""V50 export contract; synthetic amounts are independent hand calculations."""

from contextlib import closing
from dataclasses import replace
from datetime import date, datetime, timezone

import pandas as pd
import pytest
from openpyxl import load_workbook

from worldenergydata.fdas.reports import v50_workbook


@pytest.fixture
def metadata():
    return v50_workbook.V50WorkbookMetadata(
        assumption_version="test-basis-unaccepted",
        git_commit="a" * 40,
        production_cutoff=date(2026, 4, 30),
        wti_deck_source="Synthetic test input; no market prices",
        npv_reference_convention="First material expenditure; annual period zero",
        generated_at=datetime(2026, 10, 19, tzinfo=timezone.utc),
    )


@pytest.fixture
def summary():
    """Hand calculation, USD: -100 at t=0, +121 at t=1, r=10%.

    Pre-tax NPV = -100 + 121/1.1 = 10. After-tax receipt assumed 110:
    after-tax NPV = -100 + 110/1.1 = 0. These are synthetic annual
    examples, not model assumptions; the exporter must not recalculate them.
    All other numeric cells use the synthetic input zero, not missing values.
    Schema source: repository FDAS_V30/financial_project_summary.xlsx,
    Project_Summary header row; additions follow issue 901 metadata scope.
    """
    row = dict.fromkeys(v50_workbook.LEGACY_SUMMARY_COLUMNS, 0)
    row.update(
        {
            "Project Name": "Synthetic project",
            "DEV SYSTEM": "Synthetic system",
            "FO Month": date(2026, 1, 1),
            "NPV USD": 10.0,
            "After-tax NPV USD": 0.0,
            "NPV Reference Date": date(2025, 1, 1),
        }
    )
    return pd.DataFrame([row])


def test_summary_and_metadata_roundtrip(tmp_path, summary, metadata):
    target = tmp_path / "summary.xlsx"
    original = summary.copy(deep=True)
    assert v50_workbook.write_v50_workbook(target, summary, metadata) == target
    with closing(load_workbook(target, data_only=True)) as book:
        assert book.sheetnames == ["Project_Summary", "Metadata"]
        rows = list(book["Project_Summary"].values)
        assert rows[0] == v50_workbook.SUMMARY_COLUMNS
        result = dict(zip(rows[0], rows[1]))
        assert result["NPV USD"] == 10.0
        assert result["After-tax NPV USD"] == 0.0  # Real zero, not missing.
        assert result["NPV Reference Date"] == datetime(2025, 1, 1)
        info = dict(book["Metadata"].values)
        assert info["assumption_version"] == metadata.assumption_version
        assert info["git_commit"] == metadata.git_commit
        assert info["npv_reference_convention"] == metadata.npv_reference_convention
        assert info["production_cutoff"] == "2026-04-30"
        assert info["wti_deck_source"] == metadata.wti_deck_source
        assert info["generated_at"] == "2026-10-19T00:00:00+00:00"
        assert info["canonical_acceptance_status"] == "NOT_EVALUATED"
        assert info["npv_units"] == "USD"
        assert info["pre_tax_npv_column"] == "NPV USD"
        assert info["after_tax_npv_column"] == "After-tax NPV USD"
        assert info["lineage"] == "V30 is lineage-only"
    pd.testing.assert_frame_equal(summary, original)


def test_schema_matches_frozen_workbook():
    """The committed lineage workbook is the independent schema reference."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    source = (
        root
        / "docs/modules/bsee/analysis/production/FDAS_V30/financial_project_summary.xlsx"
    )
    with closing(load_workbook(source, read_only=True)) as book:
        assert (
            tuple(next(book["Project_Summary"].values))
            == v50_workbook.LEGACY_SUMMARY_COLUMNS
        )


@pytest.mark.parametrize(
    "column", ["NPV USD", "After-tax NPV USD", "NPV Reference Date"]
)
def test_missing_required_column_rejected(tmp_path, summary, metadata, column):
    with pytest.raises(ValueError, match="Missing"):
        v50_workbook.write_v50_workbook(
            tmp_path / "bad.xlsx", summary.drop(columns=column), metadata
        )
    assert not (tmp_path / "bad.xlsx").exists()


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), None, "NOT_EVALUATED", True]
)
def test_missing_or_invalid_npv_rejected(tmp_path, summary, metadata, value):
    summary["After-tax NPV USD"] = value
    with pytest.raises(ValueError, match="finite numeric"):
        v50_workbook.write_v50_workbook(tmp_path / "bad.xlsx", summary, metadata)


@pytest.mark.parametrize(
    "field,value",
    [
        ("assumption_version", " "),
        ("wti_deck_source", ""),
        ("npv_reference_convention", ""),
        ("git_commit", "unversioned"),
        ("production_cutoff", "2026-04-30"),
        ("generated_at", datetime(2026, 10, 19)),
    ],
)
def test_invalid_provenance_rejected(tmp_path, summary, metadata, field, value):
    with pytest.raises(ValueError):
        v50_workbook.write_v50_workbook(
            tmp_path / "bad.xlsx", summary, replace(metadata, **{field: value})
        )


def test_duplicate_projects_rejected(tmp_path, summary, metadata):
    with pytest.raises(ValueError, match="unique"):
        v50_workbook.write_v50_workbook(
            tmp_path / "bad.xlsx", pd.concat([summary, summary]), metadata
        )


def test_empty_summary_rejected(tmp_path, summary, metadata):
    with pytest.raises(ValueError, match="empty"):
        v50_workbook.write_v50_workbook(
            tmp_path / "bad.xlsx", summary.iloc[:0], metadata
        )


def test_formula_like_text_is_stored_as_text(tmp_path, summary, metadata):
    summary.loc[0, "Project Name"] = "=1+1"
    target = tmp_path / "summary.xlsx"
    v50_workbook.write_v50_workbook(
        target, summary, replace(metadata, wti_deck_source="=1+1")
    )
    with closing(load_workbook(target)) as book:
        assert book["Project_Summary"]["A2"].data_type == "s"
        info = {row[0].value: row[1] for row in book["Metadata"]}
        assert info["wti_deck_source"].data_type == "s"


def test_existing_output_is_preserved(tmp_path, summary, metadata):
    target = tmp_path / "summary.xlsx"
    target.write_bytes(b"existing evidence")
    with pytest.raises(FileExistsError):
        v50_workbook.write_v50_workbook(target, summary, metadata)
    assert target.read_bytes() == b"existing evidence"
