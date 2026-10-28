"""Read-only extraction of the Phase 1A HSE classifier surface.

Schema basis: scripts/exploration/intervention_hse_phase1a_explore.py (2026),
hse_incidents_profile. This is a mixed-source inventory, not proof that a row
is BSEE-sourced or associated with an intervention. Callers establish both.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HseIncident:
    """Internal classifier input; descriptions are not public report content."""

    record_id: str
    description: str | None
    incident_type: str | None
    accident_type: str | None = None

    def classifier_fields(self) -> dict[str, str]:
        """Keep incident type distinct from the BSEE accident-type field."""
        return {
            key: value
            for key, value in (
                ("description", self.description),
                ("incident_type", self.incident_type),
                ("accident_type", self.accident_type),
            )
            if value is not None
        }


def load_hse_incidents(database: str | Path) -> tuple[HseIncident, ...]:
    """Load a deterministic projection without modifying or creating a database.

    Missing sources and incompatible schemas raise rather than representing an
    empty population. No operator names, lease keys or arbitrary columns are
    loaded. The optional accident_type column is preserved when available.
    """
    path = Path(database).resolve(strict=True)
    # SQLite URI mode=ro prevents creation and writes; as_uri escapes # and ?.
    # Source: SQLite URI Filenames, "Recognized Query Parameters", mode.
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(hse_incidents)")
        }
        if not {"id", "description", "incident_type"}.issubset(columns):
            raise ValueError(
                "Incompatible HSE schema: required classifier fields missing"
            )
        if "accident_type" in columns:
            rows = connection.execute(
                "SELECT id, description, incident_type, accident_type "
                "FROM hse_incidents ORDER BY id"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, description, incident_type, NULL "
                "FROM hse_incidents ORDER BY id"
            ).fetchall()
    if any(row[0] is None for row in rows):
        raise ValueError("HSE record IDs must be present")
    incidents = tuple(HseIncident(str(row[0]), *row[1:]) for row in rows)
    if len({row.record_id for row in incidents}) != len(incidents):
        raise ValueError("HSE record IDs must be unique")
    return incidents
