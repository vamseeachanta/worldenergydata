from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar

from pydantic import BaseModel, Field

from ..constants import SourceReliability

# ---------------------------------------------------------------------------
# Field classification used by QualityScore.compute
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: list[str] = ["name", "country", "type", "status"]

ENGINEERING_PREFIXES: tuple[str, ...] = (
    "hull",
    "pipeline",
    "process",
    "storage",
    "marine",
)


def _is_engineering_field(field_name: str) -> bool:
    """Return True if *field_name* belongs to an engineering sub-model."""
    return any(field_name.startswith(prefix) for prefix in ENGINEERING_PREFIXES)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SourceCitation(BaseModel):
    """Tracks where a particular piece of data originated."""

    source_name: str
    source_url: str | None = None
    access_date: date
    fields_sourced: list[str]
    reliability: SourceReliability


class QualityScore(BaseModel):
    """Aggregate quality / completeness score for a terminal record."""

    total_score: float = Field(ge=0, le=100)
    required_fields_score: float = Field(ge=0, le=100)
    optional_fields_score: float = Field(ge=0, le=100)
    engineering_score: float = Field(ge=0, le=100)
    source_count: int = Field(ge=0)
    field_scores: dict[str, bool] = {}
    computed_at: datetime

    # Weighting constants
    _WEIGHT_REQUIRED: ClassVar[float] = 0.50
    _WEIGHT_OPTIONAL: ClassVar[float] = 0.30
    _WEIGHT_ENGINEERING: ClassVar[float] = 0.20

    @classmethod
    def compute(
        cls,
        field_presence: dict[str, bool],
        required_fields: list[str] | None = None,
        *,
        source_count: int = 0,
    ) -> QualityScore:
        """Build a *QualityScore* from a per-field presence map.

        Parameters
        ----------
        field_presence:
            Mapping of ``field_name -> has_value`` for every field in the
            terminal record.
        required_fields:
            Field names that are considered required.  Defaults to
            ``REQUIRED_FIELDS`` when *None*.
        source_count:
            Number of independent sources that contributed data.
        """
        if required_fields is None:
            required_fields = REQUIRED_FIELDS

        required_set = set(required_fields)

        req_fields = {k: v for k, v in field_presence.items() if k in required_set}
        eng_fields = {
            k: v
            for k, v in field_presence.items()
            if k not in required_set and _is_engineering_field(k)
        }
        opt_fields = {
            k: v
            for k, v in field_presence.items()
            if k not in required_set and not _is_engineering_field(k)
        }

        def _pct(mapping: dict[str, bool]) -> float:
            if not mapping:
                return 100.0
            return (sum(mapping.values()) / len(mapping)) * 100.0

        required_fields_score = _pct(req_fields)
        optional_fields_score = _pct(opt_fields)
        engineering_score = _pct(eng_fields)

        total_score = (
            cls._WEIGHT_REQUIRED * required_fields_score
            + cls._WEIGHT_OPTIONAL * optional_fields_score
            + cls._WEIGHT_ENGINEERING * engineering_score
        )

        return cls(
            total_score=round(total_score, 2),
            required_fields_score=round(required_fields_score, 2),
            optional_fields_score=round(optional_fields_score, 2),
            engineering_score=round(engineering_score, 2),
            source_count=source_count,
            field_scores=dict(field_presence),
            computed_at=datetime.utcnow(),
        )
