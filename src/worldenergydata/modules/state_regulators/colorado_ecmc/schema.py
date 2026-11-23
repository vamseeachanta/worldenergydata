"""Column contracts for Colorado ECMC source parsing (#745)."""

PRODUCTION_REQUIRED_COLUMNS = {
    "DocNum",
    "ReportMonth",
    "ReportYear",
    "FacilityId",
    "ApiCountyCode",
    "ApiSequenceNumber",
    "ApiSidetrack",
    "GasPressureTubing",
    "GasPressureCasing",
    "WaterPressureTubing",
    "WaterPressureCasing",
}

PRODUCTION_READ_COLUMNS = [
    "DocNum",
    "ReportMonth",
    "ReportYear",
    "DaysProduced",
    "OpName",
    "OpNumber",
    "FacilityId",
    "ApiCountyCode",
    "ApiSequenceNumber",
    "ApiSidetrack",
    "Well",
    "WellStatus",
    "FormationCode",
    "GasProduced",
    "GasPressureTubing",
    "GasPressureCasing",
    "WaterPressureTubing",
    "WaterPressureCasing",
]

PRODUCTION_RENAME = {
    "DocNum": "doc_num",
    "ReportMonth": "report_month",
    "ReportYear": "report_year",
    "DaysProduced": "days_produced",
    "OpName": "operator",
    "OpNumber": "operator_number",
    "FacilityId": "facility_id",
    "Well": "well_name",
    "WellStatus": "well_status",
    "FormationCode": "formation_code",
    "GasProduced": "gas_mcf",
    "GasPressureTubing": "gas_pressure_tubing_psig",
    "GasPressureCasing": "gas_pressure_casing_psig",
    "WaterPressureTubing": "water_pressure_tubing_psig",
    "WaterPressureCasing": "water_pressure_casing_psig",
}

PRODUCTION_NUMERIC_COLUMNS = [
    "doc_num",
    "report_month",
    "report_year",
    "days_produced",
    "gas_mcf",
    "gas_pressure_tubing_psig",
    "gas_pressure_casing_psig",
    "water_pressure_tubing_psig",
    "water_pressure_casing_psig",
]

WELLS_REQUIRED_COLUMNS = {
    "API",
    "API_County",
    "API_Seq",
    "API_Label",
    "Field_Name",
    "Facil_Id",
    "Max_MD",
    "Max_TVD",
}

WELL_OUTPUT_COLUMNS = [
    "api12",
    "api10",
    "api_label",
    "facility_id",
    "field",
    "field_code",
    "max_md_ft",
    "max_tvd_ft",
    "latitude",
    "longitude",
]

PRESSURE_COLUMN_SPECS = {
    "GasPressureTubing": ("gas_pressure_tubing_psig", "WHP_flowing_tubing", 0),
    "GasPressureCasing": ("gas_pressure_casing_psig", "WHP_casing", 1),
}

WATER_PRESSURE_COLUMNS = [
    "water_pressure_tubing_psig",
    "water_pressure_casing_psig",
]

OBSERVATION_COLUMNS = [
    "state",
    "well_key",
    "api12",
    "api10",
    "facility_id",
    "well_name",
    "operator",
    "operator_number",
    "field",
    "formation_code",
    "test_date",
    "test_year",
    "test_type",
    "pressure_psig_reported",
    "pressure_psia",
    "pressure_kind",
    "gas_mcf",
    "days_produced",
    "reference_depth_ft",
    "reference_depth_source",
    "gradient_psi_ft",
    "gradient_method",
    "latitude",
    "longitude",
    "is_earliest_observation",
    "screen_observation_priority",
    "source_name",
]
