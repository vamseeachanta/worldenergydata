# Field Development Playbook

An **evolving playbook** for offshore field development: take a set of field
parameters and produce a ranked concept shortlist plus schematics. Epic
[#567](https://github.com/vamseeachanta/worldenergydata/issues/567).

> **Offshore-first.** The methodology and engine target offshore fields
> (host/tieback concept selection, subsea architecture). Onshore comes later.

## Design spine

**The LLM reasons and specifies; deterministic code lays out and draws.** A
subsea field schematic is a *graph-drawing problem*, not a generative-geometry
problem. The pipeline is:

```
field parameters → FieldConcept (frozen schema)
   → recommendation engine        → ranked, scored concept shortlist
   → concept_to_graph (GraphSpec)  → layout-free node/edge IR
   → renderers                     → block diagram (logical) + plan-view (to-scale)
```

The only place an LLM enters (Phase 2, #577) is loose-brief → concept JSON, and
its output is re-validated against the schema + engineering sanity gate before
anything renders.

## Code

`src/worldenergydata/field_development/` — see the module docstrings.

| Capability | Module | Issue |
|---|---|---|
| Concept contract + validation | `models.py`, `sanity.py`, `schema/` | #568 |
| Recommendation engine | `recommendation.py` | #570 |
| Concept → graph spec | `graph.py` | #571 |
| Plan-view layout renderer | `layout.py` | #573 |
| Block-diagram renderer | `block.py` | #572 |

Field reference: [`field_development/data_dictionary.md`](../../../src/worldenergydata/field_development/data_dictionary.md).

## Reference briefing

[`concept-selection-and-ai-cad-briefing.md`](concept-selection-and-ai-cad-briefing.md)
— the methodology + AI/CAD state-of-the-art that seeds the engine: FEL/stage-gate
workflow, host-concept depth envelopes, subsea building blocks, tieback economics
& flow assurance, parameters→concept heuristics, and the deterministic
diagram-as-code pipeline. ~70 sourced references + an uncertainty-flags section.

> Thresholds, depth bands, and scoring weights in the engine are **config, not
> magic numbers**, and trace back to this briefing's §A3–A6.

## Data sources & guardrail

- **Public:** BSEE asset data (`data/modules/bsee/`), vessel fleet
  (`vessel_fleet/`), subsea hardware catalogs (`subsea/`), public FDP costs
  (`cost/`).
- **Private (off-repo):** the SubseaIQ-derived field/host database is used only
  as a private reference layer (calibration, #569). **Raw SubseaIQ records are
  never published into this public repo** — public outputs use BSEE +
  aggregated/derived parameters only.

## Roadmap

See epic #567. Phase 1 (deterministic spine): #568, #570, #571, #572, #573 done;
#574 (subsea symbol library), #575 (wire economics/vessel/jumper data), #569
(private SubseaIQ loader) in progress. Phase 2 (flagged): #577 LLM
concept-completion, #578 DEXPI interop, #579 layout optimization, #580
equipment-3D.
