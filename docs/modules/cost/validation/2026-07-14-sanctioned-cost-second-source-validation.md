# Second-source validation of sanctioned project costs — 2026-07-14

**Issue:** vamseeachanta/worldenergydata#1019 (pre-circulation gate for #1017)
**Dataset validated:** `data/modules/cost/curated/sanctioned_projects.csv` @ `33666a1a` (40 projects)
**Method:** four parallel research passes, 10 projects each; every USD figure checked against
publishers INDEPENDENT of the already-cited source; every declared gap (NULL) re-searched
for a missed citable figure. Verdicts: CONFIRMED / QUESTIONED / NO-SECOND-SOURCE /
GAP-CONFIRMED / FIGURE-EXISTS.

## Result summary

| Verdict | Count | Meaning |
|---|---|---|
| CONFIRMED | 23 / 23 figures | every USD figure matched by an independent publisher within tolerance |
| QUESTIONED | 0 | no >10% conflicts, no basis mismatches found |
| NO-SECOND-SOURCE | 0 | every figure has at least one independent corroboration |
| GAP-CONFIRMED | 14 / 17 gaps | the NULL is defensible — no operator-attributed USD figure exists |
| FIGURE-EXISTS | 3 / 17 gaps | a citable figure was recovered (see corrections) |

## Corrections adopted from this validation

1. **Tyra Redevelopment — import $3,400MM**: operator parent A.P. Møller-Mærsk Annual Report 2017 states "approx. DKK 21bn (equal to approx. USD 3.4bn)" — an operator-published USD figure (Maersk group reports in USD).
2. **Kaminho — import $6,000MM (concessionaire-stated tier)**: Angola's ANPG stated the figure (Reuters/Globe and Mail verbatim); operator TotalEnergies release is figure-free. Basis records the non-operator attribution.
3. **Coral North FLNG — import ~$7,200MM (regulator-stated tier)**: Mozambique regulator INP states "around 7.2 billion dollars"; operator Eni release figure-free. Approximate figure, basis records attribution.
4. **Mad Dog Phase 2 — FID year 2017 → 2016**: BP announced sanction 1 Dec 2016 (BHP partner approval Feb 2017). The $9,000MM figure itself is solid (BP + OGJ + BHP-share cross-check: $2.2bn / 23.9% ≈ $9.2bn gross).
5. **Coral South — add note**: Eni's own financing disclosure ($4.675bn covering ~60%) implies ~$7.8bn total; recorded as a NOTE, not a figure.

## Patterns worth keeping

