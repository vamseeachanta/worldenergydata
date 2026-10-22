#!/usr/bin/env python3
# ABOUTME: Generates the riser-fatigue grounded card — real BSEE riser incidents + a live dm run (#771).
# ABOUTME: Second live arc of the engineering<->asset circle (#764), generalising the mooring card (#768).

"""Generate the riser-fatigue grounded card.

Pairs the live BSEE grounding for riser / flowline structural failure with a LIVE
digitalmodel riser_fatigue result, rendering one self-contained HTML card.

Usage::

    python scripts/demo/generate_riser_grounded_card.py \
        [--out reports/hse/riser-fatigue-grounded-card.html] [--illustrative]

Use ``--summary-csv`` with ``--required-life-years`` and ``--basis-source``
to render previously generated results without executing an analysis. The criterion
is a required factored life, not the unfactored service life. Imported results
retain their byte digest and are never labelled live.

The grounding numbers are 100% real public BSEE records; the engineering panel is a
live digitalmodel run unless ``--illustrative`` is set or digitalmodel is unavailable.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from _riser_live import build_live_analysis
from _riser_results import analysis_from_csv

from worldenergydata.hse.grounding_card import AnalysisSummary, render_html
from worldenergydata.hse.grounding_demand import ground_and_log

# Fallback (illustrative) panel — used only with --illustrative or if dm is unavailable.
ANALYSIS = AnalysisSummary(
    title="Riser Fatigue — SCR touchdown zone",
    headline="NOT_EVALUATED — fatigue life and design criterion are not supplied.",
    metrics=[
        ("— yr", "Min fatigue life"),
        ("—", "Wave damage"),
        ("—", "VIV damage"),
        ("NOT_EVALUATED", "Required factored life"),
    ],
    method="T-N / S-N wave + VIV screening (DNV-RP-C203, DNV-OS-F201)",
    basis="Illustrative placeholder; replace with a live digitalmodel run.",
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="reports/hse/riser-fatigue-grounded-card.html")
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument(
        "--summary-csv",
        type=Path,
        help=(
            "Import results without running a solver. Nonfinite life "
            "(including zero-damage infinite life) rejects the entire import."
        ),
    )
    ap.add_argument(
        "--required-life-years",
        type=float,
        help="Required factored fatigue life in years.",
    )
    ap.add_argument(
        "--basis-source",
        help="Document, edition and clause for the supplied criterion.",
    )
    modes.add_argument(
        "--illustrative",
        action="store_true",
        help="Use the illustrative panel instead of a live digitalmodel run.",
    )
    a = ap.parse_args(argv)

    if a.summary_csv is not None:
        if a.required_life_years is None or not a.basis_source:
            ap.error("--summary-csv requires --required-life-years and --basis-source")
        analysis = analysis_from_csv(
            a.summary_csv, a.required_life_years, a.basis_source
        )
        print("  engineering  : imported summary (no solver executed)")
    elif a.required_life_years is not None or a.basis_source is not None:
        ap.error("criterion options require --summary-csv")
    elif a.illustrative:
        analysis = ANALYSIS
        print("  engineering  : illustrative (--illustrative)")
    else:
        try:
            analysis = build_live_analysis()
            print("  engineering  : LIVE digitalmodel riser_fatigue run")
        except Exception as exc:  # noqa: BLE001 — degrade gracefully, never fake "live"
            analysis = ANALYSIS
            print(f"  engineering  : live run unavailable ({exc}); using illustrative")

    g = ground_and_log("riser_fatigue")
    generated_on = dt.date.today().isoformat()
    html_doc = render_html(g.to_dict(), analysis, generated_on)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")

    print(f"wrote {out} ({len(html_doc):,} bytes)")
    print(f"  failure mode : {g.failure_mode}")
    print(f"  latest       : {[i.date for i in g.latest]}")
    print(f"  most severe  : {[(i.date, i.severity) for i in g.most_severe]}")
    print(f"  sources      : {g.source_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
