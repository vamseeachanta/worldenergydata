"""Tests for landman domain models."""

from datetime import date, datetime

from worldenergydata.landman.models import (
    CountyClerkInfo,
    FluidMineralLease,
    FluidMineralType,
    FluidMineralSearchResult,
    InterestType,
    LeaseRecord,
    LeaseStatus,
    MineralClaimType,
    MineralOwnershipRecord,
    MiningClaim,
    MiningClaimSearchResult,
    OwnerSearchResult,
    PermitInfo,
    PermitSearchResult,
    RecordType,
    SearchResult,
    TitleRecord,
    WellInfo,
    WellSearchResult,
    WellStatus,
)


class TestEnums:
    def test_well_status_values(self):
        assert WellStatus.ACTIVE.value == "active"
        assert WellStatus.PLUGGED.value == "plugged"

    def test_record_type_values(self):
        assert RecordType.DEED.value == "deed"
        assert RecordType.MINERAL_DEED.value == "mineral_deed"

    def test_mineral_claim_type_values(self):
        assert MineralClaimType.LODE.value == "lode"
        assert MineralClaimType.PLACER.value == "placer"

    def test_fluid_mineral_type_values(self):
        assert FluidMineralType.OIL_AND_GAS.value == "oil_and_gas"

    def test_lease_status_values(self):
        assert LeaseStatus.HBP.value == "held_by_production"
        assert LeaseStatus.POOLED.value == "pooled"

    def test_interest_type_values(self):
        assert InterestType.MINERAL.value == "mineral"
        assert InterestType.OVERRIDING.value == "overriding"
        assert InterestType.WORKING.value == "working"


class TestWellInfo:
    def test_required(self):
        w = WellInfo(api_number="4201312345")
        assert w.api_number == "4201312345"
        assert w.status == WellStatus.UNKNOWN

    def test_defaults(self):
        w = WellInfo(api_number="123")
        assert w.well_name is None
        assert w.operator is None
        assert w.latitude is None
        assert w.raw_data == {}

    def test_to_dict(self):
        w = WellInfo(
            api_number="42013",
            well_name="Test Well 1",
            status=WellStatus.ACTIVE,
            spud_date=date(2024, 1, 15),
        )
        d = w.to_dict()
        assert d["api_number"] == "42013"
        assert d["well_name"] == "Test Well 1"
        assert d["status"] == "active"
        assert d["spud_date"] == "2024-01-15"

    def test_to_dict_none_dates(self):
        w = WellInfo(api_number="123")
        d = w.to_dict()
        assert d["spud_date"] is None
        assert d["completion_date"] is None


class TestPermitInfo:
    def test_required(self):
        p = PermitInfo(permit_number="DP-001", state="TX")
        assert p.permit_number == "DP-001"
        assert p.state == "TX"

    def test_to_dict(self):
        p = PermitInfo(
            permit_number="DP-001",
            state="TX",
            issue_date=date(2024, 3, 1),
            expiration_date=date(2025, 3, 1),
        )
        d = p.to_dict()
        assert d["issue_date"] == "2024-03-01"
        assert d["expiration_date"] == "2025-03-01"


class TestMiningClaim:
    def test_required(self):
        m = MiningClaim(case_number="MC-001")
        assert m.claim_type == MineralClaimType.LODE

    def test_to_dict(self):
        m = MiningClaim(
            case_number="MC-001",
            claim_name="Golden Vein",
            claim_type=MineralClaimType.PLACER,
            location_date=date(2023, 6, 15),
        )
        d = m.to_dict()
        assert d["claim_type"] == "placer"
        assert d["location_date"] == "2023-06-15"


class TestFluidMineralLease:
    def test_required(self):
        f = FluidMineralLease(case_number="FML-001")
        assert f.lease_type == FluidMineralType.OIL_AND_GAS

    def test_to_dict(self):
        f = FluidMineralLease(
            case_number="FML-001",
            lessee="Company A",
            royalty_rate=0.125,
            effective_date=date(2024, 1, 1),
            expiration_date=date(2029, 1, 1),
        )
        d = f.to_dict()
        assert d["royalty_rate"] == 0.125
        assert d["effective_date"] == "2024-01-01"


