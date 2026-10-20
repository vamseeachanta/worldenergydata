"""Frozen inventory without workbook mutation, formula execution or core metadata."""

import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def inspect_workbook(path: Path) -> dict:
    # Optional dependency: importing comparison arithmetic never needs Excel.
    from openpyxl import load_workbook

    formulas = load_workbook(path, read_only=True, data_only=False)
    values = load_workbook(path, read_only=True, data_only=True)
    try:
        sheets = []
        for index, sheet in enumerate(formulas):
            cached = values.worksheets[index]
            formula_cells, uncached = [], []
            for row, value_row in zip(sheet, cached):
                for cell, value_cell in zip(row, value_row):
                    if cell.data_type == "f":
                        formula_cells.append(cell.coordinate)
                        if value_cell.value is None:
                            uncached.append(cell.coordinate)
            schema = {
                "title": sheet.title,
                "dimensions": [sheet.max_row, sheet.max_column],
                "headers": [str(cell.value) for cell in sheet[1]],
            }
            sheets.append(
                {
                    "sheet_id": f"sheet-{index:03d}",
                    "dimensions": schema["dimensions"],
                    "schema_sha256": hashlib.sha256(
                        canonical(schema).encode()
                    ).hexdigest(),
                    "formula_cells": formula_cells,
                    "uncached_formula_cells": uncached,
                }
            )
        return {"sha256": digest(path), "sheets": sheets}
    finally:
        formulas.close()
        values.close()


def read_frozen(path: Path, expected: dict) -> dict:
    if digest(path) != expected["sha256"]:
        raise ValueError(f"workbook digest drift: {path.name}")
    observed = inspect_workbook(path)
    if observed != expected:
        raise ValueError(f"workbook schema drift: {path.name}")
    return observed


def validate_crosswalk(used: set[str], rows: list[dict]) -> None:
    cells = [row["cell"] for row in rows]
    if len(cells) != len(set(cells)) or set(cells) != used:
        raise ValueError("crosswalk must cover every used cell exactly once")
    if any(
        not row.get("component")
        or row.get("disposition")
        not in {"included", "aggregate", "excluded", "unmapped"}
        for row in rows
    ):
        raise ValueError("crosswalk requires explicit component and disposition")
