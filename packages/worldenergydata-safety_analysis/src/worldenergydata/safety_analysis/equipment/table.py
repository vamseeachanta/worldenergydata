# ABOUTME: Build, write and query the equipment failure table (one row per incident and class).
# ABOUTME: Each source is read with its URL and retrieval date so every count can be cited.

"""Equipment failure table.

``build_table`` reads the public source files named in a small source list,
classifies each record and returns rows keyed by equipment class. ``summarise``
turns the rows for one class into the counts a report section prints.

The table is plain CSV (plus a JSON summary), so a report generator in another
repository can read it without importing this package.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from worldenergydata.safety_analysis.equipment.classify import (
    COLUMNS,
    EquipmentFailureRow,
    classify_records,
)
from worldenergydata.safety_analysis.equipment.taxonomy import (
    BASIS_SOURCE_CODED,
    UNKNOWN,
    EQUIPMENT_CLASSES,
    FAILURE_MECHANISMS,
    FAILURE_MODES,
    NO_CAUSE,
)

# Text encodings by source: the BSEE export is Windows-1252.
_ENCODINGS = {
    "bsee_incident_investigations": "cp1252",
    "phmsa_hazardous_liquid": "utf-8",
}


@dataclass(frozen=True)
class SourceFile:
    """One input file with the provenance a citation needs."""

    source_id: str
    path: Path
    url: str
    retrieved: str  # ISO date the file was downloaded
    title: str = ""
    licence: str = ""

    def __post_init__(self) -> None:
        if not self.url.startswith("https://"):
            raise ValueError(f"{self.source_id}: source url must be https")
        try:
            ok = dt.date.fromisoformat(self.retrieved).isoformat() == self.retrieved
        except (TypeError, ValueError):
            ok = False
        if not ok:
            raise ValueError(f"{self.source_id}: retrieved must be YYYY-MM-DD")


@dataclass
class SourceStats:
    source_id: str
    title: str
    url: str
    licence: str
    retrieved: str
    records_read: int
    records_classified: int
    first_date: str
    last_date: str

    def as_record(self) -> dict:
        return dict(self.__dict__)


# Each group lists alternative column names; one of each group must be present.
REQUIRED_HEADERS: dict[str, tuple[tuple[str, ...], ...]] = {
    "bsee_incident_investigations": (("DATE_OCCURRED",), ("ACCIDENT_TYPE",)),
    "phmsa_hazardous_liquid": (
        ("REPORT_NUMBER", "Report Number"),
        ("LOCAL_DATETIME", "Accident Date/Time"),
        ("CAUSE", "Cause Category"),
    ),
}
_DELIMITERS = ("\t", ",", "|")


def read_records(source: SourceFile) -> list[dict]:
    """Read a delimited source file into dictionaries.

    The delimiter is taken from the header line (tab, comma or pipe), because
    the agency text exports are tab-separated and the curated exports are
    comma-separated. A file without the columns its classifier needs is an
    error, so a wrong layout cannot pass as zero matching records.
    """
    encoding = _ENCODINGS.get(source.source_id, "utf-8")
    with open(source.path, encoding=encoding, errors="replace", newline="") as fh:
        header = fh.readline()
        delimiter = max(_DELIMITERS, key=header.count)
        fh.seek(0)
        reader = csv.DictReader(fh, delimiter=delimiter)
        names = {
            (name or "").strip().lstrip("\ufeff") for name in reader.fieldnames or []
        }
        missing = [
            " or ".join(group)
            for group in REQUIRED_HEADERS.get(source.source_id, ())
            if not names & set(group)
        ]
        if missing:
            raise ValueError(
                f"{source.source_id}: {source.path.name} lacks required "
                f"column(s): {'; '.join(missing)}"
            )
        return list(reader)


def build_table(
    sources: Sequence[SourceFile],
) -> tuple[list[EquipmentFailureRow], list[SourceStats]]:
    """Classify every source file; return the rows and per-source statistics."""
    ids = [source.source_id for source in sources]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise ValueError(
            f"one file per source is supported; repeated: {', '.join(repeated)}. "
            "Join the files of one source before building the table."
        )
    rows: list[EquipmentFailureRow] = []
    stats: list[SourceStats] = []
    for source in sources:
        records = read_records(source)
        got = classify_records(
            source.source_id, records, source_url=source.url, retrieved=source.retrieved
        )
        all_dates = sorted(
            d
            for d in (classify_date(source.source_id, record) for record in records)
            if d
        )
        stats.append(
            SourceStats(
                source_id=source.source_id,
                title=source.title,
                url=source.url,
                licence=source.licence,
                retrieved=source.retrieved,
                records_read=len(records),
                records_classified=len({r.source_record_id for r in got}),
                first_date=all_dates[0] if all_dates else "",
                last_date=all_dates[-1] if all_dates else "",
            )
        )
        rows.extend(got)
    rows.sort(key=lambda r: (r.equipment_class, r.date, r.source_record_id))
    return rows, stats


def classify_date(source_id: str, record: dict) -> str:
    """ISO date of a raw record, whether or not it classifies."""
    from worldenergydata.safety_analysis.equipment import classify as c

    if source_id == "bsee_incident_investigations":
        return c.iso_date(record.get("DATE_OCCURRED", ""))
    if source_id == "phmsa_hazardous_liquid":
        return c.iso_date(c.phmsa_field(record, "date"))
    return ""


def write_csv(rows: Iterable[EquipmentFailureRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_record())


def read_csv(path: Path) -> list[EquipmentFailureRow]:
    with open(path, encoding="utf-8", newline="") as fh:
        out = []
        for rec in csv.DictReader(fh):
            for flag in ("fatality", "injury", "pollution"):
                rec[flag] = rec[flag] == "True"
            out.append(EquipmentFailureRow(**rec))
        return out


def query(
    rows: Iterable[EquipmentFailureRow],
    equipment_class: str,
    *,
    subclass: Optional[str] = None,
) -> list[EquipmentFailureRow]:
    """Rows for one equipment class (and optionally one subclass)."""
    if equipment_class not in EQUIPMENT_CLASSES:
        raise KeyError(
            f"unknown equipment class {equipment_class!r}; "
            f"known: {sorted(EQUIPMENT_CLASSES)}"
        )
    return [
        r
        for r in rows
        if r.equipment_class == equipment_class
        and (subclass is None or r.equipment_subclass == subclass)
    ]


def summarise(rows: Sequence[EquipmentFailureRow]) -> dict:
    """Counts for a set of rows (normally one equipment class).

    ``by_failure_mode`` counts a record once under each of its event types, so
    the mode counts can add up to more than ``records``.
    """
    modes: Counter = Counter()
    for r in rows:
        for mode in r.failure_modes.split(";"):
            modes[mode] += 1
    mechanisms = Counter(r.mechanism for r in rows)
    coded = [r for r in rows if r.mechanism_basis == BASIS_SOURCE_CODED]
    dates = sorted(r.date for r in rows if r.date)
    decades: Counter = Counter(f"{d[:3]}0s" for d in dates)
    return {
        "records": len(rows),
        "first_date": dates[0] if dates else "",
        "last_date": dates[-1] if dates else "",
        "by_source": dict(sorted(Counter(r.source_id for r in rows).items())),
        "by_subclass": dict(
            sorted(Counter(r.equipment_subclass for r in rows).items())
        ),
        "by_decade": dict(sorted(decades.items())),
        "by_failure_mode": [
            {"key": k, "label": FAILURE_MODES[k].label, "records": n}
            for k, n in sorted(modes.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "by_mechanism": [
            {"key": k, "label": FAILURE_MECHANISMS[k].label, "records": n}
            for k, n in sorted(mechanisms.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "mechanism_stated": sum(1 for r in rows if r.mechanism not in NO_CAUSE),
        # Records whose source has a coded cause field (the code may be "unknown").
        "cause_coded": len(coded),
        "cause_coded_unknown": sum(1 for r in coded if r.mechanism == UNKNOWN),
        "cause_not_coded": len(rows) - len(coded),
        "by_coded_cause": [
            {"key": k, "label": FAILURE_MECHANISMS[k].label, "records": n}
            for k, n in sorted(
                Counter(r.mechanism for r in coded).items(),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ],
        "with_fatality": sum(1 for r in rows if r.fatality),
        "with_injury": sum(1 for r in rows if r.injury),
        "with_pollution": sum(1 for r in rows if r.pollution),
    }


def coverage(rows: Sequence[EquipmentFailureRow]) -> list[dict]:
    """One line per equipment class: how much the table holds."""
    out = []
    for key, term in EQUIPMENT_CLASSES.items():
        s = summarise(query(rows, key))
        out.append(
            {
                "equipment_class": key,
                "label": term.label,
                "records": s["records"],
                "first_date": s["first_date"],
                "last_date": s["last_date"],
                "mechanism_stated": s["mechanism_stated"],
                "sources": ", ".join(s["by_source"]),
                "note": term.note,
            }
        )
    return out


def write_summary(
    rows: Sequence[EquipmentFailureRow], stats: Sequence[SourceStats], path: Path
) -> dict:
    payload = {
        "sources": [s.as_record() for s in stats],
        "coverage": coverage(rows),
        "by_class": {key: summarise(query(rows, key)) for key in EQUIPMENT_CLASSES},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
