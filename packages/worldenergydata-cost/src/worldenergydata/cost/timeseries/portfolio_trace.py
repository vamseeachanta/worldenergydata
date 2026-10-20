"""Nominal project disclosure traces, with no FX, interpolation or award summation.

Accounting policy: curated/AWARD_REGISTRY.md and COST_REVISION_TRAILS.md
(2026-07-15), and issues 1038/1042. Unstructured total-value bounds and missing
award currencies remain NOT_EVALUATED; raw source fields are always retained.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from worldenergydata.cost.timeseries.project_trace import DateInterval

TABLES = (
    "sanctioned_projects.csv",
    "contract_awards.csv",
    "project_cost_statements.csv",
    "cost_revision_trails.csv",
)
LINK_TABLES = (
    "cost_project_identity.csv",
    "cost_award_identity.csv",
    "cost_requirement_identity.csv",
    "award_asset_links.csv",
    "project_asset_requirements.csv",
)
# Natural keys identify observations, not assertions of cross-table equivalence.
KEYS = {
    TABLES[0]: ("PROJECT",),
    TABLES[1]: ("PROJECT", "AWARD_YEAR", "CONTRACTOR", "ASSET_CLASS", "SCOPE_DESC"),
    TABLES[2]: ("PROJECT", "STATEMENT_YEAR", "COMPANY", "FIGURE_TYPE", "CURRENCY"),
    TABLES[3]: ("PROJECT", "STATEMENT_DATE", "KIND", "CURRENCY", "BASIS"),
}


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ProjectCostEvent:
    event_id: str
    project: str
    event_type: str
    lane: str
    component: str
    effective_date: DateInterval
    date_role: str
    source_available_date: DateInterval | None
    low_value: str
    high_value: str
    currency: str
    value_basis: str
    scope_basis: str
    confidence: str
    source_table: str
    source_fields: dict[str, str]
    award_id: str = ""
    requirement_ids: tuple[str, ...] = ()
    link_status: str = "unlinked"
    price_basis: str = "nominal"
    units: str = "million native currency units"
    bound_qualification: str = "NOT_EVALUATED"

    @property
    def historical_feature_eligible(self) -> bool:
        """Availability is necessary; this does not qualify values for modeling."""
        return self.source_available_date is not None

    def definitely_before(self, other: ProjectCostEvent) -> bool:
        return self.effective_date.end < other.effective_date.start

    @property
    def lane_key(self) -> tuple[str, ...]:
        return (
            self.project,
            self.lane,
            self.component,
            self.currency,
            self.price_basis,
            self.value_basis,
            self.scope_basis,
        )


@dataclass(frozen=True)
class PortfolioTrace:
    events: tuple[ProjectCostEvent, ...]
    projects: tuple[str, ...]
    source_counts: dict[str, int]
    trail_only_projects: list[str]
    missing_years: dict[str, list[int]]
    input_sha256: dict[str, str]
    consistency_status: str = "NOT_EVALUATED"
    consistency_reason: str = (
        "Component sums are not project spend. Portfolio-wide asset links, "
        "currency, ownership, bundle exclusions and comparable total bounds "
        "are not established; no residual or coverage ratio is calculated."
    )

    @property
    def lanes(self) -> dict[tuple[str, ...], tuple[ProjectCostEvent, ...]]:
        keys = sorted({e.lane_key for e in self.events})
        return {key: tuple(e for e in self.events if e.lane_key == key) for key in keys}


def _read_snapshot(root: Path):
    tables, hashes = {}, {}
    for name in (*TABLES, *LINK_TABLES):
        path = root / name
        if not path.is_file() and name in LINK_TABLES:
            continue
        payload = path.read_bytes()
        hashes[name] = _digest(payload)
        tables[name] = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    return tables, hashes


def _identity_match(identity, table, row):
    if identity.get("ACTIVE") != "true" or identity.get("STATE") != "active":
        return False
    if identity.get("SOURCE_TABLE") != table:
        return False
    locator = identity["SOURCE_RECORD_LOCATOR"]
    return all(
        row.get(k) == v for k, v in (part.split("=", 1) for part in locator.split("|"))
    )


def _award_link(row, tables):
    identities = [
        r
        for r in tables.get("cost_award_identity.csv", [])
        if _identity_match(r, TABLES[1], row)
    ]
    if not identities:
        return "", (), "unlinked"
    if len(identities) != 1:
        raise ValueError("ambiguous award identity")
    award_id = identities[0]["OPAQUE_ID"]
    links = [
        r for r in tables.get("award_asset_links.csv", []) if r["AWARD_ID"] == award_id
    ]
    if len(links) != 1:
        raise ValueError("award identity requires one link record")
    link = links[0]
    locator = link["SOURCE_LOCATOR"]
    prefix = TABLES[1] + ":"
    source_identity = {
        "ACTIVE": "true",
        "STATE": "active",
        "SOURCE_TABLE": TABLES[1],
        "SOURCE_RECORD_LOCATOR": locator.removeprefix(prefix),
    }
    if not locator.startswith(prefix) or not _identity_match(
        source_identity, TABLES[1], row
    ):
        raise ValueError("award link source locator mismatch")
    project_ids = {
        r["OPAQUE_ID"]
        for r in tables.get("cost_project_identity.csv", [])
        if _identity_match(r, TABLES[0], row)
    }
    if link["PROJECT_ID"] not in project_ids:
        raise ValueError("award project identity mismatch")
    requirements = tuple(link["REQUIREMENT_IDS"].replace(";", "|").split("|"))
    active = {
        r["OPAQUE_ID"]
        for r in tables.get("cost_requirement_identity.csv", [])
        if r.get("STATE") == "active" and r.get("ACTIVE") == "true"
    }
    owned = {
        r["REQUIREMENT_ID"]
        for r in tables.get("project_asset_requirements.csv", [])
        if r["PROJECT_ID"] == link["PROJECT_ID"]
    }
    if not requirements or not set(requirements) <= active & owned:
        raise ValueError("award requirement identity mismatch")
    return award_id, requirements, link["LINK_RESOLUTION"]


def _amount(value: str) -> str:
    if value:
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("invalid monetary amount") from exc
        if not number.is_finite() or number < 0:
            raise ValueError("amount must be finite and nonnegative")
    return value


def _event(table, row, tables):
    key = {name: row.get(name, "") for name in KEYS[table]}
    event_id = "evt-derived-" + _digest(_json([table, key]).encode())
    if not row.get("PROJECT", "").strip():
        raise ValueError("project is required")
    award = table == TABLES[1]
    year_field = {
        TABLES[0]: "FID_YEAR",
        TABLES[1]: "AWARD_YEAR",
        TABLES[2]: "STATEMENT_YEAR",
        TABLES[3]: "STATEMENT_DATE",
    }[table]
    when = DateInterval.from_text(row[year_field])
    value = row.get("VALUE_MM", row.get("SANCTIONED_CAPEX_USD_MM", ""))
    low, high = (
        (row.get("VALUE_LOW_MM", ""), row.get("VALUE_HIGH_MM", ""))
        if award
        else (value, value)
    )
    low, high = _amount(low), _amount(high)
    basis = row.get("VALUE_BASIS", row.get("FIGURE_TYPE", "as_curated"))
    if basis == "not_public" and (low or high):
        raise ValueError("not_public must not carry an amount")
    qualified = award and basis != "point"
    if award and basis == "point":
        qualified = bool(low and high and Decimal(low) == Decimal(high))
    if low and high and Decimal(low) > Decimal(high):
        raise ValueError("amount lower bound exceeds upper bound")
    award_id, requirement_ids, status = (
        _award_link(row, tables) if award else ("", (), "not_applicable")
    )
    available = row.get("SOURCE_PUBLISHED_DATE", "")
    return ProjectCostEvent(
        event_id=event_id,
        project=row["PROJECT"],
        event_type=(
            "award"
            if award
            else row.get("KIND", row.get("FIGURE_TYPE", "sanction_estimate"))
        ),
        lane="component" if award else "total",
        component=row.get("ASSET_CLASS", ""),
        effective_date=when,
        date_role=year_field,
        source_available_date=DateInterval.from_text(available) if available else None,
        low_value=low,
        high_value=high,
        # No currency column exists in legacy awards. Do not infer USD from '$'
        # or import-time FX notes; AWARD_REGISTRY.md also documents EUR bands.
        currency=row.get("CURRENCY") or ("USD" if table == TABLES[0] else "unknown"),
        value_basis=basis,
        scope_basis=row.get(
            "BASIS",
            row.get(
                "CAPEX_BASIS", row.get("SCOPE_DESC", row.get("FIGURE_TYPE", "unknown"))
            ),
        ),
        confidence=(
            "low"
            if row.get("PROVENANCE") == "trade_press"
            else row.get("CONFIDENCE", "not_evaluated")
        ),
        source_table=table,
        source_fields=dict(row),
        award_id=award_id,
        requirement_ids=requirement_ids,
        link_status=status,
        bound_qualification="structured_award_bounds" if qualified else "NOT_EVALUATED",
    )


def build_portfolio_trace(
    data_root: Path | None = None, *, tables=None
) -> PortfolioTrace:
    """Read a snapshot of the four curated tables; optional tables enable callers.

    Generated content-derived IDs are local trace keys, not canonical registry
    allocations. Different source tables remain distinct corroborating evidence.
    """
    if tables is None:
        if data_root is None:
            raise ValueError("data_root or explicit tables is required")
        tables, hashes = _read_snapshot(data_root)
    else:
        tables = {name: [dict(row) for row in rows] for name, rows in tables.items()}
        hashes = {
            name: _digest(_json(rows).encode()) for name, rows in sorted(tables.items())
        }
    projects, seen = set(), {}
    for table in TABLES:
        for row in tables[table]:
            event = _event(table, row, tables)
            projects.add(event.project)
            if event.event_id in seen and seen[event.event_id] != event:
                raise ValueError(f"conflicting duplicate event in {table}")
            seen[event.event_id] = event
    events = tuple(
        sorted(
            seen.values(),
            key=lambda e: (
                e.project,
                e.effective_date.start,
                e.effective_date.end,
                e.event_id,
            ),
        )
    )
    gaps = {}
    for project in sorted(projects):
        years = {e.effective_date.start.year for e in events if e.project == project}
        gaps[project] = sorted(set(range(min(years), max(years) + 1)) - years)
    trail_only = sorted(
        {r["PROJECT"] for r in tables[TABLES[3]]}
        - {r["PROJECT"] for r in tables[TABLES[0]]}
    )
    return PortfolioTrace(
        events,
        tuple(sorted(projects)),
        {name: len(tables[name]) for name in TABLES},
        trail_only,
        gaps,
        hashes,
    )


def _event_record(event):
    record = asdict(event)
    record["effective_date"] = event.effective_date.model_dump(mode="json")
    record["source_available_date"] = (
        event.source_available_date.model_dump(mode="json")
        if event.source_available_date
        else None
    )
    record["historical_feature_eligible"] = event.historical_feature_eligible
    return record


def canonical_events(trace: PortfolioTrace) -> str:
    return _json([_event_record(event) for event in trace.events])


def _source_link(row):
    url = row.get("SOURCE_URL", "")
    title = escape(row.get("SOURCE_TITLE", "Source unavailable"))
    try:
        parsed = urlparse(url)
    except ValueError:
        return title
    if parsed.scheme in {"https", "http"} and parsed.netloc and not parsed.username:
        return f'<a href="{escape(url, quote=True)}" rel="noreferrer">{title}</a>'
    return title


def render_trace_html(trace: PortfolioTrace) -> str:
    """Render disclosed events as rows; no line joins imply invented observations."""
    parts = [
        "<!doctype html><html lang='en'><meta charset='utf-8'>",
        "<title>Project component cost traces</title>",
        "<h1>Project component cost traces</h1>",
        f"<p>{len(trace.projects)} projects; {len(trace.events)} distinct events. "
        "Nominal values only; currencies and bases remain separate. "
        "Display order does not establish chronology for overlapping date intervals.</p>",
        "<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th><th>Change</th></tr>"
        "<tr><td>1</td><td>2026-10-19</td><td>Event trace with source coverage and evidence gaps.</td></tr></table>",
        f"<p>Component-to-total consistency: {trace.consistency_status}. "
        f"{escape(trace.consistency_reason)}</p>",
        "<p>Total-value bounds remain NOT_EVALUATED: curated scalar values can be "
        "floors, ceilings or collapsed ranges. Consult the retained quote and basis. "
        "Unknown award currency prevents numerical comparisons. Access dates are "
        "not treated as publication dates.</p>",
    ]
    for project in trace.projects:
        parts.extend(
            [
                f"<h2>{escape(project)}</h2>",
                f"<p>Years with no observations between endpoints: {escape(str(trace.missing_years[project]))}</p>",
                "<table><tr><th>Event date</th><th>Event / component</th><th>Low / high (million native units)</th>"
                "<th>Currency / value basis</th><th>Evidence</th></tr>",
            ]
        )
        for e in (e for e in trace.events if e.project == project):
            payload = escape(_json(e.source_fields))
            parts.append(
                f"<tr><td>{e.effective_date.label} ({e.effective_date.precision})</td>"
                f"<td>{escape(e.event_type)} / {escape(e.component)}<br>{escape(e.scope_basis)}</td>"
                f"<td>{escape(e.low_value or 'unavailable')} / {escape(e.high_value or 'unavailable')}</td>"
                f"<td>{escape(e.currency)} / {escape(e.value_basis)}</td>"
                f"<td>{_source_link(e.source_fields)}; confidence: {escape(e.confidence)}; "
                f"asset link: {escape(e.link_status)}; bounds: {e.bound_qualification}"
                f"<br>Award: {escape(e.award_id or 'not applicable')}; "
                f"requirements: {escape(', '.join(e.requirement_ids) or 'unavailable')}; "
                f"source available: {e.source_available_date.label if e.source_available_date else 'unknown'}"
                f"<details><summary>Source row and provenance</summary><pre>{payload}</pre></details></td></tr>"
            )
        parts.append("</table>")
    parts.append("</html>\n")
    return "\n".join(parts)


def write_trace_outputs(trace: PortfolioTrace, output_dir: Path) -> tuple[Path, ...]:
    """Write deterministic UTF-8 artifacts and verify their digests by readback."""
    if len({e.event_id for e in trace.events}) != len(trace.events):
        raise ValueError("duplicate event identity")
    stream = io.StringIO(newline="")
    records = [_event_record(e) for e in trace.events]
    fields = list(ProjectCostEvent.__dataclass_fields__) + [
        "historical_feature_eligible"
    ]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                key: (
                    _json(value).strip()
                    if isinstance(value, (dict, list, tuple))
                    else value
                )
                for key, value in record.items()
            }
        )
    payloads = {
        "project_cost_events.json": canonical_events(trace).encode(),
        "project_cost_events.csv": stream.getvalue().encode(),
        "project_cost_traces.html": render_trace_html(trace).encode(),
    }
    manifest = {
        "schema_version": "1",
        "project_count": len(trace.projects),
        "event_count": len(trace.events),
        "projects": trace.projects,
        "source_counts": trace.source_counts,
        "trail_only_projects": trace.trail_only_projects,
        "missing_years": trace.missing_years,
        "input_sha256": trace.input_sha256,
        "generated_at_policy": "not_embedded",
        "arithmetic": "none; native decimal text retained",
        "consistency_status": trace.consistency_status,
        "consistency_reason": trace.consistency_reason,
        "outputs": {name: _digest(data) for name, data in payloads.items()},
    }
    payloads["project_trace_manifest.json"] = _json(manifest).encode()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, payload in payloads.items():
        path = output_dir / name
        path.write_bytes(payload)
        if _digest(path.read_bytes()) != _digest(payload):
            raise ValueError("output digest mismatch")
        paths.append(path)
    return tuple(paths)
