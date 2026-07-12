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
    "economics_note": (
        "npv_mm / breakeven_wti are LIFE-TO-DATE, pre-tax, 10%-discounted "
        "(economics_basis=life_to_date_pretax_npv_at_10pct): full sunk capex "
        "charged against oil produced to date, not full-cycle EUR. Fields early "
        "in life are legitimately deep-negative, so their values are withheld "
        "(economics_status=early_life -> null) rather than surfaced as absurd "
        "numbers; a credible full-cycle recompute is tracked in #973."
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


# --- Economics honesty gate (#971) ---------------------------------------
# The joined economics is a LIFE-TO-DATE, pre-tax, 10%-discounted NPV that
# charges 100% of a field's sunk capex against only the oil produced to date
# (cum_oil), NOT against full-cycle EUR. For a field that has produced ~1-2% of
# its ultimate recovery that yields a legitimately large negative NPV and a
# breakeven far above any credible price deck. The numbers are arithmetically
# correct but were mislabeled as full-cycle. Until a credible full-cycle
# recompute lands (#973, gated on validating eur_mmbbl), we:
#   1. label the metric as life-to-date (economics_basis), and
#   2. surface it ONLY where it is client-credible; absurd early-life values are
#      withheld (economics_status == "early_life") so every downstream surface
#      renders "n/a — early life" instead of a scary artifact.
# The gate is applied HERE, at the single source of the per-field contract, so
# the poster / PDF / Explorer / HF projection all inherit the same suppression.
ECONOMICS_BASIS = "life_to_date_pretax_npv_at_10pct"
# $/bbl. Above this the life-to-date breakeven is not client-credible (~2x the
# realized ~$69 deck). Load-bearing: it withholds fields well past the EUR-
# fraction floor whose breakeven is still absurd (e.g. Cascade/Chinook, Stones).
CEILING_BREAKEVEN_WTI = 150.0
# Surface only once a field has produced at least this fraction of its EUR.
# NB eur_mmbbl is itself an unvalidated decline-fit extrapolation (#973); an
# inflated EUR shrinks the fraction, so this floor errs toward MORE suppression
# (conservative). The ceiling above does most of the work.
MIN_EUR_FRACTION = 0.15


def _gate_economics(agg: dict, econ: dict) -> dict:
    """Apply the #971 life-to-date honesty gate to one field's economics.

    Returns the surfaced economics keys plus an explicit basis/status. Values
    are nulled (contract keys stay present) for withheld fields so consumers
    render them as "n/a — early life". `sens_mm_per_dollar` is the derivative
    of the same NPV, so it is withheld together with the level it describes.
    """
    npv = econ.get("npv_mm")
    be = econ.get("breakeven_wti")
    sens = econ.get("sens_mm_per_dollar")
    eur = agg["eur"]
    frac = agg["cum"] / eur if eur > 0 else 0.0
    if npv is None or be is None:
        status = "unavailable"
    elif frac < MIN_EUR_FRACTION or be > CEILING_BREAKEVEN_WTI:
        status = "early_life"
    else:
        status = "surfaced"
    if status != "surfaced":
        npv = be = sens = None
    return {
        "npv_mm": npv,
        "breakeven_wti": be,
        "sens_mm_per_dollar": sens,
        "economics_basis": ECONOMICS_BASIS,
        "economics_status": status,
    }


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
        "| Field | Wells | Cum oil (MMbbl) | EUR (MMbbl) | Avg uptime % | Avg decline %/yr | Interventions | NPV, LTD @10% ($MM) | LTD breakeven WTI ($/bbl) | NPV per +$1/bbl ($MM) |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    tot = {"wells": 0, "cum": 0.0, "eur": 0.0, "interv": 0, "npv": 0.0}
    surfaced = 0
    for field, f in ordered:
        g = _gate_economics(f, _econ(field))
        npv, be, sens = g["npv_mm"], g["breakeven_wti"], g["sens_mm_per_dollar"]
        if g["economics_status"] == "surfaced":
            econ_cells = f"{npv:,.1f} | {be:,.0f} | {sens:.1f}"
            surfaced += 1
            tot["npv"] += npv
        else:
            # Withheld as early-life (or economics report absent): show n/a, not
            # an absurd number, on every consumer of this row.
            econ_cells = "n/a | n/a | n/a"
        lines.append(
            f"| {field} | {f['wells']} | {f['cum']:.1f} | {f['eur']:.0f} | "
            f"{avg(f['uptime']):.1f} | {avg(f['decline']):.1f} | {f['interv']} | "
            f"{econ_cells} |"
        )
        tot["wells"] += f["wells"]
        tot["cum"] += f["cum"]
        tot["eur"] += f["eur"]
        tot["interv"] += f["interv"]
    # The portfolio economics cell is intentionally not a sum: with most fields
    # withheld it would be a misleading fragment of the total. Em-dash it.
    lines.append(
        f"| **Portfolio** | **{tot['wells']}** | **{tot['cum']:.1f}** | **{tot['eur']:.0f}** "
        f"| — | — | **{tot['interv']}** | — | — | — |"
    )
    lines += [
        "",
        f"**Reading it:** economics are **life-to-date at 10%** on public BSEE data — "
        f"they charge each field's full sunk capital against only the oil produced "
        f"*so far*, not against full-cycle EUR. For fields early in life that is "
        f"legitimately deep-negative, so those values are **withheld as early-life** "
        f"(shown `n/a`); only {surfaced} of 7 fields have produced enough of their EUR "
        f"and clear a credible breakeven to surface a life-to-date number. Those still "
        f"read negative — the Lower Tertiary's high up-front capital, discounted "
        f"against a long revenue tail, dominates at this point in life; the LTD "
        f"breakeven shows how far above the realized ~$69/bbl the field would need to "
        f"clear zero to date. A credible **full-cycle** recompute is deferred to #973 "
        f"(gated on validating the decline-fit EUR). See per-field "
        f"`field_economics_<slug>.md` for the full life-to-date derivation.",
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
        gated = _gate_economics(f, _econ(field))
        out[_slug(field)] = {
            "display": field,
            "wells": f["wells"],
            "cum_oil_mmbbl": round(f["cum"], 1),
            "eur_mmbbl": round(f["eur"]),
            "avg_uptime_pct": round(_avg(f["uptime"]), 1),
            "avg_decline_pct_yr": round(_avg(f["decline"]), 1),
            "interventions": f["interv"],
            **gated,
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
