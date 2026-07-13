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
    # Dotted/ellipsis leaders ("Flag ...…… Liberia") -> plain wide gap
    text = re.sub(r"[.…]{2,}|…", "  ", text)
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

    # Seadrill same-line table layout — same fill-the-gaps merge.
    for field, value in _parse_seadrill_layout(text).items():
        out.setdefault(field, value)

    # Borr dotted-leader layout — same fill-the-gaps merge.
    for field, value in _parse_borr_layout(text).items():
        out.setdefault(field, value)

    # Shelf Drilling dotted-leader layout — same fill-the-gaps merge.
    for field, value in _parse_shelf_layout(text).items():
        out.setdefault(field, value)

    # Stena dotted-leader layout — same fill-the-gaps merge.
    for field, value in _parse_stena_layout(text).items():
        out.setdefault(field, value)

    # Cross-layout equipment capabilities (#1006) — same fill-the-gaps merge.
    for field, value in _parse_equipment(text).items():
        out.setdefault(field, value)

    return out


def _parse_stena_layout(text: str) -> dict[str, Any]:
    """Parse the Stena Drilling technical-specification layout.

    Dotted-leader UPPERCASE labels (collapsed by ``_normalize``), metric-first
    values with imperial in parentheses::

        DIMENSIONS            228 m (Long) x 42m (Wide) x 19m (moulded depth)
        DRAFTS                12m (39.4 ft) operating / 8.5m (27.9 ft) transit
        MAXIMUM WATER DEPTH   3,000m designed / 3,000m outfitted
                              10,000 ft designed / 10,000 ft outfitted
        HOOKLOAD CAPACITY     [MAIN] 1000st static hookload (2,000,000 lbs)
        MOONPOOL              84ft x 41ft (25.60m x 12.48m)

    The semi variant (Stena Don) drops the ft parentheses and quotes water
    depth as ``650m / 2132ft`` on one line — both forms are handled.
    """
    out: dict[str, Any] = {}

    design = re.search(
        r"RIG\s+TYPE\s*/\s*DESIGN\s{2,}(.+?)(?:\s{3,}|\s*$)", text, re.MULTILINE
    )
    if design:
        out["RIG_DESIGN"] = design.group(1).strip().rstrip("-").strip()

    year = re.search(
        r"SIGNIFICANT\s+UPGRADES\s{2,}(?:[A-Za-z]+\s+)?(\d{4})", text, re.IGNORECASE
    )
    if year:
        out["YEAR_BUILT"] = int(year.group(1))

    flag = re.search(
        r"^\s*FLAG\s{2,}([A-Za-z][A-Za-z ()]*?)(?:\s{3,}|\s*$)", text, re.MULTILINE
    )
    if flag:
        out["FLAG_STATE"] = flag.group(1).strip()

    dims = re.search(
        rf"DIMENSIONS\s{{2,}}({_NUM_TIGHT})\s*m\s*\(Long\)\s*x\s*"
        rf"({_NUM_TIGHT})\s*m\s*\(Wide\)(?:\s*x\s*({_NUM_TIGHT})\s*m)?",
        text,
        re.IGNORECASE,
    )
    if dims:
        out["LOA_M"] = round(_clean_number(dims.group(1)), 1)
        out["BEAM_M"] = round(_clean_number(dims.group(2)), 1)
        if dims.group(3):
            out["DEPTH_M"] = round(_clean_number(dims.group(3)), 1)

    drafts = re.search(
        rf"DRAFTS\s{{2,}}({_NUM_TIGHT})\s*m\s*(?:\(({_NUM_TIGHT})\s*ft\)\s*)?operating\s*/\s*"
        rf"({_NUM_TIGHT})(?:-{_NUM_TIGHT})?\s*m\s*(?:\(({_NUM_TIGHT})\s*ft\)\s*)?transit",
        text,
        re.IGNORECASE,
    )
    if drafts:
        out["DRAFT_M"] = round(_clean_number(drafts.group(1)), 1)
        if drafts.group(2):
            out["RAW_DRAFT_OPERATING_FT"] = _clean_number(drafts.group(2))
        if drafts.group(4):
            out["RAW_DRAFT_TRANSIT_FT"] = _clean_number(drafts.group(4))

    vdl = re.search(
        rf"VARIABLE\s+DECK(?:\s+LOAD)?\s*(?:\(OPERATING\))?\s{{2,}}({_NUM_TIGHT})\s*Mt\b",
        text,
        re.IGNORECASE,
    )
    if vdl:
        value = _clean_number(vdl.group(1))
        if value is not None:
            out["VARIABLE_DECK_LOAD_ST"] = round(value * SHORT_TONS_PER_TONNE)

    water = re.search(
        rf"MAXIMUM\s+WATER\s+DEPTH\s{{2,}}({_NUM_TIGHT})\s*m\s*"
        rf"(?:designed(?:[^\n]*\n){{1,2}}\s*({_NUM_TIGHT})\s*ft|/\s*({_NUM_TIGHT})\s*ft)",
        text,
        re.IGNORECASE,
    )
    if water:
        ft = _clean_number(water.group(2) or water.group(3))
        if ft is not None:
            out["WATER_DEPTH_RATING_FT"] = ft

    drilling = re.search(
        rf"MAXIMUM\s+DRILLING\s+DEPTH\s{{2,}}({_NUM_TIGHT})\s*m\s*/\s*({_NUM_TIGHT})\s*ft",
        text,
        re.IGNORECASE,
    )
    if drilling:
        out["DRILLING_DEPTH_RATING_FT"] = _clean_number(drilling.group(2))

    hook = re.search(
        rf"HOOKLOAD\s+CAPACITY\s{{2,}}(?:\[MAIN\]\s*)?({_NUM_TIGHT})\s*(?:st\b|short\s+ton)",
        text,
        re.IGNORECASE,
    )
    if hook:
        value = _clean_number(hook.group(1))
        if value is not None:
            out["HOOKLOAD_RATING_KIPS"] = round(value * KIPS_PER_SHORT_TON)

    moonpool = re.search(
        rf"MOONPOOL\s{{2,}}({_NUM_TIGHT})\s*ft\s*x\s*({_NUM_TIGHT})\s*ft\s*"
        rf"\(({_NUM_TIGHT})\s*m\s*x\s*({_NUM_TIGHT})\s*m\)",
        text,
        re.IGNORECASE,
    )
    if moonpool:
        mp_l_ft = _clean_number(moonpool.group(1))
        mp_w_ft = _clean_number(moonpool.group(2))
        out["MOONPOOL_LENGTH_M"] = round(_clean_number(moonpool.group(3)), 1)
        out["MOONPOOL_WIDTH_M"] = round(_clean_number(moonpool.group(4)), 1)
        out["RAW_MOONPOOL_FT"] = f"{mp_l_ft:g} x {mp_w_ft:g}"

    return out


