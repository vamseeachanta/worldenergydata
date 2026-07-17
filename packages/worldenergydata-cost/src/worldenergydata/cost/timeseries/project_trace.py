from __future__ import annotations

import calendar
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, model_validator

from worldenergydata.cost.timeseries.cost_map_schema import Evidence, MoneyInterval

_PILOT_GROUP = "vg-cost-map-pilot-000001"


def _has_id(value: str | None, prefix: str) -> bool:
    return value is not None and value.startswith(prefix) and len(value) > len(prefix)


class DateInterval(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    start: date
    end: date
    precision: Literal["year", "month", "day"]

    @model_validator(mode="after")
    def _validate_interval(self) -> "DateInterval":
        if self.start > self.end:
            raise ValueError("date interval start must not exceed end")
        expected = {
            "year": (date(self.start.year, 1, 1), date(self.start.year, 12, 31)),
            "month": (
                date(self.start.year, self.start.month, 1),
                date(
                    self.start.year,
                    self.start.month,
                    calendar.monthrange(self.start.year, self.start.month)[1],
                ),
            ),
            "day": (self.start, self.start),
        }[self.precision]
        if (self.start, self.end) != expected:
            raise ValueError("date interval bounds must match stated precision")
        return self

    @property
    def label(self) -> str:
        if self.precision == "year":
            return f"{self.start.year:04d}"
        if self.precision == "month":
            return f"{self.start.year:04d}-{self.start.month:02d}"
        return self.start.isoformat()

    @classmethod
    def from_text(cls, value: str) -> "DateInterval":
        parts = value.split("-")
        if len(parts) == 1:
            year = int(parts[0])
            return cls(start=date(year, 1, 1), end=date(year, 12, 31), precision="year")
        if len(parts) == 2:
            year, month = map(int, parts)
            last_day = calendar.monthrange(year, month)[1]
            return cls(
                start=date(year, month, 1),
                end=date(year, month, last_day),
                precision="month",
            )
        if len(parts) == 3:
            exact = date.fromisoformat(value)
            return cls(start=exact, end=exact, precision="day")
        raise ValueError("date must have year, month, or day precision")


class CostEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    event_type: Literal[
        "award", "sanction_estimate", "revision_unavailable", "final_outturn"
    ]
    lane: Literal["total", "component", "schedule"]
    project_id: str
    award_id: str | None
    requirement_id: str | None
    effective_date: DateInterval
    source_available_date: DateInterval | None
    money: MoneyInterval | None
    evidence: Evidence
    source_title: str
    validation_group_id: str

    @property
    def historical_feature_eligible(self) -> bool:
        return self.source_available_date is not None

    @property
    def sort_key(self) -> tuple[date, date, str]:
        return self.effective_date.start, self.effective_date.end, self.event_id

    @model_validator(mode="after")
    def _validate_event(self) -> "CostEvent":
        if not _has_id(self.event_id, "evt-"):
            raise ValueError("event_id must use prefix evt-")
        if not _has_id(self.project_id, "prj-"):
            raise ValueError("project_id must use prefix prj-")
        if self.event_type == "award":
            if not _has_id(self.award_id, "awd-") or not _has_id(
                self.requirement_id, "req-"
            ):
                raise ValueError("award events require award and requirement IDs")
            if self.lane != "component":
                raise ValueError("award events must remain in the component lane")
        elif self.award_id is not None or self.requirement_id is not None:
            raise ValueError("non-award events must not carry award or requirement IDs")
        elif self.lane != "total":
            raise ValueError("project estimate events must remain in the total lane")
        parsed_url = urlparse(self.evidence.source_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("source URL must use http(s) with a nonempty http host")
        if self.event_type == "revision_unavailable" and self.money is not None:
            raise ValueError("revision_unavailable must not carry monetary data")
        if self.event_type != "revision_unavailable" and self.money is None:
            raise ValueError("monetary events must carry a money interval")
        if not self.source_title or not self.evidence.source_locator:
            raise ValueError("event source title and locator are required")
        return self


def order_events(events: tuple[CostEvent, ...]) -> tuple[CostEvent, ...]:
    return tuple(sorted(events, key=lambda event: event.sort_key))


def _find_data_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "modules" / "cost" / "curated"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("cost curated data root not found")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _resolve_locator(root: Path, table: str, locator: str) -> dict[str, str]:
    prefix = f"{table}:"
    if locator.startswith(prefix):
        locator = locator[len(prefix) :]
    elif ":" in locator:
        raise ValueError("source locator table does not match expected table")
    fields = dict(part.split("=", 1) for part in locator.split("|"))
    rows = _read_csv(root / table)
    matches = [
        row
        for row in rows
        if all(row.get(key) == value for key, value in fields.items())
    ]
    if len(matches) != 1:
        raise ValueError("event source locator must resolve uniquely")
    return matches[0]


def _resolve_source(root: Path, identity: dict[str, str]) -> dict[str, str]:
    return _resolve_locator(
        root, identity["SOURCE_TABLE"], identity["SOURCE_RECORD_LOCATOR"]
    )


def _active_ids(root: Path, filename: str) -> set[str]:
    return {
        row["OPAQUE_ID"]
        for row in _read_csv(root / filename)
        if row["STATE"] == "active" and row["ACTIVE"] == "true"
    }


def _validate_event_identities(identities: list[dict[str, str]]) -> None:
    seen: dict[str, dict[str, str]] = {}
    numbers = []
    for identity in identities:
        event_id = identity["OPAQUE_ID"]
        if event_id in seen and identity != seen[event_id]:
            raise ValueError("conflicting duplicate event identity")
        if not _has_id(event_id, "evt-") or not event_id[4:].isdigit():
            raise ValueError("invalid controlled event identity")
        seen[event_id] = identity
        numbers.append(int(event_id[4:]))
    if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
        raise ValueError("event identity registry must be unique and monotonic")


def _validate_foreign_keys(root: Path) -> None:
    projects = _active_ids(root, "cost_project_identity.csv")
    awards = _active_ids(root, "cost_award_identity.csv")
    requirements = _active_ids(root, "cost_requirement_identity.csv")
    for link in _read_csv(root / "award_asset_links.csv"):
        if link["PROJECT_ID"] not in projects:
            raise ValueError("broken project foreign key")
        if link["AWARD_ID"] not in awards:
            raise ValueError("broken award foreign key")
        linked_requirements = link["REQUIREMENT_IDS"].replace(";", "|").split("|")
        if any(requirement not in requirements for requirement in linked_requirements):
            raise ValueError("broken requirement foreign key")


def _validate_trace(events: tuple[CostEvent, ...], project_id: str) -> None:
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("conflicting duplicate event identity")
    if any(event.project_id != project_id for event in events):
        raise ValueError("broken event project foreign key")
    for lane in ("total", "component", "schedule"):
        bases = {
            (event.money.currency, event.money.price_basis)
            for event in events
            if event.lane == lane and event.money is not None
        }
        if len(bases) > 1:
            raise ValueError("mixed currency or price basis in trace lane")


def _money(
    value: str,
    *,
    value_basis: str,
    ownership: str,
    scope: str,
    capex: str,
    basis_year: int,
    currency: str = "USD",
) -> MoneyInterval:
    amount = Decimal(value)
    return MoneyInterval(
        currency=currency,
        price_basis="nominal",
        basis_year=basis_year,
        ownership_basis=ownership,
        scope_basis=scope,
        capex_basis=capex,
        value_basis=value_basis,
        bound_type="point",
        low_value=amount,
        high_value=amount,
        source_precision="USD million",
    )


def _evidence(
    row: dict[str, str],
    locator: str,
    *,
    derivation: Literal["disclosed", "todo"] = "disclosed",
) -> Evidence:
    return Evidence(
        derivation=derivation,
        source_provenance=row.get("PROVENANCE", row.get("SOURCE_PRIORITY", "")),
        source_url=row["SOURCE_URL"],
        source_locator=locator,
        confidence=row["CONFIDENCE"],
    )


def _single_match(
    rows: list[dict[str, str]], key: str, value: str, message: str
) -> dict[str, str]:
    matches = [row for row in rows if row[key] == value]
    if len(matches) != 1:
        raise ValueError(message)
    return matches[0]


def _award_fields(
    identity: dict[str, str], row: dict[str, str], root: Path
) -> dict[str, object]:
    locator = identity["SOURCE_RECORD_LOCATOR"]
    award = _single_match(
        _read_csv(root / "cost_award_identity.csv"),
        "SOURCE_RECORD_LOCATOR",
        locator,
        "broken award foreign key",
    )
    link = _single_match(
        _read_csv(root / "award_asset_links.csv"),
        "AWARD_ID",
        award["OPAQUE_ID"],
        "broken award-link foreign key",
    )
    link_source = _resolve_locator(root, "contract_awards.csv", link["SOURCE_LOCATOR"])
    if link_source != row:
        raise ValueError("award source locators disagree")
    included = link["COUNTING_DISPOSITION"] == "included"
    return {
        "event_type": "award",
        "lane": "component",
        "project_id": link["PROJECT_ID"],
        "award_id": award["OPAQUE_ID"],
        "requirement_id": link["REQUIREMENT_IDS"],
        "effective_date": DateInterval.from_text(row["AWARD_YEAR"]),
        "money": _money(
            row["VALUE_LOW_MM"],
            value_basis=row["VALUE_BASIS"],
            ownership="gross" if included else "third_party",
            scope="component" if included else "midstream",
            capex="component_capex" if included else "non_capex",
            basis_year=int(row["AWARD_YEAR"]),
        ),
        "evidence": Evidence(
            derivation=link["EVIDENCE_DERIVATION"],
            source_provenance=link["SOURCE_PROVENANCE"],
            source_url=link["SOURCE_URL"],
            source_locator=f"contract_awards.csv:{locator}",
            confidence=link["CONFIDENCE"],
        ),
    }


def _event_from_source(
    identity: dict[str, str], row: dict[str, str], root: Path, project_id: str
) -> CostEvent:
    table = identity["SOURCE_TABLE"]
    locator = identity["SOURCE_RECORD_LOCATOR"]
    if table == "contract_awards.csv":
        fields = _award_fields(identity, row, root)
    elif table == "cost_revision_trails.csv":
        fields = {
            "event_type": row["KIND"],
            "lane": "total",
            "project_id": project_id,
            "award_id": None,
            "requirement_id": None,
            "effective_date": DateInterval.from_text(row["STATEMENT_DATE"]),
            "money": _money(
                row["VALUE_MM"],
                value_basis="point",
                ownership="gross",
                scope="project",
                capex="project_capex",
                basis_year=int(row["STATEMENT_DATE"][:4]),
                currency=row["CURRENCY"],
            ),
            "evidence": _evidence(row, f"{table}:{locator}"),
        }
    else:
        if "May-2015 tendon failure" not in row["NOTES"]:
            raise ValueError("unavailable revision month is not evidenced")
        fields = {
            "event_type": "revision_unavailable",
            "lane": "total",
            "project_id": project_id,
            "award_id": None,
            "requirement_id": None,
            "effective_date": DateInterval.from_text("2015-05"),
            "money": None,
            "evidence": _evidence(row, f"{table}:{locator}", derivation="todo"),
        }
    return CostEvent(
        event_id=identity["OPAQUE_ID"],
        source_available_date=None,
        source_title=row["SOURCE_TITLE"],
        validation_group_id=identity["VALIDATION_GROUP_ID"],
        **fields,
    )


def build_big_foot_trace(data_root: Path | None = None) -> tuple[CostEvent, ...]:
    root = data_root or _find_data_root()
    identities = _read_csv(root / "cost_event_identity.csv")
    _validate_event_identities(identities)
    _validate_foreign_keys(root)
    projects = [
        row
        for row in _read_csv(root / "cost_project_identity.csv")
        if row["VALIDATION_GROUP_ID"] == _PILOT_GROUP
        and row["STATE"] == "active"
        and row["ACTIVE"] == "true"
    ]
    project = _single_match(
        projects, "ENTITY_KIND", "project", "pilot project ambiguous"
    )
    project_source = _resolve_source(root, project)
    identities = [
        row
        for row in identities
        if row["VALIDATION_GROUP_ID"] == _PILOT_GROUP
        and row["STATE"] == "active"
        and row["ACTIVE"] == "true"
    ]
    events = []
    for identity in identities:
        source = _resolve_source(root, identity)
        if source.get("PROJECT") != project_source["PROJECT"]:
            continue
        events.append(_event_from_source(identity, source, root, project["OPAQUE_ID"]))
    ordered = order_events(tuple(events))
    _validate_trace(ordered, project["OPAQUE_ID"])
    return ordered
