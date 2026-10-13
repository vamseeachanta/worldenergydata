"""Offline registry contract checks; all constructed evidence is synthetic."""

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.cost.data_collection.operator_statement_registry import (
    SEED_OPERATORS,
    OperatorStatement,
    StatementRegistry,
    derive_coverage,
    emit_registry,
    load_registry,
)

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/operator_statements"


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden in registry tests")

    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)


@pytest.fixture
def synthetic_operator():
    return {
        "name": "Synthetic Operator",
        "primary_domains": ["example.org"],
        "market_context": "Synthetic test market; no real disclosure",
        "discovery_url": "https://example.org/reports",
        "filing_channels": ["annual_report"],
        "discovery_notes": "Synthetic listing, no inferred pattern",
        "observations": synthetic_observations(),
        "coverage_by_year": {
            str(year): {"status": "missing", "note": "Not attempted", "documents": []}
            for year in range(2020, 2025)
        },
    }


def synthetic_observations():
    return [
        {
            "url": url,
            "retrieved_at_utc": "2026-10-11T11:59:00Z",
            "http_status": 200,
            "content_type": "text/html",
            "sha256": hashlib.sha256(b"Synthetic listing and terms").hexdigest(),
            "size_bytes": len(b"Synthetic listing and terms"),
            "terms_url": "https://example.org/terms",
            "terms_retrieved_at_utc": "2026-10-11T11:59:00Z",
            "terms_wording": "Synthetic permission for tests only",
        }
        for url in ["https://example.org/reports", "https://example.org/terms"]
    ]


def synthetic_document():
    return {
        "url": "https://example.org/report-2022.pdf",
        "listing_url": "https://example.org/reports",
        "channel": "annual_report",
        "operator_name": "Synthetic Operator",
        "fiscal_year": 2022,
        "identity_quote": "Synthetic Operator Annual Report 2022",
        "identity_locator": "Synthetic PDF title page",
        "retrieved_at_utc": "2026-10-11T12:00:00Z",
        "http_status": 200,
        "content_type": "application/pdf",
        "sha256": hashlib.sha256(b"Synthetic PDF evidence").hexdigest(),
        "size_bytes": 22,
        "terms_url": "https://example.org/terms",
        "terms_retrieved_at_utc": "2026-10-11T11:59:00Z",
        "terms_wording": "Synthetic permission for tests only",
    }


def test_derived_bounds_and_channel_counts(synthetic_operator):
    synthetic_operator["coverage_by_year"]["2022"] = {
        "status": "verified",
        "note": "Synthetic evidence",
        "documents": [synthetic_document()],
    }
    row = OperatorStatement.model_validate(synthetic_operator)
    result = derive_coverage(row)
    assert result["earliest_covered_year"] == 2022
    assert result["latest_verified_year"] == 2022
    assert result["coverage_by_channel"]["annual_report"] == [2022]
    assert result["coverage_by_year"][2020] == "missing"
    assert (
        derive_coverage(
            OperatorStatement.model_validate(
                {
                    **synthetic_operator,
                    "coverage_by_year": {
                        str(y): {"status": "missing", "note": "Not tried"}
                        for y in range(2020, 2025)
                    },
                }
            )
        )["earliest_covered_year"]
        is None
    )


@pytest.mark.parametrize(
    "field", ["url", "sha256", "retrieved_at_utc", "terms_wording", "listing_url"]
)
def test_verified_requires_evidence(synthetic_operator, field):
    document = synthetic_document()
    document.pop(field)
    synthetic_operator["coverage_by_year"]["2022"] = {
        "status": "verified",
        "note": "Synthetic",
        "documents": [document],
    }
    with pytest.raises(ValidationError):
        OperatorStatement.model_validate(synthetic_operator)


@pytest.mark.parametrize(
    "patch",
    [
        {"filing_channels": ["investor_relations"]},
        {"filing_channels": ["strategy_report"]},
        {"discovery_url": "not-a-url"},
        {"earliest_covered_year": 2020},
        {"name": " "},
    ],
)
def test_bad_discovery_and_channels_rejected(synthetic_operator, patch):
    with pytest.raises(ValidationError):
        OperatorStatement.model_validate({**synthetic_operator, **patch})


@pytest.mark.parametrize("status", ["available", "unknown", "", "VERIFIED"])
def test_status_vocabulary(synthetic_operator, status):
    synthetic_operator["coverage_by_year"]["2020"]["status"] = status
    with pytest.raises(ValidationError):
        OperatorStatement.model_validate(synthetic_operator)


