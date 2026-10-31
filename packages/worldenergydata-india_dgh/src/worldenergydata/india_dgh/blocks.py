"""OALP and special-round awarded blocks, parsed from DGH PDF tables.

DGH publishes each round's award list as a PDF on https://www.dghindia.gov.in.
Layouts differ by round: rounds I-III list block name and H1 bidder only;
rounds V-VII and IX add basin and basin category; rounds IV and VIII add a
"Type / Basin / State" description and area of award in sq. km.

Each table row is anchored on the cell that holds a block code (for example
``KG-UDWHP-2022/1``). Cells drawn over several text rows are joined to the
nearest preceding block code, so vertically wrapped names stay with their block.

Acreage type (onland, shallow water, deep water, ultra-deep water) is taken
from the published description where one exists. Otherwise it is read from the
HELP block code segment (ONHP, OSHP, DWHP, UDWHP), and ``acreage_type_basis``
records which was used. Fields a round does not publish stay missing.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .sources import data_path

BLOCK_CODE = re.compile(
    r"\b([A-Z]{2})[-/]((?:ON|OS|DW|UDW)HP(?:\(CBM\))?|ONDSF|OSDSF)[-/]([0-9]{4}|[A-Za-z]+)/([0-9]+|[0-9]{4})\b"
)
# HELP block-code segment -> acreage type. DGH nomenclature: ON = onland,
# OS = offshore shallow water, DW = deep water, UDW = ultra-deep water; HP = HELP.
CODE_ACREAGE = {
    "ONHP": "onland",
    "ONHP(CBM)": "onland",
    "OSHP": "shallow_water",
    "DWHP": "deep_water",
    "UDWHP": "ultra_deep_water",
    "ONDSF": "onland",
    "OSDSF": "shallow_water",
}
# Block-code prefix -> basin. Each prefix is checked in tests against the basin
# name DGH prints beside it in rounds IV-IX (the published name varies, e.g.
# "Cambay", "Cambay Basin"). Rounds I-III print no basin; there the basin comes
# from this prefix and ``basin_basis`` is "block_code".
CODE_BASIN = {
    "AA": "Assam-Arakan Fold Belt",
    "AN": "Andaman-Nicobar",
    "AS": "Assam Shelf",
    "BP": "Bengal-Purnea",
    "CB": "Cambay",
    "CD": "Cuddapah",
    "CY": "Cauvery",
    "GK": "Kutch",
    "GS": "Saurashtra",
    "GV": "Ganga-Punjab",
    "HF": "Himalayan Foreland",
    "KG": "Krishna-Godavari",
    "KK": "Kerala-Konkan",
    "MB": "Mumbai",
    "MN": "Mahanadi",
    "NM": "Narmada",
    "RJ": "Rajasthan",
    "SR": "Satpura-South Rewa-Damodar",
    "VN": "Vindhyan",
}
# Words split mid-word by cell wrapping in the source PDF (round VIII page 1).
WRAP_FIXES = {"Petrochemic als": "Petrochemicals"}
DESCRIPTION_ACREAGE = [
    ("ultra deep", "ultra_deep_water"),
    ("deep water", "deep_water"),
    ("shallow", "shallow_water"),
    ("onland", "onland"),
]
COLUMNS = [
    "round",
    "round_family",
    "block_name",
    "basin",
    "basin_basis",
    "basin_published",
    "basin_category",
    "acreage_type",
    "acreage_type_basis",
    "area_km2",
    "area_basis",
    "awardee",
    "state",
    "contract_signed",
    "source_id",
    "source_page",
]
HEADER_KEYS = [
    # (column, words that must all appear in the header cell, words that must not)
    ("description", ("description",), ()),
    ("description", ("type",), ()),
    ("basin_category", ("category",), ()),
    ("block_name", ("block",), ()),
    ("basin", ("basin",), ("category",)),
    ("awardee", ("company",), ()),
    ("awardee", ("bidder",), ()),
    ("awardee", ("awardee",), ()),
    ("area_km2", ("area",), ()),
    ("state", ("location",), ()),
]


@dataclass(frozen=True)
class RoundSource:
    round: str
    round_family: str
    source_id: str
    contract_signed: str | None = None  # ISO date, only where the source states it


def _clean(value) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value).replace("�", "-")).strip()
    return re.sub(r"(?<=[A-Za-z])- (?=[A-Z])", "-", text)  # "Kerala- Konkan"


def normalize_block_code(text: str) -> str | None:
    """Return the block code in canonical hyphen form, or None."""
    match = BLOCK_CODE.search(re.sub(r"\s+", "", text))
    if not match:
        return None
    basin, kind, year, serial = match.groups()
    return f"{basin}-{kind}-{year}/{serial}"


def acreage_from_code(code: str) -> str | None:
    kind = code.split("-")[1]
    return CODE_ACREAGE.get(kind)


def acreage_from_description(text: str) -> str | None:
    lowered = text.lower()
    for needle, acreage in DESCRIPTION_ACREAGE:
        if needle in lowered:
            return acreage
    return None


def basin_category(value: str) -> str | None:
    """'Cat-I', 'I', 'Category II' -> 'I'/'II'/'III'/'IV'; anything else None."""
    match = re.fullmatch(r"(?:cat(?:egory)?[-\s]*)?(IV|I{1,3})", value.strip(), re.I)
    return match.group(1).upper() if match else None


def parse_area(value: str) -> float:
    text = value.replace(",", "").strip()
    if not text:
        return float("nan")
    area = float(text)
    if not 0 < area < 100_000:
        raise ValueError(f"block area out of range: {value!r} sq. km")
    return area


def _header_map(rows: list[list]) -> dict[int, str]:
    """Map column index -> field from the header rows above the first block."""
    width = max(len(r) for r in rows)
    texts = [" ".join(_clean(r[i]) for r in rows if i < len(r)).lower() for i in range(width)]
    mapping: dict[int, str] = {}
    for index, text in enumerate(texts):
        for field, required, excluded in HEADER_KEYS:
            if field in mapping.values():
                continue  # first matching column wins
            if all(w in text for w in required) and not any(w in text for w in excluded):
                mapping[index] = field
                break
    return mapping


def table_records(table: list[list], header_rows: list[list] | None = None) -> tuple[list[dict], list[list]]:
    """Group a pdfplumber table into one record per block code.

    Returns the records and the header rows used, so a table that continues on
    a following page without a header can reuse the previous page's header.
    """
    anchors = [i for i, row in enumerate(table) if any(normalize_block_code(_clean(c) or "") for c in row)]
    if not anchors:
        return [], header_rows or []
    header = table[: anchors[0]] if anchors[0] else (header_rows or [])
    mapping = _header_map(header) if header else {}
    # The block column is where the codes are, whatever its header says.
    columns = Counter(
        index
        for row in (table[i] for i in anchors)
        for index, cell in enumerate(row)
        if normalize_block_code(_clean(cell))
    )
    block_column = columns.most_common(1)[0][0]
    mapping = {i: f for i, f in mapping.items() if f != "block_name" and i != block_column}
    mapping[block_column] = "block_name"
    if not header:
        raise ValueError("block table header not recognised")
    totals = [i for i, row in enumerate(table) if _clean(next((c for c in row if _clean(c)), "")).lower().startswith("total")]
    records = []
    bounds = anchors + [len(table)]
    for start, end in zip(bounds, bounds[1:]):
        end = min([end] + [t for t in totals if t > start])
        group = table[start:end]
        record: dict[str, str] = {}
        for index, field in mapping.items():
            parts = [_clean(row[index]) for row in group if index < len(row) and _clean(row[index])]
            joined = " ".join(parts)
            for broken, whole in WRAP_FIXES.items():
                joined = joined.replace(broken, whole)
            record[field] = joined
        records.append(record)
    # A company cell merged over several blocks is printed once, on the first.
    previous = None
    for record in records:
        if record.get("awardee"):
            record["awardee"] = re.sub(r"\(all \d+ blocks\)", "", record["awardee"], flags=re.I).strip()
            previous = record["awardee"]
        elif "awardee" in record and previous:
            record["awardee"] = previous
    return records, header


def parse_round_pdf(path: str | Path, source: RoundSource) -> pd.DataFrame:
    """Parse one DGH award-list PDF into the normalized block schema."""
    import pdfplumber

    settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 4, "join_tolerance": 4}
    rows = []
    with pdfplumber.open(str(path)) as pdf:
        header: list[list] = []
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables(settings) or page.extract_tables()
            for table in tables:
                if len(table) < 2:
                    continue
                records, header = table_records(table, header)
                for record in records:
                    rows.append(_normalize(record, source, page_number))
    frame = pd.DataFrame(rows, columns=COLUMNS)
    if frame.empty:
        raise ValueError(f"no blocks parsed from {path}")
    if frame.block_name.duplicated().any():
        raise ValueError(f"duplicate block in {source.round}")
    return frame


def _normalize(record: dict, source: RoundSource, page: int) -> dict:
    code = normalize_block_code(record["block_name"])
    description = record.get("description", "")
    acreage, basis = acreage_from_description(description), "source_table"
    if acreage is None:
        acreage, basis = acreage_from_code(code), "block_code"
    published = record.get("basin") or (description.split("/")[1].strip() if description.count("/") >= 2 else "")
    basin = CODE_BASIN.get(code[:2])
    category = basin_category(record.get("basin_category", ""))
    area = parse_area(record.get("area_km2", ""))
    return {
        "round": source.round,
        "round_family": source.round_family,
        "block_name": code,
        "basin": basin,
        "basin_basis": "block_code" if basin else None,
        "basin_published": published or None,
        "basin_category": category,
        "acreage_type": acreage,
        "acreage_type_basis": basis,
        "area_km2": area,
        "area_basis": None if math.isnan(area) else "award_list",
        "awardee": record.get("awardee") or None,
        "state": record.get("state") or None,
        "contract_signed": source.contract_signed,
        "source_id": source.source_id,
        "source_page": page,
    }


def load_awarded_blocks() -> pd.DataFrame:
    """Awarded blocks shipped with the package (built by scripts/india_dgh/build_tables.py)."""
    frame = pd.read_csv(data_path("awarded_blocks.csv"), dtype={"basin_category": "string"})
    frame["contract_signed"] = pd.to_datetime(frame["contract_signed"], errors="raise")
    return frame
