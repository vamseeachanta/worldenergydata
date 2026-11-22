"""Prepare explicit, source-referenced inputs for a riser-fatigue workflow.

This preflight writes data only. It neither imports digitalmodel nor executes an
analysis. Field names follow digitalmodel/riser_fatigue/workflow.py, router,
_wave_damage and _viv_damage, revision 6476218e8f5af3fa7d16c3dafc60b6a9084c6e6c.
No standards-derived coefficient or acceptance limit is supplied by this module.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

_BASIS_FIELDS = {"design_life_years", "dff", "sn_curve", "segments"}


def _fields(value: object, required: set[str], optional: set[str], name: str):
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    missing = required - value.keys()
    unexpected = value.keys() - required - optional
    if missing or unexpected:
        raise ValueError(
            f"{name}: missing {sorted(missing)}, unexpected {sorted(unexpected)}"
        )


def _text(value: object, name: str):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")


def _number(value: object, name: str, *, allow_zero: bool = False):
    # Zero here is a domain bound, not an empirical engineering coefficient.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < 0 or (value == 0 and not allow_zero):
        raise ValueError(
            f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}"
        )


def _wave(wave: object):
    _fields(
        wave,
        {"stress_ranges_MPa", "cycles", "scf", "histogram_period_years"},
        set(),
        "wave",
    )
    for name in ("scf", "histogram_period_years"):
        _number(wave[name], f"wave.{name}")
    for name in ("stress_ranges_MPa", "cycles"):
        values = wave[name]
        if not isinstance(values, list) or not values:
            raise ValueError(f"wave.{name} must be a nonempty list")
        for value in values:
            _number(value, f"wave.{name}", allow_zero=name == "cycles")
    if len(wave["stress_ranges_MPa"]) != len(wave["cycles"]):
        raise ValueError("wave stress_ranges_MPa and cycles must have equal lengths")


def _viv(cases: object):
    if not isinstance(cases, list) or not cases:
        raise ValueError("viv_cases must be a nonempty list")
    for case in cases:
        _fields(
            case,
            {"stress_range_MPa", "frequency_hz", "exposure_fraction"},
            set(),
            "viv_cases",
        )
        for name, value in case.items():
            _number(value, f"viv_cases.{name}")
        # A dimensionless fraction cannot exceed one whole exposure period.
        if case["exposure_fraction"] > 1:
            raise ValueError("viv_cases.exposure_fraction must not exceed one")


def _segments(segments: object):
    if not isinstance(segments, list) or not segments:
        raise ValueError("segments must be a nonempty list")
    identifiers = set()
    for segment in segments:
        _fields(
            segment,
            {"id", "material", "outer_diameter_mm", "wall_thickness_mm"},
            {"wave", "viv_cases"},
            "segment",
        )
        for name in ("id", "material"):
            _text(segment[name], f"segment.{name}")
        if segment["id"] in identifiers:
            raise ValueError("duplicate segment id")
        identifiers.add(segment["id"])
        for name in ("outer_diameter_mm", "wall_thickness_mm"):
            _number(segment[name], f"segment.{name}")
        # Geometry identity: bore diameter = OD - WT - WT, not a code limit.
        if segment["wall_thickness_mm"] >= segment["outer_diameter_mm"] / 2:
            raise ValueError("segment must have a positive bore diameter")
        if not {"wave", "viv_cases"} & segment.keys():
            raise ValueError("segment requires wave or viv_cases")
        if "wave" in segment:
            _wave(segment["wave"])
        if "viv_cases" in segment:
            _viv(segment["viv_cases"])


def prepare_riser_config(payload: dict, results_dir: Path | str) -> dict:
    """Validate an explicit request and return a detached preflight bundle.

    Sources record references for the supplied values; authenticity, load
    provenance, curve availability and engineering suitability remain unverified.
    No directory is created and no input is changed. All optional loading
    contributions, when present, must be complete; downstream defaults are denied.
    """
    _fields(payload, _BASIS_FIELDS | {"sources"}, set(), "input")
    _fields(payload["sources"], _BASIS_FIELDS, set(), "sources")
    for name, source in payload["sources"].items():
        _text(source, f"sources.{name}")
    for name in ("design_life_years", "dff"):
        _number(payload[name], name)
    _fields(payload["sn_curve"], {"curve", "environment"}, set(), "sn_curve")
    for name, value in payload["sn_curve"].items():
        _text(value, f"sn_curve.{name}")
    _segments(payload["segments"])
    if not isinstance(results_dir, (str, Path)):
        raise TypeError("results_dir must be a path")
    _text(str(results_dir), "results_dir")
    settings = copy.deepcopy({name: payload[name] for name in _BASIS_FIELDS})
    settings["output_dir"] = str(results_dir)
    return {
        "workflow_config": {"basename": "riser_fatigue", "riser_fatigue": settings},
        "sources": copy.deepcopy(payload["sources"]),
        "engineering_qualification": "NOT_EVALUATED",
    }


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"duplicate JSON key: {name}")
        result[name] = value
    return result


def _reject_constant(value: str):
    raise ValueError(f"nonfinite JSON number: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Explicit input and sources JSON")
    parser.add_argument("--out", type=Path, required=True, help="New preflight bundle")
    parser.add_argument(
        "--results-dir", required=True, help="Future workflow output directory"
    )
    args = parser.parse_args(argv)
    try:
        raw = args.input.read_bytes()
        payload = json.loads(
            raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        prepared = prepare_riser_config(payload, args.results_dir)
        prepared["input_sha256"] = hashlib.sha256(raw).hexdigest()
        encoded = json.dumps(prepared, indent=2, sort_keys=True, allow_nan=False) + "\n"
        # Exclusive creation preserves the input, including identical output paths.
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    except (OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
