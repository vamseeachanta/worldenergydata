"""
ABOUTME: Vessel operation phase taxonomy for MAIB, NTSB, and USCG MISLE incident records.
ABOUTME: Classifies phase-of-operation at incident time from free-text activity descriptions.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional

# ---------------------------------------------------------------------------
# MISLE operation phase column constant
# ---------------------------------------------------------------------------

# Standard USCG MISLE CSV column for operation/activity phase at time of incident.
# Common field names in MISLE exports include ACTIVITY_TYPE and OPERATION_TYPE.
MISLE_OPERATION_COLUMN: str = "ACTIVITY_TYPE"


class OperationPhase(str, Enum):
    """
    Vessel operation phase at the time of the incident.

    Aligned with:
    - MAIB occurrence categorisation (operation phase fields)
    - USCG MISLE ACTIVITY_TYPE codes
    - IMO Casualty Investigation Code operation categories
    - NTSB marine investigation phase-of-operation
    """

    MANOEUVRING = "manoeuvring"
    """Vessel manoeuvring in confined waters, approaching berth or anchorage."""

    ANCHORED = "anchored"
    """Vessel at anchor or moored."""

    UNDERWAY = "underway"
    """Vessel underway in open water on a passage."""

    PORT_OPERATIONS = "port_operations"
    """Vessel alongside at berth, in dry dock, or engaged in port activity."""

    CARGO_OPERATIONS = "cargo_operations"
    """Loading, discharging, or transferring cargo or fuel."""

    FISHING_OPS = "fishing_ops"
    """Vessel engaged in active fishing operations (trawling, hauling, netting)."""

    UNKNOWN = "unknown"
    """Insufficient data to determine operation phase."""


# ---------------------------------------------------------------------------
# Operation phase keyword map
# ---------------------------------------------------------------------------

_PHASE_KEYWORD_MAP: List[tuple[str, OperationPhase]] = [
    # Manoeuvring
    ("manoeuv", OperationPhase.MANOEUVRING),
    ("maneouv", OperationPhase.MANOEUVRING),
    ("maneuvering", OperationPhase.MANOEUVRING),
    ("berthing", OperationPhase.MANOEUVRING),
    ("departing berth", OperationPhase.MANOEUVRING),
    ("leaving port", OperationPhase.MANOEUVRING),
    ("approach.*berth", OperationPhase.MANOEUVRING),
    ("turning", OperationPhase.MANOEUVRING),
    ("pilotage", OperationPhase.MANOEUVRING),
    # Anchored / moored
    ("at anchor", OperationPhase.ANCHORED),
    ("anchored", OperationPhase.ANCHORED),
    ("moored", OperationPhase.ANCHORED),
    ("at mooring", OperationPhase.ANCHORED),
    ("lying at anchor", OperationPhase.ANCHORED),
    ("swinging at anchor", OperationPhase.ANCHORED),
    # Underway / passage
    ("underway", OperationPhase.UNDERWAY),
    ("passage", OperationPhase.UNDERWAY),
    ("in transit", OperationPhase.UNDERWAY),
    ("proceeding", OperationPhase.UNDERWAY),
    ("on voyage", OperationPhase.UNDERWAY),
    ("open sea", OperationPhase.UNDERWAY),
    ("ocean passage", OperationPhase.UNDERWAY),
    # Port operations
    ("in port", OperationPhase.PORT_OPERATIONS),
    ("at berth", OperationPhase.PORT_OPERATIONS),
    ("docking", OperationPhase.PORT_OPERATIONS),
    ("port operation", OperationPhase.PORT_OPERATIONS),
    ("alongside", OperationPhase.PORT_OPERATIONS),
    ("dry dock", OperationPhase.PORT_OPERATIONS),
    # Cargo operations
    ("loading cargo", OperationPhase.CARGO_OPERATIONS),
    ("discharging cargo", OperationPhase.CARGO_OPERATIONS),
    ("cargo operation", OperationPhase.CARGO_OPERATIONS),
    ("bunkering", OperationPhase.CARGO_OPERATIONS),
    ("cargo transfer", OperationPhase.CARGO_OPERATIONS),
    ("loading.*terminal", OperationPhase.CARGO_OPERATIONS),
    ("unloading", OperationPhase.CARGO_OPERATIONS),
    # Fishing operations
    ("fishing", OperationPhase.FISHING_OPS),
    ("trawling", OperationPhase.FISHING_OPS),
    ("hauling", OperationPhase.FISHING_OPS),
    ("netting", OperationPhase.FISHING_OPS),
    ("pot hauling", OperationPhase.FISHING_OPS),
]


class OperationPhaseClassifier:
    """
    Classifies a vessel's operation phase at the time of an incident.

    Operates on free-text operation/activity descriptions.
    Applies a priority-ordered keyword scan with regex support.
    """

    def __init__(self) -> None:
        self._compiled: List[tuple[re.Pattern, OperationPhase]] = [
            (re.compile(pat, re.IGNORECASE), phase) for pat, phase in _PHASE_KEYWORD_MAP
        ]

    def classify(self, operation_text: Optional[str] = None) -> OperationPhase:
        """
        Classify an operation phase from free-text.

        Args:
            operation_text: Description of vessel activity at time of incident.

        Returns:
            OperationPhase enum value.
        """
        if not operation_text:
            return OperationPhase.UNKNOWN
        text = str(operation_text).strip()
        if not text:
            return OperationPhase.UNKNOWN
        for pattern, phase in self._compiled:
            if pattern.search(text):
                return phase
        return OperationPhase.UNKNOWN
