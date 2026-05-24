"""Phase 1A exploration — intervention-HSE data inventory.

Issue: https://github.com/vamseeachanta/worldenergydata/issues/416
Branch: feat/issue-416-phase1a-intervention-hse-service-type

Purpose: inventory the HSE DB + BSEE WAR data surface area BEFORE running pattern
mining. Outputs go to reports/hse/intervention-hse-patterns-2026-05-18-explore.json
so the memo can cite concrete findings (record counts, date ranges, taxonomies,
join feasibility) instead of hand-waving.

Stdlib only — no uv-run, no pandas. Inspecting schemas, counts, and value
distributions.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HSE_DB = REPO / "data" / "modules" / "hse" / "hse_incidents.db"
MARINE_DB_PRIMARY = REPO / "data" / "modules" / "marine_safety" / "database" / "marine_safety.db"
OUT_DIR = REPO / "reports" / "hse"
OUT_FILE = OUT_DIR / "intervention-hse-patterns-2026-05-18-explore.json"


def _safe_count(cur: sqlite3.Cursor, query: str, params: tuple = ()) -> int:
    try:
        return cur.execute(query, params).fetchone()[0] or 0
    except sqlite3.Error:
        return -1


def inventory_hse_db() -> dict:
    """Inventory the BSEE-anchored HSE DB."""
    out: dict = {
        "path": str(HSE_DB.relative_to(REPO)),
        "size_bytes": HSE_DB.stat().st_size,
        "tables": {},
    }
    con = sqlite3.connect(str(HSE_DB))
    cur = con.cursor()
    for (name,) in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ):
        row_count = _safe_count(cur, f'SELECT COUNT(*) FROM "{name}"')
        cols = [r[1] for r in cur.execute(f'PRAGMA table_info("{name}")')]
        out["tables"][name] = {"row_count": row_count, "columns": cols}
    con.close()
    return out


def hse_incidents_profile() -> dict:
    """Profile the hse_incidents table — the primary join surface."""
    con = sqlite3.connect(str(HSE_DB))
    cur = con.cursor()
    out: dict = {}

    out["total_rows"] = _safe_count(cur, "SELECT COUNT(*) FROM hse_incidents")

    out["date_range"] = {
        "min": cur.execute(
            "SELECT MIN(incident_date) FROM hse_incidents WHERE incident_date IS NOT NULL"
        ).fetchone()[0],
        "max": cur.execute(
            "SELECT MAX(incident_date) FROM hse_incidents WHERE incident_date IS NOT NULL"
        ).fetchone()[0],
    }

    rows_per_year = cur.execute(
        """SELECT substr(incident_date, 1, 4) AS yr, COUNT(*)
           FROM hse_incidents
           WHERE incident_date IS NOT NULL
           GROUP BY yr
           ORDER BY yr"""
    ).fetchall()
    out["rows_per_year"] = dict(rows_per_year)

    out["distinct_operators"] = _safe_count(
        cur, "SELECT COUNT(DISTINCT operator) FROM hse_incidents WHERE operator IS NOT NULL"
    )
    out["distinct_fields"] = _safe_count(
        cur,
        "SELECT COUNT(DISTINCT field_name) FROM hse_incidents WHERE field_name IS NOT NULL",
    )
    out["distinct_leases"] = _safe_count(
        cur,
        "SELECT COUNT(DISTINCT lease_number) FROM hse_incidents WHERE lease_number IS NOT NULL",
    )

    incident_type_dist = cur.execute(
        """SELECT incident_type, COUNT(*) AS n
           FROM hse_incidents
           WHERE incident_type IS NOT NULL
           GROUP BY incident_type
           ORDER BY n DESC
           LIMIT 30"""
    ).fetchall()
    out["top_30_incident_types"] = [
        {"type": t, "count": n} for t, n in incident_type_dist
    ]

    severity_dist = cur.execute(
        """SELECT severity, COUNT(*) AS n
           FROM hse_incidents
           WHERE severity IS NOT NULL
           GROUP BY severity
           ORDER BY n DESC"""
    ).fetchall()
    out["severity_distribution"] = [{"severity": s, "count": n} for s, n in severity_dist]

    out["rows_with_full_join_keys"] = _safe_count(
        cur,
        """SELECT COUNT(*) FROM hse_incidents
           WHERE operator IS NOT NULL
             AND lease_number IS NOT NULL
             AND incident_date IS NOT NULL""",
    )

    out["rows_with_lat_lon"] = _safe_count(
        cur,
        """SELECT COUNT(*) FROM hse_incidents
           WHERE latitude IS NOT NULL AND longitude IS NOT NULL""",
    )

    intervention_keywords = [
        "workover", "intervention", "wireline", "coil tubing", "snubbing",
        "well control", "well work", "P&A", "plug and abandon",
    ]
    out["intervention_keyword_hits"] = {}
    for kw in intervention_keywords:
        n = _safe_count(
            cur,
            """SELECT COUNT(*) FROM hse_incidents
               WHERE LOWER(description) LIKE ?
                  OR LOWER(incident_type) LIKE ?""",
            (f"%{kw.lower()}%", f"%{kw.lower()}%"),
        )
        out["intervention_keyword_hits"][kw] = n

    con.close()
    return out


def war_data_inventory() -> dict:
    """Inventory BSEE WAR (well activity report) local pickles."""
    war_dir = REPO / "data" / "modules" / "bsee" / ".local" / "war"
    out = {"path": str(war_dir.relative_to(REPO)), "exists": war_dir.exists()}
    if war_dir.exists():
        files = list(war_dir.iterdir())
        out["files"] = [
            {
                "name": f.name,
                "size_bytes": f.stat().st_size,
                "is_file": f.is_file(),
                "is_dir": f.is_dir(),
            }
            for f in files
        ]
    return out


def rig_fleet_inventory() -> dict:
    """Inventory rig fleet local files."""
    rf_dir = REPO / "data" / "modules" / "bsee" / ".local" / "rig_fleet"
    out = {"path": str(rf_dir.relative_to(REPO)), "exists": rf_dir.exists()}
    if rf_dir.exists():
        files = list(rf_dir.rglob("*"))
        out["file_count"] = len(files)
        out["files_sample"] = [
            {"name": str(f.relative_to(rf_dir)), "size_bytes": f.stat().st_size if f.is_file() else 0}
            for f in files[:15]
        ]
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "issue": "https://github.com/vamseeachanta/worldenergydata/issues/416",
        "branch": "feat/issue-416-phase1a-intervention-hse-service-type",
        "hse_db_inventory": inventory_hse_db(),
        "hse_incidents_profile": hse_incidents_profile(),
        "war_data": war_data_inventory(),
        "rig_fleet_data": rig_fleet_inventory(),
    }

    OUT_FILE.write_text(json.dumps(payload, indent=2, default=str))
    print(f"Wrote: {OUT_FILE.relative_to(REPO)}")
    print(json.dumps(
        {
            "hse_total_rows": payload["hse_incidents_profile"]["total_rows"],
            "hse_date_range": payload["hse_incidents_profile"]["date_range"],
            "distinct_operators": payload["hse_incidents_profile"]["distinct_operators"],
            "rows_with_full_join_keys": payload["hse_incidents_profile"]["rows_with_full_join_keys"],
            "intervention_keyword_hits": payload["hse_incidents_profile"]["intervention_keyword_hits"],
            "war_data_exists": payload["war_data"]["exists"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
