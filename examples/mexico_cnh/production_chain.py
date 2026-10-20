"""Synthetic Mexico chain worked example; no network or browser is used.

Units/layout: SENER, January 2025 field-production workbook, units/header rows,
https://hidrocarburos.energia.gob.mx/estadisticas/.
Synthetic inputs: February 2024 oil=2 Mbd, gas excluding nitrogen=3 MMpcd,
condensate=1 Mbd. Independent answers: 2*1000*29=58000 bbl petroleum,
3*1000*29=87000 Mcf gas, 1*1000*29=29000 bbl condensate. Water is unknown.
The factor 1000 follows the source units; 29 is Gregorian February 2024.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from worldenergydata.mexico_cnh.bulk import load_production_workbook
from worldenergydata.mexico_cnh.chain import run_chain


def _write_synthetic_workbook(path: Path) -> None:
    book = Workbook()
    liquid = book.active
    liquid.title = "Aceite y condensado"
    liquid.append(
        [
            "Fecha",
            "Cuenca",
            "Ubicación",
            "Campo",
            "Operador",
            "Líquidos (Mbd)",
            "Petróleo (Mbd)",
            "Condensado (Mbd)",
        ]
    )
    identity = [datetime(2024, 2, 1), "Example basin", "Terrestre", "EXAMPLE", "OP"]
    liquid.append([*identity, 3, 2, 1])
    gas = book.create_sheet("Gas Natural")
    gas.append(
        [
            "Fecha",
            "Cuenca",
            "Ubicación",
            "Campo",
            "Operador",
            "Gas natural sin nitrógeno (MMpcd)",
            "Nitrógeno (MMpcd)",
        ]
    )
    gas.append([*identity, 3, None])
    book.save(path)
    book.close()


def worked_example(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "synthetic-production.xlsx"
    _write_synthetic_workbook(path)
    observed = load_production_workbook(path)
    answer = {
        name: float(observed.production.iloc[0][name])
        for name in ("oil_bbl", "gas_mcf", "condensate_bbl")
    }
    expected = {"oil_bbl": 58000, "gas_mcf": 87000, "condensate_bbl": 29000}
    if answer != expected:
        raise AssertionError("monthly volumes differ from independent hand calculation")
    report = run_chain(observed)
    html = report.html.replace(
        "<h1>Mexico production chain analysis</h1>",
        "<h1>Synthetic Mexico production chain example</h1>",
    )
    (directory / "analysis.html").write_text(html, encoding="utf-8")
    if "NOT_EVALUATED" not in (directory / "analysis.html").read_text(encoding="utf-8"):
        raise AssertionError("readback must expose the missing economic inputs")
    return answer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(worked_example(args.output_dir), indent=2))
