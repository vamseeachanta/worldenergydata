"""Refresh orchestrator .xlsx member support (#847).

The BOEM FieldReserves annual tables ship as an .xlsx workbook inside the
ZIP (unlike the delimited BSEE raw files). The orchestrator must extract
each sheet to its own raw bin (``<stem-slug>__<sheet-slug>.bin``,
``header=None`` grid — downstream parsers own header detection), while the
delimited .txt/.csv path stays byte-for-byte unchanged.
"""

import io
import pickle
import sys
import zipfile
from pathlib import Path

import pandas as pd

_scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(_scripts_dir))
from refresh_bsee_all import BSEERefreshOrchestrator, _slug

from worldenergydata.bsee.data.refresh.url_registry import DatasetSpec


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _xlsx_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False, header=False)
    return buf.getvalue()


def test_slug_sanitizes_boem_names():
    assert _slug("2023 Tables xlsx Public ") == "2023_tables_xlsx_public"
    assert _slug("2023 - Table 4 Final") == "2023_table_4_final"
    assert _slug("HIST-2023") == "hist_2023"


def test_xlsx_member_extracts_one_bin_per_sheet(tmp_path):
    xlsx = _xlsx_bytes(
        {
            "2023 - Table 4 Final": pd.DataFrame([["Rank", "x"], [1, "MC807"]]),
            "HIST-2023": pd.DataFrame([["a"], ["b"]]),
        }
    )
    zip_bytes = _zip_bytes({"2023 Tables xlsx Public .xlsx": xlsx})
    spec = DatasetSpec("fieldreserves_tables", "https://example/x.zip", [])

    orch = BSEERefreshOrchestrator(project_root=tmp_path)
    result = orch._process_zip_to_bins(zip_bytes, spec)

    assert result.status == "success"
    out_dir = tmp_path / "data/modules/bsee/bin/fieldreserves_tables"
    t4 = out_dir / "2023_tables_xlsx_public__2023_table_4_final.bin"
    hist = out_dir / "2023_tables_xlsx_public__hist_2023.bin"
    assert t4.exists() and hist.exists()
    df = pickle.loads(t4.read_bytes())
    # header=None raw grid: first row is data, not column names
    assert list(df.iloc[0]) == ["Rank", "x"]
    assert result.bins_written == 2


def test_txt_member_path_unchanged_alongside_xlsx(tmp_path):
    zip_bytes = _zip_bytes(
        {
            "mastdatadelimit.txt": b'"AC","   24","AC024","G10379"\n"AC","   25","AC025","G10380"\n',
            "notes.xlsx": _xlsx_bytes({"Sheet1": pd.DataFrame([[1]])}),
        }
    )
    spec = DatasetSpec("fieldreserves_master", "https://example/y.zip", [])

    orch = BSEERefreshOrchestrator(project_root=tmp_path)
    result = orch._process_zip_to_bins(zip_bytes, spec)

    assert result.status == "success"
    out_dir = tmp_path / "data/modules/bsee/bin/fieldreserves_master"
    assert (out_dir / "mastdatadelimit.bin").exists()
    assert (out_dir / "notes__sheet1.bin").exists()
    assert result.bins_written == 2
