# ABOUTME: Match a field to its facility decommissioning liability figure.
# ABOUTME: Side-effect-free; drives the decommissioning risk badge on the posters (#949).
"""
worldenergydata.field_development.decommission_risk
===================================================

Surface the per-facility decommissioning liability already modeled in
``reports/decommissioning/regional_liability.csv`` as a per-field underwriting
signal, by matching a curated facility name.

HONESTY (per the #949 review):
  * This is **facility removal** liability, NOT well-plugging (P&A). Per-field
    well-plugging counts are not attributable (BSEE ``well_data.csv`` has no
    lease column and only 23 shelf field codes, none Lower Tertiary).
  * The source CSV flags "FPSO base low-confidence": an FPSO/FPU facility
    carries a flat placeholder cost, so its estimate is ``confidence="low"``;
    a depth-differentiated host (e.g. Big Foot's Mini-TLP) is ``"modeled"``.
"""

from __future__ import annotations

BASIS = "facility removal (not well P&A)"


def classify_decommissioning(
    facility_name: str | None, rows: list[dict]
) -> dict | None:
    """Return a decommissioning badge dict for ``facility_name``, or ``None``.

    ``rows`` are the parsed ``regional_liability.csv`` records (dicts with
    ``facility_name``, ``cost_musd``, ``host_type``). Matching is exact on the
    curated facility name.
    """
    if not facility_name:
        return None
    match = next((r for r in rows if r.get("facility_name") == facility_name), None)
    if match is None:
        return None
    host = (match.get("host_type") or "").upper()
    low = "FPSO" in host or "FPU" in host or "FPS" in host
    try:
        cost = round(float(match["cost_musd"]), 1)
    except (TypeError, ValueError, KeyError):
        return None
    return {
        "cost_musd": cost,
        "host_type": match.get("host_type"),
        "confidence": "low" if low else "modeled",
        "basis": BASIS,
        "label": f"Decommission ~${cost:g}M" + (" (FPSO base)" if low else ""),
    }
