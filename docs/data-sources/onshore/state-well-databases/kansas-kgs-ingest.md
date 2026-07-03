# Kansas KGS Ingest — Wells Master + Hugoton Proration Pressures

Issue: [#725](https://github.com/vamseeachanta/worldenergydata/issues/725)
(parent epic [#708](https://github.com/vamseeachanta/worldenergydata/issues/708);
sources verified in `source-catalog.md`).

First state ingested from the multi-state survey: two free KGS bulk files
become the normalized per-well pressure-observation table that the
under-pressured gas/condensate screen (#710) consumes — the same schema the
Texas RRC extraction (#709) will produce.

## Pipeline

```bash
PYTHONPATH=src python -m worldenergydata.modules.state_regulators.kansas_kgs.pipeline \
    --config config/kansas_kgs.yml
```

Code: `src/worldenergydata/modules/state_regulators/kansas_kgs/`
(parsers + pipeline; tests in `tests/unit/state_regulators/`).

Inputs (downloaded once — the proration file is frozen at 2013-10-08):

| File | Content | Size |
| --- | --- | --- |
| `kansas_proration_pressures.txt` | KCC gas proration program: per-well annual shut-in pressure, working pressure, open flow, adjusted deliverability | 14 MB |
| `ks_wells.zip` → `ks_wells.txt` | Statewide wells master: KID, API, field, total depth, formation at TD, dates, status (516,206 wells) | 44 MB |

Outputs under `/mnt/ace/worldenergydata/data/modules/kansas_kgs/`:

```text
raw/        manifest.json (sha256, source URL, size) + verbatim downloads
normalized/ pressure/proration_pressures.parquet, wells/wells_master.parquet
curated/    pressure/well_pressure_observations.parquet, pressure/coverage_stats.json
```

## Format quirks handled (unit-tested)

- The proration file header wrapped during KGS's export, leaving a stray
  continuation fragment (`RES","DIFFERENT","COEFF"`) on line 2 — detected and
  skipped structurally (any non-quote-opening lines after the header).
- `SHUT_IN_PRESS` of 0 or blank means "not tested that year", not a vacuum
  reading — excluded from observations, retained in normalized data.
- Wells-master dates are Oracle `DD-Mon-YYYY`.
- Join key is the KGS well KID (`WELL_KID` → `KID`), not the API string;
  API-14 is carried for cross-state joins.

## Honest-measurement notes

- Reported shut-in pressures are **wellhead gauge readings**
  (`pressure_kind = WHP_shut_in`), not BHP. `pressure_psia` adds the standard
  atmosphere only; the static gas-column correction to BHP is the screen's
  job (#710), so the recorded gradient
  (`gradient_method = whp_shutin_over_td_lower_bound`) is a lower bound.
- Reference depth is wells-master total depth; gradients are computed only
  where depth > 0.
- Earliest observation per well is flagged (`is_earliest_observation`), but
  the program's pressure records start in 1996 — decades after Hugoton's
  1922 discovery — so these are depleted-era pressures, not virgin. That
  still answers the motivating question (fields *producing* from very low
  BHP); virgin-pressure claims need DST-era evidence.

## Run results (2026-07-02)

| Metric | Value |
| --- | --- |
| Proration rows | 79,093 (39,134 with a real pressure) |
| Wells with ≥1 pressure observation | 10,133 (105 unmatched in wells master, ~1%) |
| Observations with gradient | 39,010 |
| Pressure-bearing test years | 1996–2004 (2001 nearly empty — program gap year) |
| Top fields | HUGOTON GAS AREA 7,150 wells; PANOMA 2,343; GREENWOOD 234 — Hugoton-trend dominance confirms the join |

**Headline: the median earliest-observation gradient is 0.028 psi/ft — about
6% of hydrostatic (0.433 psi/ft).** Quantiles (P10–P90):
0.019 / 0.024 / 0.028 / 0.036 / 0.049 psi/ft. Ten thousand Kansas wells were
producing economically at wellhead shut-in pressures far below any normal
reservoir gradient — the quantitative version of the Hugoton/West Panhandle
analog cited in the epic's motivating discussion.

Note: the survey described the file as "frozen 2013" — that is its
last-updated date. The data itself spans test years 1996–2004 only (verified:
zero rows after 2004 in the raw file).
