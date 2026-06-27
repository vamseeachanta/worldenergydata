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
309 / 334.

## v3 — moored-floater depth recalibration

v2's residual gap was the **moored-floater family** (TLP / spar / semisub): their
`DEPTH_SWEET_M` bands were nearly identical, so `depth_fit` could not separate
them and spar/TLP picks lost to the semisub's flatter, higher base profile (spar
sat at **0** recall). The observed GoM medians are distinct — TLP ≈ 1036 m, spar
≈ 1265 m, semisub ≈ 1958 m — so the bands were tightened to **tile by depth**:
TLP `(400, 1400)`, spar `(700, 1600)`, semisub `(1700, 2800)`. Water depth is a
pure input, so this carries no leakage.

| metric           | v2        | v3        |
|------------------|-----------|-----------|
| top-1 (base)     | 50.5%     | 52.6%     |
| top-1 (enriched) | 52.4%     | 54.6%     |
| spar recall      | 0 / 28    | 7 / 28    |
| TLP recall       | 15 / 46   | 30 / 46   |

Top-3 dips ~1 pt (a band-edge reshuffle) but stays well above the pinned floor.
Regression tests pin top-1 ≥ 0.50 (un-enriched) / ≥ 0.52 (enriched), FPSO ≥ 50,
subsea_tieback ≥ 15, spar ≥ 4, TLP ≥ 25.

## In-sample, not held-out (read before quoting the numbers)

Every accuracy figure here is **in-sample**. The back-test scores the whole
enriched catalog, and the `depth_fit` bands (the largest single weight) and the
basin affinities were set from that same catalog's distribution — there is **no
train/test holdout**. So:

- There is **no feature leakage** — the engine never sees a field's label; depth,
  region, etc. are genuine inputs.
- But there **is in-sample optimism** — the cutoffs were fitted (by hand, from the
  per-concept depth medians) to the fields being scored. The numbers measure how
  well the heuristic *fits known fields*, not expected accuracy on unseen ones.

Quote them as a fit/diagnostic, not a generalization estimate. A held-out or
cross-validated figure (re-deriving the bands per fold) would be the honest next
step before any external accuracy claim.

## Honest residual gaps

- **spar vs semisub** remains the weakest pair — depth now separates the bulk,
  but the overlap band (≈1600–1800 m) still mixes them; a clean split needs a
  dry-tree/intervention signal that is *downstream* of the concept choice (so it
  would leak), hence not used.
- **Per-tieback offset** is approximated by a basin median (og_host records none),
  so tieback distance is feasibility-grade, not metric-grade.
- The basin table is coarse by design; per-operator/era signatures are out of
  scope.
