# ABOUTME: PHMSA pipeline safety data importer for Excel files
# ABOUTME: Handles all 4 pipeline types (GD, GTGG, HL, LNG)
# ABOUTME: across 3 eras (1986-2001, 2002-2009, 2010-present)

import math
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from worldenergydata.common import get_logger
from worldenergydata.pipeline_safety.database.models import PipelineIncident

logger = get_logger(__name__)

# File manifest: (filename, sheet_name, pipeline_type, era)
FILE_MANIFEST = [
    # Gas Distribution
    ("gd1986tofeb2004.xlsx", "gd1986tofeb2004", "gas_distribution", "pre2004"),
    ("gdmar2004to2009.xlsx", "gdmar2004to2009", "gas_distribution", "2004_2009"),
    ("gd2010toPresent.xlsx", "gd2010toPresent", "gas_distribution", "2010_present"),
    # Gas Transmission / Gathering
    ("gtgg1986to2001.xlsx", "gtgg1986to2001", "gas_transmission", "pre2004"),
    ("gtgg2002to2009.xlsx", "gtgg2002to2009", "gas_transmission", "2004_2009"),
    (
        "gtggungs2010toPresent.xlsx",
        "gtggungs2010toPresent",
        "gas_transmission",
        "2010_present",
    ),
    # Hazardous Liquid
    ("hl1986to2001.xlsx", "hl1986to2001", "hazardous_liquid", "pre2004"),
    ("hl2002to2009.xlsx", "hl2002to2009", "hazardous_liquid", "2004_2009"),
    ("hl2010toPresent.xlsx", "hl2010toPresent", "hazardous_liquid", "2010_present"),
    # LNG
    ("lng2011toPresent.xlsx", "lng2011toPresent", "lng", "2010_present"),
]

# Column mapping for modern era (2010-present) files
# Maps standard model fields to source column names per pipeline type
MODERN_COLUMN_MAP = {
    "report_number": "REPORT_NUMBER",
    "supplemental_number": "SUPPLEMENTAL_NUMBER",
    "report_type": "REPORT_TYPE",
    "operator_id": "OPERATOR_ID",
    "operator_name": "NAME",
    "incident_date": "LOCAL_DATETIME",
    "latitude": "LOCATION_LATITUDE",
    "longitude": "LOCATION_LONGITUDE",
    "commodity_released": "COMMODITY_RELEASED_TYPE",
    "ignition": "IGNITE_IND",
    "explosion": "EXPLODE_IND",
    "estimated_property_damage": "EST_COST_PROP_DAMAGE",
    "cause_category": "CAUSE",
    "cause_subcategory": "CAUSE_DETAILS",
    "narrative": "NARRATIVE",
    "pipeline_diameter": "PIPE_DIAMETER",
}

# LNG uses different location columns
LNG_COLUMN_OVERRIDES = {
    "latitude": "FACILITY_LATITUDE",
    "longitude": "FACILITY_LONGITUDE",
    "state": "FACILITY_STATE",
}

# Location columns vary by pipeline type for modern era
LOCATION_COLUMNS = {
    "gas_distribution": {
        "city": "LOCATION_CITY_NAME",
        "county": "LOCATION_COUNTY_NAME",
        "state": "LOCATION_STATE_ABBREVIATION",
        "location_description": "LOCATION_STREET_ADDRESS",
    },
    "gas_transmission": {
        "city": "ONSHORE_CITY_NAME",
        "county": "ONSHORE_COUNTY_NAME",
        "state": "ONSHORE_STATE_ABBREVIATION",
        "location_description": None,
    },
    "hazardous_liquid": {
        "city": "ONSHORE_CITY_NAME",
        "county": "ONSHORE_COUNTY_NAME",
        "state": "ONSHORE_STATE_ABBREVIATION",
        "location_description": None,
    },
    "lng": {
        "city": None,
        "county": None,
        "state": "FACILITY_STATE",
        "location_description": "FACILITY_NAME",
    },
}

# Fatality/injury sum columns (modern era)
FATALITY_COLUMNS = [
    "NUM_EMP_FATALITIES",
    "NUM_CONTR_FATALITIES",
    "NUM_ER_FATALITIES",
    "NUM_GP_FATALITIES",
]
INJURY_COLUMNS = [
    "NUM_EMP_INJURIES",
    "NUM_CONTR_INJURIES",
    "NUM_ER_INJURIES",
    "NUM_GP_INJURIES",
]

