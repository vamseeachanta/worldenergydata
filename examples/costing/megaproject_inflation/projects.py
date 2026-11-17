"""Project-level costs of offshore mega projects from the repository's curated public records (article r2).

Four curated tables are read, unchanged, from data/modules/cost/curated/ and checked against the SHA-256 recorded in
project_sources.csv beside this file:

- sanctioned_projects.csv: the gross capital cost announced at sanction (final investment decision), with its source;
- contract_awards.csv: public contract awards, with a value where one was published (a point, or the published range
  of a contractor's size word);
- cost_revision_trails.csv: dated cost statements of a project, from the sanction estimate to the final figure;
- cost_revision_trail_qualifiers.csv: the repository's review of a statement's words (exact, approximate, lower_bound,
  upper_bound, unsupported). A statement whose note says its value is derived (not quoted) is taken as "derived".

Rules (the same as the repository's reconciliation harness, worldenergydata.cost.timeseries.reconciliation, where it
has one):

- Award value set against the sanction estimate: only bases "point", "band", "backlog" and "range" count, at their low
  bound; "lease_contract" (a lease and operate value, not capital), "midstream" (third-party export lines), "combined"
  (several projects in one value) and "not_public" are left out.
- Final over sanction: per project and currency, the first sanction estimate in the trail, and the final outturn, or
  where there is none the operator's final forecast. The change is computed only where both statements' words allow
  it: not where either is unsupported, and not where the sanction estimate is itself a bound ("more than"). A final
  that is an upper bound ("within", "under") gives a change of at most the value shown; a lower bound, at least.

A value is primary when it was read on the operator's, a partner's, a regulator's or a contractor's own page, in a
filing, or from a wire service carrying a company release, and is not rated low. Anything else (trade press, or a
later report quoting the operator) and any derived value is marked "ASSUMED - to be confirmed" by CONFIRM_BY.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from statistics import median
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
CURATED = HERE.parents[2] / "data" / "modules" / "cost" / "curated"
CONFIRM_BY = "11 Dec 2026"

CAPEX_COMPARABLE = {"point", "band", "backlog", "range"}
PRIMARY_SANCTION = {"press_release", "sec_filing", "regulator_document", "operator_annual_report"}
# Company sites and the wire services that carry company releases word for word.
PRIMARY_AWARD_HOSTS = {"saipem.com", "technipfmc.com", "deepwater.com", "sbmoffshore.com", "enbridge.com", "ten.com",
                       "bumiarmada.com", "equinor.com", "globenewswire.com", "prnewswire.com", "businesswire.com"}
# Operators, regulators and filings behind the cost statements (where the figure was read).
PRIMARY_TRAIL_HOSTS = PRIMARY_AWARD_HOSTS | {"woodside.com", "santos.com", "sec.gov", "investor.maersk.com",
                                             "enquest.com", "totalenergies.com", "sodir.no", "regjeringen.no",
                                             "corporate.exxonmobil.com"}
FILES = ("sanctioned_projects.csv", "contract_awards.csv", "cost_revision_trails.csv",
         "cost_revision_trail_qualifiers.csv")
BOUNDS = {"lower_bound", "upper_bound"}
# Statements whose own words disagree with the sanction estimate used; the comparison is kept and marked ASSUMED until
# the sources are read again. Found by the review of 17 Nov 2026 (gate run 1, fix 3).
CONFLICTS = {
    ("Peregrino Phase 2", "2022-10"): "the final statement names an original estimate of 3,000, against about 3,500 at sanction",
}


def _num(s: str | None) -> float | None:
    s = (s or "").strip()
    return float(s) if s else None


def _host(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def award_is_primary(award: dict) -> bool:
    return _host(award["SOURCE_URL"]) in PRIMARY_AWARD_HOSTS


def load(curated: Path = CURATED, record: Path = HERE / "project_sources.csv") -> dict:
    """The four tables, after their SHA-256 is checked against project_sources.csv."""
    rows = {r["file"]: r for r in csv.DictReader(record.open(encoding="utf-8"))}
    bad = [n for n in FILES if n not in rows
           or hashlib.sha256((curated / n).read_bytes()).hexdigest() != rows[n]["sha256"]]
    if bad:
        raise SystemExit(f"project sources check failed (hash mismatch or not recorded): {bad}")

    def read(name):
        with (curated / name).open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    return {"sanctioned": read(FILES[0]), "awards": read(FILES[1]), "trails": read(FILES[2]),
            "qualifiers": read(FILES[3]), "record": rows}


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


def qualifier(t: dict, quals: dict) -> str:
    """The repository's reading of a statement's words; "derived" where its note says the value is derived."""
    if re.search(r"\bvalue derived\b", t.get("NOTES", ""), flags=re.I):
        return "derived"
    return quals.get((t["PROJECT"], t["STATEMENT_DATE"], t["KIND"]), "not reviewed")


def trail_is_primary(t: dict) -> bool:
    return _host(t["SOURCE_URL"]) in PRIMARY_TRAIL_HOSTS and t["CONFIDENCE"] != "low"


def basis(quoted: str) -> str:
    """The money basis a statement gives in its own words: "money of the day", or a year's money such as "2021 NOK"."""
    if re.search(r"money of the day", quoted, flags=re.I):
        return "money of the day"
    m = re.search(r"\((\d{4}) ?([A-Z]{3})\)", quoted)
    return f"{m.group(1)} {m.group(2)}" if m else ""


