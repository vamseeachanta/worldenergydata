"""Parser for myshiptracking.com per-vessel particulars pages (#988).

The vessel page carries a particulars table of ``<th>Label</th><td>value</td>``
rows (IMO, MMSI, Flag, Size "L x B m", GT, DWT, Build). AIS-reported values
(current draught, speeds) are deliberately NOT extracted — they describe the
vessel's state, not its design particulars.

Pages are keyed by MMSI + IMO only (the name slug is ignored by the site):
``https://www.myshiptracking.com/vessels/<any-slug>-mmsi-<MMSI>-imo-<IMO>``
"""

from __future__ import annotations

import re
from typing import Any, Optional

_ROW = re.compile(
    r"<th[^>]*>\s*([^<]{2,30}?)\s*</th>\s*<td[^>]*>(.{0,160}?)</td>",
    re.DOTALL,
)
_TAG = re.compile(r"<[^>]+>")


def vessel_url(mmsi: int | str, imo: int | str, name: str = "vessel") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or "vessel"
    return f"https://www.myshiptracking.com/vessels/{slug}-mmsi-{mmsi}-imo-{imo}"


def _number(raw: str) -> Optional[float]:
    m = re.search(r"[\d][\d,]*(?:\.\d+)?", raw)
    if not m:
        return None
    return float(m.group(0).replace(",", ""))


def parse_particulars_html(html: str) -> dict[str, Any]:
    """Extract design particulars into schema-compatible fields.

    Absent labels are omitted (never None-filled); a page without an IMO row
    is treated as a miss and returns {} — the site serves a generic shell for
    unknown vessels.
    """
    pairs: dict[str, str] = {}
    for label, value in _ROW.findall(html):
        clean = _TAG.sub("", value).strip()
        if clean and label not in pairs:
            pairs[label] = clean

    if "IMO" not in pairs:
        return {}

    out: dict[str, Any] = {}
    if pairs.get("IMO"):
        out["IMO_NUMBER"] = pairs["IMO"]
    if pairs.get("MMSI"):
        out["MMSI"] = pairs["MMSI"]
    if pairs.get("Flag"):
        out["FLAG_STATE"] = pairs["Flag"]

    size = pairs.get("Size", "")
    m = re.search(r"([\d.]+)\s*x\s*([\d.]+)\s*m", size)
    if m:
        out["LOA_M"] = float(m.group(1))
        out["BEAM_M"] = float(m.group(2))

    gt = _number(pairs.get("GT", ""))
    if gt:
        out["GROSS_TONNAGE"] = gt
    dwt = _number(pairs.get("DWT", ""))
    if dwt:
        out["DEADWEIGHT_TONNES"] = dwt

    build = re.search(r"\b(19|20)\d{2}\b", pairs.get("Build", ""))
    if build:
        out["YEAR_BUILT"] = int(build.group(0))

    return out
