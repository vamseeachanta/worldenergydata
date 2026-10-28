"""Registry rules from issue 1325 (2026), Sources and Never collect.

Fixtures are synthetic: dates are calendar examples, not refresh limits.
Expected permissions are derived independently: unverified terms OR reserved
rights OR unavailable content forbids storing text. No network is used.
"""

import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from pydantic import ValidationError

from worldenergydata.hse.source_registry import SourceRegistry, load_registry, main

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "data/modules/hse/offshore/source_registry.json"


def entry(**changes):
    row = {
        "source": "synthetic",
        "url": "https://example.org/notices",
        "licence": "unverified",
        "licence_statement": "not established",
        "access_status": "unverified",
        "terms_verification": "unverified",
        "terms_check_date": None,
        "terms_url": None,
        "terms_status": "not verified",
        "storage_policy": "metadata_only",
    }
    row.update(changes)
    return row


def registry(*rows):
    return {"schema_version": 2, "sources": list(rows or [entry()])}


def test_unverified_terms_are_representable_without_inventing_a_date():
    row = SourceRegistry.model_validate(registry()).sources[0]
    assert row.licence == "unverified"
    assert row.terms_check_date is None
    assert row.storage_policy == "metadata_only"


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "url",
        "licence",
        "licence_statement",
        "access_status",
        "terms_verification",
        "terms_check_date",
        "terms_url",
        "terms_status",
        "storage_policy",
    ],
)
def test_required_fields_cannot_be_omitted(field):
    row = entry()
    del row[field]
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(registry(row))


@pytest.mark.parametrize(
    "field", ["source", "url", "licence_statement", "terms_status"]
)
@pytest.mark.parametrize("value", ["", "   ", None])
def test_required_strings_are_not_blank(field, value):
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(registry(entry(**{field: value})))


@pytest.mark.parametrize(
    "changes",
    [
        {"licence": "free to access"},
        {"access_status": "probably public"},
        {"terms_verification": "assumed"},
        {"storage_policy": "download everything"},
        {"source": "Synthetic Source"},
        {"url": "file:///notices"},
        {"url": "https://user:password" + "@" + "example.org/notices"},
        {"url": "https://example.org:invalid/notices"},
        {"url": "https://example.org/notices with spaces"},
        {"terms_url": "not a URL"},
        {"alternate_urls": ["not a URL"]},
        {"terms_check_date": "2026-02-30"},
        {"terms_check_date": "2026-1-2"},
        {"terms_check_date": "20261017"},
        {"terms_check_date": "2026-10-17T00:00:00Z"},
        {"terms_check_date": 20261017},
        {"access_date": "2026-02-30"},
        {"unexpected": "misspelled field"},
    ],
)
def test_invalid_fields_are_rejected(changes):
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(registry(entry(**changes)))


@pytest.mark.parametrize("duplicate", ["synthetic", " synthetic "])
def test_duplicate_source_is_rejected_after_whitespace_normalization(duplicate):
    with pytest.raises(ValidationError, match="duplicate source"):
        SourceRegistry.model_validate(registry(entry(), entry(source=duplicate)))


@pytest.mark.parametrize("version", [1, True, "2", 3])
def test_schema_version_is_explicit_and_strict(version):
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(dict(registry(), schema_version=version))


def test_empty_registry_is_rejected():
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate({"schema_version": 2, "sources": []})


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"licence": "all-rights-reserved"},
        {"licence": "OGL-3.0"},
        {"licence": "OGL-3.0", "terms_verification": "verified"},
        {
            "licence": "OGL-3.0",
            "terms_verification": "verified",
            "terms_check_date": "2026-10-17",
            "terms_url": "https://example.org/terms",
        },
    ],
)
def test_text_permission_fails_closed(changes):
    """Each case lacks at least one required permission or access fact."""
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(
            registry(entry(storage_policy="text_permitted", **changes))
        )


@pytest.mark.parametrize("missing", ["terms_check_date", "terms_url"])
def test_verified_terms_require_evidence_and_date(missing):
    row = entry(
        licence="OGL-3.0",
        terms_verification="verified",
        terms_check_date="2026-10-17",
        terms_url="https://example.org/terms",
    )
    row[missing] = None
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(registry(row))


def test_verified_cannot_claim_an_unverified_licence():
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(
            registry(
                entry(
                    terms_verification="verified",
                    terms_check_date="2026-10-17",
                    terms_url="https://example.org/terms",
                )
            )
        )


@pytest.mark.parametrize(
    "licence", ["OGL-3.0", "US-federal-work", "attribution-permitted"]
)
def test_text_permission_needs_verified_terms_and_public_access(licence):
    """All prerequisites hold for synthetic website text; never images or people."""
    row = entry(
        licence=licence,
        terms_verification="verified",
        access_status="public",
        terms_check_date="2026-10-17",
        terms_url="https://example.org/terms",
        storage_policy="text_permitted",
    )
    assert (
        SourceRegistry.model_validate(registry(row)).sources[0].storage_policy
        == "text_permitted"
    )


