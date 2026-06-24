"""Portfolio-level constants and helpers for the Lower Tertiary play.

This module is the single source of truth for the LT field roster. Other
modules (analysis, reporting, tests) import from here so the roster cannot
silently drift between config files, tests, and reports.

See `reports/lower_tertiary_field_summary.md` for the canonical narrative
roster of record. Updates to LT_FIELDS_2026 must flow through that document
first, then a roster-bump issue.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

# The 10 GoM Lower Tertiary fields covered by the 2026 portfolio analysis (#373).
# Order is alphabetical by field_id for stable iteration.
LT_FIELDS_2026: Tuple[str, ...] = (
    "anchor",
    "big_foot",
    "cascade_chinook",
    "jack_st_malo",
    "julia",
    "kaskida",
    "north_platte",
    "shenandoah",
    "stones",
    "tiber",
)


def fields_config_dir() -> Path:
    """Return the canonical directory holding per-field yaml configs."""
    # Phase 2 batch-3 carve (#529): now 2 levels deeper under
    # packages/worldenergydata-bsee/; repo root is parents[5] (was [3]).
    return (
        Path(__file__).resolve().parents[5]
        / "config"
        / "analysis"
        / "lower_tertiary"
        / "fields"
    )


def expected_field_yaml_paths() -> Tuple[Path, ...]:
    """Return the expected yaml path for each field in the 2026 portfolio."""
    base = fields_config_dir()
    return tuple(base / f"{field_id}.yml" for field_id in LT_FIELDS_2026)
