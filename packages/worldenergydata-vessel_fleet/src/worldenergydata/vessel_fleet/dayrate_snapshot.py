"""Public-data day-rate snapshot for the intervention/maintenance supply model.

Part of #596 (child of epic #591). This is the market-cost companion to the
unified intervention-fleet catalog (:mod:`fleet_catalog`, #598): it pairs each
fleet asset class with an indicative public day-rate band so the supply model
can price an intervention/maintenance spread.

The data lives in :data:`DEFAULT_SNAPSHOT_PATH`
(``data/dayrate_snapshot.yml``), a hand-curated, source-cited snapshot pulled
from PUBLIC primary sources only -- issuer Fleet Status Reports (Transocean,
Valaris, Noble), SEC filings, earnings commentary, and dated trade press. It is
explicitly **not** a live 4C Offshore / Bassoe RigLogix / IHS Petrodata feed
(those remain a paywalled USER GATE per #596).

Every figure carries a confidence label:

``on_record``
    Stated in an issuer's published FSR / filing.
``reported``
    Press-announced, or implied from contract value / duration.
``analyst``
    Market-research or forecast band.
``not_public``
    No public per-day figure exists (intervention semis, RLWI monohulls);
    the record carries ``rate_usd_per_day: null`` and a qualitative note.

A record's rate is either a point (``rate_usd_per_day``) or a band
(``rate_low_usd_per_day`` / ``rate_high_usd_per_day``).
:func:`summary_by_asset_class` rolls the records up to a per-class
median + low/high band, and :func:`attach_dayrates_to_catalog` decorates the
fleet catalog's asset classes with those indicative bands.
"""

from __future__ import annotations

import logging
import statistics
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Asset classes that carry an indicative day-rate band in the snapshot.
DAYRATE_ASSET_CLASSES = (
    "modu_drillship",
    "modu_semisub",
    "heavy_intervention_semi",
    "rlwi_monohull",
    "mpsv_osv",
)

# Confidence labels every figure must use (plus ``not_public`` for null rates).
CONFIDENCE_LABELS = ("on_record", "reported", "analyst", "not_public")

_PKG_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_SNAPSHOT_PATH = _PKG_DATA_DIR / "dayrate_snapshot.yml"


def load_dayrate_snapshot(path: Optional[str | Path] = None) -> dict[str, Any]:
    """Load the public day-rate snapshot YAML.

    Args:
        path: Path to the snapshot YAML. Defaults to the packaged
            :data:`DEFAULT_SNAPSHOT_PATH`.

    Returns:
        The parsed snapshot dict (``records``, ``by_asset_class``, ``as_of``,
        ``caveat``, ``sources``, ...).

    Raises:
        FileNotFoundError: If the snapshot file does not exist.
    """
    snap_path = Path(path) if path is not None else DEFAULT_SNAPSHOT_PATH
    if not snap_path.is_file():
        raise FileNotFoundError(f"Day-rate snapshot not found: {snap_path}")
    doc = yaml.safe_load(snap_path.read_text(encoding="utf-8")) or {}
    return doc


def _record_rate_values(record: dict[str, Any]) -> list[float]:
    """Return the numeric rate value(s) a record contributes to a band.

    A point rate contributes one value; a low/high band contributes both. A
    record with no public rate (``not_public``) contributes nothing.
    """
    values: list[float] = []
    point = record.get("rate_usd_per_day")
    if isinstance(point, (int, float)):
        values.append(float(point))
    low = record.get("rate_low_usd_per_day")
    high = record.get("rate_high_usd_per_day")
    if isinstance(low, (int, float)):
        values.append(float(low))
    if isinstance(high, (int, float)):
        values.append(float(high))
    return values