# Pre-2004 era column mapping (abbreviated column names)
PRE2004_COLUMN_MAP = {
    "report_number": "RPTID",
    "operator_id": "OPID",
    "operator_name": "NAME",
    "incident_date": "IDATE",
    "fatalities": "FAT",
    "injuries": "INJ",
    "narrative": None,
    "cause_category": None,
}

# 2004-2009 era column mapping
MID_COLUMN_MAP = {
    "report_number": "RPTID",
    "operator_id": "OPERATOR_ID",
    "operator_name": "NAME",
    "incident_date": "IDATE",
    "narrative": "NARRATIVE",
    "cause_category": "CAUSE",
    "cause_subcategory": "CAUSE_DETAILS",
    "estimated_property_damage": "EST_COST_PROP_DAMAGE",
    "pipeline_diameter": "PIPE_DIAMETER",
}

# Mid-era location columns
MID_LOCATION_COLUMNS = {
    "city": "ACCITY",
    "county": "ACCOUNTY",
    "state": "ACSTATE",
}


# Imported values are preserved without conversion. These labels describe the
# legacy schema, not a qualification of workbook units (knowledge pack U1).
IMPORT_UNIT_ASSUMPTIONS = {
    "pipeline_diameter": "unknown source unit; not assessment geometry",
    "latitude_longitude": "source coordinates; CRS/datum unverified",
    "incident_date": "source local timestamp; timezone unverified",
    "costs": "source currency/basis unverified; no inflation adjustment",
    "release": "barrels for BBLS fields; gas MCF assumed; LNG unit unknown",
    "consequences": "persons; missing component makes total unknown",
}


class MissingSourceColumnWarning(UserWarning):
    """A mapped source field was absent, rather than a reported blank cell."""


def _safe_int(value: Any) -> int | None:
    """Missing stays unknown; malformed or fractional counts raise."""
    number = _safe_float(value)
    if number is None:
        return None
    if not number.is_integer():
        raise ValueError("integer field is fractional")
    return int(number)


def _safe_float(value: Any) -> float | None:
    """Missing stays unknown; malformed and explicit non-finite tokens raise."""
    if pd.isna(value) or (isinstance(value, str) and not value.strip()):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("numeric field cannot be parsed") from exc
    if not math.isfinite(result):
        raise ValueError("numeric field must be finite")
    return result


def _safe_str(value: Any) -> str | None:
    """Convert value to stripped string, returning None for NaN/empty."""
    if pd.isna(value):
        return None
    result = str(value).strip()
    return result if result else None


def _parse_bool_indicator(value: Any) -> bool | None:
    """Parse YES/NO indicator to boolean."""
    if pd.isna(value) or (isinstance(value, str) and not value.strip()):
        return None
    s = str(value).strip().upper()
    if s in ("YES", "Y", "TRUE", "1"):
        return True
    if s in ("NO", "N", "FALSE", "0"):
        return False
    raise ValueError("boolean field has an unrecognized token")


def _parse_datetime(value: Any) -> datetime | None:
    """Parse datetime from various formats."""
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        return pd.to_datetime(value).to_pydatetime()
    except (ValueError, TypeError) as exc:
        raise ValueError("date field cannot be parsed") from exc


def _sum_columns(row: pd.Series, columns: list[str]) -> int | None:
    """A total is known only when every requested consequence count is known."""
    if not columns:
        return None
    values = [_safe_int(_get_col(row, col)) for col in columns]
    if any(value is None for value in values):
        return None
    if any(value < 0 for value in values):
        raise ValueError("consequence count must be nonnegative")
    return sum(values)


def _get_col(row: pd.Series, col_name: str | None) -> Any:
    """Report absent mapped columns; intentional unmapped fields stay unknown."""
    if col_name is None:
        return pd.NA
    if col_name not in row.index:
        warnings.warn(col_name, MissingSourceColumnWarning, stacklevel=2)
        return pd.NA
    return row[col_name]


