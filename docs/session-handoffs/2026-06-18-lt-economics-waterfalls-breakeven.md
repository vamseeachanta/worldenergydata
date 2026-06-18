# Session Handoff — Lower Tertiary economics: waterfalls, breakeven, full regen

**Date:** 2026-06-18
**Status:** Shipped — **PR #494 MERGED** to `main`.
**Predecessor:** [2026-06-18-lower-tertiary-field-economics.md](2026-06-18-lower-tertiary-field-economics.md) (#485 field economics + #484 3D well-path).

## What shipped (PR #494)

Refinements to the Lower Tertiary field-economics reports, applied to **all 7
producing fields** (Anchor, Big Foot, Cascade Chinook, Jack St Malo, Julia,
Shenandoah, Stones). Kaskida / North Platte / Tiber are exploration-only (no
production timeline → no economics report).

- **Executive summary** — verdict-first headline (terminal NPV vs frozen V30,
  oil/producers/revenue, high-capex driver, trough→recovery arc).
- **NPV waterfalls** (interactive Plotly), built by
  `scripts/lower_tertiary/build_npv_stackup_chart.py`, which **parses the field
  markdown** (no model recompute, no BSEE data needed):
  - *Over-time NPV bridge* — each year's Δ cumulative NPV, biggest swings
    annotated with the events that drove them (plotted on numeric indices with
    relabeled ticks so bars + annotations share one coordinate system).
  - *Per-well NPV stackup* — each well's net NPV stepping to the field total.
  - Output: `reports/lower_tertiary/<slug>_npv_stackup.html` (both charts in one
    file). Registered in `config/repo_structure.yml` (a contract test fails if a
    new generated `reports/` path isn't classified).
- **WTI breakeven + price sensitivity** — new report section.
  `build_field_npv_timeline()` gained a `wti_price_multiplier` arg (default 1.0)
  and now returns `avg_realized_wti_usd` / `oil_bbl_total`. NPV is **affine in
  the price multiplier**, so one base run + one scaled run pin the exact
  NPV-vs-price line and breakeven (NPV = 0). Julia: breakeven **$95/bbl** vs
  realized **$67**, slope **+$17.2M per $1/bbl**.
- **Sparkline anchors**, sharpened per-well ranking note, **first-oil reconcile**
  in `fields/julia.yml` (2019-05 → 2016-03, OGOR-A first production; operator
  flagged unverified), and a **3D well-geometry placeholder** (intentionally
  NOT embedded — see open item #493).
- **Full authoritative regen** of all 14 reports (latest + frozen) on live BSEE
  data + `portfolio_economics.html` rebuilt.

## How to regenerate

```bash
export WED_DATA_ROOT=/path/to/bsee/data-root        # see below
uv run python scripts/lower_tertiary/regenerate_all_field_reports.py   # 14 reports
for d in Anchor "Big Foot" "Cascade Chinook" "Jack St Malo" Julia Shenandoah Stones; do
  uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev "$d"
done
uv run --with markdown python scripts/lower_tertiary/build_portfolio_html.py
```

- **Data:** BSEE bins live on the ace-linux-1 share
  `/mnt/remote/ace-linux-1/ace/worldenergydata/data`. A fast local subset (war
  mains + OGOR yearly + ocsprod, ~940MB) was copied to
  `/mnt/local-analysis/wed-data` (deletable). Minimal set: `bin/war/mv_war_main*.bin`,
  `bin/historical_production_yearly/ogora*delimit.bin`, `bin/ocsprod/`. V30 xlsx
  inputs (`leases.xlsx`, `lease_assumptions.xlsx`, `drilling_and_completion_days.xlsx`,
  `wti_monthly.xlsx`) are in-repo under `docs/modules/bsee/analysis/production/FDAS_V30/`.
- **Network:** latest-window runs fetch ~9 tail months of WTI from EIA GitHub.
- **PR title check:** repo enforces conventional-commit PR titles
  (`amannn/action-semantic-pull-request`, types feat/fix/docs/…).

## Open items

1. **worldenergydata#493** — the 3D well-path demo
   (`scripts/bsee/demo_well_path_julia.py`) selects wells by `WELL_NAME` "JU"
   prefix and grabs the wrong 1989/1994 *Ship Shoal* wells; API `608124009400`
   is **DC101** in the economics model but **JU101** in the curated catalog
   (collision). **Fix:** select by lease G20351 (as the economics report does),
   reconcile the API identity, then embed the 3D paths into
   `field_economics_julia.md` (replace the placeholder).
2. **FDAS demo video** (deckhand-sandbox, `feat/marketing-cta-polish`): spec
   `marketing/gif-pipeline/specs/fdas-field-npv.json` updated to feature
   breakeven/sensitivity/waterfalls + a "real public BSEE data" proof beat;
   onboarding CTA already wired (`build-web-v3.mjs` START_HERE). Committed
   **locally** (`471093c`, UNPUSHED, alongside unrelated WIP). Render +
   publish are operator-gated: `SLUGS=fdas-field-npv bash render-all.sh` then
   `gh release upload`.

## Client-shareable links (public)

- Portfolio (interactive): `https://htmlpreview.github.io/?https://github.com/vamseeachanta/worldenergydata/blob/main/reports/lower_tertiary/portfolio_economics.html`
- Reports + charts: `https://github.com/vamseeachanta/worldenergydata/tree/main/reports/lower_tertiary`
