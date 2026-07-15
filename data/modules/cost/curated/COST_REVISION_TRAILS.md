# COST_REVISION_TRAILS — provenance

**Dataset:** `data/modules/cost/curated/cost_revision_trails.csv`
**Issue:** [#1027](https://github.com/vamseeachanta/worldenergydata/issues/1027) (E4, child of hardening epic [#1023](https://github.com/vamseeachanta/worldenergydata/issues/1023))
**Accessed:** 2026-07-15
**Builder:** `scripts/cost/build_cost_revision_trails.py`

A project's cost is not one number — it is a **sequence** of dated statements: sanction
estimate → revision(s) → spend-to-date → final outturn. `sanctioned_projects.csv` records the
first point (the FID number); this table records the whole trail, because the *shape* of that
trail is the proof the presentation needs: **did the project cost what its FID number said?**

**37 trail points across 17 projects (v1).** Seven have a full sanction→final trail in a single
currency, so an overrun is directly computable:

| Project | Sanction | Final | Δ |
|---|---:|---:|---:|
| Gorgon | $37.0bn | ~$54.0bn | **+46%** |
| Sangomar Ph1 | $4.2bn | $5.0bn | +19% |
| Mariner | $7.0bn | ~$7.7bn | +10% |
| Jubilee Ph1 | $3.15bn | $3.3bn | +5% |
| TEN | $4.0bn | <$4.0bn | ~0% |
| Peregrino Ph2 | $3.5bn | ~$3.0bn | **−14%** |
| Kraken | $3.2bn | $2.5bn | **−22%** |

The spread (−22% to +46%) is the finding: FID figures are **not** a reliable proxy for outturn,
and the direction is not uniform. USD-reporting mid-caps (EnQuest, Premier) and re-scoped
brownfield projects (Peregrino Ph2) came in **under**; integrated-LNG megaprojects (Gorgon) ran
far over. Mad Dog Phase 2 shows the opposite lever — a **pre-sanction** redesign that cut the
concept estimate 22 → 14 → 9 $bn before FID.

## Rules (mirroring the sanctioned-projects discipline)

- **Currencies are never converted.** A trail lives in one currency; the reconciliation harness
  (E5) compares like-for-like. Martin Linge and Tyra carry parallel USD and NOK/DKK rows because
  the operator stated both.
- **`PROVENANCE` tier is explicit per point:** `operator` / `partner_sec` / `partner_asx` /
  `regulator` / `trade_press`. A `trade_press` point with `CONFIDENCE = low` marks an outturn
  that is widely reported but not operator-attributed — it is honest about being an approximate
  endpoint, never dressed as a disclosed figure.
- **`IN_SANCTIONED_SET`** flags whether the project has a row in `sanctioned_projects.csv`.
  Pluto (AUD-native) and Catcher (outturn-only) are `False`: their FID figure did not meet the
  USD/attribution import bar, but their **trail** is still a valid, sourced observation — and
  Catcher is one more sub-sanction outturn.

## What v1 defers (documented follow-up)

The Norwegian **NOK regulator-tier trails** — Johan Sverdrup Phase 1 (NOK 117bn PDO → downward
revisions), Goliat (NOK 28bn → ~NOK 47-50bn), Aasta Hansteen (NOK 32bn → ~NOK 37.5bn) — need the
per-project investment revisions in NPD / Storting national-budget documents. Those are
regulator-grade and belong here, but the fetching pass was interrupted; see the E4 research
record. Several `trade_press` endpoints (Gorgon ~$54bn, Mariner ~$7.7bn, Martin Linge ~NOK 63bn,
Tyra ~DKK 27bn, Culzean ~$4bn) would upgrade to operator/regulator tier with the same pass.
