# ABOUTME: Baker Hughes rig count data module (WRK-1190).
# ABOUTME: Parses NA pivot table and summary Excel into standardized DataFrames.

"""Baker Hughes rig count data ingestion.

Loads weekly rig count data from Baker Hughes Excel downloads
(pivot table and summary formats) into standardized pandas DataFrames.
"""

from worldenergydata.baker_hughes.analysis import aggregate_rig_counts
from worldenergydata.baker_hughes.loader import load_pivot_table, load_summary

__all__ = ["aggregate_rig_counts", "load_pivot_table", "load_summary"]
