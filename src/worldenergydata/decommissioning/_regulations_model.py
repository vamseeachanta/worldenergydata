# ABOUTME: Dataclass model for a single regulatory decommissioning record.
# ABOUTME: Shared between regulations.py and _regulations_data.py.

"""Shared dataclass for decommissioning regulatory records."""

from dataclasses import dataclass


@dataclass
class DecommissioningRegulation:
    """Single regulatory requirement record for a region and requirement type."""

    region: str               # "gom", "ukcs", "ncs", "brazil"
    regulatory_body: str      # "BSEE", "NSTA", "PSA", "ANP"
    requirement_type: str     # e.g. "well_plugging", "structure_removal"
    lead_time_months: int     # minimum regulatory lead time
    key_threshold: str        # human-readable threshold description
    reference_doc: str        # regulatory reference document
    notes: str = ""