def test_reserved_rights_never_permit_text_even_when_verified():
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(
            registry(
                entry(
                    licence="all-rights-reserved",
                    terms_verification="verified",
                    access_status="public",
                    terms_check_date="2026-10-17",
                    terms_url="https://example.org/terms",
                    storage_policy="text_permitted",
                )
            )
        )


def test_committed_registry_covers_issue_source_table_and_legacy_holdings():
    """Issue 1325 table: nine sources; existing audit holdings add OSHA and EPA."""
    rows = {row.source: row for row in load_registry(REGISTRY).sources}
    assert set(rows) == {
        "uk_hse",
        "opred",
        "bsee",
        "iogp",
        "havtil",
        "nopsema",
        "iadc",
        "csb",
        "sec",
        "osha",
        "epa",
    }
    assert all(row.storage_policy == "metadata_only" for row in rows.values())
    assert rows["opred"].licence == "OGL-3.0"
    assert rows["iadc"].licence == "all-rights-reserved"
    for name in ("uk_hse", "iogp", "nopsema", "csb", "sec", "osha", "epa", "bsee"):
        assert rows[name].licence == "unverified"
        assert rows[name].terms_verification == "unverified"
    assert rows["nopsema"].terms_check_date is None


def test_load_registry_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text('{"schema_version": 2, "schema_version": 2, "sources": []}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_registry(path)


def test_cli_lists_sorted_sources_and_storage_policy(capsys):
    assert main(["list", "--registry", str(REGISTRY)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split("\t") == [
        "source",
        "licence",
        "access_status",
        "terms_check_date",
        "storage_policy",
        "url",
    ]
    assert [line.split("\t")[0] for line in lines[1:]] == [
        "bsee",
        "csb",
        "epa",
        "havtil",
        "iadc",
        "iogp",
        "nopsema",
        "opred",
        "osha",
        "sec",
        "uk_hse",
    ]
    assert all("metadata_only" in line for line in lines[1:])


def test_cli_json_preserves_unknown_dates(capsys):
    assert main(["list", "--registry", str(REGISTRY), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    row = next(row for row in data["sources"] if row["source"] == "nopsema")
    assert row["terms_check_date"] is None
    assert row["licence"] == "unverified"


def test_cli_validate_and_default_discovery(capsys):
    assert main(["validate"]) == 0
    assert capsys.readouterr().out.strip() == "Source registry valid: 11 sources"


@pytest.mark.parametrize("kind", ["missing", "malformed", "invalid"])
def test_cli_errors_do_not_echo_untrusted_contents(tmp_path, capsys, kind):
    path = tmp_path / "registry.json"
    if kind == "malformed":
        path.write_text("untrusted fixture content")
    elif kind == "invalid":
        path.write_text(
            json.dumps(registry(entry(licence="untrusted fixture content")))
        )
    assert main(["list", "--registry", str(path)]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "Invalid source registry" in captured.err
    assert "untrusted fixture content" not in captured.err


def test_module_cli_works_outside_checkout(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.hse.source_registry",
            "list",
            "--registry",
            str(REGISTRY),
            "--json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["schema_version"] == 2


def test_loader_source_enums_and_hosts_exist_in_registry():
    from worldenergydata.hse.offshore import AGENCIES, SOURCE_HOSTS, Source

    registered = {row.source for row in load_registry(REGISTRY).sources}
    assert {source.value for source in Source} <= registered
    assert set(SOURCE_HOSTS) <= registered
    assert set(AGENCIES) <= registered


@pytest.mark.parametrize("name", ["pilot.json", "sample.json"])
def test_collection_packet_sources_exist_in_registry(name):
    rows = json.loads((REGISTRY.parent / name).read_text())
    registered = {row.source for row in load_registry(REGISTRY).sources}
    assert {row["source"] for row in rows["sources"]} <= registered


def test_legacy_loader_urls_belong_to_registered_sources():
    """Read URL literals without running a downloader or importing its extras.

    Hosts are taken from the registry's primary/alternate URLs. In particular,
    the OSHA data service is a Department of Labor host, not an OSHA subdomain.
    A new loader with an unregistered source host must fail this guard.
    """
    rows = load_registry(REGISTRY).sources
    registered_hosts = {
        urlsplit(url).hostname for row in rows for url in [row.url, *row.alternate_urls]
    }
    package = ROOT / "packages/worldenergydata-bsee/src/worldenergydata/hse"
    observed = set()
    for folder in ("acquirers", "importers"):
        for path in (package / folder).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    for url in re.findall(r'https?://[^\s"<>`]+', node.value):
                        host = urlsplit(url).hostname
                        assert (
                            host in registered_hosts
                        ), f"unregistered source host in {path.name}"
                        observed.add(host)
    assert "enforcedata.dol.gov" in observed
    assert "www.data.bsee.gov" in observed
    assert "data.epa.gov" in observed


def test_migration_preserves_recorded_evidence():
    """Known statements and dates come from the committed 2026 source review."""
    review = json.loads((REGISTRY.parent / "source_review.json").read_text())
    rows = {row.source: row for row in load_registry(REGISTRY).sources}
    for name in ("opred", "havtil", "iadc"):
        assert name in review["licence_checks"]
        assert rows[name].terms_check_date.isoformat() == review["access_date"]
    assert rows["sec"].terms_check_date is None
