# ABOUTME: Public surface for the reusable typed-query base (workspace-hub#3286).
# ABOUTME: Exports TypedQuery + FilterSpec, generalized from marine_safety/bsee query APIs.
"""Reusable typed-query base for worldenergydata query surfaces.

Extracts the singular/plural filter-collapse + single-year shorthand boilerplate
that ``marine_safety`` and ``bsee`` each hand-rolled, and adds an OPTIONAL
``query_envelope() -> ResultEnvelope`` path that consumes the shared
``assetutilities.workflow_api`` contract (workspace-hub#3282) lazily, so the base
carries no hard assetutilities import until envelopes are actually requested.
"""

from worldenergydata.common.query_api.base import (
    FilterSpec,
    TypedQuery,
    df_content_hash,
)

__all__ = ["TypedQuery", "FilterSpec", "df_content_hash"]