def _parse_equipment(text: str) -> dict[str, Any]:
    """Extract equipment-level capabilities common to all sheet layouts (#1006).

    - QUARTERS_CAPACITY: "Quarters Capacity: 230" / "Accommodation ... 220
      persons" variants.
    - MPD_CAPABLE / DUAL_ACTIVITY: set to True only on positive mention;
      absent otherwise (unknown != false — a sheet that doesn't mention MPD
      proves nothing).
    - CRANE_MAIN_CAPACITY_T: the largest tonnage found on crane-labelled
      lines (st converted to tonnes; T/mt taken as tonnes). Derrick and
      tensioner lines are never scanned.
    """
    out: dict[str, Any] = {}

    quarters = re.search(
        rf"(?:Quarters\s*(?:Capacity)?\s*:?|Accom+odations?\s*:?)"  # vendor sheets misspell it
        rf"[ \t.…]*\n?[ \t]*(\d{{2,3}})\b\s*(?:persons|people|POB)?",
        text,
        re.IGNORECASE,
    )
    if quarters:
        value = _clean_number(quarters.group(1))
        # Plausibility window: crew capacity, not a load or a year.
        if value is not None and 20 <= value <= 400:
            out["QUARTERS_CAPACITY"] = int(value)

    if re.search(r"\bMPD\b|managed[- ]pressure", text, re.IGNORECASE):
        out["MPD_CAPABLE"] = True

    if re.search(
        r"dual[- ](?:activity|derrick|hoisting)|dual bottleneck", text, re.IGNORECASE
    ):
        out["DUAL_ACTIVITY"] = True

    best_t: Optional[float] = None
    for line in text.split("\n"):
        if not re.search(r"crane", line, re.IGNORECASE):
            continue
        # Column collapse can merge adjacent equipment onto a crane line —
        # skip derrick/tensioner/tree-trolley content, and cap at 600 t
        # (largest observed real crane: 595 T gantry).
        if re.search(r"derrick|tensioner|trolley|tree", line, re.IGNORECASE):
            continue
        for m in re.finditer(rf"({_NUM_TIGHT})\s*(sT|st|mt|MT|T)\b", line):
            value = _clean_number(m.group(1))
            if value is None or not (5 <= value <= 600):
                continue
            unit = m.group(2).lower()
            tonnes = value * 0.907185 if unit == "st" else value
            if best_t is None or tonnes > best_t:
                best_t = tonnes
    if best_t is not None:
        out["CRANE_MAIN_CAPACITY_T"] = round(best_t, 1)

    return out