class TestCountyClerkInfo:
    def test_required(self):
        c = CountyClerkInfo(state="TX", county="Harris")
        assert c.state == "TX"
        assert c.online_search_available is False

    def test_to_dict(self):
        c = CountyClerkInfo(
            state="TX",
            county="Harris",
            phone="713-555-1234",
            online_search_available=True,
        )
        d = c.to_dict()
        assert d["phone"] == "713-555-1234"
        assert d["online_search_available"] is True


class TestSearchResult:
    def test_basic(self):
        r = SearchResult(total_count=50, returned_count=10)
        assert r.total_count == 50
        assert r.page == 1
        assert r.page_size == 100
        assert r.has_more is False

    def test_with_results(self):
        r = SearchResult(
            total_count=100,
            returned_count=10,
            page=2,
            page_size=10,
            has_more=True,
            results=[{"id": 1}],
            source="texas_rrc",
        )
        assert r.page == 2
        assert r.has_more is True
        assert r.source == "texas_rrc"


class TestWellSearchResult:
    def test_with_wells(self):
        wells = [
            WellInfo(api_number="42013001", well_name="Well A"),
            WellInfo(api_number="42013002", well_name="Well B"),
        ]
        r = WellSearchResult(total_count=2, returned_count=0, wells=wells)
        assert r.returned_count == 2
        assert len(r.results) == 2
        assert r.results[0]["api_number"] == "42013001"


class TestPermitSearchResult:
    def test_with_permits(self):
        permits = [PermitInfo(permit_number="P-001", state="TX")]
        r = PermitSearchResult(total_count=1, returned_count=0, permits=permits)
        assert r.returned_count == 1


class TestMiningClaimSearchResult:
    def test_with_claims(self):
        claims = [MiningClaim(case_number="MC-001")]
        r = MiningClaimSearchResult(total_count=1, returned_count=0, claims=claims)
        assert r.returned_count == 1


class TestFluidMineralSearchResult:
    def test_with_leases(self):
        leases = [FluidMineralLease(case_number="FML-001")]
        r = FluidMineralSearchResult(total_count=1, returned_count=0, leases=leases)
        assert r.returned_count == 1


class TestMineralOwnershipRecord:
    def test_required(self):
        r = MineralOwnershipRecord(
            record_id="MO-001",
            state="TX",
            county="Harris",
            legal_description="SEC 12 T4N R5W",
            owner_name="John Smith",
        )
        assert r.interest_type == InterestType.MINERAL

    def test_to_dict(self):
        r = MineralOwnershipRecord(
            record_id="MO-001",
            state="TX",
            county="Harris",
            legal_description="SEC 12",
            owner_name="John Smith",
            mineral_interest_percent=50.0,
            effective_date=date(2020, 1, 1),
        )
        d = r.to_dict()
        assert d["mineral_interest_percent"] == 50.0
        assert d["effective_date"] == "2020-01-01"
        assert d["interest_type"] == "mineral"


