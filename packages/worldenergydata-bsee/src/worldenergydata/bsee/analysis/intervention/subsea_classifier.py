# ABOUTME: Subsea-vs-dry-tree completion classifier from BSEE data (worldenergydata #584).
# ABOUTME: Flags wells subsea/surface from the SUBSEA_TREE_HEIGHT_AML signal and cross-checks against the authoritative subsea-borehole registry.

"""Subsea-vs-dry-tree completion classifier.

Part of the subsea-intervention/maintenance database (epic #582). A well's
*completion type* — subsea (wet tree, on the seabed) vs. surface/dry-tree
(on a platform) — decides which asset can service it, so it is a key axis of
the maintenance-demand model alongside the water-depth bands of #583.

The primary signal is BSEE's ``SUBSEA_TREE_HEIGHT_AML`` (above-mud-line height
of a subsea tree). The classification rule is:

* a present (non-null, parseable) tree height  -> ``"subsea"`` (a subsea tree
  exists, so the well is a wet-tree completion);
* an empty / null / NaN value                  -> ``"surface"`` (no subsea tree
  recorded -> treated as a dry-tree completion);
* a non-empty but un-parseable value           -> ``"unknown"``.

⚠ Coverage caveat. The only carrier of this flag here,
``current/operations/ST_BP_and_tree_height.csv``, is a **~100-row sample**, not
the full Gulf-of-Mexico well set. The "surface" inference from an empty value
is therefore weak: an absent tree height usually means *not recorded in this
sample*, not a proven dry-tree completion. Counts are reported as such.

Two further BSEE sources give context but **cannot be row-joined** to the
sample:

* **Subsea-borehole registry** (``permstruc/mv_subsea_boreholes.bin``) — 593
  authoritative subsea wells. It has no ``API_WELL_NUMBER`` and the sample CSV
  has no ``WELL_NAME`` string, so :func:`cross_validate` reports a *population*
  overlap (how many subsea wells each source asserts), not a row-level match.
* **Platform-structure registry** (``platstruc/mv_platstruc_structures.bin``) —
  floating hosts (``SPAR``/``TLP``/``SEMI``) are dry-tree-capable; fixed hosts
  (``FIXED``/``CAIS``/``WP``) are not. Used only to tag host-type context.

All numbers are externalised to a reviewable YAML so downstream consumers read
data, not hard-coded constants.
"""

from __future__ import annotations

import math
import pickle
from collections import OrderedDict
from pathlib import Path
from typing import Optional

import pandas as pd

try:  # data-root resolution is best-effort; callers may pass an explicit dir
    from worldenergydata.common.data_resolver import get_module_data_safe
except Exception:  # pragma: no cover - core package may be absent in isolation
    get_module_data_safe = None  # type: ignore[assignment]

# Completion-type labels.
SUBSEA = "subsea"
SURFACE = "surface"
UNKNOWN = "unknown"
COMPLETION_TYPES: tuple[str, ...] = (SUBSEA, SURFACE, UNKNOWN)

TREE_HEIGHT_COL = "SUBSEA_TREE_HEIGHT_AML"
COMPLETION_COL = "completion_type"

# Host structure types that can carry dry-tree completions (floating) vs. the
# fixed/bottom-founded structures. Used purely for host-context tagging.
FLOATING_HOST_TYPES: tuple[str, ...] = ("SPAR", "TLP", "SEMI", "MTLP", "FPSO")
FIXED_HOST_TYPES: tuple[str, ...] = ("FIXED", "CAIS", "WP", "MOPU", "CT")

_CSV_REL = Path("current") / "operations" / "ST_BP_and_tree_height.csv"
_REGISTRY_REL = Path("bin") / "permstruc" / "mv_subsea_boreholes.bin"
_STRUCTURES_REL = Path("bin") / "platstruc" / "mv_platstruc_structures.bin"


# ---------------------------------------------------------------------------
# Classification (pure)
# ---------------------------------------------------------------------------
def classify_completion(subsea_tree_height) -> str:
    """Classify a single well's completion from its subsea-tree height.

    Returns one of ``"subsea"`` / ``"surface"`` / ``"unknown"``:

    * a present, parseable numeric height -> ``"subsea"``;
    * ``None`` / NaN / empty-or-whitespace -> ``"surface"`` (no subsea tree
      recorded; see the module-level caveat about this being a weak signal in a
      sample);
    * a non-empty value that is not a number -> ``"unknown"``.
    """
    if subsea_tree_height is None:
        return SURFACE
    # float NaN (and other non-comparable floats handled below)
    if isinstance(subsea_tree_height, float) and math.isnan(subsea_tree_height):
        return SURFACE
    try:
        if pd.isna(subsea_tree_height):
            return SURFACE
    except (TypeError, ValueError):  # pragma: no cover - defensive
        pass
    if isinstance(subsea_tree_height, str):
        stripped = subsea_tree_height.strip()
        if stripped == "":
            return SURFACE
        try:
            value = float(stripped)
        except ValueError:
            return UNKNOWN
    else:
        try:
            value = float(subsea_tree_height)
        except (TypeError, ValueError):
            return UNKNOWN
    if math.isnan(value):
        return SURFACE
    return SUBSEA