def _parse_shelf_layout(text: str) -> dict[str, Any]:
    """Parse the Shelf Drilling jackup spec-sheet layout (post dot-collapse)::

        Year Built / Last Upgrade      2008/2023
        Hull Dimensions                239.8 ft. x 224.4 ft. x 28 ft.
        Legs (3)                       506 ft. long triangular legs
        Cantilever Envelope            70 ft. by 30 ft.
        Max Variable Load (drilling)   Approx. 7,500 kips*

    Derrick hookload appears in prose ("static hook load capacity
    1,600,000 lbs."). Loads in kips/lbs.
    """
    out: dict[str, Any] = {}

    year = re.search(
        r"Year\s+Built\s*/\s*Last\s+Upgrade\s{2,}(\d{4})", text, re.IGNORECASE
    )
    if year:
        out["YEAR_BUILT"] = int(year.group(1))

    dims = re.search(
        rf"Hull\s+Dimensions\s{{2,}}({_NUM_TIGHT})\s*ft\.?\s*x\s*"
        rf"({_NUM_TIGHT})\s*ft\.?\s*x\s*({_NUM_TIGHT})\s*ft",
        text,
        re.IGNORECASE,
    )
    if dims:
        loa_ft = _clean_number(dims.group(1))
        beam_ft = _clean_number(dims.group(2))
        depth_ft = _clean_number(dims.group(3))
        out["LOA_M"] = _ft_to_m(loa_ft)
        out["BEAM_M"] = _ft_to_m(beam_ft)
        out["DEPTH_M"] = _ft_to_m(depth_ft)
        out["RAW_DIMENSIONS_FT"] = f"{loa_ft:g} x {beam_ft:g} x {depth_ft:g}"

    legs = re.search(
        rf"^\s*Legs\s*(?:\(\d+\))?\s{{2,}}({_NUM_TIGHT})\s*ft",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if legs:
        out["LEG_LENGTH_FT"] = _clean_number(legs.group(1))

    cantilever = re.search(
        rf"Cantilever\s+Envelope\s{{2,}}({_NUM_TIGHT})\s*ft\.?\s*(?:x|by)\s*"
        rf"({_NUM_TIGHT})\s*ft",
        text,
        re.IGNORECASE,
    )
    if cantilever:
        out["CANTILEVER_REACH_FT"] = _clean_number(cantilever.group(1))

    vdl = re.search(
        rf"Max\.?\s+Variable\s+Load[^\n]*?\s{{2,}}(?:Approx\.?\s*)?({_NUM_TIGHT})\s*kips",
        text,
        re.IGNORECASE,
    )
    if vdl:
        value = _clean_number(vdl.group(1))
        if value is not None:
            out["VARIABLE_DECK_LOAD_ST"] = round(value / KIPS_PER_SHORT_TON)

    hook = re.search(
        rf"hook\s+load\s+capacity\s+(?:of\s+)?({_NUM_TIGHT})\s*lbs",
        text,
        re.IGNORECASE,
    )
    if hook:
        value = _clean_number(hook.group(1))
        if value is not None:
            out["HOOKLOAD_RATING_KIPS"] = round(value / 1000)

    return out


def _parse_borr_layout(text: str) -> dict[str, Any]:
    """Parse the Borr Drilling dotted-leader jackup layout.

    Dotted leaders are collapsed to wide gaps by ``_normalize`` first::

        Delivery                2019
        Overall Dimensions      247 ft long x 230 ft wide x 27 ft deep
        Drafts                  19 ft load line draft
        Load Line Displacement  41,625.45 kips
        Variable Deck           9,700 kips elevated / 5,500 kips field transit
        Cantilever              75 ft reach aft of transom

    Displacement and deck loads are quoted in kips (converted).
    """
    out: dict[str, Any] = {}

    delivery = re.search(r"^\s*Delivery\s{2,}(\d{4})\b", text, re.MULTILINE)
    if delivery:
        out["YEAR_BUILT"] = int(delivery.group(1))

    dims = re.search(
        rf"Overall\s+Dimensions\s{{2,}}({_NUM_TIGHT})\s*ft\.?\s*long\s*x\s*"
        rf"({_NUM_TIGHT})\s*ft\.?\s*wide\s*x\s*({_NUM_TIGHT})\s*ft\.?\s*deep",
        text,
        re.IGNORECASE,
    )
    if dims:
        loa_ft = _clean_number(dims.group(1))
        beam_ft = _clean_number(dims.group(2))
        depth_ft = _clean_number(dims.group(3))
        out["LOA_M"] = _ft_to_m(loa_ft)
        out["BEAM_M"] = _ft_to_m(beam_ft)
        out["DEPTH_M"] = _ft_to_m(depth_ft)
        out["RAW_DIMENSIONS_FT"] = f"{loa_ft:g} x {beam_ft:g} x {depth_ft:g}"

    draft = re.search(
        rf"^\s*Drafts?\s{{2,}}({_NUM_TIGHT})\s*ft\.?\s*(?:at\s+)?(load\s*line|transit)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if draft:
        draft_ft = _clean_number(draft.group(1))
        if "transit" in draft.group(2).lower():
            out["RAW_DRAFT_TRANSIT_FT"] = draft_ft
        else:
            out["DRAFT_M"] = _ft_to_m(draft_ft)
            out["RAW_DRAFT_OPERATING_FT"] = draft_ft

    displacement = re.search(
        rf"^\s*(?:Load\s+Line\s+)?Displacement\s{{2,}}({_NUM_TIGHT})\s*(kips|MT)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if displacement:
        value = _clean_number(displacement.group(1))
        if value is not None:
            if displacement.group(2).lower() == "kips":
                value = value / KIPS_PER_SHORT_TON / SHORT_TONS_PER_TONNE
            out["DISPLACEMENT_TONNES"] = round(value)

    vdl = re.search(
        rf"^\s*Variable\s+Deck\s{{2,}}({_NUM_TIGHT})\s*(kips|MT)\s*(?:elevated|operating)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if vdl:
        value = _clean_number(vdl.group(1))
        if value is not None:
            factor = (
                1 / KIPS_PER_SHORT_TON
                if vdl.group(2).lower() == "kips"
                else SHORT_TONS_PER_TONNE
            )
            out["VARIABLE_DECK_LOAD_ST"] = round(value * factor)

    water_ft = _search_number(
        rf"Operating\s+Water\s+Depth\s{{2,}}({_NUM_TIGHT})\s*ft", text
    )
    if water_ft is not None:
        out["WATER_DEPTH_RATING_FT"] = water_ft

    # "75 ft reach aft of transom" / "75 ft / 15 ft Port & 15 ft Stbd" —
    # the first ft value on the Cantilever line is the aft reach.
    cantilever = re.search(
        rf"^\s*Cantilever[^\n]*?\s{{2,}}({_NUM_TIGHT})\s*ft\b",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if cantilever:
        out["CANTILEVER_REACH_FT"] = _clean_number(cantilever.group(1))

    hook = re.search(
        rf"^\s*Hookload\s+Capacity\s{{2,}}({_NUM_TIGHT})\s*lbs",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if hook:
        value = _clean_number(hook.group(1))
        if value is not None:
            out["HOOKLOAD_RATING_KIPS"] = round(value / 1000)

    return out


def _parse_seadrill_layout(text: str) -> dict[str, Any]:
    """Parse the Seadrill 'GENERAL (U.S.)' same-line table layout.

    Label and value share a line, separated by a wide gap; a metric duplicate
    block follows the U.S. block (first match wins, so U.S. values are used)::

        Built                2014 Samsung, South Korea
        Dimensions           748 ft x 137 ft            (jackups add x depth)
        Draft                27.9 ft (transit) 39.4 ft (operating)
        Variable Load        18,150 st (transit) 22,000 st (drilling)
        Legs                 3 x 673 ft / 581 ft usable

    Loads/displacement are quoted in short tons.
    """
    out: dict[str, Any] = {}

    built = re.search(r"^\s*Built\s{2,}(\d{4})\b", text, re.MULTILINE)
    if built:
        out["YEAR_BUILT"] = int(built.group(1))

    design = re.search(r"^\s*Design\s{2,}(.+?)(?:\s{3,}|\s*$)", text, re.MULTILINE)
    if design:
        out["RIG_DESIGN"] = design.group(1).strip()

    flag = re.search(r"^\s*Flag/Class\s{2,}([A-Za-z ]+?)\s*/", text, re.MULTILINE)
    if flag:
        out["FLAG_STATE"] = flag.group(1).strip()

    dims = re.search(
        rf"^\s*Dimensions\s{{2,}}({_NUM_TIGHT})\s*ft\s*x\s*({_NUM_TIGHT})\s*ft"
        rf"(?:\s*x\s*({_NUM_TIGHT})\s*ft)?",
        text,
        re.MULTILINE,
    )
    if dims:
        loa_ft = _clean_number(dims.group(1))
        beam_ft = _clean_number(dims.group(2))
        out["LOA_M"] = _ft_to_m(loa_ft)
        out["BEAM_M"] = _ft_to_m(beam_ft)
        out["RAW_DIMENSIONS_FT"] = f"{loa_ft:g} x {beam_ft:g}"
        if dims.group(3):
            depth_ft = _clean_number(dims.group(3))
            out["DEPTH_M"] = _ft_to_m(depth_ft)
            out["RAW_DIMENSIONS_FT"] += f" x {depth_ft:g}"

    draft_line = re.search(r"^\s*Draft\s{2,}([^\n]+)", text, re.MULTILINE)
    if draft_line:
        line = draft_line.group(1)
        operating = re.search(
            rf"({_NUM_TIGHT})\s*ft\s*\((?:operating|loadline)\)", line, re.IGNORECASE
        )
        transit = re.search(rf"({_NUM_TIGHT})\s*ft\s*\(transit\)", line, re.IGNORECASE)
        if operating:
            op_ft = _clean_number(operating.group(1))
            out["DRAFT_M"] = _ft_to_m(op_ft)
            out["RAW_DRAFT_OPERATING_FT"] = op_ft
        if transit:
            out["RAW_DRAFT_TRANSIT_FT"] = _clean_number(transit.group(1))

    displacement = re.search(
        rf"^\s*Displacement\s{{2,}}({_NUM_TIGHT})\s*st\b", text, re.MULTILINE
    )
    if displacement:
        value = _clean_number(displacement.group(1))
        if value is not None:
            out["DISPLACEMENT_TONNES"] = round(value / SHORT_TONS_PER_TONNE)

    vdl_line = re.search(r"^\s*Variable\s+Load\s{2,}([^\n]+)", text, re.MULTILINE)
    if vdl_line:
        line = vdl_line.group(1)
        drilling = re.search(
            rf"({_NUM_TIGHT})\s*st\s*\(?drilling\)?", line, re.IGNORECASE
        )
        any_st = re.search(rf"({_NUM_TIGHT})\s*st\b", line, re.IGNORECASE)
        pick = drilling or any_st
        if pick:
            value = _clean_number(pick.group(1))
            if value is not None:
                out["VARIABLE_DECK_LOAD_ST"] = round(value)

    legs = re.search(
        rf"^\s*Legs\s{{2,}}(?:\(?\d+\)?\s*x?\s*)?({_NUM_TIGHT})\s*ft",
        text,
        re.MULTILINE,
    )
    if legs:
        out["LEG_LENGTH_FT"] = _clean_number(legs.group(1))

    spud = re.search(rf"^\s*Spud\s+Cans\s{{2,}}({_NUM_TIGHT})\s*ft", text, re.MULTILINE)
    if spud:
        out["SPUD_CAN_DIAMETER_FT"] = _clean_number(spud.group(1))

    cantilever = re.search(
        rf"Cantilever\s+Envelope\s{{2,}}({_NUM_TIGHT})\s*ft\s*x\s*({_NUM_TIGHT})\s*ft",
        text,
        re.IGNORECASE,
    )
    if cantilever:
        out["CANTILEVER_REACH_FT"] = _clean_number(cantilever.group(1))

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

    # Stop at a 3+ space gap — other layouts put a second column on the line.
    design = re.search(r"^\s*Design\s{2,}(.+?)(?:\s{3,}|\s*$)", text, re.MULTILINE)
    if design:
        out["RIG_DESIGN"] = design.group(1).strip()

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
