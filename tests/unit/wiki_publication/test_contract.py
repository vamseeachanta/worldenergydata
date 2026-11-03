"""Routing truth table from issue #453, tightened decisions (2026-06-08).

Fixtures are synthetic declarations, not federal data or authenticated approvals.
Expected routes are derived independently: complete BSEE-only public evidence
AND both public decisions => public; complete uniform private evidence AND both
matching restricted decisions => that private target; anything else => no-publish.
No engineering calculation, coefficient or numerical acceptance limit is used.
"""

from dataclasses import replace

import pytest

from worldenergydata.wiki_publication import (
    Bundle,
    Review,
    Source,
    Target,
    route_bundle,
)


@pytest.fixture
def source():
    return Source(
        source_id="synthetic-source",
        dataset_version="synthetic-version",
        domain="bsee",
        source_class="public-federal-data",
        terms_class="public-domain",
        source_authority="Bureau of Safety and Environmental Enforcement (US DOI)",
        source_url="https://www.data.bsee.gov/",
        retrieved_at="2026-10-10T12:00:00Z",
        data_as_of="2026-10-01",
        # SHA-256 syntax: agent data handling contract, Descriptor v1 (2026-09-14).
        # Synthetic bytes only; no claim about real source bytes.
        content_sha256="a" * 64,
        derivation_path=("synthetic-source", "aggregate-summary"),
        review=Review(Target.PUBLIC, Target.PUBLIC, "synthetic-review"),
    )


@pytest.fixture
def bundle(source):
    return Bundle(
        run_id="synthetic-run",
        attempt_id="synthetic-attempt",
        code_ref="synthetic-code-revision",
        catalog_ref="synthetic-catalog-revision",
        slug="available-data-summary",
        title="Available data summary",
        findings="Synthetic aggregate findings for contract tests only.",
        sources=(source,),
        data_as_of="2026-10-01",
        generated_at="2026-10-11T12:00:00Z",
        last_license_check="2026-10-10",
        limitations=("Synthetic contract fixture; no real data.",),
        scope="all-public-bsee-available-data-summary",
        content_kind="insight",
        review=Review(Target.PUBLIC, Target.PUBLIC, "synthetic-bundle-review"),
        safety_status="passed",
    )


def test_complete_federal_bundle_routes_to_public(bundle):
    result = route_bundle(bundle)
    assert result.target is Target.PUBLIC
    assert result.reason == "eligible-public-contract"


@pytest.mark.parametrize("target", [Target.PRIVATE_GENERIC, Target.PRIVATE_RESTRICTED])
def test_private_is_distinct_from_blocked(bundle, source, target):
    review = Review(target, target, "synthetic-private-review")
    private_source = replace(
        source,
        source_class="private",
        terms_class="restricted-publication-permitted",
        domain="engineering",
        review=review,
    )
    result = route_bundle(replace(bundle, sources=(private_source,), review=review))
    assert result.target is target


@pytest.mark.parametrize(
    "changes",
    [
        {"sources": ()},
        {"sources": None},
        {"run_id": ""},
        {"attempt_id": " "},
        {"code_ref": ""},
        {"catalog_ref": ""},
        {"limitations": ()},
        {"limitations": ("",)},
        {"findings": ""},
        {"scope": "all-available-data"},
        {"content_kind": "raw-data"},
        {"content_kind": "copied-vendor-data"},
        {"content_kind": "standards-derived-text"},
        {"content_kind": "private-facts"},
        {"safety_status": "NOT_EVALUATED"},
        {"safety_status": "failed"},
        {"generated_at": "not-a-timestamp"},
        {"generated_at": "2026-10-11T12:00:00"},
        {"generated_at": "2026-09-01T12:00:00Z"},
        {"data_as_of": "2026-10-40"},
        {"last_license_check": "2026-10-12"},
        {"slug": "../escape"},
        {"slug": "unsafe/name"},
        {"slug": "unsafe\\name"},
        {"slug": "Uppercase"},
        {"review": None},
        {"review": Review(Target.PUBLIC, Target.NO_PUBLISH, "review")},
        {"review": Review(Target.PUBLIC, Target.PUBLIC, "")},
    ],
)
def test_bundle_gaps_fail_closed(bundle, changes):
    assert route_bundle(replace(bundle, **changes)).target is Target.NO_PUBLISH


