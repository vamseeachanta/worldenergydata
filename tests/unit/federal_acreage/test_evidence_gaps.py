"""Independent hand calculations on the existing synthetic PLSS fixture.

BLM Specifications for Descriptions of Land (2017), Aliquot Parts, defines
nominal quarter-quarter subdivisions; the pilot fixes each cell at 40 acres.
Expected acreage below is cell count times 40, never evaluator-derived.
"""

import pytest
from fixture_paths import FIXTURE

from worldenergydata.federal_acreage.evidence import evaluate
from worldenergydata.federal_acreage.models import FederalLandRecord
from worldenergydata.federal_acreage.provider import FixtureRecordProvider
from worldenergydata.federal_acreage.report import render_html, write_outputs


def inputs():
    provider = FixtureRecordProvider(FIXTURE)
    _, sources = provider.records_for_tract(provider.tract)
    return provider.tract, sources


def lease(serial, aliquots, **changes):
    data = dict(
        record_serial=serial,
        record_type="lease",
        record_status="active",
        aliquots=aliquots,
        area={"value": 40, "unit": "acres"},
        source_id="fixture-mlrs-synthetic",
    )
    return FederalLandRecord(**(data | changes))


@pytest.mark.parametrize("geometry", [None, []])
def test_unlocated_lease_does_not_establish_lease_split(geometry):
    """One located cell gives 40 covered acres; an unlocated lease may overlap.

    Eight tract cells total 320 acres; 320 - 40 = 280 acres lack located
    records. Neither a complete leased union nor a nonleased union is known.
    """
    tract, sources = inputs()
    records = [lease("LOCATED", ["NE-NE"]), lease("UNLOCATED", geometry)]
    result = evaluate(tract, records, sources)
    assert result.acreage.federal_record_coverage_acres.value == 40
    assert result.acreage.no_record_acres.value == 280
    for item in (
        result.acreage.leased_acres,
        result.acreage.expired_or_nonleased_acres,
    ):
        assert item.status == "ambiguous"
        assert item.value is None
        assert item.note
    assert "missing_geometry" in {e.kind for e in result.exceptions}
    assert result.screening_status == "evidence_partial"


def test_parcel_record_does_not_establish_nonleased_acreage():
    """A 40-acre public parcel establishes coverage, not absence of a lease."""
    tract, sources = inputs()
    result = evaluate(
        tract, [lease("PARCEL", ["NE-NE"], record_type="parcel")], sources
    )
    assert result.acreage.federal_record_coverage_acres.value == 40
    assert result.acreage.leased_acres.status == "ambiguous"
    assert result.acreage.expired_or_nonleased_acres.status == "ambiguous"
    assert "lease_status_not_established" in {e.kind for e in result.exceptions}
    assert result.screening_status == "evidence_partial"


def test_conflicting_lease_status_counts_coverage_once():
    """Active and expired claims on the same cell: union=40; split unknown."""
    tract, sources = inputs()
    records = [
        lease("ACTIVE", ["NE-NE"]),
        lease("EXPIRED", ["NE-NE"], record_status="expired"),
    ]
    result = evaluate(tract, records, sources)
    assert result.acreage.federal_record_coverage_acres.value == 40
    assert result.acreage.leased_acres.status == "ambiguous"
    assert result.acreage.expired_or_nonleased_acres.status == "ambiguous"
    assert next(e for e in result.exceptions if e.kind == "overlap").acres == 40


def test_hectare_definition_independently_calculated():
    """NIST HB44 (2026), Appendix C, Units of Area: 1 acre=0.40468564224 ha.

    Exactly 0.40468564224 ha / 0.40468564224 ha per acre = 1 acre.
    Geometry is deliberately missing so this tests conversion alone.
    """
    tract, sources = inputs()
    result = evaluate(
        tract,
        [lease("METRIC", None, area={"value": 0.40468564224, "unit": "hectares"})],
        sources,
    )
    assert result.records[0].area_acres.value == pytest.approx(1)


def test_gap_outputs_preserve_markers_and_escape_input(tmp_path):
    """Unknown is null in JSON and visible in HTML; no title inference."""
    import json

    tract, sources = inputs()
    tract.label = '<script>alert("fixture")</script>'
    result = evaluate(
        tract, [lease("PARCEL", ["NE-NE"], record_type="parcel")], sources
    )
    outputs = write_outputs(result, tmp_path, "gaps")
    payload = json.loads(outputs["result_json"].read_text())
    html = outputs["report_html"].read_text()
    assert payload == result.model_dump(mode="json")
    assert payload["acreage"]["leased_acres"]["value"] is None
    assert "ambiguous" in html
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    assert result.title_chain_gap.statement in html
    assert html == render_html(result)


@pytest.mark.parametrize("area, ambiguous", [(40.5, False), (40.6, True)])
def test_pilot_tolerance_boundary(area, ambiguous):
    """README pilot policy: one cell=40 acres; 40.5-40=0.5 is permitted.

    40.6-40=0.6 exceeds the fixture-only 0.5-acre discrepancy threshold.
    This is not a cadastral acceptance limit.
    """
    tract, sources = inputs()
    result = evaluate(
        tract,
        [lease("BOUNDARY", ["NE-NE"], area={"value": area, "unit": "acres"})],
        sources,
    )
    assert (result.acreage.leased_acres.status == "ambiguous") == ambiguous
    assert result.acreage.federal_record_coverage_acres.value == 40


@pytest.mark.parametrize("label", ["../escape", "/escape", "nested/file"])
def test_report_label_cannot_escape_destination(tmp_path, label):
    """An output label cannot write beyond the caller-selected directory."""
    tract, sources = inputs()
    result = evaluate(tract, [], sources)
    with pytest.raises(ValueError, match="filename slug"):
        write_outputs(result, tmp_path, label)
    assert list(tmp_path.iterdir()) == []
