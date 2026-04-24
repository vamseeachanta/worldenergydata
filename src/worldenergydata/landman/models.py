# ABOUTME: Data models for Landman module
# ABOUTME: Defines dataclasses for wells, permits, county records, and search results

"""
Data Models for Landman Module

Defines dataclasses and Pydantic models for structured data representation
across all providers and operations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WellStatus(str, Enum):
    """Well status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PLUGGED = "plugged"
    DRILLING = "drilling"
    COMPLETED = "completed"
    PERMITTED = "permitted"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class RecordType(str, Enum):
    """County record type enumeration."""

    DEED = "deed"
    LEASE = "lease"
    MORTGAGE = "mortgage"
    ASSIGNMENT = "assignment"
    EASEMENT = "easement"
    RIGHT_OF_WAY = "right_of_way"
    MINERAL_DEED = "mineral_deed"
    ROYALTY_DEED = "royalty_deed"
    RELEASE = "release"
    OTHER = "other"


class MineralClaimType(str, Enum):
    """Mining claim type enumeration."""

    LODE = "lode"
    PLACER = "placer"
    MILL_SITE = "mill_site"
    TUNNEL_SITE = "tunnel_site"


class FluidMineralType(str, Enum):
    """Fluid mineral type enumeration."""

    OIL_AND_GAS = "oil_and_gas"
    GEOTHERMAL = "geothermal"
    OTHER = "other"


@dataclass
class WellInfo:
    """Well information data structure."""

    api_number: str
    well_name: Optional[str] = None
    operator: Optional[str] = None
    status: WellStatus = WellStatus.UNKNOWN
    well_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    county: Optional[str] = None
    state: Optional[str] = None
    section: Optional[str] = None
    township: Optional[str] = None
    range: Optional[str] = None
    spud_date: Optional[date] = None
    completion_date: Optional[date] = None
    total_depth: Optional[float] = None
    permit_number: Optional[str] = None
    field_name: Optional[str] = None
    formation: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "api_number": self.api_number,
            "well_name": self.well_name,
            "operator": self.operator,
            "status": self.status.value,
            "well_type": self.well_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "county": self.county,
            "state": self.state,
            "section": self.section,
            "township": self.township,
            "range": self.range,
            "spud_date": self.spud_date.isoformat() if self.spud_date else None,
            "completion_date": (
                self.completion_date.isoformat() if self.completion_date else None
            ),
            "total_depth": self.total_depth,
            "permit_number": self.permit_number,
            "field_name": self.field_name,
            "formation": self.formation,
        }


@dataclass
class PermitInfo:
    """Permit information data structure."""

    permit_number: str
    state: str
    county: Optional[str] = None
    operator: Optional[str] = None
    well_name: Optional[str] = None
    api_number: Optional[str] = None
    permit_type: Optional[str] = None
    issue_date: Optional[date] = None
    expiration_date: Optional[date] = None
    status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    section: Optional[str] = None
    township: Optional[str] = None
    range: Optional[str] = None
    proposed_depth: Optional[float] = None
    formation: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "permit_number": self.permit_number,
            "state": self.state,
            "county": self.county,
            "operator": self.operator,
            "well_name": self.well_name,
            "api_number": self.api_number,
            "permit_type": self.permit_type,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiration_date": (
                self.expiration_date.isoformat() if self.expiration_date else None
            ),
            "status": self.status,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "section": self.section,
            "township": self.township,
            "range": self.range,
            "proposed_depth": self.proposed_depth,
            "formation": self.formation,
        }


@dataclass
class MiningClaim:
    """Mining claim data structure."""

    case_number: str
    claim_name: Optional[str] = None
    claim_type: MineralClaimType = MineralClaimType.LODE
    claimant: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    township: Optional[str] = None
    range: Optional[str] = None
    section: Optional[str] = None
    meridian: Optional[str] = None
    location_date: Optional[date] = None
    status: Optional[str] = None
    acreage: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "case_number": self.case_number,
            "claim_name": self.claim_name,
            "claim_type": self.claim_type.value,
            "claimant": self.claimant,
            "state": self.state,
            "county": self.county,
            "township": self.township,
            "range": self.range,
            "section": self.section,
            "meridian": self.meridian,
            "location_date": (
                self.location_date.isoformat() if self.location_date else None
            ),
            "status": self.status,
            "acreage": self.acreage,
        }


