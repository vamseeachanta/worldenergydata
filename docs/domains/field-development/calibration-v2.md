# Recommendation-engine calibration v2

Epic #567. Back-test of `field_development.recommendation.recommend` against the
real development concepts of the enriched SubseaIQ catalog (867 fields with a
known concept + water depth). v1 (depth envelopes + NUI fix) reached top-1 ≈ 43%;
v2 adds a **basin prior** and a **SubseaIQ host-registry enrichment** layer.

## The v1 ceiling

The confusion matrix showed five concept types at **zero** top-1 recall —
together 47% of the set:

| real concept    | v1 recall | why                                              |
|-----------------|-----------|--------------------------------------------------|
| fpso            | 0 / 226   | no regional signal — loses to jacket/semisub     |
| subsea_tieback  | 0 / 116   | removed from feasibility without a host distance |
| spar            | 0 / 44    | profile ≈ semisub; no discriminator              |
| compliant_tower | 0 / 12    | —                                                |
| flng            | 0 / 7     | —                                                |

The loader filled only depth + fluid + region, so the engine's reserves/tieback
logic ran blind. Two honest, *upstream* signals close most of the gap.

## 1. Basin prior (`basin.py`)

Within a depth band, the choice between (say) an FPSO, a semisub and a spar is
driven by **regional development culture** — documented practice, not fitted
frequencies:

- **Brazil / West Africa** deepwater → FPSO.
- **US Gulf of Mexico** → spar / semisub / TLP / subsea; FPSO historically rare
  (first GoM FPSO 2012).
- **North Sea** → fixed jackets + FPSO + subsea; spars/TLPs absent.

Encoded as a coarse `basin → concept` affinity table (favour / neutral /
disfavour), added as a weighted `region_fit` criterion. A missing/unmapped region
scores neutral, so the prior only ever *adds* signal where the basin is known.

## 2. SubseaIQ host enrichment (`host_enrichment.py`)

Built from the curated `subseaiq_hosts.csv` (see `SUBSEAIQ_HOSTS.md`):

- **Ground-truth correction** — the facility-join mislabels tieback satellites
  with their host's concept; relabel them `subsea_tieback` (19 fields).
- **Input enrichment** — a known satellite gains a reachable host and a screening
  `distance_to_host_km`; a host field gains real reserves + well count.

The host layer's gain comes from those covered fields where og_host supplies both
the corrected label and the (genuinely-known) host proximity — it is *better data
on covered fields*, not a generalizing heuristic, and is reported separately.

## Measured effect (867 fields)

| configuration                | top-1     | top-3     |
|------------------------------|-----------|-----------|
| v1 baseline (depth only)     | 42.7%     | 50.7%     |
| + basin prior alone          | 50.5%     | 62.5%     |
| + host enrichment alone      | 44.5%     | 51.7%     |
| **v2 (both)**                | **52.4%** | **62.7%** |

FPSO recall 0 → 82 / 226; subsea_tieback 0 → 19 / 135; fixed_jacket held at
309 / 334. Regression tests pin top-1 ≥ 0.48 (un-enriched) / ≥ 0.50 (enriched),
FPSO ≥ 50, subsea_tieback ≥ 15.

## Honest residual gaps

- **spar vs semisub** (still 0 recall) — near-identical profiles; needs a
  dry-tree/intervention signal not cleanly available upstream.
- **Per-tieback offset** is approximated by a basin median (og_host records none),
  so tieback distance is feasibility-grade, not metric-grade.
- The basin table is coarse by design; per-operator/era signatures are out of
  scope.
