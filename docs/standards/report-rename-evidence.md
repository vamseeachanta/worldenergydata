# Report rename evidence design

## Summary

A report rename should preserve bytes, classify the destination, and carry
verifiable approval tied to the exact source, destination and base revision.
The proposed exception is deferred: the repository has no authenticated approval
receipt verifier. A submitted URL or a boolean supplied by the change cannot
establish authority. The existing deletion and relocation gate remains in force.
This design adds no retirement entry and moves no report.

## Revision history

| Revision | Date | What changed and why |
|---|---|---|
| Initial | 2026-10-22 | Specify rename evidence and deferred acceptance tests to preserve relocation protection. |

## Existing contract and options

The current [structure standard](repo-structure.md#retiring-a-generated-file)
and `scripts/maintenance/verify_repo_structure.py` require a digest-bound
retirement for a generated source path. A rename also classifies its destination.
The retirement digest binds the committed source bytes; it does not bind the
new bytes or authenticate the approval URL. That retirement mechanism remains
appropriate for retirement, rather than proof of a byte-preserving rename.

| Option | Effect | Assessment |
|---|---|---|
| Accept Git's rename classification alone | Similarity can identify changed content as a rename. | Reject: similarity is not byte equality or permission. |
| Reuse a retirement entry | Keeps the old identifier in the runtime retirement register; does not prove destination equality. | Retain the existing retirement path, but do not call it rename evidence. |
| Change-scoped evidence with authenticated provenance | Bind both paths, base revision and source digest; compare destination bytes independently. | Recommended, pending an approval verifier and integration review. |

Git documents similarity-based rename detection under `--find-renames` in
[git-diff](https://git-scm.com/docs/git-diff). No similarity acceptance threshold
is proposed. Digests use SHA-256, as in the existing retirement contract; raw
bytes must also compare equal. No engineering coefficients or tolerances apply.

## Proposed interface and trust boundary

A future `validate_rename_evidence` entry point in the structure checker takes
status entries, the existing contract, change-scoped evidence, the repository
root and an injected `verify_authority` verifier. It returns structure violations.
The verifier must be provided by a trusted caller, never by a command-line
boolean or by executable content in a proposed change. Tests inject a synthetic
verifier to specify the boundary; it is not a production approval mechanism.

Evidence contains `source`, `destination`, `base_revision`, `sha256` and an
`authority` reference. The authenticated receipt must bind every field to an
explicit maintainer approval for a byte-preserving rename. Merely linking an
issue is insufficient. The verifier must reject an absent, unreadable, stale,
mismatched or unauthenticated receipt. Evidence remains attached to the reviewed
change, not a permanent register of old identifiers loaded at runtime.

Integration must inspect the actual Git operations independently of the evidence,
check the source blob at the pinned base and ensure the destination exists as a
regular file with identical bytes in both the index and working tree. Source
absence, path traversal, symlinks, duplicate destinations, copies presented as
moves and unused evidence cannot grant an exception. Path classification and
all independent policy violations continue to run. Evidence must not exempt
any other deletion or relocation. A relocation into or out of generated roots
must be covered consistently, including Git status expressed as delete/add
rather than a detected rename.

The old classification row may be removed only for the verified source; the new
path still needs classification. The evidence design is a separate policy
change; it must not be introduced into an otherwise path-only report move.

## Required cases

Expected results are hand deductions from byte identity and the authority
boundary, rather than results obtained from the proposed implementation.

| Case | Fixture operation and evidence | Required result |
|---|---|---|
| Legitimate rename | Same committed bytes at the new path, matching digest and authenticated receipt | Accept this relocation only; still classify the new path. |
| Rename with unrelated content change | New path has different bytes despite a matching source digest | Reject with `rename-destination-content-mismatch`; use a separate content change. |
| Deletion | Source removed and destination absent | Reject with `rename-destination-missing`; rename evidence cannot retire a file. |
| Stale digest evidence | Evidence hashes different source bytes | Reject with `rename-digest-mismatch`. |
| Missing authority provenance | Byte-identical move with no authority reference | Reject with `rename-authority-missing`. |

`tests/repo_structure/test_rename_evidence.py` contains strict expected-failure
specifications for these cases. They fail first because the proposed validator
is absent. Only that missing interface is an expected failure; future assertion
failures cannot be hidden by the marker. Once implemented correctly, strict
unexpected passes force removal of the markers. Active companion tests confirm
that today's gate still refuses every case without an approved retirement.
The existing retirement suite remains required and unchanged.

## Recommendation and implementation limit

Do not grant a new exception until the maintainers select an authenticated
receipt source and a trusted validation path. Required integration tests then
include forged authority, wrong revision/path, staged-versus-working-tree
changes, mixed rename/deletion changes and path classification. Keep all existing
deletion and retirement tests. Until then the supported route is the existing
reviewed retirement mechanism, or deferral of the move. This design neither
claims that a URL authenticates authority nor weakens the current gate.
