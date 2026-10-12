"""Shared synthetic archive builders for offline family tests."""

import io
import zipfile
from pathlib import Path

import pandas as pd

FIXTURES = Path(__file__).parents[2] / "fixtures/bsee/fieldreserves"


def archive(name: str, body: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, body)
    return buf.getvalue()


def history_archive() -> bytes:
    df = pd.read_csv(FIXTURES / "synthetic_history.csv")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as x:
        df.to_excel(x, sheet_name="2023 OFFLDHIST", index=False)
    return archive("2023 HIST/2023 OFFLDHIST.xlsx", output.getvalue())
