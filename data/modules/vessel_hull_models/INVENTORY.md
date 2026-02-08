# Vessel Hull Models - Asset Inventory

> Last Updated: 2026-01-19
> Source: Authoritative collection — hull geometry acquired from CAD exports (Rhino), OrcaWave diffraction analysis, and 3D model repositories

## Available Hull Models

### 1. Sea Cypress (Floating Production Vessel)

| Property | Value |
|----------|-------|
| **File** | `hulls/sea_cypress.obj` |
| **Source** | Orcawave diffraction analysis |
| **Original** | Rhino export (0.25 mesh resolution) |
| **Vertices** | 13,536 |
| **Faces** | 4,331 |
| **File Size** | 2.5 MB |
| **Units** | Meters |
| **Quality** | Engineering (CFD/hydrodynamic grade) |

**Notes:**
- High-quality mesh suitable for wave diffraction analysis
- Exported from Rhino CAD software
- Includes material definitions (MTL file reference)

---

## Marine Components

Small-scale components for mooring and subsea visualization:

| File | Type | Description |
|------|------|-------------|
| `marine_components/anchor.obj` | Mooring | Anchor geometry |
| `marine_components/buoy.obj` | Mooring | Surface buoy |
| `marine_components/chain_link.obj` | Mooring | Chain link segment |
| `marine_components/manifold.obj` | Subsea | Subsea manifold |
| `marine_components/valve.obj` | Subsea | Subsea valve |

**Note:** These are simplified/placeholder models, not engineering-grade.

---

## Related Engineering Tools

The following tools in the workspace can consume hull geometry from this collection.
See `workspace-hub/docs/DATA_RESIDENCE_POLICY.md` for the cross-repo data handoff contract.

### MarineTraffic API
Vessel specification lookup by IMO/MMSI number. Provides dimensions (LOA, beam, draft), vessel type, and flag data to enrich hull model metadata.

### Parametric Hull Generation
Wigley hull and Series-60 parametric formulas can generate hull geometry for vessels where 3D models are unavailable. These are engineering reference tools (Tier 2) that produce derived data — outputs stay in the engineering analysis repo, not here.

### Mesh Processing
Blender automation pipeline for hull mesh cleanup, format conversion (STL, OBJ, PLY, GLTF), and CFD preparation.

---

## Acquisition Status - GOM Installation Vessels

| Vessel | Operator | Type | IMO | Status |
|--------|----------|------|-----|--------|
| Sleipnir | Heerema | Crane | 9781400 | ⬜ Not acquired |
| Thialf | Heerema | Crane | 8757740 | ⬜ Not acquired |
| Saipem 7000 | Saipem | Crane | 8767350 | ⬜ Not acquired |
| Pioneering Spirit | Allseas | Single-lift | 9593505 | ⬜ Not acquired |
| Seven Borealis | Subsea 7 | Pipelay | 9426941 | ⬜ Not acquired |
| Sea Cypress | ? | FPV | ? | ✅ Available |

---

## Next Steps

1. **Search free 3D repositories** (SketchFab, GrabCAD) for installation vessel models
2. **Generate parametric hulls** using Wigley/Series-60 formulas for unavailable vessels
3. **Integrate MarineTraffic** for vessel specifications (LOA, beam, draft)
4. **Build visualization pipeline** for interactive 3D viewing
