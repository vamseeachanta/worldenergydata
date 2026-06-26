# Frontier Deepwater Basins — Discovery Dataset

Discovery-level catalog of the three frontier deepwater oil plays that are
reshaping global exploration and absorbing the high-day-rate deepwater drillship
fleet: **Guyana** (Stabroek + adjacent blocks), **Suriname** (Block 58 + adjacent
blocks), and **Namibia** (Orange Basin). Prompted by issue #603.

This module is the discovery-level companion to the basin-level
`worldenergydata.canada.emerging_basins` watch list (one stub per basin). It
follows the curated-CSV source-of-truth + per-row source attribution +
confidence-tier pattern used by the `subsea` and `vessel_fleet` datasets.

- **Source of truth:** [`curated/frontier_discoveries.csv`](curated/frontier_discoveries.csv)
- **Schema / loader:** `worldenergydata.canada.emerging_basins.discovery_schema.DiscoverySchema`
  and `FrontierDiscoveryLoader`
- **Rebuild:** `uv run python scripts/build_frontier_basins_db.py`
- **Records:** 51 discoveries (38 high / 9 medium / 4 low confidence)
- **Collected:** 2026-06-26

## Confidence tiers

| Tier | Meaning |
|------|---------|
| `high` | Operator-confirmed (company press release / FID statement) |
| `medium` | Reputable secondary (Reuters / Offshore Magazine / OGJ / Rigzone / trade press) |
| `low` | Analyst estimate only, in-place-only figure, or commerciality unconfirmed |

## Resource-figure caveats (read before using volumes)

Per-discovery **recoverable** volumes are mostly **not publicly disclosed**.
Treat the dataset's `RESOURCE_ESTIMATE` / `RESOURCE_BASIS` carefully:

- **Guyana / Stabroek:** ExxonMobil does **not** publish per-discovery recoverable
  volumes — finds roll only into the **block-level aggregate of ~11 billion boe**
  (stated Apr 2022, not officially revised since despite later discoveries). The
  only discrete figures are Liza (>1 Bboe) and Turbot+Longtail combined (>500 MMboe).
- **Suriname / Block 58 GranMorgu:** the **>750 million barrels recoverable** figure
  is TotalEnergies' **combined** Sapakara South + Krabdagu development volume
  (FID 1 Oct 2024, ~US$10.5 B, 220,000-bopd FPSO, first oil targeted 2028) — it is
  carried on **both** component-field rows and is not a per-well figure.
- **Namibia / Venus:** TotalEnergies' **~750 MMbbl recoverable is a Phase-1**
  development-concept figure. Frequently-quoted "~2 billion bbl recoverable" /
  larger oil-in-place numbers are **analyst estimates, unconfirmed by the operator**.
- **Namibia / Mopane:** Galp's headline **"up to 10 billion boe" is IN-PLACE**
  (`RESOURCE_BASIS = in_place`), **not recoverable** and not reserves.
- **Namibia / Shell PEL 39 (Graff, La Rona, Jonker, Cullinan, Lesedi):** multiple
  oil hits, but Shell took a **~US$400 M write-down in 2025** citing commerciality /
  reservoir difficulties — hence the `low`/`medium` grading despite the discoveries.
- Where only net hydrocarbon **pay thickness** was disclosed (common in Suriname),
  `RESOURCE_BASIS = net_pay`.

## Coverage by play

### Guyana (Guyana-Suriname basin)
- **Stabroek** (ExxonMobil 45% op / Hess 30% → Chevron Jul 2025 / CNOOC 25%): 25
  discoveries (Liza, Liza Deep, Payara, Snoek, Turbot, Ranger, Pacora, Longtail,
  Hammerhead, Pluma, Tilapia, Haimara, Yellowtail, Tripletail, Mako, Uaru, Pinktail,
  Cataback, Whiptail, Fangtooth, Lau Lau, Sailfin, Yarrow, Lancetfish, Bluefin).
  Sanctioned/producing FPSOs: Liza Destiny (2019), Liza Unity (2022), Prosperity/
  Payara (2023), ONE GUYANA/Yellowtail (2025), Uaru/Errea Wittu (~2026), Whiptail/
  Jaguar (~2027), Hammerhead (~2029).
- **Adjacent:** Kaieteur (Tanager-1, sub-commercial), Orinduik (Jethro-1, Joe-1,
  heavy oil sub-commercial), Corentyne (Kawa-1, Wei-1, CGX/Frontera light-oil finds).

### Suriname (Guyana-Suriname basin)
- **Block 58** (TotalEnergies 50% op / APA 50%; Staatsolie up to 20% on GranMorgu):
  Maka Central-1, Sapakara West-1, Kwaskwasi-1, Keskesi East-1, Sapakara South,
  Krabdagu-1, Bonboni-1 (non-commercial).
- **Block 52** (Petronas 50% op / ExxonMobil 50%): Sloanea-1, Roystonea-1, Fusaea-1.
- **Block 53** (APA 45% op / Petronas 30% / CEPSA→TotalEnergies 25%): Baja-1.

### Namibia (Orange basin)
- **PEL 39 / Block 2913A** (Shell 45% op / QatarEnergy 45% / NAMCOR 10%): Graff-1,
  La Rona-1, Jonker-1X, Cullinan-1X, Lesedi-1X (commerciality uncertain, 2025 write-down).
- **PEL 56 / Block 2913B** (TotalEnergies 45.25% op / QatarEnergy 30% / Impact 9.5% /
  NAMCOR 10%): Venus-1X.
- **PEL 83 / Block 2813A** (Galp 80% op / NAMCOR 10% / Custos 10%; TotalEnergies
  farming in as operator): Mopane.
- **PEL 85 / Block 2914** (Rhino Resources 42.5% op / Azule Energy 42.5% / NAMCOR 10%
  / Korres 5%): Capricornus 1-X (flow-tested light oil), Sagittarius 1-X, Volans-1X
  (gas-condensate).

## Known gaps / `[unverified]` figures

- Most **per-discovery recoverable volumes are not public** (see caveats above).
- **Water depths not disclosed** for: Liza Deep, Tanager-1, Kwaskwasi-1, Sapakara
  South, Bonboni-1, Sloanea-1, Fusaea-1, and the Namibia wells La Rona-1, Cullinan-1X,
  Lesedi-1X, Sagittarius-1X, Capricornus-1X, Volans-1X. These rows leave
  `WATER_DEPTH_M` blank rather than guessing. (For some Suriname/Namibia wells public
  sources report **total/measured well depth (TD)**, which must not be conflated with
  water depth, so it is excluded.)
- The Graff+La Rona+Jonker "~1.7 Bboe" figure is **secondary, of mixed in-place/EUR
  character** — flagged `[unverified]` in the row note.
- **Dry / failed wells excluded** from the catalog (mentioned for completeness only):
  Jabillo-1 & Sapote-1 (Canje, Guyana), Banjo-1 & Kokwari-1 (Stabroek), Dikkop & Awari
  (Block 58, Suriname), Kapana-1X (PEL 90, Namibia, Chevron). Shell Merlin-1X
  (PEL 39, 2026) is too early-stage to catalog.

## Sources

Operator press releases (ExxonMobil, Hess/Chevron, TotalEnergies, APA/Apache,
Petronas, Shell, Galp, Rhino Resources, Staatsolie) plus Oil & Gas Journal, Offshore
Magazine, Offshore-Energy, World Oil, Rigzone, NS Energy, OEDigital, and government /
GlobeNewswire releases. Every row carries its primary `DATA_SOURCE_URL`; see that
column in the CSV for the full per-figure provenance.
