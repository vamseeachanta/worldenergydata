# Synthetic portfolio authoring example

## Summary

This executable example shows how a documented profile keeps evidence gaps
unknown when passed to `build_profile_page`. The profile and its citation are
synthetic fixtures, not public evidence or a description of a real development.
The only populated engineering input is a fixture concept label. Unsupported
numerical inputs remain `None`, render as `Unknown`, and do not become layout,
recommendation or economics results.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-26 | Added a runnable synthetic fixture to demonstrate unknown inputs and required citations. |

## Evidence contract

The documented route in
[`build_fdp_portfolio.py`](../../../scripts/field_development/build_fdp_portfolio.py)
requires a nonempty `evidence` mapping. Each populated parameter needs an
`input_sources` entry with a source key and a scope comment. The source key must
refer to an entry in `evidence`. Removing the citation for `concept_type` raises
`ValueError: Missing input citation: concept_type`.

The fixture below supplies the metadata consumed by the renderer: `title`,
`url`, `publication_date`, `kind`, `accessed_at`, `http_status` and `sha256`.
The `example.invalid` URL is an inert fixture citation and must never be treated
as public evidence. The dates are fixture metadata, `NOT_FETCHED` explicitly
records that no HTTP request occurred, and the digest covers the in-memory
fixture text rather than a downloaded publication. No numerical engineering
value is established by that text.

The generated page includes its own summary and revision history. Its
architecture, recommended concept shortlist, and economics and execution
sections remain `NOT_EVALUATED`. The report is an authoring demonstration;
use qualified, scope-matched evidence before populating actual engineering inputs.

## Executable example

Run from the repository root with the Python environment prepared. The named
fence `portfolio-authoring-example` accepts an output directory through
`FDP_EXAMPLE_OUTPUT_DIR`. Set it to scratch outside the checkout; the example
rejects destinations within the checkout. It writes only
`synthetic-example.html` there and performs no source download. The smoke tests
execute this fence verbatim with a temporary output directory.

```python portfolio-authoring-example
import hashlib
import importlib.util
import os
from pathlib import Path

repo_root = Path.cwd().resolve()
spec = importlib.util.spec_from_file_location(
    "portfolio_example_builder",
    repo_root / "scripts/field_development/build_fdp_portfolio.py",
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

# Fixture text supplies only this concept label, never numerical design inputs.
fixture_text = "Synthetic fixture: concept_type is semisub_fps.\n"
profile = {
    "name": "Synthetic Example",
    "concept_type": "semisub_fps",
    "operator_current": None,
    "host_facility": None,
    "fluid": None,
    "water_depth_m": None,
    "num_wells": None,
    "plateau_boed": None,
    "reported_oil_capacity_bpd": None,
    "recoverable_reserves_mmboe": None,
    "first_oil_year": None,
    "tieback_distance_km": None,
    "authored_date": "2026-10-26",
    "summary": (
        "Synthetic authoring fixture, not public evidence. "
        "Only the concept label is supplied; numerical inputs are unknown."
    ),
    "narrative": (
        "The in-memory fixture labels a semisubmersible production concept. "
        "It provides no basis for concept selection or feasibility conclusions."
    ),
    "architecture": (
        "No well coordinates, manifold counts or connection lengths are supplied."
    ),
    "limitations": (
        "Fixture only; not public evidence. Replace fixture metadata with "
        "qualified sources and cite each populated input before engineering use."
    ),
    "evidence": {
        "synthetic-source": {
            "title": "Synthetic authoring fixture; not public evidence",
            "url": "https://example.invalid/portfolio-fixture",
            "publication_date": "2026-10-26 (fixture date)",
            "kind": "in-memory fixture; no download",
            "accessed_at": "2026-10-26 (fixture date; no retrieval)",
            "http_status": "NOT_FETCHED (fixture)",
            "sha256": hashlib.sha256(fixture_text.encode("utf-8")).hexdigest(),
        },
    },
    "input_sources": {
        "concept_type": {
            "source": "synthetic-source",
            "comment": "Fixture concept label only; no engineering validation.",
        },
    },
}


def write_example(output_dir):
    destination = Path(output_dir).resolve()
    if destination.is_relative_to(repo_root):
        raise ValueError("Choose an output directory outside the checkout.")
    page = builder.build_profile_page(profile)
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "synthetic-example.html"
    output.write_text(page, encoding="utf-8", newline="\n")
    return output


if __name__ == "__main__":
    write_example(os.environ["FDP_EXAMPLE_OUTPUT_DIR"])
```

For example, execute the exact named fence with scratch selected by `TMPDIR`:

```bash
export FDP_EXAMPLE_OUTPUT_DIR="${TMPDIR:?Set TMPDIR outside the checkout}/portfolio-authoring-example"
export PYTHONPATH="src:packages/worldenergydata-core/src${PYTHONPATH:+:$PYTHONPATH}"
uv run --no-sync python - <<'PY'
from pathlib import Path
import re

document = Path("docs/data-sources/field-development/portfolio-authoring-example.md")
(code,) = re.findall(
    r"^```python portfolio-authoring-example\n(.*?)^```$",
    document.read_text(encoding="utf-8"),
    flags=re.MULTILINE | re.DOTALL,
)
exec(compile(code, str(document), "exec"), {"__name__": "__main__"})
PY
```

This calls the documented profile renderer directly. The portfolio CLI,
portfolio configuration and committed reports are outside this example.
