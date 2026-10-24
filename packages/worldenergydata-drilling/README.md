# worldenergydata-drilling

## Knowledge pack distribution boundary

The member wheel includes all Markdown under `worldenergydata/drilling/docs/`.
The documented set comprises
[`agent-pack.md`](src/worldenergydata/drilling/docs/agent-pack.md), with DRAFT
status, and `detector-contracts.md`, whose engineering applicability is
**NOT_EVALUATED**. The detector contract is supplied by `main` and is included
when present in the source tree. Each document carries its own status and
qualification limits; inclusion in a wheel does not establish engineering
clearance.

The boundary follows this member's `pyproject.toml`: namespace discovery is
limited to `worldenergydata.drilling*`, and the package-data declaration includes
an explicit `docs/*.md` pattern alongside the recursive patterns. The explicit
pattern supports documentation inclusion with the declared setuptools 61.0
minimum. The member does not own the namespace root
`worldenergydata/__init__.py` or sibling domains.

`tests/unit/drilling/test_packaging.py` builds the member wheel from a temporary
copy, checks an explicit inventory of all non-Python drilling members, compares
every shipped document's bytes with the source, and checks drilling-only Python
ownership. The inventory permits the known detector contract when its source is
present; other data additions require an explicit test update. These checks
establish the wheel boundary only. Source-distribution contents, installation
into a complete workspace, and engineering qualification require separate
evidence.

## Workspace member

`drilling` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 5 final tail, #529).

Importable transparently as `worldenergydata.drilling` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.
