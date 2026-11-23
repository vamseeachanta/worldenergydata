"""Shared schema constants for the source refresh acceptance contract."""

REQUIRED_HIGH_VALUE_SOURCES = (
    "bsee eia_us sodir ukcs brazil_anp lng_terminals metocean hse "
    "marine_safety vessel_fleet vessel_hull_models oil_price wind"
).split()

REQUIRED_ROW_FIELDS = (
    "module_id materialized_module_id aliases display_name source_authority "
    "source_url_or_api source_data_latest_date source_data_latest_date_basis "
    "source_data_latest_date_unknown_reason last_successful_refresh "
    "last_successful_refresh_basis data_location external_data_root_required "
    "scheduler_job scheduler_output_dir refresh_command record_count artifact_count "
    "refresh_cadence freshness_grace_days freshness_status completeness_status "
    "credential_requirement blocker_issue downstream_consumers"
).split()

SCORECARD_RESULTS = {
    "empty|empty": ("missing", "empty"),
    "full|full": ("unknown", "full"),
    "missing|not_applicable": ("not_applicable", "not_applicable"),
    "missing|runtime_fetched": ("missing", "runtime_fetched"),
    "not_applicable|not_applicable": ("not_applicable", "not_applicable"),
    "reference_data|reference_data": ("reference_data", "reference_data"),
    "sample|sample": ("stale", "sample"),
    "unknown|unknown": ("unknown", "unknown"),
}
SCORECARD_PAIR_MAPPING = {
    pair: {"freshness_status": freshness, "completeness_status": completeness}
    for pair, (freshness, completeness) in SCORECARD_RESULTS.items()
}
REQUIRED_WILDCARD_SCORECARD_MAPPINGS = {
    "fresh|*": {
        "freshness_status": "fresh",
        "completeness_status": "mapped_from_catalog_status",
    },
    "stale|*": {
        "freshness_status": "stale",
        "completeness_status": "mapped_from_catalog_status",
    },
}

COMPLETENESS_VALUES = (
    "full sample empty missing runtime_fetched reference_data blocked unknown "
    "not_applicable"
).split()
COMPLETENESS_BY_CATALOG_STATUS = dict(zip(COMPLETENESS_VALUES, COMPLETENESS_VALUES))
