# ABOUTME: Strict parser and descriptor-relative reader for Landman fixtures.
# ABOUTME: Converts closed-schema public JSON into validated ownership records.

"""Fail-closed fixture schema and direct-child custom-file loading."""

import json
import math
import os
import stat
from dataclasses import dataclass
from datetime import date
from importlib import resources
from typing import Any, Mapping

from .exceptions import FixtureValidationError
from .models import InterestType, MineralOwnershipRecord
from .routing import validate_records_file_name
from .validators import LandmanDataValidator


MAX_FIXTURE_BYTES = 1024 * 1024
MAX_FIXTURE_RECORDS = 1000
ROOT_KEYS = {"schema_version", "dataset_id", "mode", "records"}
REQUIRED_RECORD_KEYS = {
    "record_id",
    "state",
    "county",
    "legal_description",
    "owner_name",
}
OPTIONAL_RECORD_KEYS = {
    "interest_type",
    "mineral_interest_percent",
    "net_mineral_acres",
    "gross_acres",
    "effective_date",
    "source_document",
    "grantor",
    "recorded_date",
    "book",
    "page",
    "volume",
    "instrument_number",
    "notes",
}
DATE_FIELDS = {"effective_date", "recorded_date"}
NUMERIC_FIELDS = {"mineral_interest_percent", "net_mineral_acres", "gross_acres"}


@dataclass(frozen=True)
class FixtureDataset:
    """Validated immutable fixture metadata and records."""

    dataset_id: str
    records: tuple[MineralOwnershipRecord, ...]


def _reject(source: str, reason: str, code: str = "LANDMAN_FIXTURE_SCHEMA_INVALID"):
    raise FixtureValidationError(code, source, reason)


def _reject_constant(value: str):
    raise ValueError(f"non-standard numeric constant {value}")