@pytest.mark.parametrize(
    "changes",
    [
        {"source_id": ""},
        {"dataset_version": ""},
        {"domain": "fdas"},
        {"domain": "hse"},
        {"domain": "marine"},
        {"source_class": "unknown"},
        {"source_class": "vendor"},
        {"source_class": "private"},
        {"terms_class": "unknown"},
        {"terms_class": "licensed-standard"},
        {"terms_class": "restricted"},
        {"source_authority": ""},
        {"source_url": ""},
        {"source_url": "file:relative-source"},
        {"source_url": "https://example.invalid/"},
        {"source_url": "https://bsee.gov.example.invalid/"},
        {"source_url": "https://www.data.bsee.gov/?credential=synthetic"},
        {"source_url": "https://www.data.bsee.gov/#fragment"},
        {"retrieved_at": ""},
        {"retrieved_at": "2026-10-12T12:00:00Z"},
        {"data_as_of": "2026-10-12"},
        {"content_sha256": ""},
        {"content_sha256": "not-a-digest"},
        {"derivation_path": ()},
        {"derivation_path": ("",)},
        {"review": None},
        {"review": Review(Target.PUBLIC, Target.NO_PUBLISH, "review")},
        {"review": Review(Target.PUBLIC, Target.PUBLIC, "")},
    ],
)
def test_each_input_must_pass(bundle, source, changes):
    changed = replace(replace(source, source_id="other-source"), **changes)
    result = route_bundle(replace(bundle, sources=(source, changed)))
    assert result.target is Target.NO_PUBLISH


def test_mixed_classification_is_blocked_even_with_private_approval(bundle, source):
    target = Target.PRIVATE_RESTRICTED
    review = Review(target, target, "synthetic-review")
    public = replace(source, review=review)
    private = replace(
        source,
        source_id="other-source",
        source_class="private",
        terms_class="restricted-publication-permitted",
        review=review,
    )
    assert (
        route_bundle(replace(bundle, sources=(public, private), review=review)).target
        is Target.NO_PUBLISH
    )


def test_duplicate_source_identity_is_blocked(bundle, source):
    assert (
        route_bundle(replace(bundle, sources=(source, source))).target
        is Target.NO_PUBLISH
    )


def test_blocked_decision_does_not_echo_input_values(bundle, source):
    """Rejection messages are static codes, without restricted source details."""
    changed = replace(source, source_id="restricted-marker", source_class="unknown")
    result = route_bundle(replace(bundle, sources=(changed,)))
    assert result.target is Target.NO_PUBLISH
    assert "restricted-marker" not in repr(result)


def _read_yaml_lines(text):
    """Independently decode the documented YAML mapping of JSON-valued fields."""
    import json

    return {
        key: json.loads(value)
        for key, value in (line.split(": ", 1) for line in text.strip().splitlines())
    }


