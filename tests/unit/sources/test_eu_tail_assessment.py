"""Independent truth-table cases for the decision gate in issue 753.

Basis: https://github.com/vamseeachanta/worldenergydata/issues/753,
Decision gate (2026), with the later concession-mapping and reuse caveats.
These cases contain synthetic capability flags, not measured production.
No physical constants or numerical acceptance tolerances are used.
"""

import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest

from worldenergydata.source_assessment import SourceCapabilities, assess_source

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/data/eu-tail-source-assessment.json"


@pytest.fixture
def field_monthly():
    return SourceCapabilities(
        production_granularity="field",
        production_frequency="monthly",
        production_verified=True,
        field_metadata="absent",
        reuse="permission_required",
    )


@pytest.mark.parametrize("granularity", ["field", "well"])
def test_verified_monthly_series_meets_gate(field_monthly, granularity):
    """Hand evaluation: verified AND monthly AND (field OR well) = true."""
    result = assess_source(replace(field_monthly, production_granularity=granularity))
    assert result.decision == "PROMOTE"
    assert result.fdas_production == "CANDIDATE"
    # Public access cannot override the separate reproduction restriction.
    assert result.raw_redistribution == "PERMISSION_REQUIRED"


def test_concession_is_not_silently_a_field(field_monthly):
    """Hand evaluation: concession lacks a verified field mapping => review."""
    source = replace(field_monthly, production_granularity="concession")
    assert assess_source(source).decision == "REVIEW_MAPPING"
    assert assess_source(source).fdas_production == "REQUIRES_MAPPING"
    mapped = replace(source, concession_field_mapping=True)
    assert assess_source(mapped).decision == "PROMOTE"


@pytest.mark.parametrize("verified", [False, True])
def test_mapping_does_not_replace_production_verification(field_monthly, verified):
    """Hand evaluation: mapping AND NOT verified cannot qualify production."""
    source = replace(
        field_monthly,
        production_granularity="concession",
        concession_field_mapping=True,
        production_verified=verified,
    )
    assert assess_source(source).decision == (
        "PROMOTE" if verified else "NOT_EVALUATED"
    )


@pytest.mark.parametrize("frequency", ["annual", "none", "unknown"])
def test_nonmonthly_series_cannot_feed_monthly_cashflow(field_monthly, frequency):
    """Hand evaluation: monthly=false => monthly production unavailable/unknown."""
    result = assess_source(replace(field_monthly, production_frequency=frequency))
    expected = "NOT_EVALUATED" if frequency == "unknown" else "UNAVAILABLE"
    assert result.fdas_production == expected


def test_field_metadata_alone_meets_either_branch_of_gate(field_monthly):
    """Hand evaluation: production=false OR verified field metadata=true => true."""
    result = assess_source(
        replace(
            field_monthly,
            production_granularity="none",
            production_frequency="none",
            field_metadata="verified",
        )
    )
    assert result.decision == "PROMOTE"
    assert result.fdas_production == "UNAVAILABLE"
    assert result.field_concept == "CANDIDATE"


@pytest.mark.parametrize("granularity", ["aggregate", "none"])
def test_aggregate_and_exploration_pages_are_coverage_only(field_monthly, granularity):
    """Hand evaluation: no field production AND no field metadata => false."""
    source = replace(field_monthly, production_granularity=granularity)
    assert assess_source(source).decision == "COVERAGE_ONLY"


def test_unknown_metadata_is_not_an_absence_claim(field_monthly):
    """Hand evaluation: false OR unknown => unknown, rather than false."""
    source = replace(
        field_monthly, production_granularity="aggregate", field_metadata="unverified"
    )
    assert assess_source(source).decision == "NOT_EVALUATED"


@pytest.mark.parametrize(
    "reuse, expected",
    [
        ("cc_by_4_0", "ATTRIBUTION_REQUIRED"),
        ("permission_required", "PERMISSION_REQUIRED"),
        ("unspecified", "NOT_EVALUATED"),
    ],
)
def test_reuse_is_independent_of_data_granularity(field_monthly, reuse, expected):
    """Hand evaluation: identical monthly series, independent rights input."""
    result = assess_source(replace(field_monthly, reuse=reuse))
    assert result.decision == "PROMOTE"
    assert result.raw_redistribution == expected


