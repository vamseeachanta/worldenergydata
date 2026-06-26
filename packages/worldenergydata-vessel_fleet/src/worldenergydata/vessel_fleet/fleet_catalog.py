"""Unified intervention-fleet catalog (#598, child of epic #591).

The supply-side deliverable that feeds Chuck's brief (#588). It folds together
three populations into one asset-class taxonomy:

1. The named, dedicated well-intervention fleet (``intervention_vessels_seed.yml``)
   -- the riser-capable heavy semis (Helix Q-class) and light RLWI monohulls
   (Island Offshore) that are the real supply constraint.
2. The broad curated drilling-rig roster (``drilling_rigs.csv``).
3. The broad curated construction-vessel roster (``construction_vessels.csv``).

Each unit is classified into a coarse :func:`classify_asset_class` bucket, then
aggregated at the **class level only**: count, water-depth-capability range,
and (for the dedicated fleet) the named flagship units. The committed YAML
carries those aggregates plus a reconciliation block to the research figures --
never the full per-vessel roster (that stays in the gitignored curated CSVs).

Confidence labels follow the brief's convention:
``on_record`` (hard count), ``soft`` (estimate, wide band), ``projected``.

De-duplication across sources (IMO keying) is intentionally deferred to #599;
this catalog therefore treats the three populations as additive and flags the
overlap as a caveat.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# --- Asset-class taxonomy ---------------------------------------------------

ASSET_CLASSES = (
    "modu_drillship",
    "modu_semisub",
    "modu_jackup",
    "heavy_intervention_semi",
    "rlwi_monohull",
    "mpsv_osv",
    "lift_boat",
    "construction_vessel",
    "other",
)

# --- Default data locations -------------------------------------------------

# Curated CSVs are gitignored; default to the main checkout that mounts them.
DEFAULT_CURATED_DIR = Path(
    "/mnt/local-analysis/worldenergydata/data/modules/vessel_fleet/curated"
)
_PKG_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_SEED_PATH = _PKG_DATA_DIR / "intervention_vessels_seed.yml"
DEFAULT_OUT_PATH = _PKG_DATA_DIR / "intervention_fleet_catalog.yml"

_DRILLING_RIGS_FILE = "drilling_rigs.csv"
_CONSTRUCTION_VESSELS_FILE = "construction_vessels.csv"

_FT_PER_M = 1.0 / 0.3048

# --- Research reconciliation targets (Chuck's brief #588) -------------------

_RECONCILIATION = {
    "gom_resident_dedicated_intervention_vessels": {
        "figure": "2-4",
        "confidence": "soft",
        "note": "GoM-resident dedicated intervention units; small population",
    },
    "global_rlwi_fleet": {
        "figure": "15-25",
        "confidence": "soft",
        "note": "global riserless light well-intervention fleet, +/-30-50%",
    },
    "helix_purpose_built_units": {
        "figure": "7-8",
        "confidence": "soft",
        "note": "Helix purpose-built well-intervention units worldwide",
    },
    "rigs_rated_20k_psi_worldwide": {
        "figure": "2",
        "confidence": "on_record",
        "note": "only two rigs worldwide rated to 20,000 psi",
    },
}

# Helix Q-class hull numbers -> heavy intervention semis.
_HELIX_Q_NAMES = ("q4000", "q5000", "q7000")
# Island Offshore RLWI monohull family + Skandi sister.
_RLWI_NAME_HINTS = (
    "island performer",
    "island wellserver",
    "island constructor",
    "skandi constructor",
)


def classify_asset_class(
    rig_type: Optional[str] = None,
    vessel_type: Optional[str] = None,
    name: Optional[str] = None,
) -> str:
    """Classify a single asset into one of :data:`ASSET_CLASSES`.

    Resolution order: explicit named-fleet hints (Helix Q-class, Island RLWI)
    win first, then ``vessel_type`` (construction/intervention taxonomy), then
    ``rig_type`` (MODU taxonomy). Falls back to ``"other"``.

    Args:
        rig_type: ``RIG_TYPE`` from the curated drilling-rig roster.
        vessel_type: ``VESSEL_TYPE`` from the curated construction roster or the
            seed (e.g. ``rlwi_monohull``, ``heavy_intervention_semi``).
        name: Vessel / rig name (used for the named-fleet hints).

    Returns:
        One of :data:`ASSET_CLASSES`.
    """
    nm = (name or "").strip().lower()
    if nm:
        if any(q in nm for q in _HELIX_Q_NAMES):
            return "heavy_intervention_semi"
        if any(hint in nm for hint in _RLWI_NAME_HINTS):
            return "rlwi_monohull"

    vt = (vessel_type or "").strip().lower()
    if vt:
        if vt == "rlwi_monohull":
            return "rlwi_monohull"
        if vt == "heavy_intervention_semi":
            return "heavy_intervention_semi"
        if vt in {"mpsv", "psv", "ahts", "osv", "msiv"}:
            return "mpsv_osv"
        if vt in {"heavy_lift", "crane_vessel", "pipelay_vessel", "surf_vessel"}:
            return "construction_vessel"
        if vt == "lift_boat":
            return "lift_boat"

    rt = (rig_type or "").strip().lower()
    if rt:
        if rt == "drillship":
            return "modu_drillship"
        if rt in {"semi_submersible", "semisubmersible", "semi"}:
            return "modu_semisub"
        if rt in {"jack_up", "jackup"}:
            return "modu_jackup"
        if rt == "lift_boat":
            return "lift_boat"

    return "other"


# --- Loaders ----------------------------------------------------------------


def _load_seed(seed_path: Path) -> list[dict[str, Any]]:
    """Load the dedicated-intervention seed roster from YAML."""
    if not seed_path.is_file():
        logger.warning("Seed file not found: %s; using empty roster", seed_path)
        return []
    doc = yaml.safe_load(seed_path.read_text(encoding="utf-8")) or {}
    return list(doc.get("vessels", []))


def _read_curated_csv(path: Path) -> list[dict[str, str]]:
    """Read a curated CSV into a list of row dicts (empty if missing)."""
    if not path.is_file():
        logger.warning("Curated CSV not found: %s; skipping", path)
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _to_float(value: Any) -> Optional[float]:
    """Parse a numeric cell to float, returning None on blank / bad input."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


