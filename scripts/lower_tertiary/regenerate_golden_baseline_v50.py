#!/usr/bin/env python3
"""ABOUTME: Regenerate config/analysis/lower_tertiary/golden_baseline_v50.yml.
ABOUTME: V50 = the V30 financial methodology re-run at the latest OGOR-A window.

V50 is the next sanctioned "gold standard" vintage of the Lower Tertiary
financial baseline. It runs the *identical* methodology as the frozen V30
baseline (``reproduce_v30_financials``) but with the production window, WTI
cascade, and cashflow horizon extended to the latest available BSEE OGOR-A
month (un-suffixed ``ogoradelimit.bin``). Because the only thing that changes
between V30 and V50 is the data window, every V30->V50 delta is attributable
to new data, not to a methodology change.

The frozen V30 golden baseline (``golden_baseline_v30.yml``) is NEVER touched.

Each project carries the full financial schema (matching the V30 file) plus a
``v30_comparison`` block (NPV / oil / revenue deltas) — the QA/QC "compared to
before" that the data refresh was requested for.

Because the OGOR-A ``.zip`` archives are absent in slimmed checkouts (only the
pickled ``.bin`` DataFrames are present), this driver calls
``ensure_ogor_loader`` so production reads the ``.bin`` source — including the
finalised 2025 file and the current-year 2026 ``ogoradelimit.bin``.

Dates are passed in explicitly (no wall-clock); ``--extraction-date`` stamps
the metadata header, ``--end-date`` (or auto-detect) bounds the window.

Usage
-----
    python scripts/lower_tertiary/regenerate_golden_baseline_v50.py \
        --extraction-date 2026-06-26            # auto-detect latest OGOR month
    python scripts/lower_tertiary/regenerate_golden_baseline_v50.py \
        --end-date 2026-04-30 --extraction-date 2026-06-26
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "worldenergydata-bsee" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.lower_tertiary.latest_runner import (  # noqa: E402
    FIRST_OIL_CORRECTIONS,
)
from worldenergydata.lower_tertiary.ops_timeline import (  # noqa: E402
    detect_latest_ogor_month,
    ensure_ogor_loader,
    month_end_str,
)
from worldenergydata.lower_tertiary.v30_financial_reproducer import (  # noqa: E402
    reproduce_v30_financials,
)

V30_PATH = (
    PROJECT_ROOT / "config" / "analysis" / "lower_tertiary" / "golden_baseline_v30.yml"
)
V50_PATH = (
    PROJECT_ROOT / "config" / "analysis" / "lower_tertiary" / "golden_baseline_v50.yml"
)


def _yaml_str(v: object) -> str:
    return f'"{v}"'


def _pct(new: float | None, old: float | None) -> float | None:
    """Signed % change new vs old; None when old is missing/zero."""
    if old in (None, 0) or new is None:
        return None
    return round((new - old) / abs(old) * 100.0, 2)


def _round2(v: float | None) -> float | None:
    return None if v is None else round(float(v), 2)


def build_yaml(
    v50_fin: dict[str, dict],
    v30_yml: dict,
    end_date: str,
    extraction_date: str,
    source_desc: str,
    first_oil_overrides: dict[str, str] | None = None,
) -> str:
    """Serialise golden_baseline_v50.yml mirroring the V30 schema + comparison.

    The ``v30_comparison`` block references the *frozen official* V30 figures
    (``golden_baseline_v30.yml``) — the sanctioned "before" — not a re-run, so
    the V50 file is self-consistent with the V30 file of record.

    Caveat carried into the comparison report: Jack St Malo (and, more mildly,
    Cascade Chinook) carry a known reproducer-vs-frozen NPV offset (~7.3% for
    JSM, from monthly D&C allocation timing). Their NPV deltas therefore mix the
    data/window effect with that offset; production and revenue deltas are clean
    for all fields.
    """
    projects = v30_yml["projects"]
    period_label = end_date[:7]

    lines: list[str] = []
    lines.append("# Golden Baseline: FDAS V50 Financial Project Summary")
    lines.append(
        "# V50 = V30 methodology re-run at the latest BSEE OGOR-A window "
        f"({period_label})."
    )
    lines.append(
        "# Source: BSEE OGOR-A (latest .bin) + frozen V30 lease mappings & assumptions"
    )
    lines.append(f"# OGOR source: {source_desc}")
    lines.append(f"# Generated: {extraction_date}")
    lines.append("# Frozen V30 baseline (golden_baseline_v30.yml) is NEVER modified.")
    lines.append("")
    lines.append("metadata:")
    lines.append("  based_on: golden_baseline_v30.yml")
    lines.append(
        "  methodology: reproduce_v30_financials (identical to V30; data window extended)"
    )
    lines.append(
        "  first_oil_corrections: "
        + _yaml_str(
            "Cascade Chinook 2014-01-01 -> 2012-09-01 (verified vs raw OGOR; "
            "golden V30 carried an error). V30 stays frozen; V50 adopts the fix."
        )
    )
    lines.append(f"  extraction_date: {_yaml_str(extraction_date)}")
    lines.append(f"  time_period: {_yaml_str(f'2000-09 through {period_label}')}")
    lines.append(f"  v30_time_period: {_yaml_str('2000-09 through 2025-05')}")
    lines.append(
        "  note: "
        + _yaml_str(
            "V50 extends the V30 production + WTI + cashflow window to the latest "
            "OGOR-A month. Methodology, cost assumptions, royalty/opex rates, and "
            "discounting are identical to V30 (end_date param only). Deltas vs V30 "
            "reflect new production data and the longer window."
        )
    )
    lines.append("")
    lines.append("tolerances:")
    for t in v30_yml.get("tolerances", {}):
        lines.append(f"  {t}: {v30_yml['tolerances'][t]}")
    lines.append("")
    lines.append("projects:")

    for key, p in projects.items():
        dn = p["display_name"]
        f50 = v50_fin.get(dn, {})
        # "before" = frozen official V30 (golden_baseline_v30.yml)
        f30 = {
            "total_oil_bbl": p.get("total_oil_bbl"),
            "revenue_usd": p.get("revenue_usd"),
            "npv_usd": p.get("npv_usd"),
        }
        is_producing = p.get("first_oil") is not None and p.get("total_oil_bbl", 0)

        lines.append(f"  {key}:")
        lines.append(f"    display_name: {_yaml_str(dn)}")
        lines.append(f"    dev_system: {p.get('dev_system','')}")
        fo = (first_oil_overrides or {}).get(dn, p.get("first_oil"))
        lines.append(f"    first_oil: {_yaml_str(fo) if fo else 'null'}")

        if is_producing:
            lines.append(
                f"    total_oil_bbl: {int(round(f50.get('total_oil_bbl', 0)))}"
            )
            lines.append(
                f"    facilities_cost_usd: {int(round(f50.get('facilities_cost_usd', 0)))}"
            )
            lines.append(
                f"    dnc_total_usd: {int(round(f50.get('dnc_total_usd', 0)))}"
            )
            lines.append(f"    revenue_usd: {_round2(f50.get('revenue_usd'))}")
            lines.append(f"    royalty_usd: {_round2(f50.get('royalty_usd'))}")
            lines.append(
                f"    variable_opex_usd: {int(round(f50.get('variable_opex_usd', 0)))}"
            )
            lines.append(
                f"    fixed_opex_usd: {int(round(f50.get('fixed_opex_usd', 0)))}"
            )
            lines.append(
                f"    net_cashflow_usd: {_round2(f50.get('net_cashflow_usd'))}"
            )
            lines.append(f"    npv_usd: {_round2(f50.get('npv_usd'))}")
            mm = f50.get("mirr_monthly")
            ma = f50.get("mirr_annual")
            import math as _m

            mm_s = (
                "null"
                if mm is None or (isinstance(mm, float) and _m.isnan(mm))
                else f"{mm:.6f}"
            )
            ma_s = (
                "null"
                if ma is None or (isinstance(ma, float) and _m.isnan(ma))
                else f"{ma:.5f}"
            )
            lines.append(f"    mirr_monthly: {mm_s}")
            lines.append(f"    mirr_annual: {ma_s}")
            lines.append(f"    producers: {p.get('producers', 0)}")
            lines.append(f"    injectors: {p.get('injectors', 0)}")
            lines.append(
                f"    wellbores: {int(round(f50.get('wellbores', p.get('wellbores', 0))))}"
            )
            lines.append("    v30_comparison:")
            lines.append(
                f"      v30_oil_bbl: {int(round(f30.get('total_oil_bbl', p.get('total_oil_bbl', 0)) or 0))}"
            )
            lines.append(
                f"      delta_oil_pct: {_pct(f50.get('total_oil_bbl'), f30.get('total_oil_bbl') or p.get('total_oil_bbl'))}"
            )
            lines.append(f"      v30_revenue_usd: {_round2(f30.get('revenue_usd'))}")
            lines.append(
                f"      delta_revenue_pct: {_pct(f50.get('revenue_usd'), f30.get('revenue_usd'))}"
            )
            lines.append(f"      v30_npv_usd: {_round2(f30.get('npv_usd'))}")
            lines.append(
                f"      delta_npv_usd: {_round2((f50.get('npv_usd') or 0) - (f30.get('npv_usd') or 0))}"
            )
        else:
            # Exploration-only: D&C only (no production). Window does not add oil.
            lines.append("    total_oil_bbl: 0")
            lines.append(
                f"    dnc_total_usd: {int(round(f50.get('dnc_total_usd', 0)))}"
            )
            lines.append(f"    npv_usd: {_round2(f50.get('npv_usd'))}")
            lines.append(
                f"    wellbores: {int(round(f50.get('wellbores', p.get('wellbores', 0))))}"
            )
            lines.append("    v30_comparison:")
            lines.append(f"      v30_npv_usd: {_round2(f30.get('npv_usd'))}")
            lines.append(
                f"      delta_npv_usd: {_round2((f50.get('npv_usd') or 0) - (f30.get('npv_usd') or 0))}"
            )
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--end-date",
        default=None,
        help="Upper bound YYYY-MM-DD; default auto-detect latest OGOR month.",
    )
    parser.add_argument(
        "--extraction-date",
        required=True,
        help="Date stamped into metadata (YYYY-MM-DD).",
    )
    parser.add_argument("--out", default=str(V50_PATH), help="Output YAML path.")
    args = parser.parse_args(argv)

    source_desc = ensure_ogor_loader()
    end_date = args.end_date
    if end_date is None:
        latest = detect_latest_ogor_month()
        end_date = month_end_str(latest)
        print(
            f"Auto-detected latest OGOR-A month: {latest.strftime('%Y-%m')} -> end_date {end_date}"
        )

    v30_yml = yaml.safe_load(V30_PATH.read_text())
    print(f"Computing V50 (end_date={end_date}) ...")
    print(f"  Applying verified first-oil corrections: {FIRST_OIL_CORRECTIONS}")
    v50_fin = reproduce_v30_financials(
        end_date=end_date, first_oil_overrides=FIRST_OIL_CORRECTIONS
    )

    text = build_yaml(
        v50_fin,
        v30_yml,
        end_date,
        args.extraction_date,
        source_desc,
        first_oil_overrides=FIRST_OIL_CORRECTIONS,
    )
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"Wrote {args.out} (end_date={end_date})")


if __name__ == "__main__":
    main()
