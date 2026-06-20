"""Citation sidecar emission for worldenergydata calc outputs (#361).

A *sidecar* is a JSON file written next to a primary numeric output (e.g.
``npv_result.json`` -> ``npv_result.citations.json``). It records the provenance
of every standards-derived constant used in the calc WITHOUT mutating the
primary numeric payload -- preserving downstream-consumer compatibility (#361
acceptance criterion: "Citations land on a sidecar; do NOT mutate the primary
numeric payload").

The sidecar round-trips: ``load_sidecar(emit_sidecar(...))`` reconstructs the
exact ``Citation`` objects.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Union

from worldenergydata.citations.schema import Citation, CitedValue

SIDECAR_SCHEMA_VERSION = "1.0.0"
SIDECAR_SUFFIX = ".citations.json"


def _coerce_citation(item: Union[Citation, CitedValue]) -> tuple[str, dict]:
    """Return a ``(name, payload)`` entry for a citation or cited value."""
    if isinstance(item, CitedValue):
        return item.citation.code_id, item.to_dict()
    if isinstance(item, Citation):
        return item.code_id, {"citation": item.to_dict()}
    raise TypeError(f"Expected Citation or CitedValue, got {type(item).__name__}")


def build_sidecar(
    citations: Iterable[Union[Citation, CitedValue]],
    *,
    output_name: str = "",
) -> dict:
    """Build the in-memory sidecar dict for a set of citations / cited values.

    The same ``code_id`` may appear more than once (e.g. a royalty rate cited by
    two calcs); entries are stored as a list to preserve every occurrence.
    """
    entries = []
    for item in citations:
        code_id, payload = _coerce_citation(item)
        entries.append({"code_id": code_id, **payload})
    return {
        "schema_version": SIDECAR_SCHEMA_VERSION,
        "contract": "calc-citation-contract",
        "output": output_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "citations": entries,
    }


def emit_sidecar(
    output_path: Union[str, Path],
    citations: Iterable[Union[Citation, CitedValue]],
) -> Path:
    """Write a citation sidecar next to ``output_path`` and return its path.

    The primary file at ``output_path`` is never read or modified -- only its
    name and directory are used to derive the sidecar path
    (``<stem><SIDECAR_SUFFIX>`` in the same directory).
    """
    output_path = Path(output_path)
    sidecar_path = output_path.with_name(output_path.stem + SIDECAR_SUFFIX)
    data = build_sidecar(citations, output_name=output_path.name)
    sidecar_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return sidecar_path


def load_sidecar(sidecar_path: Union[str, Path]) -> list[Citation]:
    """Load a sidecar file and reconstruct its ``Citation`` objects (round-trip)."""
    data = json.loads(Path(sidecar_path).read_text(encoding="utf-8"))
    return [Citation.from_dict(entry["citation"]) for entry in data["citations"]]
