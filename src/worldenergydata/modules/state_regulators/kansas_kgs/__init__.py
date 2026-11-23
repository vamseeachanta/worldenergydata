"""Kansas KGS ingest: wells master + Hugoton gas proration pressure tests.

Issue #725 (parent epic #708). Produces the normalized per-well pressure
observation table consumed by the under-pressured gas/condensate screen.
"""

from worldenergydata.modules.state_regulators.kansas_kgs.parsers import (
    read_proration_pressures,
    read_wells_master,
)

__all__ = ["read_proration_pressures", "read_wells_master"]
