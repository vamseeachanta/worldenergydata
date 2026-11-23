"""Official Texas RRC completion-packet schema maps used for pressure rows."""

from __future__ import annotations

from typing import Mapping

PACKET_COLUMNS = (
    "PACKET",
    "TRACKING_NO",
    "PACKET_ID",
    "SUBMITTED_DT",
    "OPERATOR_NO",
    "API_NUMBER",
    "LEASE_NO",
    "WELL_NO",
    "FIELD_NO",
    "DISTRICT",
    "FIELD_NAME",
)

G1_COLUMNS = (
    "G-1",
    "TRACKING_NO",
    "PACKET_ID",
    "G1_ID",
    "DATE_OF_TEST",
    "TEST_GAS_PRODUCTION",
    "IS_DRY_GAS_WELL",
    "GRAVITY_DRY_GAS",
    "GAS_HYDRO_RATIO",
    "AVG_SHUTIN_TEMP",
    "GRAVITY_HYDROCARBON",
    "GRAVITY_OF_MIXTURE",
    "BOTTOM_HOLE_TEMP",
    "BOTTOM_HOLE_DEPTH",
    "NOTICE_OF_INTENTION",
    "NUMBER_OF_PRODUCING_WELLS",
    "ACRES_IN_LEASE",
    "WORK_COMMENCED_DT",
    "WORK_COMPLETED_DT",
    "DISTANCE_TO_NEAREST_WELL",
    "DISTANCE_TO_BNDRY_A",
    "DIRECTION_TO_BNDRY_A_CODE",
    "DISTANCE_TO_BNDRY_B",
    "DIRECTION_TO_BNDRY_B_CODE",
    "BOUNDARY_LEASE_NAME",
    "ELEVATION",
    "ELEVATION_CODE",
    "WAS_DIRECT_SURVEY_MADE",
    "TOP_OF_PAY",
    "MEASURED_DEPTH",
    "VERTICAL_DEPTH",
    "PLUG_BACK_DEPTH",
    "CASING_DETR_FIELD_RULES",
    "CASING_DETR_RECOMMEND_DT",
    "CASING_DETR_RRC_DT",
    "DRILLING_CONTRACTOR_NM",
    "IS_MULTIPLE_COMPLETION",
    "DID_PREFLOW_48_HOURS",
    "PIPELINE_CONNECTION",
    "ANY_CONDENSATE",
    "REMARKS",
    "INTERVALS_DRILLED_BY_CODE",
    "SECTION_ONE_REMARKS",
    "CEMENTING_AFFIDAVIT_ATTACHED",
    "AMOUNT_MATERIAL_REMARKS",
    "FORM_CERTIFICATION",
    "TESTER_NAME",
    "TESTER_COMPANY",
    "INTERVALS_DRILLED_BY_OTHER",
    "PROD_INTV_REMARK",
    "TESTER_PHONE",
    "OP_IS_TESTER",
    "GMM_ORIFICE_METER",
    "GMM_FLANGE_TAPS",
    "GMM_POS_CHOKE",
    "GMM_PIPE_TAPS",
    "GMM_ORIFICE_VENT",
    "GMM_PITOT_TUBE",
    "GMM_CRITICAL_FLOW",
    "BOTTOM_HOLE_PRESS",
    "IS_UNPERFORATED_CMPL",
    "PLUG_BACK_DEPTH_TMD",
    "TOP_OF_PAY_TMD",
    "OFF_LEASE",
    "COMMINGLED",
    "INTERVAL_HYDROGEN_SULFIDE",
    "HYDRAULIC_FRACKING_USED",
    "HAS_FRACKING_DISCLOSURE",
    "TUBING_REC_REMARKS",
    "SURFACE_CASING_ROTATION_TIME",
    "CASING_DETR_RECOMMEND_DEPTH",
    "CASING_DETR_SWR_13_DEPTH",
    "IS_ACTUATION_VALVE_ON_WELL",
    "PROD_CASE_PSIG_BEF_FRACK_TREAT",
    "HYDRAULIC_FRACKING_MAX_PSIG",
    "CASING_DETR_SWR_13_EXCEP",
    "CASING_DETR_RECOMMEND_GAU_GPD",
    "ACTUATION_VALVE_ON_WELL_PSIG",
    "GMM_MASS_FLOW_METER",
    "GMM_OTHER",
    "MEASUREMENT_DATA_ROW_CNT",
    "AMOUNT_AND_MATERIAL_ROW_CNT",
    "FIELD_DATA_ROW_CNT",
    "MULTI_CMPL_ROW_COUNT",
    "CASING_DATA_ROW_COUNT",
    "LINER_DATA_ROW_COUNT",
    "TUBING_DATA_ROW_COUNT",
    "PROD_INTRVL_DATA_ROW_CNT",
    "FORMATION_DATA_ROW_CNT",
)

G1_MEASUREMENT_COLUMNS = (
    "G-1 Measurement Data",
    "TRACKING_NO",
    "PACKET_ID",
    "G1_ID",
    "ROW_NO",
    "LINE_SIZE",
    "ORIFICE_CHOKE_SIZE",
    "TWENTYFOUR_HOUR_COEFF",
    "STATIC_CHOKE_PRESS",
    "DIFF",
    "FLOW_TEMP",
    "TEMP_FACTOR",
    "GRAVITY_FACTOR",
    "COMPRESS_FACTOR",
    "VOLUME",
)

