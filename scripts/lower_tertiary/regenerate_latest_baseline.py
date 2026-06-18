#!/usr/bin/env python3
"""ABOUTME: Regenerate config/analysis/lower_tertiary/latest_baseline.yml.
ABOUTME: Extends the V30 production+revenue window to the latest OGOR-A month.

Runs the WRK-010 "latest" pipeline
(``worldenergydata.lower_tertiary.latest_runner.run_classified_analysis``)
through an end_date, compares against the frozen V30 golden baseline, and
serialises the per-development result into ``latest_baseline.yml`` using the
exact schema of the prior file.

The frozen V30 golden baseline (``golden_baseline_v30.yml``) is NEVER touched.

Because the OGOR-A ``.zip`` archives are absent in slimmed checkouts (only the
pickled ``.bin`` DataFrames are present), this driver reuses the ``.bin``
monkeypatch from ``generate_field_economics_report`` so production reads the
same source the report does — including the finalised 2025 file and the
2026 ``ogoradelimit.bin``.

Dates are passed in explicitly (no wall-clock); ``--extraction-date`` stamps
the metadata header.

Usage
-----
    uv run python scripts/lower_tertiary/regenerate_latest_baseline.py \
        --extraction-date 2026-06-17          # auto-detect latest OGOR month
    uv run python scripts/lower_tertiary/regenerate_latest_baseline.py \
        --end-date 2026-04-30 --extraction-date 2026-06-17
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "lower_tertiary"))

import generate_field_economics_report as report  # noqa: E402

from worldenergydata.lower_tertiary.latest_runner import (  # noqa: E402
    compare_against_v30,
    run_classified_analysis,
)

LATEST_BASELINE_PATH = (
    PROJECT_ROOT / "config" / "analysis" / "lower_tertiary" / "latest_baseline.yml"
)


def _proj_key(display_name: str) -> str:
    return display_name.lower().replace(" ", "_").replace("/", "_")


def _yaml_str(v: object) -> str:
    return f'"{v}"'


def regenerate(end_date: str, extraction_date: str) -> str:
    """Run the latest pipeline and return the YAML text for latest_baseline.yml."""
    # Patch the OGOR loader to read .bin (zip archives absent in checkout).
    source_desc = report._ensure_ogor_loader()

    latest = run_classified_analysis(end_date=end_date)
    comparison = compare_against_v30(latest)

    meta = latest["metadata"]
    wti = meta["wti_source_summary"]
    devs = latest["developments"]
    comps = comparison["developments"]

    end_ts = pd.Timestamp(end_date)
    period_label = end_ts.strftime("%Y-%m")

    lines: list[str] = []
    lines.append("# Latest Baseline: Extended Lower Tertiary Analysis (WRK-010)")
    lines.append(
        f"# Source: BSEE OGOR-A through {end_ts.strftime('%b %Y')} "
        "+ V30 lease mappings"
    )
    lines.append(
        f"# WTI: v30_xlsx={wti['v30_xlsx']} eia_github={wti['eia_github']} "
        f"fred_api={wti['fred_api']} flat_forward={wti['flat_forward']}"
    )
    lines.append(f"# Generated: {extraction_date}")
    lines.append(f"# OGOR source: {source_desc}")
    lines.append("")
    lines.append("metadata:")
    lines.append("  based_on: golden_baseline_v30.yml")
    lines.append(f"  extraction_date: {_yaml_str(extraction_date)}")
    lines.append(f"  time_period: {_yaml_str(f'2000-09 through {period_label}')}")
    lines.append(f"  v30_time_period: {_yaml_str('2000-09 through 2025-05')}")
    lines.append("  wti_sources:")
    lines.append(f"    v30_xlsx: {wti['v30_xlsx']}")
    lines.append(f"    eia_github: {wti['eia_github']}")
    lines.append(f"    fred_api: {wti['fred_api']}")
    lines.append(f"    flat_forward: {wti['flat_forward']}")
    lines.append(
        "  note: "
        + _yaml_str(
            f"Extended V30 production window to {period_label}. "
            "Revenue uses historical monthly WTI (EIA/FRED) with flat-forward "
            "fallback for any uncovered tail months."
        )
    )
    lines.append("")
    lines.append("projects:")

    # Preserve the original project ordering from the existing file when present.
    order: list[str] = []
    try:
        import yaml

        prior = yaml.safe_load(LATEST_BASELINE_PATH.read_text())
        order = list(prior.get("projects", {}).keys())
    except Exception:
        order = []

    display_to_key = {dn: _proj_key(dn) for dn in comps}
    key_to_display = {v: k for k, v in display_to_key.items()}
    ordered_keys = [k for k in order if k in key_to_display]
    ordered_keys += [k for k in display_to_key.values() if k not in ordered_keys]

    for key in ordered_keys:
        dn = key_to_display[key]
        comp = comps[dn]
        dev = devs.get(dn, {})
        lines.append(f"  {key}:")
        lines.append(f"    display_name: {_yaml_str(dn)}")
        lines.append(f"    total_oil_bbl: {int(comp['latest_oil_bbl'])}")
        lines.append(
            f"    total_revenue_usd: {round(float(comp['latest_revenue_usd']), 2)}"
        )
        wt = dev.get("well_test_oil_bbl", 0.0)
        if wt:
            lines.append(f"    well_test_oil_bbl: {int(round(wt))}")
        if "months" in dev:
            lines.append(f"    months: {int(dev['months'])}")
            lines.append(f"    first_date: {_yaml_str(dev['first_date'])}")
            lines.append(f"    last_date: {_yaml_str(dev['last_date'])}")
        lines.append("    v30_comparison:")
        lines.append(f"      v30_oil_bbl: {int(comp['v30_oil_bbl'])}")
        lines.append(f"      delta_oil_bbl: {int(comp['delta_oil_bbl'])}")
        lines.append(f"      delta_oil_pct: {comp['delta_oil_pct']}")
        lines.append(
            f"      v30_revenue_usd: {round(float(comp['v30_revenue_usd']), 2)}"
        )
        lines.append(
            f"      delta_revenue_usd: {round(float(comp['delta_revenue_usd']), 2)}"
        )
        lines.append(f"      delta_revenue_pct: {comp['delta_revenue_pct']}")
        lines.append(
            f"      is_significant: {str(bool(comp['is_significant'])).lower()}"
        )
        lines.append("")

    # Exploration-only developments (zero production) — preserved as
    # status:unchanged markers, matching the prior file's schema.
    for dn in comparison.get("exploration_unchanged", []):
        key = _proj_key(dn)
        lines.append(f"  {key}:")
        lines.append(f"    display_name: {_yaml_str(dn)}")
        lines.append("    total_oil_bbl: 0")
        lines.append('    status: "unchanged"')
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--end-date",
        default=None,
        help="Upper date bound YYYY-MM-DD. Default: auto-detect latest OGOR month.",
    )
    parser.add_argument(
        "--extraction-date",
        required=True,
        help="Date to stamp into metadata (YYYY-MM-DD); pass in, do not use clock.",
    )
    parser.add_argument(
        "--out",
        default=str(LATEST_BASELINE_PATH),
        help="Output YAML path (default: latest_baseline.yml).",
    )
    args = parser.parse_args(argv)

    report._ensure_ogor_loader()
    end_date = args.end_date
    if end_date is None:
        latest_month = report.detect_latest_ogor_month()
        end_date = report._month_end_str(latest_month)
        print(
            f"Auto-detected latest OGOR-A month: {latest_month.strftime('%Y-%m')} "
            f"-> end_date {end_date}"
        )

    text = regenerate(end_date, args.extraction_date)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"Wrote {args.out} (end_date={end_date})")


if __name__ == "__main__":
    main()
