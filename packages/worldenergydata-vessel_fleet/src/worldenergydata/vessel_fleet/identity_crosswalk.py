"""Real-corpus runner for the vessel identity resolver (#599).

Assembles the real fleet corpus (curated ``drilling_rigs.csv`` +
``construction_vessels.csv`` + the #593 OSV roster + the #598 dedicated
intervention seed), runs :mod:`identity_resolver` over it, and writes the
aggregate ``data/identity_crosswalk.yml`` cluster summary -- including the
specific fix to the #598 ``heavy_intervention_semi`` double-count (the Helix-Q
hull-name semis).

Only the AGGREGATE summary is committed; the full per-vessel row dump stays in
the gitignored curated CSVs.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Optional

from worldenergydata.vessel_fleet.identity_resolver import (
    canonicalize_name,
    dedupe_catalog,
    resolve_identities,
)

logger = logging.getLogger(__name__)

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_CURATED_DIR = _THIS_DIR / "_data" / "curated"
_DATA_DIR = _THIS_DIR / "data"
DEFAULT_CROSSWALK_PATH = _DATA_DIR / "identity_crosswalk.yml"

# Helix Q-class hull-name variants seen across BSEE WAR / contractor sources.
# These are spelling/marketing variants of the SAME three physical semis, used
# as the aka seed that collapses the #598 heavy_intervention_semi double-count.
_HELIX_Q_AKA: dict[str, list[str]] = {
    "Q4000": [
        "Q-4000",
        "HELIX Q4000",
        "HELIX Q-4000",
        "HELIZ Q4000",
        "MSV Q4000",
        "SV Q4000",
        "CALDIVE Q4000",
        "CALDIVE'S Q4000 DP",
    ],
    "Q5000": ["HELIX Q5000"],
    "Q7000": ["HELIX Q7000"],
}


def _classify(name: Optional[str], rig_type: Optional[str], vessel_type: Optional[str]):
    """Best-effort asset-class label (imported lazily to avoid a hard dep)."""
    try:
        from worldenergydata.vessel_fleet.fleet_catalog import classify_asset_class

        return classify_asset_class(
            rig_type=rig_type, vessel_type=vessel_type, name=name
        )
    except Exception:  # pragma: no cover - classification is best-effort
        return "other"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        logger.warning("Curated CSV not found: %s", path)
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _aka_for(name: Optional[str]) -> list[str]:
    """Attach the curated Helix-Q aka list to the canonical hull-token record."""
    if not name:
        return []
    canon = canonicalize_name(name)
    return list(_HELIX_Q_AKA.get(canon, []))


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except Exception:  # pragma: no cover
        return {}
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_seed_records() -> list[dict[str, Any]]:
    doc = _load_yaml(_DATA_DIR / "intervention_vessels_seed.yml")
    out: list[dict[str, Any]] = []
    for v in doc.get("vessels", []) or []:
        name = v.get("name")
        out.append(
            {
                "name": name,
                "operator": v.get("operator") or None,
                "owner": v.get("operator") or None,
                "imo": None,
                "mmsi": None,
                "aka": _aka_for(name),
                "source": "intervention_vessels_seed.yml",
                "class": _classify(name, None, v.get("vessel_type")),
            }
        )
    return out


def _load_roster_records() -> list[dict[str, Any]]:
    doc = _load_yaml(_DATA_DIR / "intervention_osv_roster.yml")
    out: list[dict[str, Any]] = []
    for v in doc.get("vessels", []) or []:
        name = v.get("vessel_name")
        out.append(
            {
                "name": name,
                "operator": v.get("operator") or None,
                "owner": v.get("owner") or None,
                "imo": None,
                "mmsi": None,
                "aka": _aka_for(name),
                "source": "intervention_osv_roster.yml",
                "class": _classify(name, None, v.get("vessel_type")),
            }
        )
    return out


def load_corpus_records(
    curated_dir: Optional[Path] = None,
    include_yaml: bool = True,
) -> list[dict[str, Any]]:
    """Assemble the real fleet corpus as resolver input records.

    Sources: curated ``drilling_rigs.csv`` + ``construction_vessels.csv`` plus
    (when importable) the #593 OSV roster and #598 dedicated-intervention seed.
    Each record carries name/operator/owner/imo/mmsi/aka/source/class.
    """
    curated = Path(curated_dir) if curated_dir else _DEFAULT_CURATED_DIR
    records: list[dict[str, Any]] = []

    for row in _read_csv_rows(curated / "drilling_rigs.csv"):
        name = row.get("RIG_NAME") or row.get("VESSEL_NAME")
        records.append(
            {
                "name": name,
                "operator": row.get("OPERATOR") or None,
                "owner": row.get("OWNER") or None,
                "imo": row.get("IMO_NUMBER") or None,
                "mmsi": None,
                "aka": _aka_for(name),
                "source": "drilling_rigs.csv",
                "class": _classify(name, row.get("RIG_TYPE"), None),
            }
        )

    for row in _read_csv_rows(curated / "construction_vessels.csv"):
        name = row.get("VESSEL_NAME")
        records.append(
            {
                "name": name,
                "operator": row.get("OPERATOR") or None,
                "owner": row.get("OWNER") or None,
                "imo": row.get("IMO_NUMBER") or None,
                "mmsi": row.get("MMSI") or None,
                "aka": _aka_for(name),
                "source": "construction_vessels.csv",
                "class": _classify(name, None, row.get("VESSEL_TYPE")),
            }
        )

    if include_yaml:
        records.extend(_load_seed_records())
        records.extend(_load_roster_records())
    return records


def build_identity_crosswalk(
    curated_dir: Optional[Path] = None,
    out_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Run the resolver over the real corpus and write the crosswalk summary.

    Writes an AGGREGATE YAML (cluster summary + the #598 heavy-intervention-semi
    fix), never the full per-row dump.
    """
    import yaml

    records = load_corpus_records(curated_dir=curated_dir)
    deduped, report = dedupe_catalog(records)
    clusters = resolve_identities(records)

    crosswalk = {
        "crosswalk": "vessel_identity_resolution",
        "issue": 599,
        "epic": 591,
        "key_basis": (
            "normalized canonical name + operator/owner compatibility, with an "
            "aka (alternate-name) list; IMO/MMSI used only as a confirmer when "
            "present (IMO coverage in the bulk corpus is ~0%)."
        ),
        "summary": report,
        "heavy_intervention_semi_fix": _helix_q_fix(clusters),
        "sources_reconciled": sorted({r["source"] for r in records}),
        "provenance": {
            "curated_dir": "vessel_fleet/_data/curated (gitignored, mounted)",
            "note": (
                "Aggregate cluster summary only -- the full per-vessel row dump "
                "stays in the gitignored curated CSVs."
            ),
        },
    }

    out_p = Path(out_path) if out_path else DEFAULT_CROSSWALK_PATH
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(
        yaml.safe_dump(crosswalk, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    logger.info(
        "identity_crosswalk: %d records -> %d distinct vessels (%d collapsed)",
        report["records_in"],
        report["distinct_vessels_out"],
        report["duplicates_collapsed"],
    )
    return crosswalk


def _helix_q_fix(clusters: list[dict[str, Any]]) -> dict[str, Any]:
    """Document the specific Helix-Q hull-name double-count collapse."""
    q_clusters = []
    for c in clusters:
        if c["canonical_name"] in _HELIX_Q_AKA and c["member_count"] > 1:
            q_clusters.append(
                {
                    "canonical_name": c["canonical_name"],
                    "variants_collapsed": c["member_count"],
                    "member_names": sorted(
                        {str(m.get("name")) for m in c["members"] if m.get("name")}
                    ),
                    "match_basis": c["match_basis"],
                }
            )
    collapsed_total = sum(
        c["variants_collapsed"] - 1 for c in q_clusters
    )  # rows removed
    return {
        "problem": (
            "The #598 catalog counted the Helix Q-series semis once per "
            "name-spelling variant (e.g. 'Q4000', 'HELIX Q4000', 'MSV Q4000', "
            "'CALDIVE Q4000', 'HELIX Q-4000', the seed 'Helix Q4000' and the "
            "#593 roster 'Q4000'), inflating heavy_intervention_semi."
        ),
        "resolution": (
            "canonicalize_name + the Helix-Q aka list collapse every variant of "
            "each hull (Q4000/Q5000/Q7000) into one distinct vessel."
        ),
        "clusters": q_clusters,
        "duplicate_rows_removed": collapsed_total,
    }
