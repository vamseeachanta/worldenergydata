# ABOUTME: County records reference provider
# ABOUTME: Provides information on how to access county clerk records

"""
County Reference Provider for Landman Module

Provides county clerk office information and record access guidance.
Contains a reference database of county offices with contact information,
online search availability, and instructions for accessing records.
"""

from typing import Any, Dict, List, Optional

from worldenergydata.modules.landman.exceptions import (
    CountyNotFoundError,
    StateNotSupportedError,
)
from worldenergydata.modules.landman.models import CountyClerkInfo
from worldenergydata.modules.landman.providers.base import BaseProvider


class CountyReferenceProvider(BaseProvider):
    """
    Provides county clerk office information and record access guidance.

    Contains reference data for county offices in major oil and gas producing
    states with contact information, online search URLs, and instructions
    for accessing land records.
    """

    PROVIDER_NAME = "county_reference"

    SUPPORTED_STATES = [
        "TX",
        "NM",
        "OK",
        "ND",
        "CO",
        "WY",
        "LA",
        "UT",
        "KS",
        "MT",
        "PA",
        "OH",
        "WV",
    ]

    COUNTY_DATA: Dict[str, Dict[str, Dict[str, Any]]] = {
        "TX": {
            "REEVES": {
                "office_name": "Reeves County Clerk",
                "address": "100 E 4th St",
                "city": "Pecos",
                "zip_code": "79772",
                "phone": "(432) 445-5467",
                "website": "https://www.co.reeves.tx.us/",
                "online_search_url": "https://countyclerk.co.reeves.tx.us/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
                "notes": "Oil and gas records available online from 1971",
            },
            "MIDLAND": {
                "office_name": "Midland County Clerk",
                "address": "200 W Wall St",
                "city": "Midland",
                "zip_code": "79701",
                "phone": "(432) 688-4500",
                "website": "https://www.co.midland.tx.us/",
                "online_search_url": "https://countyclerk.co.midland.tx.us/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
            },
            "LOVING": {
                "office_name": "Loving County Clerk",
                "address": "100 Bell St",
                "city": "Mentone",
                "zip_code": "79754",
                "phone": "(432) 377-2441",
                "website": None,
                "online_search_available": False,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
                "notes": "Smallest county in TX - records kept on-site only",
            },
            "MARTIN": {
                "office_name": "Martin County Clerk",
                "address": "301 N St Peter",
                "city": "Stanton",
                "zip_code": "79782",
                "phone": "(432) 756-3412",
                "online_search_available": False,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
            },
            "HOWARD": {
                "office_name": "Howard County Clerk",
                "address": "300 Main St",
                "city": "Big Spring",
                "zip_code": "79720",
                "phone": "(432) 264-2213",
                "website": "https://www.co.howard.tx.us/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
            },
            "ECTOR": {
                "office_name": "Ector County Clerk",
                "address": "300 N Grant Ave",
                "city": "Odessa",
                "zip_code": "79761",
                "phone": "(432) 498-4130",
                "website": "https://www.co.ector.tx.us/",
                "online_search_url": "https://countyclerk.co.ector.tx.us/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
            },
        },
        "NM": {
            "LEA": {
                "office_name": "Lea County Clerk",
                "address": "100 N Main St",
                "city": "Lovington",
                "zip_code": "88260",
                "phone": "(575) 396-8521",
                "website": "https://www.leacounty.net/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
                "notes": "Major Permian Basin county",
            },
            "EDDY": {
                "office_name": "Eddy County Clerk",
                "address": "101 W Greene St",
                "city": "Carlsbad",
                "zip_code": "88220",
                "phone": "(575) 885-3383",
                "website": "https://www.eddycounty.org/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
                "notes": "Delaware Basin county",
            },
            "CHAVES": {
                "office_name": "Chaves County Clerk",
                "address": "400 N Main St",
                "city": "Roswell",
                "zip_code": "88201",
                "phone": "(575) 624-6614",
                "website": "https://www.chavescounty.org/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
            },
        },
        "OK": {
            "OKLAHOMA": {
                "office_name": "Oklahoma County Clerk",
                "address": "320 Robert S Kerr Ave",
                "city": "Oklahoma City",
                "zip_code": "73102",
                "phone": "(405) 713-1513",
                "website": "https://www.oklahomacounty.org/",
                "online_search_url": "https://apps.oklahomacounty.org/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
            },
            "CANADIAN": {
                "office_name": "Canadian County Clerk",
                "address": "201 N Choctaw Ave",
                "city": "El Reno",
                "zip_code": "73036",
                "phone": "(405) 262-1070",
                "website": "https://www.canadiancounty.us/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
                "notes": "SCOOP play county",
            },
            "GRADY": {
                "office_name": "Grady County Clerk",
                "address": "326 W Choctaw Ave",
                "city": "Chickasha",
                "zip_code": "73018",
                "phone": "(405) 224-7446",
                "website": "https://www.gradycountyok.com/",
                "online_search_available": True,
                "office_hours": "8:30 AM - 4:30 PM, Mon-Fri",
                "notes": "SCOOP/STACK play county",
            },
        },
        "ND": {
            "MCKENZIE": {
                "office_name": "McKenzie County Recorder",
                "address": "201 5th St NW",
                "city": "Watford City",
                "zip_code": "58854",
                "phone": "(701) 444-3616",
                "website": "https://www.mckenziecounty.net/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 4:30 PM, Mon-Fri",
                "notes": "Highest oil producing county in ND - Bakken",
            },
            "WILLIAMS": {
                "office_name": "Williams County Recorder",
                "address": "206 E Broadway",
                "city": "Williston",
                "zip_code": "58801",
                "phone": "(701) 577-4550",
                "website": "https://www.williamsnd.com/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 4:30 PM, Mon-Fri",
                "notes": "Major Bakken county",
            },
            "MOUNTRAIL": {
                "office_name": "Mountrail County Recorder",
                "address": "101 Main St S",
                "city": "Stanley",
                "zip_code": "58784",
                "phone": "(701) 628-2915",
                "website": "https://www.mountrailcountynd.com/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 4:30 PM, Mon-Fri",
            },
            "DUNN": {
                "office_name": "Dunn County Recorder",
                "address": "205 Owens St",
                "city": "Manning",
                "zip_code": "58642",
                "phone": "(701) 573-4447",
                "website": "https://www.dunncountynd.org/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 4:30 PM, Mon-Fri",
            },
        },
        "CO": {
            "WELD": {
                "office_name": "Weld County Clerk and Recorder",
                "address": "1402 N 17th Ave",
                "city": "Greeley",
                "zip_code": "80631",
                "phone": "(970) 304-6530",
                "website": "https://www.weldgov.com/",
                "online_search_url": "https://recording.weldgov.com/",
                "online_search_available": True,
                "office_hours": "7:30 AM - 4:30 PM, Mon-Fri",
                "notes": "Highest oil producing county in CO - DJ Basin",
            },
            "ADAMS": {
                "office_name": "Adams County Clerk and Recorder",
                "address": "4430 S Adams County Pkwy",
                "city": "Brighton",
                "zip_code": "80601",
                "phone": "(720) 523-6020",
                "website": "https://www.adcogov.org/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 4:30 PM, Mon-Fri",
            },
            "ARAPAHOE": {
                "office_name": "Arapahoe County Clerk and Recorder",
                "address": "5334 S Prince St",
                "city": "Littleton",
                "zip_code": "80120",
                "phone": "(303) 795-4200",
                "website": "https://www.arapahoegov.com/",
                "online_search_available": True,
                "office_hours": "7:30 AM - 5:30 PM, Mon-Fri",
            },
        },
        "WY": {
            "CAMPBELL": {
                "office_name": "Campbell County Clerk",
                "address": "500 S Gillette Ave",
                "city": "Gillette",
                "zip_code": "82716",
                "phone": "(307) 682-7285",
                "website": "https://www.ccgov.net/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
                "notes": "Powder River Basin",
            },
            "CONVERSE": {
                "office_name": "Converse County Clerk",
                "address": "107 N 5th St",
                "city": "Douglas",
                "zip_code": "82633",
                "phone": "(307) 358-2244",
                "website": "https://www.conversecounty.org/",
                "online_search_available": True,
                "office_hours": "8:00 AM - 5:00 PM, Mon-Fri",
            },
        },
        "LA": {
            "CADDO": {
                "office_name": "Caddo Parish Clerk of Court",
                "address": "501 Texas St",
                "city": "Shreveport",
                "zip_code": "71101",
                "phone": "(318) 226-6780",
                "website": "https://www.caddoclerk.com/",
                "online_search_url": "https://www.caddoclerk.com/recordssearch/",
                "online_search_available": True,
                "office_hours": "8:30 AM - 5:00 PM, Mon-Fri",
                "notes": "Haynesville Shale",
            },
            "DESOTO": {
                "office_name": "DeSoto Parish Clerk of Court",
                "address": "101 Texas St",
                "city": "Mansfield",
                "zip_code": "71052",
                "phone": "(318) 872-3110",
                "website": "https://www.desotoparishclerk.org/",
                "online_search_available": True,
                "office_hours": "8:30 AM - 4:30 PM, Mon-Fri",
                "notes": "Haynesville Shale",
            },
        },
    }

    GENERAL_SEARCH_INSTRUCTIONS = """
## How to Search County Records

### Before You Search
1. Identify the county and state where the property is located
2. Gather the legal description (Section, Township, Range) if available
3. Know the names of parties (grantor/grantee) if searching by name
4. Determine the type of document you need (deed, lease, mortgage, etc.)

### In-Person Search
1. Visit the county clerk/recorder's office during business hours
2. Bring valid ID and payment method (many accept cash only)
3. Use the grantor/grantee indexes to locate documents
4. Request copies of needed documents (typical fees: $1-5 per page)

### Online Search Tips
1. Create an account if required (many systems require registration)
2. Start with the most specific search criteria
3. Use wildcard characters (* or %) for partial name matches
4. Check multiple spelling variations of names
5. Note document numbers for ordering certified copies

### Document Types to Search
- **Deeds**: Transfer of ownership (warranty, quitclaim, special warranty)
- **Mineral Deeds**: Transfer of mineral rights
- **Leases**: Oil and gas leases (look for memorandums)
- **Assignments**: Transfer of lease interests
- **Releases**: Release of liens or lease termination
- **Mortgages/Deeds of Trust**: Secured interests
- **Rights of Way**: Pipeline and surface easements
- **Plats/Maps**: Subdivision and survey maps

### Building a Chain of Title
1. Start with the current owner and work backwards
2. Trace the surface and mineral estates separately
3. Note any reservations or exceptions in deeds
4. Check for unreleased liens or mortgages
5. Verify legal descriptions match throughout the chain
"""

    def __init__(self, **kwargs) -> None:
        """Initialize County Reference provider."""
        super().__init__(**kwargs)

    def get_supported_states(self) -> List[str]:
        """Get list of supported state codes."""
        return self.SUPPORTED_STATES.copy()

    def get_counties_for_state(self, state: str) -> List[str]:
        """
        Get list of counties with reference data for a state.

        Args:
            state: Two-letter state code

        Returns:
            List of county names
        """
        state_upper = state.upper()
        if state_upper not in self.COUNTY_DATA:
            return []
        return list(self.COUNTY_DATA[state_upper].keys())

    def get_county_clerk_info(self, state: str, county: str) -> CountyClerkInfo:
        """
        Get county clerk office information.

        Args:
            state: Two-letter state code
            county: County name

        Returns:
            CountyClerkInfo with office details

        Raises:
            StateNotSupportedError: If state not in database
            CountyNotFoundError: If county not in database
        """
        state_upper = state.upper()
        county_upper = county.upper().replace(" COUNTY", "").replace(" PARISH", "")

        if state_upper not in self.COUNTY_DATA:
            raise StateNotSupportedError(
                state=state,
                provider=self.PROVIDER_NAME,
                supported_states=list(self.COUNTY_DATA.keys()),
            )

        state_data = self.COUNTY_DATA[state_upper]

        if county_upper not in state_data:
            matching = [c for c in state_data.keys() if county_upper in c]
            if not matching:
                raise CountyNotFoundError(county=county, state=state)
            county_upper = matching[0]

        county_data = state_data[county_upper]

        return CountyClerkInfo(
            state=state_upper,
            county=county_upper,
            office_name=county_data.get("office_name"),
            address=county_data.get("address"),
            city=county_data.get("city"),
            zip_code=county_data.get("zip_code"),
            phone=county_data.get("phone"),
            fax=county_data.get("fax"),
            email=county_data.get("email"),
            website=county_data.get("website"),
            online_search_url=county_data.get("online_search_url"),
            online_search_available=county_data.get("online_search_available", False),
            fee_schedule_url=county_data.get("fee_schedule_url"),
            recording_requirements=county_data.get("recording_requirements"),
            office_hours=county_data.get("office_hours"),
            notes=county_data.get("notes"),
        )

    def get_search_instructions(self, state: str, county: str) -> str:
        """
        Get search instructions for a specific county.

        Args:
            state: Two-letter state code
            county: County name

        Returns:
            Markdown-formatted search instructions
        """
        try:
            info = self.get_county_clerk_info(state, county)
        except (StateNotSupportedError, CountyNotFoundError):
            return self.GENERAL_SEARCH_INSTRUCTIONS

        instructions = [
            f"# Record Search Instructions for {info.county} County, {info.state}"
        ]
        instructions.append("")

        instructions.append("## County Clerk Office")
        instructions.append(f"**Office**: {info.office_name or 'County Clerk'}")
        if info.address:
            instructions.append(f"**Address**: {info.address}")
            if info.city and info.zip_code:
                instructions.append(
                    f"           {info.city}, {info.state} {info.zip_code}"
                )
        if info.phone:
            instructions.append(f"**Phone**: {info.phone}")
        if info.office_hours:
            instructions.append(f"**Hours**: {info.office_hours}")
        if info.website:
            instructions.append(f"**Website**: {info.website}")

        instructions.append("")

        if info.online_search_available:
            instructions.append("## Online Search")
            instructions.append(
                "Online record search is **AVAILABLE** for this county."
            )
            if info.online_search_url:
                instructions.append(f"**Search URL**: {info.online_search_url}")
            instructions.append("")
            instructions.append("### Online Search Tips")
            instructions.append("1. Some systems require free registration")
            instructions.append("2. Search by grantor (seller) or grantee (buyer) name")
            instructions.append(
                "3. Use legal description for property-specific searches"
            )
            instructions.append("4. Check date ranges carefully")
        else:
            instructions.append("## Online Search")
            instructions.append(
                "Online record search is **NOT AVAILABLE** for this county."
            )
            instructions.append(
                "Records must be searched in person at the county office."
            )
            instructions.append("")
            instructions.append("### In-Person Search Tips")
            instructions.append("1. Bring valid ID")
            instructions.append("2. Know the legal description or names to search")
            instructions.append("3. Bring payment (cash often preferred)")
            instructions.append("4. Allow sufficient time for research")

        if info.notes:
            instructions.append("")
            instructions.append("## Notes")
            instructions.append(info.notes)

        instructions.append("")
        instructions.append(self.GENERAL_SEARCH_INSTRUCTIONS)

        return "\n".join(instructions)

    def check_online_availability(self, state: str, county: str) -> bool:
        """
        Check if online search is available for a county.

        Args:
            state: Two-letter state code
            county: County name

        Returns:
            True if online search is available
        """
        try:
            info = self.get_county_clerk_info(state, county)
            return info.online_search_available
        except (StateNotSupportedError, CountyNotFoundError):
            return False

    def search_counties(
        self,
        state: Optional[str] = None,
        online_only: bool = False,
    ) -> List[CountyClerkInfo]:
        """
        Search for counties matching criteria.

        Args:
            state: Optional state code filter
            online_only: Only return counties with online search

        Returns:
            List of matching CountyClerkInfo objects
        """
        results = []

        states_to_search = [state.upper()] if state else list(self.COUNTY_DATA.keys())

        for state_code in states_to_search:
            if state_code not in self.COUNTY_DATA:
                continue

            for county_name, county_data in self.COUNTY_DATA[state_code].items():
                if online_only and not county_data.get(
                    "online_search_available", False
                ):
                    continue

                results.append(
                    CountyClerkInfo(
                        state=state_code,
                        county=county_name,
                        office_name=county_data.get("office_name"),
                        address=county_data.get("address"),
                        city=county_data.get("city"),
                        zip_code=county_data.get("zip_code"),
                        phone=county_data.get("phone"),
                        website=county_data.get("website"),
                        online_search_url=county_data.get("online_search_url"),
                        online_search_available=county_data.get(
                            "online_search_available", False
                        ),
                        office_hours=county_data.get("office_hours"),
                        notes=county_data.get("notes"),
                    )
                )

        return results

    def get_nearby_counties(self, state: str, county: str) -> List[str]:
        """
        Get list of nearby counties (same state).

        Args:
            state: Two-letter state code
            county: County name

        Returns:
            List of other county names in the same state
        """
        state_upper = state.upper()
        county_upper = county.upper().replace(" COUNTY", "").replace(" PARISH", "")

        if state_upper not in self.COUNTY_DATA:
            return []

        return [c for c in self.COUNTY_DATA[state_upper].keys() if c != county_upper]

    def health_check(self) -> bool:
        """
        Check if the provider is operational.

        Returns:
            True (reference data is always available)
        """
        return bool(self.COUNTY_DATA)
