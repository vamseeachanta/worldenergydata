# ABOUTME: Equipment-class, failure-mode and failure-mechanism vocabulary for incident records.
# ABOUTME: A mechanism is recorded only when the source states it; otherwise it stays not_stated.

"""Equipment failure taxonomy.

Three controlled vocabularies link a public incident record to the equipment an
engineering report analyses:

* **equipment class** - what the record concerns (riser, mooring line, ...);
* **failure mode** - what happened, as the source's event type gives it;
* **failure mechanism** - why it happened, recorded **only** when the source
  states it (an agency-coded cause field, or the cited investigation report).

No mechanism is inferred from an event type. A riser disconnect is not recorded
as fatigue, and a mooring failure in a storm is not recorded as overload, unless
the source says so. Records without a stated cause carry ``not_stated``.
"""

from __future__ import annotations

from dataclasses import dataclass

NOT_STATED = "not_stated"

# Basis of a recorded mechanism.
BASIS_SOURCE_CODED = "source_coded"  # agency-coded cause field in the data set
BASIS_INVESTIGATION = "investigation_stated"  # stated in the cited investigation
BASIS_NONE = "not_stated"
MECHANISM_BASES = (BASIS_SOURCE_CODED, BASIS_INVESTIGATION, BASIS_NONE)


@dataclass(frozen=True)
class Term:
    key: str
    label: str
    note: str = ""


EQUIPMENT_CLASSES: dict[str, Term] = {
    t.key: t
    for t in (
        Term(
            "riser",
            "Risers (SCR, SLWR, flexible, drilling and production)",
            "Subclass is recorded only when the source names the riser type.",
        ),
        Term(
            "mooring_line",
            "Mooring lines and station keeping",
            "Includes loss-of-station events of dynamically positioned units, "
            "which the source event type does not separate from moored units.",
        ),
        Term("pipeline", "Pipelines"),
        Term("jack_up", "Jack-ups and liftboats"),
        Term("lifting_rigging", "Lifting and rigging"),
        Term(
            "wellhead_conductor",
            "Wellheads and conductors",
            "Includes loss-of-well-control events; the source event type does "
            "not always name the failed component.",
        ),
        Term(
            "fpso_topsides",
            "Topsides process (FPSO and other facilities)",
            "Sources that do not give the facility type cannot separate "
            "floating from fixed facilities.",
        ),
    )
}

RISER_SUBCLASSES = (
    "scr",
    "slwr",
    "flexible",
    "drilling_riser",
    "production_riser",
    "flowline_jumper",
    NOT_STATED,
)

FAILURE_MODES: dict[str, Term] = {
    t.key: t
    for t in (
        Term("loss_of_containment", "Loss of containment (leak, release, spill)"),
        Term("loss_of_well_control", "Loss of well control"),
        Term("fire", "Fire"),
        Term("explosion", "Explosion"),
        Term("structural_damage", "Structural damage or collapse"),
        Term("collision", "Collision or contact"),
        Term("lifting_event", "Crane or lifting-device event"),
        Term("dropped_object", "Dropped object"),
        Term("loss_of_station", "Loss of station or mooring failure"),
        Term("unplanned_disconnect", "Unplanned or emergency disconnect"),
        Term("not_classified", "Event type not classified"),
    )
}

FAILURE_MECHANISMS: dict[str, Term] = {
    t.key: t
    for t in (
        Term("fatigue", "Fatigue"),
        Term("viv", "Vortex-induced vibration"),
        Term("corrosion", "Corrosion (type not stated)"),
        Term("corrosion_external", "External corrosion"),
        Term("corrosion_internal", "Internal corrosion"),
        Term("environmental_cracking", "Environmentally assisted cracking"),
        Term("hydrogen_embrittlement", "Hydrogen embrittlement"),
        Term("overload", "Overload"),
        Term("natural_force", "Natural force damage"),
        Term("outside_force", "Outside force or third-party damage"),
        Term("manufacturing_defect", "Manufacturing defect"),
        Term(
            "installation_or_fabrication_error",
            "Construction, installation or fabrication error",
        ),
        Term(
            "material_weld_or_equipment_failure",
            "Material, weld or equipment failure (not further stated)",
        ),
        Term("incorrect_operation", "Incorrect operation (human factors)"),
        Term("other_or_unknown", "Other or unknown, as coded by the source"),
        Term(NOT_STATED, "Cause not stated in the source"),
    )
}


def label(vocabulary: dict[str, Term], key: str) -> str:
    """Human label for ``key``; raises ``KeyError`` for an unknown term."""
    return vocabulary[key].label
