# Field Infrastructure Bundle Contract

Contract version: `field-infrastructure-bundle-v1`

This contract exposes field-level BSEE infrastructure joins to products.
It is designed for early engineering workflows: host/tieback screening,
pipeline and riser/appurtenance inventory, FMP/MCP measurement context,
decommissioning scope, and document retrieval queues.

## Build Command

```bash
worldenergydata bsee infrastructure-bundle \
  --field "Stones" \
  --output reports/bsee/field_infrastructure/stones
```

The command defaults to downloaded local BSEE data at:

`/mnt/ace/worldenergydata/data/modules/bsee/bin`

Override when needed:

```bash
worldenergydata bsee infrastructure-bundle \
  --field "Julia" \
  --data-root /mnt/ace/worldenergydata/data/modules/bsee/bin \
  --output reports/bsee/field_infrastructure/julia
```

## Output Files

| File | Product use |
|---|---|
| `field_context.json` | Field name/code, leases, area/block anchors, operators, average water depth. |
| `structures.csv` | Platforms/FPSOs, FMP measurement locations, MCP systems, platform decom records. |
| `pipeline_segments.csv` | Pipeline segment inventory from scanned map indexes and decom rows. |
| `pipeline_locations.csv` | Route/location rows for matched segment IDs. |
| `appurtenances.csv` | Nonblank `PPL_APURT_TYPE` rows, including riser/tie-in/manifold-style evidence when present. |
| `documents.csv` | Scanned pipeline-map, ROW, and plan document index queue. |
| `engineering_summary.json` | Counts, route bounds, appurtenance types, and contract version. |

## Required Evidence Columns

All CSV outputs preserve:

- `source_table`
- `join_key`
- `evidence_confidence`

Evidence confidence values:

| Value | Meaning |
|---|---|
| `direct` | Source row directly describes the asset or location. |
| `inferred` | Row is linked by lease, area/block, segment, or complex and needs engineering review. |
| `document_index` | Row points to a scanned document or plan index; retrieve the document before using as design basis. |

## Engineering Caveats

- There is no dedicated first-class BSEE bin table named for jumpers,
  risers, or umbilicals in the current local mirror.
- Riser evidence can appear in `appurtenances.csv` through
  `PPL_APURT_TYPE`.
- Umbilical and flowline evidence can appear in `pipeline_segments.csv`
  through product codes and endpoint names such as `UMB`, `UMBE`, `UMBH`,
  `UBEH`, `PLET`, `PLEM`, `manifold`, `FLET`, `HIPPS`, `UTA`, and `MFLD`.
- Treat `documents.csv` as a retrieval queue. Do not treat scanned-document
  index rows as final design evidence until the source map, plan, or ROW
  file has been reviewed.