@dataclass
class FluidMineralLease:
    """Fluid mineral lease data structure."""

    case_number: str
    lease_type: FluidMineralType = FluidMineralType.OIL_AND_GAS
    lessee: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    township: Optional[str] = None
    range: Optional[str] = None
    section: Optional[str] = None
    meridian: Optional[str] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    status: Optional[str] = None
    acreage: Optional[float] = None
    rental_rate: Optional[float] = None
    royalty_rate: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "case_number": self.case_number,
            "lease_type": self.lease_type.value,
            "lessee": self.lessee,
            "state": self.state,
            "county": self.county,
            "township": self.township,
            "range": self.range,
            "section": self.section,
            "meridian": self.meridian,
            "effective_date": (
                self.effective_date.isoformat() if self.effective_date else None
            ),
            "expiration_date": (
                self.expiration_date.isoformat() if self.expiration_date else None
            ),
            "status": self.status,
            "acreage": self.acreage,
            "rental_rate": self.rental_rate,
            "royalty_rate": self.royalty_rate,
        }


@dataclass
class CountyClerkInfo:
    """County clerk office information."""

    state: str
    county: str
    office_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    online_search_url: Optional[str] = None
    online_search_available: bool = False
    fee_schedule_url: Optional[str] = None
    recording_requirements: Optional[str] = None
    office_hours: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state": self.state,
            "county": self.county,
            "office_name": self.office_name,
            "address": self.address,
            "city": self.city,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "fax": self.fax,
            "email": self.email,
            "website": self.website,
            "online_search_url": self.online_search_url,
            "online_search_available": self.online_search_available,
            "fee_schedule_url": self.fee_schedule_url,
            "recording_requirements": self.recording_requirements,
            "office_hours": self.office_hours,
            "notes": self.notes,
        }


class SearchResult(BaseModel):
    """Generic search result model."""

    total_count: int = Field(description="Total number of results")
    returned_count: int = Field(description="Number of results returned")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=100, description="Results per page")
    has_more: bool = Field(default=False, description="Whether more results exist")
    results: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of results"
    )
    query_time_ms: Optional[float] = Field(
        default=None, description="Query execution time in milliseconds"
    )
    source: Optional[str] = Field(default=None, description="Data source identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Query timestamp"
    )


class WellSearchResult(SearchResult):
    """Well search result model."""

    wells: List[WellInfo] = Field(default_factory=list, description="List of wells")

    def __init__(self, **data):
        super().__init__(**data)
        self.results = [w.to_dict() for w in self.wells]
        self.returned_count = len(self.wells)