def test_dry_run_frontmatter_and_manifest(bundle):
    """Expected fields/paths come from #453 body and tightened decision 1.

    Hand construction: slug + '.md' is the page, slug + '.manifest.yaml' is
    its sibling. The page links the sibling; the sibling hashes the exact page
    bytes. There is no circular page/manifest hash and no copied raw input.
    """
    import hashlib

    from worldenergydata.wiki_publication import plan_publication

    plan = plan_publication(bundle)
    assert plan.decision.target is Target.PUBLIC
    page, manifest = plan.writes
    assert page.repository == manifest.repository == "worldenergydata-wiki"
    assert page.path == "wiki/bsee/well-operations/available-data-summary.md"
    assert manifest.path == (
        "wiki/bsee/well-operations/available-data-summary.manifest.yaml"
    )
    _, frontmatter, body = page.content.split("---\n", 2)
    metadata = _read_yaml_lines(frontmatter)
    expected = {
        "visibility": "public-federal-data",
        "license": "public-domain",
        "domain": "bsee",
        "source_authority": "Bureau of Safety and Environmental Enforcement (US DOI)",
        "contribution_status": "us_federal_only",
        "last_license_check": "2026-10-10",
        "sources": ["https://www.data.bsee.gov/"],
        "data_as_of": "2026-10-01",
        "generated_at": "2026-10-11T12:00:00Z",
        "limitations": ["Synthetic contract fixture; no real data."],
        "run_manifest": "available-data-summary.manifest.yaml",
    }
    assert metadata == expected
    assert bundle.findings in body
    assert "[Run manifest](available-data-summary.manifest.yaml)" in body
    record = _read_yaml_lines(manifest.content)
    assert record["run_id"] == bundle.run_id
    assert record["attempt_id"] == bundle.attempt_id
    assert record["code_ref"] == bundle.code_ref
    assert record["catalog_ref"] == bundle.catalog_ref
    assert record["output_sha256"] == hashlib.sha256(page.content.encode()).hexdigest()
    assert (
        record["source_records"][0]["content_sha256"]
        == bundle.sources[0].content_sha256
    )
    assert record["source_records"][0]["dataset_version"] == "synthetic-version"
    assert record["source_records"][0]["derivation_path"] == [
        "synthetic-source",
        "aggregate-summary",
    ]
    assert record["source_records"][0]["retrieved_at"] == "2026-10-10T12:00:00Z"
    assert record["limitations"] == list(bundle.limitations)
    assert record["safety_status"] == "passed"


def test_dry_run_is_deterministic_and_performs_no_io(bundle, monkeypatch):
    import builtins
    import io
    import socket
    from pathlib import Path

    from worldenergydata.wiki_publication import plan_publication

    def forbidden(*args, **kwargs):
        pytest.fail("dry-run attempted filesystem or network access")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(io, "open", forbidden)
        guard.setattr(Path, "mkdir", forbidden)
        guard.setattr(socket, "socket", forbidden)
        assert plan_publication(bundle) == plan_publication(bundle)


def test_no_io_guard_is_restored_before_reporting(bundle, monkeypatch):
    import builtins
    import io
    import socket
    from pathlib import Path

    original = (builtins.open, io.open, Path.mkdir, socket.socket)
    try:
        test_dry_run_is_deterministic_and_performs_no_io(bundle, monkeypatch)
        restored = (builtins.open, io.open, Path.mkdir, socket.socket)
    finally:
        # Restore even on regression so pytest can report the assertion failure.
        monkeypatch.undo()
    assert all(actual is expected for actual, expected in zip(restored, original))


@pytest.mark.parametrize("target", list(Target))
def test_non_public_plans_contain_no_content(bundle, source, target):
    from worldenergydata.wiki_publication import plan_publication

    if target is Target.PUBLIC:
        bundle = replace(bundle, safety_status="NOT_EVALUATED")
    else:
        review = Review(target, target, "synthetic-review")
        source = replace(
            source,
            source_class="private",
            terms_class="restricted-publication-permitted",
            review=review,
        )
        bundle = replace(bundle, sources=(source,), review=review)
    plan = plan_publication(bundle)
    assert plan.writes == ()
    assert bundle.findings not in repr(plan)
    assert source.source_id not in repr(plan)


@pytest.mark.parametrize("field", ["run_id", "attempt_id", "code_ref", "catalog_ref"])
def test_public_references_cannot_be_local_paths(bundle, field, tmp_path):
    from worldenergydata.wiki_publication import plan_publication

    local_path = str(tmp_path / "restricted-input")
    plan = plan_publication(replace(bundle, **{field: local_path}))
    assert plan.decision.target is Target.NO_PUBLISH
    assert not plan.writes
    assert local_path not in repr(plan)


