"""Brazil ANP field metadata to FieldConcept mapping."""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Optional

import pandas as pd

from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    to_field_concept,
    year_from,
)


_BRAZIL_MAPPING = FieldMetaMapping(
    {
        "name": FieldMapEntry("field_name"),
        "operator": FieldMapEntry("operator"),
        "region": FieldMapEntry("region"),
        "water_depth_m": FieldMapEntry("water_depth_m"),
        "num_wells": FieldMapEntry("well_count"),
        "year_first_oil": FieldMapEntry("first_oil_date", year_from),
        "data_source": FieldMapEntry("source"),
    }
)


def build_brazil_field_meta(
    *,
    fields_df: pd.DataFrame,
    platforms_df: pd.DataFrame,
    wells_df: pd.DataFrame,
    field_name: str,
) -> Dict[str, Any]:
    """Reduce official ANP field/platform/well CSV rows to one field meta dict."""
    field_row = _single_field_row(fields_df, field_name)
    platform_rows = _matching_platforms(platforms_df, field_name)
    well_rows = _matching_wells(wells_df, field_name)

    return {
        "field_name": str(field_row.get("CAMPO", field_name)).strip(),
        "operator": _none_if_blank(field_row.get("OPERADOR")),
        "basin": _none_if_blank(field_row.get("BACIA")),
        "environment": _environment(field_row, well_rows),
        "region": "brazil",
        "water_depth_m": _platform_water_depth(platform_rows),
        "well_count": _well_count(well_rows),
        "first_oil_date": _none_if_blank(field_row.get("DATA_INICIO_PRODUCAO")),
        "source": "anp_fase_desenvolvimento_producao",
    }


def build_brazil_field_concept(field_meta: Dict[str, Any]):
    """Build a sparse Brazil FieldConcept from reduced ANP metadata."""
    meta = dict(field_meta)
    meta["region"] = "brazil"
    meta.setdefault("source", "anp_fase_desenvolvimento_producao")
    return to_field_concept(meta, _BRAZIL_MAPPING)


def brazil_field_meta_mapping() -> FieldMetaMapping:
    """Return the Brazil ANP FieldConcept mapping."""
    return _BRAZIL_MAPPING


def _single_field_row(fields_df: pd.DataFrame, field_name: str) -> pd.Series:
    if fields_df is None or fields_df.empty:
        raise ValueError("fields_df is empty")
    mask = fields_df["CAMPO"].map(_norm) == _norm(field_name)
    rows = fields_df[mask]
    if rows.empty:
        raise ValueError(f"Brazil ANP field not found: {field_name}")
    return rows.iloc[0]


def _matching_platforms(platforms_df: pd.DataFrame, field_name: str) -> pd.DataFrame:
    if platforms_df is None or platforms_df.empty or "[CAMPOS]" not in platforms_df:
        return pd.DataFrame()
    needle = _norm(field_name)
    mask = platforms_df["[CAMPOS]"].fillna("").map(
        lambda value: needle in [_norm(part) for part in str(value).split(";")]
    )
    return platforms_df[mask]


def _matching_wells(wells_df: pd.DataFrame, field_name: str) -> pd.DataFrame:
    if wells_df is None or wells_df.empty:
        return pd.DataFrame()
    field_col = "Campo" if "Campo" in wells_df.columns else "CAMPO"
    if field_col not in wells_df.columns:
        return pd.DataFrame()
    return wells_df[wells_df[field_col].map(_norm) == _norm(field_name)]


def _platform_water_depth(platforms: pd.DataFrame) -> Optional[float]:
    col = "[LÂMINA D'ÁGUA (m)]"
    if platforms.empty or col not in platforms.columns:
        return None
    values = [_parse_brazil_number(value) for value in platforms[col]]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return float(sum(values) / len(values))


def _well_count(wells: pd.DataFrame) -> int:
    if wells.empty:
        return 0
    for col in ("Nome_poço_anp", "Nome Poço ANP", "POCO", "Poço"):
        if col in wells.columns:
            return int(wells[col].dropna().astype(str).str.strip().nunique())
    return int(len(wells))


def _environment(field_row: pd.Series, wells: pd.DataFrame) -> Optional[str]:
    value = _none_if_blank(field_row.get("AMBIENTE"))
    if value is not None:
        return value
    if not wells.empty and "Ambiente" in wells.columns:
        return _none_if_blank(wells["Ambiente"].dropna().iloc[0])
    return None


def _parse_brazil_number(value: Any) -> Optional[float]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text.replace(".", "").replace(",", "."))


def _none_if_blank(value: Any) -> Optional[Any]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return ascii_text.strip().casefold()
