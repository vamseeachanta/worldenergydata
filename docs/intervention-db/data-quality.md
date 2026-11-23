# Subsea-Intervention DB — Data-Quality Guardrail

> **Status:** caveats sheet for epic #582 (subsea well-intervention database).
> Cited by the brief (#588) and by every downstream model built on this DB.
> Mirrors the honest-data framing of digitalmodel #903.

This is the "read me first" sheet for anyone querying or modelling the
subsea-intervention database. Each entry is a real trap found while building the
DB this session, with the specific number and the safe way to use the field.
**If a model contradicts a caveat here, the model is wrong, not the caveat.**

---

## 0. Overarching framing — what this DB is (and is not)

**The whole DB is a FORWARD-LOOKING ACCESS-RISK picture, not a measured
present-day demand-vs-supply crossover.**

The recorded BSEE history shows **flat-to-declining recorded deepwater
workovers**. There is no observed "intervention demand exceeds vessel supply"
crossover in the data. The value of this DB is in characterising *future access
risk* — how hard a given subsea well will be to reach and service as the
installed base ages and moves deeper — **not** in claiming a present-day
shortfall.

Do not present any chart from this DB as evidence of a current
demand-vs-supply gap. Every count below is a *floor* or a *characterisation*,
not a measured trend. See the per-field caveats for why.

---

## 1. WAR `WATER_DEPTH` is ~94% NULL → counts are floors

**Source:** `war/mv_war_main.bin` (Well Activity Reports).

`WATER_DEPTH` is NULL in **340,875 of 363,786 rows (~94%)**. Only ~6% of WAR
rows carry their own water depth.

**Consequence:** any WAR-by-depth-band count is a **FLOOR**, not a true count.
Rows with a null depth silently drop out of every band, so each band is
under-reported by an unknown amount.

**Safe usage:** **join water depth from the well registry**, keyed on the well,
**not** from WAR's own `WATER_DEPTH` column. Treat WAR's column as present only
for the ~6% of rows that have it, and never bucket the other 94% as "unknown
shelf" — they are missing, not shallow.

---

## 2. WAR `BOP_TEST_DATE` has dirty future dates (max 2108)

**Source:** `war/mv_war_main.bin`.

`BOP_TEST_DATE` contains implausible future dates — the maximum observed is
**2108**. These are data-entry / encoding errors, not real events.

**Safe usage:** **filter implausible dates before any time trend.** Drop rows
with dates beyond the data-collection horizon (e.g. `> current year`) before
plotting or fitting anything time-indexed. A single 2108 row will silently blow
out axis ranges, bin edges, and any "latest activity" max.

---

## 3. The 593-registry UNDERCOUNTS older subsea completions

**Source:** `permstruc/mv_subsea_boreholes.bin` (the "593 registry" —
593 subsea boreholes on record).

The subsea-borehole registry is **authoritative for what it contains** but
**likely undercounts older subsea completions** (sparse coverage of legacy
wells). **Do not treat the 593 registry as the full installed base.**

**Reconciliation (done in #583)** against the well population
(`offshorestats/mv_sbwd_wells.bin`, median `WATER_DEPTH` per
`API_WELL_NUMBER`), bucketed into the MODU-servicing water-depth bands:

| Band | Subsea wells on record | Total wells in band | Subsea share |
|------|-----------------------:|--------------------:|-------------:|
| < 500 ft (shelf)     |   0 | 25,844 |   0.0% |
| 500–3,000 ft         | 114 |  2,156 |   5.3% |
| 3,000–5,000 ft       | 209 |    801 |  26.1% |
| 5,000–10,000 ft      | 270 |    485 |  55.7% |
| > 10,000 ft          |   0 |      0 |    n/a |
| **Subsea total**     | **593** | — | — |
| **Well population total** | — | **29,286** | — |

Subsea depth stats (registry): min 1,055 ft, median 4,609 ft, max 9,627 ft.

**Key qualitative result:** the **subsea share inverts with depth** — only 5.3%
of wells are subsea in the 500–3,000 ft band, rising to 26.1% (3,000–5,000 ft)
and 55.7% (5,000–10,000 ft). Deeper water is majority-subsea; the shelf is
effectively all dry-tree.

**Caveats on the reconciliation itself:**
- The registry has **no `API_WELL_NUMBER`**, so this is a **population
  comparison, not a row-level join**. The two sources cannot be merged
  per-well.
- Subsea band counts are reported as **"on record"** (floors). `subsea_share`
  depends on full-population coverage and inherits the undercount.
- **Report the delta** when you cite these numbers; do not round the registry
  up to "the installed base".

**Reuse, do not redefine:** the band scheme lives in
`worldenergydata.bsee.analysis.intervention.well_inventory_by_band`
(`BAND_LABELS`, `MODU_SERVICING_BANDS`, `classify_modu_band`). Import it; never
re-hardcode band edges.

---

## 4. Subsea vs dry-tree is AMBIGUOUS — no single BSEE flag

There is **no single BSEE field** that cleanly labels a well subsea vs
dry-tree. Classification is inferred, and the inference has limited ground
truth.

The subsea-tree-height flag in
`data/modules/bsee/current/operations/ST_BP_and_tree_height.csv` is only a
**~100-row SAMPLE** (#584), **not** a comprehensive label set. It can validate a
classifier on a sample but cannot label the full population.

**Safe usage:** treat any subsea/dry-tree label as a **classifier output with
stated confidence**, not a measured fact. Document the classifier's confidence
wherever the label is used, and never present subsea/dry-tree splits as exact
counts.

---

## 5. Pressure class (15K / 20K) is ABSENT from BSEE data

Wellhead pressure class (15,000 psi vs 20,000 psi) is **not present anywhere in
the BSEE data**. It is an **external attribute only** — it must be sourced and
joined from outside this DB and flagged as such.

Context for modellers: 20K-rated capability is extremely scarce — **only two
rigs worldwide are 20K-rated.** Any 20K-dependent scenario is supply-constrained
by that fact, which lives entirely outside BSEE.

---

## 6. OGOR partial-year / WAR reporting-lag are NOT trends

The most recent period in **OGOR (partial year)** and in **WAR (reporting lag)**
is incomplete by construction — late-arriving records have not yet landed.

**Safe usage:** **never read the latest period as a trend.** A dip in the most
recent year is almost always reporting lag, not a real decline. Exclude or clearly
annotate the trailing partial period in any time series, and do not fit decline
slopes through it.

---

## 7. Vessel-side traps

These bite when joining the BSEE well/intervention data to vessel/rig fleet data.

- **Island Innovator** — converted to a **drilling rig**; it is **not** an RLWI
  (riserless light well intervention) vessel. Do not count it in RLWI capacity.
- **Trion** — sits in **Mexican waters**. **Exclude it from US (BSEE/GoM)
  counts.** It is not part of the US installed base or US activity.
- **Drive-corpus vessel specs are 2010–2014 vintage** — **stale**. They reflect
  historical fleet snapshots, **not current availability**. Do not present them
  as today's market.

---

## Provenance & cross-references

- Epic: **#582** (subsea well-intervention DB). Brief: **#588**.
- Band reconciliation: **#583** (`well_inventory_by_band`, see
  `…/intervention/data/well_inventory_by_band.yml`).
- Subsea/dry-tree classifier: **#584**.
- Planned/projected subsea-wells overlay: **#587**.
- Honest-data framing mirror: **digitalmodel #903**.

Underlying BSEE tables (not committed to this repo; real `.bin` extracts on
`/mnt/ace`):
`permstruc/mv_subsea_boreholes.bin`, `war/mv_war_main.bin`,
`offshorestats/mv_sbwd_wells.bin`. The tree-height sample CSV **is** committed at
`data/modules/bsee/current/operations/ST_BP_and_tree_height.csv`.
