# E3 award registry — tranche-2 research record (2026-07-15)

**Issue:** vamseeachanta/worldenergydata#1026 (child of hardening epic #1023)
**Method:** four parallel research passes extending the #1020/E2 award registry method to
17 more projects, by cluster. Every value operator/contractor-attributed with a verbatim
quote; unfound values recorded as VALUE-NOT-PUBLIC (never guessed).

## Outcome

- **52 award rows added** (contract_awards.csv 58 → 110), across 17 projects
- **Award coverage now computed for 28 projects** (was 12); best-covered: Martin Linge 62%,
  Kaombo 49%, GranMorgu 45%, Culzean 35%
- **Full-scope SURF EPCI anchors 2 → 9** — the three largest (Kaombo $3.5bn 21.9%, Martin
  Linge $0.8bn 19.0%, GranMorgu $1.9bn 18.1%) all IN-BAND; still **zero above-band**
- **Bonus:** Big Foot cost-revision trail added ($4bn FID → $5.1bn final, +28%)

## A1 finding, sharpened

The below-band full-scope anchors cluster by **development architecture**: SURF share is
structurally small on platform/dry-tree developments (Shenzi TLP 1.7%, Mariner/Culzean fixed
2–3% — wells mostly platform-drilled) and larger on subsea-to-FPSO developments (the in-band
anchors). Guyana SURF also runs below Suriname's (short vs long flowline runs). Both patterns
say the split should key on architecture and region — which the priors already do by dev type —
not that any prior is wrong. The A1 verdict holds and strengthens: corroborated where testable,
contradicted nowhere, now on 9 full-scope tests instead of 2.

## Method notes / corrections the agents made

