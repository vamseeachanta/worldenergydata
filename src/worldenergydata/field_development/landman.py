# ABOUTME: Assemble a per-field landman lease panel from the canonical registry.
# ABOUTME: Joins verified lease snapshots without inferring missing dates or interests.
"""
worldenergydata.field_development.landman
=========================================

Build the per-field **Lease & landman** panel for the life-cycle posters and the
Explorer field panel.

What is real (committed data):
  * lease numbers + blocks — ``config/fields.yml`` (the canonical registry, #755);
  * per-lease water depth + development system — the FDAS V30 lease workbook;
  * field-level operator + working-interest partners — ``_facts.json``.

The optional BSEE snapshot supplies status, dates, paired area/block and
group-specific assignment interests. Registry blocks remain unpaired; they
never fill a missing per-lease block. Unknown values carry explicit reasons.
"""

from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path

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


def load_lease_snapshot(directory: Path) -> dict:
    """Read panel inputs only after checking the committed extraction digests.

    BSEE Lease Data / Lease Owner layouts, retrieved 2026-10-20:
    https://www.data.bsee.gov/Main/HtmlPage.aspx?page=leaseData
    https://www.data.bsee.gov/Main/HtmlPage.aspx?page=leaseOwner
    Values retain their source units and codes; no engineering limits are used.
    """
    manifest = json.loads((directory / "extract_manifest.json").read_text())
    source_bytes = (directory / "source_manifest.json").read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != manifest["source_manifest_sha256"]:
        raise ValueError("Lease source manifest digest mismatch")
    artifacts = {r["file"]: r for r in manifest["artifacts"]}
    tables = {}
    for name in ("leases", "panel_values", "operators"):
        record = artifacts[f"{name}.json"]
        content = (directory / f"{name}.json").read_bytes()
        if (
            hashlib.sha256(content).hexdigest() != record["sha256"]
            or len(content) != record["size_bytes"]
        ):
            raise ValueError(f"Lease snapshot digest mismatch: {name}")
        tables[name] = json.loads(content)

    def indexed(rows: list[dict]) -> dict:
        result = {}
        for row in rows:
            key = _norm(row["lease_num"])
            if key in result:
                raise ValueError("Duplicate normalized lease in snapshot")
            result[key] = row
        return result

    panels = indexed(tables["panel_values"])
    leases = indexed(tables["leases"])
    if leases.keys() != panels.keys():
        raise ValueError("Lease and panel snapshot identifiers differ")
    history: dict[str, list[dict]] = {}
    for row in tables["operators"]:
        history.setdefault(_norm(row["LEASE_NUMBER"]), []).append(row)
    sources = json.loads(source_bytes)["files"]
    return {
        "leases": {
            key: {
                **row,
                **panels[key],
                "operator_of_record_history": history.get(key, []),
            }
            for key, row in leases.items()
        },
        "source": {
            "source_manifest_sha256": manifest["source_manifest_sha256"],
            "retrieved_at_utc": sorted({r["retrieved_at_utc"] for r in sources}),
            "source_urls": sorted({r["source_url"] for r in sources}),
            "source_vintage": None,
            "freshness_status": "unknown",
            "freshness_reason": "Retrieval time does not establish database freshness",
        },
    }


def _lease_details(source: dict) -> dict:
    """Keep actual/expected dates and partial-assignment records independent."""
    values = {
        "status": source.get("status"),
        "effective_date": source.get("effective_date"),
        "approval_date": source.get("approval_date"),
        "expiration_date": source.get("expiration_date"),
        "expected_expiration_date": source.get("expected_expiration_date"),
        "lease_type": None,
        "per_lease_block": source.get("area_block") or None,
        "per_lease_working_interest": source.get("current_owners", []),
        "operator": source.get("operator", []),
        "current_operators": source.get("current_operators", []),
        "operator_of_record_history": source.get("operator_of_record_history", []),
        "royalty_system": source.get("royalty_system"),
    }
    missing = {
        key: "Not reported in the lease snapshot"
        for key, value in values.items()
        if value is None or value == [] or value == ""
    }
    missing["lease_type"] = "Lease type is not mapped by this extract"
    for key, reason_key in (
        ("expiration_date", "expiration_reason"),
        ("per_lease_working_interest", "owner_reason"),
        ("operator", "operator_reason"),
    ):
        if key in missing and source.get(reason_key):
            missing[key] = source[reason_key]
    return {**values, "missing": missing}


def _text(value: object, reason: str = "Not reported") -> str:
    return escape(str(value) if value is not None and value != "" else reason)


def _interest_html(owners: list[dict], reason: str) -> str:
    lines = []
    for owner in owners:
        # Lease Owner layout: percentage ownership depends on group and aliquot.
        # Preserve source percentages verbatim; do not sum or normalize them.
        identity = (
            f"{owner.get('SN_LSE_OWNER') or 'not reported'} / "
            f"group {owner.get('OWNER_GROUP_CODE') or 'not reported'}"
            f" / aliquot {owner.get('OWNER_ALIQUOT_CD') or 'not reported'}"
        )
        name = owner.get("owner_name") or owner.get("owner_name_reason")
        pct = owner.get("ASSIGNMENT_PCT")
        interest = f"{pct}%" if pct is not None else "Interest not reported"
        lines.append(
            f"{_text(identity)} / {_text(name)}: {_text(interest)}"
            f" (assignment approved {_text(owner.get('ASGN_APRV_DATE'))})"
        )
    return "<br>".join(lines) if lines else _text(None, reason)


