"""Drilling-HSE patterns analysis — re-application of #416 methodology to DRILL.* codes.

Issue: https://github.com/vamseeachanta/worldenergydata/issues/426 (child of #423,
sibling of #416 intervention-HSE).

Methodology mirror of #416 Phase 1A:
  1. Anchor on the BSEE INCINV (accident-investigation) operational records — the
     "gold" deep-incident surface #416 identified (the same source the WRK-013
     IncidentClassifier was built for).
  2. Re-classify every INCINV record with the SHARED, repo-canonical
     `IncidentClassifier` (`src/worldenergydata/safety_analysis/taxonomy/`).
  3. Cut to the DRILLING activity (activity code == "DRILL") instead of #416's
     intervention/well-servicing cut. The DRILL activity's subactivities ARE the
     drilling-phase taxonomy: drilling_operations, well_completion, workover,
     well_control, well_testing, casing_cementing, tripping, logging.
  4. Descriptive pattern mining on the DRILL.* subset: incident-type (ACCIDENT_TYPE)
     frequency, severity proxy, temporal trend, area/block geography, subactivity
     (drilling-phase) split, classification provenance.

DATA NOTE (honest scope, mirroring #416's caveat discipline):
  The assembled `hse_incidents.db` (97,993 rows, the surface #416's memo profiled)
  is NOT materialized in this environment (0-byte stub; `make data` not run here).
  The authoritative BSEE drilling-relevant *source* — the INCINV accident
  investigations text file — IS present locally under the module's
  `external_data_root`. We therefore run the SAME classifier directly against the
  raw INCINV source (1,987 records), which is exactly the operational-incident
  surface #416 named as "the gold". This is the faithful, reproducible cut; we do
  NOT fabricate the 97,993-row db's numbers.

  BSEE INCINV `ACCIDENT_TYPE` describes the incident KIND (Fire, Crane, Blowout,
  Injury...), not the operational phase directly. The drilling-phase label is
  DERIVED by the classifier: "Blowout" maps directly to DRILL/well_control, and
  drilling-keyword hits (drill, casing, completion, workover, kick, bop...) on the
  accident-type text map other records into DRILL.*. Records with no drilling
  signal classify to other activities and are excluded — same mechanism #416 used.

Stdlib only. Loads the taxonomy modules by file path to bypass the heavy package
`__init__` (which needs pydantic/pandas, not required for classification).
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import types
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TAXO = REPO / "src" / "worldenergydata" / "safety_analysis" / "taxonomy"

# INCINV raw source. Prefer in-repo path; fall back to module external_data_root.
INCINV_CANDIDATES = [
    REPO / "data" / "modules" / "hse" / "raw" / "bsee" / "IncInvRawData"
    / "mv_acc_investigations.txt",
    Path("/mnt/ace/worldenergydata/data/modules/hse/raw/bsee/IncInvRawData"
         "/mv_acc_investigations.txt"),
]

OUT_DIR = REPO / "reports" / "hse"
DATE_TAG = "2026-06-19"
OUT_JSON = OUT_DIR / f"drilling-hse-patterns-{DATE_TAG}.json"


# ---------------------------------------------------------------------------
# Load taxonomy + classifier by file path (bypass package __init__)
# ---------------------------------------------------------------------------
def _load_taxonomy_classifier():
    # Stub the logging dependency the classifier imports.
    pkg = types.ModuleType("worldenergydata")
    pkg.__path__ = []  # mark as package
    common = types.ModuleType("worldenergydata.common")
    common.__path__ = []
    logging_mod = types.ModuleType("worldenergydata.common.logging")

    def get_logger(name=None):
        import logging
        return logging.getLogger(name or "drill_hse")

    logging_mod.get_logger = get_logger
    sys.modules["worldenergydata"] = pkg
    sys.modules["worldenergydata.common"] = common
    sys.modules["worldenergydata.common.logging"] = logging_mod

    def _load(modname, path):
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
        return mod

    base = "worldenergydata.safety_analysis.taxonomy"
    # define the package shells so relative imports inside the files resolve
    for shell in ("worldenergydata.safety_analysis",
                  "worldenergydata.safety_analysis.taxonomy"):
        m = types.ModuleType(shell)
        m.__path__ = [str(TAXO if shell.endswith("taxonomy") else TAXO.parent)]
        sys.modules[shell] = m

    _load(f"{base}.activity_definitions", TAXO / "activity_definitions.py")
    _load(f"{base}.activity_registry", TAXO / "activity_registry.py")
    clf_mod = _load(f"{base}.incident_classifier", TAXO / "incident_classifier.py")
    return clf_mod.IncidentClassifier


# ---------------------------------------------------------------------------
# Load INCINV records
# ---------------------------------------------------------------------------
def _load_incinv():
    src = next((p for p in INCINV_CANDIDATES if p.exists() and p.stat().st_size > 0), None)
    if src is None:
        raise FileNotFoundError(
            "INCINV source not found; checked: "
            + ", ".join(str(p) for p in INCINV_CANDIDATES)
        )
    rows = []
    with open(src, newline="", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            rows.append({(k or "").strip(): (v.strip() if isinstance(v, str) else v)
                         for k, v in r.items()})
    return src, rows


# ---------------------------------------------------------------------------
# Severity proxy from ACCIDENT_TYPE (BSEE composite-type semantics)
# ---------------------------------------------------------------------------
def _severity(accident_type: str) -> str:
    t = (accident_type or "").lower()
    if "fatality" in t:
        return "fatality"
    if "blowout" in t or "explosion" in t:
        return "major"  # well-control / explosion = high consequence
    if "lta" in t or "rw/jt" in t or "injury" in t:
        return "injury_lost_time"
    if "fire" in t or "pollution" in t or "collision" in t or "$25k" in t:
        return "serious"
    if "evacuation" in t or "muster" in t or "shutdown" in t:
        return "evacuation_muster"
    return "other"


def _year(date_occurred: str):
    # format M/D/YYYY
    try:
        parts = date_occurred.split("/")
        return int(parts[-1])
    except Exception:
        return None


def main() -> None:
    Classifier = _load_taxonomy_classifier()
    clf = Classifier()
    src, rows = _load_incinv()

    activity_dist = Counter()
    drill_rows = []
    for row in rows:
        res = clf.classify(row, source="bsee")
        activity_dist[res.activity] += 1
        if res.activity == "DRILL":
            drill_rows.append((row, res))

    n_drill = len(drill_rows)

    # ---- DRILL.* statistics ----
    sub_dist = Counter()
    method_dist = Counter()
    acc_type_dist = Counter()
    severity_dist = Counter()
    year_dist = Counter()
    area_dist = Counter()
    conf_buckets = Counter()
    for row, res in drill_rows:
        sub_dist[res.subactivity] += 1
        method_dist[res.match_method] += 1
        acc_type_dist[row.get("ACCIDENT_TYPE", "").strip()] += 1
        severity_dist[_severity(row.get("ACCIDENT_TYPE", ""))] += 1
        y = _year(row.get("DATE_OCCURRED", ""))
        if y:
            year_dist[y] += 1
        area = (row.get("AREA_BLOCK", "") or "").split()[0] if row.get("AREA_BLOCK") else ""
        if area:
            area_dist[area] += 1
        if res.confidence >= 0.90:
            conf_buckets["direct_code(>=0.90)"] += 1
        elif res.confidence >= 0.70:
            conf_buckets["keyword_high(0.70-0.89)"] += 1
        elif res.confidence >= 0.50:
            conf_buckets["keyword_medium(0.50-0.69)"] += 1
        else:
            conf_buckets["keyword_low(<0.50)"] += 1

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "issue": "https://github.com/vamseeachanta/worldenergydata/issues/426",
        "methodology": "Re-application of #416 Phase 1A: shared IncidentClassifier "
                       "over BSEE INCINV records, cut to activity==DRILL.",
        "source_file": str(src),
        "incinv_total_records": len(rows),
        "drill_filter": "IncidentClassifier(source='bsee').activity == 'DRILL' "
                        "(Blowout direct-map + drilling-keyword match on ACCIDENT_TYPE)",
        "activity_distribution_all_incinv": dict(activity_dist.most_common()),
        "drill_total": n_drill,
        "drill_pct_of_incinv": round(100.0 * n_drill / len(rows), 2),
        "drill_subactivity_distribution": dict(sub_dist.most_common()),
        "drill_match_method": dict(method_dist.most_common()),
        "drill_confidence_buckets": dict(conf_buckets.most_common()),
        "drill_accident_type_top": dict(acc_type_dist.most_common(20)),
        "drill_accident_type_distinct": len(acc_type_dist),
        "drill_severity_proxy": dict(severity_dist.most_common()),
        "drill_by_year": dict(sorted(year_dist.items())),
        "drill_year_range": [min(year_dist), max(year_dist)] if year_dist else None,
        "drill_top_areas": dict(area_dist.most_common(10)),
        "drill_distinct_leases": len({r.get("LEASE_NUMBER", "") for r, _ in drill_rows
                                      if r.get("LEASE_NUMBER")}),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str))
    print(f"Wrote {OUT_JSON.relative_to(REPO)}")
    print(json.dumps({
        "incinv_total": payload["incinv_total_records"],
        "drill_total": payload["drill_total"],
        "drill_pct": payload["drill_pct_of_incinv"],
        "subactivities": payload["drill_subactivity_distribution"],
        "severity": payload["drill_severity_proxy"],
        "year_range": payload["drill_year_range"],
    }, indent=2))


if __name__ == "__main__":
    main()