class PHMSAImporter:
    """
    Importer for PHMSA pipeline safety incident data from Excel files.

    Handles all four pipeline types across three reporting eras:
    - Pre-2004: Abbreviated column names (RPTID, FAT, INJ, etc.)
    - 2004-2009: Transitional column names
    - 2010-present: Full column names (REPORT_NUMBER, LOCAL_DATETIME, etc.)

    Usage:
        importer = PHMSAImporter(
            db_session=session,
            data_dir="/path/to/phmsa/extracted",
        )
        stats = importer.import_data()
        logger.info(f"Imported: {stats['imported_count']}")
        logger.info(f"Skipped duplicates: {stats['skipped_count']}")
        logger.error(f"Errors: {stats['error_count']}")
    """

    def __init__(
        self,
        db_session: Session,
        data_dir: str,
        pipeline_types: list[str] | None = None,
    ):
        """
        Initialize the PHMSA importer.

        Args:
            db_session: SQLAlchemy database session for persistence.
            data_dir: Path to directory containing extracted PHMSA Excel files.
            pipeline_types: Optional filter for specific pipeline types.
                Valid values: gas_distribution, gas_transmission,
                hazardous_liquid, lng. Imports all types if None.
        """
        self.db_session = db_session
        self.data_dir = Path(data_dir)
        valid_types = {entry[2] for entry in FILE_MANIFEST}
        if pipeline_types is not None and not set(pipeline_types) <= valid_types:
            raise ValueError("unrecognized pipeline category")
        self.pipeline_types = pipeline_types
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.validation_errors: list[str] = []
        self.missing_source_columns: set[str] = set()

    def import_data(self) -> dict[str, Any]:
        """
        Execute full import pipeline across all PHMSA data files.

        Iterates through the file manifest, reads each Excel file,
        normalizes columns to the unified schema, validates required
        fields, checks for duplicates, and persists new records.

        Returns:
            Dictionary with import statistics:
            - imported_count: Records successfully imported
            - skipped_count: Duplicate records skipped
            - error_count: Records that failed validation
            - total_records: Total records processed
            - files_processed: Number of files read
        """
        total_records = 0
        files_processed = 0

        for filename, sheet_name, pipeline_type, era in FILE_MANIFEST:
            if self.pipeline_types and pipeline_type not in self.pipeline_types:
                continue

            filepath = self.data_dir / filename
            if not filepath.exists():
                logger.warning("File not found, skipping: %s", filepath)
                continue

            logger.info(
                "Processing %s (%s, %s era)",
                filename,
                pipeline_type,
                era,
            )

            try:
                df = pd.read_excel(
                    filepath,
                    sheet_name=sheet_name,
                    engine="openpyxl",
                )
            except (OSError, ValueError, ImportError) as exc:
                logger.error("Failed to read %s: %s", filename, exc)
                continue

            files_processed += 1
            total_records += len(df)

            for idx, row in df.iterrows():
                try:
                    normalized = self._normalize_row(row, pipeline_type, era)
                except (ValueError, TypeError, OverflowError) as exc:
                    logger.debug(
                        "Normalization error in %s row %s: %s",
                        filename,
                        idx,
                        exc,
                    )
                    # Record the parse reason without copying raw cell values.
                    self.validation_errors.append(f"{filename} row {idx}: {exc}")
                    self.error_count += 1
                    continue

                if not self._validate(normalized):
                    self.error_count += 1
                    continue

                if self._is_duplicate(normalized["report_number"]):
                    self.skipped_count += 1
                    continue

                self._persist(normalized)

            self.db_session.commit()
            logger.info(
                "Completed %s: %d rows",
                filename,
                len(df),
            )

        logger.info(
            "Import complete: %d imported, %d skipped, %d errors, %d total",
            self.imported_count,
            self.skipped_count,
            self.error_count,
            total_records,
        )

        return {
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "total_records": total_records,
            "files_processed": files_processed,
            "missing_source_columns": sorted(self.missing_source_columns),
            "unit_assumptions": dict(IMPORT_UNIT_ASSUMPTIONS),
            "validation_errors": list(self.validation_errors),
        }

    def _normalize_row(
        self,
        row: pd.Series,
        pipeline_type: str,
        era: str,
    ) -> dict[str, Any]:
        """
        Normalize a single row from any era/type to the unified schema.

        Args:
            row: pandas Series representing one incident row.
            pipeline_type: One of gas_distribution, gas_transmission,
                hazardous_liquid, lng.
            era: One of pre2004, 2004_2009, 2010_present.

        Returns:
            Dictionary matching PipelineIncident model fields.
        """
        if pipeline_type not in {entry[2] for entry in FILE_MANIFEST}:
            raise ValueError("unrecognized pipeline category")
        normalizers = {
            "2010_present": self._normalize_modern,
            "2004_2009": self._normalize_mid,
            "pre2004": self._normalize_legacy,
        }
        if era not in normalizers:
            raise ValueError("unrecognized source era")
        # Preserve missing-column diagnostics even when another cell fails.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", MissingSourceColumnWarning)
            try:
                result = normalizers[era](row, pipeline_type)
            finally:
                missing = {
                    str(w.message)
                    for w in caught
                    if issubclass(w.category, MissingSourceColumnWarning)
                }
                self.missing_source_columns.update(missing)
        result["missing_source_columns"] = sorted(missing)
        result["unit_assumptions"] = dict(IMPORT_UNIT_ASSUMPTIONS)
        return result

    def _normalize_modern(self, row: pd.Series, pipeline_type: str) -> dict[str, Any]:
        """Normalize 2010-present era rows."""
        col_map = dict(MODERN_COLUMN_MAP)

        # Apply LNG overrides
        if pipeline_type == "lng":
            col_map.update(LNG_COLUMN_OVERRIDES)

        # Location columns vary by type
        loc_cols = LOCATION_COLUMNS.get(pipeline_type, {})

        # Build the composite report number (unique across types)
        raw_report = _safe_str(_get_col(row, col_map["report_number"]))
        report_number = f"{pipeline_type}_{raw_report}" if raw_report else None

        # Sum fatality and injury sub-columns
        fatalities = _sum_columns(row, FATALITY_COLUMNS)
        injuries = _sum_columns(row, INJURY_COLUMNS)

        # Determine release quantity and unit based on type
        quantity, unit = self._extract_release_quantity(row, pipeline_type)

        # Cost of commodity lost
        commodity_cost = _safe_float(_get_col(row, "EST_COST_GAS_RELEASED"))
        if commodity_cost is None:
            commodity_cost = _safe_float(
                _get_col(row, "EST_COST_UNINTENTIONAL_RELEASE")
            )

        # Pipeline material
        pipe_material = _safe_str(_get_col(row, "PIPE_SPECIFICATION"))
        if pipe_material is None:
            pipe_material = _safe_str(_get_col(row, "MATERIAL_INVOLVED"))

        return {
            "report_number": report_number,
            "supplemental_number": _safe_str(
                _get_col(row, col_map["supplemental_number"])
            ),
            "report_type": pipeline_type,
            "operator_name": _safe_str(_get_col(row, col_map["operator_name"])),
            "operator_id": _safe_str(_get_col(row, col_map["operator_id"])),
            "incident_date": _parse_datetime(_get_col(row, col_map["incident_date"])),
            "incident_time": None,
            "state": _safe_str(_get_col(row, loc_cols.get("state"))),
            "county": _safe_str(_get_col(row, loc_cols.get("county"))),
            "city": _safe_str(_get_col(row, loc_cols.get("city"))),
            "location_description": _safe_str(
                _get_col(row, loc_cols.get("location_description"))
            ),
            "latitude": _safe_float(
                _get_col(row, col_map.get("latitude", "LOCATION_LATITUDE"))
            ),
            "longitude": _safe_float(
                _get_col(row, col_map.get("longitude", "LOCATION_LONGITUDE"))
            ),
            "pipeline_type": pipeline_type,
            "pipeline_diameter": _safe_float(
                _get_col(row, col_map["pipeline_diameter"])
            ),
            "pipeline_material": pipe_material,
            "commodity_released": _safe_str(
                _get_col(row, col_map["commodity_released"])
            ),
            "estimated_quantity_released": quantity,
            "unit_of_measure": unit,
            "ignition": _parse_bool_indicator(_get_col(row, col_map["ignition"])),
            "explosion": _parse_bool_indicator(_get_col(row, col_map["explosion"])),
            "fatalities": fatalities,
            "injuries": injuries,
            "estimated_property_damage": _safe_float(
                _get_col(row, col_map["estimated_property_damage"])
            ),
            "estimated_cost_of_commodity_lost": commodity_cost,
            "cause_category": _safe_str(_get_col(row, col_map["cause_category"])),
            "cause_subcategory": _safe_str(_get_col(row, col_map["cause_subcategory"])),
            "narrative": _safe_str(_get_col(row, col_map["narrative"])),
        }

    def _normalize_mid(self, row: pd.Series, pipeline_type: str) -> dict[str, Any]:
        """Normalize 2004-2009 era rows."""
        col_map = MID_COLUMN_MAP

        raw_report = _safe_str(_get_col(row, col_map["report_number"]))
        report_number = f"{pipeline_type}_{raw_report}" if raw_report else None

        # Mid-era uses ACSTATE, ACCITY, ACCOUNTY for location
        loc = MID_LOCATION_COLUMNS

        # Fatalities and injuries - check both old and transitional names
        fatalities = _safe_int(_get_col(row, "FAT"))
        if fatalities is None:
            fatalities = _sum_columns(row, FATALITY_COLUMNS)
        injuries = _safe_int(_get_col(row, "INJ"))
        if injuries is None:
            injuries = _sum_columns(row, INJURY_COLUMNS)

        return {
            "report_number": report_number,
            "supplemental_number": _safe_str(_get_col(row, "SUPPLEMENTAL_NUMBER")),
            "report_type": pipeline_type,
            "operator_name": _safe_str(_get_col(row, col_map["operator_name"])),
            "operator_id": _safe_str(_get_col(row, col_map["operator_id"])),
            "incident_date": _parse_datetime(_get_col(row, col_map["incident_date"])),
            "incident_time": _safe_str(_get_col(row, "IHOUR")),
            "state": _safe_str(_get_col(row, loc["state"])),
            "county": _safe_str(_get_col(row, loc["county"])),
            "city": _safe_str(_get_col(row, loc["city"])),
            "location_description": _safe_str(_get_col(row, "ACSTREET")),
            "latitude": _safe_float(_get_col(row, "LOCATION_LATITUDE")),
            "longitude": _safe_float(_get_col(row, "LOCATION_LONGITUDE")),
            "pipeline_type": pipeline_type,
            "pipeline_diameter": _safe_float(
                _get_col(row, col_map.get("pipeline_diameter"))
            ),
            "pipeline_material": _safe_str(_get_col(row, "PIPE_SPECIFICATION")),
            "commodity_released": _safe_str(_get_col(row, "COMMODITY_RELEASED_TYPE")),
            "estimated_quantity_released": None,
            "unit_of_measure": None,
            "ignition": _parse_bool_indicator(_get_col(row, "IGNITE_IND")),
            "explosion": _parse_bool_indicator(_get_col(row, "EXPLODE_IND")),
            "fatalities": fatalities,
            "injuries": injuries,
            "estimated_property_damage": _safe_float(
                _get_col(row, col_map.get("estimated_property_damage"))
            ),
            "estimated_cost_of_commodity_lost": _safe_float(
                _get_col(row, "EST_COST_GAS_RELEASED")
            ),
            "cause_category": _safe_str(_get_col(row, col_map["cause_category"])),
            "cause_subcategory": _safe_str(_get_col(row, col_map["cause_subcategory"])),
            "narrative": _safe_str(_get_col(row, col_map["narrative"])),
        }

    def _normalize_legacy(self, row: pd.Series, pipeline_type: str) -> dict[str, Any]:
        """Normalize pre-2004 era rows (abbreviated column names)."""
        raw_report = _safe_str(_get_col(row, "RPTID"))
        report_number = f"{pipeline_type}_{raw_report}" if raw_report else None

        fatalities = _safe_int(_get_col(row, "FAT"))
        injuries = _safe_int(_get_col(row, "INJ"))

        return {
            "report_number": report_number,
            "supplemental_number": None,
            "report_type": pipeline_type,
            "operator_name": _safe_str(_get_col(row, "NAME")),
            "operator_id": _safe_str(_get_col(row, "OPID")),
            "incident_date": _parse_datetime(_get_col(row, "IDATE")),
            "incident_time": _safe_str(_get_col(row, "DTHH")),
            "state": _safe_str(_get_col(row, "ACSTATE")),
            "county": _safe_str(_get_col(row, "ACCOUNTY")),
            "city": _safe_str(_get_col(row, "ACCITY")),
            "location_description": _safe_str(_get_col(row, "INADR")),
            "latitude": None,
            "longitude": None,
            "pipeline_type": pipeline_type,
            "pipeline_diameter": None,
            "pipeline_material": None,
            "commodity_released": None,
            "estimated_quantity_released": None,
            "unit_of_measure": None,
            "ignition": None,
            "explosion": None,
            "fatalities": fatalities,
            "injuries": injuries,
            "estimated_property_damage": _safe_float(_get_col(row, "TOTAL_COST")),
            "estimated_cost_of_commodity_lost": None,
            "cause_category": _safe_str(_get_col(row, "CAUSE")),
            "cause_subcategory": None,
            "narrative": _safe_str(_get_col(row, "NARRATIVE")),
        }

    def _extract_release_quantity(self, row: pd.Series, pipeline_type: str) -> tuple:
        """
        Extract release quantity and unit of measure based on pipeline type.

        HL uses barrels, gas types use MCF or cubic feet.

        Returns:
            Tuple of (quantity, unit_of_measure).
        """
        if pipeline_type == "hazardous_liquid":
            unintentional = _safe_float(_get_col(row, "UNINTENTIONAL_RELEASE_BBLS"))
            intentional = _safe_float(_get_col(row, "INTENTIONAL_RELEASE_BBLS"))
            if unintentional is None or intentional is None:
                return (None, "barrels")
            return (unintentional + intentional, "barrels")

        if pipeline_type == "lng":
            unintentional = _safe_float(_get_col(row, "UNINTENTIONAL_RELEASE"))
            intentional = _safe_float(_get_col(row, "INTENTIONAL_RELEASE"))
            if unintentional is None or intentional is None:
                return (None, None)
            # The workbook fields provide no unit-qualified name; do not guess.
            return (unintentional + intentional, None)

        # Gas distribution and transmission: estimated gas released in MCF
        est_mcf = _safe_float(_get_col(row, "ESTIMATED_GAS_RELEASED"))
        if est_mcf is not None:
            return (est_mcf, "MCF")
        return (None, None)

    def _validate(self, data: dict[str, Any]) -> bool:
        """
        Validate that required fields are present and well-formed.

        Required: report_number, incident_date, operator_name.

        Args:
            data: Normalized data dictionary.

        Returns:
            True if all required fields are present and valid.
        """
        if data.get("report_number") is None:
            self.validation_errors.append("Missing report_number")
            return False

        if data.get("incident_date") is None:
            self.validation_errors.append(
                f"Missing incident_date for {data.get('report_number')}"
            )
            return False

        if data.get("operator_name") is None:
            self.validation_errors.append(
                f"Missing operator_name for {data.get('report_number')}"
            )
            return False

        return True

    def _is_duplicate(self, report_number: str) -> bool:
        """
        Check if a report_number already exists in the database.

        Args:
            report_number: Composite key (pipeline_type + raw report number).

        Returns:
            True if the incident already exists.
        """
        existing = (
            self.db_session.query(PipelineIncident.id)
            .filter(PipelineIncident.report_number == report_number)
            .first()
        )
        return existing is not None

    def _persist(self, data: dict[str, Any]) -> None:
        """
        Create a PipelineIncident record and add to the session.

        The session is not committed here; commit happens per-file
        in import_data() for batch efficiency.

        Args:
            data: Validated, normalized data dictionary.
        """
        incident = PipelineIncident(
            report_number=data["report_number"],
            supplemental_number=data.get("supplemental_number"),
            report_type=data["report_type"],
            operator_name=data["operator_name"],
            operator_id=data.get("operator_id"),
            incident_date=data["incident_date"],
            incident_time=data.get("incident_time"),
            state=data.get("state"),
            county=data.get("county"),
            city=data.get("city"),
            location_description=data.get("location_description"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            pipeline_type=data.get("pipeline_type"),
            pipeline_diameter=data.get("pipeline_diameter"),
            pipeline_material=data.get("pipeline_material"),
            commodity_released=data.get("commodity_released"),
            estimated_quantity_released=data.get("estimated_quantity_released"),
            unit_of_measure=data.get("unit_of_measure"),
            ignition=data.get("ignition"),
            explosion=data.get("explosion"),
            fatalities=data.get("fatalities"),
            injuries=data.get("injuries"),
            estimated_property_damage=data.get("estimated_property_damage"),
            estimated_cost_of_commodity_lost=data.get(
                "estimated_cost_of_commodity_lost"
            ),
            cause_category=data.get("cause_category"),
            cause_subcategory=data.get("cause_subcategory"),
            narrative=data.get("narrative"),
        )
        self.db_session.add(incident)
        self.imported_count += 1
