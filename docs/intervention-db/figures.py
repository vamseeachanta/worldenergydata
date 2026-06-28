# ABOUTME: Figure registry for the GoM intervention brief (plots + schematics).
# ABOUTME: build_all() -> {key: svg}; FIGURES carries placement + caption metadata.
"""Figure registry for the intervention brief.

Aggregates the seven data plots (``figures_plots``) and two concept
schematics (``figures_schematics``) into an ordered registry with placement
metadata (which brief section each figure anchors to), a one-line caption and
a source tag. ``build_all`` returns inline-SVG strings; ``write_standalone``
dumps reusable ``.svg`` files under ``figures/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import figures_plots as P
import figures_schematics as S

# Ordered registry. ``section`` is the brief <h2> heading text the figure is
# appended to (substring match), ``order`` disambiguates multiple figures in
# one section.
FIGURES = [
    {
        "key": "wells_by_band",
        "fn": P.fig_wells,
        "section": "Existing subsea wells by water-depth band",
        "order": 1,
        "caption": "Subsea wells and subsea-share invert with depth — the deepest "
        "serviceable band holds the most subsea wells (270) at 55.7% share.",
        "source": "well_inventory_by_band.yml (#583)",
    },
    {
        "key": "serviceability_xsection",
        "fn": S.fig_serviceability_schematic,
        "section": "Serviceability",
        "order": 1,
        "caption": "Cross-section of who can reach each depth: riserless RLWI "
        "monohull (live well) vs riser-based Helix semi / MODU (dead well); "
        "only ~3 dedicated units are GoM-resident.",
        "source": "well_inventory_by_band.yml (#583), serviceability_matrix.yml "
        "(#586), intervention_fleet_catalog.yml (#598)",
    },
    {
        "key": "fleet_by_class",
        "fn": P.fig_fleet,
        "section": "Intervention-asset fleet",
        "order": 1,
        "caption": "Deduped global roster by class (CONTEXT only, not GoM "
        "supply): 1,018 jackups vs only 5 heavy-intervention semis and 4 RLWI "
        "monohulls.",
        "source": "intervention_fleet_catalog.yml (#598/#599)",
    },
    {
        "key": "dayrate_bands",
        "fn": P.fig_dayrate,
        "section": "Intervention-asset fleet",
        "order": 2,
        "caption": "Indicative public day-rate bands; intervention semis and "
        "RLWI monohulls carry no public per-day figure.",
        "source": "intervention_fleet_catalog.yml (#596), intervention_economics.yml (#629)",
    },
    {
        "key": "planned_by_year",
        "fn": P.fig_planned,
        "section": "Planned / projected new subsea wells",
        "order": 1,
        "caption": "On-record FID floor of new subsea wells by first-oil year "
        "(7/32/6/3/10/6/8) — later infill phases are deliberately excluded.",
        "source": "planned_subsea_wells.yml (#587)",
    },
    {
        "key": "access_ratio",
        "fn": P.fig_access_ratio,
        "section": "Access gap",
        "order": 1,
        "caption": "Forward demand vs GoM-resident supply ratio: 1.6x / 3.1x / "
        "4.4x in the populated deepwater bands (>1.0x = access risk, NOT a "
        "measured crossover).",
        "source": "access_gap.yml (#638)",
    },
    {
        "key": "demand_supply",
        "fn": P.fig_demand_supply,
        "section": "Access gap",
        "order": 2,
        "caption": "Central forward demand rig-days/yr vs the fixed ~511 "
        "rig-days/yr the GoM-resident heavy fleet can provide.",
        "source": "access_gap.yml (#638)",
    },
    {
        "key": "exposure",
        "fn": P.fig_exposure,
        "section": "Access gap",
        "order": 3,
        "caption": "Central annual $ exposure by band: $375M / $731M / $1.0B "
        "(forward-looking planning indicator).",
        "source": "access_gap.yml (#638)",
    },
    {
        "key": "riser_concept",
        "fn": S.fig_riser_concept,
        "section": "Access gap",
        "order": 4,
        "caption": "The capability split behind the gap: light riserless "
        "(monohull, live well) vs heavy riser-based (MODU/Helix, dead well).",
        "source": "serviceability_matrix.yml (#586)",
    },
]


def build_all() -> dict[str, str]:
    """Return {key: inline-SVG string} for every registered figure."""
    return {f["key"]: f["fn"]() for f in FIGURES}


def write_standalone(outdir: Path | None = None) -> list[Path]:
    """Write each figure as a standalone reusable .svg file."""
    outdir = outdir or (Path(__file__).resolve().parent / "figures")
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    svgs = build_all()
    for key, content in svgs.items():
        p = outdir / f"{key}.svg"
        p.write_text(content, encoding="utf-8")
        written.append(p)
    return written


def main(argv: list[str]) -> int:
    paths = write_standalone()
    for p in paths:
        print(f"wrote {p} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
