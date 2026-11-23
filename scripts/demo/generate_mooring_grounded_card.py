#!/usr/bin/env python3
# ABOUTME: Generates the first published mooring-fatigue grounded card (demo, #490).
# ABOUTME: Pairs the live BSEE grounding with a mooring_fatigue analysis result -> HTML.

"""Generate the mooring-fatigue grounded card.

Tracer artifact for the grounded-analysis demo stream (#486, demo slice #490):
runs the real BSEE grounding for mooring fatigue and pairs it with a
representative mooring_fatigue engineering result (from the parametric pilot,
dm#796), rendering one self-contained HTML card.

Usage::

    python scripts/demo/generate_mooring_grounded_card.py \
        [--out reports/hse/mooring-fatigue-grounded-card.html]

The grounding numbers are 100% real public BSEE records; the engineering panel
is labelled as illustrative from the mooring_fatigue workflow until wired to a
live run.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from _mooring_live import build_live_analysis

from worldenergydata.hse.grounding_card import AnalysisSummary, render_html
from worldenergydata.hse.grounding_demand import ground_and_log

# Fallback mooring_fatigue result (illustrative; from the workflow pilot). Used only if
# the live digitalmodel subprocess is unavailable (--illustrative, or dm venv missing).
ANALYSIS = AnalysisSummary(
    title="Mooring Fatigue — Deepwater Semi, 8-line Chain-Polyester",
    headline="Minimum fatigue life 18.4 yr at the fairlead chain — below the 25-yr design basis.",
    metrics=[
        ("18.4 yr", "Min fatigue life (fairlead)"),
        ("0.74", "Max annual damage / line"),
        ("Line 3", "Governing line"),
        ("25 yr", "Design basis"),
    ],
    method="T-N curve screening (DNV-OS-E301), spectral fatigue across the scatter diagram",
    basis="Illustrative result from the mooring_fatigue workflow (parametric pilot, dm#796); "
    "replace with a live run when wired.",
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="reports/hse/mooring-fatigue-grounded-card.html")
    ap.add_argument(
        "--illustrative",
        action="store_true",
        help="Use the illustrative panel instead of a live digitalmodel run.",
    )
    a = ap.parse_args(argv)

    # Engineering panel: a LIVE digitalmodel mooring_fatigue run (#768), falling back to
    # the illustrative summary only if forced or if digitalmodel is unavailable — so the
    # card never labels an illustrative result as live.
    if a.illustrative:
        analysis = ANALYSIS
        print("  engineering  : illustrative (--illustrative)")
    else:
        try:
            analysis = build_live_analysis()
            print("  engineering  : LIVE digitalmodel mooring_fatigue run")
        except Exception as exc:  # noqa: BLE001 — degrade gracefully, never fake "live"
            analysis = ANALYSIS
            print(f"  engineering  : live run unavailable ({exc}); using illustrative")

    # ground_and_log: produce the grounding AND record the request in the demand
    # signal (#491), so this live demo path feeds the coverage-gap rollup.
    g = ground_and_log("mooring_fatigue")
    generated_on = dt.date.today().isoformat()
    html_doc = render_html(g.to_dict(), analysis, generated_on)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")

    counts = g.source_counts
    print(f"wrote {out} ({len(html_doc):,} bytes)")
    print(f"  failure mode : {g.failure_mode}")
    print(f"  latest       : {[i.date for i in g.latest]}")
    print(f"  most severe  : {[(i.date, i.severity) for i in g.most_severe]}")
    print(f"  sources      : {counts}")
    print(f"  vintage      : {g.vintage_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
