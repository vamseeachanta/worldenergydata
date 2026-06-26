# Deepwater GoM — Field Development Plan Portfolio

Worked examples from the field-development playbook (epic #567): one standalone
HTML FDP per field plus an `index.html` comparison table. Open `index.html`.

Each plan composes the full pipeline — parameters → ranked concept shortlist →
subsea-architecture block diagram + to-scale plan-view layout → economics +
vessel feasibility + hardware picks — and shows the engine's recommendation
beside the concept actually built (the ✓/✗ "engine match" column on the index).

## Fields

10 deepwater/Lower-Tertiary Gulf of Mexico fields (Julia, Stones, Great White,
Chinook, Tobago, Cheyenne, Camden Hills, King, Coulomb, Aconcagua) spanning
FPSO, spar, semisub, TLP and subsea-tieback concepts.

## How it was generated (reproducible)

1. **Research** — a dynamic workflow (`field-dev-portfolio-research-batched`)
   fanned out batch agents that web-researched + skeptically verified each field
   (concept, host, operator, water depth, reserves, first oil, reservoir play)
   and wrote an engineering narrative. Output: `_research.json`. The research
   corrected several stale SubseaIQ facts — e.g. Chinook and Tobago are subsea
   **tiebacks** (to the BW Pioneer FPSO and the Perdido spar), not their hosts'
   types.
2. **Generate** — `scripts/field_development/build_fdp_portfolio.py _research.json`
   maps each profile to a `FieldConcept`, runs the playbook, and renders the
   per-field FDP HTML + index.

To regenerate after editing `_research.json`:

```
uv run python scripts/field_development/build_fdp_portfolio.py \
    reports/field_development/portfolio/_research.json
```

## Caveats

Concept-Select / FEL-1 fidelity — not sanctioned designs. Facts are
web-researched (sources in `_research.json`) but the ~2014 SubseaIQ baseline and
dated public records mean some figures are approximate. The engine's economics
are rough order-of-magnitude (generic FDAS assumptions), shown beside as-built
actuals to make the fidelity gap explicit.
