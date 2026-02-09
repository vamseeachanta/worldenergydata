---
title: "Hull Profile Library with Panel Mesh Generation and Analysis Chain"
description: "Define hull shapes as line profiles, generate panel meshes on demand, produce schematics, and link hull→size→diffraction→RAOs→accelerations in a queryable catalog"
version: "0.1.0"
module: hydrodynamics/hull_library
session:
  id: eager-petting-bonbon
  agent: claude-opus-4.6
  date: 2026-02-08
review:
  cross_review: complete
  iterations: 1
work_items: [WRK-106]
target_repo: digitalmodel
---

# Hull Profile Library with Panel Mesh Generation and Analysis Chain

## Context

digitalmodel has a mature diffraction analysis pipeline (AQWA, OrcaWave, BEMRosetta) that accepts panel meshes (`PanelMesh` dataclass) in GDF/DAT/STL formats and produces unified `DiffractionResults` with RAOs, added mass, and damping. However, there is **no way to define hull geometry from engineering curves** — all meshes must be imported from external CAD tools.

The acma-projects/_hulls/ directory contains reference data (aframax tanker with Rhino 3dm + 14K-row parametric mesh spreadsheet, semi-submersible RAO data for 3 vessels) that demonstrates the kind of hull data we want to systematize. This data requires legal scrubbing before reuse.

The user wants:
1. Hull shapes defined as **line profiles** (waterlines, sections, profiles) — the engineering source of truth
2. A **generator** that converts profiles to panel meshes on demand
3. **Schematics** (plan view, profile view, body plan) for every hull
4. A **catalog** linking hull shape → size → diffraction → RAOs → sea state response → accelerations

## Key Design Decisions

### Profiles Only (Not Meshes)

**Store hull profiles as the canonical definition. Generate panel meshes on demand.**

Rationale:
- Panel meshes are derivatives — different analyses need different mesh densities
- Storing both creates duplication and sync risk
- Profiles are the naval architecture "source of truth"
- Mesh generation is deterministic given profiles + parameters (panel count, density distribution)
- Generated meshes can be cached locally (gitignored) for performance

Exception: reference validation meshes for unit tests (small, committed).

### Seed Data: Extract Both (Scrubbed)

Extract and scrub all acma-projects hull data:
- Aframax tanker mesh → reverse-engineer into hull profile stations
- Semi RAO data (3 vessels) → generic validation datasets
- All vessel names, author metadata, and company references removed per legal-compliance.md

### Accelerations: Point-Specific On-Demand

User specifies an arbitrary (x, y, z) point on the vessel. The catalog transfers RAOs from COG to that point using rigid-body kinematics, then computes spectral accelerations. Covers crane tips, moonpools, helidecks, accommodation, etc.

## Architecture

```
Hull Profile (YAML)          ← Source of truth, committed
    │
    ├─→ Schematic Generator  → SVG/PNG plan + profile + body plan views
    │
    └─→ Panel Mesh Generator → PanelMesh (existing dataclass)
            │
            └─→ MeshPipeline → GDF/DAT → Solver → DiffractionResults
                                                        │
                                                        └─→ RAOSet → MotionResponse → Accelerations
```

### Integration Points (existing code)

| Component | File | Reuse |
|-----------|------|-------|
| `PanelMesh` | `digitalmodel/hydrodynamics/bemrosetta/models/mesh_models.py` | Output target for generator |
| `MeshPipeline` | `digitalmodel/hydrodynamics/diffraction/mesh_pipeline.py` | Format conversion downstream |
| `VesselGeometry` | `digitalmodel/hydrodynamics/diffraction/input_schemas.py` | Extend to accept profile refs |
| `VesselProperties` | `digitalmodel/hydrodynamics/models.py` | Hull catalog metadata |
| `DiffractionSpec` | `digitalmodel/hydrodynamics/diffraction/input_schemas.py` | Downstream consumer |
| `WaveSpectra` | `digitalmodel/hydrodynamics/wave_spectra.py` | Sea state → response spectrum |
| `CoefficientsInterpolator` | `digitalmodel/hydrodynamics/interpolator.py` | RAO interpolation for motion calc |
| `MeshQualityReport` | `digitalmodel/hydrodynamics/bemrosetta/models/mesh_models.py` | Validate generated meshes |

