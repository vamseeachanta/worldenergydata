# Under-Pressured Gas Fields - Multi-State Screen Results

Issue: [#710](https://github.com/vamseeachanta/worldenergydata/issues/710)
(parent epic [#708](https://github.com/vamseeachanta/worldenergydata/issues/708);
Texas integration [#732](https://github.com/vamseeachanta/worldenergydata/issues/732)).

The screen answers the epic's motivating question — *which wells and fields
actually produced from very low bottom-hole pressure?* — from state-regulator
data. The current run combines Kansas KGS proration pressure observations
([#725](https://github.com/vamseeachanta/worldenergydata/issues/725)) with
Texas RRC completion-packet pressure observations
([#709](https://github.com/vamseeachanta/worldenergydata/issues/709)).

## Method

```bash
PYTHONPATH=src python -m worldenergydata.analysis.underpressured_screen.screen \
    --config config/underpressured_screen.yml
```

1. **BHP estimate**: wellhead shut-in readings get the static gas-column
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
   filters to rows marked `usable_for_virgin_pressure_proxy`.
4. **Earliest observation per well** is the screening proxy; the source `era`
   label rides along so depleted-era Kansas proration pressures and Texas
   completion-packet screening pressures are not presented as measured virgin
   BHP. Source-provided earliest-observation flags break same-year duplicate
   ties, such as Texas G-1/G-10 rows for the same API14.
5. **Field ranking** (>=5 wells) plus a **validation gate**: the run fails
   unless Hugoton and Panoma appear in the top 10 classified severely
   under-pressured.
6. **Participation gate**: Texas must be loaded and screened, but the current
   daily completion packet is too narrow to require West Panhandle analog
   recovery.

Outputs: `/mnt/ace/worldenergydata/data/modules/pressure_screen/curated/`
(`well_screen_earliest.parquet`, `underpressured_field_ranking.parquet`,
`screen_summary.json`).

## Results (run 2026-07-03)

10,128 wells screened: **10,103 Kansas** wells and **25 Texas** wells after
earliest-observation selection. The screen loaded 39,134 Kansas pressure rows
and 43 usable Texas pressure rows from 48 curated Texas observations. Median
estimated-BHP gradient remains **0.0304 psi/ft**, with **264 near-vacuum**
shut-in wellhead-pressure wells. Validation gate: **PASSED**. Texas
participation gate: **PASSED**.

Tier counts:

| Tier | Wells |
| --- | ---: |
| Severely under-pressured | 10,126 |
| Normal | 2 |

Source counts after earliest-observation selection:

| Source | State | Wells | Era |
| --- | --- | ---: | --- |
| `kansas_kgs_proration` | KS | 10,103 | depleted |
| `texas_rrc_completion_packets` | TX | 25 | completion_packet_screening |

| Field | Wells | Median gradient (psi/ft) | P10–P90 | Near-vacuum wells |
| --- | --- | --- | --- | --- |
| HUGOTON GAS AREA | 7,146 | 0.0316 | 0.022–0.056 | 159 |
| PANOMA GAS AREA | 2,342 | 0.0289 | 0.021–0.039 | 20 |
| GREENWOOD GAS AREA | 233 | **0.0181** | 0.014–0.029 | **51 (22%)** |
| HUGOTON | 200 | 0.0352 | 0.020–0.068 | 12 |
| PANOMA | 60 | 0.0232 | 0.015–0.033 | 15 |
| GREENWOOD | 17 | 0.0212 | 0.015–0.031 | 1 |
| BRISCOE RANCH (EAGLEFORD) | 16 | 0.1361 | 0.094–0.205 | 0 |

Notable beyond the analogs:

- **Greenwood Gas Area** (Morton County, KS) remains the most extreme entry:
  median gradient under 2% of hydrostatic with 22% of tested wells at
  near-vacuum.
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
- Gradients use wells-master total depth as the reference depth and an
  average-z̄T̄ gas column; both are approximations flagged in the data
  (`bhp_method`, `gradient_method`).
- Texas RRC #709 rows in this run are all **shut-in wellhead pressure** rows,
  not measured bottom-hole pressure. They remain screening-only until a source
  provides measured BHP or a better calibrated gas-column correction.
- The Texas input is a narrow daily completion packet, not a full historical
  pressure archive. It is useful for proving the multi-state screen path and
  finding current low-gradient examples, but it is not yet a West Panhandle
  analog recovery dataset.
- The Texas quality sidecar currently carries
  `raw_manifest_warning:completion_data:error:2026-07-01T00:36:55Z`; the
  screen propagates that warning into `screen_summary.json`.
