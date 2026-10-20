"""Replay OpenLane evidence as Markdown, without executing a design flow.

Artifact meanings: OpenLane Newcomers, Run directory / Final Results / Signoff
Steps, rolling documentation retrieved 2026-10-19:
https://openlane2.readthedocs.io/en/latest/getting_started/newcomers/index.html
No engineering coefficients, default limits or unit conversions are applied.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ARTIFACTS = {
    "rtl": "RTL design and logic synthesis",
    "config": "Flow configuration and timing constraints",
    "metrics": "Final metrics and reproducible data extraction",
    "timing": "Static timing analysis and timing closure",
    "power": "Power analysis and activity assumptions",
    "drc": "Design rule checking and physical verification",
    "lvs": "Layout versus schematic and connectivity verification",
    "def": "Placement, routing and physical implementation",
    "gds": "Mask layout and layout exchange",
    "log": "Flow debugging and execution traceability",
}
CATEGORIES = {
    "timing": "Timing",
    "area": "Area",
    "power": "Power",
    "drc": "DRC",
    "lvs": "LVS",
}
PROVENANCE = (
    "openlane_version",
    "container_image_digest",
    "pdk_revision",
    "standard_cell_library",
)


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def _load(path: Path, *, metrics: bool = False) -> dict:
    # Python 3 json, Decoding JSON / parse_float (retrieved 2026-10-19):
    # https://docs.python.org/3/library/json.html#json.load
    # Decimal preserves metric precision and avoids float overflow/underflow.
    data = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_constant=Decimal if metrics else _constant,
        parse_float=Decimal,
    )
    if not isinstance(data, dict):
        raise TypeError("JSON document must be an object")
    return data


def _mapping(value: object, allowed: set, label: str) -> dict:
    if not isinstance(value, dict) or value.keys() - allowed:
        raise ValueError(f"invalid {label} fields")
    return value


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _cell(value: object) -> str:
    text = html.escape(" ".join(str(value).split()))
    for character, entity in (
        ("|", "&#124;"),
        ("`", "&#96;"),
        ("[", "&#91;"),
        ("]", "&#93;"),
    ):
        text = text.replace(character, entity)
    return text


def _artifact_path(root: Path, value: object) -> Path:
    if not _text(value) or any(
        char in value for char in ("\\", ":", "\x00", "\n", "\r")
    ):
        raise ValueError("invalid relative artifact path")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("invalid relative artifact path")
    try:
        candidate = (root / value).resolve()
    except (OSError, RuntimeError) as error:
        raise ValueError("invalid relative artifact path") from error
    if not candidate.is_relative_to(root):
        raise ValueError("artifact escapes evidence root")
    return candidate


def _digest(path: Path) -> str:
    # Python 3 hashlib, Usage / SHA-256 (retrieved 2026-10-19):
    # https://docs.python.org/3/library/hashlib.html#usage
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def build_report(manifest: Path) -> str:
    """Validate a manifest and render evidence. PRESENT/REPORTED are not signoff.

    Paths are relative to the manifest directory. Optional SHA-256 values are
    integrity checks, not authenticity checks. Metric keys and units are explicit
    user inputs; OpenLane keys can vary with the version and timing corner.
    """
    root = manifest.resolve().parent
    data = _mapping(
        _load(manifest), {"provenance", "artifacts", "observations"}, "manifest"
    )
    provenance = _mapping(data.get("provenance", {}), set(PROVENANCE), "provenance")
    for value in provenance.values():
        if value is not None and not _text(value):
            raise ValueError("provenance must contain text or null")
    artifacts = _mapping(data.get("artifacts", {}), set(ARTIFACTS), "artifact")
    observations = _mapping(
        data.get("observations", {}), set(CATEGORIES), "observation"
    )
    inventory = []
    available = {}
    for name, meaning in ARTIFACTS.items():
        entry = artifacts.get(name)
        status, display_path, digest = "NOT_EVALUATED", "not supplied", "unavailable"
        if entry is not None:
            entry = _mapping(entry, {"path", "sha256"}, "artifact entry")
            path = _artifact_path(root, entry.get("path"))
            expected = entry.get("sha256")
            if expected is not None and (
                not isinstance(expected, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected)
            ):
                raise ValueError(f"invalid SHA-256: {name}")
            display_path = entry["path"]
            if path.is_file():
                digest = _digest(path)
                if expected is not None and expected != digest:
                    raise ValueError(f"digest mismatch: {name}")
                status = "PRESENT"
                available[name] = path
            elif path.exists():
                raise ValueError(f"artifact is not a regular file: {name}")
            else:
                display_path += " (missing)"
                if expected is not None:
                    raise ValueError(f"cannot verify expected digest: {name}")
        inventory.append((name, status, display_path, digest, meaning))

    metrics = (
        _load(available["metrics"], metrics=True) if "metrics" in available else {}
    )
    results = []
    for category, title in CATEGORIES.items():
        entry = observations.get(category)
        status, value, evidence = (
            "NOT_EVALUATED",
            "unavailable",
            "metric selection or evidence not supplied",
        )
        if entry is not None:
            entry = _mapping(entry, {"key", "unit", "basis"}, "observation entry")
            if set(entry) != {"key", "unit", "basis"} or not all(
                _text(v) for v in entry.values()
            ):
                raise ValueError(f"key, unit and basis are required: {category}")
            key = entry["key"]
            evidence = f"metrics / {key}; {entry['basis']}"
            if key in metrics:
                numeric = metrics[key]
                if (
                    isinstance(numeric, bool)
                    or not isinstance(numeric, (int, Decimal))
                    or (isinstance(numeric, Decimal) and not numeric.is_finite())
                ):
                    raise ValueError(f"metric must be finite numeric data: {category}")
                status, value = "REPORTED", f"{numeric} {entry['unit']}"
            else:
                evidence += "; key or metrics artifact missing"
        results.append((title, status, value, evidence))

    lines = [
        "# OpenLane artifact replay report",
        "",
        "## Summary",
        "",
        "No flow was executed by this reporter. PRESENT means a file was read;",
        "REPORTED means a finite numeric value was read from the selected metrics key.",
        (
            "Neither status establishes correctness, timing closure, DRC/LVS signoff "
            "or manufacturability."
        ),
        "Missing evidence is NOT_EVALUATED; no acceptance limits are assumed.",
        "",
        "## Revision history",
        "",
        "| Revision | Date | What changed and why |",
        "| --- | --- | --- |",
        "| Initial | 2026-10-19 | Add evidence replay before collecting run evidence. |",
        "",
        "## Recorded environment",
        "",
        (
            "Values are supplied by the manifest; tool execution and provenance "
            "authenticity are not verified."
        ),
        "",
        "| Field | Recorded value |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| {field} | {_cell(provenance.get(field) or 'NOT_EVALUATED')} |"
        for field in PROVENANCE
    )
    lines += [
        "",
        "## Metrics",
        "",
        "Units, corner and analysis assumptions must be checked against the selected tool output.",
        "Values are copied without conversion or rounding; no numerical assessment is performed.",
        "",
        "| Category | Status | Value | Evidence key and basis |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        "| " + " | ".join(_cell(cell) for cell in row) + " |" for row in results
    )
    lines += [
        "",
        "## Artifact inventory and role keywords",
        "",
        "SHA-256 covers the artifact bytes as read; a supplied digest mismatch stops replay.",
        "File presence does not validate the artifact format or contents.",
        "",
        "| Artifact | Status | Relative path | SHA-256 | Semiconductor role keywords |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        "| " + " | ".join(_cell(cell) for cell in row) + " |" for row in inventory
    )
    lines += [
        "",
        "## Interpretation and next steps",
        "",
        (
            "- Timing: inspect setup/hold corners, constraints and unconstrained "
            "paths before claiming closure."
        ),
        (
            "- Area: identify the metric scope; cell area, core area and die area "
            "describe different quantities."
        ),
        (
            "- Power: record corner, activity assumptions and whether the result "
            "is estimated or measured."
        ),
        (
            "- DRC/LVS: inspect the respective reports and tool completion; "
            "missing results never imply clean checks."
        ),
        (
            "- DEF/GDS: retain physical views and logs with the resolved "
            "configuration and PDK revision."
        ),
        "",
        "## Sources",
        "",
        (
            "- [OpenLane Newcomers]("
            "https://openlane2.readthedocs.io/en/latest/getting_started/newcomers/index.html):"
        ),
        "  Run directory, Final Results and Signoff Steps",
        "  (rolling documentation, retrieved 2026-10-19).",
        (
            "- [Python hashlib: SHA-256 and Usage]("
            "https://docs.python.org/3/library/hashlib.html#usage)"
        ),
        "  (Python 3 documentation, retrieved 2026-10-19).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        text = build_report(args.manifest)
    except (OSError, UnicodeError):
        # Do not echo evidence contents, raw paths or potentially sensitive values.
        print(
            "invalid evidence: check manifest schema, artifact paths, digests and metric types",
            file=sys.stderr,
        )
        return 1
    except (TypeError, ValueError) as error:
        # Validation messages contain schema labels, never raw evidence values.
        print(f"invalid evidence: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
