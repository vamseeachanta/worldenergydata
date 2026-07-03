# Under-Pressured Gas Fields — Screen Results (Kansas First Cut)

Issue: [#710](https://github.com/vamseeachanta/worldenergydata/issues/710)
(parent epic [#708](https://github.com/vamseeachanta/worldenergydata/issues/708)).

The screen answers the epic's motivating question — *which wells and fields
actually produced from very low bottom-hole pressure?* — from state-regulator
data. This first cut runs on the Kansas KGS ingest (#725); Texas RRC joins
through the same observation schema once #709's extraction lands.

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
3. **Earliest observation per well** is the virgin-pressure proxy; the source
   `era` label (depleted for the 1996+ Kansas proration program) rides along
   so depleted-era pressures are never presented as virgin.
4. **Field ranking** (≥5 wells) plus a **validation gate**: the run fails
   unless Hugoton and Panoma appear in the top 10 classified severely
   under-pressured.

Outputs: `/mnt/ace/worldenergydata/data/modules/pressure_screen/curated/`
(`well_screen_earliest.parquet`, `underpressured_field_ranking.parquet`,
`screen_summary.json`).

## Results (Kansas, run 2026-07-02)

10,103 wells screened — **all severely under-pressured** (expected: the
proration program observed Hugoton-trend gas seven decades into depletion).
Median estimated-BHP gradient **0.0304 psi/ft ≈ 7% of hydrostatic**.
**264 wells were at near-vacuum** shut-in wellhead pressure. Validation gate:
**PASSED**.

| Field | Wells | Median gradient (psi/ft) | P10–P90 | Near-vacuum wells |
| --- | --- | --- | --- | --- |
| HUGOTON GAS AREA | 7,146 | 0.0316 | 0.022–0.056 | 159 |
| PANOMA GAS AREA | 2,342 | 0.0289 | 0.021–0.039 | 20 |
| GREENWOOD GAS AREA | 233 | **0.0181** | 0.014–0.029 | **51 (22%)** |
| HUGOTON | 200 | 0.0352 | 0.020–0.068 | 12 |
| PANOMA | 60 | 0.0232 | 0.015–0.033 | 15 |
| GREENWOOD | 17 | 0.0212 | 0.015–0.031 | 1 |

Notable beyond the analogs: **Greenwood Gas Area** (Morton County, KS) is the
most extreme entry — median gradient under 2% of hydrostatic with 22% of its
tested wells at near-vacuum, i.e., wells literally being sucked dry and still
on the annual test rolls.

## Caveats

- These are **depleted-era** pressures (tests begin 1996; Hugoton discovered
  1922). They prove sustained economic production at extremely low BHP — the
  epic's question — but virgin-pressure claims need DST-era evidence (KGS DST
  records are a per-well scrape, catalogued in `source-catalog.md`).
- Gradients use wells-master total depth as the reference depth and an
  average-z̄T̄ gas column; both are approximations flagged in the data
  (`bhp_method`, `gradient_method`).
- Single-source run: tier boundaries (0.433/0.35) only become discriminating
  once normally-pressured populations (TX #709, OK completions) enter the
  same table.
