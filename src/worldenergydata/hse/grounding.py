# ABOUTME: HSE incident-grounding query — failure-mode -> real-world precedent incidents.
# ABOUTME: Returns 2 latest + 2 highest-severity BSEE incidents per failure mode, vintage-stamped.

"""HSE incident grounding.

Given an engineering failure mode (mooring fatigue, well control, …), return real
precedent incidents from the public HSE corpus: the **2 most-recent** and the
**2 highest-severity** records for that mode, each stamped with the corpus data
vintage so freshness is transparent (never hidden).

Purpose: ground every digitalmodel engineering analysis in real-world precedent.
Numbers persuade engineers; real incidents persuade decision-makers; the
fresh-vs-historic contrast answers the "is this stale?" objection.

Design decisions (2026-06-18, epic #486):
- **Per-mode source routing.** Offshore structural modes (mooring/riser/well
  control) route to **BSEE only** — OSHA is onshore + stale (~1999) and adds
  off-domain noise. OSHA/EPA are reserved for modes where they are on-domain.
- **Pick = 2 newest by date + 2 highest-severity** of all time.
- **Always stamp data vintage.**
- **Operator Aggregation Contract (#423):** output cites lease blocks + dates,
  never operator names.

Usage::

    from worldenergydata.hse.grounding import ground

    g = ground("mooring_fatigue")
    print(g.render_card())          # markdown card
    g.to_dict()                     # JSON-serialisable sidecar

CLI::

    uv run python -m worldenergydata.hse.grounding --mode mooring_fatigue [--json]

The default BSEE data path resolves from ``$WED_HSE_DATA_ROOT`` or the ace-linux-1
share; tests inject a fixture path so CI needs neither the share nor network.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

# --- failure-mode registry ----------------------------------------------------
# Each mode: human label, routed sources, and an include-regex over the BSEE
# ACCIDENT_TYPE field. Extend per #488 (coverage). Keep mooring first/pilot.


@dataclass(frozen=True)
class FailureMode:
    key: str
    label: str
    sources: tuple[str, ...]
    include: re.Pattern


FAILURE_MODES: dict[str, FailureMode] = {
    "mooring_fatigue": FailureMode(
        key="mooring_fatigue",
        label="Mooring / station-keeping failure",
        sources=("bsee",),
        include=re.compile(
            r"moor(ing)?\s*(line|failure|chain)|fairlead|anchor\s*(drag|chain|line)"
            r"|anchor contact|station[- ]keep|capsiz",
            re.I,
        ),
    ),
}

# --- BSEE ACCIDENT_TYPE -> severity rank (higher = worse) ---------------------
SEVERITY_RANK: list[tuple[re.Pattern, int, str]] = [
    (re.compile(r"fatalit", re.I), 100, "fatality"),
    (re.compile(r"capsiz|blowout|explosion", re.I), 90, "catastrophic"),
    (re.compile(r"\bLTA\b|lost time|required evacuation", re.I), 60, "lost_time"),
    (re.compile(r"pollution|spill|h2s|gas release", re.I), 50, "environmental"),
    (re.compile(r"injury|RW/JT", re.I), 40, "injury"),
    (re.compile(r">\$25K|incident >\$25k", re.I), 30, "property_>$25k"),
]


def severity_of(text: str) -> tuple[int, str]:
    """Map a BSEE ACCIDENT_TYPE string to (rank, label). Higher rank = worse."""
    best = (10, "minor")
    for rx, score, name in SEVERITY_RANK:
        if rx.search(text) and score > best[0]:
            best = (score, name)
    return best


# --- data model ---------------------------------------------------------------
@dataclass
class Incident:
    source: str
    date: str  # ISO yyyy-mm-dd
    location: str  # area block + lease, never operator name
    description: str
    severity: str
    severity_rank: int
    vintage_note: str
    _dt: dt.date = field(repr=False, default=dt.date.min)

    def public(self) -> dict:
        return {k: v for k, v in asdict(self).items() if not k.startswith("_")}


@dataclass
class Grounding:
    failure_mode: str
    latest: list[Incident]
    most_severe: list[Incident]
    source_counts: dict[str, object]
    vintage_note: str

    def to_dict(self) -> dict:
        return {
            "failure_mode": self.failure_mode,
            "source_counts": self.source_counts,
            "vintage_note": self.vintage_note,
            "latest_2": [i.public() for i in self.latest],
            "most_severe_2": [i.public() for i in self.most_severe],
        }

    def render_card(self) -> str:
        L = [f"### Real-world precedent — {self.failure_mode}", ""]
        L.append("**Latest on record:**")
        for i in self.latest:
            L.append(f"- **{i.date}** — {i.location} — {i.description} "
                     f"_({i.severity}; {i.source})_")
        L.append("")
        L.append("**Highest-consequence on record:**")
        for i in self.most_severe:
            L.append(f"- **{i.date}** — {i.location} — {i.description} "
                     f"_({i.severity}; {i.source})_")
        L.append("")
        routed = ", ".join(f"{k}={v}" for k, v in self.source_counts.items())
        L.append(f"_Sources ({routed}). Domain-routed: only on-domain sources "
                 f"queried for this failure mode._")
        if self.vintage_note:
            L.append(f"_Data vintage: {self.vintage_note}._")
        return "\n".join(L)


# --- BSEE data source (CI-safe, fixture-injectable) ---------------------------
SHARE_DEFAULT = Path(
    "/mnt/remote/ace-linux-1/ace/worldenergydata/data/modules/hse/raw/bsee"
    "/IncInvRawData/mv_acc_investigations.txt"
)


def default_bsee_path() -> Optional[Path]:
    """Resolve the BSEE incident-investigation file.

    Order: ``$WED_HSE_DATA_ROOT/.../mv_acc_investigations.txt`` -> repo-local
    ``data/modules/...`` -> ace-linux-1 share. Returns None if none exist.
    """
    candidates = []
    root = os.environ.get("WED_HSE_DATA_ROOT")
    if root:
        candidates.append(Path(root) / "hse/raw/bsee/IncInvRawData/mv_acc_investigations.txt")
    repo = Path(__file__).resolve().parents[3] / "data/modules/hse/raw/bsee/IncInvRawData/mv_acc_investigations.txt"
    candidates.append(repo)
    candidates.append(SHARE_DEFAULT)
    for c in candidates:
        if c.exists():
            return c
    return None


def _parse_date(s: str) -> Optional[dt.date]:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime((s or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def load_bsee(mode: FailureMode, path: Optional[Path] = None) -> list[Incident]:
    """Load BSEE incident-investigation records matching ``mode``.

    ``path`` overrides resolution (tests pass a fixture). Vintage is the max
    incident date in the corpus, computed from the data — not file mtime.
    """
    path = path or default_bsee_path()
    if path is None or not Path(path).exists():
        return []
    rows = list(csv.DictReader(open(path, encoding="latin-1")))
    if not rows:
        return []
    newest = max((_parse_date(r.get("DATE_OCCURRED", "")) or dt.date.min) for r in rows)
    vintage = f"BSEE incident investigations; corpus current to {newest.isoformat()}"
    out: list[Incident] = []
    for r in rows:
        atype = (r.get("ACCIDENT_TYPE") or "").strip(" -")
        if not mode.include.search(atype):
            continue
        d = _parse_date(r.get("DATE_OCCURRED", ""))
        if not d:
            continue
        rank, sev = severity_of(atype)
        loc = " ".join(
            x for x in [(r.get("AREA_BLOCK") or "").strip(), (r.get("LEASE_NUMBER") or "").strip()]
            if x and x != "Not Applicable"
        )
        out.append(Incident(
            source="BSEE (offshore)", date=d.isoformat(), location=loc or "GoM (unspecified)",
            description=atype, severity=sev, severity_rank=rank, vintage_note=vintage, _dt=d))
    return out


SOURCE_LOADERS: dict[str, Callable[..., list[Incident]]] = {
    "bsee": load_bsee,
}


# --- public API ---------------------------------------------------------------
def ground(failure_mode: str, *, bsee_path: Optional[Path] = None) -> Grounding:
    """Return a :class:`Grounding` for ``failure_mode``.

    Queries only the sources routed for the mode (off-domain sources report
    ``"not routed"``). Picks 2 newest + 2 highest-severity (disjoint).
    """
    if failure_mode not in FAILURE_MODES:
        raise KeyError(f"unknown failure_mode {failure_mode!r}; "
                       f"known: {sorted(FAILURE_MODES)}")
    mode = FAILURE_MODES[failure_mode]
    pool: list[Incident] = []
    counts: dict[str, object] = {}
    for name in ("bsee", "osha", "epa_tri"):
        if name not in mode.sources:
            counts[name.upper()] = "not routed (off-domain for this mode)"
            continue
        loader = SOURCE_LOADERS[name]
        got = loader(mode, bsee_path) if name == "bsee" else loader(mode)
        counts[name.upper()] = len(got)
        pool.extend(got)

    latest = sorted(pool, key=lambda i: i._dt, reverse=True)[:2]
    picked = {id(i) for i in latest}
    most_severe = sorted(
        [i for i in pool if id(i) not in picked],
        key=lambda i: (i.severity_rank, i._dt), reverse=True,
    )[:2]
    vintage = (latest + most_severe)[0].vintage_note if (latest or most_severe) else ""
    return Grounding(
        failure_mode=mode.label, latest=latest, most_severe=most_severe,
        source_counts=counts, vintage_note=vintage)


def _main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="HSE incident grounding for a failure mode")
    ap.add_argument("--mode", default="mooring_fatigue", choices=sorted(FAILURE_MODES))
    ap.add_argument("--json", action="store_true", help="emit JSON sidecar instead of card")
    a = ap.parse_args(argv)
    g = ground(a.mode)
    print(json.dumps(g.to_dict(), indent=2) if a.json else g.render_card())
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