- **Norwegian/UK operators sanction in local currency only**; trade-press USD "figures" are unflagged FX conversions disagreeing 10–25% across publishers. Policy: local-currency-only ⇒ NULL USD, keep the local figure in the basis note.
- **Operators increasingly withhold capex at FID while host-state agencies disclose it** (ANPG — Kaminho, likely Greater PAJ; INP — Coral North). A concessionaire/regulator-stated tier recovers real figures with honest attribution.
- **Partner disclosures are a validation channel**: BHP's Mad Dog share, Hess's Liza statements, Noble's Leviathan 8-K, Navitas's Shenandoah budget — partner net ÷ interest ≈ gross. (Being systematized in #1020.)
- **Shell never discloses GoM FID capex** (Appomattox, Vito, Whale, Sparta — all confirmed undisclosed).

## Full verdict record (verbatim from the four research passes)

1|Clair Ridge|GAP-CONFIRMED|n/a|Oilfield Technology (reproducing BP announcement) — https://www.oilfieldtechnology.com/drilling-and-production/13102011/bp_receives_government_approval_for_clair_ridge_project/|BP's own 2011 announcement is GBP-only ("£4.5 billion"); USD figures in trade press are inconsistent conversions ($5.7bn vs ~$7bn), none from the operator — NULL stands.
2|Ichthys LNG|CONFIRMED|34000|TotalEnergies press release (24% partner, 13 Jan 2012) — https://totalenergies.com/media/news/press-releases/australie-total-et-inpex-lancent-ichthys-projet-strategique-de-gnl-offshore|Partner Total states US$34 billion for the full integrated project at FID — exact basis match.
3|Stampede|CONFIRMED|6000|Hess Corporation press release (28 Oct 2014) — https://investors.hess.com/news-releases/news-release-details/hess-announces-plan-develop-stampede-field-deepwater-gulf-mexico|Operator: "total project cost is expected to be approximately $6 billion" (gross, all co-owners) — exact match.
4|Appomattox|GAP-CONFIRMED|n/a|Shell Global media release (1 Jul 2015) — https://www.shell.com/media/news-and-media-releases/2015/shell-takes-final-investment-decision-appomattox.html|Shell gives only relative figures (cost "reduced 20%" pre-FID; "40% below" 2015 budget at startup), never an absolute USD total; $9bn-class numbers are analyst estimates — NULL stands.
5|Coral South FLNG|GAP-CONFIRMED|n/a|Offshore Energy — https://www.offshore-energy.biz/eni-closes-4-7-billion-coral-south-flng-project-financing/|Eni stated only $4.675bn project financing covering ~60% of cost (implies ~$7.8bn, never stated as total); trade press splits $7bn/$8bn without operator attribution — NULL stands; implied range worth a note.
6|Johan Castberg|GAP-CONFIRMED|n/a|Equinor news release (5 Dec 2017) — https://www.equinor.com/news/archive/05dec2017-johan-castberg|Operator PDO is NOK-only (NOK 49bn); USD figures are publications' own conversions; later restatements also NOK-only — NULL stands.
7|Leviathan Phase 1|CONFIRMED|3750|Noble Energy Form 8-K, SEC EDGAR (23 Feb 2017) — https://www.sec.gov/Archives/edgar/data/0000072207/000007220717000018/nbl8-kleviathansanction.htm|Operator 8-K: estimated gross Phase 1 capital $3.75bn ($1.5bn net to Noble) — basis matches.
8|Liza Phase 1|CONFIRMED|4400|Hess via Business Wire (16 Jun 2017) — https://www.businesswire.com/news/home/20170616005327/en/Hess-Takes-Final-Investment-Decision-Liza-Phase|Co-venturer Hess states just over $4.4bn incl. ~$1.2bn FPSO lease capitalization — exact basis match; also OGJ.
9|Mad Dog Phase 2 (Argos)|CONFIRMED|9000|Oil & Gas Journal — https://www.ogj.com/drilling-production/article/17250478/bp-sanctions-mad-dog-phase-2-project-in-gulf-of-mexico|BP-attributed $9bn gross at sanction; cross-checked by BHP's US$2.2bn for 23.9% share (implies ~$9.2bn gross). METADATA CORRECTION: BP sanction announced 1 Dec 2016, not 2017 (BHP approval Feb 2017).
10|Tyra Redevelopment|FIGURE-EXISTS|3400|A.P. Møller - Mærsk Annual Report 2017 (operator's parent) — https://investor.maersk.com/system/files-encrypted/nasdaq_kms/assets/2018/04/25/13-00-21/A.P._Moller_-_Maersk_Annual_Report_2017.pdf|VERBATIM: "Danish Underground Consortium, where Maersk Oil is the operator, approved an investment of approx. DKK 21bn (equal to approx. USD 3.4bn) in the full redevelopment of the Tyra gas field" — operator-published USD figure exists (Maersk group reports in USD).
# GBP/NOK operators never issued USD at FID (Clair Ridge, Castberg — gaps hold), but DKK-based Tyra has an operator USD figure via the parent's USD-currency annual report.
# Mad Dog Phase 2 date correction: sanction 1 Dec 2016; $9bn solid across BP, OGJ, and the BHP partner-share cross-check.
# Coral South: Eni's own financing disclosure implies ~$7.8bn — defensible as a NOTE, not a figure.
11|Greater Tortue Ahmeyim Phase 1|GAP-CONFIRMED|n/a|World Oil (BP FID release reprint) — https://www.worldoil.com/news/2018/12/21/bp-announces-fid-for-phase-1-of-the-cross-border-greater-tortue-ahmeyim-development|BP's FID announcement contains no cost figure; $4.6–4.8bn figures (GEM, NS Energy, Upstream 2021) are unattributed trade estimates or post-FID revisions — NULL stands.
12|Johan Sverdrup Phase 2|GAP-CONFIRMED|n/a|Maritime Executive — https://maritime-executive.com/article/johan-sverdrup-estimate-increased-costs-cut|Equinor 27 Aug 2018 release states investment ONLY as "NOK 41 billion (nominal NOK, project exchange rate)"; trade-press USD figures are publishers' own FX conversions varying $4.7–5.0bn — NULL stands.
13|Karish & Tanin|CONFIRMED|1600|Kerogen Capital (Energean announcement reprint) — https://kerogencap.com/news/energean-takes-fid-karish-tanin-gas-project/|Verbatim "$1.6 billion Karish & Tanin development" from Energean's FID announcement (partner-hosted reprint; energean.com 403) — basis matches.
14|Vito|GAP-CONFIRMED|n/a|Natural Gas Intelligence — https://naturalgasintel.com/news/shell-oks-fid-for-long-awaited-vito-development-in-deepwater-gom/|Shell's FID release gives no capex; trade press explicitly noted Shell had not revealed cost, only "<$35/bbl breakeven" and ">70% cost reduction vs original concept".
15|Anchor|CONFIRMED|5700|Chevron press release — https://www.chevron.com/newsroom/2019/q4/chevron-sanctions-anchor-project-in-the-deepwater-us-gulf-of-mexico|Operator: "investment of approximately $5.7 billion", Stage 1 = seven-well subsea + semi FPU — exact basis match.
16|Balder X / Balder Future|GAP-CONFIRMED|n/a|Norwegian Petroleum Directorate — https://www.npd.no/en/whats-new/news/general-news/2019/Increasing-recovery-from-the-Balder-field/|Original Dec 2019 PDO estimate verbatim only in NOK ("NOK 19.6 billion" per NPD); USD $2.1–2.16bn are trade FX conversions; USD 4.3bn is post-review REVISED cost — NULL stands.
17|Liza Phase 2|CONFIRMED|6000|OilNow — https://oilnow.gy/featured/exxonmobil-to-proceed-with-us6-billion-liza-phase-2-project-in-guyana/|"US$6 billion" incl. ~$1.6bn Liza Unity FPSO lease capitalization — same basis; also Offshore Energy + OE Digital.
18|Breidablikk|GAP-CONFIRMED|n/a|OE Digital — https://www.oedigital.com/news/482001-equinor-to-sanction-1-95b-breidablikk-development-in-north-sea|Operator stated NOK 18.6bn only; USD conversions scatter $1.74–2.2bn across publishers — no defensible operator USD figure.
19|Payara|CONFIRMED|9000|Offshore Technology — https://www.offshore-technology.com/news/exxonmobil-fid-payara-development-guyana/|"$9bn Payara development" at Sep/Oct 2020 FID, third Stabroek phase, 41 wells — same basis; also JPT/SPE.
20|Sangomar Phase 1|CONFIRMED|4200|Oilfield Technology (citing Reuters) — https://www.oilfieldtechnology.com/offshore-and-subsea/26032020/sangomar-project-partners-deliberating-timing/|"US$4.2 billion Sangomar oil project" post-Jan 2020 FID, Phase 1 only — matches; final Phase 1 cost later ~$5.0bn (Woodside 2025) so $4.2bn correctly the FID-time figure.
# All 5 non-NULL figures CONFIRMED; all 5 NULLs GAP-CONFIRMED — disclosure judgments held up under second-sourcing.
# Norwegian pattern: operators sanction in NOK only; trade-press USD "figures" are unflagged FX conversions disagreeing 10–25% across publishers — NOK-only ⇒ NULL-USD is the defensible policy.
# Fetch caveats: bp.com and energean.com 403; operator statements verified via faithful reprints (World Oil, Kerogen Capital).
21|Bacalhau Phase 1|CONFIRMED|8000|Oil & Gas Journal — https://www.ogj.com/exploration-development/article/14204366/equinor-partners-reach-fid-for-bacalhau-phase-1-development-in-brazil|OGJ and Rigzone both state $8bn phase 1 FID investment, 19 subsea wells + FPSO — same gross-at-FID basis, exact match.
22|Barossa|CONFIRMED|3600|Rigzone — https://www.rigzone.com/news/santos_takes_fid_on_36b_barossa_project-31-mar-2021-165038-article/|Rigzone and Offshore Energy state $3.6bn gross FID with the $600MM Darwin LNG life-extension reported as separate — basis matches exactly.
23|Scarborough (incl. Pluto Train 2)|CONFIRMED|12000|Wood Mackenzie — https://www.woodmac.com/press-releases/woodside-sanctions-us$12-billion-scarborough-and-pluto-train-2-project/|WoodMac states "US$12 billion" at Nov-2021 sanction (100% basis); later growth to $12.5bn is post-FID revision, not a FID-basis conflict.
24|Shenandoah|CONFIRMED|1800|Navitas Petroleum (JV partner) — https://www.navitaspet.com/project/the-shenandoah-field/|Partner states "total budget USD 1.8 billion (for 100%)"; the $900MM figure elsewhere is a financing tranche (debt), not capex.
25|Whale|GAP-CONFIRMED|n/a|Shell press release — https://www.shell.com/media/news-and-media-releases/2021/shell-invests-in-the-whale-development-in-the-gulf-of-mexico.html|Shell FID release + all trade coverage disclose IRR >25% and 490 MMboe but no USD capex — NULL defensible.
26|Ballymore|CONFIRMED|1600|Chevron press release — https://www.chevron.com/newsroom/2022/q2/chevron-sanctions-ballymore-project-in-deepwater-us-gulf-of-mexico|Operator + Offshore Magazine both state $1.6bn at May-2022 sanction, 3-well tieback to Blind Faith — exact basis match.
27|Yellowtail|CONFIRMED|10000|World Oil — https://www.worldoil.com/news/2022/4/4/exxonmobil-moves-forward-with-10-billion-guyana-offshore-oil-project/|World Oil and gCaptain state $10bn for fourth Stabroek development (26 prod + 25 inj = 51 wells) — matches.
28|Agogo Integrated West Hub|GAP-CONFIRMED|n/a|Azule Energy press release (PDF) — https://www.azule-energy.com/wp-content/uploads/2023/02/PRESS-RELEASE-Agogo-Contract-Signing.pdf|Only ~$7.8bn CONTRACT AWARDS disclosed; JPT confirms operator capex statement is ">$13bn" for Greater PAJ + Agogo COMBINED — no standalone FID capex exists; NULL correct.
29|Rosebank Phase 1|CONFIRMED|3800|OE Digital — https://www.oedigital.com/news/508341-equinor-and-ithaca-energy-greenlight-3-8-billion-investment-in-uk-s-largest-undeveloped-offshore-field-rosebank|OE Digital + Hart Energy + partner Ithaca all state $3.8bn gross Phase 1 at Sep-2023 FID.
30|Sparta (formerly North Platte)|GAP-CONFIRMED|n/a|Shell PR + partner Equinor release (verified: no cost figure) — https://www.equinor.com/news/20231220-final-investment-decision-sparta|Neither operator nor partner discloses capex; trade coverage carries no figure.
# All 7 non-NULL figures confirmed at face value by independent publishers; no >10% conflicts.
# Shell pattern holds: Whale + Sparta FID capex never disclosed — NULLs firmly defensible.
# Agogo watch-item: widely-reprinted $7.8bn is contract-award value; $8.2bn "largest FID 2023" is a third-party estimate — keep null, distinction note essential.
31|Uaru|CONFIRMED|12700|Hart Energy — https://www.hartenergy.com/exclusives/exxon-hess-take-127-billion-fid-uaru-development-offshore-guyana-204886|Also NS Energy. $12.7B gross FID, fifth Stabroek, 44 wells — exact match.
32|Bonga North|GAP-CONFIRMED|n/a|Shell release checked — https://www.shell.com/news-and-insights/newsroom/news-and-media-releases/2024/shell-invests-in-bonga-north-deep-water-project-nigeria.html|Operator gives scope + "IRR in excess of hurdle rate" but no capex; the $5bn circulates only via Nigerian press/presidency, never operator-attributed — NULL stands.
33|GranMorgu|CONFIRMED|10500|World Oil — https://worldoil.com/news/2024/10/1/totalenergies-approves-10-5-billion-granmorgu-oil-project-in-suriname/|Also Rigzone. $10.5B total project investment at FID — exact match.
34|Kaminho|FIGURE-EXISTS|6000|Reuters via The Globe and Mail — https://www.theglobeandmail.com/business/industry-news/energy-and-resources/article-totalenergies-moves-ahead-on-us6-billion-kaminho-oil-project-in-angola/|VERBATIM: "The $6-billion project involves developing two oil fields located in Block 20/11, Cameia and Golfino, according to a statement from Angola's national hydrocarbon agency ANPG." Attributed to ANPG (state concessionaire), NOT operator; TotalEnergies release confirmed figure-free.
35|Kaskida|CONFIRMED|5000 (upper bound)|S&P Global Commodity Insights — https://www.spglobal.com/energy/en/news-research/latest-news/crude-oil/073024-bp-takes-fid-on-kaskida-oil-project-in-us-gulf-of-mexico|CEO on Q2-2024 call: "would cost less than $5 billion", phase 1/6 wells — upper-bound treatment matches operator language.
36|Whiptail|CONFIRMED|12700|Hart Energy — https://www.hartenergy.com/exclusives/exxon-mobil-green-lights-127b-whiptail-project-offshore-guyana-208799/|Also OGJ. $12.7B gross, sixth Stabroek, 48 wells — exact match.
37|Coral North FLNG|FIGURE-EXISTS|7200 (approx)|INP (Mozambique petroleum regulator) — https://www.inp.gov.mz/en/02-10-2025-coral-norte-alcanca-decisao-final-de-investimento-e-consolida-mocambique-como-potencia-energetica/|VERBATIM: "With an investment of around 7.2 billion dollars and the start of production planned for 2028..." Regulator/government-stated, NOT operator (Eni release figure-free); President Chapo cited ">$7.2bn" per Xinhua.
38|Hammerhead|CONFIRMED|6800|JPT (SPE) — https://jpt.spe.org/exxonmobil-reaches-fid-on-6-8-billion-hammerhead-field-offshore-guyana|Also News Room Guyana. $6.8B gross, seventh Stabroek, 18 wells — exact match.
39|Tiber-Guadalupe|CONFIRMED|5000|Bloomberg — https://www.bloomberg.com/news/articles/2025-09-29/bp-approves-5-billion-tiber-guadalupe-project-off-us-gulf-coast|Also Hart Energy + bp's own release. $5B phase 1 (6 Tiber + 2 Guadalupe tieback), bp 100% — exact match.
40|Greater PAJ|GAP-CONFIRMED|n/a|Azule PR verified figure-free — https://www.azule-energy.com/wp-content/uploads/2026/06/PR_GPAJ_FID_III.pdf|Operator and Eni releases capex-free; ubiquitous $5.1bn appears to trace to ANPG but no fetchable source verbatim-attributes it — NULL stands, revisit if ANPG statement becomes fetchable.
# All 5 non-NULL figures independently corroborated within tolerance; Kaskida upper-bound matches operator "less than $5 billion" phrasing.
# NULL pattern: operators increasingly withhold capex at FID while HOST-STATE AGENCIES disclose it — ANPG ($6bn Kaminho, likely $5.1bn Greater PAJ), INP (~$7.2bn Coral North). A "concessionaire-stated" basis tier would recover 2-3 of the 5 gaps.
# Bonga North is the cleanest gap: every $5bn mention is press or Nigerian-government sourced, never operator.
