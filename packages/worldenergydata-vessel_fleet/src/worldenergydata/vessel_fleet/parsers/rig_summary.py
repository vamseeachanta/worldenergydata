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
SHORT_TONS_PER_TONNE = 1.10231
SHORT_TONS_PER_LONG_TON = 1.12

_NUM = r"[\d][\d ,.]*"
# No internal spaces — for layouts where adjacent columns can put two numbers
# on one line and the spaced pattern would glue them together.
_NUM_TIGHT = r"\d[\d,]*(?:\.\d+)?"


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

    flag = re.search(r"^\s*Flag\s*:\s*([A-Za-z][A-Za-z ]+?)\s*$", text, re.MULTILINE)
    if flag:
        out["FLAG_STATE"] = flag.group(1).strip()

    design = re.search(
        r"Rig\s+Design\s*:\s*(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE
    )
    if design:
        out["RIG_DESIGN"] = re.sub(r"\s{2,}", " ", design.group(1)).strip()

    water_ft = _search_number(rf"Water\s+Depth\s*:[ \t]*({_NUM})\s*ft", text)
    if water_ft is not None:
        out["WATER_DEPTH_RATING_FT"] = water_ft

    drill_ft = _search_number(rf"Drilling\s+Depth\s*:[ \t]*({_NUM})\s*ft", text)
    if drill_ft is not None:
        out["DRILLING_DEPTH_RATING_FT"] = drill_ft

    # Line-anchored so "Water Depth"/"Drilling Depth" never match.
    loa_ft = _search_number(rf"^\s*Length\s*:[ \t]*({_NUM})\s*ft", text)
    if loa_ft is not None:
        out["LOA_M"] = _ft_to_m(loa_ft)
        out["RAW_LENGTH_FT"] = loa_ft

    beam_ft = _search_number(rf"^\s*Breadth\s*:[ \t]*({_NUM})\s*ft", text)
    if beam_ft is not None:
        out["BEAM_M"] = _ft_to_m(beam_ft)
        out["RAW_BREADTH_FT"] = beam_ft

    depth_ft = _search_number(rf"^\s*Depth\s*:[ \t]*({_NUM})\s*ft", text)
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
        rf"Moonpool\s*:[ \t]*({_NUM})\s*ft\s*x\s*({_NUM})\s*ft", text, re.IGNORECASE
    )
    if moonpool:
        mp_l = _clean_number(moonpool.group(1))
        mp_w = _clean_number(moonpool.group(2))
        out["MOONPOOL_LENGTH_M"] = _ft_to_m(mp_l)
        out["MOONPOOL_WIDTH_M"] = _ft_to_m(mp_w)
        out["RAW_MOONPOOL_FT"] = f"{mp_l:g} x {mp_w:g}"

    vdl = re.search(
        rf"Variable\s+Deck\s*(?:Load)?\s*:?[ \t]*({_NUM})\s*(kips|ST|sT)",
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

    hook = re.search(
        rf"Hook\s+Load\s*:[ \t]*({_NUM})\s*(kips|ST|sT)", text, re.IGNORECASE
    )
    if hook:
        value = _clean_number(hook.group(1))
        if value is not None:
            unit = hook.group(2).lower()
            out["HOOKLOAD_RATING_KIPS"] = round(
                value if unit == "kips" else value * KIPS_PER_SHORT_TON
            )

    setback = _search_number(rf"Setback\s+Capacity\s*:[ \t]*({_NUM})\s*kips", text)
    if setback is not None:
        out["SETBACK_CAPACITY_KIPS"] = setback

    # Ex-Diamond Offshore "specification sheet" layout (no colons, metric in
    # parentheses) — fills anything the Rig Summary block didn't provide.
    for field, value in _parse_spec_sheet_layout(text).items():
        out.setdefault(field, value)

    # Transocean "RigSpecs" layout — same fill-the-gaps merge.
    for field, value in _parse_transocean_layout(text).items():
        out.setdefault(field, value)

    # Valaris sidebar layout — same fill-the-gaps merge.
    for field, value in _parse_valaris_layout(text).items():
        out.setdefault(field, value)

    return out


def _parse_valaris_layout(text: str) -> dict[str, Any]:
    """Parse the Valaris rig-spec sidebar layout.

    Labels sit on their own line with the value on the next line (drillship
    sheets omit the trailing colon, jackup sheets include it)::

        Length Overall          |  Hull Length:
        752ft                   |  246ft
        Moonpool, Opening at Baseline
        73.5ft x 42ft

    Design and year come from the sheet subtitle
    (``GustoMSC P10,000 Drillship • Year in Service: 2015``). Jackup hook /
    setback loads are quoted in lbs (converted to kips). Variable Deck Load
    is captured only when a unit is printed.
    """
    out: dict[str, Any] = {}

    year = re.search(r"Year\s+in\s+Service:\s*(\d{4})", text, re.IGNORECASE)
    if year:
        out["YEAR_BUILT"] = int(year.group(1))

    design = re.search(
        r"^\s*(.{3,70}?)\s*[•·]\s*Year\s+in\s+Service", text, re.MULTILINE
    )
    if design:
        out["RIG_DESIGN"] = re.sub(r"\s{2,}", " ", design.group(1)).strip()

    def _next_line_number(label: str, unit: str = "ft") -> Optional[float]:
        # pdftotext -layout preserves column positions, and body text
        # interleaves with the sidebar: the value sits 1-2 lines below the
        # label at (approximately) the SAME column. Match on column, not on
        # line order, so derrick dimensions etc. in other columns are skipped.
        for m in re.finditer(rf"{label}:?", text, re.IGNORECASE):
            col = m.start() - (text.rfind("\n", 0, m.start()) + 1)
            for line in text[m.end() :].split("\n")[1:3]:
                for num in re.finditer(
                    rf"({_NUM_TIGHT})\s*{unit}\b", line, re.IGNORECASE
                ):
                    if abs(num.start(1) - col) <= 8:
                        return _clean_number(num.group(1))
        return None

    loa_ft = _next_line_number(r"(?:Length\s+Overall|Hull\s+Length)")
    if loa_ft is not None:
        out["LOA_M"] = _ft_to_m(loa_ft)
        out["RAW_LENGTH_FT"] = loa_ft

    beam_ft = _next_line_number(r"(?:Breadth|Hull\s+Width)")
    if beam_ft is not None:
        out["BEAM_M"] = _ft_to_m(beam_ft)
        out["RAW_BREADTH_FT"] = beam_ft

    depth_ft = _next_line_number(r"(?:Depth\s+at\s+Side|Hull\s+Depth)")
    if depth_ft is not None:
        out["DEPTH_M"] = _ft_to_m(depth_ft)
        out["RAW_DEPTH_FT"] = depth_ft

    draft_ft = _next_line_number(r"Draft\s*\(Max\.?\s*Operating\)")
    if draft_ft is not None:
        out["DRAFT_M"] = _ft_to_m(draft_ft)
        out["RAW_DRAFT_OPERATING_FT"] = draft_ft

    displacement = _next_line_number("Displacement", unit="MT")
    if displacement is not None:
        out["DISPLACEMENT_TONNES"] = displacement

    water_ft = _next_line_number(r"Rated\s+Max\.?\s+Water\s+Depth")
    if water_ft is not None:
        out["WATER_DEPTH_RATING_FT"] = water_ft

    drill_ft = _next_line_number(r"Max(?:imum|\.)?\s+Drilling\s+Depth")
    if drill_ft is not None:
        out["DRILLING_DEPTH_RATING_FT"] = drill_ft

    leg_ft = _next_line_number(r"(?<!Deployed )Leg\s+Length")
    if leg_ft is not None:
        out["LEG_LENGTH_FT"] = leg_ft

    cantilever_ft = _next_line_number(r"Cantilever\s+Skid\s+Out")
    if cantilever_ft is not None:
        out["CANTILEVER_REACH_FT"] = cantilever_ft

    moonpool = re.search(
        rf"Moonpool[^\n]*\n[^\n]*?({_NUM_TIGHT})\s*ft\.?\s*x\s*({_NUM_TIGHT})\s*ft",
        text,
        re.IGNORECASE,
    )
    if moonpool:
        mp_l = _clean_number(moonpool.group(1))
        mp_w = _clean_number(moonpool.group(2))
        out["MOONPOOL_LENGTH_M"] = _ft_to_m(mp_l)
        out["MOONPOOL_WIDTH_M"] = _ft_to_m(mp_w)
        out["RAW_MOONPOOL_FT"] = f"{mp_l:g} x {mp_w:g}"

    hook_lbs = _next_line_number(r"Hook\s+Load", unit="lbs")
    if hook_lbs is not None:
        out["HOOKLOAD_RATING_KIPS"] = round(hook_lbs / 1000)

    setback_lbs = _next_line_number(r"Setback\s+Load", unit="lbs")
    if setback_lbs is not None:
        out["SETBACK_CAPACITY_KIPS"] = round(setback_lbs / 1000)

    vdl = re.search(
        rf"Variable\s+Deck\s+Load:?[ \t]*\n[^\n]*?({_NUM_TIGHT})\s*(kips|MT|ST|LT)\b",
        text,
        re.IGNORECASE,
    )
    if vdl:
        value = _clean_number(vdl.group(1))
        if value is not None:
            unit = vdl.group(2).upper()
            factor = {
                "KIPS": 1 / KIPS_PER_SHORT_TON,
                "MT": SHORT_TONS_PER_TONNE,
                "LT": SHORT_TONS_PER_LONG_TON,
                "ST": 1.0,
            }[unit]
            out["VARIABLE_DECK_LOAD_ST"] = round(value * factor)

    return out


def _parse_transocean_layout(text: str) -> dict[str, Any]:
    """Parse the Transocean deepwater.com RigSpecs layout.

    Compound lines with metric equivalents in parentheses::

        Design / Generation   Jurong Espadon JE3T Ultra Deepwater Drillship
        Dimensions            817 ft. (249 m) x 139.4 ft. (42.5 m) x 64 ft. (19.5 m) Depth
        Drafts                Maximum Operating 38.05 ft. (11.6 m) / Transit 26.3 ft. (8 m)
        Displacement          103,066 st (93,500 mt) (Loadline)
        Moonpool              92ft (28m) length x 29.5ft (9m) width
        Gross Hook Loads      (Main) 1,700 st. (1,542 mt) capacity

    Metric values are taken from the parentheses; loads quoted in short tons.
    """
    out: dict[str, Any] = {}

    year = re.search(
        r"Year\s+Entered\s+Service\s*/?[^0-9]*(\d{4})", text, re.IGNORECASE
    )
    if year:
        out["YEAR_BUILT"] = int(year.group(1))

    design = re.search(
        r"Design\s*/\s*Generation\s{2,}(.+?)(?:\s{3,}|$)", text, re.MULTILINE
    )
    if design:
        out["RIG_DESIGN"] = re.sub(r"\s{2,}", " ", design.group(1)).strip()

    flag = re.search(r"^\s*Flag\s{2,}([A-Za-z][A-Za-z ]+?)\s*$", text, re.MULTILINE)
    if flag:
        out["FLAG_STATE"] = flag.group(1).strip()

    dims = re.search(
        rf"Dimensions\s+({_NUM})\s*ft\.?\s*\(({_NUM})\s*m\.?\)\s*(?:long|LOA)?\s*x\s*"
        rf"({_NUM})\s*ft\.?\s*\(({_NUM})\s*m\.?\)\s*(?:wide|beam)?"
        rf"(?:\s*x\s*({_NUM})\s*ft\.?\s*\(({_NUM})\s*m\.?\))?",
        text,
        re.IGNORECASE,
    )
    if dims:
        out["LOA_M"] = round(_clean_number(dims.group(2)), 1)
        out["BEAM_M"] = round(_clean_number(dims.group(4)), 1)
        raw = f"{_clean_number(dims.group(1)):g} x {_clean_number(dims.group(3)):g}"
        if dims.group(5):
            out["DEPTH_M"] = round(_clean_number(dims.group(6)), 1)
            raw += f" x {_clean_number(dims.group(5)):g}"
        out["RAW_DIMENSIONS_FT"] = raw

    drafts = re.search(
        rf"Drafts\s+[^0-9]*({_NUM})\s*ft\.?\s*\(({_NUM})\s*m\)[^/]*/"
        rf"[^0-9]*({_NUM})\s*ft\.?\s*\(({_NUM})\s*m\)",
        text,
        re.IGNORECASE,
    )
    if drafts:
        out["DRAFT_M"] = round(_clean_number(drafts.group(2)), 1)
        out["RAW_DRAFT_OPERATING_FT"] = _clean_number(drafts.group(1))
        out["RAW_DRAFT_TRANSIT_FT"] = _clean_number(drafts.group(3))

    displacement = re.search(
        rf"Displacement\s+({_NUM})\s*st\s*\(({_NUM})\s*mt\)", text, re.IGNORECASE
    )
    if displacement:
        out["DISPLACEMENT_TONNES"] = _clean_number(displacement.group(2))

    water_ft = _search_number(rf"Maximum\s+Water\s+Depth\s*({_NUM})\s*ft", text)
    if water_ft is not None:
        out["WATER_DEPTH_RATING_FT"] = water_ft

    drill_ft = _search_number(rf"Maximum\s+Drilling\s+Depth\s*({_NUM})\s*ft", text)
    if drill_ft is not None:
        out["DRILLING_DEPTH_RATING_FT"] = drill_ft

    moonpool = re.search(
        rf"Moonpool\s+({_NUM})\s*ft\.?\s*\(({_NUM})\s*m\.?\)\s*"
        rf"(?:length|Fwd\s+to\s+Aft)?\s*x\s*"
        rf"({_NUM})\s*ft\.?\s*\(({_NUM})\s*m\.?\)",
        text,
        re.IGNORECASE,
    )
    if moonpool:
        out["MOONPOOL_LENGTH_M"] = round(_clean_number(moonpool.group(2)), 1)
        out["MOONPOOL_WIDTH_M"] = round(_clean_number(moonpool.group(4)), 1)
        out["RAW_MOONPOOL_FT"] = (
            f"{_clean_number(moonpool.group(1)):g} x {_clean_number(moonpool.group(3)):g}"
        )

    hook = re.search(
        rf"(?:Gross\s+Hook\s+Loads?|Hookload\s+Capacity)\s*\(Main\)\s*({_NUM})\s*st",
        text,
        re.IGNORECASE,
    )
    if hook:
        value = _clean_number(hook.group(1))
        if value is not None:
            out["HOOKLOAD_RATING_KIPS"] = round(value * KIPS_PER_SHORT_TON)

    return out


def _parse_spec_sheet_layout(text: str) -> dict[str, Any]:
    """Parse the ex-Diamond 'specification sheet' layout.

    Labels have no colon separator and imperial values carry the metric
    equivalent in parentheses, e.g.::

        Main Deck                757ft (230.73m) Long x 118ft (35.96m) Wide
        Draft                    36ft (11.0m) Operating
        Moonpool                 73 ft x 32ft (22.25m x 9.75m)
        Variable Deck Load       22,045 MT Operating

    Metric values are taken from the parentheses where printed.
    """
    out: dict[str, Any] = {}

    year = re.search(r"Year\s+Entered\s+Service\s+(\d{4})", text, re.IGNORECASE)
    if year:
        out["YEAR_BUILT"] = int(year.group(1))

    design = re.search(r"^Design\s{2,}(.+?)\s*$", text, re.MULTILINE)
    if design:
        out["RIG_DESIGN"] = re.sub(r"\s{2,}", " ", design.group(1)).strip()

    deck = re.search(
        rf"Main\s+Deck\s+({_NUM})\s*ft\s*\(({_NUM})\s*m\)\s*Long\s*x\s*"
        rf"({_NUM})\s*ft\s*\(({_NUM})\s*m\)\s*Wide",
        text,
        re.IGNORECASE,
    )
    if deck:
        # Main-deck envelope; ~LOA x beam for ship shapes.
        out["LOA_M"] = round(_clean_number(deck.group(2)), 1)
        out["BEAM_M"] = round(_clean_number(deck.group(4)), 1)
        out["RAW_MAIN_DECK_FT"] = (
            f"{_clean_number(deck.group(1)):g} x {_clean_number(deck.group(3)):g}"
        )

    draft = re.search(
        rf"^Draft\s+({_NUM})\s*ft\s*\(({_NUM})\s*m\)\s*(Operating|Drilling)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if draft:
        out["DRAFT_M"] = round(_clean_number(draft.group(2)), 1)
        out["RAW_DRAFT_OPERATING_FT"] = _clean_number(draft.group(1))

    displacement = re.search(rf"Displacement\s+({_NUM})\s*MT", text, re.IGNORECASE)
    if displacement:
        out["DISPLACEMENT_TONNES"] = _clean_number(displacement.group(1))

    vdl = re.search(
        rf"Variable\s+Deck\s+Load\s+({_NUM})\s*(MT|LT|ST)", text, re.IGNORECASE
    )
    if vdl:
        value = _clean_number(vdl.group(1))
        if value is not None:
            unit = vdl.group(2).upper()
            factor = {
                "MT": SHORT_TONS_PER_TONNE,
                "LT": SHORT_TONS_PER_LONG_TON,
                "ST": 1.0,
            }[unit]
            out["VARIABLE_DECK_LOAD_ST"] = round(value * factor)

    water_ft = _search_number(rf"Water\s+Depth\s+({_NUM})\s*ft", text)
    if water_ft is not None:
        out["WATER_DEPTH_RATING_FT"] = water_ft

    drill_ft = _search_number(rf"Drilling\s+Depth\s+({_NUM})\s*ft", text)
    if drill_ft is not None:
        out["DRILLING_DEPTH_RATING_FT"] = drill_ft

    moonpool = re.search(
        rf"Moonpool\s+({_NUM})\s*ft\.?\s*x\s*({_NUM})\s*ft\.?\s*"
        rf"(?:\(({_NUM})\s*m\s*x\s*({_NUM})\s*m\))?",
        text,
        re.IGNORECASE,
    )
    if moonpool:
        mp_l_ft = _clean_number(moonpool.group(1))
        mp_w_ft = _clean_number(moonpool.group(2))
        if moonpool.group(3):  # metric printed on the sheet
            out["MOONPOOL_LENGTH_M"] = round(_clean_number(moonpool.group(3)), 1)
            out["MOONPOOL_WIDTH_M"] = round(_clean_number(moonpool.group(4)), 1)
        else:
            out["MOONPOOL_LENGTH_M"] = _ft_to_m(mp_l_ft)
            out["MOONPOOL_WIDTH_M"] = _ft_to_m(mp_w_ft)
        out["RAW_MOONPOOL_FT"] = f"{mp_l_ft:g} x {mp_w_ft:g}"

    return out
