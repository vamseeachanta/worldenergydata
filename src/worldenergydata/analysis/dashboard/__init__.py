"""Compatibility namespace for dashboard analysis modules.

The well production dashboard was promoted to
``worldenergydata.well_production_dashboard``.  This package keeps older import
paths working for tests and downstream callers.
"""

from . import well_detail_views

__all__ = ["well_detail_views"]
