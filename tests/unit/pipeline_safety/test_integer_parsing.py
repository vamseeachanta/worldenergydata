"""Issue 1295: count parsing must not silently round fractional source tokens.

Inputs are synthetic. Literal expected counts follow decimal place value,
not a pressure criterion or a historical incident workbook.
"""

from decimal import localcontext

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from worldenergydata.pipeline_safety.database.models import Base, PipelineIncident
from worldenergydata.pipeline_safety.importers import phmsa_importer as imp


@pytest.mark.parametrize("token", ["1e-400", "-1e-400", "1.0000000000000001"])
def test_fractional_count_token_is_not_rounded_to_integer(token):
    """Nonzero fractional parts remain invalid even if float() rounds them away."""
    with localcontext() as context:
        context.prec = 2
        with pytest.raises(ValueError, match="fractional"):
            imp._safe_int(token)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("9007199254740993", 9007199254740993),
        (9007199254740993, 9007199254740993),
        (np.int64(9007199254740993), 9007199254740993),
        ("2.0000000000000001e16", 20000000000000001),
        ("2.0", 2),
        (np.float64(2.0), 2),
        ("2e1", 20),
        ("0", 0),
        (" 3 ", 3),
        ("1_000", 1000),
        ("+1", 1),
        ("1.", 1),
        ("-0", 0),
    ],
)
def test_whole_count_is_preserved_exactly(value, expected):
    """Text and integer inputs must not pass through a lossy float round trip."""
    with localcontext() as context:
        context.prec = 2
        assert imp._safe_int(value) == expected


@pytest.mark.parametrize("value", [None, pd.NA, float("nan"), "", " "])
def test_missing_count_stays_unknown(value):
    assert imp._safe_int(value) is None


@pytest.mark.parametrize(
    "value", ["NaN", "sNaN", "Infinity", "bad", True, False, np.bool_(True)]
)
def test_invalid_count_raises_with_decimal_traps_disabled(value):
    with localcontext() as context:
        for signal in context.traps:
            context.traps[signal] = False
        with pytest.raises(ValueError):
            imp._safe_int(value)


def write_workbook(tmp_path, monkeypatch, era, rows):
    """Exercise the shipped reader and import loop against real XLSX cell types."""
    name = "synthetic.xlsx"
    pd.DataFrame(rows).to_excel(tmp_path / name, sheet_name="incidents", index=False)
    with (tmp_path / name).open("rb") as stream:
        workbook = load_workbook(stream)
        sheet = workbook["incidents"]
        headers = [cell.value for cell in sheet[1]]
        for row_number, row in enumerate(rows, 2):
            for field, value in row.items():
                if isinstance(value, str):
                    cell = sheet.cell(row_number, headers.index(field) + 1)
                    assert cell.data_type == "s"
                    assert cell.value == value
        workbook.close()
    monkeypatch.setattr(
        imp, "FILE_MANIFEST", [(name, "incidents", "gas_transmission", era)]
    )


@pytest.mark.parametrize("token", ["1e-400", "1.0000000000000001"])
@pytest.mark.parametrize(
    "era, field",
    [
        ("pre2004", "FAT"),
        ("pre2004", "INJ"),
        ("2004_2009", "FAT"),
        ("2004_2009", "INJ"),
        ("2010_present", "NUM_GP_FATALITIES"),
        ("2010_present", "NUM_GP_INJURIES"),
    ],
)
def test_excel_fractional_count_is_counted_as_error_before_persistence(
    tmp_path, monkeypatch, era, field, token
):
    """One invalid row is rejected; the exact integer and true zero are stored."""
    report_key = "REPORT_NUMBER" if era == "2010_present" else "RPTID"
    date_key = "LOCAL_DATETIME" if era == "2010_present" else "IDATE"
    fields = [*imp.FATALITY_COLUMNS, *imp.INJURY_COLUMNS]
    if era == "pre2004":
        fields = ["FAT", "INJ"]
    elif era == "2004_2009":
        fields += ["FAT", "INJ"]
    counts = dict.fromkeys(fields, "0")
    valid = {
        **counts,
        report_key: "valid",
        date_key: "2020-01-01",
        "NAME": "synthetic",
        field: "9007199254740993",
    }
    invalid = dict(valid, **{report_key: "invalid", field: token})
    write_workbook(tmp_path, monkeypatch, era, [invalid, valid])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        stats = imp.PHMSAImporter(session, str(tmp_path)).import_data()
        assert stats["total_records"] == 2
        assert stats["error_count"] == 1
        assert stats["imported_count"] == 1
        assert stats["skipped_count"] == 0
        assert "fractional" in stats["validation_errors"][0]
        saved = session.query(PipelineIncident).one()
        assert saved.report_number == "gas_transmission_valid"
        target = "fatalities" if "FAT" in field else "injuries"
        other = "injuries" if target == "fatalities" else "fatalities"
        assert getattr(saved, target) == 9007199254740993
        assert getattr(saved, other) == 0


def test_excel_numeric_report_id_keeps_existing_duplicate_key(tmp_path, monkeypatch):
    """Preserve the baseline .0 ID suffix until existing keys can be migrated."""
    valid = {
        "RPTID": 12345,
        "IDATE": "2020-01-01",
        "NAME": "synthetic",
        "FAT": "0",
        "INJ": "0",
    }
    write_workbook(tmp_path, monkeypatch, "pre2004", [valid, dict(valid, RPTID=None)])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            PipelineIncident(
                report_number="gas_transmission_12345.0",
                report_type="gas_transmission",
                operator_name="synthetic",
                incident_date=pd.Timestamp("2020-01-01").to_pydatetime(),
            )
        )
        session.commit()
        stats = imp.PHMSAImporter(session, str(tmp_path)).import_data()
        assert stats["skipped_count"] == 1
        assert stats["imported_count"] == 0
        assert stats["error_count"] == 1
        assert session.query(PipelineIncident).count() == 1


def test_excel_blank_mid_era_count_keeps_component_fallback(tmp_path, monkeypatch):
    """A blank direct count may use complete components; a fraction may not."""
    counts = dict.fromkeys([*imp.FATALITY_COLUMNS, *imp.INJURY_COLUMNS], "0")
    row = {
        **counts,
        "RPTID": "fallback",
        "IDATE": "2020-01-01",
        "NAME": "synthetic",
        "FAT": None,
        "INJ": None,
        "NUM_GP_FATALITIES": "2",
    }
    write_workbook(tmp_path, monkeypatch, "2004_2009", [row])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        stats = imp.PHMSAImporter(session, str(tmp_path)).import_data()
        assert stats["imported_count"] == 1
        assert stats["error_count"] == 0
        saved = session.query(PipelineIncident).one()
        assert saved.fatalities == 2
        assert saved.injuries == 0
