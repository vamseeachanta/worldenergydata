"""Independent counts for the field comparison requested by issue 776.

Fixtures are synthetic. Expected counts are enumerated in each test; no
engineering coefficients, depth cutoffs or lifecycle acceptance limits apply.
The classification basis is issue 776 (2026) and recommendation._DRY_TREE.
"""

import hashlib
import json

import pytest

from worldenergydata.field_development import ConceptType, FieldConcept
from worldenergydata.field_development import development_comparison as comparison
from worldenergydata.field_development.portfolio_matched import (
    CrosswalkMatch,
    PortfolioRow,
)


def field(name, actual=None, region=None, block="", depth=None):
    return PortfolioRow(
        concept=FieldConcept(
            name=name, concept_type=actual, region=region, water_depth_m=depth
        ),
        match=CrosswalkMatch(name, block, block, actual, None),
        recommended=ConceptType.FPSO,
    )


@pytest.mark.parametrize(
    "actual,expected",
    [
        (ConceptType.FIXED_JACKET, "dry"),
        (ConceptType.COMPLIANT_TOWER, "dry"),
        (ConceptType.TLP, "dry"),
        (ConceptType.SPAR, "dry"),
        (ConceptType.NUI, "dry"),
        (ConceptType.SEMISUB_FPS, "wet"),
        (ConceptType.FPSO, "wet"),
        (ConceptType.FLNG, "wet"),
        (ConceptType.SUBSEA_TIEBACK, "wet"),
        (ConceptType.SUBSEA_TO_SHORE, "wet"),
        (None, "other"),
    ],
)
def test_classification_uses_actual_not_recommendation(actual, expected):
    """Issue 776 enumerates these concepts; the recommendation is always FPSO."""
    record = comparison.canonical_fields([field("sample", actual)])[0]
    assert record["tree_type"] == expected
    assert record["concept_type"] == (actual.value if actual else None)


def test_counts_and_coverage_by_region():
    """Hand count: north = one dry + one wet + one unknown = three.

    North typed = two, untyped = one, coverage = two / three. South has one
    unknown, hence zero typed / one field. Global = four, typed = two / four.
    """
    rows = [
        field("sample-a", ConceptType.TLP, "North"),
        field("sample-b", ConceptType.SUBSEA_TIEBACK, "North"),
        field("sample-c", None, "North"),
        field("sample-d", None, "South"),
    ]
    report = comparison.compare_portfolio(rows)
    north, south = report["regions"]
    assert north == {
        "region": "North",
        "dry": 1,
        "wet": 1,
        "other": 1,
        "total": 3,
        "typed": 2,
        "untyped": 1,
        "coverage_fraction": pytest.approx(2 / 3),
    }
    assert south["total"] == south["other"] == south["untyped"] == 1
    assert south["typed"] == south["coverage_fraction"] == 0
    assert report["totals"] == {
        "dry": 1,
        "wet": 1,
        "other": 2,
        "total": 4,
        "typed": 2,
        "untyped": 2,
        "coverage_fraction": 0.5,
    }
    assert report["lifecycle_metrics"]["status"] == "NOT_EVALUATED"
    assert "matched" in report["universe"].lower()


@pytest.mark.parametrize("region", [None, "US", " Gulf of Mexico "])
def test_recognized_bsee_block_supplies_gulf_region(region):
    """GC is in subseaiq.AREA_ABBR; it supplies basin evidence beyond country."""
    record = comparison.canonical_fields([field("sample", region=region, block="GC1")])[
        0
    ]
    assert record["region"] == "US Gulf of Mexico"
    assert record["region_basis"] == "bsee_block_code"


@pytest.mark.parametrize("block", ["", "XX1", "not-a-block"])
def test_us_country_without_gulf_block_is_not_promoted_to_gulf(block):
    record = comparison.canonical_fields([field("sample", region="US", block=block)])[0]
    assert record["region"] == "US"
    assert record["region_basis"] == "field_concept.region"


def test_contradictory_country_and_bsee_region_are_rejected():
    with pytest.raises(ValueError, match="conflicting region"):
        comparison.canonical_fields([field("sample", region="Norway", block="GC1")])


def test_unknown_region_retained_and_depth_is_not_filled():
    """Two fields remain two fields, even with missing geography and depth."""
    records = comparison.canonical_fields(
        [field("sample-a", region="  "), field("sample-b", depth=0)]
    )
    assert all(r["region"] == "Unknown region" for r in records)
    assert all(r["region_basis"] == "missing" for r in records)
    assert records[0]["water_depth_m"] is None
    assert records[1]["water_depth_m"] == 0


