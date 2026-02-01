"""Dataclass models for BSEE pipeline permit and location records.

Provides domain logic (computed properties) on top of validated data
from PipelinePermitSchema / PipelineLocationSchema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

_INACTIVE_STATUS_CODES: frozenset[str] = frozenset({"ABN", "OUT", "RMV"})

_DEEPWATER_DEPTH_THRESHOLD: float = 1000.0


@dataclass
class PipelinePermit:
    """Domain model for a BSEE pipeline permit record.

    Attributes use snake_case following Python conventions.
    """

    segment_num: Optional[str] = None
    ppl_size_code: Optional[str] = None
    maop_prss: Optional[float] = None
    recv_maop_prss: Optional[float] = None
    seg_length: Optional[float] = None
    max_wtr_dpth: Optional[float] = None
    min_wtr_dpth: Optional[float] = None
    prod_code: Optional[str] = None
    status_code: Optional[str] = None
    ppl_const_date: Optional[str] = None
    aban_date: Optional[str] = None
    area_code: Optional[str] = None
    block_number: Optional[str] = None
    lease_number: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """Pipeline is active when status is not abandoned/removed/out."""
        if self.status_code is None:
            return False
        return self.status_code not in _INACTIVE_STATUS_CODES

    @property
    def is_deepwater(self) -> bool:
        """Pipeline is deepwater when max water depth exceeds 1000 ft."""
        return (self.max_wtr_dpth or 0) > _DEEPWATER_DEPTH_THRESHOLD

    @property
    def segment_key(self) -> str:
        """Unique key: ``{area_code}_{block_number}_{segment_num}``."""
        return f"{self.area_code}_{self.block_number}_{self.segment_num}"


@dataclass
class PipelineLocation:
    """Domain model for a BSEE pipeline location point.

    Represents a single survey point along a pipeline segment.
    """

    segment_num: Optional[str] = None
    point_num: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    water_depth: Optional[float] = None
    area_code: Optional[str] = None
    block_number: Optional[str] = None