class PermitSearchResult(SearchResult):
    """Permit search result model."""

    permits: List[PermitInfo] = Field(
        default_factory=list, description="List of permits"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.results = [p.to_dict() for p in self.permits]
        self.returned_count = len(self.permits)


class MiningClaimSearchResult(SearchResult):
    """Mining claim search result model."""

    claims: List[MiningClaim] = Field(
        default_factory=list, description="List of mining claims"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.results = [c.to_dict() for c in self.claims]
        self.returned_count = len(self.claims)


class FluidMineralSearchResult(SearchResult):
    """Fluid mineral lease search result model."""

    leases: List[FluidMineralLease] = Field(
        default_factory=list, description="List of fluid mineral leases"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.results = [l.to_dict() for l in self.leases]  # noqa: E741
        self.returned_count = len(self.leases)


# Mineral Ownership Models for Landman Module


class LeaseStatus(str, Enum):
    """Status of an oil and gas lease."""

    ACTIVE = "active"
    EXPIRED = "expired"
    HBP = "held_by_production"  # Held by production
    TERMINATED = "terminated"
    POOLED = "pooled"
    UNITIZED = "unitized"
    PENDING = "pending"
    UNKNOWN = "unknown"


class InterestType(str, Enum):
    """Types of mineral interests."""

    MINERAL = "mineral"  # Full mineral ownership
    ROYALTY = "royalty"  # Non-participating royalty interest
    OVERRIDING = "overriding"  # Overriding royalty interest
    WORKING = "working"  # Working interest in lease
    NET_REVENUE = "net_revenue"  # Net revenue interest
    EXECUTIVE = "executive"  # Executive rights
    SURFACE = "surface"  # Surface rights only
    UNKNOWN = "unknown"


@dataclass
class MineralOwnershipRecord:
    """
    Mineral ownership record representing chain of title.

    Attributes:
        record_id: Unique identifier for the record
        state: 2-letter US state code
        county: County name
        legal_description: Section-Township-Range or other legal description
        owner_name: Current owner name
        owner_address: Owner mailing address
        interest_type: Type of mineral interest
        mineral_interest_percent: Percentage of mineral interest (0-100)
        net_mineral_acres: Net mineral acres owned
        gross_acres: Gross surface acres in tract
        effective_date: Date ownership became effective
        source_document: Document number establishing ownership
        grantor: Previous owner (seller)
        recorded_date: Date recorded in county records
        book: Recording book number
        page: Recording page number
        volume: Recording volume (if applicable)
        instrument_number: Instrument/document number
        notes: Additional notes
        provider: Data provider source
        retrieved_at: Timestamp when record was retrieved
        raw_data: Original raw data from provider
    """

    record_id: str
    state: str
    county: str
    legal_description: str
    owner_name: str
    owner_address: Optional[str] = None
    interest_type: InterestType = InterestType.MINERAL
    mineral_interest_percent: Optional[float] = None
    net_mineral_acres: Optional[float] = None
    gross_acres: Optional[float] = None
    effective_date: Optional[date] = None
    source_document: Optional[str] = None
    grantor: Optional[str] = None
    recorded_date: Optional[date] = None
    book: Optional[str] = None
    page: Optional[str] = None
    volume: Optional[str] = None
    instrument_number: Optional[str] = None
    notes: Optional[str] = None
    provider: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "record_id": self.record_id,
            "state": self.state,
            "county": self.county,
            "legal_description": self.legal_description,
            "owner_name": self.owner_name,
            "owner_address": self.owner_address,
            "interest_type": self.interest_type.value if self.interest_type else None,
            "mineral_interest_percent": self.mineral_interest_percent,
            "net_mineral_acres": self.net_mineral_acres,
            "gross_acres": self.gross_acres,
            "effective_date": (
                self.effective_date.isoformat() if self.effective_date else None
            ),
            "source_document": self.source_document,
            "grantor": self.grantor,
            "recorded_date": (
                self.recorded_date.isoformat() if self.recorded_date else None
            ),
            "book": self.book,
            "page": self.page,
            "volume": self.volume,
            "instrument_number": self.instrument_number,
            "notes": self.notes,
            "provider": self.provider,
            "retrieved_at": (
                self.retrieved_at.isoformat() if self.retrieved_at else None
            ),
        }


@dataclass
class LeaseRecord:
    """
    Oil and gas lease record.

    Attributes:
        lease_id: Unique identifier for the lease
        state: 2-letter US state code
        county: County name
        legal_description: Section-Township-Range or other legal description
        lessor: Mineral owner (landlord)
        lessee: Oil company (tenant)
        effective_date: Lease effective date
        expiration_date: Primary term expiration date
        primary_term_years: Primary term duration in years
        royalty_rate: Royalty rate as decimal (e.g., 0.1875 for 3/16)
        bonus_per_acre: Bonus payment per acre
        gross_acres: Gross acres covered
        status: Current lease status
        instrument_number: Recording instrument number
        book: Recording book number
        page: Recording page number
        recorded_date: Date recorded in county
        notes: Additional notes
        provider: Data provider source
        retrieved_at: Timestamp when record was retrieved
        raw_data: Original raw data from provider
    """

    lease_id: str
    state: str
    county: str
    legal_description: str
    lessor: str
    lessee: str
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    primary_term_years: Optional[int] = None
    royalty_rate: Optional[float] = None
    bonus_per_acre: Optional[float] = None
    gross_acres: Optional[float] = None
    status: LeaseStatus = LeaseStatus.UNKNOWN
    instrument_number: Optional[str] = None
    book: Optional[str] = None
    page: Optional[str] = None
    recorded_date: Optional[date] = None
    notes: Optional[str] = None
    provider: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "lease_id": self.lease_id,
            "state": self.state,
            "county": self.county,
            "legal_description": self.legal_description,
            "lessor": self.lessor,
            "lessee": self.lessee,
            "effective_date": (
                self.effective_date.isoformat() if self.effective_date else None
            ),
            "expiration_date": (
                self.expiration_date.isoformat() if self.expiration_date else None
            ),
            "primary_term_years": self.primary_term_years,
            "royalty_rate": self.royalty_rate,
            "bonus_per_acre": self.bonus_per_acre,
            "gross_acres": self.gross_acres,
            "status": self.status.value if self.status else None,
            "instrument_number": self.instrument_number,
            "book": self.book,
            "page": self.page,
            "recorded_date": (
                self.recorded_date.isoformat() if self.recorded_date else None
            ),
            "notes": self.notes,
            "provider": self.provider,
            "retrieved_at": (
                self.retrieved_at.isoformat() if self.retrieved_at else None
            ),
        }

    def is_active(self) -> bool:
        """Check if lease is currently active."""
        return self.status in (
            LeaseStatus.ACTIVE,
            LeaseStatus.HBP,
            LeaseStatus.POOLED,
            LeaseStatus.UNITIZED,
        )

    def is_expired(self) -> bool:
        """Check if lease has expired."""
        if self.status == LeaseStatus.EXPIRED:
            return True
        if self.expiration_date and self.expiration_date < date.today():
            if self.status != LeaseStatus.HBP:
                return True
        return False


@dataclass
class TitleRecord:
    """
    Title/deed record for chain of title analysis.

    Attributes:
        document_id: Unique identifier for the document
        record_type: Type of record (deed, lease, assignment, etc.)
        state: 2-letter US state code
        county: County name
        legal_description: Section-Township-Range or other legal description
        grantor: Seller/transferor name
        grantee: Buyer/transferee name
        execution_date: Date document was executed
        recorded_date: Date recorded in county
        consideration: Sale price or consideration
        instrument_number: Recording instrument number
        book: Recording book number
        page: Recording page number
        reservations: Mineral or other reservations
        minerals_included: Whether minerals are included
        notes: Additional notes
        provider: Data provider source
        retrieved_at: Timestamp when record was retrieved
        raw_data: Original raw data from provider
    """

    document_id: str
    record_type: RecordType
    state: str
    county: str
    legal_description: str
    grantor: str
    grantee: str
    execution_date: Optional[date] = None
    recorded_date: Optional[date] = None
    consideration: Optional[float] = None
    instrument_number: Optional[str] = None
    book: Optional[str] = None
    page: Optional[str] = None
    reservations: Optional[str] = None
    minerals_included: bool = True
    notes: Optional[str] = None
    provider: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "document_id": self.document_id,
            "record_type": self.record_type.value if self.record_type else None,
            "state": self.state,
            "county": self.county,
            "legal_description": self.legal_description,
            "grantor": self.grantor,
            "grantee": self.grantee,
            "execution_date": (
                self.execution_date.isoformat() if self.execution_date else None
            ),
            "recorded_date": (
                self.recorded_date.isoformat() if self.recorded_date else None
            ),
            "consideration": self.consideration,
            "instrument_number": self.instrument_number,
            "book": self.book,
            "page": self.page,
            "reservations": self.reservations,
            "minerals_included": self.minerals_included,
            "notes": self.notes,
            "provider": self.provider,
            "retrieved_at": (
                self.retrieved_at.isoformat() if self.retrieved_at else None
            ),
        }


