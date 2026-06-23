# ABOUTME: Regulatory database for offshore decommissioning requirements by region.
# ABOUTME: BSEE (GoM), NSTA (UKCS), PSA (NCS), ANP (Brazil).

"""Decommissioning regulatory database covering four major jurisdictions.

Provides structured access to minimum lead times, key thresholds, and
reference documents for BSEE, NSTA, PSA, and ANP regulations.

Public API::

    from worldenergydata.decommissioning.regulations import (
        DecommissioningRegulation,
        DECOMMISSIONING_REGULATIONS,
        get_regulations,
        get_lead_time,
        regulatory_summary,
    )
"""

import pandas as pd

from worldenergydata.decommissioning._regulations_data import (
    ALL_REGULATIONS as DECOMMISSIONING_REGULATIONS,
)

# Re-export the dataclass so callers only need to import from this module
from worldenergydata.decommissioning._regulations_model import (
    DecommissioningRegulation,
)

__all__ = [
    "DecommissioningRegulation",
    "DECOMMISSIONING_REGULATIONS",
    "get_regulations",
    "get_lead_time",
    "regulatory_summary",
]


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------


def get_regulations(region: str) -> list[DecommissioningRegulation]:
    """Return all regulations for the specified region.

    Args:
        region: One of 'gom', 'ukcs', 'ncs', 'brazil'. Case-insensitive.

    Returns:
        List of DecommissioningRegulation records for that region.
        Returns empty list if region is not recognised.
    """
    region = region.lower()
    return [r for r in DECOMMISSIONING_REGULATIONS if r.region == region]


def get_lead_time(region: str, requirement_type: str) -> int:
    """Return the minimum lead time in months for a region/requirement pair.

    Args:
        region: Regulatory region. Case-insensitive.
        requirement_type: Type of requirement (e.g. 'well_plugging'). Case-insensitive.

    Returns:
        Lead time in months for the first matching record, or 0 if none found.
    """
    region = region.lower()
    requirement_type = requirement_type.lower()
    for reg in DECOMMISSIONING_REGULATIONS:
        if reg.region == region and reg.requirement_type == requirement_type:
            return reg.lead_time_months
    return 0


def regulatory_summary() -> pd.DataFrame:
    """Return a summary DataFrame of all regulations.

    Returns:
        DataFrame with columns: region, regulatory_body, requirement_type,
        lead_time_months, key_threshold, reference_doc.
        One row per regulation record.
    """
    records = [
        {
            "region": r.region,
            "regulatory_body": r.regulatory_body,
            "requirement_type": r.requirement_type,
            "lead_time_months": r.lead_time_months,
            "key_threshold": r.key_threshold,
            "reference_doc": r.reference_doc,
        }
        for r in DECOMMISSIONING_REGULATIONS
    ]
    return pd.DataFrame(records)
