"""Entity readers backed by the rate-limited, cached HTTP transport."""

from typing import Any, Dict, List, Optional

from .transport import SodirTransport


class SodirAPIClient(SodirTransport):
    """HTTP client retaining the original public entity-reader interface."""

    def _setup_headers(
        self, custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Setup default and custom HTTP headers.

        Args:
            custom_headers: Optional custom headers to add

        Returns:
            Combined headers dictionary
        """
        headers = {
            "User-Agent": "WorldEnergyData SODIR Client/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }

        if custom_headers:
            headers.update(custom_headers)

        return headers

    def query_entity(self, entity: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """Read bounded field, wellbore or production ArcGIS pages.

        The base address must equal https://factmaps.sodir.no/api/rest exactly.

        Uses observed metadata and a capped transport; legacy methods retain
        their existing response contract. See feature_service.query_entity.
        """
        from .feature_service import query_entity

        records: List[Dict[str, Any]] = query_entity(self, entity, **kwargs)
        return records

    # SODIR-specific endpoint methods

    def get_blocks(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Get block data from SODIR API.

        Endpoint: /api/rest/1001 - Norwegian Continental Shelf blocks

        Args:
            **kwargs: Query parameters such as:
                - startdate: Filter by start date (YYYY-MM-DD)
                - enddate: Filter by end date (YYYY-MM-DD)

        Returns:
            List of block data dictionaries
        """
        response = self.get("/1001", params=kwargs)
        return response.get("data", []) if response else []

    def get_wellbores(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Get wellbore data from SODIR API.

        Endpoint: /api/rest/5000 - Wellbore drilling and completion

        Args:
            **kwargs: Query parameters such as:
                - wellboreStatus: Filter by status (DRILLING, COMPLETED, ABANDONED)
                - npdidBlock: Filter by block ID

        Returns:
            List of wellbore data dictionaries
        """
        response = self.get("/5000", params=kwargs)
        return response.get("data", []) if response else []

    def get_fields(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Get field data from SODIR API.

        Endpoint: /api/rest/7100 - Field information and reserves

        Args:
            **kwargs: Query parameters such as:
                - fieldStatus: Filter by status
                - operator: Filter by operator company

        Returns:
            List of field data dictionaries
        """
        response = self.get("/7100", params=kwargs)
        return response.get("data", []) if response else []

    def get_discoveries(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Get discovery data from SODIR API.

        Endpoint: /api/rest/7000 - Discovery information

        Args:
            **kwargs: Query parameters such as:
                - discoveryYear: Filter by discovery year
                - hydrocarbon: Filter by type (OIL, GAS, OIL/GAS)

        Returns:
            List of discovery data dictionaries
        """
        response = self.get("/7000", params=kwargs)
        return response.get("data", []) if response else []

    def get_surveys(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Get survey data from SODIR API.

        Endpoint: /api/rest/4000 - Seismic surveys

        Args:
            **kwargs: Query parameters such as:
                - surveyType: Type of survey (2D_SEISMIC, 3D_SEISMIC)
                - acquisitionYear: Filter by year

        Returns:
            List of survey data dictionaries
        """
        response = self.get("/4000", params=kwargs)
        return response.get("data", []) if response else []
