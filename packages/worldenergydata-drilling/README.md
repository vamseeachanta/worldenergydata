# worldenergydata-drilling

`drilling` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 5 final tail, #529).

Importable transparently as `worldenergydata.drilling` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Knowledge pack distribution boundary

The member wheel intentionally includes
[`docs/agent-pack.md`](src/worldenergydata/drilling/docs/agent-pack.md)
as documentation under `worldenergydata/drilling/`. Its DRAFT status and
qualification limits travel with the calculations it describes. Inclusion is
not engineering clearance; consult the pack before using the calculations.

The boundary follows this member's `pyproject.toml`: namespace discovery is
limited to `worldenergydata.drilling*`, and the package-data declaration includes
nested Markdown (`**/*.md`). The member does not own the namespace root
`worldenergydata/__init__.py` or sibling domains. No packaging change is needed
to include the pack in the wheel.

`tests/unit/drilling/test_packaging.py` builds the member wheel from a temporary
copy, inspects its archive, compares the pack bytes with the source, and checks
that Python code remains within the drilling namespace. This establishes the
wheel boundary only. Source-distribution contents, installation into a complete
workspace, and engineering qualification require separate evidence.
