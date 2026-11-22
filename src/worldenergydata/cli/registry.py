"""Static CLI metadata; importing the registry never loads a command family."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandFamily:
    """Import target and the distinct root-help and info-table descriptions."""

    module: str
    help: str
    info_desc: str
    key_commands: str
    attr: str = "app"


# Preserve the public registration order independently of the info table order.
COMMAND_FAMILIES: dict[str, CommandFamily] = {
    "bsee": CommandFamily(
        module="worldenergydata.cli.commands.bsee",
        help="BSEE data operations and analysis",
        info_desc="BSEE data operations and analysis",
        key_commands="analyze, report, data, refresh",
    ),
    "dashboard": CommandFamily(
        module="worldenergydata.cli.commands.dashboard",
        help="Launch the Plotly Dash BSEE/FDAS web dashboard",
        info_desc="Plotly Dash BSEE/FDAS web dashboard (server)",
        key_commands="launch",
    ),
    "eia": CommandFamily(
        module="worldenergydata.cli.commands.eia",
        help="EIA API v2 weekly petroleum and gas feed ingestion",
        info_desc="EIA API v2 weekly petroleum and gas feed ingestion",
        key_commands="fetch, status",
    ),
    "marine-safety": CommandFamily(
        module="worldenergydata.cli.commands.marine_safety",
        help="Marine safety incident data management",
        info_desc="Marine safety incident data",
        key_commands="scrape, stats, export, db",
    ),
    "fdas": CommandFamily(
        module="worldenergydata.cli.commands.fdas",
        help="Field Development Analysis System",
        info_desc="Field Development Analysis System",
        key_commands="calculate-npv, calculate-mirr, analyze",
    ),
    "hse": CommandFamily(
        module="worldenergydata.cli.commands.hse",
        help="HSE incident queries",
        info_desc="HSE incident queries",
        key_commands="incidents query",
    ),
    "lower-tertiary": CommandFamily(
        module="worldenergydata.cli.commands.lower_tertiary",
        help="Lower Tertiary portfolio analyses (10 GoM fields)",
        info_desc="Lower Tertiary portfolio analyses (10 GoM fields)",
        key_commands="analyze, report, economics",
    ),
    "sodir": CommandFamily(
        module="worldenergydata.cli.commands.sodir",
        help="SODIR (Norwegian Offshore Directorate) data operations",
        info_desc="SODIR (Norwegian Offshore Directorate)",
        key_commands="collect, analyze, status",
    ),
    "metocean": CommandFamily(
        module="worldenergydata.cli.commands.metocean",
        help="Metocean data - buoys, tides, marine weather",
        info_desc="Metocean data (buoys, tides, weather)",
        key_commands="stations, fetch, forecast, cache, db",
    ),
    "ndbc": CommandFamily(
        module="worldenergydata.cli.commands.ndbc",
        help="NDBC buoy data: scatter matrices, Weibull fits, wave roses",
        info_desc="NDBC buoy data: scatter matrices, Weibull fits, wave roses",
        key_commands="fetch, scatter, weibull, wave-rose",
    ),
    "texas-rrc": CommandFamily(
        module="worldenergydata.cli.commands.texas_rrc",
        help="Texas Railroad Commission oil & gas data",
        info_desc="Texas Railroad Commission oil & gas",
        key_commands="collect, analyze, status, validate-api",
    ),
    "kansas-kgs": CommandFamily(
        module="worldenergydata.cli.commands.kansas_kgs",
        help="Kansas Geological Survey well and pressure data",
        info_desc="Kansas Geological Survey oil & gas",
        key_commands="build-pressure-observations",
    ),
    "canada": CommandFamily(
        module="worldenergydata.cli.commands.canada",
        help="Canadian oil & gas data (AER/BCER)",
        info_desc="Canadian oil & gas (AER/BCER)",
        key_commands="collect, analyze, status, validate-uwi",
    ),
    "mexico-cnh": CommandFamily(
        module="worldenergydata.cli.commands.mexico_cnh",
        help="Mexico CNH oil & gas data (SIH dashboard)",
        info_desc="Mexico CNH oil & gas (SIH dashboard)",
        key_commands="scrape, download-open-data, status, validate-clave",
    ),
    "landman": CommandFamily(
        module="worldenergydata.cli.commands.landman",
        help="Mineral ownership and lease data operations",
        info_desc="Mineral ownership and lease data",
        key_commands="search, lookup, county-info, providers, status",
    ),
    "lng-terminals": CommandFamily(
        module="worldenergydata.cli.commands.lng_terminals",
        help="Global LNG terminal dataset with engineering design data",
        info_desc="Global LNG terminal dataset",
        key_commands="collect, process, export, report, pipeline",
    ),
    "safety-analysis": CommandFamily(
        module="worldenergydata.safety_analysis.cli",
        help="Safety analysis and HSE data processing",
        info_desc="Safety analysis and HSE data processing",
        key_commands="load, classify, correlate, report, status",
    ),
    "forecast": CommandFamily(
        module="worldenergydata.cli.commands.production_forecast",
        help="Arps decline curve analysis — fit, EUR, and production forecast",
        info_desc="Arps decline curve — fit, EUR, production forecast",
        key_commands="fit, forecast, report",
    ),
}

INFO_ROW_ORDER: tuple[str, ...] = (
    "bsee",
    "dashboard",
    "eia",
    "marine-safety",
    "fdas",
    "hse",
    "lower-tertiary",
    "forecast",
    "sodir",
    "metocean",
    "ndbc",
    "texas-rrc",
    "kansas-kgs",
    "canada",
    "mexico-cnh",
    "landman",
    "lng-terminals",
    "safety-analysis",
)
