"""FID and construction timeline analysis for LNG terminals."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from ..constants import TerminalStatus
from ..models.terminal import LNGTerminal

logger = logging.getLogger(__name__)


class TimelineAnalysis:
    """Analyze construction and commissioning timelines."""

    def __init__(self, terminals: list[LNGTerminal]) -> None:
        self.terminals = terminals

    def summary(self) -> dict[str, Any]:
        """Generate timeline summary."""
        return {
            "commissioning_by_decade": self.by_decade(),
            "under_construction": self.under_construction(),
            "planned_capacity": self.planned_capacity(),
            "commissioning_by_year": self.by_year(),
        }

    def by_decade(self) -> dict[str, dict[str, Any]]:
        """Group terminals by commissioning decade."""
        groups: dict[str, list[LNGTerminal]] = defaultdict(list)
        for t in self.terminals:
            if t.year_commissioned:
                decade = f"{(t.year_commissioned // 10) * 10}s"
                groups[decade].append(t)

        return {
            decade: {
                "count": len(terminals),
                "capacity_mtpa": round(
                    sum(t.capacity_mtpa or 0.0 for t in terminals), 2
                ),
            }
            for decade, terminals in sorted(groups.items())
        }

    def by_year(self) -> dict[int, dict[str, Any]]:
        """Group terminals by commissioning year."""
        groups: dict[int, list[LNGTerminal]] = defaultdict(list)
        for t in self.terminals:
            if t.year_commissioned:
                groups[t.year_commissioned].append(t)

        return {
            year: {
                "count": len(terminals),
                "capacity_mtpa": round(
                    sum(t.capacity_mtpa or 0.0 for t in terminals), 2
                ),
                "names": [t.terminal_name for t in terminals],
            }
            for year, terminals in sorted(groups.items())
        }

    def under_construction(self) -> list[dict[str, Any]]:
        """List terminals currently under construction."""
        return [
            {
                "terminal_name": t.terminal_name,
                "country": t.country,
                "capacity_mtpa": t.capacity_mtpa,
                "operator": t.operator,
            }
            for t in self.terminals
            if t.status == TerminalStatus.UNDER_CONSTRUCTION
        ]

    def planned_capacity(self) -> dict[str, Any]:
        """Summary of planned and under-construction capacity."""
        planned = [
            t
            for t in self.terminals
            if t.status in {TerminalStatus.PLANNED, TerminalStatus.UNDER_CONSTRUCTION}
        ]
        return {
            "count": len(planned),
            "total_capacity_mtpa": round(
                sum(t.capacity_mtpa or 0.0 for t in planned), 2
            ),
            "by_status": {
                "under_construction": sum(
                    t.capacity_mtpa or 0.0
                    for t in planned
                    if t.status == TerminalStatus.UNDER_CONSTRUCTION
                ),
                "planned": sum(
                    t.capacity_mtpa or 0.0
                    for t in planned
                    if t.status == TerminalStatus.PLANNED
                ),
            },
        }
