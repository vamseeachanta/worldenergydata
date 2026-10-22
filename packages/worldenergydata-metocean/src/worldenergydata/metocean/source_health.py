"""Current source diagnostics; no authentication, retries or bulk downloads."""

import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from worldenergydata.metocean.clients.endpoint_checks import EndpointError, probe_sample
from worldenergydata.metocean.source_register import (
    load_register,
    registered_url,
    validate_register,
)

_REVISION_NOTE = "Snapshot of registered cheap checks for access diagnostics"


def source_health(
    *,
    http: httpx.Client,
    user_agent: str,
    register: dict | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    json_path: Path | None = None,
    markdown_path: Path | None = None,
) -> list[dict]:
    """Return a table and optionally write JSON and Markdown snapshots.

    Only registered health_url requests with supported parsers are performed.
    Account/free-key sources are CREDENTIALS_REQUIRED even if local credentials
    exist: cheap anonymous checks cannot attest authenticated download readiness.
    Sources without a supported probe are UNREACHABLE with NOT_EVALUATED detail,
    not falsely marked retired. No request means last_checked is null.
    RETIRED means the checked URL returned 404/410 (removed or moved), not that
    the entire publisher service has closed. Status semantics: RFC 9110 (2022),
    sections 15.3-15.6; RFC 6585 (2012), section 4.
    """
    register = load_register() if register is None else register
    validate_register(register)
    instant = now()
    if instant.utcoffset() != timedelta(0):
        raise ValueError("Health clock must return explicit UTC")
    if not user_agent.strip():
        raise ValueError("An identifying User-Agent is required")
    stamp = instant.isoformat()
    table = []
    for source in register["sources"]:
        row = {
            "source": source["id"],
            "status": "UNREACHABLE",
            "last_checked": None,
            "terms_url": source["terms_url"],
            "detail": "NOT_EVALUATED: no supported cheap data probe",
        }
        if source["auth_requirement"] != "none":
            row.update(
                status="CREDENTIALS_REQUIRED",
                detail="Account/key access or unconfirmed anonymous access; download NOT_EVALUATED",
            )
        elif source.get("health_url"):
            url = source["health_url"]
            if not registered_url(url, {"sources": [source]}):
                raise ValueError("Health URL must be registered for its source")
            if source["id"] not in {
                "ndbc_realtime",
                "coops",
                "irish_weather_buoys",
                "met_norway",
            }:
                raise ValueError("No registered parser for health source")
            row["last_checked"] = stamp
            row.update(_check(source["id"], url, http, user_agent))
        table.append(row)
    outputs = []
    if json_path is not None:
        path = Path(json_path)
        history = []
        if path.exists():
            previous = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(previous, dict) or not isinstance(
                previous.get("revision_history"), list
            ):
                raise ValueError("Existing JSON is not a source-health report")
            history = previous["revision_history"]
        history = [
            *history,
            {
                "revision": len(history) + 1,
                "date": stamp,
                "change": _REVISION_NOTE,
            },
        ]
        payload = {
            "summary": "Anonymous sample diagnostics; engineering suitability NOT_EVALUATED",
            "revision_history": history,
            "generated_at": stamp,
            "sources": table,
        }
        outputs.append((path, json.dumps(payload, indent=2) + "\n"))
    if markdown_path is not None:
        path = Path(markdown_path)
        history = []
        if path.exists():
            previous = path.read_text(encoding="utf-8")
            if (
                not previous.startswith("# Metocean source health\n")
                or "## Revision history" not in previous
            ):
                raise ValueError("Existing Markdown is not a source-health report")
            section = (
                previous.split("## Revision history\n", 1)[1]
                .lstrip("\n")
                .split("\n\n", 1)[0]
            )
            history = [
                line
                for line in section.splitlines()
                if line.startswith("| ") and line.split("|")[1].strip().isdigit()
            ]
            if not history:
                raise ValueError("Existing report revision history is malformed")
        history = [
            *history,
            f"| {len(history) + 1} | {stamp} | {_REVISION_NOTE} |",
        ]
        outputs.append((path, _markdown(table, history)))
    for path, content in outputs:
        path.write_text(content, encoding="utf-8")
    return table


def _check(source: str, url: str, http: httpx.Client, user_agent: str) -> dict:
    try:
        probe_sample(source, http=http, user_agent=user_agent, url=url)
    except EndpointError as error:
        status = getattr(error, "status_code", None)
        if status in {404, 410}:
            return {
                "status": "RETIRED",
                "detail": "Checked URL removed or moved; consult publisher documentation",
            }
        if status in {401, 403}:
            return {
                "status": "CREDENTIALS_REQUIRED",
                "detail": "Access rejected; retirement not established",
            }
        return {
            "status": "UNREACHABLE",
            "detail": "Transport, HTTP or data schema check failed; retirement not established",
        }
    return {
        "status": "OK",
        "detail": "Sample schema, units and UTC checked; engineering suitability NOT_EVALUATED",
    }


def _markdown(table: list[dict], history: list[str]) -> str:
    lines = [
        "# Metocean source health",
        "",
        (
            "Anonymous sample diagnostics only. Download readiness and "
            "engineering suitability are NOT_EVALUATED."
        ),
        "",
        "## Revision history",
        "",
        "| Revision | Date | What changed and why |",
        "| --- | --- | --- |",
        *history,
        "",
        (
            "A null last-checked time means no request was attempted. RETIRED "
            "refers to the checked URL, which may have moved."
        ),
        "",
        "| Source | Status | Last checked (UTC) | Terms | Detail |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in table:
        cells = [
            row["source"],
            row["status"],
            row["last_checked"] or "not checked",
            row["terms_url"],
            row["detail"],
        ]
        lines.append(
            "| "
            + " | ".join(
                str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells
            )
            + " |"
        )
    return "\n".join(lines) + "\n"
