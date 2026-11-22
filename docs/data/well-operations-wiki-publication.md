# Well-operations wiki publication contract

This contract proposes a destination for a generated insight bundle without
modifying another repository. It implements the routing boundary from issue
#453, including its tightened decisions of 2026-06-08. The first supported public
scope is `all-public-bsee-available-data-summary`. Actual publication remains
pending an upstream bundle, authenticated review and reviewed destination writes.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Define routing and a dry-run projection to prevent ambiguous inputs reaching public pages. |

## Inputs and routing

`worldenergydata.wiki_publication` provides immutable `Source`, `Review` and
`Bundle` records. The upstream adapter must enumerate **every** input. It must
supply the logical run and attempt identifiers, pinned code and catalog
references, source dataset versions, SHA-256 digests, source authorities and URLs,
retrieval timestamps, data vintage, derivation references, license-check date,
limitations and publication decisions. These fields are required inputs; none
is inferred from a directory name or public-looking URL.

`route_bundle(bundle)` returns exactly one `RoutingDecision`:

| Target | Required evidence |
| --- | --- |
| `public-federal-data` | Every input is BSEE public federal data, public-domain, cited on an HTTPS BSEE authority, with matching public publisher and reviewer decisions. The bundle has the same decisions and the supported public scope. |
| `private-generic` | Every input is explicitly private with restricted publication permitted, and all source and bundle decisions select this target. |
| `private-restricted` | The same restricted-use evidence, with all decisions selecting this restricted target. No private repository locator is emitted. |
| `no-publish` | Missing, malformed, unknown, mixed, denied, duplicate or unsupported evidence; failed or unevaluated safety status. |

A failed public gate does not implicitly authorize a private destination.
FDAS, HSE, marine, vendor and ambiguous inputs cannot pass the public gate.
Only generated insights, dataset summaries and methodology content are eligible;
raw data, copied vendor data, private facts and standards-derived text are
blocked by content classification. Private routing is a logical proposal only;
it does not grant reuse rights or choose a repository.

Dates must be valid, retrieval and generation timestamps must include timezones,
and evidence cannot postdate generation. Source vintage cannot postdate retrieval
or the bundle's data vintage. Public identity, version, derivation and review
references are opaque identifiers, without filesystem separators. Public source
URLs have no credentials, port, query or fragment. These conservative constraints
may require an adapter to use a reviewed public landing-page citation.

## Dry-run output

`plan_publication(bundle)` returns a `PublicationPlan`. The function performs no
filesystem or network I/O, reads no environment variables and obtains no current
time. For an eligible public contract, `writes` contains proposed UTF-8 content:

- Repository: `worldenergydata-wiki`.
- Page: `wiki/bsee/well-operations/<slug>.md`.
- Sidecar: `wiki/bsee/well-operations/<slug>.manifest.yaml`.

Slugs are lowercase alphanumeric segments separated by hyphens. Every other
route returns an empty write set and static diagnostic codes, without input
identities, narrative content or private destination paths.

The page's YAML frontmatter carries visibility, license, domain, source authority,
contribution status, license-check date, source URLs, data-as-of, generated-at,
limitations and the relative manifest link. The manifest is an explicit public
metadata projection. It carries run/attempt identity, code/catalog references,
source versions/digests/citations/derivations/reviews, limitations, safety status
and the SHA-256 digest of the exact UTF-8 page bytes. It contains no raw payload.
It is not a replacement for the upstream YAML run manifest or JSONL history.

Both YAML mappings encode values as JSON, preventing frontmatter-key injection.
Source records and URLs are sorted so input enumeration order does not alter the
plan. Unchanged input yields identical proposed bytes. Repeated planning does
not create history or ledger events; applying or superseding writes is deferred.

## Review and refresh gates

`Review.evidence_ref` and `safety_status` are **declarations**, not authenticated
approvals. A caller may set `safety_status` to `passed` only after the extraction,
citation, contamination, determinism, duplicate-ledger, link, legal/security and
generated-diff checks in #453's clean-run definition pass. The planning API does
not execute those checks, inspect raw bytes, scan prose for sensitive facts, or
verify that the supplied source inventory is complete. It must not be used as
an automatic publisher. Unknown or `NOT_EVALUATED` safety outcomes block routing.

No numerical freshness limit is assumed. Freshness assessment and its evidence
belong to the review. No refresh or weekly scheduling is enabled. The clean-manual-
run prerequisite in #453 is deferred until real publication and the ledger exist.

## Sources and later slices

Routing, output paths, frontmatter, exclusions and private/blocked separation:
issue #453 body and tightened decisions, 2026-06-08, items 1–7. Upstream manifest
and workflow integration: issues #450 and #452. Ecosystem schema convergence:
the governing standardization issue #2975. SHA-256 digest syntax follows the
agent data handling contract, Descriptor v1, 2026-09-14. There are no engineering
equations, coefficients or numerical acceptance limits in this contract.

Later work must supply the upstream adapters, authenticated review and content
scans, private destination resolution, safe write application, immutable run
history, routing/promotion ledgers, freshness criteria, link validation and
scheduled refresh. Synthetic tests demonstrate contract behavior; they do not
establish provenance or redistribution rights for an actual dataset.
