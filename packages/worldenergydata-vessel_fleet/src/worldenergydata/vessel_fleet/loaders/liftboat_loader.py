"""Offline liftboat tables with per-observation provenance and strict keys."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import date, datetime
from io import StringIO
from pathlib import Path

VESSEL_FIELDS = (
    "vessel_name",
    "imo_number",
    "leg_length_ft",
    "leg_count",
    "deck_area_sq_ft",
    "variable_deck_load_lb",
    "deck_cargo_capacity_lb",
    "main_crane_capacity",
    "main_crane_capacity_unit",
    "water_depth_rating_ft",
    "class_society",
    "flag",
    "year_built",
    "builder",
    "design",
)
INCIDENT_FIELDS = (
    "vessel_name",
    "incident_date",
    "report_date",
    "agency",
    "report_number",
    "phase",
    "conditions",
    "failure_mode",
    "injuries",
    "fatalities",
    "missing_presumed_dead",
    "notes",
)
CROSSWALK_FIELDS = ("seed_name", "resolution", "resolution_note")
TABLE_FIELDS = {
    "liftboats.csv": VESSEL_FIELDS,
    "incidents.csv": INCIDENT_FIELDS,
    "seed_crosswalk.csv": CROSSWALK_FIELDS,
}
TABLE_KEYS = {
    "liftboats.csv": ("liftboat_id",),
    "incidents.csv": ("incident_id", "liftboat_id"),
    "seed_crosswalk.csv": ("liftboat_id",),
}
_DEFAULT_DIR = Path(__file__).resolve().parents[1] / "_data" / "liftboats"
_CONFIDENCE = {"high", "medium", "low"}
_PHASES = {"transit", "jacking", "preload", "elevated", "storm"}
_POSITIVE = {
    "leg_length_ft",
    "deck_area_sq_ft",
    "variable_deck_load_lb",
    "deck_cargo_capacity_lb",
    "main_crane_capacity",
    "water_depth_rating_ft",
}
_COUNTS = {"injuries", "fatalities", "missing_presumed_dead"}


def _name(value: str) -> str:
    return " ".join(value.upper().split())


def _unique(values: list[str], label: str) -> None:
    if any(not value for value in values) or len(set(values)) != len(values):
        raise ValueError(f"empty or duplicate {label}")


def _validate_value(field: str, value: str) -> None:
    if not value:
        return
    if field in _POSITIVE:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError(f"invalid positive number: {field}")
    if field in _COUNTS | {"leg_count", "year_built"}:
        if not re.fullmatch(r"\d+", value):
            raise ValueError(f"invalid integer: {field}")
        if field in {"leg_count", "year_built"} and int(value) == 0:
            raise ValueError(f"invalid positive integer: {field}")
        if field == "leg_count" and int(value) not in {3, 4}:
            raise ValueError("liftboat leg_count must be 3 or 4")
        if field == "year_built" and not 1800 <= int(value) <= date.today().year:
            raise ValueError("invalid year_built")
    if field in {"incident_date", "report_date"}:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(f"invalid date: {field}")
        date.fromisoformat(value)
    if field == "imo_number":
        if not re.fullmatch(r"\d{7}", value):
            raise ValueError("invalid IMO number")
        if sum(
            int(n) * weight for n, weight in zip(value[:6], range(7, 1, -1))
        ) % 10 != int(value[-1]):
            raise ValueError("invalid IMO check digit")
    if field == "phase" and value not in _PHASES:
        raise ValueError("invalid phase")
    if field == "agency" and value not in {"NTSB", "USCG", "BSEE"}:
        raise ValueError("invalid agency")
    if field == "resolution" and value not in {"matched", "unresolved"}:
        raise ValueError("invalid resolution")


class LiftboatLoader:
    """Load string-valued evidence tables; empty strings mean unreported.

    Package data is used by default. A custom directory must contain the same
    three CSV tables and a manifest. All tables are validated together before
    any rows are returned; returned rows are independent copies.
    """

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else _DEFAULT_DIR
        self._manifest: dict | None = None
        self._tables: dict[str, list[dict[str, str]]] | None = None

    @property
    def manifest(self) -> dict:
        if self._manifest is None:
            manifest = json.loads(
                (self.data_dir / "manifest.json").read_text(encoding="utf-8")
            )
            if manifest.get("schema_version") != 1:
                raise ValueError("unsupported liftboat schema_version")
            if set(manifest["tables"]) != set(TABLE_FIELDS):
                raise ValueError("unexpected manifest tables")
            for source in manifest["sources"].values():
                for field in (
                    "url",
                    "terms",
                    "terms_url",
                    "retrieved_at",
                    "digest_scope",
                ):
                    if not source.get(field):
                        raise ValueError(f"source missing {field}")
                if not source["url"].startswith("https://"):
                    raise ValueError("source URL must use HTTPS")
                if not re.fullmatch(r"[a-f0-9]{64}", source["sha256"]):
                    raise ValueError("invalid source digest")
                observed = datetime.fromisoformat(
                    source["retrieved_at"].replace("Z", "+00:00")
                )
                if observed.tzinfo is None:
                    raise ValueError("retrieval timestamp must include timezone")
            self._manifest = manifest
        return deepcopy(self._manifest)

    @property
    def tables(self) -> dict[str, list[dict[str, str]]]:
        if self._tables is None:
            manifest = self.manifest
            tables = {}
            for table, fields in TABLE_FIELDS.items():
                payload = (self.data_dir / table).read_bytes()
                if (
                    hashlib.sha256(payload).hexdigest()
                    != manifest["tables"][table]["sha256"]
                ):
                    raise ValueError(f"table digest mismatch: {table}")
                reader = csv.reader(StringIO(payload.decode("utf-8")), strict=True)
                expected = list(TABLE_KEYS[table]) + [
                    column
                    for field in fields
                    for column in (field, field + "_source", field + "_confidence")
                ]
                if next(reader, None) != expected:
                    raise ValueError(f"invalid columns: {table}")
                rows = []
                for values in reader:
                    if len(values) != len(expected):
                        raise ValueError(f"invalid CSV width: {table}")
                    row = dict(zip(expected, values))
                    self._validate_observations(row, fields, manifest["sources"])
                    rows.append(row)
                if len(rows) != manifest["tables"][table]["row_count"]:
                    raise ValueError(f"row count mismatch: {table}")
                tables[table] = rows
            self._validate_keys(tables)
            self._tables = tables
        return deepcopy(self._tables)

    @staticmethod
    def _validate_observations(row: dict, fields: tuple, sources: dict) -> None:
        for field in fields:
            value, source, confidence = (
                row[field + suffix] for suffix in ("", "_source", "_confidence")
            )
            if not value:
                if source or confidence:
                    raise ValueError(f"provenance for empty value: {field}")
                continue
            if not value.strip():
                raise ValueError(f"whitespace value: {field}")
            if source.partition("#")[0] not in sources or confidence not in _CONFIDENCE:
                raise ValueError(f"missing or invalid provenance: {field}")
            _validate_value(field, value)

    @staticmethod
    def _validate_keys(tables: dict) -> None:
        vessels = tables["liftboats.csv"]
        incidents = tables["incidents.csv"]
        crosswalk = tables["seed_crosswalk.csv"]
        ids = [row["liftboat_id"] for row in vessels]
        _unique(ids, "liftboat_id")
        _unique([_name(row["vessel_name"]) for row in vessels], "vessel_name")
        _unique(
            [row["imo_number"] for row in vessels if row["imo_number"]], "IMO number"
        )
        _unique([row["incident_id"] for row in incidents], "incident_id")
        _unique([_name(row["seed_name"]) for row in crosswalk], "seed_name")
        for row in incidents + crosswalk:
            if row["liftboat_id"] and row["liftboat_id"] not in ids:
                raise ValueError("invalid liftboat foreign key")
        for row in crosswalk:
            if (row["resolution"] == "matched") != bool(row["liftboat_id"]):
                raise ValueError("crosswalk resolution contradicts foreign key")
        for row in vessels:
            if bool(row["main_crane_capacity"]) != bool(
                row["main_crane_capacity_unit"]
            ):
                raise ValueError("crane capacity requires source unit")
        for row in incidents:
            if not row["agency"] or not row["report_number"] or not row["failure_mode"]:
                raise ValueError(
                    "incident requires agency, report_number and failure_mode"
                )
            if row["missing_presumed_dead"] and row["fatalities"]:
                if int(row["missing_presumed_dead"]) > int(row["fatalities"]):
                    raise ValueError("presumed dead exceeds total fatalities")
        aliases = {_name(row["vessel_name"]): row["liftboat_id"] for row in vessels}
        for row in crosswalk:
            name, identity = _name(row["seed_name"]), row["liftboat_id"]
            if identity and name in aliases and aliases[name] != identity:
                raise ValueError("ambiguous alias")
            if identity:
                aliases[name] = identity
        for row in incidents:
            expected = aliases.get(_name(row["vessel_name"]))
            if expected != (row["liftboat_id"] or None):
                raise ValueError("incident identity contradicts vessel name")
        events = [
            (
                row["agency"],
                row["report_number"],
                _name(row["vessel_name"]),
                row["incident_date"],
            )
            for row in incidents
        ]
        if len(set(events)) != len(events):
            raise ValueError("duplicate incident event")

    def load(self) -> list[dict[str, str]]:
        """Return unique named vessel records without inferring missing values."""
        return self.tables["liftboats.csv"]

    def load_incidents(self) -> list[dict[str, str]]:
        """Return report records, including anonymous and historical incidents."""
        return self.tables["incidents.csv"]

    def load_seed_crosswalk(self) -> list[dict[str, str]]:
        """Return every selected seed label, including unresolved labels."""
        return self.tables["seed_crosswalk.csv"]

    def get_by_name(self, name: str) -> dict[str, str] | None:
        """Match canonical or seed names, ignoring only case and whitespace."""
        tables = self.tables
        vessels = tables["liftboats.csv"]
        for row in vessels:
            if _name(row["vessel_name"]) == _name(name):
                return row
        for alias in tables["seed_crosswalk.csv"]:
            if _name(alias["seed_name"]) == _name(name) and alias["liftboat_id"]:
                return next(
                    row for row in vessels if row["liftboat_id"] == alias["liftboat_id"]
                )
        return None

    def incidents_for(self, liftboat_id: str) -> list[dict[str, str]]:
        """Return records linked to a known vessel key; reject unknown keys."""
        tables = self.tables
        if liftboat_id not in {row["liftboat_id"] for row in tables["liftboats.csv"]}:
            raise KeyError(liftboat_id)
        return [
            row for row in tables["incidents.csv"] if row["liftboat_id"] == liftboat_id
        ]
