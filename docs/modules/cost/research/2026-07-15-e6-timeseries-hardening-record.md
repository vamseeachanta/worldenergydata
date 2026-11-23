# E6 time-series hardening — research record (2026-07-15)

**Issue:** vamseeachanta/worldenergydata#1029 (child of hardening epic #1023)

Two threads: (A) Norwegian NOK regulator-tier outturn trails — the deferred pass from E4; and
(B) heavy-lift / pipelay vessel day rates — a declared gap in the component time-series.

## A. NOK regulator-tier outturn trails — ADDED (10 points, 4 fields)

Norway's regulator (Sokkeldirektoratet, former NPD) and the Storting (Prop. 1 S budget documents)
publish per-project investment revisions — regulator-grade sources that upgrade the earlier
trade-tier NOK points. Imported into `cost_revision_trails.csv`:

- **Johan Sverdrup Phase 1** (Equinor): PDO ~NOK 123bn → 99bn (2016) → 86bn (2018) → 83bn outturn
  (2019). A **−33% under-run**, the dataset's best, each step an Equinor verbatim; Sokkeldirektoratet
  OD-04-20 corroborates ("savings of 24 per cent").
- **Martin Linge** (Total→Equinor): sanction basis corrected to the **NOK 31.5bn PDO** (Jun 2012);
  Prop. 1 S (2019-2020) reported +NOK 26bn/+85% to NOK 56bn (regulator-tier via OD-04-20) → NOK 63bn
  outturn (2021). **+100%**, the worst overrun.
- **Goliat** (Eni): NOK 28bn PDO (2009) → NOK 46.7bn (Prop. 1 S 2015, +49%) → ~NOK 50bn first oil.
- **Aasta Hansteen** (Equinor): NOK 32bn PDO (2013) → NOK 37.5bn outturn (+17%, within PDO band).

**Effect:** the outturn multiplier distribution now spans **×0.67 (Johan Sverdrup) to ×2.00
(Martin Linge)** — both poles Norwegian and regulator-corroborated.

### Still open (browser-fetch pass)
`regjeringen.no` (St.prp. nr. 64 2008-2009 for the Goliat PDO; annual Prop. 1 S PDFs) returns 403
to automated fetch and a JS shell to curl. An authenticated/browser fetch would lift the exact
Norwegian verbatims (Goliat 2009 ~28bn vs the 31.3bn Teknisk Ukeblad relay; the annual cost lines).
Sokkeldirektoratet Factpages cumulative figures (Goliat 57,013 MNOK, Martin Linge 59,079 MNOK,
Aasta Hansteen 36,798 MNOK) are lifetime spend incl. operations — NOT development outturn; noted,
not used as the delta.

## B. Heavy-lift / pipelay day rates — DECLARED GAP CONFIRMED (not imported)

The component time-series' declared gap is essentially real. No transactional, named-vessel HLV or
pipelay day rate is public for any year:

- Heerema is privately held (no financials). Saipem / Subsea7 / Allseas annual reports disclose only
  fleet-level revenue, EBITDA, backlog and utilisation — never revenue-per-vessel-day. Rates are
  negotiated per project and confidential.
- The only citable figures are **proxies**, kept as leads (NOT imported, per the no-weak-numbers rule):
  Ship Universe trade ranges (HLV $200-400k/day, cable-lay $50-130k/day, 2025); a broker listing
  ($45k/day pipelay barge, 2020); Kaiser & Snyder's 2012 academic model ($60-300k/day self-propelled
  install; $25-150k/day jack-up). All ranges or model estimates, none contemporaneous fixtures.
- **The only real time-series source is S&P Global Commodity Insights "ConstructionVesselBase"**
  (subscription) — a buy-decision if #1029 needs an actual annual HLV/pipelay series rather than a
  documented gap. Contractor annual reports are a structural dead end (fleet-level disclosure only).

Verdict: the declared gap stands, now with the search documented and the one paid path identified.
