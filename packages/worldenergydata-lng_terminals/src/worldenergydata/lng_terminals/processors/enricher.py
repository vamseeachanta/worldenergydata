"""Enricher for LNG terminal data.

Merges multi-source terminal records by priority, combining citations
and filling in missing fields from lower-priority sources.
"""

from __future__ import annotations

import logging

from ..models.terminal import LNGTerminal

# ---------------------------------------------------------------------------
# Source priority (higher number = higher priority)
# ---------------------------------------------------------------------------

SOURCE_PRIORITY: dict[str, int] = {
    "seed_dataset": 10,
    "web": 20,
    "giignl": 30,
    "gie": 40,
    "ferc": 50,
}

# Fields that should NOT be overwritten during enrichment
_IMMUTABLE_FIELDS = {"terminal_id", "terminal_name", "country"}

# Fields that are lists and should be merged (union) rather than replaced
_LIST_FIELDS = {"aliases", "pipelines", "sources"}

# Sub-model fields that should be enriched field-by-field
_SUB_MODEL_FIELDS = {
    "hull_design",
    "process_equipment",
    "storage",
    "marine_infrastructure",
}


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------


class Enricher:
    """Merge multi-source LNG terminal records by priority."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def enrich(
        self,
        base_terminals: list[LNGTerminal],
        additional: list[LNGTerminal],
        source_name: str = "unknown",
    ) -> list[LNGTerminal]:
        """Enrich base terminals with data from additional source.

        For each terminal in *base_terminals*, if a matching record exists
        in *additional* (by ``terminal_id``), merge fields using source
        priority.  Additional records with no match are appended.

        Args:
            base_terminals: Existing terminal records.
            additional: New records to merge in.
            source_name: Name of the additional source for priority lookup.

        Returns:
            Enriched list of terminals.
        """
        base_by_id = {t.terminal_id: t for t in base_terminals}
        added = 0
        merged = 0

        for new_terminal in additional:
            if new_terminal.terminal_id in base_by_id:
                existing = base_by_id[new_terminal.terminal_id]
                base_by_id[new_terminal.terminal_id] = self._merge_terminals(
                    existing, new_terminal, source_name
                )
                merged += 1
            else:
                base_by_id[new_terminal.terminal_id] = new_terminal
                added += 1

        self.logger.info(
            "Enrichment from '%s': %d merged, %d added",
            source_name,
            merged,
            added,
        )
        return list(base_by_id.values())

    # -- Private helpers ----------------------------------------------------

    def _merge_terminals(
        self,
        existing: LNGTerminal,
        new: LNGTerminal,
        source_name: str,
    ) -> LNGTerminal:
        """Merge two terminal records, preferring higher-priority source."""
        existing_priority = self._get_max_priority(existing)
        new_priority = SOURCE_PRIORITY.get(source_name, 0)

        merged_data = existing.model_dump()
        new_data = new.model_dump()

        for field_name in LNGTerminal.model_fields:
            if field_name in _IMMUTABLE_FIELDS:
                continue

            if field_name in _LIST_FIELDS:
                existing_list = merged_data.get(field_name, []) or []
                new_list = new_data.get(field_name, []) or []

                if field_name == "sources":
                    merged_data[field_name] = existing_list + new_list
                elif field_name == "aliases":
                    merged_data[field_name] = list(set(existing_list + new_list))
                else:
                    merged_data[field_name] = existing_list + new_list
                continue

            existing_val = merged_data.get(field_name)
            new_val = new_data.get(field_name)

            # Fill empty fields or overwrite with higher-priority source
            if (existing_val is None and new_val is not None) or (
                new_val is not None and new_priority > existing_priority
            ):
                merged_data[field_name] = new_val

        # Update timestamp to the most recent
        merged_data["last_updated"] = max(
            existing.last_updated, new.last_updated
        ).isoformat()

        return LNGTerminal.model_validate(merged_data)

    @staticmethod
    def _get_max_priority(terminal: LNGTerminal) -> int:
        """Get the highest source priority from a terminal's citations."""
        if not terminal.sources:
            return 0
        return max(SOURCE_PRIORITY.get(s.source_name, 0) for s in terminal.sources)