def _strict_number(value: Any, field: str, source: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _reject(source, f"{field} must be a JSON number")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        _reject(source, f"{field} must be a finite JSON number")
    if not math.isfinite(number):
        _reject(source, f"{field} must be finite")
    return number


def _strict_date(value: Any, field: str, source: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        _reject(source, f"{field} must use ISO YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _reject(source, f"{field} must use ISO YYYY-MM-DD")
    if parsed.isoformat() != value:
        _reject(source, f"{field} must use ISO YYYY-MM-DD")
    return parsed


def _required_string(record: Mapping[str, Any], field: str, source: str) -> str:
    value = record[field]
    if not isinstance(value, str) or not value.strip():
        _reject(source, f"{field} must be a non-empty string")
    return value


def _optional_values(record: Mapping[str, Any], source: str) -> dict[str, Any]:
    values = {}
    for field in OPTIONAL_RECORD_KEYS:
        if field not in record or record[field] is None:
            continue
        value = record[field]
        if field in NUMERIC_FIELDS:
            values[field] = _strict_number(value, field, source)
        elif field in DATE_FIELDS:
            values[field] = _strict_date(value, field, source)
        elif field == "interest_type":
            try:
                values[field] = InterestType(value)
            except (TypeError, ValueError):
                _reject(source, "interest_type is invalid")
        elif not isinstance(value, str):
            _reject(source, f"{field} must be a string")
        else:
            values[field] = value
    return values


def _validate_existing_rules(values: dict[str, Any], source: str) -> None:
    validator = LandmanDataValidator()
    valid, errors = validator.validate_ownership_record(values)
    if not valid:
        _reject(source, "; ".join(errors))
    if "gross_acres" in values:
        valid, error = validator.validate_acreage(values["gross_acres"])
        if not valid:
            _reject(source, f"Gross acreage: {error}")


def _parse_record(record: Any, source: str) -> MineralOwnershipRecord:
    if not isinstance(record, dict):
        _reject(source, "each record must be an object")
    keys = set(record)
    missing = REQUIRED_RECORD_KEYS - keys
    unknown = keys - REQUIRED_RECORD_KEYS - OPTIONAL_RECORD_KEYS
    if missing or unknown:
        _reject(
            source,
            f"record keys invalid; missing={sorted(missing)}, unknown={sorted(unknown)}",
        )
    values = {
        field: _required_string(record, field, source) for field in REQUIRED_RECORD_KEYS
    }
    values.update(_optional_values(record, source))
    _validate_existing_rules(values, source)
    return MineralOwnershipRecord(**values)


def parse_fixture_bytes(data: bytes, source_name: str) -> FixtureDataset:
    """Parse bounded UTF-8 JSON using the closed fixture schema."""
    if len(data) > MAX_FIXTURE_BYTES:
        _reject(source_name, "file exceeds 1 MiB", "LANDMAN_FIXTURE_TOO_LARGE")
    try:
        payload = json.loads(data.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        _reject(source_name, "content is not strict UTF-8 JSON")
    if not isinstance(payload, dict) or set(payload) != ROOT_KEYS:
        _reject(source_name, "root keys must match the fixture schema exactly")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        _reject(source_name, "schema_version must be integer 1")
    if payload["mode"] != "fixture-only":
        _reject(source_name, "mode must be fixture-only")
    if not isinstance(payload["dataset_id"], str) or not payload["dataset_id"].strip():
        _reject(source_name, "dataset_id must be a non-empty string")
    if not isinstance(payload["records"], list):
        _reject(source_name, "records must be an array")
    if len(payload["records"]) > MAX_FIXTURE_RECORDS:
        _reject(source_name, "records exceeds 1000 entries")
    records = tuple(_parse_record(row, source_name) for row in payload["records"])
    identifiers = [record.record_id for record in records]
    if len(identifiers) != len(set(identifiers)):
        _reject(source_name, "record_id values must be unique")
    return FixtureDataset(payload["dataset_id"], records)


def _descriptor_support_available() -> bool:
    return (
        os.open in os.supports_dir_fd
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_CLOEXEC")
        and hasattr(os, "O_NONBLOCK")
    )


def _read_descriptor(fd: int, source: str) -> bytes:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        _reject(
            source,
            "custom fixture must be a regular file",
            "LANDMAN_FIXTURE_PATH_INVALID",
        )
    if info.st_size > MAX_FIXTURE_BYTES:
        _reject(source, "file exceeds 1 MiB", "LANDMAN_FIXTURE_TOO_LARGE")
    chunks = []
    remaining = MAX_FIXTURE_BYTES + 1
    while remaining:
        chunk = os.read(fd, min(65536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    if len(data) > MAX_FIXTURE_BYTES:
        _reject(source, "file exceeds 1 MiB", "LANDMAN_FIXTURE_TOO_LARGE")
    return data


def read_custom_fixture(records_file: str) -> FixtureDataset:
    """Open one direct child of CWD by descriptor and parse from that same fd."""
    name = validate_records_file_name(records_file)
    if not _descriptor_support_available():
        _reject(
            name,
            "secure descriptor-relative open is unavailable",
            "LANDMAN_FIXTURE_UNSUPPORTED",
        )
    root_fd = -1
    file_fd = -1
    try:
        root_fd = os.open(".", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
        file_fd = os.open(name, flags, dir_fd=root_fd)
        return parse_fixture_bytes(_read_descriptor(file_fd, name), name)
    except FixtureValidationError:
        raise
    except OSError:
        _reject(name, "custom fixture could not be opened", "LANDMAN_FIXTURE_IO")
    finally:
        if file_fd >= 0:
            os.close(file_fd)
        if root_fd >= 0:
            os.close(root_fd)


def read_packaged_fixture() -> FixtureDataset:
    """Read the known bundled sample through importlib resources."""
    name = "county_records_v1.json"
    data = (
        resources.files("worldenergydata.landman.fixtures").joinpath(name).read_bytes()
    )
    return parse_fixture_bytes(data, name)
