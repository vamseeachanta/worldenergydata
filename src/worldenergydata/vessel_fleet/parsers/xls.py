"""Transposed XLS fleet data parser.

Handles the historical rig fleet XLS format where rigs are in columns
and fields are in rows. Transposes, maps field labels to schema columns,
and parses mixed-format values.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from worldenergydata.vessel_fleet.parsers.numeric import (
    parse_bool,
    parse_dimension_pair,
    parse_int_from_label,
    parse_numeric,
)

logger = logging.getLogger(__name__)

# XLS vessel type code -> standardised value
_VESSEL_TYPE_MAP: dict[str, str] = {
    "SS": "semi_submersible",
    "DS": "drillship",
}

# XLS row label -> DrillingRigSchema field name.
# Only maps fields we want to extract; unmapped rows are skipped.
_FIELD_MAP: dict[str, str] = {
    # Identification
    "VESSEL TYPE": "_VESSEL_TYPE_RAW",
    "VESSEL DESIGN": "RIG_DESIGN",
    "CONSTRUCTION DATE (yr.)": "_YEAR_BUILT_RAW",
    "UPGRADE DATE (yr.)": "_YEAR_UPGRADED_RAW",
    "CLASSIFICATION (society)": "CLASSIFICATION_SOCIETY",
    # Ratings
    "MAXIMUM WATER DEPTH EQUIPPED (ft.)": "MAX_WATER_DEPTH_FT",
    "MAXIMUM WATER DEPTH RATING (ft.)": "WATER_DEPTH_RATING_FT",
    "MAXIMUM DRILLING DEPTH (ft.)": "DRILLING_DEPTH_RATING_FT",
    "AREA OF OPERATION": "_AREA_OF_OPERATION",
    # Vessel particulars
    "TOTAL VESSEL POWER (H.P.)": "_TOTAL_POWER_HP",
    "MAX. VESSEL SPEED (knots)": "TRANSIT_SPEED_KNOTS",
    "QUARTERS CAPACITY (persons)": "QUARTERS_CAPACITY",
    "LENGTH (ft.)": "_LENGTH_FT",
    "WIDTH (ft.)": "_WIDTH_FT",
    "TRANSIT DRAFT (ft.)": "_TRANSIT_DRAFT_FT",
    "OPERATING DRAFT (ft.)": "_OPERATING_DRAFT_FT",
    "MAX. VARIABLE LOAD (S.T.)": "VARIABLE_DECK_LOAD_ST",
    "MOONPOOL LENGTH (ft.)": "_MOONPOOL_COMPOUND",
    # Station keeping
    "D.P. RATING": "_DP_RATING_RAW",
    # Drilling equipment
    "DERRICK RATING (Max Hook Kips)": "HOOKLOAD_RATING_KIPS",
    "DRAWWORKS (H.P.)": "DRAWWORKS_HP",
    "ROTARY TABLE SIZE (In.)": "ROTARY_TABLE_SIZE_IN",
    # Mud systems
    "MUD PUMPS No.": "MUD_PUMP_COUNT",
    # Riser
    "RISER SIZE (O.D. In.)": "RISER_SIZE_IN",
    "RISER JOINT LENGTH (ft.)": "RISER_LENGTH_FT",
    # BOP
    "BOP OPERATING PRESSURE (Ksi)": "_BOP_PRESSURE_KSI",
}

# Rows that are section headers (skip during parsing)
_SECTION_HEADERS: frozenset[str] = frozenset({
    "RIG INFORMATION",
    "RIG INFORMATION (CONTINUED)",
    "VESSEL PARTICULARS",
    "MOORING/STATION KEEPING",
    "LIFTING EQUIPMENT",
    "DRILLING EQUIPMENT",
    "ENGINEERING COMPANY DETAILS",
    "MUD PUMPS",
    "MUD PIT DATA",
    "SOLIDS CONTROL",
    "RISER AND TENSIONER DATA",
    "BOP and BOP CONTROL DETAILS",
})

FT_TO_M: float = 0.3048


class XlsFleetParser:
    """Parse transposed XLS fleet data into DrillingRigSchema-compatible dicts."""

    def __init__(self, xls_path: str | Path) -> None:
        self.xls_path = Path(xls_path)

    def parse(self) -> list[dict[str, Any]]:
        """Read, transpose, map fields, and return schema-ready dicts."""
        raw_df = self._read_transposed()
        records: list[dict[str, Any]] = []
        for _, row in raw_df.iterrows():
            record = self._map_row(row)
            if record:
                records.append(record)
        logger.info("Parsed %d rigs from %s", len(records), self.xls_path.name)
        return records

    def _read_transposed(self) -> pd.DataFrame:
        """Read the transposed XLS and pivot to rig-per-row."""
        df = pd.read_excel(self.xls_path, header=None, dtype=str)

        # Row 0 has rig names across columns 1..N
        rig_names = df.iloc[0, 1:].tolist()

        # Column 0 has field labels in rows 1..M
        field_labels = df.iloc[1:, 0].tolist()

        # Values matrix: rows 1..M, columns 1..N
        values = df.iloc[1:, 1:].values

        # Build transposed DataFrame: rigs as rows, fields as columns
        transposed = pd.DataFrame(
            values.T,
            columns=field_labels,
            index=range(len(rig_names)),
        )
        transposed.insert(0, "_RIG_NAME", rig_names)

        return transposed

    def _map_row(self, row: pd.Series) -> Optional[dict[str, Any]]:
        """Map a single transposed row to a schema-ready dict."""
        rig_name = str(row.get("_RIG_NAME", "")).strip()
        if not rig_name or rig_name.lower() in ("nan", "none", ""):
            return None

        record: dict[str, Any] = {
            "VESSEL_NAME": rig_name,
            "DATA_SOURCE": "xls_historical",
        }

        # Extract raw mapped fields
        raw: dict[str, Any] = {}
        for xls_label, schema_field in _FIELD_MAP.items():
            val = row.get(xls_label)
            if val is not None and str(val).strip() not in ("", "nan"):
                raw[schema_field] = str(val).strip()

        # Vessel type mapping
        vtype_raw = raw.get("_VESSEL_TYPE_RAW", "")
        record["VESSEL_TYPE"] = "drilling_rig"
        record["RIG_TYPE"] = _VESSEL_TYPE_MAP.get(
            vtype_raw, vtype_raw.lower() if vtype_raw else None
        )

        # Simple string fields
        for field in ("RIG_DESIGN", "CLASSIFICATION_SOCIETY"):
            if field in raw:
                record[field] = raw[field]

        # Year fields
        year_raw = raw.get("_YEAR_BUILT_RAW")
        if year_raw:
            parsed = parse_numeric(year_raw)
            if parsed and 1900 <= parsed <= 2035:
                record["YEAR_BUILT"] = int(parsed)

        # Numeric fields (parse mixed formats)
        numeric_fields = [
            "MAX_WATER_DEPTH_FT", "WATER_DEPTH_RATING_FT",
            "DRILLING_DEPTH_RATING_FT", "TRANSIT_SPEED_KNOTS",
            "VARIABLE_DECK_LOAD_ST", "HOOKLOAD_RATING_KIPS",
            "DRAWWORKS_HP", "ROTARY_TABLE_SIZE_IN",
            "RISER_SIZE_IN", "RISER_LENGTH_FT",
        ]
        for field in numeric_fields:
            if field in raw:
                record[field] = parse_numeric(raw[field])

        # Integer fields
        int_fields = ["QUARTERS_CAPACITY", "MUD_PUMP_COUNT"]
        for field in int_fields:
            if field in raw:
                parsed = parse_numeric(raw[field])
                if parsed is not None:
                    record[field] = int(parsed)

        # Length/Width -> LOA_M, BEAM_M (ft to m)
        length_ft = parse_numeric(raw.get("_LENGTH_FT"))
        if length_ft:
            record["LOA_M"] = round(length_ft * FT_TO_M, 2)

        width_ft = parse_numeric(raw.get("_WIDTH_FT"))
        if width_ft:
            record["BEAM_M"] = round(width_ft * FT_TO_M, 2)

        # Drafts (store in metres)
        transit_draft = parse_numeric(raw.get("_TRANSIT_DRAFT_FT"))
        if transit_draft:
            record["DRAFT_M"] = round(transit_draft * FT_TO_M, 2)

        # Moonpool compound "L x W" -> moonpool_length_m, moonpool_width_m
        moonpool_raw = raw.get("_MOONPOOL_COMPOUND")
        if moonpool_raw:
            pair = parse_dimension_pair(moonpool_raw)
            if pair:
                record["MOONPOOL_LENGTH_M"] = round(pair[0] * FT_TO_M, 2)
                record["MOONPOOL_WIDTH_M"] = round(pair[1] * FT_TO_M, 2)
            else:
                # Single value -> treat as diameter
                single = parse_numeric(moonpool_raw)
                if single:
                    record["MOONPOOL_DIAMETER_M"] = round(
                        single * FT_TO_M, 2
                    )

        # DP rating: "DP2" -> 2
        dp_raw = raw.get("_DP_RATING_RAW")
        if dp_raw:
            record["DP_CLASS"] = parse_int_from_label(dp_raw)

        # BOP pressure: Ksi -> PSI (multiply by 1000)
        bop_ksi = parse_numeric(raw.get("_BOP_PRESSURE_KSI"))
        if bop_ksi:
            record["BOP_PRESSURE_PSI"] = bop_ksi * 1000.0

        # Set offshore flag (all XLS rigs are offshore floaters)
        record["IS_OFFSHORE"] = True
        record["VESSEL_CATEGORY"] = "drilling_rig"

        return record