G1_FIELD_COLUMNS = (
    "G-1 Field Data",
    "TRACKING_NO",
    "PACKET_ID",
    "G1_ID",
    "ROW_NO",
    "TIME_OF_RUN",
    "CHOKE_SIZE",
    "WELLHEAD_PRESS",
    "WELLHEAD_FLOW_TEMP",
)

G10_COLUMNS = (
    "G-10",
    "TRACKING_NO",
    "PACKET_ID",
    "G10_ID",
    "REASON_CODE",
    "DUE_DT",
    "EFFECTIVE_DT",
    "COND_PRODUCED",
    "COND_GRAVITY",
    "WATER_PRODUCED",
    "XBHOLE_PRESSURE",
    "FORM_CERTIFICATION",
    "DATE_TESTED",
    "TESTER_NAME",
    "TESTER_COMPANY",
    "GAS_PROD_DURING_TEST",
    "GRAVITY_DRY_GAS",
    "SIWH_PRESSURE",
    "FLOWING_PRESSURE",
    "TESTER_PHONE",
)

W2_COLUMNS = (
    "W-2",
    "TRACKING_NO",
    "PACKET_ID",
    "W2_ID",
    "DATE_OF_TEST",
    "OIL_PROD_DURING_TEST",
    "GAS_PROD_DURING_TEST",
    "CHOKE_SIZE",
    "FLOW_TUBING_PRESS",
    "CASING_PRESS",
    "CALC_CASING_PRESS",
    "PROD_CASE_PSIG_BEF_FRACK_TREAT",
    "HYDRAULIC_FRACKING_MAX_PSIG",
    "ACTUATION_VALVE_ON_WELL_PSIG",
)

PRODUCTION_INTERVAL_COLUMNS = (
    "RECORD_TYPE",
    "TRACKING_NO",
    "PACKET_ID",
    "FORM_ID",
    "ROW_NO",
    "FROM",
    "TO",
    "BOTTOM_HOLE_LABEL",
    "LATERAL_LABEL",
    "OPEN_HOLE",
)

FORMATION_COLUMNS = (
    "RECORD_TYPE",
    "TRACKING_NO",
    "PACKET_ID",
    "FORM_ID",
    "ROW_NO",
    "FORMATION",
    "DEPTH",
    "DEPTH_TMD",
    "USER_ENCOUNTERED",
    "USER_REMARK",
    "USER_ISOLATED",
)

PRESSURE_RECORD_SCHEMAS: Mapping[str, tuple[str, ...]] = {
    "PACKET": PACKET_COLUMNS,
    "G-1": G1_COLUMNS,
    "G-1 Measurement Data": G1_MEASUREMENT_COLUMNS,
    "G-1 Field Data": G1_FIELD_COLUMNS,
    "G-10": G10_COLUMNS,
    "W-2": W2_COLUMNS,
    "G-1 Production Interval Data": (
        "G-1 Production Interval Data",
        *PRODUCTION_INTERVAL_COLUMNS[1:],
    ),
    "W-2 Production Interval Data": (
        "W-2 Production Interval Data",
        *PRODUCTION_INTERVAL_COLUMNS[1:],
    ),
    "G-1 Formation Data": ("G-1 Formation Data", *FORMATION_COLUMNS[1:]),
    "W-2 Formation Data": ("W-2 Formation Data", *FORMATION_COLUMNS[1:]),
}

PRESSURE_FIELDS: Mapping[str, tuple[str, ...]] = {
    "G-1": ("BOTTOM_HOLE_PRESS",),
    "G-1 Measurement Data": ("STATIC_CHOKE_PRESS",),
    "G-1 Field Data": ("WELLHEAD_PRESS",),
    "G-10": ("XBHOLE_PRESSURE", "SIWH_PRESSURE", "FLOWING_PRESSURE"),
    "W-2": (
        "FLOW_TUBING_PRESS",
        "CASING_PRESS",
        "CALC_CASING_PRESS",
        "PROD_CASE_PSIG_BEF_FRACK_TREAT",
        "HYDRAULIC_FRACKING_MAX_PSIG",
        "ACTUATION_VALVE_ON_WELL_PSIG",
    ),
}


def field_index(record_type: str, field_name: str) -> int:
    """Return the brace-delimited field index for a named packet field."""
    try:
        columns = PRESSURE_RECORD_SCHEMAS[record_type]
    except KeyError as exc:
        raise KeyError(f"Unknown Texas RRC packet record type: {record_type}") from exc
    try:
        return columns.index(field_name)
    except ValueError as exc:
        raise KeyError(f"{field_name} is not defined for {record_type}") from exc


def pressure_fields_for(record_type: str) -> tuple[str, ...]:
    """Return pressure-bearing source fields for a packet record type."""
    return PRESSURE_FIELDS.get(record_type, ())


__all__ = [
    "PRESSURE_RECORD_SCHEMAS",
    "field_index",
    "pressure_fields_for",
]
