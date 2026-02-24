"""
ABOUTME: Cross-database incident correlator for MAIB, NTSB, and USCG MISLE records.
ABOUTME: Matches incidents by date window, location proximity, and vessel name similarity.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
    TaxonomyRecord,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_DATE_WINDOW_DAYS = 5
_DEFAULT_LOCATION_KM = 100.0
_DEFAULT_NAME_SIMILARITY = 0.75
_EARTH_RADIUS_KM = 6371.0


@dataclass
class CorrelationConfig:
    """
    Thresholds for cross-database incident matching.

    Attributes:
        date_window_days: Maximum days between two incidents to be considered.
        location_threshold_km: Maximum distance (km) between two incidents.
        name_similarity_threshold: Minimum Jaccard token similarity for vessel names.
        require_location: Skip location check if neither record has coordinates.
    """

    date_window_days: int = _DEFAULT_DATE_WINDOW_DAYS
    location_threshold_km: float = _DEFAULT_LOCATION_KM
    name_similarity_threshold: float = _DEFAULT_NAME_SIMILARITY
    require_location: bool = False

    def __post_init__(self) -> None:
        if self.date_window_days < 0:
            raise ValueError("date_window_days must be >= 0")
        if self.location_threshold_km <= 0:
            raise ValueError("location_threshold_km must be > 0")
        if not 0.0 <= self.name_similarity_threshold <= 1.0:
            raise ValueError("name_similarity_threshold must be in [0, 1]")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CorrelationMatch:
    """
    A confirmed match between two TaxonomyRecord instances from different sources.

    Attributes:
        record_a: First matched record.
        record_b: Second matched record.
        date_diff_days: Absolute difference in incident dates.
        distance_km: Geographic distance (None if coordinates missing).
        name_similarity: Vessel name similarity score (0–1).
        confidence: Combined confidence score.
    """

    record_a: TaxonomyRecord
    record_b: TaxonomyRecord
    date_diff_days: Optional[int]
    distance_km: Optional[float]
    name_similarity: float
    confidence: float
    match_reasons: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Correlator
# ---------------------------------------------------------------------------


class IncidentCorrelator:
    """
    Finds matching incidents across MAIB, NTSB, and USCG MISLE datasets.

    Matching strategy (all criteria must pass to produce a match):
    1. Date proximity: within ``date_window_days``.
    2. Location proximity: within ``location_threshold_km`` when coordinates exist.
    3. Vessel name similarity: Jaccard token similarity >= ``name_similarity_threshold``
       when vessel names are present; skipped if both names are absent.

    Cross-source only: records with the same source are never matched against each other.
    """

    def __init__(self, config: Optional[CorrelationConfig] = None) -> None:
        self.config = config or CorrelationConfig()

    def correlate(
        self,
        records_a: Iterable[TaxonomyRecord],
        records_b: Iterable[TaxonomyRecord],
    ) -> List[CorrelationMatch]:
        """
        Find matching incidents between two record sets.

        Args:
            records_a: First set of TaxonomyRecord instances.
            records_b: Second set of TaxonomyRecord instances.

        Returns:
            List of CorrelationMatch sorted by confidence descending.
        """
        list_a = list(records_a)
        list_b = list(records_b)

        matches: List[CorrelationMatch] = []
        for a in list_a:
            for b in list_b:
                if a.source == b.source:
                    continue
                result = self._compare(a, b)
                if result is not None:
                    matches.append(result)

        matches.sort(key=lambda m: m.confidence, reverse=True)
        logger.info(
            "Correlator found %d matches between %d and %d records",
            len(matches),
            len(list_a),
            len(list_b),
        )
        return matches

    def correlate_multi(
        self,
        *record_sets: Iterable[TaxonomyRecord],
    ) -> List[CorrelationMatch]:
        """
        Find all cross-source matches across multiple record sets.

        Args:
            *record_sets: Variable number of TaxonomyRecord iterables.

        Returns:
            Deduplicated list of CorrelationMatch sorted by confidence descending.
        """
        lists = [list(rs) for rs in record_sets]
        all_matches: List[CorrelationMatch] = []
        for i in range(len(lists)):
            for j in range(i + 1, len(lists)):
                all_matches.extend(self.correlate(lists[i], lists[j]))

        # Deduplicate: keep highest-confidence match per (report_id_a, report_id_b) pair
        seen: Dict[Tuple[str, str], CorrelationMatch] = {}
        for m in all_matches:
            key = (
                min(m.record_a.report_id, m.record_b.report_id),
                max(m.record_a.report_id, m.record_b.report_id),
            )
            if key not in seen or m.confidence > seen[key].confidence:
                seen[key] = m

        deduped = sorted(seen.values(), key=lambda m: m.confidence, reverse=True)
        return deduped

    def _compare(
        self,
        a: TaxonomyRecord,
        b: TaxonomyRecord,
    ) -> Optional[CorrelationMatch]:
        """Compare two records; return a CorrelationMatch or None."""
        reasons: List[str] = []
        score_parts: List[float] = []

        # --- Date check ---
        date_diff = _days_apart(a.incident_date, b.incident_date)
        if date_diff is not None:
            if date_diff > self.config.date_window_days:
                return None
            date_score = 1.0 - (date_diff / max(self.config.date_window_days, 1))
            score_parts.append(date_score)
            reasons.append(f"date_diff={date_diff}d")
        # If both dates are missing, we do not enforce date matching

        # --- Location check ---
        dist_km: Optional[float] = None
        if a.latitude is not None and b.latitude is not None:
            dist_km = _haversine(a.latitude, a.longitude, b.latitude, b.longitude)
            if dist_km > self.config.location_threshold_km:
                return None
            loc_score = 1.0 - (dist_km / self.config.location_threshold_km)
            score_parts.append(loc_score)
            reasons.append(f"dist={dist_km:.1f}km")
        elif self.config.require_location:
            return None

        # --- Vessel name check ---
        name_sim = _jaccard_similarity(a.vessel_name, b.vessel_name)
        if a.vessel_name and b.vessel_name:
            if name_sim < self.config.name_similarity_threshold:
                return None
            score_parts.append(name_sim)
            reasons.append(f"name_sim={name_sim:.2f}")

        if not score_parts:
            # No evidence whatsoever
            return None

        confidence = sum(score_parts) / len(score_parts)

        return CorrelationMatch(
            record_a=a,
            record_b=b,
            date_diff_days=date_diff,
            distance_km=dist_km,
            name_similarity=name_sim,
            confidence=confidence,
            match_reasons=reasons,
        )


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------


def build_correlation_summary(matches: List[CorrelationMatch]) -> pd.DataFrame:
    """
    Build a summary DataFrame from a list of CorrelationMatch results.

    Columns:
        report_id_a, source_a, report_id_b, source_b,
        incident_date_a, incident_date_b,
        vessel_name_a, vessel_name_b,
        root_cause_a, root_cause_b,
        vessel_type_a, vessel_type_b,
        date_diff_days, distance_km, name_similarity, confidence, match_reasons

    Args:
        matches: List of CorrelationMatch instances.

    Returns:
        DataFrame, one row per match.
    """
    if not matches:
        return pd.DataFrame()

    rows = []
    for m in matches:
        rows.append(
            {
                "report_id_a": m.record_a.report_id,
                "source_a": m.record_a.source,
                "report_id_b": m.record_b.report_id,
                "source_b": m.record_b.source,
                "incident_date_a": m.record_a.incident_date,
                "incident_date_b": m.record_b.incident_date,
                "vessel_name_a": m.record_a.vessel_name,
                "vessel_name_b": m.record_b.vessel_name,
                "root_cause_a": m.record_a.root_cause.value,
                "root_cause_b": m.record_b.root_cause.value,
                "vessel_type_a": m.record_a.vessel_type,
                "vessel_type_b": m.record_b.vessel_type,
                "date_diff_days": m.date_diff_days,
                "distance_km": m.distance_km,
                "name_similarity": round(m.name_similarity, 4),
                "confidence": round(m.confidence, 4),
                "match_reasons": "; ".join(m.match_reasons),
            }
        )

    return pd.DataFrame(rows)


def build_pattern_report(
    records: List[TaxonomyRecord],
) -> pd.DataFrame:
    """
    Produce a cross-tabulation of incident patterns by cause type, vessel type, and year.

    Args:
        records: Combined list of TaxonomyRecord from all sources.

    Returns:
        DataFrame with columns: year, vessel_type, root_cause, source, count,
        fatalities, injuries.
    """
    if not records:
        return pd.DataFrame(
            columns=[
                "year",
                "vessel_type",
                "root_cause",
                "source",
                "count",
                "fatalities",
                "injuries",
            ]
        )

    rows = []
    for r in records:
        year = _extract_year(r.incident_date)
        rows.append(
            {
                "year": year,
                "vessel_type": r.vessel_type or "unknown",
                "root_cause": r.root_cause.value,
                "source": r.source,
                "count": 1,
                "fatalities": r.fatality_count,
                "injuries": r.injury_count,
            }
        )

    df = pd.DataFrame(rows)
    summary = (
        df.groupby(["year", "vessel_type", "root_cause", "source"], dropna=False)
        .agg(
            count=("count", "sum"),
            fatalities=("fatalities", "sum"),
            injuries=("injuries", "sum"),
        )
        .reset_index()
        .sort_values(["root_cause", "vessel_type"])
    )
    return summary


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _haversine(
    lat1: float,
    lon1: Optional[float],
    lat2: float,
    lon2: Optional[float],
) -> float:
    """Return great-circle distance in km between two (lat, lon) pairs."""
    if lon1 is None or lon2 is None:
        return float("inf")
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians((lon2 or 0) - (lon1 or 0))
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon / 2) ** 2
    )
    return _EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def _days_apart(
    date_a: Optional[str],
    date_b: Optional[str],
) -> Optional[int]:
    """Return absolute day difference between two ISO 8601 date strings, or None."""
    if not date_a or not date_b:
        return None
    try:
        da = _parse_date(date_a)
        db = _parse_date(date_b)
        if da is None or db is None:
            return None
        return abs((da - db).days)
    except Exception:
        return None


def _parse_date(value: str) -> Optional[date]:
    """Parse a date string; try ISO 8601 first then common formats."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None


def _jaccard_similarity(name_a: Optional[str], name_b: Optional[str]) -> float:
    """
    Compute token-level Jaccard similarity between two vessel name strings.

    Returns 0.0 if either name is None/empty.
    """
    if not name_a or not name_b:
        return 0.0
    tokens_a = set(name_a.upper().split())
    tokens_b = set(name_b.upper().split())
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def _extract_year(date_str: Optional[str]) -> Optional[int]:
    """Extract calendar year from an ISO 8601 date string."""
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None
