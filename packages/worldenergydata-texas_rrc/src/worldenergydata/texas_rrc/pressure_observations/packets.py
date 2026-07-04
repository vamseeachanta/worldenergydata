"""Parse Texas RRC brace-delimited completion packet pressure candidates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from worldenergydata.texas_rrc.lifecycle.keys import derive_api10, normalize_api14
from worldenergydata.texas_rrc.pressure_observations.packet_schema import (
    field_index,
    pressure_fields_for,
)

PACKET_CONTEXT_INDEXES = {
    "source_tracking_no": 1,
    "source_packet_id": 2,
    "operator_number": 5,
    "api_number": 6,
    "lease_number": 8,
    "packet_completion_date": 21,
    "field_no": 25,
    "district": 27,
    "field_name": 29,
}

BASE_COLUMNS = (
    "api14",
    "api10",
    "district",
    "field_no",
    "field_name",
    "lease_number",
    "operator_number",
    "test_date",
    "test_year",
    "source_record_type",
    "source_pressure_field",
    "pressure_raw_psi",
    "source_tracking_no",
    "source_packet_id",
    "source_form_id",
    "source_row_no",
    "source_file",
    "source_row_id",
    "bottom_hole_depth_ft",
    "vertical_depth_ft",
    "measured_depth_ft",
    "plug_back_depth_ft",
    "production_interval_from_ft",
    "production_interval_to_ft",
    "reference_formation",
)


@dataclass(frozen=True)
class PacketParseResult:
    """Pressure candidates and parser quality counts from one packet text."""

    candidates: pd.DataFrame
    malformed_row_count: int = 0
    unlinked_row_count: int = 0


def read_packet_pressure_candidates(
    text: str,
    source_file: str = "",
) -> PacketParseResult:
    """Read brace-delimited packet text into normalized pressure candidates."""
    packet_contexts: dict[tuple[str, str], dict[str, str]] = {}
    form_contexts: dict[tuple[str, str, str], dict[str, str]] = {}
    rows: list[dict[str, Any]] = []
    malformed_count = 0
    unlinked_count = 0

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        fields = [part.strip() for part in raw_line.rstrip("\r\n").split("{")]
        record_type = fields[0] if fields else ""
        if not record_type:
            continue
        if record_type == "PACKET":
            context = _packet_context(fields)
            if context:
                packet_contexts[
                    (context["source_tracking_no"], context["source_packet_id"])
                ] = context
            continue
        if record_type in {
            "G-1 Production Interval Data",
            "W-2 Production Interval Data",
        }:
            form_key = (_field(fields, 1), _field(fields, 2), _field(fields, 3))
            form = form_contexts.setdefault(form_key, {"source_form_id": form_key[2]})
            form.update(_interval_context(record_type, fields))
            _apply_form_context_to_existing_rows(rows, form_key, form)
            continue
        if record_type in {"G-1 Formation Data", "W-2 Formation Data"}:
            form_key = (_field(fields, 1), _field(fields, 2), _field(fields, 3))
            form = form_contexts.setdefault(form_key, {"source_form_id": form_key[2]})
            form.update(_formation_context(record_type, fields))
            _apply_form_context_to_existing_rows(rows, form_key, form)
            continue
        if not _pressure_relevant(record_type):
            continue
        if len(fields) < 4:
            malformed_count += 1
            continue

        key = (_field(fields, 1), _field(fields, 2))
        packet = packet_contexts.get(key)
        if packet is None:
            unlinked_count += 1
            continue

        if record_type in {"G-1", "G-10", "W-2"}:
            form = _form_context(record_type, fields)
            form_key = (key[0], key[1], form["source_form_id"])
            form_contexts.setdefault(form_key, {}).update(form)
        else:
            form_id = _field(fields, 3)
            form = form_contexts.get((key[0], key[1], form_id), {})

        rows.extend(
            _candidate_rows(
                fields,
                packet=packet,
                form=form,
                record_type=record_type,
                source_file=source_file,
                line_number=line_number,
            )
        )

    return PacketParseResult(
        candidates=pd.DataFrame(rows, columns=BASE_COLUMNS),
        malformed_row_count=malformed_count,
        unlinked_row_count=unlinked_count,
    )


def _pressure_relevant(record_type: str) -> bool:
    return bool(pressure_fields_for(record_type))


def _packet_context(fields: list[str]) -> dict[str, str]:
    context = {
        key: _field(fields, index) for key, index in PACKET_CONTEXT_INDEXES.items()
    }
    if not context["source_tracking_no"] or not context["source_packet_id"]:
        return {}
    api14 = normalize_api14(context["api_number"])
    context["api14"] = api14 or ""
    context["api10"] = derive_api10(api14) or ""
    return context


def _form_context(record_type: str, fields: list[str]) -> dict[str, str]:
    form_id_name = {
        "G-1": "G1_ID",
        "G-10": "G10_ID",
        "W-2": "W2_ID",
    }[record_type]
    form = {
        "source_form_id": _field(fields, field_index(record_type, form_id_name)),
        "test_date": _form_test_date(record_type, fields),
    }
    if record_type == "G-1":
        form.update(
            {
                "bottom_hole_depth_ft": _numeric(
                    _field(fields, field_index(record_type, "BOTTOM_HOLE_DEPTH"))
                ),
                "vertical_depth_ft": _numeric(
                    _field(fields, field_index(record_type, "VERTICAL_DEPTH"))
                ),
                "measured_depth_ft": _numeric(
                    _field(fields, field_index(record_type, "MEASURED_DEPTH"))
                ),
                "plug_back_depth_ft": _numeric(
                    _field(fields, field_index(record_type, "PLUG_BACK_DEPTH"))
                ),
            }
        )
    return form


def _interval_context(record_type: str, fields: list[str]) -> dict[str, float | None]:
    return {
        "production_interval_from_ft": _numeric(
            _field(fields, field_index(record_type, "FROM"))
        ),
        "production_interval_to_ft": _numeric(
            _field(fields, field_index(record_type, "TO"))
        ),
    }


def _formation_context(record_type: str, fields: list[str]) -> dict[str, str]:
    formation = _field(fields, field_index(record_type, "FORMATION"))
    return {"reference_formation": formation}


def _form_test_date(record_type: str, fields: list[str]) -> str:
    for name in ("DATE_OF_TEST", "DATE_TESTED", "EFFECTIVE_DT"):
        try:
            value = _parse_date(_field(fields, field_index(record_type, name)))
        except KeyError:
            continue
        if value:
            return value
    return ""


def _candidate_rows(
    fields: list[str],
    *,
    packet: dict[str, str],
    form: dict[str, str],
    record_type: str,
    source_file: str,
    line_number: int,
) -> list[dict[str, Any]]:
    rows = []
    for pressure_field in pressure_fields_for(record_type):
        raw_value = _field(fields, field_index(record_type, pressure_field))
        pressure = _numeric(raw_value)
        if pressure is None:
            continue
        test_date = form.get("test_date", "")
        row = {
            "api14": packet.get("api14", ""),
            "api10": packet.get("api10", ""),
            "district": packet.get("district", ""),
            "field_no": packet.get("field_no", ""),
            "field_name": packet.get("field_name", ""),
            "lease_number": packet.get("lease_number", ""),
            "operator_number": packet.get("operator_number", ""),
            "test_date": test_date,
            "test_year": _test_year(test_date),
            "source_record_type": record_type,
            "source_pressure_field": pressure_field,
            "pressure_raw_psi": pressure,
            "source_tracking_no": _field(fields, 1),
            "source_packet_id": _field(fields, 2),
            "source_form_id": _field(fields, 3),
            "source_row_no": _source_row_no(record_type, fields),
            "source_file": source_file,
            "source_row_id": f"{source_file}:{line_number}:{pressure_field}",
        }
        row.update(_candidate_context(form))
        rows.append(row)
    return rows


def _candidate_context(form: dict[str, Any]) -> dict[str, Any]:
    return {
        "bottom_hole_depth_ft": form.get("bottom_hole_depth_ft"),
        "vertical_depth_ft": form.get("vertical_depth_ft"),
        "measured_depth_ft": form.get("measured_depth_ft"),
        "plug_back_depth_ft": form.get("plug_back_depth_ft"),
        "production_interval_from_ft": form.get("production_interval_from_ft"),
        "production_interval_to_ft": form.get("production_interval_to_ft"),
        "reference_formation": form.get("reference_formation", ""),
    }


def _apply_form_context_to_existing_rows(
    rows: list[dict[str, Any]],
    form_key: tuple[str, str, str],
    form: dict[str, Any],
) -> None:
    tracking_no, packet_id, form_id = form_key
    context = _candidate_context(form)
    for row in rows:
        if (
            row["source_tracking_no"] == tracking_no
            and row["source_packet_id"] == packet_id
            and row["source_form_id"] == form_id
        ):
            row.update(context)


def _source_row_no(record_type: str, fields: list[str]) -> str:
    try:
        return _field(fields, field_index(record_type, "ROW_NO"))
    except KeyError:
        return ""


def _field(fields: list[str], index: int) -> str:
    if index >= len(fields):
        return ""
    return fields[index].strip()


def _parse_date(value: str) -> str:
    text = value.strip()
    if not text or text == "00000000":
        return ""
    if len(text) == 8 and text.isdigit():
        try:
            return date(int(text[:4]), int(text[4:6]), int(text[6:8])).isoformat()
        except ValueError:
            return ""
    if "/" in text:
        parts = text.split("/")
        if len(parts) != 3:
            return ""
        try:
            month, day, year = (int(part) for part in parts)
            return date(year, month, day).isoformat()
        except ValueError:
            return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return ""


def _numeric(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _test_year(test_date: str) -> int | None:
    if not test_date:
        return None
    try:
        return int(test_date[:4])
    except ValueError:
        return None


__all__ = [
    "PacketParseResult",
    "read_packet_pressure_candidates",
]
