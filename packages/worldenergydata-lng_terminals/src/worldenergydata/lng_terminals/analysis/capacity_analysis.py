"""Regional and global capacity summaries for LNG terminal data."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from ..constants import TerminalStatus
from ..models.terminal import LNGTerminal

logger = logging.getLogger(__name__)


class CapacityAnalysis:
    """Regional and global LNG capacity summaries."""

    def __init__(self, terminals: list[LNGTerminal]) -> None:
        self.terminals = terminals

    def summary(self) -> dict[str, Any]:
        """Generate a complete capacity summary."""
        return {
            "total_terminals": len(self.terminals),
            "total_capacity_mtpa": self._total_capacity(),
            "by_region": self.by_region(),
            "by_country": self.by_country(),
            "by_type": self.by_type(),
            "by_status": self.by_status(),
            "top_countries": self.top_countries(n=10),
        }

    def _total_capacity(self) -> float:
        """Sum of all capacity_mtpa values."""
        return sum(t.capacity_mtpa or 0.0 for t in self.terminals)

    def by_region(self) -> dict[str, dict[str, Any]]:
        """Group capacity by region."""
        groups: dict[str, list[LNGTerminal]] = defaultdict(list)
        for t in self.terminals:
            key = t.region.value if t.region else "Unknown"
            groups[key].append(t)

        return {
            region: {
                "count": len(terminals),
                "capacity_mtpa": round(
                    sum(t.capacity_mtpa or 0.0 for t in terminals), 2
                ),
                "operational": sum(
                    1 for t in terminals if t.status == TerminalStatus.OPERATIONAL
                ),
            }
            for region, terminals in sorted(groups.items())
        }

    def by_country(self) -> dict[str, dict[str, Any]]:
        """Group capacity by country."""
        groups: dict[str, list[LNGTerminal]] = defaultdict(list)
        for t in self.terminals:
            groups[t.country].append(t)

        return {
            country: {
                "count": len(terminals),
                "capacity_mtpa": round(
                    sum(t.capacity_mtpa or 0.0 for t in terminals), 2
                ),
            }
            for country, terminals in sorted(groups.items())
        }

    def by_type(self) -> dict[str, dict[str, Any]]:
        """Group capacity by terminal type."""
        groups: dict[str, list[LNGTerminal]] = defaultdict(list)
        for t in self.terminals:
            groups[t.terminal_type.value].append(t)

        return {
            ttype: {
                "count": len(terminals),
                "capacity_mtpa": round(
                    sum(t.capacity_mtpa or 0.0 for t in terminals), 2
                ),
            }
            for ttype, terminals in sorted(groups.items())
        }

    def by_status(self) -> dict[str, dict[str, Any]]:
        """Group capacity by status."""
        groups: dict[str, list[LNGTerminal]] = defaultdict(list)
        for t in self.terminals:
            groups[t.status.value].append(t)

        return {
            status: {
                "count": len(terminals),
                "capacity_mtpa": round(
                    sum(t.capacity_mtpa or 0.0 for t in terminals), 2
                ),
            }
            for status, terminals in sorted(groups.items())
        }

    def top_countries(self, n: int = 10) -> list[dict[str, Any]]:
        """Top N countries by total capacity."""
        by_country = self.by_country()
        ranked = sorted(
            by_country.items(),
            key=lambda x: x[1]["capacity_mtpa"],
            reverse=True,
        )
        return [{"country": country, **data} for country, data in ranked[:n]]
