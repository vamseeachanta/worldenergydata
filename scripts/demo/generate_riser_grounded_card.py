#!/usr/bin/env python3
# ABOUTME: Generates the riser-fatigue grounded card — real BSEE riser incidents + a live dm run (#771).
# ABOUTME: Second live arc of the engineering<->asset circle (#764), generalising the mooring card (#768).

"""Generate the riser-fatigue grounded card.

Pairs the live BSEE grounding for riser / flowline structural failure with a LIVE
digitalmodel riser_fatigue result, rendering one self-contained HTML card.

Usage::

    python scripts/demo/generate_riser_grounded_card.py \
        [--out reports/hse/riser-fatigue-grounded-card.html] [--illustrative]

The grounding numbers are 100% real public BSEE records; the engineering panel is a
live digitalmodel run unless ``--illustrative`` is set or digitalmodel is unavailable.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from _riser_live import build_live_analysis

from worldenergydata.hse.grounding_card import AnalysisSummary, render_html
from worldenergydata.hse.grounding_demand import ground_and_log

# Fallback (illustrative) panel — used only with --illustrative or if dm is unavailable.
ANALYSIS = AnalysisSummary(
    title="Riser Fatigue — SCR touchdown zone",
    headline="Illustrative riser fatigue screening — replace with a live run.",
    metrics=[
        ("— yr", "Min fatigue life"),
        ("—", "Wave damage"),
        ("—", "VIV damage"),
        ("25 yr", "Design basis"),
    ],
    method="T-N / S-N wave + VIV screening (DNV-RP-C203, DNV-OS-F201)",
    basis="Illustrative placeholder; replace with a live digitalmodel run.",
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="reports/hse/riser-fatigue-grounded-card.html")
    ap.add_argument(
        "--illustrative",
        action="store_true",
        help="Use the illustrative panel instead of a live digitalmodel run.",
    )
    a = ap.parse_args(argv)

    if a.illustrative:
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
