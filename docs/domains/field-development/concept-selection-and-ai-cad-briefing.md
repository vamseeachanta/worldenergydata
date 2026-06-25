# Offshore Field Development Concept Selection + AI/Generative CAD for Subsea Schematics — Engineering Briefing (2025–2026)

*Purpose: seed a GitHub epic for a software tool that takes field-development parameters and emits (a) a recommended concept and (b) schematics/field-layout drawings. Numbers are sourced; uncertain figures are flagged.*

---

# TOPIC A — Offshore Field Development Concept Selection Methodology & Playbook Structure

## A1. The FEL / stage-gate workflow

Operators run field development through a **stage-gated Front-End Loading (FEL)** process. Each phase ends in a **Decision Gate (DG)** where a deliverables package supports a go/no-go funding decision. The FEL stages map cleanly onto **AACE cost-estimate classes** — this mapping is the single most useful backbone for the tool, because it tells you *what fidelity of answer is expected at each stage*.

| Phase (common names) | AACE class | Cost accuracy | Project def. | Core question | Key deliverables |
|---|---|---|---|---|---|
| **FEL-0 / Appraise / Identify** | Class 5 | -50% / +100% | 0–2% | "Is there something worth developing?" | Appraisal wells → reservoir size, PVT/fluid, well deliverability; play/prospect framing |
| **FEL-1 / Concept Select (Assess)** | Class 4 | -30% / +50% | 1–15% | "Which concept gives the most value?" | Screen multiple concepts; **Basis of Design / DBM**; shortlist → single selected concept at **DG2** |
| **FEL-2/3 / Define = FEED** | Class 3 (often pushed to Class 2) | -20% / +30% (Class 3); -15%/+20% (Class 2) | 10–75% | "Freeze the design; is it sanctionable?" | FEED package: PFDs, P&IDs, equipment specs, execution plan, firm CAPEX/OPEX → **FID at DG3** |
| **Execute** | Class 2 → 1 | down to -10%/+15% | 50–100% | "Build it." | Detailed design, EPC, fabrication, install, commission |

- **FID (Final Investment Decision)** is the gate at the end of FEED — formal capital commitment.
- **Concept Select vs FEED is the distinction the tool lives in**: Concept Select compares *many* options at low fidelity (Class 4/5) to pick one; FEED takes *that one* to a frozen, sanctionable design. **The tool targets Concept Select** — fast, parametric, many-options, "good enough to rank," explicitly NOT FEED-grade.
- Typical durations: FEED ~4–8 months for a ~$100M unit; 12–18 months for $1B+ megaprojects.

> *Sources: SPE/JPT FDP series; AACE 18R-97; Offshore Magazine "Structured concept selection"; constructionfront FEED guide. (See References.)*

## A2. Concept selection drivers

**Primary drivers (in rough order of leverage):**

1. **Water depth** — the dominant host-concept gate. Practical bands:
   - **Shallow** ≲ ~400–450 m: fixed jacket feasible (deepest fixed jacket = Bullwinkle ~412 m; compliant tower Petronius ~535 m extends fixed-like reach).
   - **Deep** ~450–1500 m: floating hosts + subsea.
   - **Ultra-deep** > ~1500 m: floating + subsea only; dry-tree limited to Spar (TLP tendon cost limit ~1500 m, extended to Big Foot ETLP 1,580 m).
   - *Note the definitional split: BOEM/regulatory "deepwater" often = >305 m (1,000 ft); facilities engineers often use ~150 m as the shelf/deepwater break. Flag both in the tool.*
2. **Reservoir size / recoverable reserves** — sets whether a dedicated host is justified vs. a tieback. Small/marginal → tieback; large → standalone host.
3. **Fluid type & properties** — oil vs gas vs gas-condensate; **GOR**, **API/viscosity**, wax/asphaltene content, H2S/CO2 (sour), wax appearance temp. Drives flow assurance, processing, export route (pipeline vs FPSO storage vs FLNG vs reinjection).
4. **Distance to existing infrastructure** — the tieback-vs-standalone pivot.
5. **Metocean / environment** — region-specific (see below); drives hull type, mooring, riser, disconnectability.
6. **Geography / regulatory regime** — local content, emissions/flaring rules, jurisdiction.

**Regional concept signatures (real patterns):**

