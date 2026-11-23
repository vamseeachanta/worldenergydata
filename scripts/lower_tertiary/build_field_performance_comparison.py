#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Build the Lower Tertiary FIELD-performance comparison (deterministic).

Aggregates the per-well benchmark (`lt_well_benchmark_*.csv`) up to the field
level and joins each field's economics (NPV @10%, WTI break-even, $/bbl
sensitivity) parsed from the committed `field_economics_<slug>.md` reports.
`eur_mmbbl` is the CURATED published/booked recoverable reserve from
`config/lt_field_reserves.yml` (#973) — NOT the ~2-6.6x-inflated decline-fit
sum. Deterministic; same inputs -> byte-identical output.

    uv run python scripts/lower_tertiary/build_field_performance_comparison.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import yaml

REPORTS = Path(__file__).resolve().parents[2] / "reports" / "lower_tertiary"
BENCH = REPORTS / "lt_well_benchmark_lower_tertiary_2010_latest.csv"
RESERVES = Path(__file__).resolve().parents[2] / "config" / "lt_field_reserves.yml"
OUT = REPORTS / "lt_field_performance_comparison.md"
CONTRACT = REPORTS / "lifecycle" / "_performance.json"

CONTRACT_META = {
    "source": (
        "BSEE OGOR-A per-well benchmark + cost model, "
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
    "eur_note": (
        "eur_mmbbl is CURATED published/booked recoverable reserves "
        "(config/lt_field_reserves.yml, #973) with eur_source + eur_confidence "
        "— NOT the decline-fit sum, which ran ~2-6.6x too high. null where no "
        "credible public figure exists (eur_confidence=none)."
    ),
    "inputs": [
        "reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv",
        "reports/lower_tertiary/field_economics_<slug>.md",
        "config/lt_field_reserves.yml",
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


def _reserves() -> dict:
    """Curated recoverable-reserves table (#973), keyed by canonical field id.

    eur_mmbbl here is published/booked recoverable reserves (or None where no
    credible public figure exists) — the AUTHORITATIVE full-cycle EUR, replacing
    the ~2-6.6x-inflated decline-fit sum. See config/lt_field_reserves.yml.
    """
    return (yaml.safe_load(RESERVES.read_text(encoding="utf-8")) or {}).get(
        "fields", {}
    )


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
# Evaluated against the CURATED reserve (#973). When EUR is unknown (curated
# null) the fraction can't be computed, so the breakeven ceiling governs alone.
MIN_EUR_FRACTION = 0.15


def _gate_economics(cum: float, eur, econ: dict) -> dict:
    """Apply the #971 life-to-date honesty gate to one field's economics.

    `eur` is the curated recoverable reserve (#973), possibly None. Returns the
    surfaced economics keys plus an explicit basis/status. Values are nulled
    (contract keys stay present) for withheld fields so consumers render them as
    "n/a — early life". `sens_mm_per_dollar` is the derivative of the same NPV,
    so it is withheld together with the level it describes.
    """
    npv = econ.get("npv_mm")
    be = econ.get("breakeven_wti")
    sens = econ.get("sens_mm_per_dollar")
    if npv is None or be is None:
        status = "unavailable"
    else:
        over_ceiling = be > CEILING_BREAKEVEN_WTI
        # Fraction test only when EUR is known; else the ceiling governs alone.
        too_early = eur is not None and eur > 0 and cum / eur < MIN_EUR_FRACTION
        status = "early_life" if (over_ceiling or too_early) else "surfaced"
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
    reserves = _reserves()
    avg = _avg

    ordered = sorted(fields.items(), key=lambda kv: kv[1]["cum"], reverse=True)

    lines = [
        "# Lower Tertiary — field-performance comparison",
        "",
        "All seven producing Lower Tertiary fields, side by side, from **public BSEE",
        "data**. Per-well benchmark aggregated to the field level; economics joined",
        "from the per-field reports. Life-to-date on public data — not full-cycle",
        "economics. Deterministic and reproducible.",
        "",
        "| Field | Wells | Cum oil (MMbbl) | EUR (MMbbl) | Avg uptime % | Avg decline %/yr | Interventions | NPV, LTD @10% ($MM) | LTD breakeven WTI ($/bbl) | NPV per +$1/bbl ($MM) |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    tot = {"wells": 0, "cum": 0.0, "eur": 0.0, "interv": 0, "npv": 0.0}
    surfaced = 0
    for field, f in ordered:
        eur = reserves.get(_slug(field), {}).get("eur_mmbbl")
        g = _gate_economics(f["cum"], eur, _econ(field))
        npv, be, sens = g["npv_mm"], g["breakeven_wti"], g["sens_mm_per_dollar"]
        eur_cell = f"{eur:.0f}" if eur is not None else "pending"
        if eur is not None:
            tot["eur"] += eur
        if g["economics_status"] == "surfaced":
            econ_cells = f"{npv:,.1f} | {be:,.0f} | {sens:.1f}"
            surfaced += 1
            tot["npv"] += npv
        else:
            # Withheld as early-life (or economics report absent): show n/a, not
            # an absurd number, on every consumer of this row.
            econ_cells = "n/a | n/a | n/a"
        lines.append(
            f"| {field} | {f['wells']} | {f['cum']:.1f} | {eur_cell} | "
            f"{avg(f['uptime']):.1f} | {avg(f['decline']):.1f} | {f['interv']} | "
            f"{econ_cells} |"
        )
        tot["wells"] += f["wells"]
        tot["cum"] += f["cum"]
        tot["interv"] += f["interv"]
    # Portfolio EUR = sum of the curated reserves that ARE known (pending fields
    # excluded). The economics cell is intentionally not a sum: with most fields
    # withheld it would be a misleading fragment of the total. Em-dash it.
    lines.append(
        f"| **Portfolio** | **{tot['wells']}** | **{tot['cum']:.1f}** | **{tot['eur']:.0f}+** "
        f"| — | — | **{tot['interv']}** | — | — | — |"
    )
    lines += [
        "",
        f"**Reading it:** **EUR is curated published/booked recoverable reserves** "
        f"(operator & independent-auditor disclosures, `config/lt_field_reserves.yml`), "
        f"NOT the decline-fit extrapolation — which ran ~2–6.6x too high (#973). Two "
        f"fields with no public recoverable figure show `pending`. Economics are "
        f"**life-to-date at 10%** on public BSEE data: full sunk capital charged against "
        f"only the oil produced *so far*, not full-cycle EUR. Early-life fields are "
        f"**withheld** (`n/a`); only {surfaced} of 7 surface a credible life-to-date "
        f"number, and those still read negative — the Lower Tertiary's high up-front "
        f"capital, discounted against a long revenue tail, dominates at this point in "
        f"life. A credible **full-cycle** NPV projected to the curated reserves is the "
        f"next step (#971 Tier 1). See per-field `field_economics_<slug>.md` for the "
        f"life-to-date derivation.",
        "",
        "_Source: `worldenergydata` BSEE OGOR-A + cost model. Regenerate:_",
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
    reserves = _reserves()
    out: dict[str, dict] = {}
    for field, f in fields.items():
        res = reserves.get(_slug(field), {})
        eur = res.get("eur_mmbbl")  # curated recoverable reserve, may be None
        gated = _gate_economics(f["cum"], eur, _econ(field))
        out[_slug(field)] = {
            "display": field,
            "wells": f["wells"],
            "cum_oil_mmbbl": round(f["cum"], 1),
            "eur_mmbbl": eur,
            "eur_source": res.get("basis") or "reserves pending (#973)",
            "eur_confidence": res.get("confidence", "none"),
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