## Implementation Plan

### Phase 1: Hull Profile Schema

**New file**: `digitalmodel/src/digitalmodel/hydrodynamics/hull_library/profile_schema.py`

Define Pydantic models for hull geometry from naval architecture curves:

```python
class HullStation:
    """Single transverse section at a longitudinal position."""
    x_position: float           # meters from AP (aft perpendicular)
    waterline_offsets: list[tuple[float, float]]  # (z, y) pairs — half-breadth at each draft

class HullProfile:
    """Complete hull definition from line drawings."""
    name: str
    hull_type: HullType         # TANKER, SEMI_PONTOON, BARGE, SHIP, CUSTOM
    stations: list[HullStation] # Transverse sections from AP to FP
    # Key dimensions (derived or declared)
    length_bp: float            # Length between perpendiculars (m)
    beam: float                 # Moulded beam (m)
    draft: float                # Design draft (m)
    depth: float                # Moulded depth (m)
    # Optional curves
    deck_profile: list[tuple[float, float]] | None   # (x, z) keel-to-deck profile
    keel_profile: list[tuple[float, float]] | None   # (x, z) keel line
    # Metadata
    block_coefficient: float | None
    displacement: float | None  # tonnes
    source: str                 # provenance
```

**Data format**: YAML files in `data/hull_library/profiles/`

```yaml
# data/hull_library/profiles/generic_aframax.yaml
name: generic_aframax
hull_type: tanker
length_bp: 226.8
beam: 36.6
draft: 15.0
depth: 21.0
stations:
  - x_position: 0.0
    waterline_offsets: [[0.0, 0.0], [5.0, 8.2], [10.0, 14.5], [15.0, 18.3]]
  - x_position: 22.68
    waterline_offsets: [[0.0, 2.1], [5.0, 12.4], ...]
  # ... 10-20 stations typically sufficient
```

### Phase 2: Panel Mesh Generator

**New file**: `digitalmodel/src/digitalmodel/hydrodynamics/hull_library/mesh_generator.py`

```python
class MeshGeneratorConfig:
    target_panels: int = 1000       # Approximate panel count
    waterline_refinement: float = 2.0  # Finer panels near waterline
    symmetry: bool = True           # Use port/starboard symmetry
    mesh_below_waterline_only: bool = True  # Diffraction convention

class HullMeshGenerator:
    def generate(self, profile: HullProfile, config: MeshGeneratorConfig) -> PanelMesh:
        """Convert hull profile to panel mesh."""
        # 1. Interpolate between stations (cubic spline)
        # 2. Generate surface points on regular grid
        # 3. Panelise into quads (waterline-parallel + station-parallel)
        # 4. Apply density distribution (finer at waterline)
        # 5. Compute normals (outward-pointing, into fluid)
        # 6. Validate via MeshQualityReport
```

Algorithm:
1. **Cubic spline interpolation** between stations along hull length
2. **Section interpolation** — at each intermediate x-position, interpolate half-breadth offsets
3. **Surface grid** — create regular (u, v) parametric grid mapping to (x, y, z)
4. **Quad panelisation** — connect grid points into quadrilateral panels
5. **Density grading** — cluster panels near waterline (z=0) where hydrodynamic loads peak
6. **Symmetry** — generate starboard half only, set `symmetry_plane='y'`

Output: `PanelMesh` instance ready for `MeshPipeline.convert()` or direct solver use.

### Phase 3: Schematic Generator

**New file**: `digitalmodel/src/digitalmodel/hydrodynamics/hull_library/schematic_generator.py`

For every hull profile, generate three standard naval architecture views:

1. **Profile view** (side elevation) — keel line, deck line, waterlines
2. **Plan view** (waterplane) — waterline at design draft, deck outline
3. **Body plan** (transverse sections) — all stations overlaid, FP right / AP left

