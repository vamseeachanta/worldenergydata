"""Parser for contractor rig-summary one-pager text (Noble 'Rig Summary' PDFs).

Extracts the 'General' and 'Ratings & Dimensions' blocks into schema-compatible
fields (see ``schemas.drilling_rig.DrillingRigSchema``). Text extracted from
these PDFs (pdfplumber / pdftotext) carries recurring quirks the parser
normalizes before matching:

- spaces injected inside numbers: ``"12 ,000 ft"``
- European decimal commas: ``"137,8 ft"`` (1-2 decimals) alongside
  thousands separators: ``"44,092 kips"`` (3 digits)
- fused unit tokens: ``"84 ftx 41 ft"``
- load values quoted in either kips or short tons across sister vessels

Dimensions are returned in metres (schema ``*_M`` fields, 1 decimal) with the
source imperial values preserved under ``RAW_*`` keys for provenance review.
"""

from __future__ import annotations

import re
from typing import Any, Optional

FT_TO_M = 0.3048
KIPS_PER_SHORT_TON = 2.0  # 1 short ton = 2,000 lb; 1 kip = 1,000 lb

_NUM = r"[\d][\d ,.]*"


def _clean_number(raw: str) -> Optional[float]:
    """Parse a number that may mix thousands commas and decimal commas.

    A comma followed by exactly 3 digits is a thousands separator
    ("44,092" -> 44092); a comma followed by 1-2 digits is a decimal
    comma ("137,8" -> 137.8).
    """
    s = raw.strip().replace(" ", "")
    if not s:
        return None
    s = re.sub(r",(\d{3})(?!\d)", r"\1", s)  # thousands
    s = re.sub(r",(\d{1,2})(?!\d)", r".\1", s)  # decimal comma
    try:
        return float(s)
    except ValueError:
        return None


def _ft_to_m(value_ft: Optional[float]) -> Optional[float]:
    if value_ft is None:
        return None
    return round(value_ft * FT_TO_M, 1)


def _normalize(text: str) -> str:
    """Collapse extraction artifacts so field regexes can be simple."""
    # "12 ,000" / "137 ,8" -> "12,000" / "137,8"
    text = re.sub(r"(\d)\s+([,.])\s*(\d)", r"\1\2\3", text)
    # "84 ftx 41" -> "84 ft x 41"
    text = re.sub(r"ftx", "ft x", text)
    return text


def _search_number(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    return _clean_number(m.group(1))


def parse_rig_summary_text(text: str) -> dict[str, Any]:
    """Parse rig-summary text into DrillingRigSchema-compatible fields.

    Only fields present in the text are returned; absent fields are omitted
    (never None-filled) so callers can distinguish "not stated" from parsed.
    """
    text = _normalize(text)
    out: dict[str, Any] = {}

    year = re.search(r"Year\s+Built\s*/?\s*(\d{4})", text, re.IGNORECASE)
    if year:
        out["YEAR_BUILT"] = int(year.group(1))

    flag = re.search(r"^Flag\s*:\s*([A-Za-z][A-Za-z ]+?)\s*$", text, re.MULTILINE)
    if flag:
        out["FLAG_STATE"] = flag.group(1).strip()

    design = re.search(
        r"Rig\s+Design\s*:\s*(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE
    )
    if design:
        out["RIG_DESIGN"] = re.sub(r"\s{2,}", " ", design.group(1)).strip()

    water_ft = _search_number(rf"Water\s+Depth\s*:\s*({_NUM})\s*ft", text)
    if water_ft is not None:
        out["WATER_DEPTH_RATING_FT"] = water_ft

    drill_ft = _search_number(rf"Drilling\s+Depth\s*:\s*({_NUM})\s*ft", text)
    if drill_ft is not None:
        out["DRILLING_DEPTH_RATING_FT"] = drill_ft

    # Line-anchored so "Water Depth"/"Drilling Depth" never match.
    loa_ft = _search_number(rf"^Length\s*:\s*({_NUM})\s*ft", text)
    if loa_ft is not None:
        out["LOA_M"] = _ft_to_m(loa_ft)
        out["RAW_LENGTH_FT"] = loa_ft

    beam_ft = _search_number(rf"^Breadth\s*:\s*({_NUM})\s*ft", text)
    if beam_ft is not None:
        out["BEAM_M"] = _ft_to_m(beam_ft)
        out["RAW_BREADTH_FT"] = beam_ft

    depth_ft = _search_number(rf"^Depth\s*:\s*({_NUM})\s*ft", text)
    if depth_ft is not None:
        out["DEPTH_M"] = _ft_to_m(depth_ft)
        out["RAW_DEPTH_FT"] = depth_ft

    draft = re.search(
        rf"Draft\s*\(\s*Operating\s*/[^0-9]*({_NUM})\s*ft\s*/\s*({_NUM})\s*ft",
        text,
        re.IGNORECASE,
    )
    if draft:
        op_ft = _clean_number(draft.group(1))
        transit_ft = _clean_number(draft.group(2))
        out["DRAFT_M"] = _ft_to_m(op_ft)
        out["RAW_DRAFT_OPERATING_FT"] = op_ft
        out["RAW_DRAFT_TRANSIT_FT"] = transit_ft

    moonpool = re.search(
        rf"Moonpool\s*:\s*({_NUM})\s*ft\s*x\s*({_NUM})\s*ft", text, re.IGNORECASE
    )
    if moonpool:
        mp_l = _clean_number(moonpool.group(1))
        mp_w = _clean_number(moonpool.group(2))
        out["MOONPOOL_LENGTH_M"] = _ft_to_m(mp_l)
        out["MOONPOOL_WIDTH_M"] = _ft_to_m(mp_w)
        out["RAW_MOONPOOL_FT"] = f"{mp_l:g} x {mp_w:g}"

    vdl = re.search(
        rf"Variable\s+Deck\s*(?:Load)?\s*:?\s*({_NUM})\s*(kips|ST|sT)",
        text,
        re.IGNORECASE,
    )
    if vdl:
        value = _clean_number(vdl.group(1))
        if value is not None:
            unit = vdl.group(2).lower()
            out["VARIABLE_DECK_LOAD_ST"] = round(
                value / KIPS_PER_SHORT_TON if unit == "kips" else value
            )

    hook = re.search(rf"Hook\s+Load\s*:\s*({_NUM})\s*(kips|ST|sT)", text, re.IGNORECASE)
    if hook:
        value = _clean_number(hook.group(1))
        if value is not None:
            unit = hook.group(2).lower()
            out["HOOKLOAD_RATING_KIPS"] = round(
                value if unit == "kips" else value * KIPS_PER_SHORT_TON
            )

    setback = _search_number(rf"Setback\s+Capacity\s*:\s*({_NUM})\s*kips", text)
    if setback is not None:
        out["SETBACK_CAPACITY_KIPS"] = setback

    return out
