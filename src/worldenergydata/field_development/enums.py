# ABOUTME: Controlled vocabularies for the offshore field-development concept model.
# ABOUTME: Issue #568 — enums shared by the FieldConcept schema and sanity gate.
"""
worldenergydata.field_development.enums
=======================================

Controlled vocabularies (enums) for the :class:`FieldConcept` contract.

Keeping these as ``str``-valued enums means they serialize to plain strings in
JSON (stable, human-readable) while still constraining the allowed values at
construction time. Values are lower_snake_case for machine use; the
``data_dictionary.md`` carries the human-readable labels.
"""

from __future__ import annotations

from enum import Enum


class FluidType(str, Enum):
    """Reservoir fluid classification."""

    OIL = "oil"
    GAS = "gas"
    CONDENSATE = "condensate"
    GAS_CONDENSATE = "gas_condensate"


class ConceptType(str, Enum):
    """Host / development concept options (briefing §A3)."""

    FIXED_JACKET = "fixed_jacket"
    COMPLIANT_TOWER = "compliant_tower"
    TLP = "tlp"
    SPAR = "spar"
    SEMISUB_FPS = "semisub_fps"
    FPSO = "fpso"
    FLNG = "flng"
    SUBSEA_TIEBACK = "subsea_tieback"
    SUBSEA_TO_SHORE = "subsea_to_shore"
    NUI = "nui"  # normally unmanned installation / minimal facilities platform


class TreeType(str, Enum):
    """Well completion access type."""

    DRY = "dry"  # surface trees on TLP/Spar — direct vertical access
    WET = "wet"  # subsea trees on the seabed


class Topology(str, Enum):
    """Subsea field topology (briefing §A4)."""

    SATELLITE = "satellite"
    CLUSTER = "cluster"
    DAISY_CHAIN = "daisy_chain"
    PIGGING_LOOP = "pigging_loop"


class FlowlineMaterial(str, Enum):
    """Flowline construction / insulation class."""

    RIGID = "rigid"
    FLEXIBLE = "flexible"
    PIPE_IN_PIPE = "pipe_in_pipe"


class RiserType(str, Enum):
    """Riser configuration (briefing §A4)."""

    SCR = "scr"  # steel catenary riser
    SLWR = "slwr"  # steel lazy-wave riser
    FLEXIBLE = "flexible"
    HYBRID_TOWER = "hybrid_tower"
    TTR = "ttr"  # top-tensioned riser (dry tree)


class MetoceanRegime(str, Enum):
    """Environmental severity class driving hull/mooring/disconnectability."""

    BENIGN = "benign"
    HARSH_PERSISTENT = "harsh_persistent"
    HURRICANE_CYCLONE = "hurricane_cyclone"


class ReservoirDistribution(str, Enum):
    """Areal distribution of the reservoir, drives dry-vs-wet tree choice."""

    COMPACT_STACKED = "compact_stacked"
    DISTRIBUTED = "distributed"
