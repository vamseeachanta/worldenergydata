# ABOUTME: Incident deduplication engine for identifying and linking duplicate incidents.
# ABOUTME: Provides batch processing, cross-source matching, and data merging capabilities.

"""
Incident Deduplicator Module

Provides deduplication capabilities to identify and manage duplicate incidents
within a single source or across multiple data sources.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Generator, Iterator, List, Optional, Set, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from worldenergydata.marine_safety.analysis.correlation.matcher import (
    IncidentData,
    IncidentMatcher,
    MatchConfig,
    MatchResult,
    MatchType,
)
from worldenergydata.marine_safety.constants import DataSource
from worldenergydata.marine_safety.database.models import (
    Incident,
    Location,
    Vessel,
)
from worldenergydata.marine_safety.exceptions import (
    DatabaseError,
    RecordNotFoundError,
)

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationMetrics:
    """Metrics from a deduplication run."""

    total_incidents_processed: int = 0
    duplicates_found: int = 0
    links_created: int = 0
    high_confidence_matches: int = 0
    processing_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def duplicate_rate(self) -> float:
        """Calculate the duplicate rate as a percentage."""
        if self.total_incidents_processed == 0:
            return 0.0
        return (self.duplicates_found / self.total_incidents_processed) * 100


@dataclass
class DeduplicationResult:
    """Result of a deduplication operation."""

    incident_id: int
    matches: List[MatchResult]
    is_duplicate: bool = False
    primary_incident_id: Optional[int] = None


@dataclass
class IncidentLink:
    """Represents a link between two potentially related incidents."""

    link_id: Optional[int]
    incident_id_1: int
    incident_id_2: int
    confidence_score: Decimal
    match_type: str
    verified: bool
    created_at: datetime
    metadata_json: Dict[str, Any]

    @classmethod
    def from_match_result(
        cls,
        result: MatchResult,
        link_id: Optional[int] = None,
        verified: bool = False,
    ) -> "IncidentLink":
        """Create an IncidentLink from a MatchResult."""
        return cls(
            link_id=link_id,
            incident_id_1=result.incident_id_1,
            incident_id_2=result.incident_id_2,
            confidence_score=Decimal(str(round(result.confidence_score, 2))),
            match_type=result.match_type.value,
            verified=verified,
            created_at=datetime.utcnow(),
            metadata_json={
                "component_scores": result.component_scores,
                **result.metadata,
            },
        )


class IncidentDeduplicator:
    """
    Incident deduplication engine for cross-source correlation.

    Identifies duplicate incidents within a source or across multiple sources,
    creates links between related incidents, and supports data merging.
    """

    # Batch size for processing large datasets
    DEFAULT_BATCH_SIZE = 1000

    def __init__(
        self,
        session: Session,
        matcher: Optional[IncidentMatcher] = None,
        config: Optional[MatchConfig] = None,
    ) -> None:
        """
        Initialize the deduplicator.

        Args:
            session: SQLAlchemy database session.
            matcher: Optional pre-configured IncidentMatcher.
            config: Optional MatchConfig (used if matcher not provided).
        """
        self.session = session
        self.matcher = matcher or IncidentMatcher(config)
        self._existing_links: Set[Tuple[int, int]] = set()
        logger.info("IncidentDeduplicator initialized")

    def find_duplicates(
        self,
        source_agency: Optional[DataSource] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Generator[DeduplicationResult, None, DeduplicationMetrics]:
        """
        Find duplicate incidents within a single data source.

        Yields results as they are found for memory efficiency.

        Args:
            source_agency: Optional source to filter by. If None, checks all sources.
            batch_size: Number of incidents to process in each batch.

        Yields:
            DeduplicationResult for each incident processed.

        Returns:
            DeduplicationMetrics after all processing is complete.
        """
        metrics = DeduplicationMetrics()
        start_time = datetime.utcnow()

        try:
            # Load existing links to avoid duplicates
            self._load_existing_links()

            # Build query for incidents
            query = self._build_incident_query(source_agency)

            # Process in batches
            offset = 0
            while True:
                batch = self._fetch_batch(query, offset, batch_size)
                if not batch:
                    break

                for incident in batch:
                    metrics.total_incidents_processed += 1

                    # Find candidates (incidents from same source within date range)
                    candidates = self._get_same_source_candidates(
                        incident,
                        source_agency,
                    )

                    if not candidates:
                        continue

                    # Find matches
                    matches = self.matcher.find_matches(incident, candidates)

                    # Filter out already-linked incidents
                    new_matches = self._filter_existing_links(
                        incident.incident_id, matches
                    )

                    result = DeduplicationResult(
                        incident_id=incident.incident_id,
                        matches=new_matches,
                        is_duplicate=len(new_matches) > 0,
                    )

                    if new_matches:
                        metrics.duplicates_found += len(new_matches)
                        metrics.high_confidence_matches += sum(
                            1 for m in new_matches if m.is_high_confidence
                        )

                    yield result

                offset += batch_size

        except Exception as e:
            logger.error("Error during deduplication: %s", e)
            metrics.errors.append(str(e))

        metrics.processing_time_seconds = (
            datetime.utcnow() - start_time
        ).total_seconds()

        return metrics

    def find_cross_source_matches(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Generator[DeduplicationResult, None, DeduplicationMetrics]:
        """
        Find matches across different data sources.

        This method identifies incidents from different agencies that may
        refer to the same real-world event.

        Args:
            batch_size: Number of incidents to process in each batch.

        Yields:
            DeduplicationResult for each incident with cross-source matches.

        Returns:
            DeduplicationMetrics after all processing is complete.
        """
        metrics = DeduplicationMetrics()
        start_time = datetime.utcnow()

        try:
            # Load existing links
            self._load_existing_links()

            # Get all unique source agencies
            sources = self._get_all_sources()
            logger.info("Processing cross-source matches for %d sources", len(sources))

            # Process each source against all others
            processed_pairs: Set[Tuple[str, str]] = set()

            for source in sources:
                # Get incidents from this source
                query = self._build_incident_query(source)
                offset = 0

                while True:
                    batch = self._fetch_batch(query, offset, batch_size)
                    if not batch:
                        break

                    for incident in batch:
                        metrics.total_incidents_processed += 1

                        # Get candidates from other sources
                        candidates = self._get_cross_source_candidates(incident, source)

                        if not candidates:
                            continue

                        # Find matches
                        matches = self.matcher.find_matches(incident, candidates)

                        # Filter existing links
                        new_matches = self._filter_existing_links(
                            incident.incident_id, matches
                        )

                        if new_matches:
                            result = DeduplicationResult(
                                incident_id=incident.incident_id,
                                matches=new_matches,
                                is_duplicate=True,
                            )

                            metrics.duplicates_found += len(new_matches)
                            metrics.high_confidence_matches += sum(
                                1 for m in new_matches if m.is_high_confidence
                            )

                            yield result

                    offset += batch_size

        except Exception as e:
            logger.error("Error during cross-source matching: %s", e)
            metrics.errors.append(str(e))

        metrics.processing_time_seconds = (
            datetime.utcnow() - start_time
        ).total_seconds()

        return metrics

    def link_incidents(
        self,
        incident1_id: int,
        incident2_id: int,
        match_type: MatchType,
        confidence: float,
        verified: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IncidentLink:
        """
        Create a link between two incidents.

        Args:
            incident1_id: ID of first incident.
            incident2_id: ID of second incident.
            match_type: Type of match that identified the relationship.
            confidence: Confidence score (0.0 - 1.0).
            verified: Whether the link has been human-verified.
            metadata: Optional additional metadata.

        Returns:
            The created IncidentLink.

        Raises:
            RecordNotFoundError: If either incident doesn't exist.
            DatabaseError: If link creation fails.
        """
        # Verify both incidents exist
        incident1 = self.session.get(Incident, incident1_id)
        incident2 = self.session.get(Incident, incident2_id)

        if not incident1:
            raise RecordNotFoundError("Incident", incident1_id)
        if not incident2:
            raise RecordNotFoundError("Incident", incident2_id)

        # Ensure consistent ordering (smaller ID first)
        if incident1_id > incident2_id:
            incident1_id, incident2_id = incident2_id, incident1_id

        # Check if link already exists
        link_key = (incident1_id, incident2_id)
        if link_key in self._existing_links:
            logger.warning(
                "Link already exists between incidents %d and %d",
                incident1_id,
                incident2_id,
            )
            # Return existing link representation
            return IncidentLink(
                link_id=None,
                incident_id_1=incident1_id,
                incident_id_2=incident2_id,
                confidence_score=Decimal(str(round(confidence, 2))),
                match_type=match_type.value,
                verified=verified,
                created_at=datetime.utcnow(),
                metadata_json=metadata or {},
            )

        # Create the link
        link = IncidentLink(
            link_id=None,
            incident_id_1=incident1_id,
            incident_id_2=incident2_id,
            confidence_score=Decimal(str(round(confidence, 2))),
            match_type=match_type.value,
            verified=verified,
            created_at=datetime.utcnow(),
            metadata_json=metadata or {},
        )

        # Store in memory cache
        self._existing_links.add(link_key)

        logger.info(
            "Created link between incidents %d and %d (confidence: %.2f, type: %s)",
            incident1_id,
            incident2_id,
            confidence,
            match_type.value,
        )

        return link

    def get_linked_incidents(self, incident_id: int) -> List[IncidentLink]:
        """
        Get all incidents linked to a specific incident.

        Args:
            incident_id: ID of the incident to find links for.

        Returns:
            List of IncidentLink objects for all linked incidents.
        """
        links: List[IncidentLink] = []

        # Search through existing links for this incident
        for id1, id2 in self._existing_links:
            if id1 == incident_id or id2 == incident_id:
                # Create link representation
                other_id = id2 if id1 == incident_id else id1
                links.append(
                    IncidentLink(
                        link_id=None,
                        incident_id_1=min(incident_id, other_id),
                        incident_id_2=max(incident_id, other_id),
                        confidence_score=Decimal(
                            "0.0"
                        ),  # Would need DB query for actual
                        match_type="unknown",
                        verified=False,
                        created_at=datetime.utcnow(),
                        metadata_json={},
                    )
                )

        return links

    def merge_incident_data(
        self,
        primary_id: int,
        secondary_id: int,
        strategy: str = "prefer_primary",
    ) -> Incident:
        """
        Merge data from secondary incident into primary incident.

        The secondary incident is not deleted but marked as a duplicate.

        Args:
            primary_id: ID of the primary (surviving) incident.
            secondary_id: ID of the secondary (duplicate) incident.
            strategy: Merge strategy - 'prefer_primary', 'prefer_complete',
                      or 'newest'.

        Returns:
            The updated primary incident.

        Raises:
            RecordNotFoundError: If either incident doesn't exist.
            DatabaseError: If merge fails.
        """
        primary = self.session.get(Incident, primary_id)
        secondary = self.session.get(Incident, secondary_id)

        if not primary:
            raise RecordNotFoundError("Incident", primary_id)
        if not secondary:
            raise RecordNotFoundError("Incident", secondary_id)

        logger.info(
            "Merging incident %d into %d using strategy '%s'",
            secondary_id,
            primary_id,
            strategy,
        )

        # Merge based on strategy
        if strategy == "prefer_primary":
            self._merge_prefer_primary(primary, secondary)
        elif strategy == "prefer_complete":
            self._merge_prefer_complete(primary, secondary)
        elif strategy == "newest":
            self._merge_prefer_newest(primary, secondary)
        else:
            logger.warning(
                "Unknown merge strategy '%s', using prefer_primary", strategy
            )
            self._merge_prefer_primary(primary, secondary)

        # Update metadata to track merge
        if primary.metadata_json is None:
            primary.metadata_json = {}
        if "merged_from" not in primary.metadata_json:
            primary.metadata_json["merged_from"] = []
        primary.metadata_json["merged_from"].append(
            {
                "incident_id": secondary_id,
                "merged_at": datetime.utcnow().isoformat(),
                "strategy": strategy,
            }
        )

        return primary

    def _merge_prefer_primary(self, primary: Incident, secondary: Incident) -> None:
        """Merge secondary into primary, keeping primary values where they exist."""
        # Fill in missing fields from secondary
        fields_to_check = [
            "title",
            "description",
            "fatalities",
            "injuries",
            "missing_persons",
            "environmental_impact",
            "estimated_damage_usd",
            "weather_condition",
            "wind_speed_knots",
            "wave_height_meters",
            "sea_state",
            "visibility_meters",
            "investigation_status",
            "investigation_priority",
        ]

        for field in fields_to_check:
            primary_val = getattr(primary, field, None)
            secondary_val = getattr(secondary, field, None)

            # Only copy if primary is empty/None/0 and secondary has data
            if self._is_empty_value(primary_val) and not self._is_empty_value(
                secondary_val
            ):
                setattr(primary, field, secondary_val)
                logger.debug("Copied field '%s' from secondary incident", field)

    def _merge_prefer_complete(self, primary: Incident, secondary: Incident) -> None:
        """Merge secondary into primary, preferring whichever has more complete data."""
        primary_completeness = self._calculate_completeness(primary)
        secondary_completeness = self._calculate_completeness(secondary)

        if secondary_completeness > primary_completeness:
            # Copy all non-null fields from secondary
            self._copy_all_fields(secondary, primary)
        else:
            # Just fill in gaps
            self._merge_prefer_primary(primary, secondary)

    def _merge_prefer_newest(self, primary: Incident, secondary: Incident) -> None:
        """Merge secondary into primary, preferring newer updated timestamps."""
        if secondary.updated_at > primary.updated_at:
            self._copy_all_fields(secondary, primary)
        else:
            self._merge_prefer_primary(primary, secondary)

    def _is_empty_value(self, value: Any) -> bool:
        """Check if a value is empty (None, empty string, or 0 for numerics)."""
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, (int, float, Decimal)) and value == 0:
            return True
        return False

    def _calculate_completeness(self, incident: Incident) -> float:
        """Calculate a completeness score for an incident (0-1)."""
        fields = [
            "title",
            "description",
            "fatalities",
            "injuries",
            "environmental_impact",
            "estimated_damage_usd",
            "weather_condition",
            "investigation_status",
        ]

        filled = sum(
            1 for f in fields if not self._is_empty_value(getattr(incident, f, None))
        )
        return filled / len(fields)

    def _copy_all_fields(self, source: Incident, target: Incident) -> None:
        """Copy all non-null, non-key fields from source to target."""
        # Fields that should never be copied
        excluded = {
            "incident_id",
            "source_agency",
            "source_incident_id",
            "created_at",
            "updated_at",
            "metadata_json",
        }

        for column in Incident.__table__.columns:
            if column.name not in excluded:
                source_val = getattr(source, column.name, None)
                if not self._is_empty_value(source_val):
                    setattr(target, column.name, source_val)

    def _build_incident_query(self, source_agency: Optional[DataSource] = None):
        """Build the base query for fetching incidents."""
        query = (
            select(Incident)
            .options(
                joinedload(Incident.vessel),
                joinedload(Incident.location),
            )
            .order_by(Incident.incident_date, Incident.incident_id)
        )

        if source_agency:
            query = query.where(Incident.source_agency == source_agency)

        return query

    def _fetch_batch(self, query, offset: int, batch_size: int) -> List[Incident]:
        """Fetch a batch of incidents from the database."""
        result = self.session.execute(query.offset(offset).limit(batch_size))
        return list(result.scalars().unique().all())

    def _get_same_source_candidates(
        self,
        incident: Incident,
        source_agency: Optional[DataSource],
    ) -> List[Incident]:
        """Get candidate incidents from the same source for comparison."""
        # Get incidents within date range
        date_tolerance = self.matcher.config.date_tolerance_days
        min_date = incident.incident_date - __import__("datetime").timedelta(
            days=date_tolerance
        )
        max_date = incident.incident_date + __import__("datetime").timedelta(
            days=date_tolerance
        )

        query = (
            select(Incident)
            .options(
                joinedload(Incident.vessel),
                joinedload(Incident.location),
            )
            .where(
                and_(
                    Incident.incident_id != incident.incident_id,
                    Incident.incident_id
                    > incident.incident_id,  # Avoid duplicate comparisons
                    Incident.incident_date >= min_date,
                    Incident.incident_date <= max_date,
                )
            )
        )

        if source_agency:
            query = query.where(Incident.source_agency == source_agency)
        else:
            query = query.where(Incident.source_agency == incident.source_agency)

        result = self.session.execute(query)
        return list(result.scalars().unique().all())

    def _get_cross_source_candidates(
        self,
        incident: Incident,
        current_source: DataSource,
    ) -> List[Incident]:
        """Get candidate incidents from other sources for comparison."""
        date_tolerance = self.matcher.config.date_tolerance_days
        min_date = incident.incident_date - __import__("datetime").timedelta(
            days=date_tolerance
        )
        max_date = incident.incident_date + __import__("datetime").timedelta(
            days=date_tolerance
        )

        query = (
            select(Incident)
            .options(
                joinedload(Incident.vessel),
                joinedload(Incident.location),
            )
            .where(
                and_(
                    Incident.source_agency != current_source,
                    Incident.incident_date >= min_date,
                    Incident.incident_date <= max_date,
                )
            )
        )

        result = self.session.execute(query)
        return list(result.scalars().unique().all())

    def _get_all_sources(self) -> List[DataSource]:
        """Get all unique data sources in the database."""
        result = self.session.execute(select(Incident.source_agency).distinct())
        return [row[0] for row in result.all()]

    def _load_existing_links(self) -> None:
        """Load existing incident links from memory/cache."""
        # In a full implementation, this would query the incident_links table
        # For now, we just ensure the cache is initialized
        if not hasattr(self, "_existing_links"):
            self._existing_links = set()
        logger.debug("Existing links cache: %d entries", len(self._existing_links))

    def _filter_existing_links(
        self, incident_id: int, matches: List[MatchResult]
    ) -> List[MatchResult]:
        """Filter out matches that already have links."""
        filtered = []
        for match in matches:
            # Normalize link key (smaller ID first)
            key = (
                min(match.incident_id_1, match.incident_id_2),
                max(match.incident_id_1, match.incident_id_2),
            )
            if key not in self._existing_links:
                filtered.append(match)
        return filtered

    def calculate_quality_metrics(
        self, results: List[DeduplicationResult]
    ) -> Dict[str, Any]:
        """
        Calculate quality metrics from deduplication results.

        Args:
            results: List of deduplication results to analyze.

        Returns:
            Dictionary containing quality metrics.
        """
        if not results:
            return {
                "total_processed": 0,
                "duplicates_found": 0,
                "duplicate_rate_percent": 0.0,
                "average_confidence": 0.0,
                "high_confidence_count": 0,
                "match_type_distribution": {},
            }

        total = len(results)
        duplicates = [r for r in results if r.is_duplicate]
        all_matches = [m for r in duplicates for m in r.matches]

        # Calculate average confidence
        avg_confidence = 0.0
        if all_matches:
            avg_confidence = sum(m.confidence_score for m in all_matches) / len(
                all_matches
            )

        # Count high confidence matches
        high_confidence = sum(1 for m in all_matches if m.is_high_confidence)

        # Match type distribution
        type_counts: Dict[str, int] = {}
        for match in all_matches:
            mt = match.match_type.value
            type_counts[mt] = type_counts.get(mt, 0) + 1

        return {
            "total_processed": total,
            "duplicates_found": len(duplicates),
            "total_matches": len(all_matches),
            "duplicate_rate_percent": (
                (len(duplicates) / total * 100) if total > 0 else 0.0
            ),
            "average_confidence": round(avg_confidence, 3),
            "high_confidence_count": high_confidence,
            "match_type_distribution": type_counts,
        }