@dataclass
class OwnerSearchResult:
    """
    Aggregated search result for owner/property searches.

    Attributes:
        search_id: Unique identifier for the search
        search_criteria: Dictionary of search criteria used
        state: State searched
        county: County searched
        owner_name: Owner name searched (if applicable)
        legal_description: Legal description searched (if applicable)
        ownership_records: List of ownership records found
        lease_records: List of lease records found
        title_records: List of title/deed records found
        total_records: Total number of records found
        search_timestamp: When the search was performed
        provider: Data provider used
        search_duration_ms: Search duration in milliseconds
        has_more_results: Whether more results are available
        warnings: Any warnings from the search
        errors: Any errors encountered
    """

    search_id: str
    search_criteria: Dict[str, Any]
    state: str
    county: Optional[str] = None
    owner_name: Optional[str] = None
    legal_description: Optional[str] = None
    ownership_records: List[MineralOwnershipRecord] = field(default_factory=list)
    lease_records: List[LeaseRecord] = field(default_factory=list)
    title_records: List[TitleRecord] = field(default_factory=list)
    total_records: int = 0
    search_timestamp: Optional[datetime] = None
    provider: Optional[str] = None
    search_duration_ms: Optional[int] = None
    has_more_results: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate total records after initialization."""
        self.total_records = (
            len(self.ownership_records)
            + len(self.lease_records)
            + len(self.title_records)
        )
        if not self.search_timestamp:
            self.search_timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "search_id": self.search_id,
            "search_criteria": self.search_criteria,
            "state": self.state,
            "county": self.county,
            "owner_name": self.owner_name,
            "legal_description": self.legal_description,
            "ownership_records": [r.to_dict() for r in self.ownership_records],
            "lease_records": [r.to_dict() for r in self.lease_records],
            "title_records": [r.to_dict() for r in self.title_records],
            "total_records": self.total_records,
            "search_timestamp": (
                self.search_timestamp.isoformat() if self.search_timestamp else None
            ),
            "provider": self.provider,
            "search_duration_ms": self.search_duration_ms,
            "has_more_results": self.has_more_results,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def has_results(self) -> bool:
        """Check if search returned any results."""
        return self.total_records > 0

    def has_errors(self) -> bool:
        """Check if search encountered errors."""
        return len(self.errors) > 0

    def add_ownership_record(self, record: MineralOwnershipRecord) -> None:
        """Add an ownership record to results."""
        self.ownership_records.append(record)
        self.total_records += 1

    def add_lease_record(self, record: LeaseRecord) -> None:
        """Add a lease record to results."""
        self.lease_records.append(record)
        self.total_records += 1

    def add_title_record(self, record: TitleRecord) -> None:
        """Add a title record to results."""
        self.title_records.append(record)
        self.total_records += 1

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
