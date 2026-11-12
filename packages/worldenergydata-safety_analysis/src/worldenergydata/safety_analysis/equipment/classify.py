# ABOUTME: Rule-based mapping of public incident records to equipment class, failure mode and mechanism.
# ABOUTME: Rules read only source fields; a mechanism comes from a source-coded cause, never from inference.

"""Classify incident records against the equipment failure taxonomy.

Two public record layouts are supported:

* BSEE incident investigations (``mv_acc_investigations.txt``): the
  ``ACCIDENT_TYPE`` field is an event type. It gives equipment class and failure
  mode. It gives **no cause**, so the mechanism is always ``not_stated``.
* PHMSA pipeline accident reports (hazardous liquid): the agency codes a cause
  category and subcategory. The mechanism is mapped from that coded cause and
  the source text is kept beside it.

Every rule is a regular expression over a named source field, so a reader can
trace each row of the table to the source text that produced it. A record can
belong to more than one equipment class and carry more than one failure mode.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Optional

from worldenergydata.safety_analysis.equipment.taxonomy import (
    BASIS_NONE,
    BASIS_SOURCE_CODED,
    NOT_STATED,
    UNKNOWN,
)

COLUMNS = (
    "equipment_class",
    "equipment_subclass",
    "source_id",
    "source_record_id",
    "date",
    "location",
    "event_text",
    "failure_modes",
    "mechanism",
    "mechanism_basis",
    "mechanism_source_text",
    "fatality",
    "injury",
    "pollution",
    "classification_rule",
    "source_url",
    "retrieved",
)


@dataclass
class EquipmentFailureRow:
    """One (incident, equipment class) row of the equipment failure table."""

    equipment_class: str
    equipment_subclass: str
    source_id: str
    source_record_id: str
    date: str
    location: str
    event_text: str
    failure_modes: str  # ";"-joined, sorted
    mechanism: str = NOT_STATED
    mechanism_basis: str = BASIS_NONE
    mechanism_source_text: str = ""
    fatality: bool = False
    injury: bool = False
    pollution: bool = False
    classification_rule: str = ""
    source_url: str = ""
    retrieved: str = ""

    def as_record(self) -> dict:
        return asdict(self)


def _rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


# --- BSEE incident investigations --------------------------------------------
# Equipment class <- ACCIDENT_TYPE. Order is not a precedence: all matches apply.
BSEE_EQUIPMENT_RULES: tuple[tuple[str, re.Pattern], ...] = (
    ("riser", _rx(r"\brisers?\b|\bflowline\b|\bjumper\b|\bSCR\b|\bSLWR\b")),
    (
        "mooring_line",
        _rx(
            r"\bmoor|\banchor|loss of station|drift[- ]?off|station[- ]keep"
            r"|\btendon"
        ),
    ),
    ("pipeline", _rx(r"\bpipeline\b|subsea leak")),
    (
        "jack_up",
        _rx(r"jack-?up|lift ?boat|leg fracture|rig move|punch[- ]?through"),
    ),
    (
        "lifting_rigging",
        _rx(
            r"\bcrane|lifting device|\bhoist|\brigging\b|dropped|falling object"
            r"|lost overboard|unplanned descent"
        ),
    ),
    (
        "wellhead_conductor",
        _rx(
            r"wellhead|\bconductor|\bcasing\b|\btree\b|blowout|well control"
            r"|loss of well|\bkick\b|diverter"
        ),
    ),
    (
        "fpso_topsides",
        _rx(r"\bfire\b|explosion|gas release|pressure release|chemical release"),
    ),
)

BSEE_RISER_SUBCLASS_RULES: tuple[tuple[str, re.Pattern], ...] = (
    ("slwr", _rx(r"lazy[- ]wave|\bSLWR\b")),
    ("scr", _rx(r"\bSCR\b|steel catenary")),
    ("flexible", _rx(r"flexible")),
    ("drilling_riser", _rx(r"marine riser|drilling riser|riser/BOP|\bLMRP\b")),
    ("production_riser", _rx(r"prod(\.|uction)? riser")),
    ("flowline_jumper", _rx(r"\bflowline\b|\bjumper\b")),
)

BSEE_MODE_RULES: tuple[tuple[str, re.Pattern], ...] = (
    (
        "loss_of_well_control",
        _rx(r"blowout|well control|loss of well|\bkick\b|diverter"),
    ),
    ("fire", _rx(r"\bfire\b|ignit|\bflash\b")),
    ("explosion", _rx(r"explosion")),
    (
        "loss_of_containment",
        _rx(
            r"pollution|\bspill|\bleak|gas release|pressure release"
            r"|chemical release|ruptur"
        ),
    ),
    (
        "structural_damage",
        _rx(
            r"structural damage|collapse|toppled|capsiz|fracture|parted|\bburst"
            r"|weld failure"
        ),
    ),
    ("collision", _rx(r"collision|allision|\bcontact\b")),
    ("lifting_event", _rx(r"\bcrane|lifting device|\bhoist|\bboom\b")),
    (
        "dropped_object",
        _rx(r"dropped|falling object|lost overboard|unplanned descent"),
    ),
    (
        "loss_of_station",
        _rx(
            r"loss of station|drift[- ]?off|anchor drag|mooring failure"
            r"|mooring line"
        ),
    ),
    ("unplanned_disconnect", _rx(r"disconnect|\bEDS\b")),
)

_BSEE_FATALITY = _rx(r"fatalit")
_BSEE_INJURY = _rx(r"injury|\bLTA\b|RW/JT")
_BSEE_POLLUTION = _rx(r"pollution|\bspill")


def _clean(text: Optional[str]) -> str:
    text = (text or "").replace("\x96", "-").replace("�", "-")
    return re.sub(r"\s+", " ", text).strip(" -")


def iso_date(text: str) -> str:
    text = (text or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M"):
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def bsee_record_id(record: Mapping[str, str]) -> str:
    """Composite key used across the HSE module: date|time|lease|area block."""
    return "|".join(
        (
            iso_date(record.get("DATE_OCCURRED", "")),
            (record.get("MILITARY_TIME") or "").strip(),
            (record.get("LEASE_NUMBER") or "").strip(),
            (record.get("AREA_BLOCK") or "").strip(),
        )
    )


def classify_bsee(
    record: Mapping[str, str], *, source_url: str = "", retrieved: str = ""
) -> list[EquipmentFailureRow]:
    """Rows for one BSEE incident-investigation record (may be empty)."""
    text = _clean(record.get("ACCIDENT_TYPE"))
    if not text:
        return []
    classes = [(k, rx) for k, rx in BSEE_EQUIPMENT_RULES if rx.search(text)]
    if not classes:
        return []
    modes = sorted(k for k, rx in BSEE_MODE_RULES if rx.search(text))
    area = (record.get("AREA_BLOCK") or "").strip()
    rows = []
    for key, rx in classes:
        sub = NOT_STATED
        if key == "riser":
            sub = next(
                (s for s, srx in BSEE_RISER_SUBCLASS_RULES if srx.search(text)),
                NOT_STATED,
            )
        rows.append(
            EquipmentFailureRow(
                equipment_class=key,
                equipment_subclass=sub,
                source_id="bsee_incident_investigations",
                source_record_id=bsee_record_id(record),
                date=iso_date(record.get("DATE_OCCURRED", "")),
                location="" if area == "Not Applicable" else area,
                event_text=text,
                failure_modes=";".join(modes) or "not_classified",
                fatality=bool(_BSEE_FATALITY.search(text)),
                injury=bool(_BSEE_INJURY.search(text)),
                pollution=bool(_BSEE_POLLUTION.search(text)),
                classification_rule=f"ACCIDENT_TYPE ~ /{rx.pattern}/",
                source_url=source_url,
                retrieved=retrieved,
            )
        )
    return rows


# --- PHMSA hazardous-liquid accident reports ----------------------------------
# Column names: the agency flagged file first, then the curated export held in
# data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/.
_PHMSA_FIELDS = {
    "id": ("REPORT_NUMBER", "Report Number"),
    "date": ("LOCAL_DATETIME", "Accident Date/Time"),
    "on_off": ("ON_OFF_SHORE", "Pipeline Location"),
    "state": ("ONSHORE_STATE_ABBREVIATION", "Accident State"),
    "cause": ("CAUSE", "Cause Category"),
    "cause_detail": ("CAUSE_DETAILS", "Cause Subcategory"),
    "ignite": ("IGNITE_IND", "Liquid Ignition"),
    "explode": ("EXPLODE_IND", "Liquid Explosion"),
    "fatal": ("FATAL", "All Fatalities"),
    "injure": ("INJURE", "All Injuries"),
}


def phmsa_field(record: Mapping[str, str], name: str) -> str:
    for column in _PHMSA_FIELDS[name]:
        value = record.get(column)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def phmsa_mechanism(cause: str, detail: str) -> str:
    """Map the PHMSA coded cause to a mechanism term. No text inference."""
    c, d = cause.upper(), detail.upper()
    if "CORROSION" in c:
        if "EXTERNAL" in d:
            return "corrosion_external"
        if "INTERNAL" in d:
            return "corrosion_internal"
        return "corrosion"
    if "MATERIAL" in c or "WELD" in c or "EQUIP" in c:
        if "ENVIRONMENTAL CRACKING" in d:
            return "environmental_cracking"
        if "CONSTRUCTION" in d or "INSTALLATION" in d or "FABRICATION" in d:
            return "installation_or_fabrication_error"
        if "MANUFACTURING" in d:
            return "manufacturing_defect"
        return "material_weld_or_equipment_failure"
    if "INCORRECT OPERATION" in c:
        return "incorrect_operation"
    if "NATURAL FORCE" in c:
        return "natural_force"
    if "EXCAVATION" in c or "OUTSIDE FORCE" in c:
        return "outside_force"
    if "UNKNOWN" in c or "UNKNOWN" in d:
        return UNKNOWN
    if c:
        return "other"
    return NOT_STATED


def _truthy(value: str) -> bool:
    return value.strip().upper() in {"YES", "Y", "TRUE", "1"}


def _positive(value: str) -> bool:
    try:
        return float(value) > 0
    except ValueError:
        return False


def classify_phmsa(
    record: Mapping[str, str], *, source_url: str = "", retrieved: str = ""
) -> list[EquipmentFailureRow]:
    """Row for one PHMSA hazardous-liquid accident report (always pipeline)."""
    rid = phmsa_field(record, "id")
    if not rid:
        return []
    cause, detail = phmsa_field(record, "cause"), phmsa_field(record, "cause_detail")
    mechanism = phmsa_mechanism(cause, detail)
    modes = {"loss_of_containment"}  # every accident report is a release
    if _truthy(phmsa_field(record, "ignite")):
        modes.add("fire")
    if _truthy(phmsa_field(record, "explode")):
        modes.add("explosion")
    on_off = phmsa_field(record, "on_off").upper()
    sub = on_off.lower() if on_off in {"ONSHORE", "OFFSHORE"} else NOT_STATED
    coded = " / ".join(x for x in (cause, detail) if x)
    return [
        EquipmentFailureRow(
            equipment_class="pipeline",
            equipment_subclass=sub,
            source_id="phmsa_hazardous_liquid",
            source_record_id=rid,
            date=iso_date(phmsa_field(record, "date")),
            location="offshore" if sub == "offshore" else phmsa_field(record, "state"),
            event_text="Hazardous liquid pipeline accident report",
            failure_modes=";".join(sorted(modes)),
            mechanism=mechanism,
            mechanism_basis=(
                BASIS_SOURCE_CODED if mechanism != NOT_STATED else BASIS_NONE
            ),
            mechanism_source_text=coded,
            fatality=_positive(phmsa_field(record, "fatal")),
            injury=_positive(phmsa_field(record, "injure")),
            pollution=True,
            classification_rule="PHMSA accident report; cause from coded field",
            source_url=source_url,
            retrieved=retrieved,
        )
    ]


CLASSIFIERS = {
    "bsee_incident_investigations": classify_bsee,
    "phmsa_hazardous_liquid": classify_phmsa,
}


def classify_records(
    source_id: str,
    records: Iterable[Mapping[str, str]],
    *,
    source_url: str = "",
    retrieved: str = "",
) -> list[EquipmentFailureRow]:
    """Classify every record of a supported source."""
    try:
        classifier = CLASSIFIERS[source_id]
    except KeyError:
        raise KeyError(
            f"unsupported source {source_id!r}; known: {sorted(CLASSIFIERS)}"
        ) from None
    rows: list[EquipmentFailureRow] = []
    for record in records:
        rows.extend(classifier(record, source_url=source_url, retrieved=retrieved))
    return rows