Output formats:
- **SVG** for documentation and web embedding
- **Plotly HTML** for interactive exploration (hover over station data)
- **PNG** for reports

Uses matplotlib or Plotly — no CAD dependencies.

### Phase 4: Hull Catalog and Analysis Chain

**New file**: `digitalmodel/src/digitalmodel/hydrodynamics/hull_library/catalog.py`

A registry that links the full analysis chain:

```python
class HullCatalogEntry:
    hull_id: str                          # e.g. "generic_aframax"
    profile: HullProfile                  # Source definition
    schematics: dict[str, Path]           # {profile_view: path, plan_view: path, body_plan: path}
    variations: list[HullVariation]       # Parametric size variations

class HullVariation:
    variation_id: str                     # e.g. "generic_aframax_deep_draft"
    scale_factors: dict                   # {length: 1.0, beam: 1.0, draft: 1.2}
    mesh_config: MeshGeneratorConfig
    diffraction_results: Path | None      # Path to DiffractionResults
    rao_set: Path | None                  # Path to RAO data
    motion_responses: dict[str, Path]     # {sea_state_id: response_path}

class MotionResponse:
    """Response for a hull variation in a specific sea state."""
    sea_state: SeaStateDefinition         # Hs, Tp, spectrum_type, heading
    response_spectra: dict[str, NDArray]  # {heave: S_response, pitch: S_response, ...}
    significant_values: dict[str, float]  # {heave_sig: 1.2, pitch_sig: 2.3, ...}
    accelerations: dict[str, dict]        # {cog: {vertical: 0.8, lateral: 0.3}, bow: {...}}

class HullCatalog:
    def list_hulls() -> list[str]
    def get_hull(hull_id: str) -> HullCatalogEntry
    def generate_mesh(hull_id: str, config: MeshGeneratorConfig) -> PanelMesh
    def get_raos(hull_id: str, variation_id: str) -> RAOSet
    def compute_motions(hull_id: str, variation_id: str, sea_state: SeaStateDefinition) -> MotionResponse
    def compute_accelerations(hull_id: str, variation_id: str, sea_state: SeaStateDefinition, point: tuple) -> dict
```

The `compute_motions` method chains: RAO × WaveSpectra → response spectrum → statistical values.

The `compute_accelerations` method implements **point-specific** calculations:
1. Transfer 6-DOF RAOs from COG to arbitrary point (x, y, z) via rigid-body kinematics
2. Convert displacement RAOs → acceleration RAOs (multiply by ω²)
3. Compute acceleration response spectrum: S_acc(ω) = |RAO_acc(ω)|² × S_wave(ω)
4. Integrate for significant acceleration: a_sig = 2 × √(m₀) where m₀ = ∫S_acc(ω)dω
5. Return vertical, lateral, longitudinal accelerations at the specified point

This covers any location: crane tips, moonpool, helideck, accommodation blocks, etc.

### Phase 5: Seed Data (acma-projects extraction)

**Prerequisite**: Legal scrubbing per `.claude/rules/legal-compliance.md`

Extractable from acma-projects/_hulls/:

| Source File | Usable Data | Scrubbing Required |
|---|---|---|
| Generic Tanker Mesh Parametric Scaling1.xlsx | Reverse-engineer station offsets from 14K mesh vertices | Remove author metadata, NEDA reference → "public tanker reference" |
| Example Aframax GA.pdf | Visual reference for schematic validation | Not committed — reference only |
| Typical Fairlead Locations.xlsx | Fairlead coordinates as hull metadata | Remove vessel-specific dimensions, generalize |
| Semi RAO data (Q4000, SDP 3500, Uncle John) | Validation RAO datasets | Remove all vessel names → generic_semi_001, generic_semi_002, generic_semi_003 |

**Output**: 2-3 seed hull profiles in `data/hull_library/profiles/`:
- `generic_tanker.yaml` — derived from aframax mesh data
- `generic_barge.yaml` — simple rectangular (already needed for WRK-100 benchmark)
- `unit_box.yaml` — trivial test case (already needed for WRK-099 benchmark)