def _record_representative_rate(record: dict[str, Any]) -> Optional[float]:
    """Return one representative rate for a record (point, or band midpoint)."""
    point = record.get("rate_usd_per_day")
    if isinstance(point, (int, float)):
        return float(point)
    low = record.get("rate_low_usd_per_day")
    high = record.get("rate_high_usd_per_day")
    if isinstance(low, (int, float)) and isinstance(high, (int, float)):
        return (float(low) + float(high)) / 2.0
    if isinstance(low, (int, float)):
        return float(low)
    if isinstance(high, (int, float)):
        return float(high)
    return None


def summary_by_asset_class(
    snapshot: Optional[dict[str, Any]] = None,
) -> dict[str, dict[str, Any]]:
    """Roll the snapshot records up to a per-asset-class day-rate band.

    For each asset class with at least one public rate, computes the median of
    representative rates (point rate, or band midpoint) and the overall low/high
    band across every contributing value. Classes with no public rate
    (intervention semis, RLWI monohulls) get a ``rate_disclosed=False`` entry
    with null figures and the set of confidence labels seen.

    Args:
        snapshot: A loaded snapshot dict. If ``None``, loads the default.

    Returns:
        Mapping of asset class -> summary dict with keys ``rate_count``,
        ``median_usd_per_day``, ``band_low_usd_per_day``,
        ``band_high_usd_per_day``, ``rate_disclosed``, and ``confidence_labels``.
    """
    snap = snapshot if snapshot is not None else load_dayrate_snapshot()
    records = snap.get("records", []) or []

    grouped: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        cls = rec.get("asset_class")
        if cls is None:
            continue
        grouped.setdefault(cls, []).append(rec)

    summary: dict[str, dict[str, Any]] = {}
    for cls, recs in grouped.items():
        all_values: list[float] = []
        representatives: list[float] = []
        labels: set[str] = set()
        for rec in recs:
            labels.add(rec.get("confidence", "not_public"))
            all_values.extend(_record_rate_values(rec))
            rep = _record_representative_rate(rec)
            if rep is not None:
                representatives.append(rep)

        if representatives:
            summary[cls] = {
                "rate_count": len(representatives),
                "median_usd_per_day": round(statistics.median(representatives)),
                "band_low_usd_per_day": round(min(all_values)),
                "band_high_usd_per_day": round(max(all_values)),
                "rate_disclosed": True,
                "confidence_labels": sorted(labels),
            }
        else:
            summary[cls] = {
                "rate_count": 0,
                "median_usd_per_day": None,
                "band_low_usd_per_day": None,
                "band_high_usd_per_day": None,
                "rate_disclosed": False,
                "confidence_labels": sorted(labels),
            }
    return summary


def attach_dayrates_to_catalog(
    catalog: dict[str, Any],
    snapshot: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Attach indicative day-rate bands to a fleet catalog's asset classes.

    Decorates each ``by_asset_class`` entry of a fleet catalog (as built by
    :mod:`fleet_catalog`) with an ``indicative_dayrate`` block from the snapshot
    summary, so the supply model can read fleet counts and price bands together.
    The input catalog is not mutated; a deep-ish copy of ``by_asset_class`` is
    returned in a new dict.

    Args:
        catalog: A fleet-catalog dict with a ``by_asset_class`` mapping.
        snapshot: A loaded snapshot dict. If ``None``, loads the default.

    Returns:
        A new catalog dict whose ``by_asset_class`` entries carry an
        ``indicative_dayrate`` key (only for classes the snapshot prices, i.e.
        :data:`DAYRATE_ASSET_CLASSES`).
    """
    snap = snapshot if snapshot is not None else load_dayrate_snapshot()
    summary = summary_by_asset_class(snap)

    by_class = catalog.get("by_asset_class", {}) or {}
    enriched: dict[str, Any] = {}
    for cls, entry in by_class.items():
        new_entry = dict(entry)
        if cls in DAYRATE_ASSET_CLASSES and cls in summary:
            new_entry["indicative_dayrate"] = dict(summary[cls])
        enriched[cls] = new_entry

    result = dict(catalog)
    result["by_asset_class"] = enriched
    result["dayrate_snapshot_as_of"] = snap.get("as_of")
    return result
