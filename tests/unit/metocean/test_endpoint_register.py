"""Publisher endpoint inventory; no physical equations or acceptance limits.

Expected URLs are the actual client constants and string literals, independently
read through the AST. Access categories follow the publisher documents linked in
the register. Mutation controls show that omissions and unregistered hosts fail.
"""

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from worldenergydata.metocean.source_register import (
    load_register,
    registered_url,
    validate_register,
)

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = ROOT / "packages/worldenergydata-metocean/src/worldenergydata/metocean"


def test_all_source_rows_have_endpoint_evidence():
    validate_register(load_register())


@pytest.mark.parametrize(
    "field", ["base_url", "auth_requirement", "docs_url", "terms_url", "endpoints"]
)
def test_missing_evidence_is_rejected(field):
    register = deepcopy(load_register())
    del register["sources"][0][field]
    with pytest.raises(ValueError, match=field):
        validate_register(register)


def test_invalid_auth_and_duplicate_identity_are_rejected():
    register = deepcopy(load_register())
    register["sources"][0]["auth_requirement"] = "probably anonymous"
    with pytest.raises(ValueError, match="auth_requirement"):
        validate_register(register)
    register = deepcopy(load_register())
    register["sources"].append(register["sources"][0])
    with pytest.raises(ValueError, match="duplicate"):
        validate_register(register)


def client_urls(text):
    tree = ast.parse(text)
    docstrings = set()
    for node in ast.walk(tree):
        if (
            isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            )
            and node.body
            and isinstance(node.body[0], ast.Expr)
        ):
            docstrings.add(id(node.body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and id(node) not in docstrings
        and isinstance(node.value, str)
        and node.value.startswith(("https://", "http://"))
    ]


def test_clients_do_not_introduce_unregistered_urls():
    paths = [DOMAIN / "constants.py", *(DOMAIN / "clients").glob("*.py")]
    for path in paths:
        for url in client_urls(path.read_text(encoding="utf-8")):
            assert registered_url(url), path.name


def test_audit_detects_direct_request_literals_and_ignores_reference_docstrings():
    urls = client_urls(
        '"""https://reference.example.org"""\n'
        'client.get("https://unregistered.invalid/data")'
    )
    assert urls == ["https://unregistered.invalid/data"]
    assert not registered_url(urls[0])


def test_documentation_lists_every_source_and_its_evidence():
    page = (ROOT / "docs/data-sources/metocean-endpoint-audit.md").read_text(
        encoding="utf-8"
    )
    for row in load_register()["sources"]:
        assert f"| {row['id']} |" in page
        assert row["docs_url"] in page
        if row["terms_url"] is None:
            source_line = next(
                line
                for line in page.splitlines()
                if line.startswith(f"| {row['id']} |")
            )
            assert "NOT_EVALUATED" in source_line
            assert "[terms]" not in source_line
        else:
            assert row["terms_url"] in page


def test_url_matching_respects_origin_and_path_boundaries():
    assert registered_url("https://www.ndbc.noaa.gov/data/realtime2/42001.txt")
    assert not registered_url("https://www.ndbc.noaa.gov.example.org/data")
    assert not registered_url("https://example.org/unregistered")
    assert not registered_url("http://www.ndbc.noaa.gov/data")
    userinfo_separator = "@"
    credential_url = (
        f"https://user:placeholder{userinfo_separator}www.ndbc.noaa.gov/data"
    )
    assert not registered_url(credential_url)


@pytest.mark.parametrize("identifier", ["era5", "cmems"])
def test_account_sources_are_explicit(identifier):
    row = next(row for row in load_register()["sources"] if row["id"] == identifier)
    assert row["auth_requirement"] == "account"
    assert row["account_required"] is True
    assert row["legacy_status"] == (
        "RETIRED" if identifier == "cmems" else "NOT_EVALUATED"
    )
    assert row["migration_docs_url"].startswith("https://")


@pytest.mark.parametrize(
    "identifier",
    [
        "canada_gdwps",
        "brazil_pnboia",
        "india_incois",
        "pirata",
        "ncep_wave_hindcast",
        "ndbc_currents",
        "nhc_best_track",
    ],
)
def test_unconfirmed_access_is_separate_from_documented_account_access(identifier):
    source = next(row for row in load_register()["sources"] if row["id"] == identifier)
    assert source["auth_requirement"] == "unconfirmed"
    assert source["auth_evaluation"].startswith("NOT_EVALUATED")
    assert source["account_required"] is None


@pytest.mark.parametrize("requirement", ["account", "free key"])
@pytest.mark.parametrize(
    "evidence,evaluation",
    [
        (None, "confirmed"),
        (
            "https://example.invalid/access",
            "NOT_EVALUATED; requirement not established",
        ),
    ],
)
def test_credential_requirement_needs_documented_auth_evidence(
    requirement, evidence, evaluation
):
    source = deepcopy(load_register()["sources"][0])
    source["auth_requirement"] = requirement
    source["auth_evaluation"] = evaluation
    source["auth_evidence_url"] = evidence
    with pytest.raises(ValueError, match="auth_evidence"):
        validate_register({"sources": [source]})


@pytest.mark.parametrize("evaluation", [None, "", "confirmed"])
def test_unconfirmed_access_requires_explicit_evaluation(evaluation):
    source = deepcopy(load_register()["sources"][0])
    source.update(auth_requirement="unconfirmed", auth_evaluation=evaluation)
    with pytest.raises(ValueError, match="auth_evaluation"):
        validate_register({"sources": [source]})


@pytest.mark.parametrize(
    "identifier", ["india_incois", "ndbc_currents", "indonesia_bmkg", "nhc_best_track"]
)
def test_absent_terms_are_registered_as_null_with_explicit_evidence(identifier):
    source = next(row for row in load_register()["sources"] if row["id"] == identifier)
    assert source["terms_url"] is None
    assert source["terms_evaluation"].startswith("NOT_EVALUATED")
    assert source["terms_quote"] == "no terms statement found"
    validate_register({"sources": [source]})


@pytest.mark.parametrize(
    "evaluation",
    [
        None,
        "",
        "confirmed",
        "NOT_EVALUATED; no confirmed reuse grant",
        "NOT_EVALUATEDx",
    ],
)
def test_null_terms_require_explicit_not_evaluated_evidence(evaluation):
    source = deepcopy(load_register()["sources"][0])
    source.update(terms_url=None, terms_evaluation=evaluation)
    with pytest.raises(ValueError, match="terms_url"):
        validate_register({"sources": [source]})