| Region | Environment | Typical concept signature |
|---|---|---|
| **Gulf of Mexico** | Hurricanes (sporadic, severe); deep/ultra-deep | Dry-tree Spar/TLP for big stacked reservoirs (Perdido, Big Foot); lean standardized **semisub FPS** now dominant (Vito, King's Quay, Whale, Anchor, Appomattox); **FPSO** only recently (Stones/Turritella, >2,900 m, **disconnectable turret** for hurricanes) |
| **North Sea** | Harsh, persistent (no hurricanes); mature infrastructure | Tiebacks to existing hosts (Penguins 65 km); **NUI/unmanned** wellhead platforms; FPSOs built for extreme persistent weather; Aasta Hansteen Spar (~1,300 m, deepest on NCS) |
| **West Africa** | Benign, deep | **FPSO**-centric (turret/spread moored); subsea clusters; e.g. Pazflor subsea separation |
| **Brazil pre-salt** | Benign-moderate, ultra-deep, CO2-rich | Large **FPSOs** (Búzios, Tupi; 150–225 kbopd units); subsea boosting; CO2 reinjection |
| **Australia NWS / Barents** | Remote gas, long offsets | **Subsea-to-shore** (Snøhvit 143 km, no platform, remote control from shore, CO2 reinjection); FLNG (Prelude) |

## A3. Host / facility concept options — water-depth & payload envelopes

| Concept | Practical water depth | Topsides payload | Dry/wet trees | When chosen | Anchor example |
|---|---|---|---|---|---|
| **Fixed steel jacket** | up to ~400–450 m (econ. ~400 m) | wide, high | Dry | Shallow, benign, high well count, storage via pipeline | Bullwinkle 412 m |
| **Compliant tower** | ~450–900 m | moderate-high | Dry | Niche intermediate depth; flexes with waves | Petronius ~535 m |
| **TLP** | ~300–1,500 m (ETLP to 1,580 m) | moderate (payload ↓ as tendon wt ↑ with depth) | **Dry** (direct vertical access) | Stacked reservoir from one drill center; intervention-heavy | Big Foot ETLP 1,580 m; Magnolia 1,432 m |
| **Spar** | ~600–2,450 m | ~3,000–~15,000 t wellbay | **Dry** (deep draft → low riser motion) | Ultra-deep dry-tree; only proven dry-tree hull >1,500 m | Perdido ~2,450 m; Aasta Hansteen (gas) ~1,300 m |
| **Semisubmersible FPS** | ~600–2,600 m | wide "universal host" bandwidth | **Wet** (subsea) | Deep GoM workhorse; phased, flexible well placement; no storage | Vito/King's Quay ~1,200 m → Whale ~2,600 m; 80–175 kboepd |
| **FPSO** | ~few hundred m to >2,900 m | very high; **has storage** | Wet | No export pipeline / remote; large reserves; benign-to-managed metocean (disconnectable turret for hurricanes) | Stones/Turritella >2,900 m (world's deepest) |
| **Subsea tieback to existing host** | up to host depth; tieback length-limited | n/a (uses host) | Wet | Marginal reserves near infrastructure; lowest CAPEX | Penguins 65 km; Mensa 109 km |
| **Subsea-to-shore (all-subsea)** | up to ~1,000s m | n/a | Wet | Remote gas, no host viable | Snøhvit 143 km |
| **NUI / minimal/unmanned platform** | shallow | minimal (wellheads only) | Dry | Marginal shallow fields; remote ops; monopile/MFP | UK North Sea NUIs; 2025 NUI buoy pilot |

**Dry vs wet tree decision (a sub-engine in itself):**
- **Dry tree** (TLP/Spar): direct vertical well access → cheaper light/heavy intervention, higher recovery, lower OPEX; needs **compact/stacked reservoir reachable from one drill center**. Limits hull to TLP/Spar.
- **Wet tree** (subsea, on semisub/FPSO host): **flexible well placement** over a large/distributed reservoir area; intervention needs a MODU (costly); enables tiebacks and phasing.

## A4. Subsea architecture building blocks

- **Subsea trees (wet trees):** Vertical XT (VXT — tubing hanger in wellhead, tree retrievable independently; common, 5–15 ksi) vs Horizontal XT (HXT — valves on side, tubing hanger in tree; favored for high intervention / high well count). Each has SCM (subsea control module) fed by umbilical.
- **Manifolds:** flow routers between trees and flowlines. **Template manifold** (drill-through, trees docked side-by-side) vs **cluster manifold** (standalone, ~4–8 wells around it). Reduces riser/flowline count.
- **Templates:** structural frames housing/guiding multiple wells.
- **Jumpers vs spools:** **jumper** = short connector standing vertically (U/M/Z-shape); **spool** = lies horizontally on seabed. Connect tree↔manifold, manifold↔PLET, etc. Rigid (steel) or flexible. Require **subsea metrology** for fit; connectors tolerate ~±3° misalignment.
- **Flowlines:** **rigid** (carbon steel, reeled/S-lay/J-lay) vs **flexible** (bonded layers, easier install/routing) vs **pipe-in-pipe (PiP)** (best insulation, U-value <~0.7 W/m²K). Trend: ~90% of installs now **wet-insulated rigid** (polyurethane/polypropylene/syntactic); PiP/active heating reserved for stringent thermal cases.
- **Risers (map to host):**
   - **SCR** (steel catenary): cheapest, deepest reach; fatigue concentration at touchdown point; good with low-motion hosts (Spar/TLP).
   - **Steel Lazy Wave Riser (SLWR):** buoyancy arch decouples vessel motion — used on high-motion FPSOs/semisubs (e.g. Stones).
   - **Flexible riser:** handles motion well; collapse-pressure limited / expensive in deep water.
   - **Hybrid riser tower / SLOR / OSCR:** steel risers on a buoyancy tank + flexible jumper to floater; field-proven GoM/Brazil/WAfrica ~1,500–8,600 ft.
   - **TTR** (top-tensioned): dry-tree risers on TLP/Spar.
- **Umbilicals:** carry hydraulics, chemical injection, power, electrical/fiber signal. Steel-tube (STU), thermoplastic (TPU), electro-hydraulic (EHU), power umbilicals, **IPB (integrated production bundle)** combining flow + power + signal. Static (seabed) or dynamic (riser). Trend toward **all-electric controls** (reduces hydraulic umbilical demand).
- **PLET / PLEM:** Pipeline End Termination (valves/hub terminating a rigid line for a jumper/spool tie-in) / Pipeline End Manifold (simpler manifold for 1–2 trees).
- **Topology:**
   - **Satellite wells** — individual flowlines per well; few wells / individual tiebacks; max flexibility.
   - **Cluster** — multiple drill centers each with a cluster manifold; cost-saving for many wells.
   - **Daisy chain** — wells connected in series.
   - **Pigging loop** — dual flowlines joined end-to-end → round-trip pig circuit (standard for tiebacks needing pigging).
- **Artificial lift / boosting:**
   - **Gas lift** — downhole, flowline, or **riser-base** (suppresses severe slugging at the riser base; reduces hydrostatic head).
   - **Subsea multiphase pumps** (helico-axial / twin-screw) — boost low-energy / long-offset wells; OneSubsea >100 pumps, records to ~1,700 m & ~29 km step-out.
   - **Subsea separation** — Tordis (world-first SSBI, North Sea, 200 m; +35 MMbbl, life +15–17 yr; recovery ~49→55%); Pazflor (gas/liquid sep, Angola); BC-10 caisson ESPs ~1,500 hp @ ~1,780 m.
   - **Subsea compression** — Åsgard (world-first full subsea gas compression, 2015, 2×~11.5 MW trains; secures ~306 MMboe; depth cited 270 *vs* 300 m — **flag**); Gullfaks South (world-first **wet-gas** compression, 2×5 MW; Brent recovery ~62→74%).

## A5. Tieback economics & limits

**Distance records / bands:**
- Typical multiphase oil tiebacks: ~5–50 km.
- Long gas tiebacks: 10 km to ~200 km.
- **Mensa** (GoM gas) ~109 km; **Penguins** (UK) 65 km PiP; **Snøhvit** (subsea-to-shore) 143 km; **Petrel** (Australia, planned) ~285 km.
- OneSubsea markets tieback solutions to ~150 km (with boosting/compression).
- Research/simulation suggests "pseudo dry gas" / in-line liquids removal could push gas tiebacks to ~200–380 km.

**Flow assurance constraints (the real limiters):**
- **Hydrates** — form at cold (4–15°C) / high-pressure (50–200 bar) conditions; managed by **MEG** (gas systems, recoverable) / **methanol** (oil), **LDHI** (low-dosage, lower OPEX), insulation, and active heating.
- **Wax / asphaltene** deposition; **slugging** (terrain & severe/riser-base slugging).
- **Cooldown / no-touch time** — must keep fluid above hydrate/wax temp during shutdown long enough to intervene; sets insulation U-value and heating need.
- **Heating:** **DEH** (direct electrical heating — current through pipe steel; >40 installs, lines to ~43 km, ~1,000 m) and **ETH-PiP** (electrically trace-heated pipe-in-pipe).
- **Power/cable limits:** Ferranti effect limits high-power AC step-out cables to ~40–50 km (drives boosting architecture choices).
- A single blockage can shut in production for weeks, costing $50–200M — why flow assurance gates tieback length.

**When standalone host beats tieback:**
- Reserves large enough to justify dedicated facility CAPEX; OR
- Distance/flow-assurance make tieback infeasible or recovery-limiting (host processing constraints reduce subsea recovery); OR
- No host with spare capacity within reach; OR
- Nearfield exploration upside that a host would unlock.
- Rule-of-thumb cited: umbilical/tieback economics deteriorate sharply beyond ~20 miles (~32 km) for some cases; standalone or NUI buoy can beat a 20-mile tieback. Cost scaling: **jacket cost rises steeply with depth; subsea satellite cost rises with well count** — the crossover defines the choice.

## A6. Parameters → concept engine: inputs & decision heuristics

**Recommended input parameter set (the tool's `field_concept` contract):**

*Reservoir/fluid:* recoverable reserves (MMbbl / Bcf), fluid type (oil/gas/condensate), API gravity, GOR, viscosity, WAT (wax), H2S/CO2 (sour), reservoir pressure/temp (HPHT flag), drive mechanism, areal distribution (compact-stacked vs spread).
*Production:* plateau rate (bopd / MMscfd), per-well rate, well count, water/gas injection needs, field life, recovery profile.
*Location/physical:* water depth (m), distance to nearest host (km), host spare capacity, distance to shore/export, seabed terrain.
*Environment/regulatory:* metocean regime (benign / harsh-persistent / hurricane-cyclone), region/jurisdiction, flaring/emissions rules, local content.
*Commercial:* oil/gas price deck, discount rate, fiscal terms.

**Decision heuristics (first-pass rules — deterministic, then optionally MCDA-weighted):**

1. **Host vs tieback:** IF distance-to-host < ~30–60 km AND host has spare capacity AND reserves are small/marginal AND flow-assurance OK → **tieback**. ELSE → **standalone**.
2. **Standalone host by depth:**
   - depth < ~400 m → **fixed jacket** (NUI/MFP if marginal & shallow).
   - ~400–900 m → compliant tower (rare) / TLP / semisub.
   - ~900–1,500 m → **TLP** (if dry-tree wanted) / **semisub FPS** (wet tree) / **Spar**.
   - > ~1,500 m → **Spar** (dry tree) or **semisub/FPSO** (wet tree, subsea).
3. **Dry vs wet tree:** compact/stacked reservoir reachable from one drill center + intervention-heavy → **dry tree** (TLP/Spar). Distributed reservoir / phased / flexible placement → **wet tree** (subsea).
4. **Storage/export:** no export pipeline feasible OR remote → **FPSO** (storage) or **FLNG** (stranded gas). Pipeline available → fixed/floating host + export line. Remote gas, no host → **subsea-to-shore**.
5. **Boosting/processing trigger:** long offset / low reservoir energy / tail-end → multiphase pump; gas with liquids over long offset → wet-gas/subsea compression; high water cut → subsea separation.
6. **Topology:** few wells → satellite; many wells/multiple drill centers → cluster manifolds; tieback needing pigging → pigging loop (dual flowline).
7. **Flow assurance overlay:** compute hydrate/wax margin & cooldown vs distance → choose insulation (wet-insul / PiP) and/or heating (DEH/ETH-PiP) and inhibitor (MEG/methanol/LDHI); flag tiebacks that exceed feasible length.

**Methodology note:** real concept selection ranks the shortlist via **multi-criteria decision analysis** (AHP / weighted scoring / SAW) across CAPEX, OPEX, schedule, recovery, flexibility, risk, ESG, then by **life-cycle cost / NPV**. The engine should produce a *ranked, scored* shortlist, not a single answer — matching how operators actually gate.

**Prior art / competitive tools (do not reinvent — interoperate/differentiate):** **SFACE** (sface.no — early-phase subsea field-architecture modeling & comparison: satellite/cluster/template/daisy-chain/loop); **OneSubsea "Subsea Concept Selection"** service; flow-assurance standards **OLGA** (transient) / **PIPESIM** (steady-state).

---

# TOPIC B — AI / Generative CAD for Subsea & Field-Layout Schematics

## B1. The core framing (most important point)

Two different problems get conflated under "AI CAD." Treat them separately:

| Problem | Meaning | Maturity for *subsea schematics* |
|---|---|---|
| **3D solid geometry generation** (Text-to-CAD: Zoo, Autodesk neural CAD, DeepCAD lineage) | "Make me a 3D part / B-rep / STEP" | **Wrong tool for schematics.** Useful only for *equipment 3D models*. Experimental. |
| **Diagram/schematic generation** (block diagrams, field layouts, P&IDs) | "Arrange labeled nodes + connections into a readable 2D drawing" | **Right tool — and it's a solved, deterministic problem** via diagram-as-code + auto-layout. The LLM writes the *spec*, not the pixels. |

**Headline:** A subsea field schematic (host → manifold → trees → flowlines/umbilicals + a plan-view layout) is a **graph-drawing problem, not a generative-geometry problem.** The reliable architecture: **schema-validated concept JSON → deterministic layout engine → diagram-as-code/SVG**, with the LLM confined to (a) concept reasoning and (b) emitting a *validated diagram spec*. Anything claiming an LLM will "draw the schematic" end-to-end is hype.

## B2. State of the art — proven vs hype

- **Text-to-3D-CAD — experimental, not for diagrams:**
   - **Zoo.dev / Text-to-CAD** (formerly KittyCAD): most mature commercial; REST `POST /ai/text-to-cad/{format}` → STEP + **KCL** (their parametric language); "Zookeeper" conversational agent. Their own docs label ML endpoints *experimental*. Good for simple single parts; not assemblies, not diagrams.
   - **Autodesk neural CAD / Autodesk Assistant** (AU 2025): text→editable geometry, "Text to Command." Explicitly *in development / not a product spec* — roadmap, not shippable API.
   - **Autodesk generative design** = topology optimization (single load-bearing part). Mature but **irrelevant to schematics**.
- **CAD-LLM research (active, not production):** converging on **code-based generation** (LLM emits parametric code, then you validate deterministically). DeepCAD dataset; **Text2CAD** (NeurIPS 2024); **Text-to-CadQuery** (2025, ~69% exact-match — i.e. ~1 in 3 wrong → needs a validation gate); CAD-Coder, cadrille, NURBGen, Seek-CAD. *The technique to borrow — "LLM emits code, code is validated" — applied to diagram-as-code, not 3D.*
- **AI P&ID tools = digitization (reading), NOT generation:** SymphonyAI IRIS, AWS P&ID Digitization (Bedrock), Acuvate DiagramIQ, iDrawings. They read existing drawings into structured data. **The "generate from concept" gap is exactly what your tool fills.** **DEXPI / pyDEXPI** = a standards-based machine-readable P&ID data model — adopt as your *target graph model*.
- **Subsea-specific layout research = classical optimization, not LLM:** "A framework for early-stage automated layout design of subsea production systems" (Ocean Engineering 2024) — drill-center clustering, manifold positioning, host positioning, flowline design via ML clustering + geometric optimization. This is the best-matching prior art for an *optional* layout-optimization module (keep out of v1).

## B3. Programmatic approaches

- **Parametric CAD in Python (equipment 3D only):** **CadQuery** (OCCT, headless, STEP export, the research generation target — best pick) > **build123d** (cleaner Pythonic API) > **OpenSCAD** (weaker kernel, own DSL — avoid for interchange).
- **Diagram-as-code (THE core tech — mature, deterministic, open source):**
   - **D2** (Terrastruct) — modern DSL, nested containers, **pluggable layout (dagre/ELK/TALA)**, headless SVG/PNG/PDF — *strong pick for block diagrams.*
   - **`diagrams` (mingrammer)** — pure-Python "diagram as code" on Graphviz; supports **custom node images** — *strong pick if you want Python-native + custom subsea icons.*
   - **Graphviz/DOT** — bedrock Sugiyama layout, max control, ugly defaults.
   - **Mermaid** — ubiquitous but weak on dense cross-edges, no engineering icons.
   - **PlantUML** — UML-centric, has ELK mode; heavier (Java).
   - **Direct LLM SVG** — avoid for production (hallucinated coordinates, non-reproducible).
- **Auto-layout engines (deterministic core):** **ELK (Eclipse Layout Kernel / elk.js)** — strongest layered/compound layout with ports; standardize on this for block diagrams. **dagre** (simple), **Graphviz dot** (reference). *None apply to plan-view layout — that's coordinate geometry.*
- **Symbology:** **ANSI/ISA-5.1-2024** governs instrumentation symbols (not free). Open SVG libs (Wikimedia P&ID category, CC0 gists) exist but are fragmented. **Subsea symbols (XT, manifold, PLET/PLEM, jumper, umbilical, FPSO/TLP/Spar host) are NOT in standard P&ID libraries → build a small custom SVG set** (bounded, one-time deliverable).

## B4. Recommended pipeline (buildable)

**Principle: LLM reasons and specifies; deterministic code lays out and draws. The LLM never emits pixels or coordinates.**

```
STAGE 0  field_concept.json  (JSON Schema — the frozen contract)
            {water_depth, host_type, well_count, tieback_distance_km,
             equipment[], flowlines[], umbilicals[], topology, fluid...}
   │
   ▼  STAGE 1 (optional, gated)  LLM concept reasoning
            loose brief → fills gaps / proposes concept & equipment list
            OUTPUT must re-validate against Stage-0 schema  ← only place
            hallucination enters; gate hard (schema + sanity checks)
   │
   ▼  STAGE 2  Diagram spec (graph model)
            deterministic rules: concept JSON → nodes[{id,type,label,symbol}]
            + edges[{from,to,kind}]; align to DEXPI-like model
   │
   ├─► STAGE 3a BLOCK DIAGRAM: graph spec → D2/ELK or mingrammer `diagrams`
   │        → auto-layout → SVG (+ custom subsea node icons)
   │
   └─► STAGE 3b FIELD LAYOUT (plan view): NOT auto-layout — deterministic
            geometry (manifold at origin, wells at bearing/offset, host at
            tieback distance) → Jinja2/svgwrite SVG + north arrow + scale bar
   │
   ▼  Reproducible SVG (+ PNG/PDF). Same input → same output.
```

**Why the split:** ELK/dagre give reproducible, collision-free *block* diagrams from a spec; the *field layout* uses real coordinates from the concept (pure trig). Both deterministic and testable; the LLM's surface is bounded and schema-gated.

**Pitfalls (state in the epic):** (1) LLMs hallucinate coordinates → never let them emit SVG/positions; (2) no subsea symbol library exists → build custom SVG set; (3) reproducibility → pin layout engine+version, keep LLM out of layout; (4) freeze `field_concept.json` schema → everything downstream deterministic; (5) every LLM output passes schema + engineering sanity gate (well_count == tree count, tieback_distance > 0, depth within host envelope, etc.) before rendering.

## B5. Discrete buildable features (epic seeds)

**Build first (proven / low-risk):**
1. `field_concept.json` JSON Schema + validator (the contract).
2. Deterministic concept-JSON → graph-spec mapper (rules-based).
3. Block-diagram renderer via **D2+ELK** or **mingrammer `diagrams`** → SVG.
4. Plan-view field-layout renderer (deterministic geometry + Jinja2/svgwrite SVG, north arrow, scale bar, tieback distance).
5. **Custom subsea SVG symbol library** (XT, manifold, PLET/PLEM, jumper, umbilical, FPSO/TLP/Spar/semisub/jacket host).
6. PNG/PDF export (headless render).
7. **Concept recommendation engine** (Topic A heuristics → ranked scored shortlist) feeding the concept JSON.

**Build later (behind a flag / experimental):**
8. LLM concept-completion (loose brief → validated concept JSON), schema+sanity gated.
9. DEXPI/pyDEXPI-aligned graph model for P&ID-tool interoperability.
10. Layout-*optimization* module (manifold/well positioning) per Ocean Engineering 2024 methods.
11. Optional equipment-3D via CadQuery/build123d (or Zoo API) — separate from schematics.

**Avoid / dismiss for schematics:** 3D Text-to-CAD for field diagrams; direct LLM SVG in production; topology optimization.

## B6. Advanced / later-phase capabilities (features 8–11) — expanded

*These are the "behind a flag / experimental" items from B5, consolidated here with the supporting research from B2/B3 so they can each seed a later-phase child issue rather than living as one-liners.*

### Feature 8 — LLM concept-completion (gated)
- **Pattern:** loose natural-language brief ("32 MMbbl oil, 1,400 m, 18 km from an FPSO with spare capacity") → LLM fills gaps / proposes a concept + equipment list → output **re-validated against the Stage-0 `field_concept.json` schema + an engineering sanity gate** before anything renders.
- **Borrowed technique:** the CAD-LLM research consensus (Text2CAD, Text-to-CadQuery) is "LLM emits a *structured artifact*, deterministic code *validates* it." Text-to-CadQuery reports ~69% exact-match (≈1 in 3 wrong) — so the validation gate is **mandatory, not optional**.
- **Provider:** Claude (`claude-opus-4-8`) for the reasoning step, constrained via tool-use / structured output to force schema conformance.
- **Risk surface:** this is the *only* place hallucination enters the pipeline; B1–B4 keep everything downstream deterministic, so the gate is the whole safety story.

### Feature 9 — DEXPI / pyDEXPI-aligned graph model (interoperability)
- **What:** DEXPI (Data Exchange in the Process Industry; ISO 15926-rooted) is a machine-readable P&ID data model; **pyDEXPI** (arXiv 2502.18928) is a Python implementation.
- **Why:** aligning the Stage-2 graph spec to a DEXPI-like model lets the tool's schematics **interoperate with commercial P&ID tooling** (SymphonyAI IRIS, AWS Bedrock P&ID digitization, Acuvate DiagramIQ) — import/export instead of a bespoke lock-in format.
- **Scope caveat:** subsea hardware (XT, manifold, PLET/PLEM, jumper, umbilical, floating hosts) is **not native** to DEXPI's process-plant symbol set → this is a *mapping/extension* exercise layered over the existing graph model, **not a rewrite**.

### Feature 10 — Layout-*optimization* module
- **Prior art:** "A framework for early-stage automated layout design of subsea production systems," *Ocean Engineering* 2024 (S0029801824005122) — drill-center clustering, manifold positioning, host positioning, and flowline routing via ML clustering + geometric optimization.
- **Distinct from Stage-3b:** 3b *draws* a plan-view layout from coordinates already in the concept (deterministic trig); feature 10 *computes the optimal* coordinates — where to place manifolds / drill centers / host to minimize flowline length / cost subject to constraints.
- **Sequencing:** keep out of v1. The deterministic renderer (3b) must exist and be trusted before adding an optimizer on top of it.

### Feature 11 — Equipment-3D via CadQuery / Zoo (separate track)
- **Different problem from schematics:** produces 3D **solid models** (STEP / B-rep) of *individual* equipment (a tree, a manifold), not field diagrams. Do not conflate with the 2D pipeline.
- **Tooling:** **CadQuery** (OCCT-based, headless, STEP export, parametric Python) is the recommended pick; **build123d** the cleaner-API alternative; **Zoo.dev** text-to-CAD REST API the experimental commercial option (its own docs flag the ML endpoints as experimental, simple single parts only).
- **Natural use case here:** parametric 3D of the **catalog hardware already in `worldenergydata`'s `subsea` module** (the rigid-jumper and mooring-component specs) for visualization or downstream analysis — a track that reuses existing repo data and stays independent of the schematic generator.

---

# References

**Topic A — concept selection & subsea**
- Offshore Mag — Structured offshore field development concept selection: https://www.offshore-mag.com/production/article/16755079/structured-offshore-field-development-concept-selection-adds-real-value
- SPE/JPT — Field Development Options and Selection Strategies: https://jpt.spe.org/field-development-options-and-selection-strategies
- AACE 18R-97 cost estimate classification: https://www.somaprojectcontrols.com/resources/glossary/aace-18r-97/
- FEED study process/deliverables/cost: https://constructionfront.com/front-end-engineering-design/
- Front-end loading (Wikipedia): https://en.wikipedia.org/wiki/Front-end_loading
- Applicability ranges for offshore oil & gas production facilities (ScienceDirect): https://www.sciencedirect.com/science/article/abs/pii/S095183390500050X
- Assessing floating platform concepts for deepwater production: https://www.offshore-mag.com/field-development/article/16761414/assessing-floating-platform-concepts-for-deepwater-production
- Spar platforms overview (ScienceDirect): https://www.sciencedirect.com/topics/engineering/spar-platforms
- Compliant tower overview (ScienceDirect): https://www.sciencedirect.com/topics/engineering/compliant-tower
- Wet tree vs dry tree criteria: https://www.oedigital.com/news/452137-wet-tree-vs-dry-tree-criteria
- Multiple factors drive wet/dry tree decisions (JPT): https://jpt.spe.org/multiple-factors-drive-decisions-toward-wet-or-dry-trees-deepwater-projects
- Semisubmersibles in the GoM: https://www.offshore-mag.com/regional-reports/us-gulf-of-mexico/article/14213384/semisubmersibles-setting-the-standard-in-the-gulf-of-mexico
- Stones/Turritella (deepest FPSO): https://www.offshore-mag.com/subsea/article/16754767/shell-takes-ultra-deepwater-to-record-depths-with-stones
- Perdido spar (deepest spar): https://en.wikipedia.org/wiki/Perdido_(oil_platform)
- Magnolia / Big Foot ETLP: https://en.wikipedia.org/wiki/Magnolia_(oil_platform)
- Aasta Hansteen spar (gas): https://www.equinor.com/energy/aasta-hansteen
- Disconnectable turret FPSO / GoM metocean: https://dynamic-positioning.com/proceedings/dp2004/environment_yetsko.pdf
- Brazil pre-salt FPSOs: https://brazilenergyinsight.com/2025/11/09/5-countries-with-the-most-fpsos-in-the-world-brazil-leads-with-46-fpsos-and-accelerates-pre-salt-development/
- Minimum facilities platform / NUI: https://www.offshore-mag.com/field-development/article/16761203/minimum-facilities-platform-provides-alternative-for-marginal-field-developments
- Monopile wellhead platforms (2H Offshore): https://2hoffshore.com/sectors/oil-and-gas/platforms/monopile-wellhead-platforms
- NUI / unmanned platforms trend: https://www.offshore-mag.com/field-development/article/14213949/industry-advancing-unmanned-platforms-remote-operations
- Subsea manifold / PLET / PLEM (ScienceDirect): https://www.sciencedirect.com/topics/engineering/subsea-manifold
- Subsea tree (vertical/horizontal) overview: https://www.sciencedirect.com/topics/engineering/subsea-tree
- Subsea Engineering Handbook (Bai & Bai): https://www.oreilly.com/library/view/subsea-engineering-handbook/9780123978042/
- Rigid jumper spools (eSubsea): https://www.esubsea.com/rigid-jumper-spools/
- SCR / flexible / hybrid risers: https://www.offshore-mag.com/deepwater/article/16759340/deepwater-risers-steel-catenary-flexible-risers-battle-for-technical-supremacy
- Steel catenary riser (Wikipedia): https://en.wikipedia.org/wiki/Steel_catenary_riser
- Flowline insulation rigid/flexible/PiP: https://www.offshore-mag.com/pipelines/article/16759115/pipeline-technology-pipeline-heat-loss-in-rigid-flexible-and-pipe-in-pipe-deepwater-transport
- Umbilical systems (OneSubsea): https://www.onesubsea.slb.com/products-and-services/subsea-field-development/subsea-umbilical-systems
- Integrated production umbilicals (IPB): https://www.onesubsea.slb.com/products-and-services/subsea-field-development/subsea-umbilical-systems/integrated-production-umbilicals
- Subsea gas lift / riser-base (GATE): https://www.gate.energy/the-brainery/artificial-lift-for-subsea-applications
- Subsea boosting (OneSubsea): https://www.onesubsea.slb.com/products-and-services/subsea-field-development/subsea-processing-systems/subsea-boosting-pumps
- Long subsea tiebacks (OneSubsea, to 150 km): https://www.onesubsea.slb.com/solutions-and-capabilities/long-subsea-tiebacks
- Åsgard subsea compression (OTC): https://onepetro.org/OTCONF/proceedings/25OTC/25OTC/D011S011R005/662740
- Statoil subsea compression to extend field life (JPT): https://jpt.spe.org/statoil-subsea-compression-systems-extend-field-life
- Tordis world-first subsea processing: https://www.offshore-mag.com/subsea/article/16760845/tordis-becomes-worlds-first-subsea-processing-installation
- Subsea processing overview (ScienceDirect): https://www.sciencedirect.com/topics/engineering/subsea-processing
- Subsea long-distance tiebacks — a look back: https://www.offshore-mag.com/subsea/article/16762892/subsea-long-distance-tiebacks-a-look-back
- 100-mile tiebacks technologies: https://www.offshore-mag.com/subsea/article/16757598/what-technologies-will-be-required-for-100-mile-tiebacks
- Penguins redevelopment (65 km): https://www.offshore-technology.com/projects/penguins-field-redevelopment-north-sea/
- Snøhvit subsea-to-shore (143 km): https://www.offshore-mag.com/subsea/article/16754525/snhvit-development-employs-subsea-to-beach-long-offset-control-system
- Flow assurance strategies for long tiebacks: https://www.offshore-mag.com/subsea/article/16755185/developing-flow-assurance-strategies-for-long-distance-tiebacks
- DEH direct electrical heating (SINTEF): https://blog.sintef.com/ocean/direct-electrical-heating-deh/
- Hydrate inhibitors (MEG/MeOH/LDHI): https://www.offshore-mag.com/pipelines/article/16755698/flow-assurance-hydrate-inhibitors-for-deepwater-flow-assurance
- Subsea tieback vs standalone economics: https://www.offshore-mag.com/subsea/article/16763319/solution-for-subsea-tiebacks-can-lower-reserves-hurdle-rate
- Subsea field architecture types (SFACE): https://sface.no/blogs/subsea-field-architecture/
- SFACE early-phase tool: https://sface.no/
- OneSubsea subsea concept selection: https://www.onesubsea.slb.com/products-and-services/subsea-field-development/integrated-field-development/subsea-concept-selection
- Framework for early-stage automated layout of subsea production systems (Ocean Engineering 2024): https://www.sciencedirect.com/science/article/abs/pii/S0029801824005122
- OLGA dynamic multiphase simulator (SLB): https://www.slb.com/products-and-services/delivering-digital-at-scale/software/olga
- MCDA for offshore concept selection (AHP/SAW): https://link.springer.com/article/10.1007/s41660-023-00376-1

**Topic B — AI / generative CAD & diagrams**
- Zoo ML for CAD Design API: https://zoo.dev/machine-learning-api
- Zoo Text-to-CAD FAQ (KCL, experimental): https://zoo.dev/docs/faq
- Text-to-CadQuery (Xie & Ju 2025): https://arxiv.org/html/2505.06507v1
- Text2CAD (NeurIPS 2024): https://sadilkhan.github.io/text2cad-project/
- Large Language Models for CAD: A Survey: https://arxiv.org/html/2505.08137v1
- Autodesk upcoming 3D generative AI foundation models: https://adsknews.autodesk.com/en/news/upcoming-3d-generative-ai-foundation-models/
- Autodesk generative design (topology optimization): https://www.autodesk.com/solutions/generative-design
- AI P&ID digitization (Acuvate DiagramIQ): https://acuvate.com/blog/intelligent-pid-digitization-solution/
- AWS P&ID digitization guidance: https://aws.amazon.com/solutions/guidance/piping-and-instrumentation-diagram-digitization-on-aws/
- pyDEXPI (DEXPI machine-readable P&ID model): https://arxiv.org/html/2502.18928v1
- CadQuery: https://github.com/cadquery/cadquery
- build123d vs CadQuery: https://www.oreateai.com/blog/build123d-vs-cadquery-navigating-the-future-of-python-cad-modeling/b9e17e3134422786a0ab67c0a6d1eeda
- diagrams (mingrammer) — Diagram as Code: https://diagrams.mingrammer.com/
- D2 (Terrastruct): https://github.com/terrastruct/d2
- Eclipse Layout Kernel (ELK): https://eclipse.dev/elk/
- Graphviz layouts: https://graphviz.org/docs/layouts/
- ANSI/ISA-5.1-2024 instrumentation symbols: https://blog.ansi.org/ansi/ansi-isa-5-1-2024-instrumentation-symbols/
- Wikimedia Commons P&ID symbols (SVG): https://commons.wikimedia.org/wiki/Category:P&ID_symbols

**Uncertainty flags (confirm against primary OTC/SPE papers before quoting):** Åsgard water depth (270 vs 300 m); wet-insulation "~90% of installs" share; flowline U-value bands; subsea pump RPM ranges and EUR-uplift %; Tordis recovery (49→55% vs +35 MMbbl framing); exact fixed-jacket economic depth (cited 400 m vs 1,500 ft elsewhere); "deepwater" definition (BOEM 305 m vs facilities ~150 m).