def test_verified_without_documents_rejected(synthetic_operator):
    synthetic_operator["coverage_by_year"]["2020"]["status"] = "verified"
    with pytest.raises(ValidationError):
        OperatorStatement.model_validate(synthetic_operator)


def test_year_window_exact(synthetic_operator):
    synthetic_operator["coverage_by_year"].pop("2020")
    with pytest.raises(ValidationError):
        OperatorStatement.model_validate(synthetic_operator)


@pytest.mark.parametrize(
    "patch",
    [
        {"url": "https://aggregator.example/report.pdf"},
        {"retrieved_at_utc": "2026-10-11T12:00:00"},
        {"http_status": 403},
        {"sha256": "wrong"},
        {"size_bytes": 0},
        {"content_type": "text/html"},
        {"channel": "sec_10k"},
        {"operator_name": "Different synthetic operator"},
        {"fiscal_year": 2021},
    ],
)
def test_document_evidence_validation(synthetic_operator, patch):
    synthetic_operator["coverage_by_year"]["2022"] = {
        "status": "verified",
        "note": "Synthetic",
        "documents": [{**synthetic_document(), **patch}],
    }
    with pytest.raises(ValidationError):
        OperatorStatement.model_validate(synthetic_operator)


def test_unverified_cannot_hold_documents(synthetic_operator):
    synthetic_operator["coverage_by_year"]["2022"]["documents"] = [synthetic_document()]
    with pytest.raises(ValidationError):
        OperatorStatement.model_validate(synthetic_operator)


def test_exact_seed_and_manifest_reproduction():
    registry = load_registry(DATA / "registry.json")
    assert {row.name for row in registry.operators} == set(SEED_OPERATORS)
    assert len(registry.operators) == 9
    assert (
        emit_registry(DATA / "observations.json")
        == (DATA / "registry.json").read_bytes()
    )
    assert all(
        set(row.coverage_by_year) == set(range(2020, 2025))
        for row in registry.operators
    )


def test_synthetic_manifest_reproduction(synthetic_operator):
    fixture = ROOT / "tests/unit/cost/fixtures/operator_statements_synthetic.json"
    assert emit_registry(fixture, require_seed=False) == (
        fixture.with_name("operator_statements_synthetic_manifest.json").read_bytes()
    )


def test_duplicate_operators_rejected(synthetic_operator):
    with pytest.raises(ValidationError):
        StatementRegistry.model_validate(
            {
                "schema_version": 1,
                "operators": [synthetic_operator, deepcopy(synthetic_operator)],
            }
        )


def test_observation_changes_manifest(tmp_path, synthetic_operator):
    import json

    input_path = tmp_path / "synthetic_input.json"
    payload = {"schema_version": 1, "operators": [synthetic_operator]}
    input_path.write_text(json.dumps(payload))
    before = emit_registry(input_path, require_seed=False)
    payload["operators"][0]["discovery_notes"] = "Changed synthetic observation"
    input_path.write_text(json.dumps(payload))
    assert emit_registry(input_path, require_seed=False) != before


def test_refusal_requires_scope_and_observation(synthetic_operator):
    synthetic_operator["coverage_by_year"]["2020"]["status"] = "access_refused"
    with pytest.raises(ValidationError):
        OperatorStatement.model_validate(synthetic_operator)


@pytest.mark.parametrize(
    "channel", ["annual_report", "sec_10k", "sec_20f", "sustainability_report"]
)
def test_document_channels_and_nonadjacent_year_bounds(synthetic_operator, channel):
    synthetic_operator["filing_channels"] = [channel]
    for year in [2020, 2024]:
        document = {**synthetic_document(), "fiscal_year": year, "channel": channel}
        synthetic_operator["coverage_by_year"][str(year)] = {
            "status": "verified",
            "note": "Synthetic evidence",
            "documents": [document],
        }
    result = derive_coverage(OperatorStatement.model_validate(synthetic_operator))
    assert result["earliest_covered_year"] == 2020
    assert result["latest_verified_year"] == 2024
    assert result["coverage_by_channel"][channel] == [2020, 2024]


def test_verified_listing_requires_successful_observation(synthetic_operator):
    synthetic_operator["observations"] = []
    synthetic_operator["coverage_by_year"]["2022"] = {
        "status": "verified",
        "note": "Synthetic",
        "documents": [synthetic_document()],
    }
    with pytest.raises(ValidationError, match="listing"):
        OperatorStatement.model_validate(synthetic_operator)


