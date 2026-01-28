# ABOUTME: BLM MLRS provider for federal land mineral records
# ABOUTME: Queries Bureau of Land Management Mineral & Land Records System

"""
BLM Provider for Landman Module

Queries Bureau of Land Management (BLM) Mineral and Land Records System (MLRS)
for federal land records including mining claims, fluid mineral leases, and
land patents.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from worldenergydata.modules.landman.exceptions import (
    ParsingError,
    RecordNotFoundError,
    StateNotSupportedError,
)
from worldenergydata.modules.landman.models import (
    FluidMineralLease,
    FluidMineralSearchResult,
    FluidMineralType,
    MineralClaimType,
    MiningClaim,
    MiningClaimSearchResult,
)
from worldenergydata.modules.landman.providers.base import BaseProvider


class BLMProvider(BaseProvider):
    """
    Provider for BLM federal land records.

    Queries the Bureau of Land Management Mineral and Land Records System
    (MLRS) for mining claims, fluid mineral leases, and federal land patents.
    """

    PROVIDER_NAME = "blm"
    BASE_URL = "https://reports.blm.gov/"
    MLRS_URL = "https://mlrs.blm.gov/"
    LR2000_URL = "https://www.blm.gov/lr2000/"

    SUPPORTED_STATES = [
        "AK",  # Alaska
        "AZ",  # Arizona
        "CA",  # California
        "CO",  # Colorado
        "ID",  # Idaho
        "MT",  # Montana
        "NV",  # Nevada
        "NM",  # New Mexico
        "OR",  # Oregon
        "UT",  # Utah
        "WA",  # Washington
        "WY",  # Wyoming
    ]

    MERIDIANS = {
        "AK": ["Copper River", "Fairbanks", "Seward", "Umiat", "Kateel River"],
        "AZ": ["Gila and Salt River", "Navajo"],
        "CA": [
            "Humboldt",
            "Mount Diablo",
            "San Bernardino",
        ],
        "CO": [
            "Sixth Principal",
            "New Mexico Principal",
            "Ute",
        ],
        "ID": ["Boise"],
        "MT": ["Principal"],
        "NV": ["Mount Diablo"],
        "NM": ["New Mexico Principal"],
        "OR": ["Willamette"],
        "UT": ["Salt Lake", "Uintah"],
        "WA": ["Willamette"],
        "WY": ["Sixth Principal", "Wind River"],
    }

    CLAIM_STATUS_CODES = {
        "AC": "Active",
        "CL": "Closed",
        "VO": "Voided",
        "AB": "Abandoned",
        "PT": "Patented",
        "RE": "Relinquished",
        "CO": "Contested",
    }

    def __init__(self, **kwargs) -> None:
        """Initialize BLM provider."""
        super().__init__(**kwargs)

    def _validate_state(self, state: str) -> str:
        """
        Validate state code.

        Args:
            state: Two-letter state code

        Returns:
            Validated uppercase state code

        Raises:
            StateNotSupportedError: If state is not supported
        """
        state_upper = state.upper()
        if state_upper not in self.SUPPORTED_STATES:
            raise StateNotSupportedError(
                state=state,
                provider=self.PROVIDER_NAME,
                supported_states=self.SUPPORTED_STATES,
            )
        return state_upper

    def get_supported_states(self) -> List[str]:
        """Get list of supported state codes."""
        return self.SUPPORTED_STATES.copy()

    def get_meridians(self, state: str) -> List[str]:
        """
        Get available meridians for a state.

        Args:
            state: Two-letter state code

        Returns:
            List of meridian names
        """
        state_upper = self._validate_state(state)
        return self.MERIDIANS.get(state_upper, [])

    def search_mining_claims(
        self,
        state: str,
        county: Optional[str] = None,
        township: Optional[str] = None,
        range_: Optional[str] = None,
        section: Optional[str] = None,
        meridian: Optional[str] = None,
        claim_type: Optional[MineralClaimType] = None,
        status: Optional[str] = None,
        claimant: Optional[str] = None,
        limit: int = 100,
    ) -> MiningClaimSearchResult:
        """
        Search for mining claims on federal land.

        Args:
            state: Two-letter state code
            county: Optional county name
            township: Optional township
            range_: Optional range
            section: Optional section
            meridian: Optional principal meridian
            claim_type: Optional claim type filter
            status: Optional status filter
            claimant: Optional claimant name filter
            limit: Maximum results to return

        Returns:
            MiningClaimSearchResult with matching claims
        """
        state_upper = self._validate_state(state)

        self.logger.info(f"Searching mining claims in {state_upper}")

        claims = self._query_mining_claims(
            state=state_upper,
            county=county,
            township=township,
            range_=range_,
            section=section,
            meridian=meridian,
            claim_type=claim_type,
            status=status,
            claimant=claimant,
            limit=limit,
        )

        return MiningClaimSearchResult(
            total_count=len(claims),
            returned_count=len(claims),
            claims=claims,
            source=f"{self.PROVIDER_NAME}:mining_claims:{state_upper}",
        )

    def _query_mining_claims(
        self,
        state: str,
        county: Optional[str],
        township: Optional[str],
        range_: Optional[str],
        section: Optional[str],
        meridian: Optional[str],
        claim_type: Optional[MineralClaimType],
        status: Optional[str],
        claimant: Optional[str],
        limit: int,
    ) -> List[MiningClaim]:
        """
        Query BLM for mining claims.

        This implementation provides a framework for BLM data access.
        Actual BLM LR2000 system requires authenticated access for bulk queries.
        """
        claims = []

        query_url = urljoin(self.LR2000_URL, "reports/serialsearch")

        params: Dict[str, Any] = {
            "state": state,
            "format": "json",
            "limit": limit,
        }

        if county:
            params["county"] = county.upper()
        if township:
            params["twp"] = township
        if range_:
            params["rng"] = range_
        if section:
            params["sec"] = section
        if meridian:
            params["mer"] = meridian
        if claim_type:
            params["type"] = claim_type.value
        if status:
            params["status"] = status
        if claimant:
            params["claimant"] = claimant.upper()

        try:
            data = self._get_json(query_url, params=params)
            claims = self._parse_mining_claims(data, state)
        except Exception as e:
            self.logger.warning(
                f"BLM mining claims query returned empty results: {e}. "
                "Note: BLM LR2000 requires authentication for bulk data access."
            )

        return claims

    def _parse_mining_claims(
        self, data: Dict[str, Any], state: str
    ) -> List[MiningClaim]:
        """Parse BLM response into MiningClaim objects."""
        claims = []
        records = data.get("results", data.get("records", []))

        for record in records:
            case_number = record.get("case_nr") or record.get("serial_nr")
            if not case_number:
                continue

            claim_type_str = (record.get("claim_type") or "lode").lower()
            claim_type = self._map_claim_type(claim_type_str)

            status_code = record.get("status") or record.get("case_status")
            status = self.CLAIM_STATUS_CODES.get(status_code, status_code)

            claims.append(
                MiningClaim(
                    case_number=case_number,
                    claim_name=record.get("claim_name"),
                    claim_type=claim_type,
                    claimant=record.get("claimant") or record.get("name"),
                    state=state,
                    county=record.get("county"),
                    township=record.get("twp") or record.get("township"),
                    range=record.get("rng") or record.get("range"),
                    section=record.get("sec") or record.get("section"),
                    meridian=record.get("mer") or record.get("meridian"),
                    status=status,
                    acreage=record.get("acres") or record.get("acreage"),
                    raw_data=record,
                )
            )

        return claims

    def _map_claim_type(self, claim_type_str: str) -> MineralClaimType:
        """Map string to MineralClaimType enum."""
        type_map = {
            "lode": MineralClaimType.LODE,
            "placer": MineralClaimType.PLACER,
            "mill": MineralClaimType.MILL_SITE,
            "mill_site": MineralClaimType.MILL_SITE,
            "tunnel": MineralClaimType.TUNNEL_SITE,
            "tunnel_site": MineralClaimType.TUNNEL_SITE,
        }
        return type_map.get(claim_type_str.lower(), MineralClaimType.LODE)

    def search_fluid_minerals(
        self,
        state: str,
        county: Optional[str] = None,
        township: Optional[str] = None,
        range_: Optional[str] = None,
        section: Optional[str] = None,
        meridian: Optional[str] = None,
        lease_type: Optional[FluidMineralType] = None,
        lessee: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> FluidMineralSearchResult:
        """
        Search for fluid mineral leases on federal land.

        Args:
            state: Two-letter state code
            county: Optional county name
            township: Optional township
            range_: Optional range
            section: Optional section
            meridian: Optional principal meridian
            lease_type: Optional lease type filter
            lessee: Optional lessee name filter
            status: Optional status filter
            limit: Maximum results to return

        Returns:
            FluidMineralSearchResult with matching leases
        """
        state_upper = self._validate_state(state)

        self.logger.info(f"Searching fluid mineral leases in {state_upper}")

        leases = self._query_fluid_minerals(
            state=state_upper,
            county=county,
            township=township,
            range_=range_,
            section=section,
            meridian=meridian,
            lease_type=lease_type,
            lessee=lessee,
            status=status,
            limit=limit,
        )

        return FluidMineralSearchResult(
            total_count=len(leases),
            returned_count=len(leases),
            leases=leases,
            source=f"{self.PROVIDER_NAME}:fluid_minerals:{state_upper}",
        )

    def _query_fluid_minerals(
        self,
        state: str,
        county: Optional[str],
        township: Optional[str],
        range_: Optional[str],
        section: Optional[str],
        meridian: Optional[str],
        lease_type: Optional[FluidMineralType],
        lessee: Optional[str],
        status: Optional[str],
        limit: int,
    ) -> List[FluidMineralLease]:
        """
        Query BLM for fluid mineral leases.

        This implementation provides a framework for BLM data access.
        Actual BLM LR2000 system requires authenticated access for bulk queries.
        """
        leases = []

        query_url = urljoin(self.LR2000_URL, "reports/fluidminerals")

        params: Dict[str, Any] = {
            "state": state,
            "format": "json",
            "limit": limit,
        }

        if county:
            params["county"] = county.upper()
        if township:
            params["twp"] = township
        if range_:
            params["rng"] = range_
        if section:
            params["sec"] = section
        if meridian:
            params["mer"] = meridian
        if lease_type:
            params["type"] = lease_type.value
        if lessee:
            params["lessee"] = lessee.upper()
        if status:
            params["status"] = status

        try:
            data = self._get_json(query_url, params=params)
            leases = self._parse_fluid_minerals(data, state)
        except Exception as e:
            self.logger.warning(
                f"BLM fluid minerals query returned empty results: {e}. "
                "Note: BLM LR2000 requires authentication for bulk data access."
            )

        return leases

    def _parse_fluid_minerals(
        self, data: Dict[str, Any], state: str
    ) -> List[FluidMineralLease]:
        """Parse BLM response into FluidMineralLease objects."""
        leases = []
        records = data.get("results", data.get("records", []))

        for record in records:
            case_number = record.get("case_nr") or record.get("serial_nr")
            if not case_number:
                continue

            lease_type_str = (record.get("lease_type") or "oil_and_gas").lower()
            lease_type = self._map_fluid_type(lease_type_str)

            leases.append(
                FluidMineralLease(
                    case_number=case_number,
                    lease_type=lease_type,
                    lessee=record.get("lessee") or record.get("name"),
                    state=state,
                    county=record.get("county"),
                    township=record.get("twp") or record.get("township"),
                    range=record.get("rng") or record.get("range"),
                    section=record.get("sec") or record.get("section"),
                    meridian=record.get("mer") or record.get("meridian"),
                    status=record.get("status") or record.get("case_status"),
                    acreage=record.get("acres") or record.get("acreage"),
                    rental_rate=record.get("rental"),
                    royalty_rate=record.get("royalty"),
                    raw_data=record,
                )
            )

        return leases

    def _map_fluid_type(self, type_str: str) -> FluidMineralType:
        """Map string to FluidMineralType enum."""
        type_map = {
            "oil": FluidMineralType.OIL_AND_GAS,
            "gas": FluidMineralType.OIL_AND_GAS,
            "oil_and_gas": FluidMineralType.OIL_AND_GAS,
            "geothermal": FluidMineralType.GEOTHERMAL,
        }
        return type_map.get(type_str.lower(), FluidMineralType.OIL_AND_GAS)

    def get_case_detail(
        self,
        case_number: str,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed information for a specific case.

        Args:
            case_number: BLM case/serial number
            state: Optional state code

        Returns:
            Dictionary with case details

        Raises:
            RecordNotFoundError: If case not found
        """
        self.logger.info(f"Getting case detail for {case_number}")

        query_url = urljoin(self.LR2000_URL, f"reports/case/{case_number}")

        params = {"format": "json"}
        if state:
            params["state"] = state.upper()

        try:
            data = self._get_json(query_url, params=params, use_cache=False)
            if data and (data.get("case_nr") or data.get("results")):
                return data
        except Exception as e:
            self.logger.error(f"Case detail query failed: {e}")

        raise RecordNotFoundError(
            record_type="BLM Case",
            identifier=case_number,
        )

    def get_land_status(
        self,
        state: str,
        township: str,
        range_: str,
        section: str,
        meridian: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get land status for a legal description.

        Args:
            state: Two-letter state code
            township: Township
            range_: Range
            section: Section
            meridian: Optional principal meridian

        Returns:
            Dictionary with land status information
        """
        state_upper = self._validate_state(state)

        self.logger.info(
            f"Getting land status for T{township} R{range_} Sec{section}, {state_upper}"
        )

        query_url = urljoin(self.BASE_URL, "reports/landstatus")

        params = {
            "state": state_upper,
            "twp": township,
            "rng": range_,
            "sec": section,
            "format": "json",
        }

        if meridian:
            params["mer"] = meridian

        try:
            return self._get_json(query_url, params=params)
        except Exception as e:
            self.logger.warning(f"Land status query failed: {e}")
            return {
                "state": state_upper,
                "township": township,
                "range": range_,
                "section": section,
                "status": "unknown",
                "error": str(e),
            }

    def health_check(self) -> bool:
        """
        Check if the provider is operational.

        Tests connectivity to BLM websites.

        Returns:
            True if provider is healthy
        """
        try:
            response = self._make_request(self.BASE_URL, use_cache=False)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
