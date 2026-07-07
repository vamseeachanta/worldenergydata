#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Build the Lower Tertiary FIELD-performance comparison (deterministic).

Aggregates the per-well benchmark (`lt_well_benchmark_*.csv`) up to the field
level and joins each field's economics (NPV @10%, WTI break-even, $/bbl
sensitivity) parsed from the committed `field_economics_<slug>.md` reports.
Pure stdlib; same inputs -> byte-identical output.

    uv run python scripts/lower_tertiary/build_field_performance_comparison.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPORTS = Path(__file__).resolve().parents[2] / "reports" / "lower_tertiary"
BENCH = REPORTS / "lt_well_benchmark_lower_tertiary_2010_latest.csv"
OUT = REPORTS / "lt_field_performance_comparison.md"
CONTRACT = REPORTS / "lifecycle" / "_performance.json"

CONTRACT_META = {
    "source": (
        "BSEE OGOR-A per-well benchmark + V30 cost model, "
        "life-to-date (not full-cycle)"
    ),
    "inputs": [
        "reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv",
        "reports/lower_tertiary/field_economics_<slug>.md",
    ],
    "regenerate": (
        "uv run python scripts/lower_tertiary/build_field_performance_comparison.py"
    ),
}

_NPV = re.compile(r"terminal cumulative NPV \*\*\$(-?[\d,]+\.?\d*) M")
_BE = re.compile(r"zero at a flat-equivalent realized WTI of \$([\d,]+)/bbl")
_SENS = re.compile(
    r"\+\$1/bbl\*\* on the realized oil price moves field NPV by \*\*\$\+?([\d.]+) M"
)


def _slug(field: str) -> str:
    return field.strip().lower().replace(" ", "_")


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _econ(field: str) -> dict:
    """NPV / break-even / sensitivity for a field from its economics report."""
    md = REPORTS / f"field_economics_{_slug(field)}.md"
    if not md.exists():
        return {}
    txt = md.read_text(encoding="utf-8")
    out: dict[str, float] = {}
    if m := _NPV.search(txt):
        out["npv_mm"] = _num(m.group(1))
    if m := _BE.search(txt):
        out["breakeven_wti"] = _num(m.group(1))
    if m := _SENS.search(txt):
        out["sens_mm_per_dollar"] = _num(m.group(1))
    return out


def _aggregate() -> dict[str, dict]:
    """Per-field roll-up of the per-well benchmark (single source of the math)."""
    rows = list(csv.DictReader(BENCH.open(encoding="utf-8")))
    fields: dict[str, dict] = {}
    for r in rows:
        f = fields.setdefault(
            r["field"],
            {
                "wells": 0,
                "cum": 0.0,
                "rev": 0.0,
                "uptime": [],
                "decline": [],
                "interv": 0,
                "eur": 0.0,
            },
        )
        f["wells"] += 1
        f["cum"] += float(r["cum_oil_mmbbl"] or 0)
        f["rev"] += float(r["est_revenue_mm"] or 0)
        if r["uptime_pct"]:
            f["uptime"].append(float(r["uptime_pct"]))
        if r["decline_annual_pct"]:
            f["decline"].append(float(r["decline_annual_pct"]))
        f["interv"] += int(float(r["interventions"] or 0))
        f["eur"] += float(r["eur_mmbbl"] or 0)
    return fields


def _avg(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def build() -> str:
    fields = _aggregate()
    avg = _avg

    ordered = sorted(fields.items(), key=lambda kv: kv[1]["cum"], reverse=True)

    lines = [
        "# Lower Tertiary — field-performance comparison",
        "",
        "All seven producing Lower Tertiary fields, side by side, from **public BSEE",
        "data**. Per-well benchmark aggregated to the field level; economics joined",
        "from the per-field reports. Life-to-date on public data — not full-cycle",
        "sanctioned economics. Deterministic and reproducible.",
        "",
        "| Field | Wells | Cum oil (MMbbl) | EUR (MMbbl) | Avg uptime % | Avg decline %/yr | Interventions | NPV @10% ($MM) | WTI break-even ($/bbl) | NPV per +$1/bbl ($MM) |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    tot = {"wells": 0, "cum": 0.0, "eur": 0.0, "interv": 0, "npv": 0.0}
    for field, f in ordered:
        e = _econ(field)
        npv = e.get("npv_mm")
        be = e.get("breakeven_wti")
        sens = e.get("sens_mm_per_dollar")
        lines.append(
            f"| {field} | {f['wells']} | {f['cum']:.1f} | {f['eur']:.0f} | "
            f"{avg(f['uptime']):.1f} | {avg(f['decline']):.1f} | {f['interv']} | "
            f"{npv:,.1f} | {be:,.0f} | {sens:.1f} |"
            if npv is not None and be is not None and sens is not None
            else f"| {field} | {f['wells']} | {f['cum']:.1f} | {f['eur']:.0f} | "
            f"{avg(f['uptime']):.1f} | {avg(f['decline']):.1f} | {f['interv']} | ? | ? | ? |"
        )
        tot["wells"] += f["wells"]
        tot["cum"] += f["cum"]
        tot["eur"] += f["eur"]
        tot["interv"] += f["interv"]
        if npv is not None:
            tot["npv"] += npv
    lines.append(
        f"| **Portfolio** | **{tot['wells']}** | **{tot['cum']:.1f}** | **{tot['eur']:.0f}** "
        f"| — | — | **{tot['interv']}** | **{tot['npv']:,.1f}** | — | — |"
    )
    lines += [
        "",
        "**Reading it:** every field is NPV-negative at 10% life-to-date — the Lower",
        "Tertiary's high up-front capital dominates. Break-even WTI shows how far",
        "above the realized ~$69/bbl each field would need to clear zero; the",
        "per-$1/bbl column is the exact NPV slope (NPV is affine in price).",
        "",
        "_Source: `worldenergydata` BSEE OGOR-A + V30 cost model. Regenerate:_",
        "_`uv run python scripts/lower_tertiary/build_well_benchmark.py` then_",
        "_`uv run python scripts/lower_tertiary/build_field_performance_comparison.py`._",
        "",
    ]
    return "\n".join(lines)


def build_contract() -> str:
    """Machine-readable per-field performance contract (same aggregation as the
    md renderer). Keyed by canonical id (`_slug` == life-cycle poster id).
    Benchmark-derived numbers rounded to the table's displayed precision;
    economics keys are nullable (None when the report regexes miss)."""
    fields = _aggregate()
    out: dict[str, dict] = {}
    for field, f in fields.items():
        e = _econ(field)
        out[_slug(field)] = {
            "display": field,
            "wells": f["wells"],
            "cum_oil_mmbbl": round(f["cum"], 1),
            "eur_mmbbl": round(f["eur"]),
            "avg_uptime_pct": round(_avg(f["uptime"]), 1),
            "avg_decline_pct_yr": round(_avg(f["decline"]), 1),
            "interventions": f["interv"],
            "npv_mm": e.get("npv_mm"),
            "breakeven_wti": e.get("breakeven_wti"),
            "sens_mm_per_dollar": e.get("sens_mm_per_dollar"),
        }
    payload = {"meta": CONTRACT_META, "fields": out}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> int:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPORTS.parents[1])}")
    CONTRACT.write_text(build_contract(), encoding="utf-8")
    print(f"wrote {CONTRACT.relative_to(REPORTS.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
