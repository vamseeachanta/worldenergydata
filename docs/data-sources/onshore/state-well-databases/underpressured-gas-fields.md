# Under-Pressured Gas Fields - Multi-State Screen Results

Issue: [#710](https://github.com/vamseeachanta/worldenergydata/issues/710)
(parent epic [#708](https://github.com/vamseeachanta/worldenergydata/issues/708);
Texas integration [#732](https://github.com/vamseeachanta/worldenergydata/issues/732);
Oklahoma integration [#740](https://github.com/vamseeachanta/worldenergydata/issues/740)).

The screen answers the epic's motivating question — *which wells and fields
actually produced from very low bottom-hole pressure?* — from state-regulator
data. The current run combines Kansas KGS proration pressure observations
([#725](https://github.com/vamseeachanta/worldenergydata/issues/725)) with
Texas RRC completion-packet pressure observations
([#709](https://github.com/vamseeachanta/worldenergydata/issues/709)) and
Oklahoma OCC Form 1002A completion pressure observations
([#740](https://github.com/vamseeachanta/worldenergydata/issues/740)).

## Method

```bash
PYTHONPATH=src:packages/worldenergydata-core/src python3.12 \
  -m worldenergydata.analysis.underpressured_screen.screen \
    --config config/underpressured_screen.yml
```

1. **BHP estimate**: wellhead readings get the static gas-column
   correction `BHP = WHP_psia · exp(0.01875·γg·D / (z̄·T̄))` (γg 0.65,
   z̄ 0.95, T̄ 520 °R from config — a ~7% uplift at Hugoton depths);
   measured BHP values pass through unchanged.
2. **Tiers** on the estimated-BHP gradient: normal ≥ 0.433 psi/ft; mildly
   under-pressured 0.35–0.433; severely under-pressured < 0.35. A separate
   **near-vacuum flag** marks shut-in wellhead pressure < 50 psia — the West
   Panhandle vacuum-operations regime.
3. **Source normalization** adapts state-specific physical schemas into the
   screen contract. Kansas already emits `well_key` and `field`; Texas maps
   `api14` to `well_key`, `field_name` to `field`, injects `state=TX`, and
   filters to rows marked `usable_for_virgin_pressure_proxy`; Oklahoma maps
   OCC completion observations into `well_key`, `field`, `pressure_kind`,
   `pressure_psia`, and `reference_depth_ft`.
4. **Earliest observation per well** is the screening proxy; the source `era`
   label rides along so depleted-era Kansas proration pressures and Texas
   or Oklahoma completion-test screening pressures are not presented as
   measured virgin BHP. Source-provided earliest-observation flags break
   same-year duplicate ties, such as Texas G-1/G-10 rows for the same API14 or
   Oklahoma multi-formation completion rows for the same API.
5. **Field ranking** (>=5 wells) plus a **validation gate**: the run fails
   unless Hugoton and Panoma appear in the top 10 classified severely
   under-pressured.
6. **Participation gate**: Texas and Oklahoma must be loaded and screened, but
   neither completion-test lane is required to recover West Panhandle analogs
   until a full historical or Form 1016 source is available.

Outputs: `/mnt/ace/worldenergydata/data/modules/pressure_screen/curated/`
(`well_screen_earliest.parquet`, `underpressured_field_ranking.parquet`,
`screen_summary.json`).

## Results (run 2026-07-03)

30,100 wells screened: **10,103 Kansas**, **25 Texas**, and **19,972
Oklahoma** wells after earliest-observation selection. The screen loaded
39,134 Kansas pressure rows, 43 usable Texas rows from 48 curated Texas
observations, and 108,518 Oklahoma pressure rows from the OCC completion
extract. Median estimated-BHP gradient is **0.0411 psi/ft**, with **697
near-vacuum** shut-in wellhead-pressure wells. Validation gate: **PASSED**.
Texas and Oklahoma participation gates: **PASSED**.

Tier counts:

| Tier | Wells |
| --- | ---: |
| Severely under-pressured | 28,248 |
| Mildly under-pressured | 855 |
| Normal | 997 |

Source counts after earliest-observation selection:

| Source | State | Wells | Era |
| --- | --- | ---: | --- |
| `kansas_kgs_proration` | KS | 10,103 | depleted |
| `texas_rrc_completion_packets` | TX | 25 | completion_packet_screening |
| `oklahoma_occ_completions` | OK | 19,972 | completion_test_2010_present |

| Field | Wells | Median gradient (psi/ft) | P10–P90 | Near-vacuum wells |
| --- | --- | --- | --- | --- |
| HUGOTON GAS AREA | 7,146 | 0.0316 | 0.022–0.056 | 159 |
| MISSISSIPPIAN | 3,920 | 0.0667 | 0.015–0.332 | 24 |
| WOODFORD | 3,705 | 0.1366 | 0.027–0.373 | 5 |
| PANOMA GAS AREA | 2,342 | 0.0289 | 0.021–0.039 | 20 |
| (unmatched) | 1,306 | 0.0204 | 0.013–0.111 | 15 |
| MISSISSIPPI LIME | 924 | 0.0279 | 0.013–0.244 | 7 |
| CLEVELAND | 745 | 0.0990 | 0.018–0.302 | 7 |
| HUNTON | 647 | 0.0736 | 0.009–0.250 | 25 |
| TONKAWA | 466 | 0.0980 | 0.016–0.223 | 2 |
| OSWEGO | 431 | 0.0416 | 0.013–0.163 | 4 |

Notable beyond the analogs:

- **Greenwood Gas Area** (Morton County, KS) remains the most extreme entry:
  median gradient under 2% of hydrostatic with 22% of tested wells at
  near-vacuum.
- **Mississippian** and **Woodford** are the largest Oklahoma completion-test
  entries. They are screening-only formation-name buckets, not yet a
  field-development architecture model.
- **Briscoe Ranch (Eagleford)** enters as the first Texas ranked field: 16
  earliest wells, all screening-only WHP-derived observations, median estimated
  gradient 0.1361 psi/ft.
- Two Texas wells classify normal after the gas-column correction:
  `CARTHAGE (HAYNESVILLE SHALE)` and `HAWKVILLE (AUSTIN CHALK)`.

## Caveats

- These are **depleted-era** pressures (tests begin 1996; Hugoton discovered
  1922). They prove sustained economic production at extremely low BHP — the
  epic's question — but virgin-pressure claims need DST-era evidence (KGS DST
  records are a per-well scrape, catalogued in `source-catalog.md`).
- Gradients use source-provided TVD/depth fields and an average-z̄T̄ gas
  column; both are approximations flagged in the data (`bhp_method`,
  `gradient_method`).
- Texas RRC [#709](https://github.com/vamseeachanta/worldenergydata/issues/709)
  rows and Oklahoma OCC
  [#740](https://github.com/vamseeachanta/worldenergydata/issues/740) rows are
  **wellhead pressure**
  rows, not measured bottom-hole pressure. Oklahoma uses `WHP_shut_in` first
  and `WHP_flowing_tubing` as a fallback when shut-in pressure is missing.
  Both remain screening-only until a source provides measured BHP or a better
  calibrated gas-column correction.
- The Texas input is a narrow daily completion packet, not a full historical
  pressure archive. It is useful for proving the multi-state screen path and
  finding current low-gradient examples, but it is not yet a West Panhandle
  analog recovery dataset.
- The Oklahoma input covers structured Form 1002A completion records from
  2010-present. Pre-2010 legacy completions and Form 1016 back-pressure tests
  remain imaged/legacy lanes and are not in this run.
- The Texas quality sidecar currently carries
  `raw_manifest_warning:completion_data:error:2026-07-01T00:36:55Z`; the
  screen propagates that warning into `screen_summary.json`.
