"""
FDAS Data Processing Module

Handles production aggregation and data preparation for financial analysis.

D&C timeline extraction was REMOVED here (#1075, epic #1063).  The former
``drilling.py`` derived "drilling days" as a calendar ``(td - spud)`` span and,
when TD was absent, fabricated a 60-day duration (plus a flat 30-day completion
estimate) out of nothing.  It had no production caller: the only consumers were
its own tests, docs, and a stale example.  The single supported implementation
is now ``worldenergydata.bsee.analysis.war_rig_days``, which derives rig days
from BSEE WAR ``WELL_ACTIVITY_CD`` weeks and emits an explicit
``no_war_activity`` status instead of a fabricated number.

That module deliberately is NOT re-exported here: ``worldenergydata-bsee``
depends on ``worldenergydata-fdas`` (see both pyproject.toml files and ADR
0001), so an fdas -> bsee import would close a member-level dependency cycle.
Callers that need rig days import ``war_rig_days`` from the bsee package
directly and pass the result in (e.g. as ``CashflowEngine`` /
``generate_monthly_cashflow``'s ``drilling_timeline`` argument).

Author: WorldEnergyData Team
Date: 2025-10-03
"""

from .production import (
    ProductionProcessingError,
    ProductionProcessor,
    aggregate_monthly_production,
    identify_first_oil_date,
)

__all__ = [
    # Production processing
    "ProductionProcessor",
    "aggregate_monthly_production",
    "identify_first_oil_date",
    "ProductionProcessingError",
]