def render_lease_table(panel: dict) -> str:
    """One escaped table shared by the poster and Explorer, built offline."""
    headers = (
        "Lease",
        "Water depth (ft)",
        "Development system",
        "Area/block",
        "Status code",
        "Effective",
        "Actual expiration",
        "Expected expiration",
        "Owner assignment interest (%)",
        "Designated operator",
        "Royalty bid-system code",
    )
    rows = []
    for row in panel["leases"]:
        missing = row["missing"]
        cells = [
            _text(row["lease_num"]),
            _text(row.get("water_depth_ft")),
            _text(row.get("dev_system")),
        ]
        cells.extend(
            _text(row[key], missing.get(key, "Not reported"))
            for key in (
                "per_lease_block",
                "status",
                "effective_date",
                "expiration_date",
                "expected_expiration_date",
            )
        )
        cells.append(
            _interest_html(
                row["per_lease_working_interest"],
                missing.get("per_lease_working_interest", "Not reported"),
            )
        )
        operators = "<br>".join(_text(name) for name in row["operator"])
        history = "<br>".join(
            _text(
                f"{r.get('operator_name') or r.get('operator_name_reason') or 'not reported'} / "
                f"status {r.get('ASGN_STATUS_CODE') or 'not reported'} / "
                f"designated {r.get('LEASE_DESIG_DATE') or 'not reported'} / "
                f"effective {r.get('ASGN_EFF_DATE') or 'not reported'} / "
                f"approved {r.get('ASGN_APRV_DATE') or 'not reported'}"
            )
            for r in row["operator_of_record_history"]
        )
        cells.append(
            (operators or _text(None, missing.get("operator", "Not reported")))
            + (
                f"<details><summary>Operator assignment history</summary>{history}</details>"
                if history
                else ""
            )
        )
        cells.append(_text(row["royalty_system"]))
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    source = panel.get("source") or {}
    retrievals = source.get("retrieved_at_utc", [])
    caption = (
        "BSEE snapshot retrieved " + _text(retrievals[0])
        if retrievals
        else "No BSEE lease snapshot supplied"
    )
    return (
        '<div class="scrollx"><table class="lease xwells">'
        + f"<caption>{caption}; source update date unknown.</caption><thead><tr>"
        + "".join(f'<th scope="col">{label}</th>' for label in headers)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        + '<p class="leadin">Owner interests retain source groups and aliquots; no totals '
        + "across groups. Actual and expected expiration dates are distinct. "
        + "Company names are those resolved at retrieval, including on historical rows. "
        + "Lease type is not mapped. "
        + "BSEE working database; not a legal document. "
        + '<a href="https://www.data.bsee.gov/Main/Leasing.aspx">BSEE leasing sources</a>.</p>'
    )


def build_landman(
    field_facts: dict,
    leases: list[str],
    blocks: list[str],
    lease_rows: dict,
    ingest_issue: int,
    block_note: str | None = None,
    *,
    lease_snapshot: dict | None = None,
) -> dict:
    """Return the landman panel dict for one field.

    ``lease_rows`` maps a normalized lease number -> ``{water_depth_ft,
    dev_system, lease_name}`` (from the V30 workbook). ``leases``/``blocks`` are
    the canonical registry lists. Only the snapshot can supply a per-lease block.
    """
    rows = []
    for lease in leases:
        v = lease_rows.get(_norm(lease), {})
        source = (lease_snapshot or {}).get("leases", {}).get(_norm(lease), {})
        rows.append(
            {
                "lease_num": lease,
                "lease_name": v.get("lease_name"),
                "water_depth_ft": v.get("water_depth_ft"),
                "dev_system": v.get("dev_system"),
                **_lease_details(source),
            }
        )
    wi = field_facts.get("working_interest") or []
    panel = {
        "leases": rows,
        "n_leases": len(rows),
        "blocks": list(blocks),
        "block_note": block_note,
        "operator": field_facts.get("operator"),
        "working_interest": wi,  # per-FIELD partner split (real)
        "pending": [
            attr for attr in PENDING_ATTRS if any(attr in r["missing"] for r in rows)
        ],
        "ingest_issue": ingest_issue,
        "source": (lease_snapshot or {}).get("source"),
    }
    panel["table_html"] = render_lease_table(panel)
    return panel


def _norm(lease: str) -> str:
    """Normalize a lease number for joining: 'OCS-G 25806' -> 'G25806'.

    Strips the 'OCS-' prefix (keeping the region letter) and all spaces, uppercase.
    """
    return lease.upper().replace("OCS-", "").replace(" ", "").strip()