@pytest.mark.parametrize("duplicate", ["sample", " SAMPLE "])
def test_duplicate_field_names_are_rejected(duplicate):
    with pytest.raises(ValueError, match="duplicate field"):
        comparison.canonical_fields([field("sample"), field(duplicate)])


def test_blank_identity_is_rejected():
    row = field("sample")
    row.match = CrosswalkMatch(" ", "", "", None, None)
    with pytest.raises(ValueError, match="field name"):
        comparison.canonical_fields([row])


def test_crosswalk_and_concept_identity_must_agree():
    row = field("sample")
    row.concept.name = "different"
    with pytest.raises(ValueError, match="identity mismatch"):
        comparison.canonical_fields([row])


def test_order_is_deterministic_and_inputs_unchanged():
    rows = [field("sample-b", region="South"), field("sample-a", region="North")]
    before = [row.concept.model_dump() for row in rows]
    assert comparison.compare_portfolio(rows) == comparison.compare_portfolio(
        reversed(rows)
    )
    assert [row.concept.model_dump() for row in rows] == before


def test_empty_portfolio_has_no_evaluated_coverage():
    """Zero fields yield zero counts; a zero denominator has no coverage ratio."""
    report = comparison.compare_portfolio([])
    assert report["fields"] == report["regions"] == []
    assert report["totals"]["total"] == 0
    assert report["totals"]["coverage_fraction"] is None


def test_builder_delegates_to_existing_portfolio(monkeypatch, tmp_path):
    paths = (tmp_path / "crosswalk.csv", tmp_path / "fields.csv")
    for path in paths:
        path.write_text(path.name, encoding="utf-8")
    calls = []

    def build(crosswalk_path=None, fields_path=None):
        calls.append((crosswalk_path, fields_path))
        return [field("sample", ConceptType.NUI)]

    monkeypatch.setattr(comparison, "build_portfolio", build)
    report = comparison.build_comparison(*paths)
    assert calls == [paths]
    assert report["totals"]["dry"] == 1
    assert {source["role"] for source in report["sources"]} == {
        "matched_crosswalk",
        "field_catalog",
        "host_registry",
    }
    assert [
        source["sha256"]
        for source in report["sources"]
        if source["role"] in {"matched_crosswalk", "field_catalog"}
    ] == [hashlib.sha256(path.name.encode()).hexdigest() for path in paths]
    assert all("path" not in source for source in report["sources"])


def test_builder_rejects_sources_changed_during_loading(monkeypatch, tmp_path):
    paths = (tmp_path / "crosswalk.csv", tmp_path / "fields.csv")
    for path in paths:
        path.write_text("original", encoding="utf-8")

    def build(**kwargs):
        paths[0].write_text("changed", encoding="utf-8")
        return []

    monkeypatch.setattr(comparison, "build_portfolio", build)
    with pytest.raises(ValueError, match="source changed during loading"):
        comparison.build_comparison(*paths)


def test_cli_exports_the_same_report(monkeypatch, tmp_path):
    expected = comparison.compare_portfolio([field("sample", ConceptType.SPAR)])
    monkeypatch.setattr(comparison, "build_comparison", lambda **kwargs: expected)
    output = tmp_path / "comparison.json"
    comparison.main(["--output", str(output)])
    assert json.loads(output.read_text(encoding="utf-8")) == expected


def test_cli_does_not_overwrite_an_existing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(comparison, "build_comparison", lambda **kwargs: {})
    output = tmp_path / "existing.json"
    output.write_text("preserved", encoding="utf-8")
    with pytest.raises(FileExistsError):
        comparison.main(["--output", str(output)])
    assert output.read_text(encoding="utf-8") == "preserved"


def test_cli_rejects_an_input_as_output(tmp_path):
    source = tmp_path / "fields.csv"
    source.write_text("preserved", encoding="utf-8")
    with pytest.raises(SystemExit):
        comparison.main(["--fields", str(source), "--output", str(source)])
    assert source.read_text(encoding="utf-8") == "preserved"


def test_real_portfolio_reconciles_without_pinning_stale_counts():
    """Independent enumeration: all rows contribute once to exactly one cell.

    Counts are derived directly from the actual labels, separately from the
    aggregation. The test establishes reconciliation, not source freshness.
    """
    from worldenergydata.field_development.portfolio_matched import build_portfolio

    rows = build_portfolio()
    report = comparison.compare_portfolio(rows)
    assert report["totals"]["total"] == len(rows)
    assert report["totals"]["typed"] == sum(row.actual is not None for row in rows)
    assert report["totals"]["untyped"] == sum(row.actual is None for row in rows)
    assert sum(r["total"] for r in report["regions"]) == len(rows)
    assert all(
        r["dry"] + r["wet"] + r["other"] == r["total"] for r in report["regions"]
    )
