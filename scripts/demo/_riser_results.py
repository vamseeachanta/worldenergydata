# ABOUTME: Validate imported riser fatigue summaries without executing an analysis.
# ABOUTME: Require a sourced, factored life criterion rather than assume a design factor.

"""Data-only adapter for the digitalmodel riser_fatigue summary CSV contract.

Source: digitalmodel, riser_fatigue/workflow.py, _evaluate_segment (2026).
The summary carries segment_id, wave_damage, viv_damage and fatigue_life_years.
Optional required_life_years must match the caller's criterion on every row;
optional passes_dff must agree with the life comparison on every row.
No S-N equation, coefficient, DFF or engineering acceptance limit is embedded here.
Required factored life and its documentary source are supplied by the caller.
An imported result is not evidence that a live calculation ran in this process.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
from pathlib import Path

from worldenergydata.hse.grounding_card import AnalysisSummary


def _number(value: str, name: str, *, positive: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}") from exc
    # Zero is the mathematical lower bound of damage, not a design limit.
    if not math.isfinite(number) or number < 0 or (positive and number == 0):
        raise ValueError(f"Invalid {name}")
    return number


def analysis_from_csv(
    path: Path, required_life_years: float, basis_source: str
) -> AnalysisSummary:
    """Validate every segment before comparing minimum life with the given criterion.

    Nonfinite life (including zero-damage infinite life) is deliberately withheld;
    this adapter does not qualify extrapolation or an unbounded fatigue life.
    The digest identifies imported bytes; it does not authenticate their origin.
    """
    required = _number(required_life_years, "required factored life", positive=True)
    if not basis_source.strip():
        raise ValueError("A criterion source is required")
    payload = path.read_bytes()
    # Parse the same bytes that are hashed, avoiding a read/hash race.
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    fields = {"segment_id", "fatigue_life_years", "wave_damage", "viv_damage"}
    if not fields <= set(reader.fieldnames or ()):
        raise ValueError("Incomplete riser fatigue summary columns")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("Ambiguous duplicate CSV columns")
    segments = []
    identifiers = set()
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Ambiguous CSV row width")
        identifier = (row["segment_id"] or "").strip()
        if not identifier or identifier in identifiers:
            raise ValueError("Missing or duplicate segment_id")
        identifiers.add(identifier)
        life = _number(row["fatigue_life_years"], "fatigue_life_years", positive=True)
        wave = _number(row["wave_damage"], "wave_damage")
        viv = _number(row["viv_damage"], "viv_damage")
        if "required_life_years" in row:
            imported_required = _number(
                row["required_life_years"], "required_life_years", positive=True
            )
            if imported_required != required:
                raise ValueError("required_life_years mismatch with supplied criterion")
        if "passes_dff" in row:
            imported_pass = row["passes_dff"]
            if imported_pass not in {"True", "False"}:
                raise ValueError("Invalid passes_dff: expected True or False")
            if (imported_pass == "True") != (life >= required):
                raise ValueError("passes_dff disagrees with fatigue life comparison")
        segments.append((life, identifier, wave, viv))
    if not segments:
        raise ValueError("Empty riser fatigue summary")
    life, identifier, wave, viv = min(segments, key=lambda segment: segment[0])
    relation = "meets" if life >= required else "below"
    life_label, required_label = f"{life:,.1f}", f"{required:,.1f}"
    if life != required and life_label == required_label:
        # Round-trip precision preserves distinctions hidden by one-decimal labels.
        life_label, required_label = repr(life), repr(required)
    return AnalysisSummary(
        title="Riser fatigue analysis — imported summary",
        headline=(
            f"Minimum fatigue life {life_label} yr at segment {identifier} — "
            f"{relation} the {required_label}-yr required factored life."
        ),
        metrics=[
            (f"{life_label} yr", "Min fatigue life"),
            (f"{wave:.3f}", "Wave damage"),
            (f"{viv:.3f}", "VIV damage"),
            (f"{required_label} yr", "Required factored life"),
        ],
        method="Imported digitalmodel riser_fatigue summary; no solver executed.",
        basis=(
            f"Imported CSV SHA-256: {hashlib.sha256(payload).hexdigest()}. "
            f"Criterion source: {basis_source.strip()}. "
            "Source authenticity, loading provenance and engineering qualification "
            "are NOT_EVALUATED; comparison applies only to the supplied rows."
        ),
    )
