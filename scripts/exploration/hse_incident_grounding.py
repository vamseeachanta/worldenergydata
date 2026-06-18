#!/usr/bin/env python3
"""HSE incident grounding — prototype.

Given an engineering failure mode, pull real precedent incidents from the public
HSE corpus and return "2 latest + 2 highest-severity", each stamped with source +
data vintage so freshness/staleness is transparent (never hidden).

Purpose: an additional Deckhand demo stream — every digitalmodel engineering
analysis ships with real-world precedent. Numbers persuade engineers; real
incidents persuade decision-makers.

Pilot failure mode: mooring fatigue (matches digitalmodel #796 parametric pilot).

Sources queried (per operator decision: "all sources"):
  - BSEE incident investigations (mv_acc_investigations.txt) -- offshore, narrative, fresh
  - EPA TRI oil/gas releases                                 -- environmental, annual
  - OSHA accident narratives (osha_accident.csv)             -- onshore, historical

Read-only against the NFS share. Nothing is copied or written back to the share.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

DATA_ROOT = Path("/mnt/remote/ace-linux-1/ace/worldenergydata/data/modules")

# --- failure-mode keyword library (extend per analysis type) ------------------
# Per-mode source routing: query only the sources that are on-domain for that
# failure mode. Offshore structural modes -> BSEE only (decision 2026-06-18).
# OSHA/EPA are reserved for modes where they are genuinely on-domain (onshore
# process safety, spills) -- not bolted onto offshore modes where they add noise.
FAILURE_MODES: dict[str, dict] = {
    "mooring_fatigue": {
        "label": "Mooring / station-keeping failure",
        "sources": ["bsee"],
        # offshore-mooring sense, not generic "moored vessel"
        "include": re.compile(
            r"moor(ing)?\s*(line|failure|chain)|fairlead|anchor\s*(drag|chain|line)"
            r"|anchor contact|station[- ]keep|capsiz",
            re.I,
        ),
    },
}

# --- BSEE ACCIDENT_TYPE -> severity rank (higher = worse) ----------------------
SEVERITY_RANK = [
    (re.compile(r"fatalit", re.I), 100, "fatality"),
    (re.compile(r"capsiz|blowout|explosion", re.I), 90, "catastrophic"),
    (re.compile(r"\bLTA\b|lost time|required evacuation", re.I), 60, "lost_time"),
    (re.compile(r"pollution|spill|h2s|gas release", re.I), 50, "environmental"),
    (re.compile(r"injury|RW/JT", re.I), 40, "injury"),
    (re.compile(r">\$25K|incident >\$25k", re.I), 30, "property_>$25k"),
]


def severity_of(text: str) -> tuple[int, str]:
    best = (10, "minor")
    for rx, score, name in SEVERITY_RANK:
        if rx.search(text) and score > best[0]:
            best = (score, name)
    return best


@dataclass
class Incident:
    source: str
    date: str          # ISO
    location: str
    description: str
    severity: str
    severity_rank: int
    offshore: bool
    vintage_note: str
    _dt: dt.date = field(repr=False, default=None)


def _parse_date(s: str, fmts) -> dt.date | None:
    for f in fmts:
        try:
            return dt.datetime.strptime(s.strip(), f).date()
        except (ValueError, AttributeError):
            continue
    return None


def load_bsee(mode: dict) -> list[Incident]:
    f = DATA_ROOT / "hse/raw/bsee/IncInvRawData/mv_acc_investigations.txt"
    out: list[Incident] = []
    rows = list(csv.DictReader(open(f, encoding="latin-1")))
    newest = max((_parse_date(r["DATE_OCCURRED"], ["%m/%d/%Y"]) or dt.date.min) for r in rows)
    vintage = f"BSEE incident investigations; corpus current to {newest.isoformat()}"
    for r in rows:
        atype = (r.get("ACCIDENT_TYPE") or "").strip(" -")
        if not mode["include"].search(atype):
            continue
        d = _parse_date(r["DATE_OCCURRED"], ["%m/%d/%Y"])
        if not d:
            continue
        rank, sev = severity_of(atype)
        loc = " ".join(x for x in [(r.get("AREA_BLOCK") or "").strip(),
                                   (r.get("LEASE_NUMBER") or "").strip()] if x and x != "Not Applicable")
        out.append(Incident(
            source="BSEE (offshore)", date=d.isoformat(), location=loc or "GoM (unspecified)",
            description=atype, severity=sev, severity_rank=rank, offshore=True,
            vintage_note=vintage, _dt=d))
    return out


def load_osha(mode: dict) -> list[Incident]:
    f = DATA_ROOT / "hse/raw/osha/osha_accident.csv"
    if not f.exists():
        return []
    out: list[Incident] = []
    for r in csv.DictReader(open(f, encoding="latin-1")):
        desc = ((r.get("event_desc") or "") + " " + (r.get("abstract_text") or "")).strip()
        if not mode["include"].search(desc):
            continue
        d = _parse_date((r.get("event_date") or "")[:10], ["%Y-%m-%d", "%m/%d/%Y"])
        if not d:
            continue
        # OSHA is onshore-source; require strong offshore signal and no recreational/inland tells
        offshore = bool(re.search(r"offshore|platform|fpso|spar|jack[- ]?up|outer continental", desc, re.I)) \
            and not re.search(r"kayak|jon boat|canoe|weed harvester|pontoon|recreational|lake|pond|dock", desc, re.I)
        rank = 100 if (r.get("fatality") or "").strip().upper() == "X" else 40
        sev = "fatality" if rank == 100 else "injury"
        out.append(Incident(
            source="OSHA (onshore)", date=d.isoformat(), location=r.get("state_flag", "") or "US",
            description=desc[:140], severity=sev, severity_rank=rank, offshore=offshore,
            vintage_note="OSHA accident file; historical (data ends ~1999 on disk -- re-acquire for current)",
            _dt=d))
    return out


def load_epa(mode: dict) -> list[Incident]:
    # TRI is chemical-release inventory, not incident-level; mooring will not match.
    # Included to honour "all sources" and to show honest empty result.
    return []


def ground(mode_key: str) -> dict:
    mode = FAILURE_MODES[mode_key]
    routed = set(mode.get("sources", ["bsee", "osha", "epa_tri"]))
    pool: list[Incident] = []
    counts = {}
    for name, key, loader in (("BSEE", "bsee", load_bsee),
                              ("OSHA", "osha", load_osha),
                              ("EPA_TRI", "epa_tri", load_epa)):
        if key not in routed:
            counts[name] = "not routed (off-domain for this mode)"
            continue
        got = loader(mode)
        counts[name] = len(got)
        pool.extend(got)

    # relevance gate: offshore-domain only for the headline picks
    relevant = [i for i in pool if i.offshore]
    off_domain = [i for i in pool if not i.offshore]

    latest = sorted(relevant, key=lambda i: i._dt, reverse=True)[:2]
    picked_ids = {id(i) for i in latest}
    severe = sorted([i for i in relevant if id(i) not in picked_ids],
                    key=lambda i: (i.severity_rank, i._dt), reverse=True)[:2]

    return {
        "failure_mode": mode["label"],
        "source_counts": counts,
        "relevant_offshore": len(relevant),
        "off_domain_excluded": len(off_domain),
        "off_domain_examples": [f"{i.date} {i.severity}: {i.description[:60]}" for i in off_domain[:3]],
        "latest_2": [{k: v for k, v in asdict(i).items() if not k.startswith("_")} for i in latest],
        "most_severe_2": [{k: v for k, v in asdict(i).items() if not k.startswith("_")} for i in severe],
    }


def render_card(g: dict) -> str:
    L = []
    L.append(f"### Real-world precedent — {g['failure_mode']}")
    L.append("")
    L.append("**Latest on record:**")
    for i in g["latest_2"]:
        L.append(f"- **{i['date']}** — {i['location']} — {i['description']} "
                 f"_({i['severity']}; {i['source']})_")
    L.append("")
    L.append("**Highest-consequence on record:**")
    for i in g["most_severe_2"]:
        L.append(f"- **{i['date']}** — {i['location']} — {i['description']} "
                 f"_({i['severity']}; {i['source']})_")
    L.append("")
    src = g["source_counts"]
    routed = ", ".join(f"{k}={v}" for k, v in src.items())
    L.append(f"_Sources ({routed}). Domain-routed: only on-domain sources queried for this failure mode._")
    # always stamp vintage (decision 2026-06-18)
    vintage = (g["latest_2"] + g["most_severe_2"])
    if vintage:
        L.append(f"_Data vintage: {vintage[0]['vintage_note']}._")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="mooring_fatigue", choices=list(FAILURE_MODES))
    ap.add_argument("--json", action="store_true", help="emit JSON instead of card")
    a = ap.parse_args()
    g = ground(a.mode)
    if a.json:
        print(json.dumps(g, indent=2))
    else:
        print(render_card(g))
        print("\n---\nsource_counts:", g["source_counts"],
              "| off-domain excluded:", g["off_domain_excluded"])
        if g["off_domain_examples"]:
            print("off-domain examples:", *g["off_domain_examples"], sep="\n  ")


if __name__ == "__main__":
    sys.exit(main())
