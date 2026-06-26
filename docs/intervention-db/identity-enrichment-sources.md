# Vessel Identity Enrichment — Public Source Registry (#619)

> **Status:** scaffold for automated IMO / aka / operator enrichment of the
> dedicated-intervention fleet. Child of epic #591; feeds the #599 identity
> resolver. The bulk vessel corpus has ~0% IMO coverage, so identity must be
> enriched from PUBLIC registries.

This sheet lists the **public** registries usable to enrich vessel identity
(IMO / MMSI / former-names / owner-operator) for the named intervention units.
The first pass (#619) was done by **manual, cited web research** against public
ship pages (per-field `source_url` + `identity_confidence` in the two YAMLs).
The registries below are the path for **future automated bulk enrichment**.

**Hard rule (carried from #593 / #598):** an IMO is recorded only when a public
page confirms it. Unknown IMO is `null`, **never** guessed. US-flagged Jones-Act
OSVs frequently carry a USCG *official number* but **no IMO** — for those, `imo`
stays `null` and the absence is expected, not a gap.

---

## Bulk public registries

| Source | Access tier | What it yields | Notes |
|---|---|---|---|
| **Equasis** (equasis.org) | Free account required | IMO, flag, class society, owner/manager/ISM company, P&I, port-state-control history | Repo already has `vessel_fleet/collectors/equasis_collector.py`. Rate-limit ~1 req / 3 s. Keyed by IMO **or** name search. Best single source for owner/operator chains and former managers. No bulk download — per-ship lookups only. |
| **GISIS** (gisis.imo.org) — IMO Ship & Company particulars | Free IMO Web Account (1–2 day approval) | Authoritative IMO number, ship name history (renames → **aka**), flag, GT, company particulars | The system of record for the IMO number itself and for the official name history. See `docs/IMO_GISIS_DOWNLOAD_SETUP.md` for the authenticated Selenium download harness already in-repo. |
| **USCG PSIX / Vessel Documentation** (cgmix.uscg.mil/PSIX, cgmix port-state) | Public, no account; bulk DB available | USCG **official number**, hull/build, owner/operator, US flag status | Authoritative for US-flagged OSVs (Oceaneering MSVs, Candies, Bordelon units). **Many US OSVs have an official number but NO IMO** — use PSIX to confirm the official number and record `imo: null` deliberately. Bulk dataset downloadable (no per-ship rate limit). |

## Free public AIS / vessel pages (manual citation tier — used in #619)

These were used to cite individual IMOs in the first pass. They are **public
result pages**, not bulk feeds, and are fine for manual per-vessel citation:

- **balticshipping.com** — IMO, MMSI, build year, former names; stable per-ship URLs.
- **vesselfinder.com** (public ship page) — IMO, MMSI, flag, type.
- **marinetraffic.com** (public ship page) — IMO, MMSI, current position/flag.
- **Wikipedia** — for well-documented units (Helix Q-series, ex-Skandi Aker) with cited build/rename history.
- **Operator / shipyard pages** — Helix (helixesg.com), Ulstein/Vard references, AKOFS, DOF fleet pages — for owner/operator confirmation (not for the IMO number itself).

## Recommended automated pipeline (future work, #599+)

1. **Seed by name** from the two roster YAMLs.
2. **GISIS** lookup → authoritative IMO + full name history (populate `aka`).
3. **Equasis** lookup (existing collector) → owner / manager / ISM company chain.
4. **USCG PSIX** join for US-flagged units → official number; assert `imo: null` where none exists.
5. Write back `imo` / `mmsi` / `aka` / `operator` with `identity_source` + `identity_confidence`; feed the #599 resolver to collapse renames.

**Do not scrape credentialed sources in CI.** Equasis and GISIS require accounts
and have rate limits / terms; run those collectors only in an attended,
credentialed job, never in the test path.