def test_ordinary_response_cannot_prove_unavailability(synthetic_operator):
    document = synthetic_document()
    observation = {
        k: document[k]
        for k in (
            "url",
            "retrieved_at_utc",
            "http_status",
            "content_type",
            "sha256",
            "size_bytes",
            "terms_url",
            "terms_retrieved_at_utc",
            "terms_wording",
        )
    }
    synthetic_operator["observations"] = [observation]
    synthetic_operator["coverage_by_year"]["2020"].update(
        status="known_unavailable",
        refusal_url=observation["url"],
        refusal_scope="Synthetic source only",
    )
    with pytest.raises(ValidationError, match="refusal|finding"):
        OperatorStatement.model_validate(synthetic_operator)


@pytest.mark.parametrize(
    "status,quote",
    [(403, None), (429, None), (200, "Synthetic source does not publish this year")],
)
def test_refusal_or_explicit_finding_is_valid(synthetic_operator, status, quote):
    observation = synthetic_observations()[0]
    observation["http_status"] = status
    synthetic_operator["observations"] = [observation]
    synthetic_operator["coverage_by_year"]["2020"].update(
        status="access_refused" if status in {403, 429} else "known_unavailable",
        refusal_url=observation["url"],
        refusal_scope="Synthetic access scope",
        finding_quote=quote,
    )
    row = OperatorStatement.model_validate(synthetic_operator)
    assert derive_coverage(row)["earliest_covered_year"] is None


def refused_operator(synthetic_operator):
    observation = synthetic_observations()[0]
    observation["http_status"] = 403
    synthetic_operator["observations"] = [observation]
    synthetic_operator["coverage_by_year"]["2020"].update(
        status="access_refused",
        refusal_url=observation["url"],
        refusal_scope="Synthetic source only",
    )
    return synthetic_operator


def test_access_refused_with_evidence_validates(synthetic_operator):
    row = OperatorStatement.model_validate(refused_operator(synthetic_operator))
    assert row.coverage_by_year[2020].status == "access_refused"


@pytest.mark.parametrize("missing", ["refusal_url", "refusal_scope", "observations"])
def test_access_refused_without_evidence_rejected(synthetic_operator, missing):
    payload = refused_operator(synthetic_operator)
    if missing == "observations":
        payload[missing] = []
    else:
        payload["coverage_by_year"]["2020"].pop(missing)
    with pytest.raises(
        ValidationError, match="access_refused requires|refusal response"
    ):
        OperatorStatement.model_validate(payload)


@pytest.mark.parametrize("status", [403, 429])
def test_refusal_cannot_prove_known_unavailable(synthetic_operator, status):
    payload = refused_operator(synthetic_operator)
    payload["observations"][0]["http_status"] = status
    payload["coverage_by_year"]["2020"].update(
        status="known_unavailable",
        finding_quote="Synthetic source does not publish this year",
    )
    with pytest.raises(ValidationError, match="explicit source finding"):
        OperatorStatement.model_validate(payload)


def test_ordinary_response_cannot_prove_access_refused(synthetic_operator):
    payload = refused_operator(synthetic_operator)
    payload["observations"][0]["http_status"] = 200
    with pytest.raises(ValidationError, match="refusal response"):
        OperatorStatement.model_validate(payload)


def test_seed_refusals_are_access_refused():
    registry = load_registry(DATA / "registry.json")
    refused = {
        (row.name, year)
        for row in registry.operators
        for year, coverage in row.coverage_by_year.items()
        if coverage.status == "access_refused"
    }
    assert refused == {
        (name, year) for name in ["BP", "Chevron"] for year in range(2020, 2025)
    }
    assert not any(
        coverage.status == "known_unavailable"
        for row in registry.operators
        for coverage in row.coverage_by_year.values()
    )


def test_coverage_preserves_access_refused(synthetic_operator):
    from collections import Counter

    row = OperatorStatement.model_validate(refused_operator(synthetic_operator))
    result = derive_coverage(row)
    assert Counter(result["coverage_by_year"].values()) == {
        "access_refused": 1,
        "missing": 4,
    }
    assert result["coverage_by_channel"]["annual_report"] == []
    assert result["earliest_covered_year"] is None
    assert result["latest_verified_year"] is None


def test_document_year_bounds_match_coverage_window():
    from worldenergydata.cost.data_collection.operator_statement_registry import (
        YEARS,
        DocumentEvidence,
    )

    bounds = DocumentEvidence.model_json_schema()["properties"]["fiscal_year"]
    assert bounds["minimum"] == min(YEARS)
    assert bounds["maximum"] == max(YEARS)
