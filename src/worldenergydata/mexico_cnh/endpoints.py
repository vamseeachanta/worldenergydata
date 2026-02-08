# ABOUTME: CNH portal URL definitions and endpoint configuration
# ABOUTME: Defines URLs for SIH dashboard, production portal, maps, and open data

"""
Mexico CNH (Comision Nacional de Hidrocarburos) Portal Endpoints.

This module defines the URLs and endpoint configurations for accessing
Mexico's National Hydrocarbons Commission data portals.

Portals:
- SIH (Sistema de Informacion de Hidrocarburos): Main dashboard
- Production Portal: Monthly/annual production reports
- Map Portal: Geographic data and maps
- Open Data Portal: Public datasets and downloads
- Rondas (Bidding Rounds): Contract information
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class CNHPortal(Enum):
    """Enumeration of CNH data portals."""

    SIH = "sih"
    PRODUCTION = "production"
    MAPS = "maps"
    OPEN_DATA = "open_data"
    RONDAS = "rondas"
    CONTRACTS = "contracts"


@dataclass
class CNHEndpoint:
    """Configuration for a CNH endpoint."""

    name: str
    url: str
    portal: CNHPortal
    requires_javascript: bool = True
    requires_auth: bool = False
    description: str = ""


class CNHEndpoints:
    """
    Mexico CNH Portal URL Definitions.

    Contains URLs for all CNH data portals and their sub-pages.
    Many portals require JavaScript rendering via Selenium.
    """

    # Base URLs
    BASE_URL = "https://www.gob.mx/cnh"
    SIH_BASE = "https://sih.hidrocarburos.gob.mx"
    RONDAS_BASE = "https://rondasmexico.gob.mx"

    # SIH Dashboard URLs
    SIH_DASHBOARD = f"{SIH_BASE}/"
    SIH_PRODUCTION = f"{SIH_BASE}/produccion/"
    SIH_WELLS = f"{SIH_BASE}/pozos/"
    SIH_FIELDS = f"{SIH_BASE}/campos/"
    SIH_RESERVES = f"{SIH_BASE}/reservas/"
    SIH_EXPLORATION = f"{SIH_BASE}/exploracion/"

    # Production Portal URLs
    PRODUCTION_MONTHLY = f"{SIH_BASE}/produccion/mensual/"
    PRODUCTION_ANNUAL = f"{SIH_BASE}/produccion/anual/"
    PRODUCTION_BY_OPERATOR = f"{SIH_BASE}/produccion/operador/"
    PRODUCTION_BY_FIELD = f"{SIH_BASE}/produccion/campo/"
    PRODUCTION_BY_CONTRACT = f"{SIH_BASE}/produccion/contrato/"

    # Map Portal URLs
    MAP_PORTAL = f"{SIH_BASE}/mapas/"
    MAP_WELLS = f"{SIH_BASE}/mapas/pozos/"
    MAP_FIELDS = f"{SIH_BASE}/mapas/campos/"
    MAP_CONTRACTS = f"{SIH_BASE}/mapas/contratos/"
    MAP_SEISMIC = f"{SIH_BASE}/mapas/sismica/"

    # Open Data Portal URLs
    OPEN_DATA_PORTAL = "https://datos.gob.mx/busca/organization/cnh"
    OPEN_DATA_PRODUCTION = (
        "https://datos.gob.mx/busca/dataset/produccion-de-hidrocarburos"
    )
    OPEN_DATA_WELLS = "https://datos.gob.mx/busca/dataset/pozos-de-hidrocarburos"
    OPEN_DATA_RESERVES = "https://datos.gob.mx/busca/dataset/reservas-de-hidrocarburos"

    # Rondas (Bidding Rounds) URLs
    RONDAS_MAIN = f"{RONDAS_BASE}/"
    RONDAS_ROUND1 = f"{RONDAS_BASE}/ronda-1/"
    RONDAS_ROUND2 = f"{RONDAS_BASE}/ronda-2/"
    RONDAS_ROUND3 = f"{RONDAS_BASE}/ronda-3/"
    RONDAS_FARMOUTS = f"{RONDAS_BASE}/farmouts/"

    # Contract Information URLs
    CONTRACTS_ACTIVE = f"{SIH_BASE}/contratos/activos/"
    CONTRACTS_ASSIGNMENTS = f"{SIH_BASE}/contratos/asignaciones/"
    CONTRACTS_LICENSES = f"{SIH_BASE}/contratos/licencias/"
    CONTRACTS_PSC = f"{SIH_BASE}/contratos/produccion-compartida/"

    # Download URLs (direct file downloads)
    DOWNLOADS_BASE = f"{SIH_BASE}/descargas/"
    DOWNLOADS_PRODUCTION_XLS = f"{SIH_BASE}/descargas/produccion.xlsx"
    DOWNLOADS_WELLS_XLS = f"{SIH_BASE}/descargas/pozos.xlsx"
    DOWNLOADS_RESERVES_XLS = f"{SIH_BASE}/descargas/reservas.xlsx"

    # API Endpoints (if available)
    API_BASE = f"{SIH_BASE}/api/v1"
    API_PRODUCTION = f"{API_BASE}/produccion"
    API_WELLS = f"{API_BASE}/pozos"
    API_FIELDS = f"{API_BASE}/campos"

    @classmethod
    def get_all_endpoints(cls) -> Dict[str, CNHEndpoint]:
        """
        Get all defined CNH endpoints.

        Returns:
            Dictionary mapping endpoint names to CNHEndpoint objects
        """
        return {
            # SIH Dashboard
            "sih_dashboard": CNHEndpoint(
                name="SIH Dashboard",
                url=cls.SIH_DASHBOARD,
                portal=CNHPortal.SIH,
                requires_javascript=True,
                description="Main SIH dashboard with overview statistics",
            ),
            "sih_production": CNHEndpoint(
                name="SIH Production",
                url=cls.SIH_PRODUCTION,
                portal=CNHPortal.SIH,
                requires_javascript=True,
                description="Production data section of SIH",
            ),
            "sih_wells": CNHEndpoint(
                name="SIH Wells",
                url=cls.SIH_WELLS,
                portal=CNHPortal.SIH,
                requires_javascript=True,
                description="Well data section of SIH",
            ),
            "sih_fields": CNHEndpoint(
                name="SIH Fields",
                url=cls.SIH_FIELDS,
                portal=CNHPortal.SIH,
                requires_javascript=True,
                description="Field data section of SIH",
            ),
            "sih_reserves": CNHEndpoint(
                name="SIH Reserves",
                url=cls.SIH_RESERVES,
                portal=CNHPortal.SIH,
                requires_javascript=True,
                description="Reserves data section of SIH",
            ),
            # Production Portal
            "production_monthly": CNHEndpoint(
                name="Monthly Production",
                url=cls.PRODUCTION_MONTHLY,
                portal=CNHPortal.PRODUCTION,
                requires_javascript=True,
                description="Monthly production reports",
            ),
            "production_annual": CNHEndpoint(
                name="Annual Production",
                url=cls.PRODUCTION_ANNUAL,
                portal=CNHPortal.PRODUCTION,
                requires_javascript=True,
                description="Annual production reports",
            ),
            "production_by_operator": CNHEndpoint(
                name="Production by Operator",
                url=cls.PRODUCTION_BY_OPERATOR,
                portal=CNHPortal.PRODUCTION,
                requires_javascript=True,
                description="Production data grouped by operator",
            ),
            "production_by_field": CNHEndpoint(
                name="Production by Field",
                url=cls.PRODUCTION_BY_FIELD,
                portal=CNHPortal.PRODUCTION,
                requires_javascript=True,
                description="Production data grouped by field",
            ),
            # Map Portal
            "map_portal": CNHEndpoint(
                name="Map Portal",
                url=cls.MAP_PORTAL,
                portal=CNHPortal.MAPS,
                requires_javascript=True,
                description="Interactive map portal",
            ),
            "map_wells": CNHEndpoint(
                name="Well Map",
                url=cls.MAP_WELLS,
                portal=CNHPortal.MAPS,
                requires_javascript=True,
                description="Map of wells",
            ),
            "map_fields": CNHEndpoint(
                name="Field Map",
                url=cls.MAP_FIELDS,
                portal=CNHPortal.MAPS,
                requires_javascript=True,
                description="Map of fields",
            ),
            # Open Data
            "open_data_portal": CNHEndpoint(
                name="Open Data Portal",
                url=cls.OPEN_DATA_PORTAL,
                portal=CNHPortal.OPEN_DATA,
                requires_javascript=False,
                description="Government open data portal for CNH",
            ),
            "open_data_production": CNHEndpoint(
                name="Open Data Production",
                url=cls.OPEN_DATA_PRODUCTION,
                portal=CNHPortal.OPEN_DATA,
                requires_javascript=False,
                description="Production datasets on open data portal",
            ),
            # Rondas
            "rondas_main": CNHEndpoint(
                name="Rondas Main",
                url=cls.RONDAS_MAIN,
                portal=CNHPortal.RONDAS,
                requires_javascript=True,
                description="Main bidding rounds portal",
            ),
            # Contracts
            "contracts_active": CNHEndpoint(
                name="Active Contracts",
                url=cls.CONTRACTS_ACTIVE,
                portal=CNHPortal.CONTRACTS,
                requires_javascript=True,
                description="List of active contracts",
            ),
            "contracts_assignments": CNHEndpoint(
                name="PEMEX Assignments",
                url=cls.CONTRACTS_ASSIGNMENTS,
                portal=CNHPortal.CONTRACTS,
                requires_javascript=True,
                description="PEMEX assignment contracts",
            ),
            # Downloads
            "downloads_production": CNHEndpoint(
                name="Production Download",
                url=cls.DOWNLOADS_PRODUCTION_XLS,
                portal=CNHPortal.OPEN_DATA,
                requires_javascript=False,
                description="Direct download of production Excel file",
            ),
            "downloads_wells": CNHEndpoint(
                name="Wells Download",
                url=cls.DOWNLOADS_WELLS_XLS,
                portal=CNHPortal.OPEN_DATA,
                requires_javascript=False,
                description="Direct download of wells Excel file",
            ),
        }

    @classmethod
    def get_endpoint(cls, name: str) -> Optional[CNHEndpoint]:
        """
        Get a specific endpoint by name.

        Args:
            name: Endpoint name

        Returns:
            CNHEndpoint if found, None otherwise
        """
        endpoints = cls.get_all_endpoints()
        return endpoints.get(name)

    @classmethod
    def get_endpoints_by_portal(cls, portal: CNHPortal) -> Dict[str, CNHEndpoint]:
        """
        Get all endpoints for a specific portal.

        Args:
            portal: CNHPortal enum value

        Returns:
            Dictionary of endpoints for the specified portal
        """
        all_endpoints = cls.get_all_endpoints()
        return {
            name: endpoint
            for name, endpoint in all_endpoints.items()
            if endpoint.portal == portal
        }

    @classmethod
    def get_javascript_required_endpoints(cls) -> Dict[str, CNHEndpoint]:
        """
        Get all endpoints that require JavaScript/Selenium.

        Returns:
            Dictionary of endpoints requiring JavaScript rendering
        """
        all_endpoints = cls.get_all_endpoints()
        return {
            name: endpoint
            for name, endpoint in all_endpoints.items()
            if endpoint.requires_javascript
        }

    @classmethod
    def get_direct_download_endpoints(cls) -> Dict[str, CNHEndpoint]:
        """
        Get all endpoints for direct file downloads.

        Returns:
            Dictionary of endpoints for direct downloads
        """
        all_endpoints = cls.get_all_endpoints()
        return {
            name: endpoint
            for name, endpoint in all_endpoints.items()
            if not endpoint.requires_javascript and "download" in name.lower()
        }


# Default timeout settings for different portal types
DEFAULT_TIMEOUTS = {
    CNHPortal.SIH: 60,  # SIH pages can be slow
    CNHPortal.PRODUCTION: 45,
    CNHPortal.MAPS: 90,  # Maps load many resources
    CNHPortal.OPEN_DATA: 30,
    CNHPortal.RONDAS: 45,
    CNHPortal.CONTRACTS: 45,
}


# Default rate limiting settings (seconds between requests)
DEFAULT_RATE_LIMITS = {
    CNHPortal.SIH: 3.0,
    CNHPortal.PRODUCTION: 2.0,
    CNHPortal.MAPS: 5.0,
    CNHPortal.OPEN_DATA: 1.0,
    CNHPortal.RONDAS: 2.0,
    CNHPortal.CONTRACTS: 2.0,
}
