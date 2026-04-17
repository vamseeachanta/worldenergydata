"""
UK Marine Accident Investigation Branch (MAIB) Importer

Imports marine incidents from MAIB database including:
- maib_occurrences.csv: Main incident records (5,877 records)
- maib_vessels.csv: Vessel information (linked by Occurrence_Id)
- maib_affected_persons.csv: Affected person records (linked by Occurrence_Id)
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from worldenergydata.common.logging import get_logger

from ..constants import IncidentType, VesselType
from ..database.models import Incident, Location, Vessel
from .base_importer import BaseImporter

logger = get_logger(__name__)


class MAIBImporter(BaseImporter):
    """Import UK MAIB marine occurrence data."""

    # Map MAIB severity to incident types (heuristic)
    SEVERITY_TYPE_MAPPINGS = {
        "very serious marine casualty": "collision",
        "serious marine casualty": "collision",
        "marine casualty": "other",
        "marine incident": "other",
        "less serious": "other",
    }

    # Map MAIB main event types to our IncidentType enum
    EVENT_TYPE_MAPPINGS = {
        "collision": "collision",
        "contact": "collision",
        "grounding": "grounding",
        "foundering": "flooding",
        "flooding": "flooding",
        "fire": "fire",
        "explosion": "explosion",
        "capsizing": "capsizing",
        "listing": "other",
        "damage": "other",
        "equipment": "other",
        "machinery": "other",
        "accident to person": "personnel_injury",
        "person overboard": "personnel_injury",
        "injury": "personnel_injury",
        "death": "personnel_injury",
    }

    # Map MAIB vessel types to our VesselType enum
    VESSEL_TYPE_MAPPINGS = {
        "fishing": "fishing",
        "cargo": "cargo",
        "tanker": "tanker",
        "chemical tanker": "tanker",
        "oil tanker": "tanker",
        "gas carrier": "tanker",
        "passenger": "passenger",
        "cruise": "passenger",
        "ferry": "passenger",
        "tugboat": "tugboat",
        "tug": "tugboat",
        "recreational": "other",
        "yacht": "other",
        "merchant": "cargo",
        "bulk carrier": "cargo",
    }

    def __init__(
        self,
        occurrences_file: Path,
        vessels_file: Optional[Path] = None,
        persons_file: Optional[Path] = None,
        session: Any = None,
        batch_size: int = 1000,
    ):
        """
        Initialize MAIB importer.

        Args:
            occurrences_file: Path to maib_occurrences.csv
            vessels_file: Path to maib_vessels.csv (optional)
            persons_file: Path to maib_affected_persons.csv (optional)
            session: SQLAlchemy session
            batch_size: Records per batch
        """
        super().__init__(occurrences_file, session, batch_size)
        self.vessels_file = vessels_file
        self.persons_file = persons_file

        # Caches for related data
        self.vessels_by_occid: Dict[str, list] = {}
        self.persons_by_occid: Dict[str, list] = {}

        # Caches for locations and vessels
        self._location_cache: Dict[str, int] = {}
        self._vessel_cache: Dict[str, int] = {}

    def _load_related_data(self):
        """Pre-load vessels and affected persons data into memory."""
        # Load vessels
        if self.vessels_file and self.vessels_file.exists():
            logger.info(f"Loading vessels data from {self.vessels_file}...")
            count = 0
            with open(self.vessels_file, "r", encoding="utf-8", errors="replace") as f:
                # MAIB files use semicolon delimiter
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    occid = row.get("Occurrence_Id", "").strip()
                    if occid:
                        if occid not in self.vessels_by_occid:
                            self.vessels_by_occid[occid] = []
                        self.vessels_by_occid[occid].append(row)
                        count += 1
            logger.info(
                f"Loaded {count} vessel records for {len(self.vessels_by_occid)} unique occurrences"
            )

        # Load affected persons
        if self.persons_file and self.persons_file.exists():
            logger.info(f"Loading affected persons data from {self.persons_file}...")
            count = 0
            with open(self.persons_file, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    occid = row.get("Occurrence_Id", "").strip()
                    if occid:
                        if occid not in self.persons_by_occid:
                            self.persons_by_occid[occid] = []
                        self.persons_by_occid[occid].append(row)
                        count += 1
            logger.info(
                f"Loaded {count} affected person records for {len(self.persons_by_occid)} unique occurrences"
            )

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """Read records from occurrences CSV file."""
        # Load related data first
        self._load_related_data()

        with open(self.source_path, "r", encoding="utf-8", errors="replace") as f:
            # MAIB files use semicolon delimiter
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                # Normalize keys
                normalized_row = {
                    k.strip() if k else k: v for k, v in row.items() if k is not None
                }
                yield normalized_row

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw MAIB record into standardized format."""
        try:
            occid = self._extract_incident_id(raw_record)
            if not occid:
                return None

            parsed = self._build_base_record(occid)
            self._add_incident_date(parsed, raw_record)
            parsed["incident_type"] = self._determine_incident_type(raw_record)
            self._add_casualty_counts(parsed, occid)
            self._add_description(parsed, raw_record)
            self._add_location_data(parsed, raw_record)
            self._add_vessel_info(parsed, occid)
            self._add_environmental_metadata(parsed, raw_record)

            return parsed

        except Exception as e:
            logger.error(
                f"Error parsing MAIB record {raw_record.get('Occurrence_Id')}: {e}"
            )
            return None

    def _extract_incident_id(self, raw_record: Dict[str, Any]) -> Optional[str]:
        """Extract and validate incident ID from raw record."""
        occid = raw_record.get("Occurrence_Id", "").strip()
        return occid if occid else None

    def _build_base_record(self, occid: str) -> Dict[str, Any]:
        """Build base parsed record with source info."""
        return {
            "source_agency": "MAIB_UK",
            "source_incident_id": occid,
        }

    def _add_incident_date(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Parse and add incident date to parsed record."""
        date_str = raw_record.get("Local_Date_Main_Event", "").strip()
        if date_str:
            parsed["incident_date"] = self._parse_date(date_str)

    def _determine_incident_type(self, raw_record: Dict[str, Any]) -> str:
        """Map severity and event types to incident type."""
        event_fields = [
            raw_record.get("Main_Event_L3", "").strip().lower(),
            raw_record.get("Main_Event_L2", "").strip().lower(),
            raw_record.get("Main_Event_L1", "").strip().lower(),
            raw_record.get("Occurrence_Severity", "").strip().lower(),
        ]

        for event_str in event_fields:
            if not event_str:
                continue
            matched_type = self._match_event_type(event_str)
            if matched_type != "other":
                return matched_type

        return "other"

    def _match_event_type(self, event_str: str) -> str:
        """Match event string against EVENT_TYPE_MAPPINGS."""
        for key_word, mapped_type in self.EVENT_TYPE_MAPPINGS.items():
            if key_word in event_str:
                return mapped_type
        return "other"

    def _add_casualty_counts(self, parsed: Dict[str, Any], occid: str) -> None:
        """Count and add casualties from affected persons data."""
        fatalities, injuries = self._count_casualties(occid)
        parsed["fatalities"] = fatalities
        parsed["injuries"] = injuries
        parsed["missing"] = 0  # Not explicitly tracked in MAIB data

    def _count_casualties(self, occid: str) -> tuple:
        """Count fatalities and injuries for an occurrence."""
        if occid not in self.persons_by_occid:
            return 0, 0

        fatalities = 0
        injuries = 0
        for person in self.persons_by_occid[occid]:
            injury_type = person.get("Injury_Type", "").strip().lower()
            if "fatal" in injury_type or "death" in injury_type:
                fatalities += 1
            elif "injury" in injury_type or "injured" in injury_type:
                injuries += 1

        return fatalities, injuries

    def _add_description(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Extract and add description to parsed record."""
        short_desc = raw_record.get("Short_Description", "").strip()
        full_desc = raw_record.get("Description", "").strip()
        parsed["description"] = full_desc if full_desc else short_desc

    def _add_location_data(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Extract and add location information to parsed record."""
        location_data = self._extract_location_fields(raw_record)
        if self._has_location_data(location_data):
            parsed["location"] = location_data

    def _extract_location_fields(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all location-related fields from raw record."""
        return {
            "location_description": raw_record.get("Occurrence_Location", "").strip(),
            "coastal_state": raw_record.get("Coastal_State_Affected", "").strip(),
            "national_location_l1": raw_record.get("National_Location_L1", "").strip(),
            "national_location_l2": raw_record.get("National_Location_L2", "").strip(),
            "port_l1": raw_record.get("Port_Of_Accident_L1", "").strip(),
            "port_l2": raw_record.get("Port_Of_Accident_L2", "").strip(),
            "latitude": self._parse_float(raw_record.get("Latitude", "")),
            "longitude": self._parse_float(raw_record.get("Longitude", "")),
        }

    def _has_location_data(self, location_data: Dict[str, Any]) -> bool:
        """Check if location data contains meaningful information."""
        return bool(
            location_data.get("location_description")
            or location_data.get("coastal_state")
            or location_data.get("latitude")
            or location_data.get("longitude")
        )

    def _add_vessel_info(self, parsed: Dict[str, Any], occid: str) -> None:
        """Extract and add vessel information from linked vessels data."""
        vessels = self.vessels_by_occid.get(occid)
        if not vessels:
            return

        vessel_data = vessels[0]  # Use first vessel (primary vessel in incident)
        parsed["vessel"] = self._build_vessel_record(vessel_data)

    def _build_vessel_record(self, vessel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build vessel record from raw vessel data."""
        return {
            "flag_state": vessel_data.get("Flag_State", "").strip(),
            "vessel_category_l1": vessel_data.get("Vessel_Category_L1", "").strip(),
            "vessel_category_l2": vessel_data.get("Vessel_Category_L2", "").strip(),
            "ship_type_l1": vessel_data.get("Ship_Craft_Type_L1", "").strip(),
            "ship_type_l2": vessel_data.get("Ship_Craft_Type_L2", "").strip(),
            "ship_type_l3": vessel_data.get("Ship_Craft_Type_L3", "").strip(),
            "length_meters": self._parse_float(
                vessel_data.get("LOA_Length_Overall_in_Metres", "")
            ),
            "gross_tonnage": self._parse_float(vessel_data.get("GT_Gross_Tonnage", "")),
            "year_built": self._parse_int(vessel_data.get("Year_Built", "")),
            "hull_material": vessel_data.get("Hull_Material", "").strip(),
            "is_commercial": vessel_data.get("Is_Commercial_Vessel", "").strip().lower()
            == "true",
            "crew_voyage": self._parse_int(vessel_data.get("Crew_Voyage", "0")),
            "deaths_crew": self._parse_int(vessel_data.get("Deaths_Crew", "0")),
            "deaths_passenger": self._parse_int(
                vessel_data.get("Deaths_Passenger", "0")
            ),
            "deaths_other": self._parse_int(vessel_data.get("Deaths_Other", "0")),
            "injuries_crew": self._parse_int(vessel_data.get("Injuries_Crew", "0")),
            "injuries_passenger": self._parse_int(
                vessel_data.get("Injuries_Passenger", "0")
            ),
            "injuries_other": self._parse_int(vessel_data.get("Injuries_Other", "0")),
        }

    def _add_environmental_metadata(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Extract and add environmental conditions metadata."""
        metadata = self._extract_environmental_fields(raw_record)
        if metadata:
            parsed["metadata"] = metadata

    def _extract_environmental_fields(
        self, raw_record: Dict[str, Any]
    ) -> Dict[str, str]:
        """Extract environmental condition fields from raw record."""
        field_mappings = {
            "Natural_Light": "natural_light",
            "Sea_State": "sea_state",
            "Visibility": "visibility",
            "Weather": "weather",
            "Wind_Force": "wind_force",
            "SAR_Intervention": "sar_intervention",
        }

        metadata = {}
        for raw_key, meta_key in field_mappings.items():
            value = raw_record.get(raw_key, "").strip()
            if value:
                metadata[meta_key] = value

        return metadata

    def map_to_model(self, parsed_record: Dict[str, Any]) -> Optional[Incident]:
        """Map parsed record to Incident model."""
        try:
            # Check for duplicate
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
                return None

            # Create location
            location_id = None
            if "location" in parsed_record:
                location_id = self._get_or_create_location(parsed_record["location"])

            # Create vessel
            vessel_id = None
            if "vessel" in parsed_record:
                vessel_id = self._get_or_create_vessel(parsed_record["vessel"])

            # Create incident
            incident = Incident(
                source_agency=parsed_record.get("source_agency"),
                source_incident_id=parsed_record.get("source_incident_id"),
                incident_date=parsed_record.get("incident_date"),
                incident_type=IncidentType[
                    parsed_record.get("incident_type", "other").upper()
                ],
                fatalities=parsed_record.get("fatalities", 0),
                injuries=parsed_record.get("injuries", 0),
                missing_persons=parsed_record.get("missing", 0),
                description=parsed_record.get("description"),
                location_id=location_id,
                vessel_id=vessel_id,
                metadata_json=parsed_record.get("metadata"),
            )

            return incident

        except Exception as e:
            logger.info(
                f"Error creating model for {parsed_record.get('source_incident_id')}: {e}"
            )
            import traceback

            traceback.print_exc()
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse MAIB date format (YYYY-MM-DD)."""
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return None

    def _parse_int(self, value: str) -> int:
        """Parse integer value."""
        if not value or value.strip() == "" or value.strip().lower() == "na":
            return 0
        try:
            return int(float(value))
        except:
            return 0

    def _parse_float(self, value: str) -> Optional[float]:
        """Parse float value."""
        if not value or value.strip() == "" or value.strip().lower() == "na":
            return None
        try:
            return float(value)
        except:
            return None

    def _map_vessel_type(self, ship_type_l1: str, ship_type_l2: str) -> str:
        """Map MAIB vessel type to our VesselType enum."""
        # Try both levels
        combined = f"{ship_type_l1} {ship_type_l2}".lower()

        for key, value in self.VESSEL_TYPE_MAPPINGS.items():
            if key in combined:
                return value
        return "other"

    def _get_or_create_location(self, location_data: Dict[str, Any]) -> Optional[int]:
        """Create location from MAIB location data."""
        try:
            # Build location name
            parts = []
            if location_data.get("port_l2"):
                parts.append(location_data["port_l2"])
            if location_data.get("port_l1"):
                parts.append(location_data["port_l1"])
            if location_data.get("national_location_l2"):
                parts.append(location_data["national_location_l2"])
            if location_data.get("national_location_l1"):
                parts.append(location_data["national_location_l1"])
            if location_data.get("coastal_state"):
                parts.append(location_data["coastal_state"])
            if location_data.get("location_description"):
                parts.append(location_data["location_description"])

            location_name = ", ".join(filter(None, parts)) or "Unknown UK Waters"

            # Check cache
            cache_key = f"maib_{location_name}"
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
            # Map coastal state to country code
            coastal_state = location_data.get("coastal_state", "").upper()
            if "UNITED KINGDOM" in coastal_state or coastal_state == "UK":
                country_code = "GB"
            else:
                country_code = None

            location = Location(
                location_name=location_name,
                country_code=country_code or "GB",  # Default to GB for MAIB data
                latitude=location_data.get("latitude"),
                longitude=location_data.get("longitude"),
            )
            self.session.add(location)
            self.session.flush()

            self._location_cache[cache_key] = location.location_id
            return location.location_id

        except Exception as e:
            logger.error(f"Error creating location: {e}")
            return None

    def _get_or_create_vessel(self, vessel_data: Dict[str, Any]) -> Optional[int]:
        """Create vessel from MAIB vessel data."""
        try:
            # MAIB doesn't include IMO or official numbers in the provided data
            # Use a composite key for caching
            cache_key = f"maib_{vessel_data.get('flag_state', '')}_{vessel_data.get('ship_type_l1', '')}_{vessel_data.get('gross_tonnage', '')}"

            # Check cache
            if cache_key in self._vessel_cache:
                return self._vessel_cache[cache_key]

            # Since we don't have unique identifiers, we'll create vessels each time
            # This is acceptable for MAIB as they focus on incident details

            # Create new vessel
            metadata = {}
            for key in [
                "vessel_category_l1",
                "vessel_category_l2",
                "ship_type_l1",
                "ship_type_l2",
                "ship_type_l3",
                "hull_material",
                "is_commercial",
                "crew_voyage",
                "deaths_crew",
                "deaths_passenger",
                "deaths_other",
                "injuries_crew",
                "injuries_passenger",
                "injuries_other",
                "gross_tonnage",
            ]:
                if vessel_data.get(key):
                    metadata[key] = vessel_data[key]

            # Store length_meters in metadata
            if vessel_data.get("length_meters"):
                metadata["length_meters"] = vessel_data["length_meters"]

            # Determine vessel type from ship types
            vessel_type = self._map_vessel_type(
                vessel_data.get("ship_type_l1", ""), vessel_data.get("ship_type_l2", "")
            )

            # Map flag state to country code
            flag_state = vessel_data.get("flag_state", "").upper()
            if "UNITED KINGDOM" in flag_state or flag_state == "UK":
                flag_code = "GB"
            elif "NORWAY" in flag_state:
                flag_code = "NO"
            elif "GERMANY" in flag_state:
                flag_code = "DE"
            elif "NETHERLANDS" in flag_state:
                flag_code = "NL"
            else:
                flag_code = None

            vessel = Vessel(
                vessel_name="Unknown",  # MAIB data doesn't include vessel names
                vessel_type=VesselType[vessel_type.upper()],
                year_built=vessel_data.get("year_built"),
                flag_state=flag_code,
                metadata_json=metadata,
            )
            self.session.add(vessel)
            self.session.flush()

            self._vessel_cache[cache_key] = vessel.vessel_id
            return vessel.vessel_id

        except Exception as e:
            logger.error(f"Error creating vessel: {e}")
            return None
