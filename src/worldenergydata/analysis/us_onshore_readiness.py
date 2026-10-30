"""Evidence-backed U.S. onshore source matrix for #911.

Statuses describe materialization only. Qualification remains NOT_EVALUATED;
freshness and completeness remain unknown until the evidence required by
``docs/data/source-refresh-acceptance-criteria.md`` (#462) is assessed.
No remote requests, recursive discovery, or underwriting calculations occur.
"""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Vocabulary: #910 acceptance criteria; NOT_EVALUATED is the #911 task fallback.
STATUSES = frozenset(
    {
        "downloaded",
        "derived",
        "configured-only",
        "partial/error",
        "missing",
        "private/legacy",
    }
)
CATALOG_FIELDS = frozenset(
    {
        "source_id",
        "state",
        "source",
        "domain",
        "coverage",
        "status",
        "evidence",
        "evidence_scope",
        "observed_at",
        "discovery_required",
        "priority",
        "reason",
        "issues",
        "limitations",
    }
)
OBSERVATION_FIELDS = frozenset(
    {"source_id", "status", "evidence", "observed_at", "limitations"}
)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_row(row: Any, fields: frozenset[str]) -> None:
    if not isinstance(row, dict) or set(row) != fields:
        raise ValueError("record fields do not match the source evidence contract")
    if not _text(row["status"]) or row["status"] not in STATUSES:
        raise ValueError("unsupported materialization status")
    for field in ("source_id", "evidence", "limitations"):
        if not _text(row[field]):
            raise ValueError(f"{field} requires nonempty evidence text")
    try:
        observed_at = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
        if observed_at.tzinfo is None:
            raise ValueError("timestamp needs a time zone")
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError(
            "observed_at requires an ISO timestamp with time zone"
        ) from error
    if fields == CATALOG_FIELDS:
        for field in (
            "state",
            "source",
            "domain",
            "evidence_scope",
            "priority",
            "reason",
        ):
            if not _text(row[field]):
                raise ValueError(f"{field} requires nonempty text")
        for field in ("coverage", "issues"):
            if not isinstance(row[field], list) or not row[field]:
                raise ValueError(f"{field} requires a nonempty list")
            if not all(_text(value) for value in row[field]):
                raise ValueError(f"{field} requires text entries")
        if type(row["discovery_required"]) is not bool:
            raise ValueError("discovery_required requires a boolean")
        if row["priority"] not in {"first", "next", "reuse"}:
            raise ValueError("unsupported acquisition priority")


def _validate_catalog(rows: Any) -> None:
    if not isinstance(rows, list) or not rows:
        raise ValueError("sources requires a nonempty list")
    seen = set()
    for row in rows:
        _validate_row(row, CATALOG_FIELDS)
        if row["source_id"] in seen:
            raise ValueError("duplicate source in catalog")
        seen.add(row["source_id"])


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
    )


def load_catalog(path: Path) -> list[dict[str, Any]]:
    """Read the explicit catalog; it is not evidence of a successful download."""
    payload = _read_json(path)
    if not isinstance(payload, dict) or set(payload) != {"sources"}:
        raise ValueError("catalog requires sources")
    _validate_catalog(payload["sources"])
    return payload["sources"]


def build_matrix(
    catalog: list[dict[str, Any]], observations: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Apply explicit inventory observations by source ID, preserving the baseline.

    A supplied inventory is an assertion, not authenticated source qualification.
    Error/missing/private observations never fall back to a reported download.
    Unmentioned sources retain their original evidence and status.
    """
    _validate_catalog(catalog)
    rows = copy.deepcopy(catalog)
    by_id = {row["source_id"]: row for row in rows}
    if observations is None:
        observations = []
    if not isinstance(observations, list):
        raise TypeError("observations requires a list")
    seen = set()
    for observation in observations:
        _validate_row(observation, OBSERVATION_FIELDS)
        source_id = observation["source_id"]
        if source_id not in by_id:
            raise ValueError("unknown source in inventory")
        if source_id in seen:
            raise ValueError("duplicate source in inventory")
        seen.add(source_id)
        row = by_id[source_id]
        row["prior_evidence"] = {key: copy.deepcopy(row[key]) for key in CATALOG_FIELDS}
        row.update(observation)
        row["evidence_scope"] = "supplied inventory"
    for row in rows:
        row.update(
            qualification="NOT_EVALUATED",
            freshness="unknown",
            completeness="unknown",
            public_ingest=(
                "quarantined" if row["status"] == "private/legacy" else "NOT_EVALUATED"
            ),
        )
    return rows


def render_markdown(rows: list[dict[str, Any]]) -> str:
    """Render evidence and acquisition rationale alongside each source."""

    def cell(value: Any) -> str:
        if isinstance(value, list):
            value = ", ".join(value)
        return " ".join(str(value).splitlines()).replace("|", "\\|")

    columns = [
        ("State", "state"),
        ("Source ID", "source_id"),
        ("Source", "source"),
        ("Domain", "domain"),
        ("Coverage", "coverage"),
        ("Status", "status"),
        ("Evidence scope", "evidence_scope"),
        ("Evidence", "evidence"),
        ("Observed at", "observed_at"),
        ("Discovery required", "discovery_required"),
        ("Priority", "priority"),
        ("Why", "reason"),
        ("Issues", "issues"),
        ("Limits", "limitations"),
        ("Qualification", "qualification"),
        ("Freshness", "freshness"),
        ("Completeness", "completeness"),
        ("Public ingest", "public_ingest"),
    ]
    lines = [
        "# U.S. onshore source readiness matrix",
        "",
        (
            "Materialization evidence only; freshness, completeness, rights and title "
            "qualification have not been established."
        ),
        "",
        "## Revision history",
        "",
        "| Revision | Date | Change and reason |",
        "| --- | --- | --- |",
        "| Initial | 2026-10-20 | Separate reported materialization from qualification. |",
        (
            "| 1 | 2026-10-20 | Align state endpoint domains and coverage with "
            "configured data types; identify unsupported land records for discovery. |"
        ),
        "",
        "## Sources",
        "",
        "| " + " | ".join(title for title, _ in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        cells = []
        for _, key in columns:
            if key == "issues":
                cells.append(
                    ", ".join(
                        f"[{issue}](../../../../../issues/{issue.removeprefix('#')})"
                        for issue in row[key]
                    )
                )
            else:
                cells.append(cell(row[key]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Emit a deterministic report from a catalog and optional bounded inventory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, default=Path("config/us_onshore_readiness.json")
    )
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        observations = None
        if args.inventory:
            payload = _read_json(args.inventory)
            if not isinstance(payload, dict) or set(payload) != {"observations"}:
                raise ValueError("inventory requires observations")
            observations = payload["observations"]
            if observations is None:
                raise TypeError("observations requires a list")
        rows = build_matrix(load_catalog(args.catalog), observations)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        print(render_markdown(rows), end="")


if __name__ == "__main__":
    main()
