"""Normalization helpers for Colorado ECMC source parsing (#745)."""

from __future__ import annotations

import pandas as pd


def month_end(year: pd.Series, month: pd.Series) -> pd.Series:
    years = pd.to_numeric(year, errors="coerce").astype("Int64")
    months = pd.to_numeric(month, errors="coerce").astype("Int64")
    text = years.astype("string") + "-" + months.astype("string").str.zfill(2) + "-01"
    return pd.to_datetime(text, errors="coerce") + pd.offsets.MonthEnd(0)


def clean_int(value: object, width: int) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text:
        return None
    try:
        return str(int(text)).zfill(width)
    except ValueError:
        return None


def clean_identifier(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text if text else None


def clean_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def clean_api12(value: object) -> str | None:
    text = clean_identifier(value)
    if not text:
        return None
    digits = "".join(char for char in text if char.isdigit())
    return digits.zfill(12) if digits else None


def clean_api10(value: object) -> str | None:
    api12 = clean_api12(value)
    return api12[:10] if api12 else None


def validate_columns(
    frame: pd.DataFrame, required: set[str], source_name: str, source_type: str
) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            f"{source_name} missing required ECMC {source_type} columns: "
            + ", ".join(missing)
        )
