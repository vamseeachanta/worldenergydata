#!/usr/bin/env python3
"""ABOUTME: Build reports/lower_tertiary/v30_vs_v50_comparison.md from the two baselines.
ABOUTME: Pure YAML diff of golden_baseline_v30.yml vs golden_baseline_v50.yml (no OGOR load).

This is the QA/QC "compared to before" deliverable: per-field oil, revenue, NPV,
and MIRR deltas between the frozen V30 gold standard and the new V50 vintage.

Honesty caveat baked into the report: Jack St Malo (and, mildly, Cascade
Chinook) carry a known reproducer-vs-frozen NPV offset (~7.3% for JSM, from
monthly D&C allocation timing — see test_jsm_npv_within_known_deviation). Their
NPV deltas therefore mix the data/window effect with that offset; production and
revenue deltas are clean for every field.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
V30 = ROOT / "config/analysis/lower_tertiary/golden_baseline_v30.yml"
V50 = ROOT / "config/analysis/lower_tertiary/golden_baseline_v50.yml"
OUT = ROOT / "reports/lower_tertiary/v30_vs_v50_comparison.md"

# Jack St Malo: known reproducer-vs-frozen NPV offset (~7.3%, monthly D&C timing).
# Cascade Chinook: V50 adopts the verified first-oil correction (2014-01 -> 2012-09).
NPV_CAVEAT = {"Jack St Malo"}
FIRST_OIL_FIX = {"Cascade Chinook"}


def _mm(v):
    return None if v is None else v / 1e6


def _bbl_mm(v):
    return None if v is None else v / 1e6


def _pct(new, old):
    if old in (None, 0) or new is None:
        return None
    return (new - old) / abs(old) * 100.0


def _f(v, nd=1):
    return "—" if v is None else f"{v:,.{nd}f}"


def _sign(v, nd=1):
    if v is None:
        return "—"
    return f"+{v:,.{nd}f}" if v >= 0 else f"{v:,.{nd}f}"


def main() -> None:
    v30 = yaml.safe_load(V30.read_text())
    v50 = yaml.safe_load(V50.read_text())
    p30 = v30["projects"]
    p50 = v50["projects"]
    meta50 = v50.get("metadata", {})

    L: list[str] = []
    L.append("# Lower Tertiary Gold Standard: V30 → V50 Comparison")
    L.append("")
    L.append(
        f"- **V30 window:** {v30['metadata'].get('time_period','2000-09 through 2025-05')} "
        "(frozen gold standard — `golden_baseline_v30.yml`)"
    )
    L.append(
        f"- **V50 window:** {meta50.get('time_period','?')} "
        "(new gold standard — `golden_baseline_v50.yml`)"
    )
    L.append(
        f"- **Methodology:** {meta50.get('methodology','reproduce_v30_financials (identical; data window extended)')}"
    )
    L.append(f"- **Generated:** {meta50.get('extraction_date','?')}")
    L.append(
        "- **Source:** new BSEE OGOR-A `.bin` (latest) re-run of Roy Shilling's "
        "rerun-with-latest-ogora request; same lease mapping, cost assumptions, "
        "royalty/opex rates, and 10%/yr discounting as V30."
    )
    L.append("")
    L.append(
        "> **Reproduction gate (before update):** V30 reproduces from raw OGOR within"
    )
    L.append(
        "> ±0.1% on production and ±1% on NPV for all matched projects; Jack St Malo"
    )
    L.append(
        "> NPV sits in its known ~7.3% band (monthly D&C allocation timing). Because"
    )
    L.append(
        "> V50 changes *only* the data window, V30→V50 deltas isolate the new data."
    )
    L.append("")

    # --- Producing fields table ---
    L.append("## Producing fields")
    L.append("")
    L.append(
        "| Field | Oil V30 (MMbbl) | Oil V50 (MMbbl) | ΔOil % | "
        "Rev V30 ($MM) | Rev V50 ($MM) | ΔRev % | "
        "NPV V30 ($MM) | NPV V50 ($MM) | ΔNPV ($MM) |"
    )
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")

    producing = [
        k for k, p in p30.items() if p.get("first_oil") and p.get("total_oil_bbl", 0)
    ]
    tot = {"o30": 0.0, "o50": 0.0, "r30": 0.0, "r50": 0.0, "n30": 0.0, "n50": 0.0}
    for k in producing:
        a, b = p30[k], p50.get(k, {})
        dn = a["display_name"]
        o30, o50 = a.get("total_oil_bbl"), b.get("total_oil_bbl")
        r30, r50 = a.get("revenue_usd"), b.get("revenue_usd")
        n30, n50 = a.get("npv_usd"), b.get("npv_usd")
        for key, val in [
            ("o30", o30),
            ("o50", o50),
            ("r30", r30),
            ("r50", r50),
            ("n30", n30),
            ("n50", n50),
        ]:
            tot[key] += val or 0.0
        star = " ⚠️" if dn in NPV_CAVEAT else (" †" if dn in FIRST_OIL_FIX else "")
        L.append(
            f"| {dn}{star} | {_f(_bbl_mm(o30))} | {_f(_bbl_mm(o50))} | {_sign(_pct(o50,o30))} "
            f"| {_f(_mm(r30))} | {_f(_mm(r50))} | {_sign(_pct(r50,r30))} "
            f"| {_f(_mm(n30))} | {_f(_mm(n50))} | {_sign(_mm((n50 or 0)-(n30 or 0)))} |"
        )
    L.append(
        f"| **Total** | **{_f(_bbl_mm(tot['o30']))}** | **{_f(_bbl_mm(tot['o50']))}** | "
        f"**{_sign(_pct(tot['o50'],tot['o30']))}** | **{_f(_mm(tot['r30']))}** | **{_f(_mm(tot['r50']))}** | "
        f"**{_sign(_pct(tot['r50'],tot['r30']))}** | **{_f(_mm(tot['n30']))}** | **{_f(_mm(tot['n50']))}** | "
        f"**{_sign(_mm(tot['n50']-tot['n30']))}** |"
    )
    L.append("")
    L.append(
        "⚠️ = Jack St Malo NPV carries the known ~7.3% reproducer-vs-frozen offset "
        "(monthly D&C allocation timing); its oil/revenue deltas are data-clean."
    )
    L.append("")
    L.append(
        "† = Cascade Chinook V50 adopts the verified first-oil correction "
        "(2014-01-01 → 2012-09-01, confirmed against raw OGOR); V30 stays frozen "
        "at 2014-01-01. Its delta therefore includes this one fix plus new data."
    )
    L.append("")

    # --- Exploration-only ---
    L.append("## Exploration-only (D&C, no production)")
    L.append("")
    L.append("| Field | NPV V30 ($MM) | NPV V50 ($MM) | ΔNPV ($MM) |")
    L.append("|---|--:|--:|--:|")
    for k, p in p30.items():
        if k in producing:
            continue
        b = p50.get(k, {})
        n30, n50 = p.get("npv_usd"), b.get("npv_usd")
        L.append(
            f"| {p['display_name']} | {_f(_mm(n30))} | {_f(_mm(n50))} | {_sign(_mm((n50 or 0)-(n30 or 0)))} |"
        )
    L.append("")
    L.append("## Notes")
    L.append("")
    L.append(
        "- V50 extends every producer's window by 11 months (2025-05 → 2026-04), so"
    )
    L.append("  oil and revenue rise across the board. The largest jumps are the late")
    L.append(
        "  starters — Shenandoah and Anchor — which had almost no production captured"
    )
    L.append("  in V30.")
    L.append(
        "- NPV improvements reflect the added producing months net of continued opex;"
    )
    L.append("  no field crosses into positive NPV.")
    L.append(
        "- Frozen V30 (`golden_baseline_v30.yml`) is unchanged. V50 lives alongside it."
    )
    L.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
