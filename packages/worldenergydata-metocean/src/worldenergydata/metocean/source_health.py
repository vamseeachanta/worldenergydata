"""Current source diagnostics; no authentication, retries or bulk downloads."""

import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from worldenergydata.metocean.clients.endpoint_checks import EndpointError, probe_sample
from worldenergydata.metocean.source_register import (
    _https_url,
    load_register,
    registered_url,
    validate_register,
)

_REVISION_NOTE = "Snapshot of registered cheap checks for access diagnostics"
_REPORT_TYPE = "metocean_source_health"
_SUMMARY = "Anonymous sample diagnostics; engineering suitability NOT_EVALUATED"
_STATUSES = {"OK", "RETIRED", "CREDENTIALS_REQUIRED", "UNREACHABLE"}


def _report_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Expected a UTC timestamp")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.utcoffset() != timedelta(0):
        raise ValueError("Expected a UTC timestamp")
    return timestamp


def _report_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _previous_history(previous: object) -> list[dict]:
    """Accept only complete reports, preserving earlier valid report histories.

    Legacy reports use the exact summary as their discriminator. New reports
    also carry report_type. Unknown fields are rejected to avoid data loss.
    """
    try:
        fields = {"summary", "revision_history", "generated_at", "sources"}
        if not isinstance(previous, dict):
            raise ValueError
        if "report_type" in previous:
            fields.add("report_type")
            if previous["report_type"] != _REPORT_TYPE:
                raise ValueError
        if set(previous) != fields or previous["summary"] != _SUMMARY:
            raise ValueError
        generated_at = _report_timestamp(previous["generated_at"])
        history = previous["revision_history"]
        if not isinstance(history, list) or not history:
            raise ValueError
        for revision, entry in enumerate(history, 1):
            if not isinstance(entry, dict) or set(entry) != {
                "revision",
                "date",
                "change",
            }:
                raise ValueError
            if type(entry["revision"]) is not int or entry["revision"] != revision:
                raise ValueError
            if not _report_text(entry["change"]):
                raise ValueError
            _report_timestamp(entry["date"])
        if _report_timestamp(history[-1]["date"]) != generated_at:
            raise ValueError
        sources = previous["sources"]
        if not isinstance(sources, list):
            raise ValueError
        seen = set()
        for row in sources:
            if not isinstance(row, dict) or set(row) != {
                "source",
                "status",
                "last_checked",
                "terms_url",
                "detail",
            }:
                raise ValueError
            if not _report_text(row["source"]) or row["source"] in seen:
                raise ValueError
            seen.add(row["source"])
            if row["status"] not in _STATUSES or not _report_text(row["detail"]):
                raise ValueError
            if not _https_url(row["terms_url"]):
                raise ValueError
            if row["last_checked"] is not None:
                _report_timestamp(row["last_checked"])
        return history
    except (ValueError, KeyError, TypeError):
        raise ValueError("Existing JSON is not a valid source-health report") from None


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
            history = _previous_history(previous)
        history = [
            *history,
            {
                "revision": len(history) + 1,
                "date": stamp,
                "change": _REVISION_NOTE,
            },
        ]
        payload = {
            "report_type": _REPORT_TYPE,
            "summary": _SUMMARY,
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
