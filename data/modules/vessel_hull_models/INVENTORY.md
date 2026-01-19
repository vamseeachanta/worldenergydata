# Vessel Hull Models - Asset Inventory

> Last Updated: 2026-01-19
> Source: Gathered from digitalmodel repository

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

## External Resources (digitalmodel)

### MarineTraffic API Integration

A MarineTraffic API client exists in digitalmodel for vessel specifications:

```
/mnt/github/workspace-hub/digitalmodel/src/digitalmodel/data_procurement/vessel/api_clients/marinetraffic_client.py
```

**Capabilities:**
- Query vessel by IMO number
- Query vessel by MMSI
- Search by vessel name
- Get vessel dimensions (LOA, beam, draft)
- Get vessel type and flag

### Wigley Hull Reference

OpenFOAM case study for parametric Wigley hull:
```
/mnt/github/workspace-hub/digitalmodel/docs/modules/openfoam/case_studies/wigleHull_LTS/
- wigley_hull_coefficients.ods (spreadsheet with coefficients)
- wigley_hull_in_waves.pdf (documentation)
- wigleyHull_LTS.tar.gz (OpenFOAM case files)
```

### Blender Automation

Marine engineering integration examples:
```
/mnt/github/workspace-hub/digitalmodel/src/blender_automation/examples/marine_engineering_integration.py
```

**Capabilities:**
- Ship hull import/export
- Mesh cleanup and optimization
- Multi-format export (STL, OBJ, PLY, GLTF)
- CFD preparation

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
