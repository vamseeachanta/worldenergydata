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
    - measure_skim, measure_shore, measure_bio, measure_disperse, measure_burn: Response measures (0/1)
    - max_ptl_release_gallons: Maximum potential release in gallons
    - posts: Number of posts/updates
    - description: Incident description
"""

import csv
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from ..constants import IncidentType
from ..database.models import Incident, Location
from .base_importer import BaseImporter


class NOAAImporter(BaseImporter):
    """Import NOAA Oil Spill and Chemical Release data."""

    # Map NOAA threat types to our IncidentType enum
    THREAT_TYPE_MAPPINGS = {
        "oil": IncidentType.POLLUTION,
        "chemical": IncidentType.POLLUTION,
        "other": IncidentType.OTHER,
    }

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
            incident_id = raw_record.get("id", "").strip()
            if not incident_id:
                return None

            # Basic mappings
            parsed = {
                "source_agency": "NOAA_ORR",
                "source_incident_id": incident_id,
            }

            # Parse date
            date_str = raw_record.get("open_date", "").strip()
            if date_str:
                parsed["incident_date"] = self._parse_date(date_str)
                if not parsed["incident_date"]:
                    # Skip records without valid dates
                    return None

            # Parse incident type from threat field
            threat = raw_record.get("threat", "").strip().lower()
            parsed["incident_type"] = self.THREAT_TYPE_MAPPINGS.get(
                threat, IncidentType.OTHER
            )

            # Title from name field
            name = raw_record.get("name", "").strip()
            if name:
                parsed["title"] = name[:500]  # Max length constraint

            # Description
            description = raw_record.get("description", "").strip()
            if description:
                # Combine name and description
                if name:
                    parsed["description"] = f"{name}\n\n{description}"
                else:
                    parsed["description"] = description

            # Parse estimated damage from max_ptl_release_gallons
            max_release = raw_record.get("max_ptl_release_gallons", "").strip()
            if max_release and max_release not in ("", "0", "None"):
                try:
                    gallons = float(max_release)
                    # Estimate cost based on gallons (rough estimate: $100-500 per gallon for cleanup)
                    # Using conservative $200/gallon average
                    estimated_cost = gallons * 200
                    parsed["estimated_damage_usd"] = Decimal(str(estimated_cost))
                except (ValueError, TypeError):
                    pass

            # Location information
            location_name = raw_record.get("location", "").strip()
            lat_str = raw_record.get("lat", "").strip()
            lon_str = raw_record.get("lon", "").strip()

            if lat_str or lon_str or location_name:
                location_data = {}

                # Parse coordinates
                if lat_str and lon_str:
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                        # Validate coordinates
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            location_data["latitude"] = lat
                            location_data["longitude"] = lon
                    except (ValueError, TypeError):
                        pass

                # Location name
                if location_name:
                    location_data["location_name"] = location_name[:500]

                if location_data:
                    parsed["location"] = location_data

            # Store additional metadata
            metadata = {}

            # Commodity/substance
            commodity = raw_record.get("commodity", "").strip()
            if commodity:
                metadata["commodity"] = commodity

            # Tags
            tags = raw_record.get("tags", "").strip()
            if tags:
                metadata["tags"] = tags

            # Response measures
            if raw_record.get("measure_skim", "").strip() == "1":
                metadata["response_measures"] = metadata.get("response_measures", [])
                metadata["response_measures"].append("skimming")
            if raw_record.get("measure_shore", "").strip() == "1":
                metadata["response_measures"] = metadata.get("response_measures", [])
                metadata["response_measures"].append("shoreline_cleanup")
            if raw_record.get("measure_bio", "").strip() == "1":
                metadata["response_measures"] = metadata.get("response_measures", [])
                metadata["response_measures"].append("bioremediation")
            if raw_record.get("measure_disperse", "").strip() == "1":
                metadata["response_measures"] = metadata.get("response_measures", [])
                metadata["response_measures"].append("dispersants")
            if raw_record.get("measure_burn", "").strip() == "1":
                metadata["response_measures"] = metadata.get("response_measures", [])
                metadata["response_measures"].append("in_situ_burning")

            # Number of posts/updates
            posts = raw_record.get("posts", "").strip()
            if posts:
                try:
                    metadata["num_updates"] = int(posts)
                except (ValueError, TypeError):
                    pass

            # Maximum potential release
            if max_release and max_release not in ("", "0", "None"):
                try:
                    metadata["max_potential_release_gallons"] = float(max_release)
                except (ValueError, TypeError):
                    pass

            if metadata:
                parsed["metadata_json"] = metadata

            # No vessel data in NOAA (vessel_id = None)
            # No casualties reported in this dataset (fatalities = 0, injuries = 0)
            parsed["fatalities"] = 0
            parsed["injuries"] = 0
            parsed["missing_persons"] = 0

            return parsed

        except Exception as e:
            print(f"Error parsing NOAA record {raw_record.get('id')}: {e}")
            return None

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
            print(
                f"Error creating model for {parsed_record.get('source_incident_id')}: {e}"
            )
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
        except:
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
                existing = (
                    self.session.query(Location)
                    .filter(
                        Location.latitude.between(
                            Decimal(str(lat - 0.001)), Decimal(str(lat + 0.001))
                        ),
                        Location.longitude.between(
                            Decimal(str(lon - 0.001)), Decimal(str(lon + 0.001))
                        ),
                    )
                    .first()
                )

                if existing:
                    self._location_cache[cache_key] = existing.location_id
                    return existing.location_id

                # Create new location with coordinates
                location = Location(
                    location_name=location_data.get(
                        "location_name", f"Location {lat:.4f}, {lon:.4f}"
                    ),
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
                cache_key = f"noaa_{location_data['latitude']:.4f}_{location_data['longitude']:.4f}"
            else:
                cache_key = f"noaa_{location_data.get('location_name')}"

            self._location_cache[cache_key] = location.location_id
            return location.location_id

        except Exception as e:
            print(f"Error creating location: {e}")
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
