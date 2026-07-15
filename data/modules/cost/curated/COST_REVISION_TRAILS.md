# COST_REVISION_TRAILS — provenance

**Dataset:** `data/modules/cost/curated/cost_revision_trails.csv`
**Issue:** [#1027](https://github.com/vamseeachanta/worldenergydata/issues/1027) (E4, child of hardening epic [#1023](https://github.com/vamseeachanta/worldenergydata/issues/1023))
**Accessed:** 2026-07-15
**Builder:** `scripts/cost/build_cost_revision_trails.py`

A project's cost is not one number — it is a **sequence** of dated statements: sanction
estimate → revision(s) → spend-to-date → final outturn. `sanctioned_projects.csv` records the
first point (the FID number); this table records the whole trail, because the *shape* of that
trail is the proof the presentation needs: **did the project cost what its FID number said?**

**47 trail points across 20 projects.** Twelve have a full sanction→final trail in a single
currency, so an overrun is directly computable (E6/#1029 added the regulator-tier Norwegian NOK
trails, which now bracket the whole distribution):

| Project | Sanction | Final | Δ |
|---|---:|---:|---:|
| Martin Linge (NOK) | 31.5bn | 63.0bn | **+100%** |
| Goliat (NOK) | 28.0bn | ~50.0bn | **+79%** |
| Gorgon (USD) | $37.0bn | ~$54.0bn | +46% |
| Tyra (DKK) | 21.0bn | ~27.0bn | +29% |
| Sangomar Ph1 (USD) | $4.2bn | $5.0bn | +19% |
| Aasta Hansteen (NOK) | 32.0bn | 37.5bn | +17% |
| Mariner (USD) | $7.0bn | ~$7.7bn | +10% |
| Jubilee Ph1 (USD) | $3.15bn | $3.3bn | +5% |
| TEN (USD) | $4.0bn | <$4.0bn | ~0% |
| Peregrino Ph2 (USD) | $3.5bn | ~$3.0bn | −14% |
| Kraken (USD) | $3.2bn | $2.5bn | −22% |
| Johan Sverdrup Ph1 (NOK) | ~123bn | 83bn | **−33%** |

The spread (**−33% to +100%**) is the finding: FID figures are **not** a reliable proxy for
outturn, and the direction is not uniform. The two poles are both Norwegian and both regulator-
corroborated: **Johan Sverdrup Phase 1** cut ~NOK 40bn (a third) below its PDO through phased
de-risking, while **Martin Linge** doubled after yard and hook-up failures. USD-reporting mid-caps
(EnQuest Kraken −22%, Premier Catcher −30%) and re-scoped brownfields (Peregrino Ph2 −14%) also
came in under; integrated-LNG megaprojects (Gorgon +46%) ran over. Mad Dog Phase 2 shows the
pre-sanction lever — a redesign that cut the concept 22 → 14 → 9 $bn *before* FID.

## Rules (mirroring the sanctioned-projects discipline)

- **Currencies are never converted.** A trail lives in one currency; the reconciliation harness
  (E5) compares like-for-like. Martin Linge and Tyra carry parallel USD and NOK/DKK rows because
  the operator stated both.
- **`PROVENANCE` tier is explicit per point:** `operator` / `partner_sec` / `partner_asx` /
  `regulator` / `trade_press`. A `trade_press` point with `CONFIDENCE = low` marks an outturn
  that is widely reported but not operator-attributed — it is honest about being an approximate
  endpoint, never dressed as a disclosed figure.
- **`IN_SANCTIONED_SET`** flags whether the project has a row in `sanctioned_projects.csv`.
  Pluto/Catcher (AUD-native / outturn-only) and the four Norwegian NOK-only fields (Johan Sverdrup
  Ph1, Goliat, Aasta Hansteen — plus Martin Linge which *is* in the set) are `False` where their
  FID figure did not meet the USD/attribution import bar, but their **trail** is still a valid,
  sourced observation.

## NOK regulator-tier trails (E6/#1029 — added)

The Norwegian fields sanction in NOK, so they never entered `sanctioned_projects` (USD-only), but
their trails are the richest in the table — the regulator (Sokkeldirektoratet) and the Storting
(Prop. 1 S budget documents) publish per-project investment revisions. E6 added:

- **Johan Sverdrup Phase 1** — ~NOK 123bn PDO → 99bn (2016) → 86bn (2018) → **83bn outturn** (−33%),
  each step an Equinor statement; the biggest under-run in the dataset.
- **Martin Linge** — corrected: the sanction basis is the **NOK 31.5bn PDO** (Jun 2012), not the
  NOK 25.6bn launch PR; +NOK 26bn/+85% revision reported to the Storting in **Prop. 1 S (2019-2020)**
  (regulator-tier, via Sokkeldirektoratet OD-04-20) → **NOK 63bn outturn** (+100%).
- **Goliat** — NOK 28bn PDO (2009) → NOK 46.7bn (Prop. 1 S 2015, +49%) → ~NOK 50bn at first oil.
- **Aasta Hansteen** — NOK 32bn PDO (2013) → NOK 37.5bn outturn (+17%, within PDO uncertainty).

Still open: exact Storting verbatims for the Goliat 2009 PDO (regjeringen.no 403s to automated
fetch — a browser-fetch pass would lift the St.prp. nr. 64 figure). Sokkeldirektoratet Factpages
also give *cumulative lifetime* investment (Goliat 57,013 MNOK, Martin Linge 59,079 MNOK) which
includes post-startup spend and is **not** the development outturn — recorded in notes, not used
as the sanction→outturn delta.