# --- Aggregation ------------------------------------------------------------


class _ClassAccumulator:
    """Accumulates count, depth range, and flagship names for one class."""

    def __init__(self) -> None:
        self.count = 0
        self.min_ft: Optional[float] = None
        self.max_ft: Optional[float] = None
        self.flagships: list[str] = []

    def add(
        self,
        depth_ft: Optional[float],
        *,
        flagship: Optional[str] = None,
    ) -> None:
        self.count += 1
        if depth_ft is not None:
            self.min_ft = (
                depth_ft if self.min_ft is None else min(self.min_ft, depth_ft)
            )
            self.max_ft = (
                depth_ft if self.max_ft is None else max(self.max_ft, depth_ft)
            )
        if flagship and flagship not in self.flagships:
            self.flagships.append(flagship)

    def summary(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "water_depth_capability_ft": {
                "min": round(self.min_ft, 1) if self.min_ft is not None else None,
                "max": round(self.max_ft, 1) if self.max_ft is not None else None,
            },
            "named_flagship_units": list(self.flagships),
        }


def build_fleet_catalog(
    curated_dir: Optional[str | Path] = None,
    seed_path: Optional[str | Path] = None,
    out_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Build the unified intervention-fleet catalog and emit the summary YAML.

    Loads the dedicated-intervention seed plus the curated drilling-rig and
    construction-vessel rosters, classifies every unit into an asset class, and
    aggregates at the class level (count, water-depth range in ft, named
    flagship units from the seed). Adds a GoM-resident dedicated-intervention
    summary and a reconciliation block to the research figures.

    Args:
        curated_dir: Directory holding ``drilling_rigs.csv`` and
            ``construction_vessels.csv``. Defaults to
            :data:`DEFAULT_CURATED_DIR` (the main checkout). Missing files are
            skipped with a warning so CI degrades gracefully.
        seed_path: Path to ``intervention_vessels_seed.yml``. Defaults to the
            packaged seed.
        out_path: Where to write ``intervention_fleet_catalog.yml``. Defaults to
            the package ``data/`` dir. Pass ``None`` only via the default; set to
            an explicit path (or use the return value) to avoid writing.

    Returns:
        The catalog dict (also serialised to ``out_path``).
    """
    curated = Path(curated_dir) if curated_dir is not None else DEFAULT_CURATED_DIR
    seed_p = Path(seed_path) if seed_path is not None else DEFAULT_SEED_PATH
    out_p = Path(out_path) if out_path is not None else DEFAULT_OUT_PATH

    accumulators: dict[str, _ClassAccumulator] = {
        cls: _ClassAccumulator() for cls in ASSET_CLASSES
    }
    gom_dedicated: list[dict[str, Any]] = []

    # 1. Seed (dedicated intervention fleet) -- named flagship units.
    seed_vessels = _load_seed(seed_p)
    for v in seed_vessels:
        name = v.get("name")
        cls = classify_asset_class(vessel_type=v.get("vessel_type"), name=name)
        depth_m = _to_float(v.get("water_depth_rating_m"))
        depth_ft = depth_m * _FT_PER_M if depth_m is not None else None
        accumulators[cls].add(depth_ft, flagship=name)
        if v.get("gom_resident") is True:
            gom_dedicated.append(
                {
                    "name": name,
                    "intervention_class": v.get("intervention_class"),
                    "asset_class": cls,
                    "water_depth_rating_m": depth_m,
                }
            )

    # 2. Curated drilling rigs.
    for row in _read_curated_csv(curated / _DRILLING_RIGS_FILE):
        cls = classify_asset_class(
            rig_type=row.get("RIG_TYPE"), name=row.get("RIG_NAME")
        )
        accumulators[cls].add(_to_float(row.get("WATER_DEPTH_RATING_FT")))

    # 3. Curated construction vessels (depth is in metres here).
    for row in _read_curated_csv(curated / _CONSTRUCTION_VESSELS_FILE):
        cls = classify_asset_class(
            vessel_type=row.get("VESSEL_TYPE"), name=row.get("VESSEL_NAME")
        )
        depth_m = _to_float(row.get("WATER_DEPTH_RATING_M"))
        depth_ft = depth_m * _FT_PER_M if depth_m is not None else None
        accumulators[cls].add(depth_ft)

    by_class = {
        cls: accumulators[cls].summary()
        for cls in ASSET_CLASSES
        if accumulators[cls].count > 0
    }
    total_units = sum(acc.count for acc in accumulators.values())

    catalog: dict[str, Any] = {
        "catalog": "unified_intervention_fleet",
        "issue": 598,
        "epic": 591,
        "feeds": "Chuck brief #588",
        "asset_class_taxonomy": list(ASSET_CLASSES),
        "totals": {
            "units_classified": total_units,
            "seed_dedicated_units": len(seed_vessels),
        },
        "by_asset_class_scope": (
            "GLOBAL available roster (curated contractor/BSEE fleet + seed), "
            "NOT GoM-resident. These are worldwide fleet counts; for GoM supply "
            "use gom_resident_dedicated_intervention below."
        ),
        "by_asset_class": by_class,
        "gom_resident_dedicated_intervention": {
            "count": len(gom_dedicated),
            "confidence": "soft",
            "units": gom_dedicated,
        },
        "reconciliation_to_research": _RECONCILIATION,
        "provenance": {
            "seed": str(seed_p.name),
            "curated_dir": str(curated),
            "curated_files": [_DRILLING_RIGS_FILE, _CONSTRUCTION_VESSELS_FILE],
        },
        "caveats": [
            "Curated CSV rosters may be stale (snapshot, not live).",
            "Drive-corpus historical fleet records date to 2010-2014.",
            "Populations are additive: dedup vs IMO is deferred to #599, so "
            "counts may double-count a unit present in both seed and curated.",
            "Water-depth ratings are nameplate vendor figures and approximate.",
            "by_asset_class counts are GLOBAL fleet, not GoM-resident supply; "
            "MODU/jackup counts include shelf + non-GoM assets. The binding GoM "
            "intervention supply is gom_resident_dedicated_intervention (~2-4).",
            "mpsv_osv is under-counted: the ~500-vessel OSV/MPSV roster awaits "
            "the vendor-scrape ingest (#593).",
        ],
    }

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(
        yaml.safe_dump(catalog, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    logger.info(
        "Wrote intervention-fleet catalog (%d units, %d classes) to %s",
        total_units,
        len(by_class),
        out_p,
    )
    return catalog
