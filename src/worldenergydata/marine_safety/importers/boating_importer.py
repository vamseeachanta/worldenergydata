"""
Boating Accident Report Database (BARD) Importer

Imports recreational boating accident data from the Data Liberation Project's
converted CSV files (1995-2012 USCG BARD data).

Schema:
    - Accidents.csv: Main accident records
    - Vessels.csv: Vessel information (linked by BARDID + VesselID)
    - Deaths.csv: Fatality details (linked by BARDID)
    - Injuries.csv: Injury details (linked by BARDID + VesselID)
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


class BoatingImporter(BaseImporter):
    """Import USCG Boating Accident Report Database (BARD) data."""

    # Field mappings from BARD CSV to our schema
    FIELD_MAPPINGS = {
        "BARDID": "source_incident_id",
        "Year": "incident_year",
        "Date": "incident_date",
        "Time": "incident_time",
        "NameofBodyofWater": "body_of_water",
        "NearestCityorTown": "nearest_city",
        "County": "county",
        "State": "state_code",
        "AccidentEvent1": "accident_event_primary",
        "AccidentEvent2": "accident_event_secondary",
        "AccidentCause1": "accident_cause_primary",
        "AccidentCause2": "accident_cause_secondary",
        "Numberdeaths": "fatalities",
        "Numberinjured": "injuries",
        "NumberDisappeared": "missing",
        "Totaldamage": "estimated_damage_usd",
        "AlcoholInvolved": "alcohol_involved",
        "Redactednarrative": "incident_description",
    }

    # Map BARD accident events to our IncidentType enum
    INCIDENT_TYPE_MAPPINGS = {
        "collision with vessel": "collision",
        "collision with fixed object": "collision",
        "collision with floating object": "collision",
        "grounding": "grounding",
        "capsizing": "capsizing",
        "fire": "fire",
        "explosion": "explosion",
        "flooding": "flooding",
        "sinking": "flooding",
        "falls overboard": "personnel_injury",
        "falls in boat": "personnel_injury",
        "struck by boat": "collision",
        "struck by propeller": "collision",
        "skier mishap": "other",
        "other": "other",
    }

    # Map BARD vessel types to our VesselType enum
    VESSEL_TYPE_MAPPINGS = {
        "personal watercraft": "other",
        "cabin motorboat": "other",
        "open motorboat": "other",
        "auxiliary sail": "other",
        "sail only": "other",
        "pontoon boat": "other",
        "canoe": "other",
        "kayak": "other",
        "rowboat": "other",
        "houseboat": "passenger",
        "inflatable boat": "other",
        "other": "other",
    }

    def __init__(
        self,
        accidents_file: Path,
        vessels_file: Optional[Path] = None,
        deaths_file: Optional[Path] = None,
        injuries_file: Optional[Path] = None,
        session: Any = None,
        batch_size: int = 100,
    ):
        """
        Initialize boating data importer.

        Args:
            accidents_file: Path to Accidents.csv
            vessels_file: Path to Vessels.csv (optional)
            deaths_file: Path to Deaths.csv (optional)
            injuries_file: Path to Injuries.csv (optional)
            session: SQLAlchemy session
            batch_size: Records per batch
        """
        super().__init__(accidents_file, session, batch_size)
        self.vessels_file = vessels_file
        self.deaths_file = deaths_file
        self.injuries_file = injuries_file

        # Caches for related data
        self.vessels_by_bardid: Dict[str, list] = {}
        self.deaths_by_bardid: Dict[str, list] = {}
        self.injuries_by_bardid: Dict[str, int] = {}

        # Initialize caches for locations and vessels
        self._location_cache: Dict[str, int] = {}
        self._vessel_cache: Dict[str, int] = {}

    def _load_related_data(self):
        """Pre-load vessels, deaths, and injuries data into memory."""
        # Load vessels
        if self.vessels_file and self.vessels_file.exists():
            logger.info(f"Loading vessels data from {self.vessels_file}...")
            with open(self.vessels_file, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bardid = row.get("BARDID", "").strip()
                    if bardid:
                        if bardid not in self.vessels_by_bardid:
                            self.vessels_by_bardid[bardid] = []
                        self.vessels_by_bardid[bardid].append(row)
            logger.info(
                f"Loaded {len(self.vessels_by_bardid)} unique BARD incidents with vessel data"
            )

        # Load deaths
        if self.deaths_file and self.deaths_file.exists():
            logger.info(f"Loading deaths data from {self.deaths_file}...")
            with open(self.deaths_file, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bardid = row.get("BARDID", "").strip()
                    if bardid:
                        if bardid not in self.deaths_by_bardid:
                            self.deaths_by_bardid[bardid] = []
                        self.deaths_by_bardid[bardid].append(row)
            logger.info(
                f"Loaded {sum(len(v) for v in self.deaths_by_bardid.values())} death records"
            )

        # Load injuries - count per BARDID
        if self.injuries_file and self.injuries_file.exists():
            logger.info(f"Loading injuries data from {self.injuries_file}...")
            with open(self.injuries_file, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bardid = row.get("BARDID", "").strip()
                    if bardid:
                        self.injuries_by_bardid[bardid] = (
                            self.injuries_by_bardid.get(bardid, 0) + 1
                        )
            logger.info(
                f"Loaded {sum(self.injuries_by_bardid.values())} injury records"
            )

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """Read records from Accidents CSV file."""
        # Load related data first
        self._load_related_data()

        with open(self.source_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys (remove leading/trailing whitespace)
                normalized_row = {
                    k.strip() if k else k: v for k, v in row.items() if k is not None
                }
                yield normalized_row

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw BARD record into standardized format."""
        try:
            bardid = self._extract_incident_id(raw_record)
            if not bardid:
                return None

            parsed = self._build_base_record(bardid, raw_record)
            self._add_incident_date(parsed, raw_record)
            self._add_incident_type(parsed, raw_record)
            self._add_casualty_counts(parsed, bardid)
            self._add_damage_estimate(parsed)
            self._add_location_data(parsed, raw_record)
            self._add_vessel_info(parsed, bardid)

            return parsed

        except Exception as e:
            logger.error(f"Error parsing BARD record {raw_record.get('BARDID')}: {e}")
            return None

    def _extract_incident_id(self, raw_record: Dict[str, Any]) -> Optional[str]:
        """Extract and validate the BARD incident ID."""
        bardid = raw_record.get("BARDID", "").strip().strip('"')
        return bardid if bardid else None

    def _clean_field_value(self, value: str) -> str:
        """Clean a field value by stripping whitespace and quotes."""
        return value.strip().strip('"') if value else ""

    def _is_valid_field_value(self, value: str) -> bool:
        """Check if a field value is valid (not empty or placeholder)."""
        return bool(value) and value not in ("", "-1", "Unknown", "Unk")

    def _build_base_record(
        self, bardid: str, raw_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build base record with mapped fields."""
        parsed = {
            "source_agency": "USCG_BARD",
            "source_incident_id": bardid,
        }

        for bard_field, our_field in self.FIELD_MAPPINGS.items():
            if bard_field not in raw_record:
                continue
            value = self._clean_field_value(raw_record[bard_field])
            if self._is_valid_field_value(value):
                parsed[our_field] = value

        return parsed

    def _add_incident_date(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Parse and add incident date to record."""
        date_str = self._clean_field_value(raw_record.get("Date", ""))
        if date_str:
            parsed["incident_date"] = self._parse_date(date_str)

    def _add_incident_type(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Determine and add incident type from accident event."""
        event1 = self._clean_field_value(raw_record.get("AccidentEvent1", "")).lower()
        if event1:
            parsed["incident_type"] = self.INCIDENT_TYPE_MAPPINGS.get(event1, "other")

    def _parse_int_safely(self, value: Any, default: int = 0) -> int:
        """Safely parse an integer value."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _add_casualty_counts(self, parsed: Dict[str, Any], bardid: str) -> None:
        """Add fatalities, injuries, and missing counts."""
        # Fatalities: prefer Deaths.csv data
        if bardid in self.deaths_by_bardid:
            parsed["fatalities"] = len(self.deaths_by_bardid[bardid])
        elif "fatalities" in parsed:
            parsed["fatalities"] = self._parse_int_safely(parsed["fatalities"])

        # Injuries: prefer Injuries.csv data
        if bardid in self.injuries_by_bardid:
            parsed["injuries"] = self.injuries_by_bardid[bardid]
        elif "injuries" in parsed:
            parsed["injuries"] = self._parse_int_safely(parsed["injuries"])

        # Missing persons
        if "missing" in parsed:
            parsed["missing"] = self._parse_int_safely(parsed["missing"])

    def _add_damage_estimate(self, parsed: Dict[str, Any]) -> None:
        """Parse and add damage estimate."""
        if "estimated_damage_usd" not in parsed:
            return

        try:
            damage_str = (
                parsed["estimated_damage_usd"].replace(",", "").replace("$", "")
            )
            parsed["estimated_damage_usd"] = float(damage_str)
        except (ValueError, TypeError, AttributeError):
            parsed["estimated_damage_usd"] = None

    def _add_location_data(
        self, parsed: Dict[str, Any], raw_record: Dict[str, Any]
    ) -> None:
        """Extract and add location information."""
        state = self._clean_field_value(raw_record.get("State", ""))
        if not state:
            return

        parsed["location"] = {
            "state_code": state,
            "city": self._clean_field_value(raw_record.get("NearestCityorTown", "")),
            "county": self._clean_field_value(raw_record.get("County", "")),
            "body_of_water": self._clean_field_value(
                raw_record.get("NameofBodyofWater", "")
            ),
        }

    def _add_vessel_info(self, parsed: Dict[str, Any], bardid: str) -> None:
        """Add vessel information from related data."""
        if bardid not in self.vessels_by_bardid:
            return

        vessels = self.vessels_by_bardid[bardid]
        if not vessels:
            return

        vessel_data = vessels[0]
        parsed["vessel"] = self._build_vessel_record(vessel_data)

    def _build_vessel_record(self, vessel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build vessel record from raw vessel data."""
        return {
            "vessel_name": self._clean_field_value(vessel_data.get("VesselName", "")),
            "vessel_type": self._map_vessel_type(
                self._clean_field_value(vessel_data.get("Vesseltype", ""))
            ),
            "length_meters": self._parse_length(
                self._clean_field_value(vessel_data.get("Length", ""))
            ),
            "year_built": self._parse_year(
                self._clean_field_value(vessel_data.get("Yearbuilt", ""))
            ),
            "registration_number": self._clean_field_value(
                vessel_data.get("RegistrationNumber", "")
            ),
        }

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
                location_id = self._get_or_create_location_from_state(
                    parsed_record["location"]
                )

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
                estimated_damage_usd=parsed_record.get("estimated_damage_usd"),
                description=parsed_record.get("incident_description"),
                location_id=location_id,
                vessel_id=vessel_id,
            )

            return incident

        except Exception as e:
            logger.info(
                f"Error creating model for {parsed_record.get('source_incident_id')}: {e}"
            )
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse BARD date format (MM/DD/YY HH:MM:SS)."""
        if not date_str:
            return None

        try:
            # Remove time portion if present
            date_part = date_str.split(" ")[0]
            # Try MM/DD/YY format
            return datetime.strptime(date_part, "%m/%d/%y")
        except:
            try:
                # Try MM/DD/YYYY format
                return datetime.strptime(date_part, "%m/%d/%Y")
            except:
                return None

    def _parse_length(self, length_str: str) -> Optional[float]:
        """Parse vessel length (in feet) and convert to meters."""
        if not length_str or length_str in ("-1", "Unknown"):
            return None

        try:
            feet = float(length_str)
            return round(feet * 0.3048, 2)  # Convert feet to meters
        except:
            return None

    def _parse_year(self, year_str: str) -> Optional[int]:
        """Parse year built."""
        if not year_str or year_str in ("-1", "Unknown"):
            return None

        try:
            year = int(year_str)
            # Handle 2-digit years
            if year < 100:
                year += 1900 if year > 50 else 2000
            return year if 1900 <= year <= 2030 else None
        except:
            return None

    def _map_vessel_type(self, vessel_type_str: str) -> str:
        """Map BARD vessel type to our VesselType enum."""
        if not vessel_type_str:
            return "other"

        vessel_type_lower = vessel_type_str.lower()
        return self.VESSEL_TYPE_MAPPINGS.get(vessel_type_lower, "other")

    def _get_or_create_location_from_state(
        self, location_data: Dict[str, Any]
    ) -> Optional[int]:
        """Create location from state/city/county information."""
        try:
            # Create a basic location entry
            # Note: We don't have GPS coordinates for most boating accidents
            description_parts = []
            if location_data.get("body_of_water"):
                description_parts.append(location_data["body_of_water"])
            if location_data.get("city"):
                description_parts.append(location_data["city"])
            if location_data.get("county"):
                description_parts.append(f"{location_data['county']} County")
            if location_data.get("state_code"):
                description_parts.append(location_data["state_code"])

            description = ", ".join(filter(None, description_parts))
            if not description:
                return None

            # Check cache
            cache_key = f"boating_{description}"
            if cache_key in self._location_cache:
                return self._location_cache[cache_key]

            # Check database
            existing = (
                self.session.query(Location)
                .filter(Location.location_name == description)
                .first()
            )

            if existing:
                self._location_cache[cache_key] = existing.location_id
                return existing.location_id

            # Create new location
            location = Location(
                location_name=description,
                country_code="US",
                region_code=location_data.get("state_code"),
            )
            self.session.add(location)
            self.session.flush()

            self._location_cache[cache_key] = location.location_id
            return location.location_id

        except Exception as e:
            logger.error(f"Error creating location: {e}")
            return None

    def _get_or_create_vessel(self, vessel_data: Dict[str, Any]) -> Optional[int]:
        """Create vessel from BARD vessel data."""
        try:
            # Use registration number as unique identifier
            reg_number = vessel_data.get("registration_number", "").strip()
            if not reg_number or reg_number == "":
                return None

            # Check cache
            cache_key = f"vessel_{reg_number}"
            if cache_key in self._vessel_cache:
                return self._vessel_cache[cache_key]

            # Check database - use metadata_json for registration number
            # For now, skip duplicate checking on boating vessels since we don't have
            # a unique field like IMO number. Will rely on incident-level duplicate detection.
            existing = None

            if existing:
                self._vessel_cache[cache_key] = existing.vessel_id
                return existing.vessel_id

            # Create new vessel
            metadata = {"registration_number": reg_number}
            if vessel_data.get("length_meters"):
                metadata["length_meters"] = vessel_data["length_meters"]

            vessel = Vessel(
                vessel_name=vessel_data.get("vessel_name") or "Unknown",
                vessel_type=VesselType[vessel_data.get("vessel_type", "other").upper()],
                year_built=vessel_data.get("year_built"),
                flag_state="US",  # All BARD data is US vessels
                metadata_json=metadata,
            )
            self.session.add(vessel)
            self.session.flush()

            self._vessel_cache[cache_key] = vessel.vessel_id
            return vessel.vessel_id

        except Exception as e:
            logger.error(f"Error creating vessel: {e}")
            return None
