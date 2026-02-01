"""Per-field and per-record completeness scoring for LNG terminal data.

Computes a weighted quality score (0-100) for each terminal record based on
the presence of required, optional, and engineering fields.  Weights:

* 50 % -- required fields (name, country, type, status)
* 30 % -- optional scalar fields (capacity, operator, year, etc.)
* 20 % -- engineering sub-model fields (hull, pipeline, process, storage, marine)
"""

from __future__ import annotations

import logging

from ..models.data_quality import QualityScore
from ..models.terminal import LNGTerminal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Field mapping & classification
# ---------------------------------------------------------------------------

# Map terminal model field names to the quality-score field names used by
# ``QualityScore.compute`` (which classifies via ``REQUIRED_FIELDS``).
_FIELD_MAP: dict[str, str] = {
    "terminal_name": "name",
    "country": "country",
    "terminal_type": "type",
    "status": "status",
}

# Scalar fields to check (excludes sub-models and meta fields like
# ``terminal_id``, ``aliases``, ``last_updated``).
_SCALAR_FIELDS: list[str] = [
    "terminal_name",
    "country",
    "terminal_type",
    "status",
    "capacity_mtpa",
    "year_commissioned",
    "operator",
    "owner",
    "epc_contractor",
    "capex_usd_million",
    "region",
    "latitude",
    "longitude",
    "metocean_notes",
]

# Engineering sub-model fields grouped by parent model attribute.
_ENGINEERING_CHECKS: dict[str, list[str]] = {
    "hull_design": [
        "hull_type",
        "loa_m",
        "beam_m",
        "depth_m",
        "draft_m",
        "displacement_tonnes",
        "mooring_type",
    ],
    "process_equipment": [
        "liquefaction_process",
        "number_of_trains",
        "capacity_per_train_mtpa",
        "compressor_type",
        "regasification_capacity_mmscfd",
        "regasification_type",
    ],
    "storage": [
        "tank_type",
        "number_of_tanks",
        "total_capacity_m3",
    ],
    "marine_infrastructure": [
        "water_depth_m",
        "jetty_count",
        "berth_count",
        "loading_arms_count",
    ],
}


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


class QualityScorer:
    """Compute data quality scores for LNG terminal records."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    # -- Public API ---------------------------------------------------------

    def score_terminals(self, terminals: list[LNGTerminal]) -> list[LNGTerminal]:
        """Compute quality scores for all *terminals*.

        Updates each terminal's ``data_quality_score`` field in place and
        returns the same list for convenient chaining.
        """
        for terminal in terminals:
            try:
                terminal.data_quality_score = self.score_terminal(terminal)
            except Exception as e:
                self.logger.warning(f"Failed to score '{terminal.terminal_name}': {e}")

        # Log summary statistics
        scores = [
            t.data_quality_score.total_score
            for t in terminals
            if t.data_quality_score is not None
        ]
        if scores:
            avg = sum(scores) / len(scores)
            self.logger.info(
                f"Quality scores: avg={avg:.1f}, min={min(scores):.1f}, "
                f"max={max(scores):.1f} ({len(scores)} terminals)"
            )

        return terminals

    def score_terminal(self, terminal: LNGTerminal) -> QualityScore:
        """Compute a :class:`QualityScore` for a single *terminal*."""
        field_presence: dict[str, bool] = {}

        # -- Scalar fields --------------------------------------------------
        for field_name in _SCALAR_FIELDS:
            value = getattr(terminal, field_name, None)
            score_key = _FIELD_MAP.get(field_name, field_name)
            field_presence[score_key] = value is not None

        # -- Pipeline presence (at least one pipeline counts) ---------------
        field_presence["pipeline_count"] = len(terminal.pipelines) > 0

        # -- Engineering sub-models -----------------------------------------
        for sub_model_name, sub_fields in _ENGINEERING_CHECKS.items():
            sub_model = getattr(terminal, sub_model_name, None)
            for sub_field in sub_fields:
                key = f"{sub_model_name}_{sub_field}"
                if sub_model is not None:
                    field_presence[key] = (
                        getattr(sub_model, sub_field, None) is not None
                    )
                else:
                    field_presence[key] = False

        return QualityScore.compute(
            field_presence=field_presence,
            source_count=len(terminal.sources),
        )
