# worldenergydata-drilling

`drilling` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 5 final tail, #529).

Importable transparently as `worldenergydata.drilling` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Knowledge pack distribution boundary

The member wheel intentionally includes all Markdown under
`worldenergydata/drilling/docs/`, currently
[`docs/agent-pack.md`](src/worldenergydata/drilling/docs/agent-pack.md)
as documentation under `worldenergydata/drilling/`. The pack's DRAFT status and
qualification limits travel with the calculations it describes. Inclusion is
not engineering clearance; consult the pack before using the calculations.

The boundary follows this member's `pyproject.toml`: namespace discovery is
limited to `worldenergydata.drilling*`, and the package-data declaration includes
nested Markdown (`**/*.md`), supported by the declared `setuptools>=62.3`
build requirement. The member does not own the namespace root
`worldenergydata/__init__.py` or sibling domains.

### Detector contract integration

The `main` branch also contains `docs/detector-contracts.md` and a README
detector-contract section alongside newer detector behavior. Those changes
are not yet integrated into this branch. Integration must retain both README
sections and the matching implementation. The Markdown distribution rule will
then ship both `agent-pack.md` and `detector-contracts.md`; each document carries
its own status and qualification limits. The exact archive membership test must
be updated with that integration. Distribution alone grants neither document
engineering clearance.

`tests/unit/drilling/test_packaging.py` builds the member wheel from a temporary
copy, inspects its archive, asserts the exact non-Python member set and source
bytes, and checks that Python code remains within the drilling namespace.
It also checks the build requirement's recursive-glob support. This establishes the
wheel boundary only. Source-distribution contents, installation into a complete
workspace, and engineering qualification require separate evidence.
