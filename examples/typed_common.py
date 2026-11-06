"""Typed result, exception and logging example.

The synthetic input contains north, south and west records, with two records on
the first page. Independent count: two records fill that page and one remains,
so two pages are needed. No measured or engineering values are used.

See docs/development/incremental_typing.md for the input, method and answer.
"""

import json
import logging
from collections import UserDict
from collections.abc import MutableMapping
from typing import Any

from worldenergydata.common.exceptions import WorldEnergyDataError
from worldenergydata.common.logging import LoggerAdapter
from worldenergydata.common.types import DataResult, PaginatedResult


def summarize(rows: list[dict[str, Any]], page_size: int) -> dict[str, Any]:
    """Summarize the first page of synthetic rows with serialized context."""
    result = DataResult(rows[:page_size], metadata={"source": "example"})
    page = PaginatedResult(
        data=result.data,
        page=1,  # First page; PaginatedResult examples use one-based page numbers.
        page_size=page_size,
        total_count=len(rows),
        has_next=len(rows) > page_size,
        has_previous=False,
    )
    error = WorldEnergyDataError("Missing date", context={"fields": ["date"]})
    adapter = LoggerAdapter(
        logging.getLogger(__name__), {"source": "default", "task": "sample"}
    )
    kwargs: MutableMapping[str, Any] = UserDict({"extra": {"source": "call"}})
    _, processed = adapter.process("Loaded page", kwargs)
    return {
        "record_count": result.record_count,
        "total_pages": page.total_pages,
        "error": error.to_dict(),
        "context": processed["extra"],
    }


if __name__ == "__main__":
    sample = [{"region": "north"}, {"region": "south"}, {"region": "west"}]
    # Synthetic page size from this module's worked example, not a domain limit.
    print(json.dumps(summarize(sample, page_size=2), sort_keys=True))
