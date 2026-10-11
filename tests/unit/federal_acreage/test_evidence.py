import pytest
from fixture_paths import FIXTURE

from worldenergydata.federal_acreage.evidence import evaluate
from worldenergydata.federal_acreage.models import FederalLandRecord
from worldenergydata.federal_acreage.provider import FixtureRecordProvider


def run(records=None):
    provider = FixtureRecordProvider(FIXTURE)
    original, sources = provider.records_for_tract(provider.tract)
    return evaluate(provider.tract, original if records is None else records, sources)


def record(aliquots=None, **changes):
    data = dict(
        record_serial="SYN-TEST",
        record_type="lease",
        record_status="active",
        area=dict(value=40, unit="acres"),
        aliquots=aliquots,
        source_id="fixture-mlrs-synthetic",
    )
    data.update(changes)
    return FederalLandRecord(**data)


def test_pilot_union_overlap_and_buckets():
    result = run()
    assert result.acreage.leased_acres.value == 200
    assert result.acreage.expired_or_nonleased_acres.value == 80
    assert result.acreage.federal_record_coverage_acres.value == 280
    assert sorted(e.kind for e in result.exceptions) == [
        "missing_geometry",
        "non_intersecting",
        "overlap",
    ]
    assert next(e for e in result.exceptions if e.kind == "overlap").acres == 40


def test_partial_intersection():
    result = run([record(["NE-NE", "NE-SE"], area=dict(value=80, unit="acres"))])
    assert result.records[0].intersect_acres.value == 40
    assert result.acreage.no_record_acres.value == 280


def test_non_intersecting():
    result = run([record(["NE-SE"])])
    assert result.exceptions[0].kind == "non_intersecting"
    assert result.screening_status == "evidence_blocked"


def test_missing_geometry():
    result = run([record()])
    assert result.exceptions[0].kind == "missing_geometry"
    assert result.records[0].intersect_acres.status == "unavailable"


def test_hectares_conversion():
    result = run([record(["NE-NE"], area=dict(value=16.1874, unit="hectares"))])
    assert result.records[0].area_acres.value == pytest.approx(40, abs=0.001)
    assert not result.exceptions


def test_unit_ambiguous():
    result = run([record(["NE-NE"], area=dict(value=100, unit="acres"))])
    assert result.exceptions[0].kind == "unit_ambiguous"
    assert result.acreage.leased_acres.status == "ambiguous"


@pytest.mark.parametrize("status", ["unknown", "pending"])
def test_stale_status(status):
    result = run([record(["NE-NE"], record_status=status)])
    assert result.exceptions[0].kind == "stale_status"
    assert result.acreage.leased_acres.value is None


def test_expired_by_data_date():
    result = run([record(["NE-NE"], expiration_date="2024-01-31")])
    assert result.exceptions[0].kind == "stale_status"
    assert result.acreage.leased_acres.status == "ambiguous"


def test_empty_records_blocked():
    result = run([])
    assert result.screening_status == "evidence_blocked"
    for value in result.acreage.model_dump().values():
        assert value["value"] is None
        assert value["status"] == "unavailable"


def test_clean_full_coverage_and_determinism():
    provider = FixtureRecordProvider(FIXTURE)
    records = [record(provider.tract.aliquots, area=dict(value=320, unit="acres"))]
    result = run(records)
    assert result.screening_status == "evidence_complete"
    assert result.acreage.no_record_acres.value == 0
    assert result == run(records)


def test_no_record_area_is_explicitly_derived():
    result = run()
    item = result.acreage.no_record_acres
    assert item.value == 40
    assert item.source_id == "derived-no-record"
    assert item.note == (
        "derived: tract gross area minus federal-record coverage; "
        "not a federal-record value"
    )
    source = next(s for s in result.sources if s.source_id == item.source_id)
    assert source.dataset == "Derived from tract-input and fixture-mlrs-synthetic"
    assert result.acreage.gross_area_acres.source_id == "tract-input"
    assert result.acreage.gross_area_acres.note is None
