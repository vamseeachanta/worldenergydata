"""Project existing field panels into availability metadata without recalculation.

Pass a registry returned by ``load_fields`` and one Explorer field payload.
Regions are registry labels, not inferred onshore/offshore classifications.
No result values are returned and no source object is changed. This describes
source evidence only; it is not a financial, risk or ownership conclusion.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from worldenergydata.field_development.landman import PENDING_ATTRS

if TYPE_CHECKING:
    from worldenergydata.common.fields_registry import FieldsRegistry

_CONTRACTS = {
    "economics": "scripts/hf_export/publish_explorer_refresh_to_hf.py#_released_economics",
    "underwriting": "scripts/lower_tertiary/build_lifecycle_posters.py#facts_to_field",
    "landman": "src/worldenergydata/field_development/landman.py#build_landman",
}
_ECON_LEVELS = ("npv_mm", "breakeven_wti", "sens_mm_per_dollar")
_WITHHELD = ("withheld", "withheld_pending_redistribution_review")
# Lifecycle statuses emitted by build_lifecycle_posters.STATUS. Older payloads
# omit this key; any other explicit status suppresses stale panel evidence.
_PAYLOAD_STATUSES = (
    "producing",
    "execution",
    "sanctioned",
    "appraisal",
    "select",
    "explore",
    "abandoned",
)


def _state(status, missing=(), reason=None):
    return {"status": status, "missing_dimensions": list(missing), "reason": reason}


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _blocked_records(status, reason):
    records = {name: _state(status, (name,), reason) for name in _CONTRACTS}
    records["underwriting"]["subpanels"] = {
        name: _state(status, (name,), reason) for name in ("hpht", "decommissioning")
    }
    return records


def _finite(value):
    return not isinstance(value, bool) and (
        isinstance(value, int) or isinstance(value, float) and math.isfinite(value)
    )


def _economics(performance):
    status = performance.get("economics_status")
    if status in (*_WITHHELD, "early_life"):
        return _state("withheld", ("economics_status",), "source_status")
    if status != "surfaced":
        return _state("unavailable", ("economics_status",), "source_status")
    missing = []
    if performance.get("economics_basis") != "life_to_date_pretax_npv_at_10pct":
        missing.append("economics_basis")
    missing.extend(key for key in _ECON_LEVELS if not _finite(performance.get(key)))
    return (
        _state("unavailable", missing, "incomplete_evidence")
        if missing
        else _state("available")
    )


def _hpht(badge):
    severity = badge.get("severity")
    classification = badge.get("class")
    if badge.get("basis") not in ("reservoir", "subsea_system"):
        return _state("unavailable", ("basis",), "unsupported_basis")
    if severity == "class-only" and (
        isinstance(classification, str)
        and classification.strip()
        or _finite(badge.get("pressure_psi"))
    ):
        return _state("partial", ("reservoir_equipment_comparison",), "class_only")
    if severity not in ("within", "at-rating", "over-rating"):
        return _state("unavailable", ("severity",), "unknown_or_absent_signal")
    missing = [
        key
        for key in ("pressure_psi", "equip_rating_psi", "exceedance_pct")
        if not _finite(badge.get(key))
    ]
    if badge.get("basis") != "reservoir":
        missing.append("reservoir_basis")
    return (
        _state("unavailable", missing, "incomplete_evidence")
        if missing
        else _state("available")
    )


def _decommissioning(risk):
    # Older producers omit the status; only that legacy shape uses the badge.
    if "decommissioning_status" in risk:
        status = risk["decommissioning_status"]
        return _state(
            "withheld" if status in _WITHHELD else "unavailable",
            ("decommissioning_status",),
            "source_status",
        )
    badge = _mapping(risk.get("decommissioning"))
    missing = []
    if not _finite(badge.get("cost_musd")):
        missing.append("facility_removal_cost")
    if badge.get("basis") != "facility removal (not well P&A)":
        missing.append("basis")
    if badge.get("confidence") not in ("low", "modeled"):
        missing.append("confidence")
    return (
        _state("unavailable", missing, "incomplete_evidence")
        if missing
        else _state("available")
    )


def _underwriting(risk):
    panels = {
        "hpht": _hpht(_mapping(risk.get("hpht"))),
        "decommissioning": _decommissioning(risk),
    }
    states = [panel["status"] for panel in panels.values()]
    if all(status == "available" for status in states):
        status = "available"
    elif any(status in ("available", "partial") for status in states):
        status = "partial"
    else:
        status = "withheld" if "withheld" in states else "unavailable"
    record = _state(
        status,
        (name for name, panel in panels.items() if panel["status"] != "available"),
        None if status == "available" else "subpanel_states",
    )
    return {**record, "subpanels": panels}


def _landman(panel):
    leases = panel.get("leases")
    if (
        not isinstance(leases, list)
        or not leases
        or not all(
            isinstance(row, dict)
            and isinstance(row.get("lease_num"), str)
            and row["lease_num"].strip()
            for row in leases
        )
    ):
        return _state("unavailable", ("lease_identifiers",), "absent_identifiers")
    # The current producer explicitly defers these attributes for every lease.
    return _state("partial", PENDING_ATTRS, "pending_attributes")


def lens_availability(
    canonical_id: str, payload: dict | None, *, registry: FieldsRegistry
) -> dict:
    """Return economics, underwriting and landman records in stable order.

    Unknown canonical ids and supplied payloads with absent or inconsistent ids
    raise ValueError. An absent payload is unavailable. Explicit withholding
    takes precedence over stale values; explicit statuses outside the producer's
    lifecycle statuses fail closed. Legacy payloads may omit status. Each risk
    subpanel keeps its own state, including when the payload is absent or blocked.
    Lease ids establish only partial availability:
    the existing producer defers status, dates and per-lease ownership details.
    """
    field = registry.by_id(canonical_id)
    if field is None:
        raise ValueError("Unknown canonical id")
    if payload is not None and payload.get("id") != canonical_id:
        raise ValueError("Payload identity does not match canonical id")
    if payload is None:
        records = _blocked_records("unavailable", "absent_payload")
    elif payload.get("status") in _WITHHELD:
        records = _blocked_records("withheld", "source_status")
    elif "status" in payload and payload["status"] not in _PAYLOAD_STATUSES:
        records = _blocked_records("unavailable", "source_status")
    else:
        records = {
            "economics": _economics(_mapping(payload.get("performance"))),
            "underwriting": _underwriting(_mapping(payload.get("risk"))),
            "landman": _landman(_mapping(payload.get("landman"))),
        }
    return {
        name: {
            "canonical_id": canonical_id,
            "region": field.region,
            **record,
            "source_contract": _CONTRACTS[name],
        }
        for name, record in records.items()
    }
