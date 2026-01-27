"""
Canadian Transportation Safety Board (TSB) Marine Occurrence Importer

Imports marine incidents from TSB database including:
- occurrence.csv: Main incident records (86,289 records)
- vessel.csv: Vessel information (linked by OccNo)
- injuries.csv: Injury details (linked by OccNo)
- equipment data: Navigation, lifesaving, recording equipment
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from ..constants import IncidentType, VesselType
from ..database.models import Incident, Location, Vessel
from .base_importer import BaseImporter


class TSBImporter(BaseImporter):
    """Import Canadian TSB marine occurrence data."""

    # Map TSB occurrence types to our IncidentType enum
    INCIDENT_TYPE_MAPPINGS = {
        "accident": "collision",
        "incident": "other",
        "serious incident": "fire",
        "grounding": "grounding",
        "collision": "collision",
        "capsizing": "capsizing",
        "fire": "fire",
        "explosion": "explosion",
        "flooding": "flooding",
        "sinking": "flooding",
    }

    # Map TSB vessel types to our VesselType enum
    VESSEL_TYPE_MAPPINGS = {
        "fishing": "fishing",
        "cargo": "cargo",
        "tanker": "tanker",
        "passenger": "passenger",
        "tug": "tugboat",
        "tugboat": "tugboat",
        "recreational": "other",
        "other": "other",
    }

    def __init__(
        self,
        occurrence_file: Path,
        vessels_file: Optional[Path] = None,
        injuries_file: Optional[Path] = None,
        equipment_files: Optional[Dict[str, Path]] = None,
        session: Any = None,
        batch_size: int = 1000,
    ):
        """
        Initialize TSB importer.

        Args:
            occurrence_file: Path to occurrence.csv
            vessels_file: Path to vessel.csv (optional)
            injuries_file: Path to injuries.csv (optional)
            equipment_files: Dict of equipment file paths (optional)
            session: SQLAlchemy session
            batch_size: Records per batch
        """
        super().__init__(occurrence_file, session, batch_size)
        self.vessels_file = vessels_file
        self.injuries_file = injuries_file
        self.equipment_files = equipment_files or {}

        # Caches for related data
        self.vessels_by_occno: Dict[str, list] = {}
        self.injuries_by_occno: Dict[str, list] = {}
        self.equipment_by_occno: Dict[str, Dict[str, list]] = {}

        # Caches for locations and vessels
        self._location_cache: Dict[str, int] = {}
        self._vessel_cache: Dict[str, int] = {}

        # Track seen occurrence IDs to handle duplicates in source data
        self._seen_occnos: set = set()

    def _load_related_data(self):
        """Pre-load vessels, injuries, and equipment data into memory."""
        # Load vessels
        if self.vessels_file and self.vessels_file.exists():
            print(f"Loading vessels data from {self.vessels_file}...")
            count = 0
            with open(
                self.vessels_file, "r", encoding="utf-8-sig", errors="replace"
            ) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Strip BOM from keys (handles \ufeff)
                    cleaned_row = {
                        k.lstrip("\ufeff").strip(): v for k, v in row.items()
                    }
                    occno = cleaned_row.get("OccNo", "").strip()
                    if occno:
                        if occno not in self.vessels_by_occno:
                            self.vessels_by_occno[occno] = []
                        self.vessels_by_occno[occno].append(cleaned_row)
                        count += 1
            print(
                f"Loaded {count} vessel records for {len(self.vessels_by_occno)} unique occurrences"
            )

        # Load injuries
        if self.injuries_file and self.injuries_file.exists():
            print(f"Loading injuries data from {self.injuries_file}...")
            count = 0
            with open(
                self.injuries_file, "r", encoding="utf-8-sig", errors="replace"
            ) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Strip BOM from keys
                    cleaned_row = {
                        k.lstrip("\ufeff").strip(): v for k, v in row.items()
                    }
                    occno = cleaned_row.get("OccNo", "").strip()
                    if occno:
                        if occno not in self.injuries_by_occno:
                            self.injuries_by_occno[occno] = []
                        self.injuries_by_occno[occno].append(cleaned_row)
                        count += 1
            print(
                f"Loaded {count} injury records for {len(self.injuries_by_occno)} unique occurrences"
            )

        # Load equipment data (stored in metadata, not loaded upfront due to size)
        # Equipment files: navigation_equipment, lifesaving_equipment, recording_equipment
        print("Equipment files will be processed on-demand (large datasets)")

    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """Read records from occurrence CSV file."""
        # Load related data first
        self._load_related_data()

        with open(self.source_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys and strip BOM
                normalized_row = {
                    k.lstrip("\ufeff").strip() if k else k: v
                    for k, v in row.items()
                    if k is not None
                }
                yield normalized_row

    def _extract_incident_id(self, raw_record: Dict[str, Any]) -> Optional[str]:
        """Extract and validate incident ID, returning None for duplicates."""
        occno = raw_record.get("OccNo", "").strip()
        if not occno:
            return None
        if occno in self._seen_occnos:
            return None
        self._seen_occnos.add(occno)
        return occno

    def _determine_incident_type(self, raw_record: Dict[str, Any]) -> str:
        """Determine incident type from occurrence and accident type fields."""
        occ_type = raw_record.get("OccTypeDisplayEng", "").strip().lower()
        acc_type = raw_record.get("AccIncTypeDisplayEng", "").strip().lower()

        for key_word, mapped_type in self.INCIDENT_TYPE_MAPPINGS.items():
            if key_word in occ_type or key_word in acc_type:
                return mapped_type
        return "other"

    def _parse_casualties(self, raw_record: Dict[str, Any]) -> Dict[str, int]:
        """Parse casualty counts from raw record."""
        return {
            "fatalities": self._parse_int(raw_record.get("TotalDeaths", "0")),
            "injuries": (
                self._parse_int(raw_record.get("TotalMinorInjuries", "0"))
                + self._parse_int(raw_record.get("TotalSeriousInjuries", "0"))
            ),
            "missing": self._parse_int(raw_record.get("TotalMissingIndividuals", "0")),
        }

    def _build_location_data(
        self, raw_record: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Build location dictionary from raw record."""
        province = raw_record.get("ProvinceDisplayEng", "").strip()
        lat = self._parse_float(raw_record.get("Latitude", ""))
        lon = self._parse_float(raw_record.get("Longitude", ""))

        if not (province or lat or lon):
            return None

        return {
            "province": province,
            "latitude": lat,
            "longitude": lon,
            "region": raw_record.get("RegionOfOccurrenceDisplayEng", "").strip(),
            "area_type": raw_record.get("AreaTypeDisplayEng", "").strip(),
            "position_description": raw_record.get(
                "NearestLocationDescription", ""
            ).strip(),
            "position_distance_nm": self._parse_float(
                raw_record.get("NearestLocationDistance_Nm", "")
            ),
        }

    def _build_vessel_data(self, occno: str) -> Optional[Dict[str, Any]]:
        """Build vessel dictionary from cached vessel data."""
        vessels = self.vessels_by_occno.get(occno)
        if not vessels:
            return None

        vessel_data = vessels[0]  # Use primary vessel
        return {
            "vessel_name": vessel_data.get("VesselName", "").strip(),
            "vessel_type": self._map_vessel_type(
                vessel_data.get("VesselTypeDisplayEng", "").strip()
            ),
            "imo_number": vessel_data.get("IMO", "").strip(),
            "official_number": vessel_data.get("OfficialNo", "").strip(),
            "mmsi": vessel_data.get("MMSI", "").strip(),
            "call_sign": vessel_data.get("CallSign", "").strip(),
            "flag_state": vessel_data.get("VesselFlagDisplayEng", "").strip(),
            "length_meters": self._parse_float(vessel_data.get("Length_Meters", "")),
            "gross_tonnage": self._parse_float(vessel_data.get("GrossTonnage", "")),
            "year_built": self._parse_int(vessel_data.get("YearBuilt", "")),
            "crew_count": self._parse_int(vessel_data.get("NumberOfCrew", "0")),
            "passenger_count": self._parse_int(vessel_data.get("NumberOfPass", "0")),
            "total_people": self._parse_int(vessel_data.get("TotalPeopleOnBoard", "0")),
        }

    def _build_environmental_metadata(
        self, raw_record: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Build environmental conditions metadata."""
        field_mappings = {
            "WeatherConditionDisplayEng": "weather",
            "WindSpeed_Knots": "wind_speed_knots",
            "SeaStateDisplayEng": "sea_state",
            "VisibilityDistance_Nm": "visibility_nm",
            "LightConditionDisplayEng": "light_condition",
        }
        numeric_fields = {"WindSpeed_Knots", "VisibilityDistance_Nm"}

        metadata = {}
        for source_field, target_field in field_mappings.items():
            value = raw_record.get(source_field)
            if not value:
                continue
            if source_field in numeric_fields:
                metadata[target_field] = self._parse_float(value)
            else:
                metadata[target_field] = value.strip()

        return metadata if metadata else None

    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw TSB record into standardized format."""
        try:
            occno = self._extract_incident_id(raw_record)
            if not occno:
                return None

            parsed = {
                "source_agency": "TSB_CANADA",
                "source_incident_id": occno,
                "incident_type": self._determine_incident_type(raw_record),
            }

            # Parse date
            date_str = raw_record.get("OccDate", "").strip()
            if date_str:
                parsed["incident_date"] = self._parse_date(date_str)

            # Add casualties
            parsed.update(self._parse_casualties(raw_record))

            # Add description
            summary = raw_record.get("Summary", "").strip()
            if summary:
                parsed["description"] = summary

            # Add optional sections
            location = self._build_location_data(raw_record)
            if location:
                parsed["location"] = location

            vessel = self._build_vessel_data(occno)
            if vessel:
                parsed["vessel"] = vessel

            metadata = self._build_environmental_metadata(raw_record)
            if metadata:
                parsed["metadata"] = metadata

            return parsed

        except Exception as e:
            print(f"Error parsing TSB record {raw_record.get('OccNo')}: {e}")
            return None

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
            print(
                f"Error creating model for {parsed_record.get('source_incident_id')}: {e}"
            )
            import traceback

            traceback.print_exc()
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse TSB date format (YYYY-MM-DD HH:MM:SS.0000000)."""
        if not date_str:
            return None

        try:
            # Remove time portion and microseconds
            date_part = date_str.split(" ")[0]
            return datetime.strptime(date_part, "%Y-%m-%d")
        except:
            return None

    def _parse_int(self, value: str) -> int:
        """Parse integer value."""
        if not value or value.strip() == "":
            return 0
        try:
            return int(float(value))
        except:
            return 0

    def _parse_float(self, value: str) -> Optional[float]:
        """Parse float value."""
        if not value or value.strip() == "":
            return None
        try:
            return float(value)
        except:
            return None

    def _map_vessel_type(self, vessel_type_str: str) -> str:
        """Map TSB vessel type to our VesselType enum."""
        if not vessel_type_str:
            return "other"

        vessel_type_lower = vessel_type_str.lower()
        for key, value in self.VESSEL_TYPE_MAPPINGS.items():
            if key in vessel_type_lower:
                return value
        return "other"

    def _get_or_create_location(self, location_data: Dict[str, Any]) -> Optional[int]:
        """Create location from TSB location data."""
        try:
            # Build location name
            parts = []
            if location_data.get("position_description"):
                parts.append(location_data["position_description"])
            if location_data.get("area_type"):
                parts.append(location_data["area_type"])
            if location_data.get("province"):
                parts.append(location_data["province"])
            if location_data.get("region"):
                parts.append(location_data["region"])

            location_name = ", ".join(filter(None, parts)) or "Unknown Canadian Waters"

            # Check cache
            cache_key = f"tsb_{location_name}"
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
                country_code="CA",
                region_code=self._map_province_code(location_data.get("province", "")),
                latitude=location_data.get("latitude"),
                longitude=location_data.get("longitude"),
            )
            self.session.add(location)
            self.session.flush()

            self._location_cache[cache_key] = location.location_id
            return location.location_id

        except Exception as e:
            print(f"Error creating location: {e}")
            return None

    def _map_province_code(self, province: str) -> Optional[str]:
        """Extract province code from province string."""
        # Province strings are like "NOVA SCOTIA (NS)" or "BRITISH COLUMBIA (BC)"
        if "(" in province and ")" in province:
            code = province.split("(")[1].split(")")[0].strip()
            return code if len(code) == 2 else None
        return None

    def _get_or_create_vessel(self, vessel_data: Dict[str, Any]) -> Optional[int]:
        """Create vessel from TSB vessel data."""
        try:
            # Use IMO number as unique identifier
            imo = vessel_data.get("imo_number", "").strip()
            if not imo:
                # Try official number
                official_no = vessel_data.get("official_number", "").strip()
                if not official_no:
                    return None
                cache_key = f"tsb_official_{official_no}"
            else:
                cache_key = f"tsb_imo_{imo}"

            # Check cache
            if cache_key in self._vessel_cache:
                return self._vessel_cache[cache_key]

            # Check database by IMO or official number
            if imo:
                existing = (
                    self.session.query(Vessel).filter(Vessel.imo_number == imo).first()
                )
            else:
                existing = None

            if existing:
                self._vessel_cache[cache_key] = existing.vessel_id
                return existing.vessel_id

            # Create new vessel
            metadata = {}
            for key in [
                "official_number",
                "mmsi",
                "call_sign",
                "crew_count",
                "passenger_count",
                "total_people",
                "gross_tonnage",
            ]:
                if vessel_data.get(key):
                    metadata[key] = vessel_data[key]

            # Store length_meters in metadata
            if vessel_data.get("length_meters"):
                metadata["length_meters"] = vessel_data["length_meters"]

            # Map flag state to country code
            flag_state = vessel_data.get("flag_state", "").upper()
            if "CANADA" in flag_state:
                flag_code = "CA"
            elif "UNITED STATES" in flag_state or "USA" in flag_state:
                flag_code = "US"
            else:
                flag_code = None

            vessel = Vessel(
                vessel_name=vessel_data.get("vessel_name") or "Unknown",
                vessel_type=VesselType[vessel_data.get("vessel_type", "other").upper()],
                imo_number=imo if imo else None,
                year_built=vessel_data.get("year_built"),
                flag_state=flag_code,
                metadata_json=metadata,
            )
            self.session.add(vessel)
            self.session.flush()

            self._vessel_cache[cache_key] = vessel.vessel_id
            return vessel.vessel_id

        except Exception as e:
            print(f"Error creating vessel: {e}")
            return None
