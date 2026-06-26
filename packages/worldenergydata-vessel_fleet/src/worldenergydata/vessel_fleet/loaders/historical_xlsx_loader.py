"""Ingest historical fleet spreadsheets from the Google Drive corpus.

These spreadsheets (DrillRigs, Semisub, Stimulation Vessels, and the
``Semi Sub/`` set) are a HISTORICAL baseline captured circa 2010-2014. They
describe rigs and vessels as they were specced/operating in that era and are
**NOT** a statement of current availability or current ownership. Every record
is tagged ``DATA_SOURCE = xls_historical`` and ``COLLECTION_DATE = 2010-2014``
so downstream consumers never mistake it for a live fleet snapshot.

The corpus is heterogeneous: some sheets are row-oriented (one vessel per row),
some are transposed (one vessel per column), and a few are geometry/mesh models
with no fleet roster at all. The loader inspects each sheet, picks an
orientation, maps the columns it recognises onto the vessel_fleet
base/drilling_rig schema fields, and preserves every original column value in a
``RAW`` dict so nothing is silently dropped.

Raw xlsx files are read-only inputs and are NEVER committed; the curated output
directory is gitignored.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from worldenergydata.vessel_fleet.constants import M_TO_FT, DataSource
from worldenergydata.vessel_fleet.parsers.numeric import parse_numeric

logger = logging.getLogger(__name__)

# Historical baseline era for the Drive corpus spreadsheets.
COLLECTION_DATE: str = "2010-2014"
DATA_SOURCE: str = DataSource.XLS_HISTORICAL.value

FT_TO_M: float = 0.3048

# Files that make up the historical Drive fleet corpus, relative to base_dir.
DRIVE_FLEET_FILES: tuple[str, ...] = (
    "DrillRigs.xlsx",
    "Semisub.xlsx",
    "Stimulation Vessels.xlsx",
    "Semi Sub/Semi sub Basic info.xlsx",
    "Semi Sub/Semi Submersible Detailed Engineering Data.xlsx",
    "Semi Sub/Semisub project related data.xlsx",
    "Semi Sub/Semi sub Riser information.xlsx",
)

# Column-header keywords that identify the vessel-name column. Checked as
# normalised (uppercase, whitespace-collapsed) substrings, longest first.
_NAME_KEYS: tuple[str, ...] = (
    "VESSEL NAME",
    "FACILITY NAME",
    "RIG NAME",
    "NAME",
)

# XLS vessel/rig type code -> standardised value.
_RIG_TYPE_MAP: dict[str, str] = {
    "SS": "semi_submersible",
    "DS": "drillship",
    "JU": "jack_up",
}

# Ordered (most-specific-first) substring -> (schema_field, kind) mapping.
# kind: "str" (verbatim), "float" (parse_numeric), "len_ft" (ft -> LOA/BEAM m),
# "wd" (water depth, unit-aware -> WATER_DEPTH_RATING_FT),
# "draft_m" (metres, verbatim), "type" (rig type code).
_COLUMN_MAP: tuple[tuple[str, str, str], ...] = (
    ("VESSEL TYPE", "RIG_TYPE", "type"),
    ("RIG TYPE", "RIG_TYPE", "type"),
    ("VESSEL DESIGN", "RIG_DESIGN", "str"),
    ("RIG DESIGN", "RIG_DESIGN", "str"),
    ("CURRENT STATUS", "STATUS", "str"),
    ("STATUS", "STATUS", "str"),
    ("VESSEL OPERATOR", "OPERATOR", "str"),
    ("OPERATOR", "OPERATOR", "str"),
    ("CONTRACTOR", "OPERATOR", "str"),
    ("VESSEL OWNER", "OWNER", "str"),
    ("OWNER", "OWNER", "str"),
    ("CLASSIFICATION", "CLASSIFICATION_SOCIETY", "str"),
    ("WATER DEPTH", "WATER_DEPTH_RATING_FT", "wd"),
    ("DRILLING DEPTH", "DRILLING_DEPTH_RATING_FT", "float"),
    ("OPERATING DRAFT", "DRAFT_M", "draft_m"),
    ("TRANSIT DRAFT", "DRAFT_M", "draft_m"),
    ("TOTAL LENGTH", "LOA_M", "len_ft"),
    ("LENGTH", "LOA_M", "len_ft"),
    ("TOTAL BEAM", "BEAM_M", "len_ft"),
    ("BEAM", "BEAM_M", "len_ft"),
    ("WIDTH", "BEAM_M", "len_ft"),
    ("CRUISING SPEED", "TRANSIT_SPEED_KNOTS", "float"),
    ("VESSEL SPEED", "TRANSIT_SPEED_KNOTS", "float"),
    ("QUARTERS", "QUARTERS_CAPACITY", "float"),
)

# Field labels (column 0/1) that signal a TRANSPOSED sheet (vessel per column).
_TRANSPOSED_LABELS: frozenset[str] = frozenset(
    {
        "VESSEL TYPE",
        "VESSEL DESIGN",
        "CONSTRUCTION DATE",
        "UPGRADE DATE",
        "CLASSIFICATION",
        "RIG INFORMATION",
        "VESSEL PARTICULARS",
        "DRILLING EQUIPMENT",
    }
)

_WS_RE = re.compile(r"\s+")
# Trailing feet/inch/quote marks the corpus uses, e.g. "5,000'", '15"'.
_FOOT_INCH_RE = re.compile(r"[\'\"‘’“”]+\s*$")


def _norm(value: object) -> str:
    """Normalise a header/label to uppercase, whitespace-collapsed string."""
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return _WS_RE.sub(" ", s).upper()


def _is_name_key(header: str) -> bool:
    norm = _norm(header)
    return any(norm == k or norm.startswith(k + " ") or norm == k for k in _NAME_KEYS)


def _num(raw: Any) -> Optional[float]:
    """parse_numeric with trailing foot/inch marks (5,000' / 15") stripped."""
    if isinstance(raw, str):
        raw = _FOOT_INCH_RE.sub("", raw.strip())
    return parse_numeric(raw)


def _match_column(header: str) -> Optional[tuple[str, str]]:
    """Return (schema_field, kind) for a recognised column header, else None."""
    norm = _norm(header)
    if not norm:
        return None
    for keyword, field, kind in _COLUMN_MAP:
        if keyword in norm:
            return field, kind
    return None


def _coerce_value(field: str, kind: str, raw: Any, header: str) -> Any:
    """Coerce a raw cell value for a mapped schema field."""
    if kind == "str" or kind == "type":
        s = str(raw).strip()
        if kind == "type":
            token = s.split()[0].upper() if s else ""
            # Leading alpha code only: "SS- PQ" -> "SS", "DS Gusto" -> "DS".
            alpha = re.match(r"[A-Z]+", token)
            code = alpha.group() if alpha else token
            return _RIG_TYPE_MAP.get(code, s.lower() or None)
        return s or None
    if kind == "float":
        return _num(raw)
    if kind == "draft_m":
        return _num(raw)
    if kind == "len_ft":
        ft = _num(raw)
        return round(ft * FT_TO_M, 2) if ft is not None else None
    if kind == "wd":
        val = _num(raw)
        if val is None:
            return None
        # Column says metres -> convert to feet to match the *_FT schema field.
        if "(M)" in _norm(header) or _norm(header).endswith(" M"):
            return round(val * M_TO_FT, 1)
        return val
    return raw


def normalize_to_records(
    df: pd.DataFrame,
    source_name: str,
    sheet_name: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Map a row-oriented fleet DataFrame to vessel_fleet record dicts.

    Each input row becomes one record dict containing the recognised schema
    fields (VESSEL_NAME, RIG_TYPE, OPERATOR, WATER_DEPTH_RATING_FT, ...), the
    historical provenance tags (DATA_SOURCE / COLLECTION_DATE / SOURCE_FILE),
    and a ``RAW`` sub-dict that preserves every original column value keyed by
    its original column header.

    Args:
        df: Row-oriented DataFrame (one vessel per row, named columns). The
            vessel-name column is auto-detected from its header.
        source_name: Source file name, recorded as SOURCE_FILE provenance.
        sheet_name: Optional sheet name, recorded as SOURCE_SHEET.

    Returns:
        List of record dicts. Rows without a usable vessel name are skipped.
    """
    if df is None or df.empty:
        return []

    columns = list(df.columns)
    name_col = next((c for c in columns if _is_name_key(str(c))), None)
    if name_col is None:
        logger.info("No vessel-name column in %s/%s; skipping", source_name, sheet_name)
        return []

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        name = str(row[name_col]).strip() if row[name_col] is not None else ""
        if not name or name.lower() in ("nan", "none"):
            continue

        record: dict[str, Any] = {
            "VESSEL_NAME": name,
            "DATA_SOURCE": DATA_SOURCE,
            "COLLECTION_DATE": COLLECTION_DATE,
            "SOURCE_FILE": source_name,
        }
        if sheet_name:
            record["SOURCE_SHEET"] = sheet_name

        raw: dict[str, Any] = {}
        for col in columns:
            value = row[col]
            if value is None or (isinstance(value, float) and pd.isna(value)):
                value = None
            elif isinstance(value, str) and value.strip().lower() in ("", "nan"):
                value = None

            header = str(col)
            if value is not None:
                raw[header] = value if not isinstance(value, str) else value.strip()

            if col == name_col or value is None:
                continue
            match = _match_column(header)
            if match is None:
                continue
            field, kind = match
            # Do not overwrite an already-populated mapped field (first wins).
            if record.get(field) in (None, ""):
                coerced = _coerce_value(field, kind, value, header)
                if coerced is not None:
                    record[field] = coerced

        record["RAW"] = raw
        records.append(record)

    logger.info(
        "Normalised %d records from %s/%s", len(records), source_name, sheet_name
    )
    return records


def _detect_orientation(raw_df: pd.DataFrame) -> str:
    """Return 'transposed', 'row', or 'skip' for a raw (header=None) sheet."""
    if raw_df.empty or raw_df.shape[0] < 2:
        return "skip"

    # Count field-label hits down the first two columns -> transposed signal.
    label_hits = 0
    for col_idx in (0, 1):
        if col_idx >= raw_df.shape[1]:
            continue
        for value in raw_df.iloc[:, col_idx].tolist():
            if _norm(value) in _TRANSPOSED_LABELS:
                label_hits += 1
    if label_hits >= 3:
        return "transposed"

    # Row-oriented if a name keyword appears in the first few cells of an
    # early row.
    for r in range(min(6, raw_df.shape[0])):
        for c in range(min(4, raw_df.shape[1])):
            if _is_name_key(str(raw_df.iat[r, c])):
                return "row"
    return "skip"


def _read_row_oriented(raw_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Flatten a (possibly multi-row) header and return a clean DataFrame."""
    # Locate the header row + the column holding the name keyword.
    header_row = name_col = None
    for r in range(min(6, raw_df.shape[0])):
        for c in range(min(6, raw_df.shape[1])):
            if _is_name_key(str(raw_df.iat[r, c])):
                header_row, name_col = r, c
                break
        if header_row is not None:
            break
    if header_row is None:
        return None

    # Data starts at the first row (after header_row) where the name column has
    # a real value; rows between are extra header rows to be flattened.
    data_start = None
    for r in range(header_row + 1, raw_df.shape[0]):
        if _norm(raw_df.iat[r, name_col]):
            data_start = r
            break
    if data_start is None:
        return None

    header_rows = range(header_row, data_start)
    headers: list[str] = []
    for c in range(raw_df.shape[1]):
        label = ""
        for hr in header_rows:
            cell = _norm(raw_df.iat[hr, c])
            if cell:
                label = cell  # last non-empty across header rows wins
        headers.append(label if label else f"COL_{c}")

    # De-duplicate headers so RAW keys never collide.
    seen: dict[str, int] = {}
    unique_headers: list[str] = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            unique_headers.append(f"{h} ({seen[h]})")
        else:
            seen[h] = 0
            unique_headers.append(h)

    body = raw_df.iloc[data_start:].copy()
    body.columns = unique_headers
    body = body.reset_index(drop=True)
    return body


def _label_score(raw_df: pd.DataFrame, col: int) -> int:
    """Count rows where ``col`` holds a recognised field label."""
    score = 0
    for value in raw_df.iloc[:, col].tolist():
        norm = _norm(value)
        if not norm:
            continue
        if norm in _TRANSPOSED_LABELS or _match_column(norm) is not None:
            score += 1
    return score


def _read_transposed(raw_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Pivot a vessel-per-column sheet into a vessel-per-row DataFrame."""
    # Find the row + column whose cell is the NAME label; vessel names span the
    # columns to the right of that cell on the same row.
    name_row = name_label_col = None
    for r in range(min(8, raw_df.shape[0])):
        for c in range(min(3, raw_df.shape[1])):
            if _norm(raw_df.iat[r, c]) == "NAME":
                name_row, name_label_col = r, c
                break
        if name_row is not None:
            break
    if name_row is None:
        return None

    names = raw_df.iloc[name_row].tolist()
    value_cols = [c for c in range(name_label_col + 1, len(names)) if _norm(names[c])]
    if not value_cols:
        return None
    first_val = min(value_cols)

    # The label column is whichever column left of the first value column holds
    # the most recognised field labels (units/section columns score low).
    candidate_cols = range(name_label_col, first_val) or [name_label_col]
    label_col = max(candidate_cols, key=lambda c: _label_score(raw_df, c))

    field_labels: list[str] = []
    for r in range(raw_df.shape[0]):
        if r == name_row:
            continue
        label = _norm(raw_df.iat[r, label_col])
        field_labels.append(label if label else f"ROW_{r}")

    rows: list[dict[str, Any]] = []
    for c in value_cols:
        vessel = _norm(names[c])
        record: dict[str, Any] = {"VESSEL NAME": names[c]}
        idx = 0
        for r in range(raw_df.shape[0]):
            if r == name_row:
                continue
            label = field_labels[idx]
            idx += 1
            value = raw_df.iat[r, c]
            if label and label not in record:
                record[label] = value
        if vessel:
            rows.append(record)
    if not rows:
        return None
    return pd.DataFrame(rows)


def load_sheet_records(path: str | Path) -> list[dict[str, Any]]:
    """Read one xlsx file and return normalised records across all sheets."""
    path = Path(path)
    records: list[dict[str, Any]] = []
    try:
        xl = pd.ExcelFile(path)
    except Exception as exc:  # pragma: no cover - defensive I/O guard
        logger.warning("Could not open %s: %s", path, exc)
        return []

    for sheet in xl.sheet_names:
        try:
            raw_df = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str)
        except Exception as exc:  # pragma: no cover - defensive I/O guard
            logger.warning("Could not read %s/%s: %s", path.name, sheet, exc)
            continue

        orientation = _detect_orientation(raw_df)
        if orientation == "skip":
            continue
        if orientation == "transposed":
            clean = _read_transposed(raw_df)
        else:
            clean = _read_row_oriented(raw_df)
        if clean is None:
            continue
        records.extend(normalize_to_records(clean, path.name, sheet))
    return records


def load_drive_fleet_spreadsheets(base_dir: str | Path) -> pd.DataFrame:
    """Load and combine the historical Drive fleet spreadsheets.

    Iterates the known corpus files under ``base_dir``, normalises each into
    vessel_fleet records, and returns a single combined DataFrame. Missing
    files are skipped with a warning (the corpus lives on read-only storage).

    Args:
        base_dir: Directory containing the Drive fleet spreadsheets.

    Returns:
        Combined DataFrame of historical fleet records (empty if none found).
        Every row carries DATA_SOURCE = xls_historical and
        COLLECTION_DATE = 2010-2014.
    """
    base = Path(base_dir)
    all_records: list[dict[str, Any]] = []
    for rel in DRIVE_FLEET_FILES:
        path = base / rel
        if not path.exists():
            logger.warning("Drive fleet file not found: %s", path)
            continue
        all_records.extend(load_sheet_records(path))

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    logger.info(
        "Loaded %d historical fleet records from %s files under %s",
        len(df),
        len(DRIVE_FLEET_FILES),
        base,
    )
    return df
