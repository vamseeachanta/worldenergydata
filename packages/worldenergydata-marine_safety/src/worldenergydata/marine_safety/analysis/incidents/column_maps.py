"""
ABOUTME: Source-specific column name mappings for MAIB, NTSB, and USCG MISLE taxonomy pipeline.
ABOUTME: Maps raw source field names to canonical taxonomy column names.
"""

from __future__ import annotations

from typing import Dict

# Maps from raw USCG MISLE CSV column names to canonical taxonomy names.
# Handles both standard MISLE exports and the USCG boating incident variant.
USCG_COLUMN_MAP: Dict[str, str] = {
    "REPORT_NUM": "report_id",
    "MASTER_KEY": "report_id",
    "VESSEL_NAME": "vessel_name",
    "VES_NAME": "vessel_name",
    "EVENT_DATE": "incident_date",
    "DATE": "incident_date",
    "LATITUDE": "latitude",
    "LAT": "latitude",
    "LONGITUDE": "longitude",
    "LON": "longitude",
    "CASUALTY_TYPE": "incident_type",
    "PRIMARY_CAUSE": "primary_cause",
    "NARRATIVE": "narrative",
    "INJURY_COUNT": "injury_count",
    "FATALITY_COUNT": "fatality_count",
    "VESSEL_TYPE": "vessel_type",
    "VES_TYPE": "vessel_type",
    # MISLE-specific operation phase field
    "ACTIVITY_TYPE": "activity_type",
    "OPERATION_TYPE": "activity_type",
    "OPERATION_PHASE": "activity_type",
}

# Maps from raw MAIB occurrence CSV column names to canonical taxonomy names.
MAIB_COLUMN_MAP: Dict[str, str] = {
    "Occurrence_Id": "report_id",
    "Date": "incident_date",
    "Accident_Title": "title",
    "Main_Event": "incident_type",
    "Abstract": "narrative",
    "Vessel_Name": "vessel_name",
    "Vessel_Type": "vessel_type",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Deaths": "fatality_count",
    "Injuries": "injury_count",
}

# Maps from raw NTSB CAROL CSV column names to canonical taxonomy names.
NTSB_COLUMN_MAP: Dict[str, str] = {
    "EventId": "report_id",
    "EventDate": "incident_date",
    "AccidentTitle": "title",
    "IncidentType": "incident_type",
    "ProbableCause": "primary_cause",
    "Narrative": "narrative",
    "VesselName": "vessel_name",
    "VesselType": "vessel_type",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "FatalCount": "fatality_count",
    "InjuryCount": "injury_count",
}