def test_public_source_references_cannot_be_local_paths(bundle, source, tmp_path):
    from worldenergydata.wiki_publication import plan_publication

    changed = replace(source, derivation_path=(str(tmp_path / "restricted-input"),))
    assert plan_publication(replace(bundle, sources=(changed,))).writes == ()


def test_yaml_special_characters_are_data(bundle):
    from worldenergydata.wiki_publication import plan_publication

    bundle = replace(bundle, limitations=('Quoted: "value"\n---\nvisibility: private',))
    plan = plan_publication(bundle)
    page = plan.writes[0]
    _, frontmatter, _ = page.content.split("---\n", 2)
    assert _read_yaml_lines(frontmatter)["limitations"] == list(bundle.limitations)


def test_reordered_sources_produce_identical_plans(bundle, source):
    from worldenergydata.wiki_publication import plan_publication

    other = replace(source, source_id="another-source", dataset_version="other-version")
    a = replace(bundle, sources=(source, other))
    b = replace(bundle, sources=(other, source))
    assert plan_publication(a) == plan_publication(b)


@pytest.mark.parametrize(
    "changes",
    [
        {"data_as_of": "20261001"},
        {"source_url": "https://www.data.bsee.gov:invalid/"},
        {"source_url": "https://@www.data.bsee.gov/"},
        {"source_url": "https://www.data.bsee.gov:443/"},
        {"source_url": "https://www.data.bsee.gov/unsafe path"},
        {"source_authority": "unverified-authority"},
        {"dataset_version": "../restricted-version"},
        {"content_sha256": None},
        {"derivation_path": ["mutable-reference"]},
        {"review": Review("public-federal-data", Target.PUBLIC, "synthetic-review")},
    ],
)
def test_malformed_source_evidence_fails_closed(bundle, source, changes):
    from worldenergydata.wiki_publication import plan_publication

    plan = plan_publication(replace(bundle, sources=(replace(source, **changes),)))
    assert plan.decision.target is Target.NO_PUBLISH
    assert plan.writes == ()


def test_wrong_bundle_type_is_a_safe_denial():
    from worldenergydata.wiki_publication import plan_publication

    assert plan_publication(None).decision.target is Target.NO_PUBLISH


def test_source_review_must_match_destination(bundle, source):
    changed = replace(
        source,
        review=Review(Target.PRIVATE_RESTRICTED, Target.PRIVATE_RESTRICTED, "review"),
    )
    assert route_bundle(replace(bundle, sources=(changed,))).target is Target.NO_PUBLISH


def test_source_timezone_offsets_compare_as_instants(bundle, source):
    """Hand calculation: 13:00 at +01:00 is 12:00 UTC, the generation instant."""
    changed = replace(source, retrieved_at="2026-10-11T13:00:00+01:00")
    assert route_bundle(replace(bundle, sources=(changed,))).target is Target.PUBLIC


def test_generated_yaml_parses_with_safe_loader(bundle):
    import yaml

    from worldenergydata.wiki_publication import plan_publication

    page, manifest = plan_publication(bundle).writes
    _, frontmatter, _ = page.content.split("---\n", 2)
    assert yaml.safe_load(frontmatter) == _read_yaml_lines(frontmatter)
    assert yaml.safe_load(manifest.content) == _read_yaml_lines(manifest.content)


def test_unencodable_narrative_is_blocked(bundle):
    from worldenergydata.wiki_publication import plan_publication

    plan = plan_publication(replace(bundle, findings="unencodable: \ud800"))
    assert plan.decision.target is Target.NO_PUBLISH
    assert plan.writes == ()


def test_control_character_in_citation_is_blocked(bundle, source):
    from worldenergydata.wiki_publication import plan_publication

    changed = replace(source, source_url="\x00https://www.data.bsee.gov/")
    assert plan_publication(replace(bundle, sources=(changed,))).writes == ()
