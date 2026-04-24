"""Cross-source benchmarking for multi-regulatory field comparison.

Takes the output of :class:`MultiSourceQuery.query` (a dict of
source_id -> AdapterResult) and produces comparative DataFrames
for production, wellbore counts, drilling activity, and a high-level
summary.

Used by WRK-018 Phase 4 to benchmark the same (or equivalent) field
across BSEE, SODIR, RRC, CNH, and ANP.
"""

from __future__ import annotations

import pandas as pd

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterResult,
)

# Six canonical domains on AdapterResult / DataAvailability
_DOMAIN_ATTRS = (
    "wellbore",
    "well_path",
    "casing",
    "drilling_completion",
    "intervention",
    "production",
)


class CrossSourceBenchmark:
    """Comparative analysis across adapter results.

    Parameters
    ----------
    results:
        Mapping of source_id to :class:`AdapterResult`, typically the
        return value of ``MultiSourceQuery.query()``.
    """

    def __init__(self, results: dict[str, AdapterResult]) -> None:
        self._results = results

    # -- domain comparisons -------------------------------------------------

    def compare_production(self) -> pd.DataFrame:
        """Merge production DataFrames from all sources.

        Each source's production DataFrame gets a ``source`` column
        prepended.  Returns an empty DataFrame when no source has
        production data.
        """
        return self._merge_domain("production", "production")

    def compare_wellbore_counts(self) -> pd.DataFrame:
        """Merge wellbore summary DataFrames from all sources."""
        return self._merge_domain("wellbore_summary", "wellbore_counts")

    def compare_drilling_activity(self) -> pd.DataFrame:
        """Merge drilling activity DataFrames from all sources."""
        return self._merge_domain("drilling_activities", "drilling_activity")

    # -- high-level summary -------------------------------------------------

    def summary(self) -> pd.DataFrame:
        """One-row-per-source overview.

        Columns: source_id, field_name, well_count,
        num_available_domains, has_production, has_drilling, has_casing.
        """
        rows: list[dict] = []
        for sid, result in self._results.items():
            availability = self._count_available_domains(result)
            rows.append(
                {
                    "source_id": sid,
                    "field_name": result.field_name,
                    "well_count": result.well_count,
                    "num_available_domains": availability,
                    "has_production": not result.production.empty,
                    "has_drilling": not result.drilling_activities.empty,
                    "has_casing": not result.casing_strings.empty,
                }
            )
        if not rows:
            return pd.DataFrame(
                columns=[
                    "source_id",
                    "field_name",
                    "well_count",
                    "num_available_domains",
                    "has_production",
                    "has_drilling",
                    "has_casing",
                ]
            )
        return pd.DataFrame(rows)

    # -- internals ----------------------------------------------------------

    def _merge_domain(self, attr: str, label: str) -> pd.DataFrame:
        """Concatenate a domain DataFrame from every source."""
        frames: list[pd.DataFrame] = []
        for sid, result in self._results.items():
            df: pd.DataFrame = getattr(result, attr)
            if df is not None and not df.empty:
                tagged = df.copy()
                tagged.insert(0, "source", sid)
                frames.append(tagged)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    @staticmethod
    def _count_available_domains(result: AdapterResult) -> int:
        """Count how many domain DataFrames are non-empty."""
        domain_attrs = (
            "wellbore_summary",
            "well_paths",
            "casing_strings",
            "drilling_activities",
            "completion_activities",
            "intervention_activities",
            "production",
        )
        return sum(1 for attr in domain_attrs if not getattr(result, attr).empty)