def outturn(trails: list[dict], qualifiers: list[dict] | None = None) -> list[dict]:
    """Final over sanction, per project and currency (the harness rule), with both statements and their words kept."""
    quals = {(q["TRAIL_PROJECT"], q["STATEMENT_DATE"], q["KIND"]): q["QUALIFIER"] for q in (qualifiers or [])}
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
            sq, fq = qualifier(s, quals), qualifier(f, quals)
            computable = "unsupported" not in (sq, fq) and sq not in BOUNDS
            bound = {"upper_bound": "at most", "lower_bound": "at least"}.get(fq, "") if computable else ""
            out.append({
                "project": p, "currency": ccy, "sanction_mm": sv, "final_mm": fv, "final_kind": f["KIND"],
                "sanction_date": s["STATEMENT_DATE"], "final_date": f["STATEMENT_DATE"],
                "sanction_year": _year(s["STATEMENT_DATE"]), "final_year": _year(f["STATEMENT_DATE"]),
                "sanction_qualifier": sq, "final_qualifier": fq,
                "sanction_primary": trail_is_primary(s) and sq != "derived",
                "final_primary": trail_is_primary(f) and fq != "derived" and (p, f["STATEMENT_DATE"]) not in CONFLICTS,
                "conflict": CONFLICTS.get((p, f["STATEMENT_DATE"]), ""),
                "sanction_basis": basis(s.get("QUOTED_TEXT", "")), "final_basis": basis(f.get("QUOTED_TEXT", "")),
                "sanction_source": s["SOURCE_TITLE"], "final_source": f["SOURCE_TITLE"],
                "sanction_url": s["SOURCE_URL"], "final_url": f["SOURCE_URL"],
                "computable": computable, "bound": bound,
                "change_pct": 100.0 * (fv / sv - 1.0) if computable else None})
    return sorted(out, key=lambda o: (o["sanction_year"], o["project"]))


def market_escalation(index: dict[int, float], first: int, last: int, window) -> float:
    """Escalation of a price index over a project's own years, sanction year to final statement year inclusive, on
    the article's bell-shaped spend (window = inflation.window_escalation). Fraction."""
    return window(index, first, last - first + 1)


def summary(cov: list[dict], out: list[dict]) -> dict:
    shares = [c["share_low_pct"] for c in cov]
    top = max(cov, key=lambda c: c["share_low_pct"])
    comp = [o for o in out if o["computable"]]
    lo, hi = min(comp, key=lambda o: o["change_pct"]), max(comp, key=lambda o: o["change_pct"])

    def assumed(o):
        return not (o["sanction_primary"] and o["final_primary"])
    return {"n_cov": len(cov), "share_median": median(shares), "share_min": min(shares), "share_max": max(shares),
            "share_max_project": top["project"], "n_out": len(out), "n_comp": len(comp),
            "n_out_assumed": sum(1 for o in out if assumed(o)), "n_comp_assumed": sum(1 for o in comp if assumed(o)),
            "n_final_secondary": sum(1 for o in out if not o["final_primary"]),
            "n_out_forecast": sum(1 for o in out if o["final_kind"] == "final_forecast"),
            "n_comp_forecast": sum(1 for o in comp if o["final_kind"] == "final_forecast"),
            "n_bound": sum(1 for o in comp if o["bound"]),
            "out_min": lo["change_pct"], "out_min_project": lo["project"], "out_min_year": lo["sanction_year"],
            "out_max": hi["change_pct"], "out_max_project": hi["project"], "out_max_year": hi["sanction_year"]}
