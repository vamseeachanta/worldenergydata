"""Project-level costs of offshore mega projects from the repository's curated public records (article r2).

Three curated tables are read, unchanged, from data/modules/cost/curated/ and checked against the SHA-256 recorded in
project_sources.csv beside this file:

- sanctioned_projects.csv: the gross capital cost announced at sanction (final investment decision), with its source;
- contract_awards.csv: public contract awards, with a value where one was published (a point, or the published range
  of a contractor's size word);
- cost_revision_trails.csv: dated cost statements of a project, from the sanction estimate to the final figure.

Rules (the same as the repository's reconciliation harness, worldenergydata.cost.timeseries.reconciliation):

- Award value set against the sanction estimate: only bases "point", "band", "backlog" and "range" count, at their low
  bound; "lease_contract" (a lease and operate value, not capital), "midstream" (third-party export lines), "combined"
  (several projects in one value) and "not_public" are left out.
- Final over sanction: per project and currency, the first sanction estimate in the trail, and the final outturn, or
  where there is none the operator's final forecast.

A value is primary when it comes from the operator, a partner, a regulator or a company release (a contractor's own
release, or one carried by a wire service). Anything else (trade press, or a later report quoting the operator) is
marked "ASSUMED - to be confirmed" by CONFIRM_BY.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from statistics import median
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
CURATED = HERE.parents[2] / "data" / "modules" / "cost" / "curated"
CONFIRM_BY = "11 Dec 2026"

CAPEX_COMPARABLE = {"point", "band", "backlog", "range"}
PRIMARY_SANCTION = {"press_release", "sec_filing", "regulator_document", "operator_annual_report"}
PRIMARY_TRAIL = {"operator", "partner", "partner_sec", "regulator"}
# Company sites and the wire services that carry company releases word for word.
PRIMARY_AWARD_HOSTS = {"saipem.com", "technipfmc.com", "deepwater.com", "sbmoffshore.com", "enbridge.com", "ten.com",
                       "bumiarmada.com", "equinor.com", "globenewswire.com", "prnewswire.com", "businesswire.com"}
FILES = ("sanctioned_projects.csv", "contract_awards.csv", "cost_revision_trails.csv")


def _num(s: str | None) -> float | None:
    s = (s or "").strip()
    return float(s) if s else None


def _host(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def award_is_primary(award: dict) -> bool:
    return _host(award["SOURCE_URL"]) in PRIMARY_AWARD_HOSTS


def load(curated: Path = CURATED, record: Path = HERE / "project_sources.csv") -> dict:
    """The three tables, after their SHA-256 is checked against project_sources.csv."""
    rows = {r["file"]: r for r in csv.DictReader(record.open(encoding="utf-8"))}
    bad = [n for n in FILES if hashlib.sha256((curated / n).read_bytes()).hexdigest() != rows[n]["sha256"]]
    if bad:
        raise SystemExit(f"project sources check failed (hash mismatch): {bad}")

    def read(name):
        with (curated / name).open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    return {"sanctioned": read(FILES[0]), "awards": read(FILES[1]), "trails": read(FILES[2]), "record": rows}


def award_counts(awards: list[dict]) -> dict:
    valued = [a for a in awards if _num(a["VALUE_LOW_MM"]) is not None or _num(a["VALUE_HIGH_MM"]) is not None]
    return {"awards": len(awards), "valued": len(valued), "projects": len({a["PROJECT"] for a in awards}),
            "projects_valued": len({a["PROJECT"] for a in valued}),
            "valued_primary": sum(1 for a in valued if award_is_primary(a)),
            "valued_secondary": sum(1 for a in valued if not award_is_primary(a)),
            "not_public": sum(1 for a in awards if a["VALUE_BASIS"] == "not_public")}


def coverage(sanctioned: list[dict], awards: list[dict]) -> list[dict]:
    """Per project with awards and a sanction estimate: the capital value of its valued awards against the estimate."""
    san = {r["PROJECT"]: r for r in sanctioned}
    by: dict[str, list[dict]] = {}
    for a in awards:
        by.setdefault(a["PROJECT"], []).append(a)
    out = []
    for p, rows in by.items():
        s = san.get(p)
        gross = _num(s["SANCTIONED_CAPEX_USD_MM"]) if s else None
        if not gross:
            continue
        cmp_ = [a for a in rows if a["VALUE_BASIS"] in CAPEX_COMPARABLE and _num(a["VALUE_LOW_MM"]) is not None]
        low = sum(_num(a["VALUE_LOW_MM"]) for a in cmp_)
        high = sum(_num(a["VALUE_HIGH_MM"]) or _num(a["VALUE_LOW_MM"]) for a in cmp_)
        out.append({
            "project": p, "operator": s["OPERATOR"], "fid": int(s["FID_YEAR"]), "gross_mm": gross,
            "gross_primary": s["SOURCE_PRIORITY"] in PRIMARY_SANCTION, "gross_source": s["SOURCE_TITLE"],
            "gross_url": s["SOURCE_URL"], "n_awards": len(rows),
            "n_valued": sum(1 for a in rows if _num(a["VALUE_LOW_MM"]) is not None or _num(a["VALUE_HIGH_MM"]) is not None),
            "n_comparable": len(cmp_), "n_not_public": sum(1 for a in rows if a["VALUE_BASIS"] == "not_public"),
            "awards_low_mm": low, "awards_high_mm": high,
            "high_open": any(a["VALUE_BASIS"] == "band" and _num(a["VALUE_HIGH_MM"]) is None for a in cmp_),
            "awards_primary": all(award_is_primary(a) for a in cmp_),
            "share_low_pct": 100.0 * low / gross})
    return sorted(out, key=lambda c: (c["fid"], c["project"]))


def _year(date: str) -> int:
    return int(date[:4])


def outturn(trails: list[dict]) -> list[dict]:
    """Final over sanction, per project and currency (the harness rule), with both statements kept."""
    by: dict[tuple[str, str], dict[str, dict]] = {}
    for t in trails:
        if _num(t["VALUE_MM"]) is None:
            continue
        d = by.setdefault((t["PROJECT"], t["CURRENCY"]), {})
        if t["KIND"] == "sanction_estimate" and "sanction" not in d:
            d["sanction"] = t
        elif t["KIND"] in ("final_outturn", "final_forecast"):
            cur = d.get("final")
            if cur is None or (t["KIND"] == "final_outturn" and cur["KIND"] != "final_outturn"):
                d["final"] = t
    out = []
    for (p, ccy), d in by.items():
        if "sanction" in d and "final" in d:
            s, f = d["sanction"], d["final"]
            sv, fv = _num(s["VALUE_MM"]), _num(f["VALUE_MM"])
            prim = lambda r: r["PROVENANCE"] in PRIMARY_TRAIL and r["CONFIDENCE"] != "low"  # noqa: E731
            out.append({
                "project": p, "currency": ccy, "sanction_mm": sv, "final_mm": fv, "final_kind": f["KIND"],
                "sanction_date": s["STATEMENT_DATE"], "final_date": f["STATEMENT_DATE"],
                "sanction_year": _year(s["STATEMENT_DATE"]), "final_year": _year(f["STATEMENT_DATE"]),
                "sanction_primary": prim(s), "final_primary": prim(f),
                "sanction_source": s["SOURCE_TITLE"], "final_source": f["SOURCE_TITLE"],
                "sanction_url": s["SOURCE_URL"], "final_url": f["SOURCE_URL"],
                "change_pct": 100.0 * (fv / sv - 1.0)})
    return sorted(out, key=lambda o: (o["sanction_year"], o["project"]))


def market_escalation(index: dict[int, float], first: int, last: int, window) -> float:
    """Escalation of a price index over a project's own years, sanction year to final statement year inclusive, on
    the article's bell-shaped spend (window = inflation.window_escalation). Fraction."""
    return window(index, first, last - first + 1)


def summary(cov: list[dict], out: list[dict]) -> dict:
    shares = [c["share_low_pct"] for c in cov]
    top = max(cov, key=lambda c: c["share_low_pct"])
    lo, hi = min(out, key=lambda o: o["change_pct"]), max(out, key=lambda o: o["change_pct"])
    return {"n_cov": len(cov), "share_median": median(shares), "share_min": min(shares), "share_max": max(shares),
            "share_max_project": top["project"], "n_out": len(out),
            "n_out_assumed": sum(1 for o in out if not (o["sanction_primary"] and o["final_primary"])),
            "n_out_forecast": sum(1 for o in out if o["final_kind"] == "final_forecast"),
            "out_min": lo["change_pct"], "out_min_project": lo["project"], "out_min_year": lo["sanction_year"],
            "out_max": hi["change_pct"], "out_max_project": hi["project"], "out_max_year": hi["sanction_year"]}
