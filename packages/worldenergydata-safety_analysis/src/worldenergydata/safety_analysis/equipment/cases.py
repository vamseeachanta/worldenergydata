# ABOUTME: Load and validate the register of illustrative public incident cases.
# ABOUTME: A case carries only what its cited investigation states, as page-referenced paraphrase.

"""Public case register.

Each case points to one public investigation report and records, as original
paraphrase with a page reference, what the report says failed, what it states
as the cause and what it recommends. Report text is not copied (the HSE source
registry stores links and paraphrase only), and nothing is added that the
report does not state: a case whose report gives no cause keeps the mechanism
``not_stated``. A factor the report rules out is recorded under ``ruled_out``,
never as a cause.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Optional

import yaml

from worldenergydata.safety_analysis.equipment.taxonomy import (
    EQUIPMENT_CLASSES,
    FAILURE_MECHANISMS,
    FAILURE_MODES,
    NOT_STATED,
)

MAX_STATEMENT_WORDS = 60

_CASE_KEYS = {
    "id",
    "equipment_class",
    "equipment_subclass",
    "date",
    "location",
    "area_block",
    "facility_type",
    "authority",
    "title",
    "report_ref",
    "url",
    "retrieved",
    "sha256",
    "what_failed",
    "failure_modes",
    "mechanism",
    "cause_statements",
    "ruled_out",
    "lessons",
    "consequences",
}
_REQUIRED = _CASE_KEYS - {
    "equipment_subclass",
    "area_block",
    "sha256",
    "ruled_out",
    "consequences",
    "lessons",
}


@dataclass(frozen=True)
class Statement:
    """A paraphrase of the report with the page that supports it."""

    statement: str
    page: int

    def cite(self) -> str:
        return f"{self.statement} (p. {self.page})"


@dataclass(frozen=True)
class PublicCase:
    id: str
    equipment_class: str
    date: str
    location: str
    facility_type: str
    authority: str
    title: str
    report_ref: str
    url: str
    retrieved: str
    what_failed: Statement
    failure_modes: tuple[str, ...]
    mechanism: str
    cause_statements: tuple[Statement, ...]
    ruled_out: tuple[Statement, ...] = ()
    lessons: tuple[Statement, ...] = ()
    consequences: tuple[Statement, ...] = ()
    equipment_subclass: str = NOT_STATED
    area_block: str = ""  # as the incident data set writes it, for matching
    sha256: str = ""

    def reference(self) -> str:
        """Web-reference line: owner, title, where it is published, date read.

        ``url`` is the regulator's page for the report. Where the direct file
        address carries a company name, the register gives the regulator's
        listing page instead; the title (block and date) and the digest of the
        file read identify the report.
        """
        digest = f" SHA-256 of the file read: {self.sha256}." if self.sha256 else ""
        return (
            f"{self.authority}, {self.title}, {self.report_ref}. "
            f"Available from {self.url} (read {self.retrieved}).{digest}"
        )


def _statement(raw: Any, where: str) -> Statement:
    if not isinstance(raw, dict) or set(raw) != {"statement", "page"}:
        raise ValueError(f"{where}: needs exactly 'statement' and 'page'")
    text = str(raw["statement"]).strip()
    if not text:
        raise ValueError(f"{where}: empty statement")
    if len(text.split()) > MAX_STATEMENT_WORDS:
        raise ValueError(f"{where}: statement over {MAX_STATEMENT_WORDS} words")
    if '"' in text or "“" in text:
        raise ValueError(f"{where}: paraphrase only; no quoted report text")
    page = raw["page"]
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise ValueError(f"{where}: page must be a positive integer")
    return Statement(text, page)


def _sha256(value: Any, where: str) -> str:
    text = str(value or "").strip().lower()
    if text and (len(text) != 64 or set(text) - set("0123456789abcdef")):
        raise ValueError(f"{where}: sha256 must be 64 hexadecimal characters")
    return text


def _statements(raw: Any, where: str) -> tuple[Statement, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"{where}: must be a list")
    return tuple(_statement(item, f"{where}[{i}]") for i, item in enumerate(raw))


def _date(value: Any, where: str) -> str:
    text = str(value)
    try:
        dt.date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{where}: {text!r} is not a YYYY-MM-DD date") from None
    return text


def parse_case(raw: dict) -> PublicCase:
    where = f"case {raw.get('id', '?')!r}"
    unknown = set(raw) - _CASE_KEYS
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
    missing = _REQUIRED - set(raw)
    if missing:
        raise ValueError(f"{where}: missing keys {sorted(missing)}")
    if raw["equipment_class"] not in EQUIPMENT_CLASSES:
        raise ValueError(f"{where}: unknown equipment class")
    modes = tuple(raw["failure_modes"])
    if not modes or any(m not in FAILURE_MODES for m in modes):
        raise ValueError(f"{where}: failure_modes must be known terms")
    mechanism = raw["mechanism"]
    if mechanism not in FAILURE_MECHANISMS:
        raise ValueError(f"{where}: unknown mechanism {mechanism!r}")
    causes = _statements(raw["cause_statements"], f"{where} cause_statements")
    if mechanism != NOT_STATED and not causes:
        raise ValueError(
            f"{where}: a mechanism needs a page-referenced cause statement"
        )
    url = str(raw["url"])
    if not url.startswith("https://") or "@" in url.split("/")[2]:
        raise ValueError(f"{where}: url must be a public https link")
    return PublicCase(
        id=str(raw["id"]),
        equipment_class=raw["equipment_class"],
        equipment_subclass=raw.get("equipment_subclass", NOT_STATED),
        date=_date(raw["date"], f"{where} date"),
        location=str(raw["location"]),
        area_block=str(raw.get("area_block", "")).strip(),
        facility_type=str(raw["facility_type"]),
        authority=str(raw["authority"]),
        title=str(raw["title"]),
        report_ref=str(raw["report_ref"]),
        url=url,
        retrieved=_date(raw["retrieved"], f"{where} retrieved"),
        sha256=_sha256(raw.get("sha256", ""), where),
        what_failed=_statement(raw["what_failed"], f"{where} what_failed"),
        failure_modes=modes,
        mechanism=mechanism,
        cause_statements=causes,
        ruled_out=_statements(raw.get("ruled_out"), f"{where} ruled_out"),
        lessons=_statements(raw.get("lessons"), f"{where} lessons"),
        consequences=_statements(raw.get("consequences"), f"{where} consequences"),
    )


def load_cases(path: Optional[Path] = None) -> list[PublicCase]:
    """Load the case register (the packaged one when ``path`` is None)."""
    if path is None:
        text = (
            resources.files("worldenergydata.safety_analysis.equipment")
            .joinpath("data/public_cases.yml")
            .read_text(encoding="utf-8")
        )
    else:
        text = Path(path).read_text(encoding="utf-8")
    doc = yaml.safe_load(text) or {}
    if doc.get("schema_version") != 1 or not isinstance(doc.get("cases"), list):
        raise ValueError("case register: needs schema_version 1 and a cases list")
    cases = [parse_case(raw) for raw in doc["cases"]]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("case register: duplicate case id")
    return cases


def cases_for(cases: list[PublicCase], equipment_class: str) -> list[PublicCase]:
    return [c for c in cases if c.equipment_class == equipment_class]
