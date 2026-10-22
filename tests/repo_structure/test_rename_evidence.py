"""Executable proposal for report-rename evidence, issue #1341.

Expected results are independent hand deductions written in
docs/standards/report-rename-evidence.md, "Required cases": same bytes plus a
verified approval permits a rename; changed bytes, no destination, a digest of
other bytes, or no provenance must refuse it. SHA-256 is the existing retirement
contract's algorithm; hashlib supplies fixture digests independently of the
checker. No production rename exemption or approval verifier exists yet.
"""

import hashlib

import pytest

from scripts.maintenance import verify_repo_structure as guard


class RenameEvidenceUnavailable(Exception):
    """The proposed validator has not been implemented."""


# Case names and violation codes specify the proposed interface in the design.
CASES = [
    ("legitimate-rename", set()),
    ("unrelated-content-change", {"rename-destination-content-mismatch"}),
    ("deletion", {"rename-destination-missing"}),
    ("stale-digest", {"rename-digest-mismatch"}),
    ("missing-authority", {"rename-authority-missing"}),
]


@pytest.fixture
def rename_case(tmp_path):
    """Use synthetic bytes and a synthetic trust verifier, never real approval."""
    source = "reports/example.txt"
    destination = "reports/renamed.txt"
    original = b"synthetic report\x00unchanged\xff"
    contract = guard.RepoStructureContract(
        allowed_roots=frozenset({"docs"}),
        ignored_roots=frozenset(),
        generated_artifact_roots=frozenset({"reports"}),
        temporary_exceptions={},
    )
    target = tmp_path / destination
    target.parent.mkdir()
    target.write_bytes(original)
    evidence = {
        "source": source,
        "destination": destination,
        "sha256": hashlib.sha256(original).hexdigest(),
        "base_revision": "synthetic-base",
        "authority": "synthetic-authenticated-receipt",
    }

    def prepare(case):
        if case == "unrelated-content-change":
            target.write_bytes(b"different report")
        if case == "deletion":
            # Preserve fixture data: absence is represented by another path.
            evidence["destination"] = "reports/absent.txt"
        if case == "stale-digest":
            evidence["sha256"] = hashlib.sha256(b"different source").hexdigest()
        if case == "missing-authority":
            del evidence["authority"]
        entries = [guard.WorktreeStatusEntry("R ", evidence["destination"], source)]
        if case == "deletion":
            entries = [guard.WorktreeStatusEntry(" D", source)]
        return entries, evidence, contract, tmp_path

    return prepare


@pytest.mark.parametrize("case,expected", CASES)
def test_existing_gate_still_refuses_without_retirement(rename_case, case, expected):
    """Even the legitimate proposal cannot bypass the current retirement rule."""
    entries, _, contract, root = rename_case(case)
    violations = guard.validate_worktree_status_entries(
        entries, contract, repo_root=root
    )
    assert {v.code for v in violations} == {"generated-artifact-deletion-or-relocation"}


@pytest.mark.xfail(
    strict=True,
    raises=RenameEvidenceUnavailable,
    reason="Deferred: authenticated rename approval verifier has not been selected",
)
@pytest.mark.parametrize("case,expected", CASES)
def test_proposed_rename_evidence_contract(rename_case, monkeypatch, case, expected):
    """Specify exact outcomes; missing API alone is an expected failure.

    The source digest is supplied independently here because this is a proposed
    validation interface, not production integration. The fake authority verifier
    stands for a receipt bound to these exact fields. It grants no real authority.
    Integration must additionally check base objects, classification and index
    bytes as described in the design; these tests do not claim that coverage.
    """
    entries, evidence, contract, root = rename_case(case)
    original_digest = hashlib.sha256(b"synthetic report\x00unchanged\xff").hexdigest()
    monkeypatch.setattr(guard, "git_head_digest", lambda root, path: original_digest)

    def verify_authority(record):
        return record.get("authority") == "synthetic-authenticated-receipt"

    # Resolve the intentionally absent API outside any fallback implementation.
    if not hasattr(guard, "validate_rename_evidence"):
        raise RenameEvidenceUnavailable
    validate = guard.validate_rename_evidence
    violations = validate(
        entries, contract, [evidence], root, verify_authority=verify_authority
    )
    assert {v.code for v in violations} == expected
