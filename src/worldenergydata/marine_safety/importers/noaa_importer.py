"""
NOAA Office of Response and Restoration (OR&R) Incident Importer

Imports oil spill and chemical release data from NOAA's Emergency Response Division.

Data Source: NOAA OR&R Incident News Archive
Schema:
    - id: Incident ID
    - open_date: Date incident opened
    - name: Incident name/title
    - location: Location description
    - lat, lon: GPS coordinates
    - threat: Type (Oil/Chemical/Other)
    - tags: Comma-separated tags
    - commodity: Substance involved
    - measure_skim, measure_shore, measure_bio, measure_disperse, measure_burn:
        Response measures (0/1)
    - max_ptl_release_gallons: Maximum potential release in gallons
    - posts: Number of posts/updates
    - description: Incident description
"""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from ..constants import IncidentType
from ..database.models import Incident, Location
from .base_importer import BaseImporter

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)


class NOAAImporter(BaseImporter):
    """Import NOAA Oil Spill and Chemical Release data."""

    # Map NOAA threat types to our IncidentType enum
    THREAT_TYPE_MAPPINGS = {
        "oil": IncidentType.POLLUTION,
        "chemical": IncidentType.POLLUTION,
        "other": IncidentType.OTHER,
    }

    # Response measure field mappings
    RESPONSE_MEASURE_MAPPINGS = {
        "measure_skim": "skimming",
        "measure_shore": "shoreline_cleanup",
        "measure_bio": "bioremediation",
        "measure_disperse": "dispersants",
        "measure_burn": "in_situ_burning",
    }

    # Cost estimate per gallon for cleanup (conservative average)
    CLEANUP_COST_PER_GALLON = 200

    def __init__(self, source_path: Path, session: Any, batch_size: int = 100):
        """
        Initialize NOAA data importer.

        Args:
            source_path: Path to incidents.csv
            session: SQLAlchemy session
            batch_size: Records per batch
        """
        super().__init__(source_path, session, batch_size)

        # Cache for locations (by coordinates)
        self._location_cache: Dict[str, int] = {}

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """Read records from NOAA incidents CSV file."""
        with open(self.source_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys (remove leading/trailing whitespace)
                normalized_row = {
                    k.strip() if k else k: v for k, v in row.items() if k is not None
                }
                yield normalized_row

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw NOAA record into standardized format."""
        try:
            # Guard clause: validate incident ID
            incident_id = self._extract_incident_id(raw_record)
            if not incident_id:
                return None

            # Guard clause: validate date
            incident_date = self._parse_incident_date(raw_record)
            if incident_date is None:
                return None

            # Build parsed record from extracted components
            parsed = self._build_base_record(incident_id, incident_date, raw_record)

            # Add optional components
            self._add_title_and_description(parsed, raw_record)
            self._add_estimated_damage(parsed, raw_record)
            self._add_location_data(parsed, raw_record)
            self._add_metadata(parsed, raw_record)
            self._add_casualty_defaults(parsed)

            return parsed

        except Exception as e:
            logger.error(f"Error parsing NOAA record {raw_record.get('id')}: {e}")
            return None

    def _extract_incident_id(self, raw_record: Dict[str, Any]) -> Optional[str]:
        """Extract and validate incident ID from raw record."""
        incident_id = raw_record.get("id", "").strip()
        return incident_id if incident_id else None

    def _parse_incident_date(self, raw_record: Dict[str, Any]) -> Optional[datetime]:
        """Parse and validate incident date from raw record."""
        date_str = raw_record.get("open_date", "").strip()
        if not date_str:
            return None
        return self._parse_date(date_str)

    def _build_base_record(
        self, incident_id: str, incident_date: datetime, raw_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the base parsed record with required fields."""
        threat = raw_record.get("threat", "").strip().lower()
        return {
            "source_agency": "NOAA_ORR",
            "source_incident_id": incident_id,
            "incident_date": incident_date,
            "incident_type": self.THREAT_TYPE_MAPPINGS.get(threat, IncidentType.OTHER),
        }

    def _add_title_and_description(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Extract and add title and description fields."""
        name = raw_record.get("name", "").strip()
        description = raw_record.get("description", "").strip()

        if name:
            parsed["title"] = name[:500]

        if description:
            parsed["description"] = f"{name}\n\n{description}" if name else description

    def _add_estimated_damage(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Calculate and add estimated damage from release gallons."""
        gallons = self._parse_release_gallons(raw_record)
        if gallons is not None:
            estimated_cost = gallons * self.CLEANUP_COST_PER_GALLON
            parsed["estimated_damage_usd"] = Decimal(str(estimated_cost))

    def _parse_release_gallons(self, raw_record: Dict[str, Any]) -> Optional[float]:
        """Parse max potential release gallons from raw record."""
        max_release = raw_record.get("max_ptl_release_gallons", "").strip()
        if not max_release or max_release in ("0", "None"):
            return None
        try:
            return float(max_release)
        except (ValueError, TypeError):
            return None

    def _add_location_data(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Extract and add location data (coordinates and name)."""
        location_data = {}

        # Parse coordinates
        coords = self._parse_coordinates(raw_record)
        if coords:
            location_data["latitude"] = coords[0]
            location_data["longitude"] = coords[1]

        # Parse location name
        location_name = raw_record.get("location", "").strip()
        if location_name:
            location_data["location_name"] = location_name[:500]

        if location_data:
            parsed["location"] = location_data

    def _parse_coordinates(self, raw_record: Dict[str, Any]) -> Optional[tuple]:
        """Parse and validate GPS coordinates from raw record."""
        lat_str = raw_record.get("lat", "").strip()
        lon_str = raw_record.get("lon", "").strip()

        if not (lat_str and lon_str):
            return None

        try:
            lat = float(lat_str)
            lon = float(lon_str)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
        except (ValueError, TypeError):
            pass

        return None

    def _add_metadata(self, parsed: Dict[str, Any], raw_record: Dict[str, Any]) -> None:
        """Extract and add metadata fields."""
        metadata = {}

        self._add_commodity_and_tags(metadata, raw_record)
        self._add_response_measures(metadata, raw_record)
        self._add_numeric_metadata(metadata, raw_record)

        if metadata:
            parsed["metadata_json"] = metadata

    def _add_commodity_and_tags(
        self, metadata: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Add commodity and tags to metadata."""
        commodity = raw_record.get("commodity", "").strip()
        if commodity:
            metadata["commodity"] = commodity

        tags = raw_record.get("tags", "").strip()
        if tags:
            metadata["tags"] = tags

    def _add_response_measures(
        self, metadata: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Extract response measures using dictionary dispatch."""
        measures = [
            measure_name
            for field_name, measure_name in self.RESPONSE_MEASURE_MAPPINGS.items()
            if raw_record.get(field_name, "").strip() == "1"
        ]

        if measures:
            metadata["response_measures"] = measures

    def _add_numeric_metadata(
        self, metadata: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Add numeric metadata fields (posts count, release gallons)."""
        # Number of posts/updates
        posts = raw_record.get("posts", "").strip()
        if posts:
            try:
                metadata["num_updates"] = int(posts)
            except (ValueError, TypeError):
                pass

        # Maximum potential release
        gallons = self._parse_release_gallons(raw_record)
        if gallons is not None:
            metadata["max_potential_release_gallons"] = gallons

    def _add_casualty_defaults(self, parsed: Dict[str, Any]) -> None:
        """Add default casualty values (no casualties in NOAA data)."""
        parsed["fatalities"] = 0
        parsed["injuries"] = 0
        parsed["missing_persons"] = 0

    def map_to_model(self, parsed_record: Dict[str, Any]) -> Optional[Incident]:
        """Map parsed record to Incident model."""
        try:
            # Check for duplicate using source_agency + source_incident_id
            existing = (
                self.session.query(Incident)
                .filter(
                    Incident.source_agency == parsed_record.get("source_agency"),
                    Incident.source_incident_id
                    == parsed_record.get("source_incident_id"),
                )
                .first()
            )

            if existing:
                self.stats["duplicates"] += 1
                return None

            # Create location
            location_id = None
            if "location" in parsed_record:
                location_id = self._get_or_create_location(parsed_record["location"])

            # Create incident
            incident = Incident(
                source_agency=parsed_record.get("source_agency"),
                source_incident_id=parsed_record.get("source_incident_id"),
                incident_date=parsed_record.get("incident_date"),
                incident_type=parsed_record.get("incident_type", IncidentType.OTHER),
                title=parsed_record.get("title"),
                description=parsed_record.get("description"),
                fatalities=parsed_record.get("fatalities", 0),
                injuries=parsed_record.get("injuries", 0),
                missing_persons=parsed_record.get("missing_persons", 0),
                estimated_damage_usd=parsed_record.get("estimated_damage_usd"),
                location_id=location_id,
                vessel_id=None,  # No vessel data in NOAA
                metadata_json=parsed_record.get("metadata_json"),
            )

            return incident

        except Exception as e:
            incident_id = parsed_record.get("source_incident_id")
            logger.error(f"Error creating model for {incident_id}: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse NOAA date format (YYYY-MM-DD)."""
        if not date_str:
            return None

        # Try various date formats
        formats = [
            "%Y-%m-%d",  # 2025-09-29
            "%m/%d/%Y",  # 09/29/2025
            "%m/%d/%y",  # 09/29/25
            "%Y/%m/%d",  # 2025/09/29
            "%d-%m-%Y",  # 29-09-2025
            "%d/%m/%Y",  # 29/09/2025
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try to extract just the date part if there's a time component
        try:
            date_part = date_str.split(" ")[0]
            for fmt in formats:
                try:
                    return datetime.strptime(date_part, fmt)
                except ValueError:
                    continue
        except Exception:
            pass

        return None

    def _get_or_create_location(self, location_data: Dict[str, Any]) -> Optional[int]:
        """Create location from GPS coordinates or location name."""
        try:
            # Build cache key
            if "latitude" in location_data and "longitude" in location_data:
                # Use coordinates for caching
                lat = location_data["latitude"]
                lon = location_data["longitude"]
                cache_key = f"noaa_{lat:.4f}_{lon:.4f}"

                # Check cache
                if cache_key in self._location_cache:
                    return self._location_cache[cache_key]

                # Check database for nearby coordinates (within 0.001 degrees)
                lat_min = Decimal(str(lat - 0.001))
                lat_max = Decimal(str(lat + 0.001))
                lon_min = Decimal(str(lon - 0.001))
                lon_max = Decimal(str(lon + 0.001))
                existing = (
                    self.session.query(Location)
                    .filter(
                        Location.latitude.between(lat_min, lat_max),
                        Location.longitude.between(lon_min, lon_max),
                    )
                    .first()
                )

                if existing:
                    self._location_cache[cache_key] = existing.location_id
                    return existing.location_id

                # Create new location with coordinates
                default_name = f"Location {lat:.4f}, {lon:.4f}"
                location = Location(
                    location_name=location_data.get("location_name", default_name),
                    latitude=Decimal(str(lat)),
                    longitude=Decimal(str(lon)),
                    country_code="US",  # Most NOAA incidents are US
                )
            else:
                # No coordinates, use location name only
                location_name = location_data.get("location_name")
                if not location_name:
                    return None

                cache_key = f"noaa_{location_name}"

                # Check cache
                if cache_key in self._location_cache:
                    return self._location_cache[cache_key]

                # Check database
                existing = (
                    self.session.query(Location)
                    .filter(Location.location_name == location_name)
                    .first()
                )

                if existing:
                    self._location_cache[cache_key] = existing.location_id
                    return existing.location_id

                # Create new location
                location = Location(
                    location_name=location_name,
                    country_code="US",  # Most NOAA incidents are US
                )

            self.session.add(location)
            self.session.flush()

            if "latitude" in location_data and "longitude" in location_data:
                loc_lat = location_data["latitude"]
                loc_lon = location_data["longitude"]
                cache_key = f"noaa_{loc_lat:.4f}_{loc_lon:.4f}"
            else:
                cache_key = f"noaa_{location_data.get('location_name')}"

            self._location_cache[cache_key] = location.location_id
            return location.location_id

        except Exception as e:
            logger.error(f"Error creating location: {e}")
            return None

    def is_duplicate(self, model_instance: Incident) -> bool:
        """Check if record already exists in database."""
        existing = (
            self.session.query(Incident)
            .filter(
                Incident.source_agency == model_instance.source_agency,
                Incident.source_incident_id == model_instance.source_incident_id,
            )
            .first()
        )

        return existing is not None