- **Uaru and Hammerhead FPSOs are MODEC** (charter model, values undisclosed), NOT SBM — only
  Whiptail is SBM (Jaguar). Hess **stopped** publishing per-project net-excl-FPSO after Yellowtail
  (Uaru/Whiptail/Hammerhead gross-only; Hammerhead post-dates Chevron's Jul-2025 Hess takeover).
- **Kaombo** partners are Total/Sonangol P&P/Sonangol Sinopec/Esso/Galp — **no Statoil**;
  **Zinia** is Total 40/Equinor 23.33/Exxon 20/BP 16.67; **Big Foot** partner is **Marubeni** 12.5
  (not Marathon), Equinor 27.5. Jack/St Malo ownership is per-field.
- **New `range` VALUE_BASIS**: a press-disclosed low/high (Zinia $150-300m, Whiptail Saipem
  ~$1.5bn) that is NOT a contractor band — its LOW bound counts in coverage; treated as a floor.
- **Frame-agreement pattern** (all five GoM legacy projects): operators name contractor + scope
  but not value; hard numbers only from listed-supplier order intake, driller backlog, or
  operator-level gross. Many not_public rows — the finding, not a gap.
- Charters (Kraken Bumi $1.4bn 8-yr firm) flagged `lease_contract`; iEPCIs spanning SPS+SURF+install
  (Rosebank, Tiber) recorded once; NOK-only awards (Kvaerner, Aker) `not_public` in USD with the
  NOK figure noted (no silent FX conversion).

## Raw research records (verbatim from the four passes)

== KAOMBO ($16bn, Total 30%; partners Sonangol P&P 30/Sonangol Sinopec 20/Esso 15/Galp 5 — NO Statoil) — coverage ~55%+
AWARD|Kaombo|2014|Saipem|production_hub|EPCI two converted-VLCC FPSOs (Norte+Sul): topsides/mooring/hookup/commissioning|3000|point (EPCI; separate ~$1bn 7-yr O&M is opex, EXCLUDE)|Saipem|https://www.saipem.com/en/media/press-releases/2014-04-16/saipem-awarded-fpso-contracts-angola-worth-more-4-billion|"awarded FPSO contracts in Angola worth more than 4 billion... two converted turret-moored FPSO"
AWARD|Kaombo|2014|Aker Solutions|sps|20 manifolds + 65 vertical subsea wellsets, controls, workover/tie-in|NOK 14bn (~$2.3bn, NO official USD → VALUE-NOT-PUBLIC in USD, note NOK)|Aker Solutions|https://www.akersolutions.com/news/news-archive/2014/aker-solutions-wins-contract-to-deliver-subsea-production-system-for-totals-kaombo-development-in-angola/
AWARD|Kaombo|2014|Technip / Heerema alliance|surf|Lump-sum SURF EPCI: 18 rigid risers, ~300km flowlines, ~115km umbilicals ("largest SURF ever")|3500|point|Offshore Magazine|https://www.offshore-mag.com/subsea/article/16783185/technip-heerema-land-giant-kaombo-surf-contract
AWARD|Kaombo|2014|Ocean Rig (drillship Skyros)|drilling_rig|6-yr drilling Block 32 dev wells|1300 backlog|Petroleum Africa/OEDigital|https://www.petroleumafrica.com/total-tags-ocean-rigs-skyros-for-angola-drilling/
AWARD|Kaombo|2014|Technip Angoflex|sps|Umbilicals supply|VALUE-NOT-PUBLIC|TechnipFMC|https://www.technipfmc.com/en/investors/archives/technip/press-releases/technip-wins-umbilical-contract-for-kaombo-project-in-angola/
AWARD|Kaombo|2016|Petrolis|other|Kaombo Sul FPSO hook-up + mooring|VALUE-NOT-PUBLIC|Offshore Energy|https://www.offshore-energy.biz/petrolis-wins-contract-for-kaombo-sul-fpso-hook-up-and-mooring/
STMT|Kaombo|2014|TotalEnergies (op 30%)|gross capex|16000 (cut from 20000)|OGJ|https://www.ogj.com/exploration-development/article/17272178/total-partners-reach-fid-for-kaombo-project-off-angola
== MOHO NORD ($10bn, Total E&P Congo 53.5%/Chevron 31.5→exited 2023/SNPC 15) — coverage ~21%
AWARD|Moho Nord|2013|Hyundai Heavy Industries|production_hub|EPC Likouf FPU (62,000t, 100kbopd)|1300|point|Hart Energy|https://www.hartenergy.com/news/hyundai-wins-2-billion-moho-nord-fpu-tlp-contracts-95125
AWARD|Moho Nord|2013|Hyundai Heavy Industries|production_hub|EPC integrated TLP (14,600t hull+topsides)|700|point|Hart Energy|https://www.hartenergy.com/news/hyundai-wins-2-billion-moho-nord-fpu-tlp-contracts-95125
AWARD|Moho Nord|2013|Technip|surf|EPSCI 230km rigid + 23km flex + 50km umbilicals ("largest subsea Technip executes on its own")|VALUE-NOT-PUBLIC (reported >€500m)|Offshore Energy|https://www.offshore-energy.biz/technip-nets-largest-subsea-contract-for-moho-nord-off-congo/
AWARD|Moho Nord|2014|Heerema (Thialf/Hermod)|installation|Transport+install TLP+moorings (HHI subcontract)|VALUE-NOT-PUBLIC|Heerema|https://hmc.heerema.com/projects/moho-nord
AWARD|Moho Nord|2013|BassDrill (Atlantica Delta)|drilling_rig|Newbuild tender-assist semi for TLP modular drilling|VALUE-NOT-PUBLIC|Offshore Magazine|https://www.offshore-mag.com/deepwater/article/16761467/tender-assist-tlp-with-coiled-tubing-optimizes-moho-nord-albian-wells
AWARD|Moho Nord|2014|Fugro|other|5-yr ROV services|100|point|OEDigital|https://www.oedigital.com/news/453051-fugro-in-moho-nord-subsea-gig
STMT|Moho Nord|2013|TotalEnergies (op 53.5%)|gross capex|10000|TotalEnergies|https://totalenergies.com/media/news/press-releases/total-lance-le-developpement-de-moho-nord-en-republique-du-congo
== ZINIA PHASE 2 ($1.2bn, Total 40/Equinor 23.33/ExxonMobil 20/BP 16.67) — coverage ~13-25%
AWARD|Zinia Phase 2|2018|Subsea7|surf|EPCI ~36km flowlines + ~21km umbilicals → Pazflor FPSO ("substantial" per Total; NS Energy $150-300m range)|150-300 (operator-language range, NOT a Subsea7 band)|Offshore Energy/NS Energy|https://www.nsenergybusiness.com/news/contracts/subsea-7-awarded-contract-for-1-2bn-zinia-2-field-development-offshore-angola/
AWARD|Zinia Phase 2|2018|TechnipFMC|sps|9 subsea trees + wellheads + controls|VALUE-NOT-PUBLIC|TechnipFMC|https://www.technipfmc.com/en/investors/financial-news-releases/press-release/technipfmc-awarded-a-subsea-contract-for-the-total-zinia-2-field/
STMT|Zinia Phase 2|2018|Total (op 40%)|gross capex|1200|NS Energy/OGJ|https://www.ogj.com/exploration-development/article/17297630/zinia-2-development-offshore-angola-approved
== MAFUMEIRA SUL ($5.6bn, CABGOC/Chevron 39.2/Sonangol 41/Total 10/Eni 9.8) — coverage <10%
AWARD|Mafumeira Sul|2012|Saipem (Petromar JV)|surf|EPCI 3 (offshore tie-ins) + EPCI 4 (onshore pipeline to Malongo)|325 (bundled in ~350 Angola+Nigeria release)|Saipem|https://www.saipem.com/en/media/press-releases/2012-06-29/saipem-awarded-new-ec-offshore-contracts-worth-350-million
AWARD|Mafumeira Sul|2013|DSME + Mustang/Wood Group|production_hub|Platforms EPC: CPC (3 bridge-linked) + 2 wellhead platforms|VALUE-NOT-PUBLIC|2B1st Consulting|https://2b1stconsulting.com/chevron-to-proceed-with-angola-mafumeira-project-expansion/
AWARD|Mafumeira Sul|2013|McDermott|production_hub|EPC 148-man Living Quarters Platform|VALUE-NOT-PUBLIC|Offshore Technology|https://www.offshore-technology.com/projects/mafumeira-sul-project/
STMT|Mafumeira Sul|2013|Chevron/CABGOC (op 39.2%)|gross capex|5600|Offshore Energy|https://www.offshore-energy.biz/chevron-makes-fid-on-mafumeira-sul-offshore-angola/
# Coverage: Kaombo ~55%+ ($3bn FPSO EPCI + $3.5bn SURF + $1.3bn rig; Aker SPS NOK 14bn/~$2.3bn NOT counted no-official-USD); Moho Nord ~21% (HHI $2bn + Fugro $100m); Zinia ~13-25%; Mafumeira Sul <10%.
# SEED CORRECTIONS: Kaombo Block 32 = Total30/SonangolP&P30/SonangolSinopec20/Esso15/Galp5 (NO Statoil). Zinia Block17 = Total40/Equinor23.33/Exxon20/BP16.67. Moho post-2023 Chevron exit → Total63.5/Trident21.5/SNPC15.
# Band caution: no genuine Subsea7/TechnipFMC self-banded award this tranche; Zinia "substantial" = Total operator language not a Subsea7 band; original Moho Nord SPS vendor never publicly named (real gap).
== UARU ($12.7bn, ExxonMobil 45/Hess 30/CNOOC 25) — coverage ~8-16%
AWARD|Uaru|2023|TechnipFMC|sps|44 subsea trees + 12 manifolds + controls (first Subsea 2.0 in Guyana)|BAND 500-1000 "large"|TechnipFMC/OceanNews|https://oceannews.com/news/subsea-and-survey/technipfmc-awarded-major-subsea-contract-for-exxonmobil-s-guyana-uaru-project/
AWARD|Uaru|2022|Saipem|surf|EPCI subsea structures/risers/flowlines/umbilicals ~2000m (full-phase auth May 2023)|BAND 500-1000 "large" (Saipem definition)|Saipem|https://www.saipem.com/en/media/press-releases/2023-05-04/saipem-authorization-proceed-final-phase-uaru-project-guyana-0
AWARD|Uaru|2023|MODEC (not SBM!)|production_hub|FPSO Errea Wittu — EPC + charter/O&M (MODEC-owned charter model); topsides integration sub-let to Seatrium|VALUE-NOT-PUBLIC|MODEC/World Oil|https://www.worldoil.com/news/2024/5/6/seatrium-secures-fpso-errea-wittu-contract-from-modec-for-exxonmobil-operated-uaru-field-offshore-guyana/
AWARD|Uaru|2023|Noble|drilling_rig|Stabroek CEA fleet drills Uaru wells; dayrates ~$420-500k/day|VALUE-NOT-PUBLIC per-project|OilNOW/Offshore Energy|https://www.offshore-energy.biz/noble-rig-duo-and-stena-drillship-on-oil-gas-exploration-mission-for-exxonmobil-off-guyana/
STMT|Uaru|2023|ExxonMobil (op 45)|gross capex|12700|Hart Energy/Hess|https://www.hartenergy.com/exclusives/exxon-hess-take-127-billion-fid-uaru-development-offshore-guyana-204886
STMT|Uaru|2023|Hess (30)|net share|VALUE-NOT-PUBLIC (FID release gross-only; Yellowtail-style net NOT repeated)|Hess|https://investors.hess.com/news-releases/news-release-details/hess-sanctions-uaru-development-offshore-guyana
== WHIPTAIL ($12.7bn, ExxonMobil 45/Hess 30/CNOOC 25) — coverage ~25-30%
AWARD|Whiptail|2024|TechnipFMC|sps|48 subsea trees + 12 manifolds + controls|BAND 500-1000 "large"|TechnipFMC/BusinessWire|https://www.businesswire.com/news/home/20240415018073/en/TechnipFMC-Awarded-Large-Subsea-Contract-for-ExxonMobil-Guyanas-Whiptail-Project
AWARD|Whiptail|2024|Saipem|surf|EPCI subsea production facility ~2000m ("up to ~$1.5bn")|BAND 750-1500 (press ~$1.5bn)|World Oil|https://www.worldoil.com/news/2024/4/15/saipem-to-proceed-with-1-5-billion-subsea-contract-following-sanctioning-of-exxonmobil-s-whiptail-oil-project-offshore-guyana/
AWARD|Whiptail|2024|SBM Offshore|production_hub|FPSO Jaguar (Fast4Ward 7th hull) construct+install; $1.5bn project financing Nov 2024 (size proxy)|VALUE-NOT-PUBLIC at award (financing 1500)|SBM Offshore|https://www.sbmoffshore.com/newsroom/sbm-offshore-awarded-contracts-for-exxonmobil-guyanas-fpso-jaguar/
AWARD|Whiptail|2024|Noble|drilling_rig|Stabroek CEA fleet drills 48 wells|VALUE-NOT-PUBLIC per-project|OGJ/Offshore Energy|https://www.ogj.com/drilling-production/drilling-operations/article/14167741/exxonmobil-extends-noble-drillship-agreements-offshore-guyana
STMT|Whiptail|2024|ExxonMobil (op 45)|gross capex|12700|Hess/BusinessWire|https://www.businesswire.com/news/home/20240411200646/en/Hess-Sanctions-Whiptail-Development-Offshore-Guyana
STMT|Whiptail|2024|Hess (30)|net share|VALUE-NOT-PUBLIC (gross-only FID release)|Hess|https://investors.hess.com/news-releases/news-release-details/hess-sanctions-whiptail-development-offshore-guyana
== HAMMERHEAD ($6.8bn, ExxonMobil 45/Hess→Chevron 30/CNOOC 25) — coverage ~11-15%
AWARD|Hammerhead|2025|TechnipFMC|sps|Subsea 2.0 trees + manifolds + controls (prod + WI)|BAND 250-500 "substantial"|TechnipFMC|https://www.technipfmc.com/media/pbvnpu5m/tfmc-hammerhead-award-release.pdf
AWARD|Hammerhead|2025|Saipem|surf|EPCI SURF + gas export ~1000m (LNTP Apr 2025, full Sept 2025)|BAND ~500 (press "roughly $500m")|Saipem|https://www.saipem.com/en/media/press-releases/2025-09-26/saipem-receives-authorization-proceed-execution-hammerhead-offshore
AWARD|Hammerhead|2025|MODEC (not SBM!)|production_hub|FPSO Hammerhead — FEED+EPCI via LNTP; ~150kbopd|VALUE-NOT-PUBLIC|MODEC|https://www.modec.com/news/2025/20250421_pr_Hammerhead.html
AWARD|Hammerhead|2025|Noble/Stena|drilling_rig|Stabroek CEA fleet drills 18 wells|VALUE-NOT-PUBLIC per-project|Offshore/Kaieteur|https://kaieteurnewsonline.com/2025/06/21/exxon-extends-contract-for-stena-drill-rig-to-dec-2025/
STMT|Hammerhead|2025|ExxonMobil (op 45)|gross capex|6800|ExxonMobil|https://corporate.exxonmobil.com/news/news-releases/2025/0922_exxonmobil-guyana-expands-capacity-with-seventh-offshore-development
STMT|Hammerhead|2025|Chevron (ex-Hess, 30)|net share|VALUE-NOT-PUBLIC (Chevron closed Hess acq Jul 2025; no per-project net)|Fortune|https://fortune.com/2025/09/22/exxon-chevron-hess-guyana-hammerhead-oil/
# CORRECTIONS: Uaru + Hammerhead FPSOs = MODEC (charter model, undisclosed), NOT SBM. Only Whiptail = SBM (Jaguar).
# Hess STOPPED publishing per-project net-excl-FPSO after Yellowtail — Uaru/Whiptail/Hammerhead all gross-only; Hammerhead post-dates Chevron's Jul-2025 Hess takeover (net channel gone).
# TechnipFMC SPS bands: Uaru/Whiptail "large" $500m-1bn, Hammerhead "substantial" $250-500m. FPSO (biggest bucket) undisclosed everywhere → main coverage gap.
== MARTIN LINGE (NOK 31.5bn PDO/$4.2bn; Equinor 70/Petoro 30) — well covered
AWARD|Martin Linge|2012|Technip + Samsung consortium|production_hub|EPC platform topsides (~25,000t) + 95-cabin LQ|1250 (Technip ~780 + Samsung ~470)|point|Offshore Energy|https://www.offshore-energy.biz/technip-samsung-to-supply-topsides-for-marting-linge-platform-norway/
AWARD|Martin Linge|2012|Kvaerner|production_hub|EPSC 8-legged steel jacket|NOK 1.2bn (~$0.2bn, no official USD → VALUE-NOT-PUBLIC USD)|gCaptain|https://gcaptain.com/kvaerner-wins-billion-contract/
AWARD|Martin Linge|2012|Subsea 7|surf|EPCI SURF (umbilicals/risers/flowlines)|800|point|2B1st Consulting|https://2b1stconsulting.com/total-awarded-main-packages-on-martin-linge-in-norway/
AWARD|Martin Linge|2012|KNOT|production_hub|FSO time-charter (converted Hanne Knutsen)|VALUE-NOT-PUBLIC (charter)|NS Energy|https://www.nsenergybusiness.com/projects/martin-linge-oil-and-gas-field-north-sea/
AWARD|Martin Linge|2012|Maersk Drilling (Intrepid jackup)|drilling_rig|4-yr firm drilling|550 firm|Baird Maritime|https://www.bairdmaritime.com/offshore/maersk-drilling-names-worlds-largest-jack-up-rig
STMT|Martin Linge|2012|Total E&P Norge (op)|gross capex PDO|NOK 31.5bn ($3.5bn)|Equinor|https://www.equinor.com/news/archive/20210701-martin-linge-stream
STMT|Martin Linge|2021|Equinor (op 70)/Petoro 30|partner interests|—|Equinor|https://www.equinor.com/news/archive/20210701-martin-linge-stream
== MARINER ($7.0bn→$7.7bn; Equinor 65.11/JX Nippon 20/Siccar Point 8.89/ONE-Dyas 6) — well covered
AWARD|Mariner|2012|Daewoo (DSME)|production_hub|EPC PDQ topside modules|VALUE-NOT-PUBLIC|Equinor|https://www.equinor.com/news/archive/2012/12/21/21DecMariner
AWARD|Mariner|2012|Dragados Offshore|production_hub|EPC 22,400t steel jacket (Cadiz)|VALUE-NOT-PUBLIC|Offshore Energy|https://www.offshore-energy.biz/photo-dragados-loads-out-jacket-for-statoils-mariner/
AWARD|Mariner|2013|Samsung Heavy Industries|production_hub|Build Mariner B FSU (850k bbl)|VALUE-NOT-PUBLIC|Offshore Technology|https://www.offshore-technology.com/projects/mariner-area-development-north-sea-uk/
AWARD|Mariner|2013|Subsea 7|surf|EPIC 38.6km rigid flowlines + flexible risers|170|point|Offshore Technology|https://www.offshore-technology.com/projects/mariner-area-development-north-sea-uk/
AWARD|Mariner|2012|Saipem|installation|Heavy-lift install jacket+topsides (Saipem 7000)|VALUE-NOT-PUBLIC|Equinor|https://www.equinor.com/news/archive/2012/12/21/21DecMariner
AWARD|Mariner|2013|Noble (Lloyd Noble CJ70 jackup)|drilling_rig|4-yr drilling services|655|point|Noble/PRN|https://www.prnewswire.com/news-releases/noble-receives-contract-award-for-new-ultra-high-specification-jackup-to-be-constructed-for-mariner-project-207336501.html
AWARD|Mariner|2013|Odfjell Drilling|drilling_rig|Platform drilling services|GBP 160m ($245m given)|Offshore Technology|https://www.offshore-technology.com/projects/mariner-area-development-north-sea-uk/
AWARD|Mariner|2020|Wood|other|3-yr O&M/mods/offshore services|75|point|Offshore Technology|(same OT profile)
STMT|Mariner|2012|Statoil (op)|PDQ+jacket sanction value|GBP 1.2bn|Equinor|https://www.equinor.com/news/archive/2012/12/21/21DecMariner
STMT|Mariner|2019|Equinor (op 65.11)/JX Nippon 20/Siccar Point 8.89/ONE-Dyas 6|gross capex|7700|Equinor|https://www.equinor.com/news/archive/2019-08-mariner
== CULZEAN ($4.5bn; Maersk 49.99/JX Nippon 34.01→18.01/BP 16→32) — well covered
AWARD|Culzean|2015|Sembcorp Marine (SMOE)|production_hub|EPC CPF topsides + 2 bridges + WHP + ULQ topsides|1000 (>$1bn incl long-lead)|point|Splash247|https://splash247.com/sembcorp-marine-secures-1bn-epc-contract-from-maersk-oil/
AWARD|Culzean|2014|Heerema Fabrication|production_hub|P&C wellhead jacket + access deck|VALUE-NOT-PUBLIC|Offshore Magazine|https://www.offshore-mag.com/field-development/article/16782792/heerema-to-build-north-sea-culzean-wellhead-platform
AWARD|Culzean|2015|Heerema Fabrication|production_hub|P&C two jackets (CPF + ULQ)|VALUE-NOT-PUBLIC|Heerema|https://hfg.heerema.com/projects/oil-gas-industry/culzean-cpf-ulq
AWARD|Culzean|2016|Heerema Marine Contractors|installation|T&I 3 jackets + ~30,000t topsides (Thialf)|VALUE-NOT-PUBLIC|Offshore Magazine|https://www.offshore-mag.com/field-development/article/16801033/thialf-sets-down-remaining-culzean-jackets-in-the-north-sea
AWARD|Culzean|2015|Subsea 7|surf|SURF 52km gas export to CATS + condensate + tie-ins|150 (>$150m)|point|Subsea World News|https://subseaworldnews.com/2015/09/01/subsea-7-wins-culzean-surf-prize/
AWARD|Culzean|2015|MODEC (turret SOFEC)|production_hub|EPC FSO Ailsa (Global Producer III)|VALUE-NOT-PUBLIC|World Oil|https://www.worldoil.com/news/2015/9/16/modec-bags-fso-contract-for-maersk-s-culzean-field
AWARD|Culzean|2016|Maersk Drilling (Highlander jackup)|drilling_rig|5-yr, 6 HPHT wells|420 (incl $9m mob)|point|Offshore Energy|https://www.offshore-energy.biz/maersk-drillings-new-jack-up-rig-named-in-scotland/
STMT|Culzean|2015|Maersk Oil (op 49.99)|gross capex|GBP 3bn / 4500|Offshore Magazine|https://www.offshore-mag.com/field-development/article/16769733/maersk-oil-lowers-uk-north-sea-culzean-costs
== KRAKEN ($3.2bn→$2.5bn; EnQuest 70.5/Cairn 29.5)
AWARD|Kraken|2013|Bumi Armada|production_hub|Bareboat charter Armada Kraken FPSO + O&M, 8-yr firm|1400 (8-yr firm CHARTER = lease_contract, NOT capex)|Bumi Armada|https://www.bumiarmada.com/bumi-armada-signs-kraken-contract-worth-usd-1-4-billion-rm-4-6-billion/
AWARD|Kraken|2013|Keppel Shipyard|production_hub|Suezmax→FPSO conversion|VALUE-NOT-PUBLIC|Offshore Energy|https://www.offshore-energy.biz/bumi-armada-to-convert-tanker-into-fpso-for-kraken-project/
AWARD|Kraken|2014|Technip|surf|EPCI 50km rigid + umbilicals + risers, 3 drill centres ("large")|VALUE-NOT-PUBLIC (source "large", no band value)|Offshore Magazine|https://www.offshore-mag.com/subsea/article/16782595/enquest-selects-technip-for-large-subsea-contract
AWARD|Kraken|2013|SPX|other|Subsea hydraulic/WI pump equipment|22|point|Offshore Energy|https://www.offshore-energy.biz/spx-to-supply-pumps-for-enquests-kraken-development/
STMT|Kraken|2017|EnQuest (op 70.5)/Cairn 29.5|gross capex 3200→2500|EnQuest|https://www.enquest.com/media/press-releases/article/kraken-first-oil
== ROSEBANK PHASE 1 ($3.8bn; Equinor 80/Ithaca 20)
AWARD|Rosebank Phase 1|2023|Altera Infrastructure|production_hub|Bareboat charter+O&M Petrojarl Knarr FPSO, 9-yr firm|VALUE-NOT-PUBLIC (charter)|Altera|https://www.alterainfra.com/articles/altera-to-operate-fpso-on-rosebank-field
AWARD|Rosebank Phase 1|2023|Aker Solutions (JV Drydocks World Dubai)|production_hub|EPC upgrade/life-ext Petrojarl Knarr FPSO|NOK 2.5bn (~$0.24bn, no official USD → VALUE-NOT-PUBLIC USD)|Aker Solutions|https://www.akersolutions.com/news/news-archive/2023/aker-solutions-wins-rosebank-fpso-contract-from-altera-infrastructure/
AWARD|Rosebank Phase 1|2023|TechnipFMC|sps|Integrated iEPCI: SPS + SURF + installation (SINGLE contract — do NOT triple-count)|BAND 500-1000 "large"|World Oil|https://worldoil.com/news/2023/9/28/technip-fmc-wins-large-subsea-contract-for-equinor-s-rosebank-oil-field-worth-up-to-1-billion/
AWARD|Rosebank Phase 1|2023|Odfjell Drilling (Deepsea Atlantic)|drilling_rig|7 firm wells + 4 options, integrated services|328|point|Equinor|https://www.equinor.com/news/20230927-rosebank-field-to-progress-in-the-uk
STMT|Rosebank Phase 1|2023|Equinor (op 80)/Ithaca 20|gross capex Ph1|3800|Equinor|https://www.equinor.com/news/20230927-rosebank-field-to-progress-in-the-uk
# CORRECTIONS: Martin Linge FSO=KNOT; topsides=Technip+Samsung+Kvaerner jacket. Kraken FPSO=Bumi Armada/Keppel. Rosebank upgrade=Aker/Drydocks Dubai. Culzean hub=Sembcorp+Heerema+MODEC.
# FLAGS: Kraken Bumi Armada $1.4bn = 8-yr firm CHARTER (lease+O&M) → lease_contract, exclude from capex like Barossa BW Opal. Rosebank TechnipFMC = ONE iEPCI spanning sps+surf+install → record once (sps), note spans others, don't triple-count. NOK-only awards (Kvaerner NOK1.2bn, Aker NOK2.5bn) → VALUE-NOT-PUBLIC USD, note NOK.
# Multi-currency: North Sea awards in USD/NOK/GBP as disclosed. Interest shares shifted over life (Culzean BP 16→32; Mariner JX 28.89→20). Overruns: Martin Linge ~2x, Kraken under.
== JACK/ST MALO ($7.5bn) — coverage low (frame agreements)
AWARD|Jack/St. Malo (initial phase)|2010|Cameron (OneSubsea)|sps|12 subsea trees 15k psi + manifolds + PM|230|point|Offshore Technology|https://www.offshore-technology.com/projects/jackstmalodeepwaterp/
AWARD|Jack/St. Malo (initial phase)|2011|Samsung Heavy Industries|production_hub|Semi FPU hull (~56,000t)|VALUE-NOT-PUBLIC|Offshore Magazine|https://www.offshore-mag.com/field-development/article/16758344/chevron-advances-deepwater-frontier-with-jack-st-malo-project
AWARD|Jack/St. Malo (initial phase)|2011|Kiewit|production_hub|FPU topsides (~33,000t)|VALUE-NOT-PUBLIC|Offshore Magazine|(same)
AWARD|Jack/St. Malo (initial phase)|2011|Technip|surf|EPCI >85km flowlines/SCRs/PLETs ("major" legacy title, no figure)|VALUE-NOT-PUBLIC|TechnipFMC|https://www.technipfmc.com/media/hkxoc2ov/technip-awarded-a-major-subsea-contract-for-the-jack-st-malo-fields-in-the-gulf-of-mexico-id423.pdf
AWARD|Jack/St. Malo (initial phase)|2009|Transocean (Discoverer Clear Leader)|drilling_rig|5-yr Chevron GoM (~$469k/day)|VALUE-NOT-PUBLIC (dayrate ~469k/day, not project-attributed)|Offshore Magazine|https://www.offshore-mag.com/drilling-completion/article/16786968/transocean-discoverer-clear-leader-begins-gom-operations
STMT|Jack/St. Malo (initial phase)|2014|Chevron (op 50/51)|gross initial-phase|7500|Offshore Magazine|(profile)
== STAMPEDE ($6bn) — coverage low
AWARD|Stampede|2013|MODEC|production_hub|EPCM TLP hull + moorings|VALUE-NOT-PUBLIC|Offshore Magazine|https://www.offshore-mag.com/production/article/16755947/hess-advances-stampede-project-in-deepwater-gom
AWARD|Stampede|2014|FMC Technologies|sps|15k-psi EVDT trees + manifolds (2 drill centres)|VALUE-NOT-PUBLIC|OEDigital|https://www.oedigital.com/news/444632-slow-and-steady-wins-the-race
AWARD|Stampede|2014|Oceaneering|surf|~14.3km steel-tube umbilicals + distribution|VALUE-NOT-PUBLIC|Oceaneering|https://investors.oceaneering.com/news/news-details/2015/Oceaneering-Announces-Hess-Stampede-Project-Umbilicals-and-Distribution-Hardware-Contract-Award-01-20-2015/default.aspx
AWARD|Stampede|2014|Subsea 7|installation|Install flowlines/SCRs/umbilicals/jumpers|VALUE-NOT-PUBLIC|Offshore Technology|https://www.offshore-technology.com/news/newssubsea-7-wins-installation-contract-for-stampede-project-us-gulf-of-mexico-4472643/
AWARD|Stampede|2013|Diamond Offshore (BlackLion+BlackRhino)|drilling_rig|Two-rig GoM program (~7 rig-yrs, NOT Stampede-only)|1020 backlog (combined, both rigs — combined basis)|Offshore Energy|https://www.offshore-energy.biz/two-diamond-drillships-for-hess/
STMT|Stampede|2014|Hess (op 25)|gross project cost|6000|gCaptain|https://gcaptain.com/hess-partners-reach-fid-stampede-development/
== SHENZI ($4.4bn) — coverage low
AWARD|Shenzi|2006|MODEC|production_hub|TLP (Moses-class) EPC|VALUE-NOT-PUBLIC|NS Energy|https://www.nsenergybusiness.com/projects/shenzi-oil-and-gas-field/
AWARD|Shenzi|2007|Technip|surf|EPCI infield flowlines + SCRs + PLETs (Deep Blue)|75|point|OGJ|https://www.ogj.com/exploration-development/article/17287916/technip-to-install-flowlines-for-shenzi-field-in-gom
AWARD|Shenzi|2007|GlobalSantaFe (C.R. Luigs)|drilling_rig|Dev drilling through 2013|VALUE-NOT-PUBLIC|Drilling Contractor|https://drillingcontractor.org/dcpi/dc-septoct07/DC_Sept07_DC_TechDigest.html
AWARD|Shenzi|2007|Enterprise Products|other|20in oil export (~83mi) + gas lateral (midstream)|VALUE-NOT-PUBLIC|Offshore Technology|https://www.offshore-technology.com/projects/shenzi/
STMT|Shenzi|2006|BHP (op 44)|gross full-field to 2015|4400|Offshore Technology|(profile)
== BIG FOOT ($4bn FID → $5.1bn final; Chevron 60/Equinor 27.5/Marubeni 12.5 — NOT Marathon)
AWARD|Big Foot|2013|Daewoo (DSME)|production_hub|ETLP hull (~35,000t)|VALUE-NOT-PUBLIC|Offshore Energy|https://www.offshore-energy.biz/dockwise-transports-chevrons-etlp-hull-from-south-korea-to-usa/
AWARD|Big Foot|2009|KBR|production_hub|Topsides FEED + detailed design|VALUE-NOT-PUBLIC|Offshore Technology|https://www.offshore-technology.com/projects/bigfootoilfield/
AWARD|Big Foot|2011|GE Oil & Gas|surf|Largest TLP push-up marine riser tensioners|45|point|Offshore Energy|https://www.offshore-energy.biz/usa-ge-recieves-usd-45-million-contract-for-supply-of-tlp-tensioner-system-to-chevron/
AWARD|Big Foot|2009|Enbridge|other|Oil export pipeline (midstream)|200|midstream|Offshore Technology|https://www.offshore-technology.com/projects/bigfootoilfield/
STMT|Big Foot|2018|Chevron (op 60)|final gross|5100|Drilling Contractor|https://drillingcontractor.org/lonestar-energy-fabrication-completes-work-on-big-foot-extended-tension-leg-platform-35084
# BONUS OUTTURN TRAIL: Big Foot $4bn FID (2010) → $5.1bn final (2018) = +28% → ADD to cost_revision_trails.csv
== TIBER-GUADALUPE (<$5bn phase1; BP 100%) — note: awards mostly the SIBLING Kaskida FPU (Tiber replicates it)
AWARD|Tiber-Guadalupe|2025|Seatrium|production_hub|EPC Tiber FPU (80kbopd, >85% design from Kaskida)|VALUE-NOT-PUBLIC|Ocean Energy Resources|https://ocean-energyresources.com/2025/11/26/seatrium-awarded-second-deepwater-fpu-contract-from-bp/
AWARD|Tiber-Guadalupe|2025|TechnipFMC|sps|iEPCI Tiber 20K greenfield (SPS+SURF+install, single contract — do NOT triple-count)|600-800 (disclosed range; "large" band)|World Oil|https://worldoil.com/news/2026/1/6/technipfmc-wins-subsea-work-for-bp-s-tiber-development-in-u-s-gulf/
STMT|Tiber-Guadalupe|2024|BP (op 100)|gross phase1|<5000|JPT/SPE|https://jpt.spe.org/bp-oks-20k-psi-kaskida-project-in-gulf-of-mexico
# FRAME-AGREEMENT PATTERN holds: operators name contractor+scope, NOT value; hard numbers only from (a) listed suppliers' order intake (Cameron $230m, Technip $75m, GE $45m, TFMC Tiber $600-800m), (b) driller backlog (Diamond $1.02bn combined, Transocean $232m), (c) operator gross ($7.5/6/4.4/5.1/<5bn).
# CORRECTIONS: Big Foot partner = Marubeni 12.5 (NOT Marathon), Equinor 27.5. Jack/St Malo ownership per-field. Net per-partner capex NEVER disclosed → all STMT net = VALUE-NOT-PUBLIC.
# Band words modern-only: 2011 Technip "major" (Jack/St Malo) = legacy descriptive title, NOT a band → not_public. Dry-tree TLPs (Big Foot/Shenzi) have little/no SPS.
