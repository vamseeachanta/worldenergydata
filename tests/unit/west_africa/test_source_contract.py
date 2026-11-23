"""Offline acceptance checks for the Nigeria source and acquisition contract."""

import json
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs/data-sources/west-africa"
REQUIRED_METADATA = {
    "publisher",
    "url",
    "data_type",
    "format",
    "native_grain",
    "units",
    "observation_period",
    "publication_date",
    "cadence",
    "access",
    "rights",
    "checked_date",
    "evidence",
    "supported_uses",
    "unavailable_uses",
    "scheduler_eligible",
}


def register():
    return json.loads((DOCS / "source-contract.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "source,grain",
    [
        ("nuprc-production", "blend-period"),
        ("eiti-production", "country-company-commodity-year"),
        ("eiti-payments", "country-company-payment-type-year"),
    ],
)
def test_source_metadata_and_use_boundaries(source, grain):
    row = register()["sources"][source]
    assert REQUIRED_METADATA <= row.keys()
    for key in REQUIRED_METADATA - {"scheduler_eligible"}:
        assert row[key], key
    assert urlsplit(row["url"]).scheme == "https"
    assert date.fromisoformat(row["checked_date"])
    assert row["native_grain"] == grain
    assert "field-production" in row["unavailable_uses"]
    assert set(row["supported_uses"]).isdisjoint(row["unavailable_uses"])
    assert row["scheduler_eligible"] is False


@pytest.mark.parametrize("topic", ["wells", "reserves", "licensing", "fiscal"])
def test_discovery_gaps_have_a_source_and_a_release_condition(topic):
    gap = register()["discovery_gaps"][topic]
    assert urlsplit(gap["lead"]).scheme == "https"
    assert gap["evidence"]
    assert gap["required_evidence"]
    assert gap["status"] == "unqualified"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs)["href"])


def test_contract_links_existing_acceptance_and_adapter_criteria():
    links = Links()
    links.feed((DOCS / "source-contract.html").read_text(encoding="utf-8"))
    expected = {
        DOCS / "source-contract.json",
        ROOT / "docs/modules/fdas/country-adapter-checklist.md",
        ROOT / "docs/data/source-refresh-acceptance-criteria.md",
    }
    local_files = {
        (DOCS / href).resolve() for href in links.hrefs if not urlsplit(href).scheme
    }
    assert expected <= local_files
    assert all(path.is_file() for path in local_files)


def test_source_evidence_resolves_to_dated_publisher_checks():
    contract = register()
    checks = contract["publisher_checks"]
    rows = [*contract["sources"].values(), *contract["discovery_gaps"].values()]
    for row in rows:
        for key in row["evidence"]:
            check = checks[key]
            assert urlsplit(check["url"]).scheme == "https"
            assert check["retrieved_utc"].endswith("Z")
            assert check["finding"]
    for row in contract["sources"].values():
        assert row["rights"] == "unknown"
        assert row["grain_basis"] == "local-client-expectation"
        checked_dates = {checks[key]["retrieved_utc"][:10] for key in row["evidence"]}
        assert checked_dates == {row["checked_date"]}