def _zeroed_summary() -> "OrderedDict[str, int]":
    return OrderedDict((t, 0) for t in COMPLETION_TYPES)


# ---------------------------------------------------------------------------
# Table classification + summary (pure — operate on loaded frames)
# ---------------------------------------------------------------------------
def classify_tree_height_table(
    df: pd.DataFrame, tree_height_col: str = TREE_HEIGHT_COL
) -> pd.DataFrame:
    """Return a copy of ``df`` with a ``completion_type`` column appended."""
    if tree_height_col not in df.columns:
        raise KeyError(f"{tree_height_col!r} not in frame (cols={list(df.columns)})")
    out = df.copy()
    out[COMPLETION_COL] = out[tree_height_col].map(classify_completion)
    return out


def summarize_completions(classified: pd.DataFrame) -> "OrderedDict[str, int]":
    """Count rows per completion type; always returns all keys (zero-filled)."""
    counts = _zeroed_summary()
    if COMPLETION_COL not in classified.columns:
        raise KeyError(
            f"{COMPLETION_COL!r} missing; run classify_tree_height_table first."
        )
    observed = classified[COMPLETION_COL].value_counts().to_dict()
    for key, value in observed.items():
        counts[key] = counts.get(key, 0) + int(value)
    return counts


# ---------------------------------------------------------------------------
# Cross-validation against the authoritative subsea registry
# ---------------------------------------------------------------------------
def cross_validate(classified: pd.DataFrame, truth_registry: pd.DataFrame) -> dict:
    """Compare the sample's subsea count to the registry's subsea population.

    The sample CSV carries no ``WELL_NAME`` string and the registry carries no
    ``API_WELL_NUMBER``, so the two cannot be row-joined. This is therefore an
    honest *population* comparison, not a corroboration of individual wells.
    """
    sample_subsea = int(
        (classified.get(COMPLETION_COL) == SUBSEA).sum()
        if COMPLETION_COL in classified.columns
        else 0
    )
    registry_subsea = int(len(truth_registry))
    return {
        "sample_subsea_wells": sample_subsea,
        "sample_total_wells": int(len(classified)),
        "registry_subsea_wells": registry_subsea,
        "row_level_join_possible": False,
        "join_limitation": (
            "Sample CSV has no WELL_NAME and the registry has no "
            "API_WELL_NUMBER; no shared key exists, so wells cannot be matched "
            "one-to-one. Counts are population totals, not corroborated rows."
        ),
        "coverage_gap": (
            "Sample carries the subsea flag for "
            f"{sample_subsea} well(s); the registry lists {registry_subsea} "
            "subsea wells. The sample covers only a small fraction of the "
            "authoritative subsea population."
        ),
    }


def host_type_context(structures: pd.DataFrame) -> "OrderedDict[str, object]":
    """Summarise platform host types into floating (dry-tree-capable) vs fixed."""
    col = "STRUC_TYPE_CODE"
    by_code: "OrderedDict[str, int]" = OrderedDict()
    floating = fixed = other = 0
    if col in structures.columns:
        counts = structures[col].value_counts()
        for code, n in counts.items():
            by_code[str(code)] = int(n)
            if code in FLOATING_HOST_TYPES:
                floating += int(n)
            elif code in FIXED_HOST_TYPES:
                fixed += int(n)
            else:
                other += int(n)
    return OrderedDict(
        [
            ("floating_dry_tree_capable", floating),
            ("fixed_bottom_founded", fixed),
            ("other", other),
            ("by_struc_type_code", dict(by_code)),
        ]
    )


# ---------------------------------------------------------------------------
# Loaders (I/O — thin, so the logic above stays unit-testable)
# ---------------------------------------------------------------------------
def _resolve_data_dir(data_dir: Optional[Path]) -> Path:
    if data_dir is not None:
        return Path(data_dir)
    if get_module_data_safe is not None:
        return Path(get_module_data_safe("bsee"))
    raise RuntimeError(
        "No data_dir given and worldenergydata.common.data_resolver is unavailable."
    )


