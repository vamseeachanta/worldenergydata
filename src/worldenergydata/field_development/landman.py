# ABOUTME: Assemble a per-field landman lease panel from the canonical registry.
# ABOUTME: Ships the leases we can source; missing attributes become grabbable placeholders (#951).
"""
worldenergydata.field_development.landman
=========================================

Build the per-field **Lease & landman** panel for the life-cycle posters and the
Explorer field panel.

What is real (committed data):
  * lease numbers + blocks — ``config/fields.yml`` (the canonical registry, #755);
  * per-lease water depth + development system — the FDAS V30 lease workbook;
  * field-level operator + working-interest partners — ``_facts.json``.

What is NOT in committed data (→ grabbable placeholders linking an ingest issue,
per the owner's 2026-07-11 guidance): lease **status**, **effective/expiration
dates**, **lease type**, **per-lease block**, **per-lease working interest**,
**operator-of-record history**. ``config/fields.yml`` lists ``leases`` and
``area_blocks`` as UNPAIRED parallel lists, so a block is NEVER placed next to an
individual lease (that pairing is one of the deferred placeholders).
"""

from __future__ import annotations

# Attributes the committed data cannot supply yet; each renders as a placeholder
# cell linking the BSEE Lease & Lease-Owner ingest issue.
PENDING_ATTRS = [
    "status",
    "effective_date",
    "expiration_date",
    "lease_type",
    "per_lease_block",
    "per_lease_working_interest",
    "operator_of_record_history",
]


def build_landman(
    field_facts: dict,
    leases: list[str],
    blocks: list[str],
    lease_rows: dict,
    ingest_issue: int,
    block_note: str | None = None,
) -> dict:
    """Return the landman panel dict for one field.

    ``lease_rows`` maps a normalized lease number -> ``{water_depth_ft,
    dev_system, lease_name}`` (from the V30 workbook). ``leases``/``blocks`` are
    the canonical registry lists. Per-lease block is deliberately absent.
    """
    rows = []
    for lease in leases:
        v = lease_rows.get(_norm(lease), {})
        rows.append(
            {
                "lease_num": lease,
                "lease_name": v.get("lease_name"),
                "water_depth_ft": v.get("water_depth_ft"),
                "dev_system": v.get("dev_system"),
            }
        )
    wi = field_facts.get("working_interest") or []
    return {
        "leases": rows,
        "n_leases": len(rows),
        "blocks": list(blocks),
        "block_note": block_note,
        "operator": field_facts.get("operator"),
        "working_interest": wi,  # per-FIELD partner split (real)
        "pending": list(PENDING_ATTRS),
        "ingest_issue": ingest_issue,
    }


def _norm(lease: str) -> str:
    """Normalize a lease number for joining: 'OCS-G 25806' -> 'G25806'.

    Strips the 'OCS-' prefix (keeping the region letter) and all spaces, uppercase.
    """
    return lease.upper().replace("OCS-", "").replace(" ", "").strip()
