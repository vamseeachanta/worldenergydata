# ABOUTME: SubseaIQ field loader + BSEE crosswalk (block-keyed join).
# ABOUTME: Issue #569 (epic #567) — normalize SubseaIQ fields → FieldConcept + BSEE link.
"""
worldenergydata.field_development.subseaiq
==========================================

Loads the SubseaIQ-derived field catalog (the normalized
``data/modules/offshore_assets/curated/fields.csv``) into the playbook's
:class:`FieldConcept` model, and crosswalks it to BSEE.

**The join key is the BOEM block, not the field name.** BSEE OGOR-A identifies
each field by an area+block code (e.g. ``GC254`` = Green Canyon 254), so
matching on field *name* fails (BSEE doesn't name deepwater fields). Matching on
the SubseaIQ ``BLOCK`` column — parsed to ``(area_abbrev, block_number)`` —
connects them. Empirically ~22%+ of SubseaIQ GoM fields match the OGOR field-code
set (rises with more OGOR years / a fuller area map; undeveloped discoveries
never appear in production data).

The SubseaIQ data is stale (~2014) and freely usable, so this loader reads it
directly and may surface derived data publicly — no off-repo restriction.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from worldenergydata.field_development.enums import ConceptType, FluidType
from worldenergydata.field_development.models import FieldConcept

# BOEM Gulf-of-Mexico planning-area name → official abbreviation.
AREA_ABBR: dict[str, str] = {
    "MISSISSIPPI CANYON": "MC", "GREEN CANYON": "GC", "KEATHLEY CANYON": "KC",
    "GARDEN BANKS": "GB", "EAST CAMERON": "EC", "WALKER RIDGE": "WR",
    "ATWATER VALLEY": "AT", "EWING BANK": "EW", "SHIP SHOAL": "SS",
    "SOUTH TIMBALIER": "ST", "VIOSCA KNOLL": "VK", "WEST CAMERON": "WC",
    "ALAMINOS CANYON": "AC", "DESOTO CANYON": "DC", "WEST DELTA": "WD",
    "SOUTH MARSH ISLAND": "SM", "EUGENE ISLAND": "EI", "GRAND ISLE": "GI",
    "MAIN PASS": "MP", "VERMILION": "VR", "HIGH ISLAND": "HI",
    "MUSTANG ISLAND": "MU", "MATAGORDA ISLAND": "MI", "LUND": "LU",
    "SOUTH PASS": "SP", "SOUTH PELTO": "PL", "BRETON SOUND": "BS",
    "EAST BREAKS": "EB", "LLOYD RIDGE": "LL", "DE SOTO CANYON": "DC",
    "GALVESTON": "GA", "SABINE PASS": "SB", "PORT ISABEL": "PI",
    "CORPUS CHRISTI": "MU",
}


def _curated_dir() -> Path:
    return Path(__file__).parents[3] / "data" / "modules" / "offshore_assets" / "curated"


def _curated_fields_path() -> Path:
    return _curated_dir() / "fields.csv"


# SubseaIQ production-facility HOST_TYPE → playbook ConceptType.
HOST_TYPE_MAP: dict[str, ConceptType] = {
    "FIXED PLATFORM": ConceptType.FIXED_JACKET,
    "COMPLIANT TOWER": ConceptType.COMPLIANT_TOWER,
    "TLP": ConceptType.TLP,
    "MINI-TLP": ConceptType.TLP,
    "SPAR": ConceptType.SPAR,
    "DDCV": ConceptType.SPAR,           # deep-draft caisson vessel ≈ spar
    "SEMISUB": ConceptType.SEMISUB_FPS,
    "FPU/FPS": ConceptType.SEMISUB_FPS,
    "FPSO": ConceptType.FPSO,
    "FLNG": ConceptType.FLNG,
    "SUBSEA TIEBACK": ConceptType.SUBSEA_TIEBACK,
}

# When a field has several facilities, this priority picks its concept: a
# subsea-tieback facility means the field is *produced via tieback* (it ties
# back to a host), so that wins over the host's own type.
_CONCEPT_PRIORITY = [
    ConceptType.SUBSEA_TIEBACK, ConceptType.FPSO, ConceptType.SPAR,
    ConceptType.TLP, ConceptType.SEMISUB_FPS, ConceptType.FIXED_JACKET,
    ConceptType.FLNG, ConceptType.COMPLIANT_TOWER,
]


@dataclass(frozen=True)
class CrosswalkRow:
    """One SubseaIQ→BSEE crosswalk result."""

    field_name: str
    block: str
    bsee_block_key: Optional[str]   # e.g. "GC254", or None if unparseable
    matched: bool
    match_type: str                 # "block" | "none" | "unparsed"


def bsee_block_key(block: str) -> Optional[tuple[str, int]]:
    """Parse a SubseaIQ BLOCK string to a BSEE ``(area_abbrev, block_number)`` key.

    Handles full area names ("Green Canyon 254"), already-abbreviated codes
    ("MC26"), and multi-block fields ("Mississippi Canyon 108, 109" → first
    block). Zero-padding is normalized via integer block numbers. Returns None
    if no GoM area/block can be parsed (e.g. a North Sea "PL 218" licence).
    """
    if not block:
        return None
    s = str(block).upper().split(",")[0].strip()
    # Full area name + number. Drop stray "BLOCK"/"AREA"/"LEASE" filler words
    # ("Main Pass Block 123", "Galveston Area 255").
    m = re.match(r"([A-Z][A-Z ]+?)\s+0*(\d+)", s)
    if m:
        area = re.sub(r"\b(BLOCK|AREA|LEASE)\b", " ", m.group(1)).strip()
        area = re.sub(r"\s+", " ", area)
        if area in AREA_ABBR:
            return (AREA_ABBR[area], int(m.group(2)))
    # Already-abbreviated two-letter code + number ("MC26", "GC 254").
    m2 = re.match(r"([A-Z]{2})\s*0*(\d+)$", s)
    if m2:
        return (m2.group(1), int(m2.group(2)))
    return None


def key_to_code(key: tuple[str, int]) -> str:
    """Render a parsed key back to a BSEE-style field code, e.g. ('GC', 254)→'GC254'."""
    return f"{key[0]}{key[1]}"


def _fluid_from_reserve_type(reserve_type: str) -> Optional[FluidType]:
    s = (reserve_type or "").lower()
    if "condensate" in s:
        return FluidType.CONDENSATE
    if "oil" in s and "gas" in s:
        return FluidType.OIL          # oil-primary for mixed
    if "oil" in s:
        return FluidType.OIL
    if "gas" in s:
        return FluidType.GAS
    return None


def _year(text: str) -> Optional[int]:
    m = re.search(r"(19|20)\d{2}", str(text or ""))
    return int(m.group(0)) if m else None


def _float(text: str) -> Optional[float]:
    try:
        return float(str(text).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _load_facility_picks(
    facilities_csv: Optional[Path] = None,
) -> dict[str, tuple[Optional["ConceptType"], Optional[str]]]:
    """Map field-id → (concept_type, operator) from production_facilities.csv.

    A field may have several facilities; the concept is chosen by
    :data:`_CONCEPT_PRIORITY` (subsea-tieback wins — the field ties back to a host).
    Returns ``{field_id: (ConceptType|None, operator|None)}``.
    """
    path = facilities_csv or (_curated_dir() / "production_facilities.csv")
    picks: dict[str, tuple[Optional[ConceptType], Optional[str]]] = {}
    by_field: dict[str, list[tuple[int, ConceptType, Optional[str]]]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fid = (row.get("FACILITY_ID") or "").strip()
            ct = HOST_TYPE_MAP.get((row.get("HOST_TYPE") or "").strip().upper())
            if not fid or ct is None:
                continue
            by_field.setdefault(fid, []).append(
                (_CONCEPT_PRIORITY.index(ct), ct, (row.get("OPERATOR") or None))
            )
    for fid, cands in by_field.items():
        _, ct, op = min(cands, key=lambda t: t[0])
        picks[fid] = (ct, op)
    return picks


def load_subseaiq_fields(
    csv_path: Optional[Path] = None,
    enrich_facilities: bool = False,
    facilities_csv: Optional[Path] = None,
) -> list[FieldConcept]:
    """Load the normalized SubseaIQ field catalog as :class:`FieldConcept` objects.

    Args:
        csv_path: Path to ``fields.csv``; defaults to the curated in-repo copy.
        enrich_facilities: If True, join ``production_facilities.csv`` on the
            project id to fill ``concept_type`` (from HOST_TYPE) and ``operator``.
        facilities_csv: Override path for the facilities file.

    Returns:
        One :class:`FieldConcept` per field (rows with an empty name are skipped).
    """
    path = csv_path or _curated_fields_path()
    picks = _load_facility_picks(facilities_csv) if enrich_facilities else {}
    out: list[FieldConcept] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("FIELD_NAME") or "").strip()
            if not name:
                continue
            fid = (row.get("FIELD_ID") or "").strip()
            concept_type, operator = picks.get(fid, (None, None))
            out.append(FieldConcept(
                name=name,
                operator=operator,
                region=(row.get("COUNTRY") or None),
                water_depth_m=_float(row.get("WATER_DEPTH_M")),
                fluid_type=_fluid_from_reserve_type(row.get("RESERVE_TYPE", "")),
                concept_type=concept_type,
                year_first_oil=_year(row.get("PRODUCTION_START")),
                data_source="SubseaIQ (og-website-db, ~2014)",
            ))
    return out


def build_bsee_crosswalk(
    bsee_field_codes: Iterable[str],
    csv_path: Optional[Path] = None,
    gom_only: bool = True,
) -> list[CrosswalkRow]:
    """Crosswalk SubseaIQ fields to BSEE field codes on the BOEM block key.

    Args:
        bsee_field_codes: BSEE field codes (e.g. OGOR-A field-code column values
            like ``"GC254"``, ``"WD030"``). Parsed to ``(area, block)`` keys.
        csv_path: ``fields.csv`` path; defaults to the curated in-repo copy.
        gom_only: If True (default), only crosswalk rows flagged US_GOM.

    Returns:
        One :class:`CrosswalkRow` per (GoM) SubseaIQ field.
    """
    path = csv_path or _curated_fields_path()
    bsee_keys = {bsee_block_key(c) for c in bsee_field_codes}
    bsee_keys.discard(None)

    rows: list[CrosswalkRow] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("FIELD_NAME") or "").strip()
            if not name:
                continue
            if gom_only and (row.get("US_GOM_FLAG") or "").strip() != "Y":
                continue
            block = (row.get("BLOCK") or "").strip()
            key = bsee_block_key(block)
            if key is None:
                rows.append(CrosswalkRow(name, block, None, False, "unparsed"))
                continue
            matched = key in bsee_keys
            rows.append(CrosswalkRow(
                name, block, key_to_code(key), matched,
                "block" if matched else "none",
            ))
    return rows


def crosswalk_summary(rows: list[CrosswalkRow]) -> dict[str, int]:
    """Aggregate counts for a crosswalk run (total / matched / unparsed)."""
    return {
        "total": len(rows),
        "matched": sum(r.matched for r in rows),
        "unparsed": sum(r.match_type == "unparsed" for r in rows),
    }