def _read_pickle_df(path: Path) -> pd.DataFrame:
    with open(path, "rb") as fh:
        obj = pickle.load(fh)
    return obj if isinstance(obj, pd.DataFrame) else pd.DataFrame(obj)


def load_tree_height_table(
    data_dir: Optional[Path] = None, csv_path: Optional[Path] = None
) -> pd.DataFrame:
    """Load the subsea-tree-height sample CSV (the completion-flag carrier)."""
    path = (
        Path(csv_path)
        if csv_path is not None
        else _resolve_data_dir(data_dir) / _CSV_REL
    )
    df = pd.read_csv(path)
    if TREE_HEIGHT_COL not in df.columns:
        raise KeyError(f"{TREE_HEIGHT_COL} not in {path} (cols={list(df.columns)})")
    return df


def load_subsea_registry(
    data_dir: Optional[Path] = None, registry_path: Optional[Path] = None
) -> pd.DataFrame:
    """Load the authoritative subsea-borehole registry (one row per subsea well)."""
    path = (
        Path(registry_path)
        if registry_path is not None
        else _resolve_data_dir(data_dir) / _REGISTRY_REL
    )
    return _read_pickle_df(path)


def load_structures(
    data_dir: Optional[Path] = None, structures_path: Optional[Path] = None
) -> pd.DataFrame:
    """Load the platform-structure registry (host-type context)."""
    path = (
        Path(structures_path)
        if structures_path is not None
        else _resolve_data_dir(data_dir) / _STRUCTURES_REL
    )
    return _read_pickle_df(path)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_classification(
    data_dir: Optional[Path] = None,
    out_path: Optional[Path] = None,
    csv_path: Optional[Path] = None,
    registry_path: Optional[Path] = None,
    structures_path: Optional[Path] = None,
) -> dict:
    """Classify the sample, cross-check it, and (optionally) write a YAML summary.

    The tree-height CSV is required. The subsea registry and platform
    structures are best-effort context: if either file is missing the build
    still succeeds and records the gap in ``caveats``.

    Returns a dict with ``summary`` (completion counts), ``sample_total``,
    ``cross_validation``, ``host_context``, ``provenance`` and ``caveats``.
    """
    table = load_tree_height_table(data_dir=data_dir, csv_path=csv_path)
    classified = classify_tree_height_table(table)
    summary = summarize_completions(classified)
    sample_total = int(len(classified))

    caveats = [
        "SUBSEA_TREE_HEIGHT_AML lives only in ST_BP_and_tree_height.csv, a "
        "~100-row SAMPLE — coverage is limited; this is NOT the full well set.",
        "'surface' is inferred from an empty/absent tree height; absence usually "
        "means 'not recorded in this sample', not a proven dry-tree completion.",
        "Subsea registry has no API_WELL_NUMBER and the sample has no WELL_NAME, "
        "so cross-validation is a population comparison, not a row-level join.",
        "Confidence: subsea flag where present is [on record]; 'surface' counts "
        "are [low-confidence inference]; cross-validation is [population-level].",
    ]

    cross = None
    registry_total = None
    try:
        registry = load_subsea_registry(data_dir=data_dir, registry_path=registry_path)
        cross = cross_validate(classified, registry)
        registry_total = int(len(registry))
    except (FileNotFoundError, OSError, pickle.UnpicklingError) as exc:
        caveats.append(
            f"Subsea registry unavailable; cross-validation skipped ({exc})."
        )

    host_context = None
    try:
        structures = load_structures(data_dir=data_dir, structures_path=structures_path)
        host_context = dict(host_type_context(structures))
    except (FileNotFoundError, OSError, pickle.UnpicklingError) as exc:
        caveats.append(
            f"Platform structures unavailable; host context skipped ({exc})."
        )

    result = {
        "summary": dict(summary),
        "sample_total": sample_total,
        "cross_validation": cross,
        "registry_subsea_total": registry_total,
        "host_context": host_context,
        "provenance": {
            "completion_source": (
                "BSEE current/operations/ST_BP_and_tree_height.csv "
                "(SUBSEA_TREE_HEIGHT_AML; ~100-row sample)"
            ),
            "registry_source": "BSEE permstruc/mv_subsea_boreholes.bin (subsea registry)",
            "structures_source": "BSEE platstruc/mv_platstruc_structures.bin (host types)",
            "rule": (
                "present tree height -> subsea; empty/null -> surface; "
                "non-numeric -> unknown"
            ),
            "issue": "worldenergydata#584 (epic #582)",
        },
        "caveats": caveats,
    }

    if out_path is not None:
        import yaml

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            yaml.safe_dump(result, fh, sort_keys=False, default_flow_style=False)

    return result