### Phase 6: Tests

TDD approach — tests written before each phase implementation:

1. **Profile schema tests**: Load/save YAML, validate dimensions, reject invalid stations
2. **Mesh generator tests**: Unit box → expected panel count, normals point outward, watertight check, mesh quality score > 80
3. **Schematic tests**: SVG output contains expected elements, views match profile dimensions
4. **Catalog tests**: Register hull → generate mesh → mock diffraction → retrieve RAOs → compute motions
5. **Round-trip test**: Profile → mesh → GDF file → reload → compare vertex count

## Data Residence

Per WRK-097 three-tier policy:
- Hull profiles + generator + catalog = **Tier 2 (Engineering Reference Data)** → **digitalmodel**
- This plan does NOT touch worldenergydata (plan file location is per plan-mode convention only)

## File Structure (new files in digitalmodel)

```
src/digitalmodel/hydrodynamics/hull_library/
├── __init__.py
├── profile_schema.py        # Phase 1: HullProfile, HullStation, HullType
├── mesh_generator.py        # Phase 2: HullMeshGenerator
├── schematic_generator.py   # Phase 3: SVG/Plotly views
├── catalog.py               # Phase 4: HullCatalog, analysis chain
└── seed_data.py             # Phase 5: Extraction helpers

data/hull_library/
├── profiles/                # YAML hull definitions (committed)
│   ├── unit_box.yaml
│   ├── generic_barge.yaml
│   └── generic_tanker.yaml
├── schematics/              # Generated SVG/PNG (committed)
└── cache/                   # Generated meshes (gitignored)

tests/hydrodynamics/hull_library/
├── test_profile_schema.py
├── test_mesh_generator.py
├── test_schematic_generator.py
├── test_catalog.py
└── test_seed_data.py
```

## Work Items

| ID | Title | Scope | Repo |
|---|---|---|---|
| **WRK-106** | Hull panel geometry generator from line definitions | Phases 1-3 (profile schema + mesh generator + schematics) | digitalmodel |
| **WRK-107** | Hull catalog with analysis chain (hull→RAO→point accelerations) | Phase 4 (catalog registry + motion response + point-specific accelerations) | digitalmodel |
| **WRK-108** | Seed hull library with scrubbed generic profiles from reference data | Phase 5 (extract acma-projects data + legal scrub + create YAML profiles) | digitalmodel |

## Verification

1. `pytest tests/hydrodynamics/hull_library/ -v` — all tests pass
2. Load `unit_box.yaml` → generate mesh → verify 6 faces × N panels
3. Load `generic_barge.yaml` → generate mesh → export GDF → verify readable by mesh handlers
4. Generate schematics for generic_tanker → verify SVG has profile/plan/body views
5. Catalog round-trip: register hull → generate mesh → mock RAOs → compute motions for Hs=3m Tp=10s → verify acceleration output

## Completion Status

| ID | Title | Status | Commit |
|---|---|---|---|
| **WRK-106** | Hull panel geometry generator from line definitions | Complete | `34f1a904f` |
| **WRK-107** | Hull catalog with analysis chain | Complete | `34f1a904f` |
| **WRK-108** | Seed hull library with scrubbed generic profiles | Complete | `34f1a904f` |

### Cross-Review
- **Claude Opus 4.6**: REQUEST_CHANGES → 2 P0 fixed in `cd65c71e6`, 7 P1 addressed
- **Codex CLI**: P2 finding (dynacard init_value, unrelated)
- **Gemini CLI**: NO_OUTPUT

### Deliverables
- 6 source modules in `digitalmodel/src/digitalmodel/hydrodynamics/hull_library/`
- 6 test files (73 tests, all passing)
- 3 seed hull profiles (unit_box, generic_barge, generic_tanker)
- 9 SVG schematics (3 views × 3 hulls)
- Cross-review report at `digitalmodel/docs/reviews/hull-library-cross-review.md`
