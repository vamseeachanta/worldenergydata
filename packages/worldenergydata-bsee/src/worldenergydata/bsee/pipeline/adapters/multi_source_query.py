"""Cross-source query dispatcher for multi-regulatory field analysis.

Routes field queries to one or more registered adapters and collects
normalised results.  Used by WRK-018 Phase 4 to compare the same field
(or equivalent fields) across BSEE, SODIR, RRC, CNH, and ANP.
"""

from __future__ import annotations

import logging
from typing import Any

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterInterface,
    AdapterResult,
    DataAvailability,
    DomainStatus,
)

logger = logging.getLogger(__name__)


class MultiSourceQuery:
    """Registry and dispatcher for cross-source field queries.

    Parameters
    ----------
    adapters:
        Initial mapping of *source_id* to adapter instance.
        Pass ``None`` (the default) to start with an empty registry.
    """

    def __init__(self, adapters: dict[str, AdapterInterface] | None = None) -> None:
        self._adapters: dict[str, AdapterInterface] = dict(adapters or {})

    # -- registration -------------------------------------------------------

    def register(self, source_id: str, adapter: AdapterInterface) -> None:
        """Register (or replace) an adapter under *source_id*."""
        self._adapters[source_id] = adapter

    # -- querying -----------------------------------------------------------

    def query(
        self,
        field_name: str,
        sources: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, AdapterResult]:
        """Dispatch *field_name* to selected adapters.

        Parameters
        ----------
        field_name:
            The field name (or well / lease identifier) to resolve.
        sources:
            Subset of registered source IDs to query.  ``None`` means
            query every registered adapter.
        **kwargs:
            Forwarded to each adapter's ``adapt()`` call.

        Returns
        -------
        dict mapping *source_id* to :class:`AdapterResult`.  Adapters
        that raise are logged and omitted from the result dict.
        """
        targets = self._resolve_targets(sources)
        results: dict[str, AdapterResult] = {}

        for sid, adapter in targets.items():
            try:
                results[sid] = adapter.adapt(field_name, **kwargs)
            except Exception:
                logger.exception("Adapter '%s' failed for query '%s'", sid, field_name)

        return results

    def query_all(self, field_name: str, **kwargs: Any) -> dict[str, AdapterResult]:
        """Convenience wrapper — query every registered adapter."""
        return self.query(field_name, sources=None, **kwargs)

    # -- introspection ------------------------------------------------------

    def available_sources(self) -> list[str]:
        """Return sorted list of registered source IDs."""
        return sorted(self._adapters)

    def source_availability_matrix(self) -> list[dict]:
        """Aggregate availability from all registered adapters.

        Returns a flat list of dicts (one per source/domain pair)
        suitable for ``pd.DataFrame`` construction.
        """
        rows: list[dict] = []
        domains = (
            "wellbore",
            "well_path",
            "casing",
            "drilling_completion",
            "intervention",
            "production",
        )
        for sid in sorted(self._adapters):
            avail: DataAvailability = self._adapters[sid].get_availability()
            for domain in domains:
                ds: DomainStatus = getattr(avail, domain)
                rows.append(
                    {
                        "source_id": sid,
                        "source_name": avail.source_name,
                        "domain": domain,
                        "status": ds.status,
                        "notes": ds.notes,
                    }
                )
        return rows

    # -- internal -----------------------------------------------------------

    def _resolve_targets(
        self, sources: list[str] | None
    ) -> dict[str, AdapterInterface]:
        if sources is None:
            return dict(self._adapters)
        unknown = set(sources) - set(self._adapters)
        if unknown:
            logger.warning("Unknown source IDs ignored: %s", unknown)
        return {s: self._adapters[s] for s in sources if s in self._adapters}
