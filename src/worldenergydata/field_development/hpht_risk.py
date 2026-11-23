# ABOUTME: Classify a field's reservoir facts into an HPHT underwriting signal.
# ABOUTME: Side-effect-free; drives the HPHT risk badge on the life-cycle posters (#949).
"""
worldenergydata.field_development.hpht_risk
===========================================

Derive an HPHT (high-pressure / high-temperature) underwriting badge from the
per-field ``reservoir`` block already curated in
``reports/lower_tertiary/lifecycle/_facts.json``.

The signal an underwriter cares about is **reservoir pore pressure vs the
installed equipment rating** — e.g. Anchor's 25,000-psi reservoir against
20,000-psi equipment (+25%). That exceedance is only meaningful when the
pressure figure is a reservoir pore pressure; a *subsea-system* pressure (a
tree/HIPPS rating, as for Julia) is NOT reservoir-vs-equipment and must not be
rendered as an exceedance (``pressure_basis == "subsea_system"``).
"""

from __future__ import annotations

# Severity buckets, most-to-least severe.
OVER_RATING = "over-rating"  # reservoir pressure exceeds equipment rating
AT_RATING = "at-rating"  # reservoir pressure equals equipment rating
WITHIN = "within"  # reservoir pressure below equipment rating
CLASS_ONLY = "class-only"  # HPHT class known, no reservoir-vs-equipment pair


def classify_hpht(reservoir: dict | None) -> dict | None:
    """Return an HPHT badge dict, or ``None`` when there is no HPHT signal.

    ``None`` when the field has neither a pressure nor an HPHT class (e.g. Big
    Foot). Otherwise a dict with ``class``, ``pressure_psi``,
    ``equip_rating_psi``, ``exceedance_pct`` (or ``None``), ``severity``,
    ``basis`` and a human ``label``.
    """
    if not reservoir:
        return None
    hpht_class = reservoir.get("hpht_class")
    pressure = reservoir.get("pressure_psi")
    equip = reservoir.get("equip_rating_psi")
    if hpht_class is None and pressure is None:
        return None

    basis = reservoir.get("pressure_basis") or "reservoir"
    exceedance = None
    severity = CLASS_ONLY
    # Exceedance is only a reservoir-vs-equipment statement when BOTH values are
    # present AND the pressure is a reservoir pore pressure (not a system rating).
    if pressure is not None and equip and basis == "reservoir":
        exceedance = round((pressure - equip) / equip * 100)
        if exceedance > 0:
            severity = OVER_RATING
        elif exceedance == 0:
            severity = AT_RATING
        else:
            severity = WITHIN

    label = _label(hpht_class, pressure, equip, exceedance, severity, basis)
    return {
        "class": hpht_class,
        "pressure_psi": pressure,
        "equip_rating_psi": equip,
        "exceedance_pct": exceedance,
        "severity": severity,
        "basis": basis,
        "label": label,
    }


def _k(psi: int) -> str:
    """20000 -> '20k', 13500 -> '13.5k', 19374 -> '19.4k'."""
    return f"{round(psi / 1000, 1):g}k"


def _label(hpht_class, pressure, equip, exceedance, severity, basis) -> str:
    cls = hpht_class or "HPHT"
    if severity in (OVER_RATING, AT_RATING, WITHIN):
        sign = "+" if exceedance > 0 else ""
        return f"{cls} · {_k(pressure)} vs {_k(equip)} psi ({sign}{exceedance}%)"
    if basis == "subsea_system" and pressure is not None:
        rating = f" / {_k(equip)}-psi trees" if equip else ""
        return f"{cls} · subsea system {_k(pressure)}{rating}"
    if pressure is not None:
        return f"{cls} · {_k(pressure)} psi"
    if equip is not None:
        return f"{cls} · {_k(equip)}-psi equipment"
    return cls