class TestLeaseRecord:
    def test_required(self):
        l = LeaseRecord(
            lease_id="L-001",
            state="TX",
            county="Harris",
            legal_description="SEC 12",
            lessor="Owner A",
            lessee="Company B",
        )
        assert l.status == LeaseStatus.UNKNOWN

    def test_is_active(self):
        for status in [LeaseStatus.ACTIVE, LeaseStatus.HBP, LeaseStatus.POOLED, LeaseStatus.UNITIZED]:
            l = LeaseRecord(
                lease_id="L", state="TX", county="C",
                legal_description="S", lessor="O", lessee="L",
                status=status,
            )
            assert l.is_active() is True

    def test_is_not_active(self):
        for status in [LeaseStatus.EXPIRED, LeaseStatus.TERMINATED, LeaseStatus.UNKNOWN]:
            l = LeaseRecord(
                lease_id="L", state="TX", county="C",
                legal_description="S", lessor="O", lessee="L",
                status=status,
            )
            assert l.is_active() is False

    def test_is_expired_by_status(self):
        l = LeaseRecord(
            lease_id="L", state="TX", county="C",
            legal_description="S", lessor="O", lessee="L",
            status=LeaseStatus.EXPIRED,
        )
        assert l.is_expired() is True

    def test_is_expired_by_date(self):
        l = LeaseRecord(
            lease_id="L", state="TX", county="C",
            legal_description="S", lessor="O", lessee="L",
            status=LeaseStatus.ACTIVE,
            expiration_date=date(2020, 1, 1),
        )
        assert l.is_expired() is True

    def test_not_expired_hbp(self):
        l = LeaseRecord(
            lease_id="L", state="TX", county="C",
            legal_description="S", lessor="O", lessee="L",
            status=LeaseStatus.HBP,
            expiration_date=date(2020, 1, 1),
        )
        assert l.is_expired() is False

    def test_to_dict(self):
        l = LeaseRecord(
            lease_id="L-001", state="TX", county="Harris",
            legal_description="SEC 12", lessor="O", lessee="Co",
            royalty_rate=0.1875, status=LeaseStatus.HBP,
        )
        d = l.to_dict()
        assert d["royalty_rate"] == 0.1875
        assert d["status"] == "held_by_production"


class TestTitleRecord:
    def test_required(self):
        t = TitleRecord(
            document_id="D-001",
            record_type=RecordType.DEED,
            state="TX",
            county="Harris",
            legal_description="SEC 12",
            grantor="Seller",
            grantee="Buyer",
        )
        assert t.minerals_included is True

    def test_to_dict(self):
        t = TitleRecord(
            document_id="D-001",
            record_type=RecordType.MINERAL_DEED,
            state="TX",
            county="Harris",
            legal_description="SEC 12",
            grantor="Seller",
            grantee="Buyer",
            execution_date=date(2023, 6, 1),
        )
        d = t.to_dict()
        assert d["record_type"] == "mineral_deed"
        assert d["execution_date"] == "2023-06-01"


class TestOwnerSearchResult:
    def test_empty(self):
        r = OwnerSearchResult(
            search_id="S-001",
            search_criteria={"owner": "Smith"},
            state="TX",
        )
        assert r.total_records == 0
        assert r.has_results() is False
        assert r.has_errors() is False
        assert r.search_timestamp is not None

    def test_with_records(self):
        ownership = MineralOwnershipRecord(
            record_id="MO-1", state="TX", county="Harris",
            legal_description="S12", owner_name="Smith",
        )
        r = OwnerSearchResult(
            search_id="S-001",
            search_criteria={},
            state="TX",
            ownership_records=[ownership],
        )
        assert r.total_records == 1
        assert r.has_results() is True

    def test_add_records(self):
        r = OwnerSearchResult(
            search_id="S-001",
            search_criteria={},
            state="TX",
        )
        r.add_ownership_record(
            MineralOwnershipRecord(
                record_id="MO-1", state="TX", county="C",
                legal_description="S", owner_name="N",
            )
        )
        r.add_lease_record(
            LeaseRecord(
                lease_id="L-1", state="TX", county="C",
                legal_description="S", lessor="O", lessee="L",
            )
        )
        r.add_title_record(
            TitleRecord(
                document_id="D-1", record_type=RecordType.DEED,
                state="TX", county="C", legal_description="S",
                grantor="G", grantee="G2",
            )
        )
        assert r.total_records == 3

    def test_add_warning_and_error(self):
        r = OwnerSearchResult(
            search_id="S-001",
            search_criteria={},
            state="TX",
        )
        r.add_warning("Partial data")
        r.add_error("Timeout occurred")
        assert len(r.warnings) == 1
        assert r.has_errors() is True

    def test_to_dict(self):
        r = OwnerSearchResult(
            search_id="S-001",
            search_criteria={"owner": "Smith"},
            state="TX",
            county="Harris",
        )
        d = r.to_dict()
        assert d["search_id"] == "S-001"
        assert d["state"] == "TX"
        assert d["total_records"] == 0