@pytest.mark.parametrize(
    "changes",
    [
        {"production_granularity": "country"},
        {"production_frequency": "quarterly"},
        {"production_verified": "false"},
        {"field_metadata": True},
        {"reuse": "open"},
        {"concession_field_mapping": "false"},
    ],
)
def test_malformed_inputs_fail_closed(field_monthly, changes):
    """Strings such as 'false' must not become truthy evidence."""
    with pytest.raises(ValueError):
        assess_source(replace(field_monthly, **changes))


def test_publisher_observations_reproduce_documented_dispositions():
    """Hand gate: ISPRA aggregate; Italy concession; DGEG none; CORES unverified.

    Evidence: the cited publisher pages and partial CSV in the assessment file.
    HEAD establishes workbook availability, not its internal field structure.
    """
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    results = {
        entry["key"]: assess_source(SourceCapabilities(**entry["capabilities"]))
        for entry in payload["sources"]
    }
    assert {key: value.decision for key, value in results.items()} == {
        "italy_ispra": "COVERAGE_ONLY",
        "italy_unmig": "REVIEW_MAPPING",
        "portugal_dgeg": "COVERAGE_ONLY",
        "spain_cores": "NOT_EVALUATED",
    }
    for entry in payload["sources"]:
        assert entry["observations"]
        assert entry["limitations"]
        for observation in entry["observations"]:
            assert observation["url"].startswith("https://")
            assert observation["observed_at"].endswith("Z")
            assert observation["http_status"] in (200, 206)
            assert observation["digest_scope"] in (
                "response_body",
                "response_headers",
                "partial_response_body",
            )
            assert len(bytes.fromhex(observation["sha256"])) == 32


def test_worked_example_uses_the_same_assessment():
    """The offline example must expose qualifications, without retrieving data."""
    spec = importlib.util.spec_from_file_location(
        "eu_tail_example", ROOT / "examples/eu_tail_source_assessment.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.summarize(EVIDENCE)
    assert result["italy_unmig"]["fdas_production"] == "REQUIRES_MAPPING"
    assert result["spain_cores"]["raw_redistribution"] == "PERMISSION_REQUIRED"
    assert result["spain_cores"]["fdas_production"] == "NOT_EVALUATED"


def test_annual_asset_production_qualifies_chain_but_not_monthly_fdas(field_monthly):
    """Issue gate is asset production OR metadata; monthly fit is independent.

    Hand evaluation: verified annual field series=true for the chain, but
    annual != monthly, so no monthly FDAS production is established.
    """
    result = assess_source(replace(field_monthly, production_frequency="annual"))
    assert result.decision == "PROMOTE"
    assert result.fdas_production == "UNAVAILABLE"


def _example_module():
    spec = importlib.util.spec_from_file_location(
        "eu_tail_example", ROOT / "examples/eu_tail_source_assessment.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_research_note_is_reproducible_from_evidence():
    """The human-readable finding and executable assessment share one input."""
    rendered = _example_module().render_report(EVIDENCE)
    report = ROOT / "docs/data/eu-tail-source-assessment.html"
    assert report.read_text(encoding="utf-8") == rendered
    assert rendered.index("Summary</h2>") < rendered.index("Revision history</h2>")
    assert rendered.index("Revision history</h2>") < rendered.index("Method</h2>")
    assert "REVIEW_MAPPING" in rendered
    assert "PERMISSION_REQUIRED" in rendered
    assert "No raw CORES workbook was downloaded" in rendered


def test_report_escapes_publisher_text(tmp_path):
    """Publisher strings are text, so injected HTML cannot become markup."""
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    payload["sources"][0]["title"] = '<script>alert("example")</script>'
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    rendered = _example_module().render_report(path)
    assert '<script>alert("example")</script>' not in rendered
    assert "&lt;script&gt;" in rendered
