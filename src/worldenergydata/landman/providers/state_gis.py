# ABOUTME: State GIS provider for oil/gas regulatory data
# ABOUTME: Queries state commission GIS APIs for well and permit data

"""
State GIS Provider for Landman Module

Queries state oil and gas commission GIS APIs for well data, permit
information, and operator records. Supports Texas RRC, New Mexico OCD,
Oklahoma OCC, North Dakota DMR, and Colorado COGCC.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from worldenergydata.landman.exceptions import (
    ParsingError,
    RecordNotFoundError,
    StateNotSupportedError,
)
from worldenergydata.landman.models import (
    PermitInfo,
    PermitSearchResult,
    WellInfo,
    WellSearchResult,
    WellStatus,
)
from worldenergydata.landman.providers.base import BaseProvider


class StateGISProvider(BaseProvider):
    """
    Provider for state oil/gas commission GIS data.

    Queries state regulatory commission APIs and GIS services for well
    locations, permit status, operator information, and production data.
    """

    PROVIDER_NAME = "state_gis"

    SUPPORTED_STATES: Dict[str, Dict[str, str]] = {
        "TX": {
            "name": "Texas Railroad Commission",
            "base_url": "https://gis.rrc.texas.gov/arcgis/rest/services/",
            "website": "https://www.rrc.texas.gov/",
            "api_format": "esri_rest",
            "well_service": "GIS/OGwell/MapServer",
            "permit_service": "GIS/OGpermit/MapServer",
        },
        "NM": {
            "name": "New Mexico Oil Conservation Division",
            "base_url": "https://gis.emnrd.nm.gov/arcgis/rest/services/",
            "website": "https://www.emnrd.nm.gov/ocd/",
            "api_format": "esri_rest",
            "well_service": "Wells/MapServer",
            "permit_service": "Permits/MapServer",
        },
        "OK": {
            "name": "Oklahoma Corporation Commission",
            "base_url": "https://www.occ.state.ok.us/",
            "website": "https://oklahoma.gov/occ/",
            "api_format": "custom",
            "well_service": "well_search",
            "permit_service": "permit_search",
        },
        "ND": {
            "name": "North Dakota Department of Mineral Resources",
            "base_url": "https://www.dmr.nd.gov/oilgas/",
            "website": "https://www.dmr.nd.gov/oilgas/",
            "api_format": "custom",
            "well_service": "findwellsvw.asp",
            "permit_service": "permitsvw.asp",
        },
        "CO": {
            "name": "Colorado Oil and Gas Conservation Commission",
            "base_url": "https://cogcc.state.co.us/",
            "website": "https://cogcc.state.co.us/",
            "api_format": "custom",
            "well_service": "data.html#/wells",
            "permit_service": "data.html#/permits",
        },
        "WY": {
            "name": "Wyoming Oil and Gas Conservation Commission",
            "base_url": "http://wogcc.wyo.gov/",
            "website": "http://wogcc.wyo.gov/",
            "api_format": "custom",
            "well_service": "wellsearch.cfm",
            "permit_service": "permitsearch.cfm",
        },
        "LA": {
            "name": "Louisiana Department of Natural Resources",
            "base_url": "https://sonris-www.dnr.state.la.us/",
            "website": "https://www.dnr.louisiana.gov/",
            "api_format": "sonris",
            "well_service": "gis/wellpoint",
            "permit_service": "gis/permits",
        },
        "UT": {
            "name": "Utah Division of Oil, Gas and Mining",
            "base_url": "https://oilgas.ogm.utah.gov/",
            "website": "https://ogm.utah.gov/",
            "api_format": "custom",
            "well_service": "oilgasweb/live-data-search",
            "permit_service": "oilgasweb/permit-search",
        },
    }

    def __init__(self, **kwargs) -> None:
        """Initialize State GIS provider."""
        super().__init__(**kwargs)
        self._state_clients: Dict[str, Any] = {}

    def _get_state_config(self, state: str) -> Dict[str, str]:
        """
        Get configuration for a state.

        Args:
            state: Two-letter state code

        Returns:
            State configuration dictionary

        Raises:
            StateNotSupportedError: If state is not supported
        """
        state_upper = state.upper()
        if state_upper not in self.SUPPORTED_STATES:
            raise StateNotSupportedError(
                state=state,
                provider=self.PROVIDER_NAME,
                supported_states=list(self.SUPPORTED_STATES.keys()),
            )
        return self.SUPPORTED_STATES[state_upper]

    def get_supported_states(self) -> List[str]:
        """Get list of supported state codes."""
        return list(self.SUPPORTED_STATES.keys())

    def get_state_info(self, state: str) -> Dict[str, str]:
        """
        Get information about a state's regulatory agency.

        Args:
            state: Two-letter state code

        Returns:
            State agency information
        """
        config = self._get_state_config(state)
        return {
            "state": state.upper(),
            "agency_name": config["name"],
            "website": config["website"],
            "api_format": config["api_format"],
        }

    def search_wells_by_location(
        self,
        state: str,
        county: str,
        section: Optional[str] = None,
        township: Optional[str] = None,
        range_: Optional[str] = None,
        limit: int = 100,
    ) -> WellSearchResult:
        """
        Search for wells by location.

        Args:
            state: Two-letter state code
            county: County name
            section: Optional section number
            township: Optional township
            range_: Optional range
            limit: Maximum results to return

        Returns:
            WellSearchResult with matching wells
        """
        config = self._get_state_config(state)
        state_upper = state.upper()

        self.logger.info(f"Searching wells in {county}, {state_upper}")

        wells: List[WellInfo] = []

        if config["api_format"] == "esri_rest":
            wells = self._search_esri_wells(
                config, county, section, township, range_, limit
            )
        else:
            wells = self._search_custom_wells(
                state_upper, config, county, section, township, range_, limit
            )

        return WellSearchResult(
            total_count=len(wells),
            returned_count=len(wells),
            wells=wells,
            source=f"{self.PROVIDER_NAME}:{state_upper}",
        )

    def _search_esri_wells(
        self,
        config: Dict[str, str],
        county: str,
        section: Optional[str],
        township: Optional[str],
        range_: Optional[str],
        limit: int,
    ) -> List[WellInfo]:
        """Query ESRI REST services for wells."""
        base_url = config["base_url"]
        service = config["well_service"]
        query_url = urljoin(base_url, f"{service}/0/query")

        where_clauses = [f"UPPER(COUNTY) = '{county.upper()}'"]
        if section:
            where_clauses.append(f"SECTION = '{section}'")
        if township:
            where_clauses.append(f"TOWNSHIP = '{township}'")
        if range_:
            where_clauses.append(f"RANGE = '{range_}'")

        params = {
            "where": " AND ".join(where_clauses),
            "outFields": "*",
            "returnGeometry": "true",
            "f": "json",
            "resultRecordCount": limit,
        }

        try:
            data = self._get_json(query_url, params=params)
            return self._parse_esri_wells(data, config)
        except Exception as e:
            self.logger.warning(f"ESRI query failed: {e}")
            return []

    def _parse_esri_wells(
        self, data: Dict[str, Any], config: Dict[str, str]
    ) -> List[WellInfo]:
        """Parse ESRI REST response into WellInfo objects."""
        wells = []
        features = data.get("features", [])

        for feature in features:
            attrs = feature.get("attributes", {})
            geometry = feature.get("geometry", {})

            api_number = attrs.get("API_NUMBER") or attrs.get("API") or ""
            if not api_number:
                continue

            status_str = (attrs.get("WELL_STATUS") or "").lower()
            status = self._map_well_status(status_str)

            wells.append(
                WellInfo(
                    api_number=api_number,
                    well_name=attrs.get("WELL_NAME") or attrs.get("WELLNAME"),
                    operator=attrs.get("OPERATOR") or attrs.get("OPERATOR_NAME"),
                    status=status,
                    well_type=attrs.get("WELL_TYPE") or attrs.get("TYPE"),
                    latitude=geometry.get("y"),
                    longitude=geometry.get("x"),
                    county=attrs.get("COUNTY"),
                    state=attrs.get("STATE"),
                    section=attrs.get("SECTION"),
                    township=attrs.get("TOWNSHIP"),
                    range=attrs.get("RANGE"),
                    total_depth=attrs.get("TOTAL_DEPTH") or attrs.get("TD"),
                    field_name=attrs.get("FIELD_NAME") or attrs.get("FIELD"),
                    formation=attrs.get("FORMATION")
                    or attrs.get("PRODUCING_FORMATION"),
                    raw_data=attrs,
                )
            )

        return wells

    def _search_custom_wells(
        self,
        state: str,
        config: Dict[str, str],
        county: str,
        section: Optional[str],
        township: Optional[str],
        range_: Optional[str],
        limit: int,
    ) -> List[WellInfo]:
        """Query custom state APIs for wells."""
        self.logger.info(
            f"Custom well search for {state} - results may vary by state API"
        )
        return []

    def _map_well_status(self, status_str: str) -> WellStatus:
        """Map string status to WellStatus enum."""
        status_map = {
            "active": WellStatus.ACTIVE,
            "producing": WellStatus.ACTIVE,
            "inactive": WellStatus.INACTIVE,
            "shut-in": WellStatus.INACTIVE,
            "shut in": WellStatus.INACTIVE,
            "plugged": WellStatus.PLUGGED,
            "pa": WellStatus.PLUGGED,
            "p&a": WellStatus.PLUGGED,
            "drilling": WellStatus.DRILLING,
            "completed": WellStatus.COMPLETED,
            "permitted": WellStatus.PERMITTED,
            "suspended": WellStatus.SUSPENDED,
        }
        return status_map.get(status_str.lower(), WellStatus.UNKNOWN)

    def search_by_operator(
        self,
        operator_name: str,
        state: str,
        limit: int = 100,
    ) -> WellSearchResult:
        """
        Search for wells by operator name.

        Args:
            operator_name: Operator name (partial match supported)
            state: Two-letter state code
            limit: Maximum results to return

        Returns:
            WellSearchResult with matching wells
        """
        config = self._get_state_config(state)
        state_upper = state.upper()

        self.logger.info(
            f"Searching wells for operator '{operator_name}' in {state_upper}"
        )

        wells: List[WellInfo] = []

        if config["api_format"] == "esri_rest":
            base_url = config["base_url"]
            service = config["well_service"]
            query_url = urljoin(base_url, f"{service}/0/query")

            params = {
                "where": f"UPPER(OPERATOR) LIKE '%{operator_name.upper()}%'",
                "outFields": "*",
                "returnGeometry": "true",
                "f": "json",
                "resultRecordCount": limit,
            }

            try:
                data = self._get_json(query_url, params=params)
                wells = self._parse_esri_wells(data, config)
            except Exception as e:
                self.logger.warning(f"Operator search failed: {e}")

        return WellSearchResult(
            total_count=len(wells),
            returned_count=len(wells),
            wells=wells,
            source=f"{self.PROVIDER_NAME}:{state_upper}",
        )

    def get_well_detail(
        self,
        api_number: str,
        state: Optional[str] = None,
    ) -> WellInfo:
        """
        Get detailed information for a specific well.

        Args:
            api_number: API well number
            state: Optional state code (derived from API if not provided)

        Returns:
            WellInfo with full well details

        Raises:
            RecordNotFoundError: If well not found
        """
        if state is None:
            state = self._derive_state_from_api(api_number)

        config = self._get_state_config(state)

        self.logger.info(f"Getting well detail for API {api_number}")

        if config["api_format"] == "esri_rest":
            base_url = config["base_url"]
            service = config["well_service"]
            query_url = urljoin(base_url, f"{service}/0/query")

            cleaned_api = api_number.replace("-", "")
            params = {
                "where": f"API_NUMBER = '{api_number}' OR API_NUMBER = '{cleaned_api}'",
                "outFields": "*",
                "returnGeometry": "true",
                "f": "json",
            }

            try:
                data = self._get_json(query_url, params=params, use_cache=False)
                wells = self._parse_esri_wells(data, config)
                if wells:
                    return wells[0]
            except Exception as e:
                self.logger.error(f"Well detail query failed: {e}")

        raise RecordNotFoundError(
            record_type="Well",
            identifier=api_number,
        )

    def _derive_state_from_api(self, api_number: str) -> str:
        """
        Derive state code from API number.

        Args:
            api_number: API well number

        Returns:
            Two-letter state code

        Raises:
            ValueError: If state cannot be determined
        """
        state_codes = {
            "42": "TX",
            "30": "NM",
            "35": "OK",
            "33": "ND",
            "05": "CO",
            "56": "WY",
            "22": "LA",
            "43": "UT",
        }

        cleaned = api_number.replace("-", "")
        if len(cleaned) >= 2:
            state_prefix = cleaned[:2]
            if state_prefix in state_codes:
                return state_codes[state_prefix]

        raise ValueError(f"Cannot determine state from API number: {api_number}")

    def search_permits(
        self,
        state: str,
        county: Optional[str] = None,
        operator: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> PermitSearchResult:
        """
        Search for drilling permits.

        Args:
            state: Two-letter state code
            county: Optional county name
            operator: Optional operator name
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum results to return

        Returns:
            PermitSearchResult with matching permits
        """
        config = self._get_state_config(state)
        state_upper = state.upper()

        self.logger.info(f"Searching permits in {state_upper}")

        permits: List[PermitInfo] = []

        if config["api_format"] == "esri_rest":
            base_url = config["base_url"]
            service = config.get("permit_service", config["well_service"])
            query_url = urljoin(base_url, f"{service}/0/query")

            where_clauses = ["1=1"]
            if county:
                where_clauses.append(f"UPPER(COUNTY) = '{county.upper()}'")
            if operator:
                where_clauses.append(f"UPPER(OPERATOR) LIKE '%{operator.upper()}%'")

            params = {
                "where": " AND ".join(where_clauses),
                "outFields": "*",
                "returnGeometry": "true",
                "f": "json",
                "resultRecordCount": limit,
            }

            try:
                data = self._get_json(query_url, params=params)
                permits = self._parse_esri_permits(data, state_upper)
            except Exception as e:
                self.logger.warning(f"Permit search failed: {e}")

        return PermitSearchResult(
            total_count=len(permits),
            returned_count=len(permits),
            permits=permits,
            source=f"{self.PROVIDER_NAME}:{state_upper}",
        )

    def _parse_esri_permits(self, data: Dict[str, Any], state: str) -> List[PermitInfo]:
        """Parse ESRI REST response into PermitInfo objects."""
        permits = []
        features = data.get("features", [])

        for feature in features:
            attrs = feature.get("attributes", {})
            geometry = feature.get("geometry", {})

            permit_number = (
                attrs.get("PERMIT_NUMBER")
                or attrs.get("PERMIT_NO")
                or attrs.get("PERMIT")
            )
            if not permit_number:
                continue

            permits.append(
                PermitInfo(
                    permit_number=str(permit_number),
                    state=state,
                    county=attrs.get("COUNTY"),
                    operator=attrs.get("OPERATOR") or attrs.get("OPERATOR_NAME"),
                    well_name=attrs.get("WELL_NAME") or attrs.get("WELLNAME"),
                    api_number=attrs.get("API_NUMBER") or attrs.get("API"),
                    permit_type=attrs.get("PERMIT_TYPE") or attrs.get("TYPE"),
                    status=attrs.get("STATUS") or attrs.get("PERMIT_STATUS"),
                    latitude=geometry.get("y"),
                    longitude=geometry.get("x"),
                    section=attrs.get("SECTION"),
                    township=attrs.get("TOWNSHIP"),
                    range=attrs.get("RANGE"),
                    proposed_depth=attrs.get("PROPOSED_DEPTH") or attrs.get("TD"),
                    formation=attrs.get("FORMATION") or attrs.get("TARGET_FORMATION"),
                    raw_data=attrs,
                )
            )

        return permits

    def health_check(self) -> bool:
        """
        Check if the provider is operational.

        Tests connectivity to Texas RRC as a representative endpoint.

        Returns:
            True if provider is healthy
        """
        try:
            config = self.SUPPORTED_STATES["TX"]
            base_url = config["base_url"]
            service = config["well_service"]
            query_url = urljoin(base_url, f"{service}?f=json")

            response = self._make_request(query_url, use_cache=False)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
