"""Build the curated subsea-manifold supplier (key-players) database.

Source of truth for the records is this module (researched via agent team,
each row source-attributed). Running it validates every record against
:class:`ManifoldSupplierSchema` and writes the curated CSV + parquet to
``data/modules/subsea/curated/``.

Usage:
    uv run python scripts/build_manifold_suppliers_db.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from worldenergydata.subsea.schemas.manifold_supplier import (
    LIST_DELIMITER,
    ManifoldSupplierSchema,
)

COLLECTION_DATE = "2026-06-21"

# Each record researched 2026-06-21 via web search of company sites, annual
# reports, and trade press (Offshore Magazine, World Oil, Offshore-Energy,
# company press releases). DATA_SOURCE_URLS carries the per-row provenance.
RECORDS: list[dict] = [
    {
        "COMPANY": "TechnipFMC plc",
        "TICKER": "NYSE:FTI",
        "HQ_COUNTRY": "United Kingdom",
        "HQ_CITY": "Newcastle upon Tyne (operational HQ Houston, USA)",
        "PARENT_OR_JV": "Independent (2017 Technip + FMC Technologies merger)",
        "MANIFOLD_ROLE": "OEM",
        "ROLE_TIER": "tier_1",
        "MARKET_POSITION": (
            "Tier-1 global subsea market leader; only provider integrating "
            "SPS + SURF via iEPCI. Subsea backlog ~$15.8B (Q1 2026); 100th "
            "Subsea 2.0 tree delivered May 2025."
        ),
        "MAX_WATER_DEPTH_M": 3000,
        "PRODUCT_LINES": [
            "Subsea 2.0 compact/configured manifolds",
            "Production and injection manifolds",
            "Templates and tie-in systems",
            "PLEM / PLET",
            "Subsea 2.0 trees (horizontal and vertical)",
            "Subsea controls and distribution systems",
            "Configured-to-order standardized subsea systems",
        ],
        "NOTABLE_PROJECTS": [
            "TotalEnergies GranMorgu, Block 58, Suriname (>$1B iEPCI, Q4 2024)",
            "Eni Maha deepwater, offshore Indonesia (iEPCI, Nov 2025)",
            "Energean Katlan, Eastern Mediterranean (large iEPCI)",
        ],
        "RECENT_DEVELOPMENTS": [
            "Nov 2024: >$1B iEPCI award for TotalEnergies GranMorgu (Suriname)",
            "May 2025: 100th Subsea 2.0 tree delivered",
            "Nov 2025: substantial iEPCI scope from Eni for Maha (Indonesia)",
            "2025: FCF rose to $1.4B; subsea-driven guidance raise",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.technipfmc.com/en/what-we-do/subsea/subsea-systems/well-control/manifolds/",
            "https://www.technipfmc.com/en/what-we-do/subsea/iepci-subsea/",
            "https://www.technipfmc.com/en/investors/financial-news-releases/press-release/technipfmc-awarded-major-iepci-contract-for-totalenergies-granmorgu-development-offshore-suriname/",
            "https://www.worldoil.com/news/2025/11/18/eni-awards-technipfmc-substantial-iepci-scope-for-maha-project-offshore-indonesia/",
        ],
        "NOTES": (
            "Subsea 2.0 is a modular standardized platform (~50% size/weight/"
            "part-count reduction). MAX_WATER_DEPTH_M reflects connection-"
            "system qualification ~3,000 m / 20,000 psi; trees rated ~10,000 ft."
        ),
    },
    {
        "COMPANY": "SLB OneSubsea",
        "TICKER": "NYSE:SLB (OneSubsea is a non-listed JV)",
        "HQ_COUNTRY": "Norway / United States (dual)",
        "HQ_CITY": "Oslo, Norway and Houston, Texas",
        "PARENT_OR_JV": "OneSubsea JV: SLB 70% / Aker Solutions 20% / Subsea7 10% (closed Oct 2023)",
        "MANIFOLD_ROLE": "OEM",
        "ROLE_TIER": "tier_1",
        "MARKET_POSITION": (
            "Tier-1 global leader in subsea production systems and the market "
            "leader in subsea boosting/processing; combines SLB + Aker Solutions "
            "manufacturing with Subsea7 installation (Subsea Integration Alliance)."
        ),
        "MAX_WATER_DEPTH_M": 3050,
        "PRODUCT_LINES": [
            "Production and injection (water/gas) manifolds",
            "Cluster manifolds (multi well-slot)",
            "PLEM / PLET and tie-in structures",
            "Integrated template structures (ITS)",
            "Subsea trees (vertical and horizontal, ultra-deepwater)",
            "Multiphase boosting / helico-axial pumps",
            "Subsea wet-gas compression and processing",
            "Subsea controls and connectors",
        ],
        "NOTABLE_PROJECTS": [
            "Shell Stones, Gulf of Mexico (~2,900 m, world's deepest; boosting)",
            "Shell Ormen Lange, Norway (first subsea wet-gas compression)",
            "CNOOC Kaiping 18-1, South China Sea (20-well integrated EPC, 2024/2026)",
            "Var Energi NCS framework (trees, templates, manifolds, 2025)",
        ],
        "RECENT_DEVELOPMENTS": [
            "Oct 2023: OneSubsea JV closed (SLB 70/AKSO 20/SUBC 10), ~11,000 staff",
            "2024: integrated EPC award from CNOOC for Kaiping 18-1 deepwater",
            "Mar 2026: deepwater award offshore Malaysia (PTTEP)",
            "Push on standardized/configurable manifold and tree designs",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.onesubsea.slb.com/products-and-services/subsea-field-development/subsea-production-systems/subsea-manifolds",
            "https://www.akersolutions.com/news/news-archive/2023/aker-solutions-slb-and-subsea7-announce-closing-of-the-onesubsea-joint-venture/",
            "https://www.slb.com/newsroom/press-release/2026/pr-2026-0316oss-kaiping-cnooc",
        ],
        "NOTES": (
            "MAX_WATER_DEPTH_M = ~10,000 ft rated manifold capability "
            "(15,000 psi, 175C) per OneSubsea product page; deepest field "
            "deployment is Shell Stones ~2,900 m. Consolidated within SLB."
        ),
    },
    {
        "COMPANY": "Baker Hughes Company",
        "TICKER": "NASDAQ:BKR",
        "HQ_COUNTRY": "United States",
        "HQ_CITY": "Houston, Texas",
        "PARENT_OR_JV": "Independent (carries former GE Oil & Gas subsea heritage)",
        "MANIFOLD_ROLE": "OEM",
        "ROLE_TIER": "tier_1",
        "MARKET_POSITION": (
            "Tier-1 global subsea production system OEM; one of three majors "
            "alongside SLB-OneSubsea and TechnipFMC, differentiated by the "
            "lightweight/modular Aptara TOTEX-lite system."
        ),
        "MAX_WATER_DEPTH_M": 3000,
        "PRODUCT_LINES": [
            "Production/injection manifolds (cluster, template, WAG)",
            "Aptara modular compact manifold (TOTEX-lite)",
            "PLEM / PLET / riser bases / in-line tees",
            "HIPPS and subsea isolation valve modules (SSIV)",
            "Subsea trees (vertical/horizontal and compact)",
            "Subsea controls (SemStar5) and connection systems (FLX360)",
            "Flexible pipe systems and jumpers",
        ],
        "NOTABLE_PROJECTS": [
            "TPAO Sakarya Gas Phase 3, Black Sea (trees + structures, 2025)",
            "Azule Energy Agogo West Hub, Angola (23 trees + 11 Aptara manifolds)",
            "Petrobras Buzios, Santos Basin (WAG manifolds, ~2,000 m)",
            "TotalEnergies Kaminho deepwater, Angola (compression, 2024)",
        ],
        "RECENT_DEVELOPMENTS": [
            "2025: integrated subsea + completion systems for TPAO Sakarya Phase 3",
            "2025: added a large Brazilian deepwater field (Petrobras)",
            "Oct 2024: all-electric compression order for TotalEnergies Kaminho",
            "Ongoing Aptara compact manifold + FLX360 expansion",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.bakerhughes.com/subsea/subsea-production-systems/subsea-manifolds-pipeline-products",
            "https://www.bakerhughes.com/subsea/subsea-connect/aptara-totexlite-subsea-system",
            "https://investors.bakerhughes.com/news-releases/news-release-details/baker-hughes-supply-integrated-subsea-completion-systems-turkish",
            "https://investors.bakerhughes.com/news-releases/news-release-details/baker-hughes-awarded-major-subsea-contract-azule-energy-agogo",
        ],
        "NOTES": (
            "Subsea business sits in Oilfield Services & Equipment (Subsea & "
            "Surface Pressure Systems). MAX_WATER_DEPTH_M reflects flexible-"
            "pipe qualification target; manifolds deployed >2,000 m."
        ),
    },
    {
        "COMPANY": "Aker Solutions ASA",
        "TICKER": "OSE:AKSO",
        "HQ_COUNTRY": "Norway",
        "HQ_CITY": "Fornebu (Oslo area)",
        "PARENT_OR_JV": "Subsea OEM business contributed to OneSubsea JV (20% stake) Oct 2023",
        "MANIFOLD_ROLE": "OEM",
        "ROLE_TIER": "tier_1",
        "MARKET_POSITION": (
            "Tier-1 subsea OEM heritage; subsea/manifold OEM capability folded "
            "into OneSubsea (Oct 2023). Retains 20% JV stake plus field "
            "development, floaters and life-cycle services outside the JV."
        ),
        "MAX_WATER_DEPTH_M": 2500,
        "PRODUCT_LINES": [
            "Production and injection manifolds (deepwater range)",
            "Templates and integrated template structures (ITS)",
            "Subsea structures: flow base, guide base, riser base",
            "Subsea trees (vertical/standardized)",
            "Wellheads and subsea control systems",
            "PLET / PLEM and tie-in equipment",
        ],
        "NOTABLE_PROJECTS": [
            "Equinor Irpa gas, Norwegian Sea (trees + manifolds, Sept 2025)",
            "Equinor Halten East, Norwegian Sea (7 trees, 5 manifold structures, 2022)",
            "Statoil/Equinor Skuld, Norwegian Sea (template manifolds, trees)",
            "CNOOC Kaiping 18-1 deepwater (via OneSubsea, 2025/2026)",
        ],
        "RECENT_DEVELOPMENTS": [
            "Oct 2023: closed OneSubsea JV (20% stake; SLB 70%, Subsea7 10%)",
            "Feb 2025: SLB OneSubsea + Var Energi NCS SPS agreement",
            "Sept 2025: awarded Equinor Irpa subsea production system",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.akersolutions.com/what-we-do/subsea-production-systems-and-lifecycle-services/onesubsea/",
            "https://www.akersolutions.com/news/news-archive/2022/aker-solutions-to-provide-subsea-production-system-for-the-halten-east-development/",
            "https://www.slb.com/newsroom/press-release/2025/slb-onesubsea-signs-agreement-with-var-energi-for-upcoming-subsea-developments-in-norway",
        ],
        "NOTES": (
            "Since Oct 2023 not a standalone manifold OEM; most new SPS "
            "hardware flows through SLB OneSubsea, though some Norwegian awards "
            "(e.g. Irpa) still report under the Aker Solutions name. "
            "MAX_WATER_DEPTH_M is indicative design/study capability."
        ),
    },
    {
        "COMPANY": "Subsea 7 S.A.",
        "TICKER": "OSE:SUBC",
        "HQ_COUNTRY": "Luxembourg (registered); UK operational HQ",
        "HQ_CITY": "Luxembourg City (registered); London/Sutton (operational)",
        "PARENT_OR_JV": "OneSubsea JV 10% stake; Saipem merger ('Saipem7') signed 2025, pending",
        "MANIFOLD_ROLE": "EPC",
        "ROLE_TIER": "tier_1",
        "MARKET_POSITION": (
            "Tier-1 global SURF/EPCI contractor; one of two dominant SURF "
            "installers (with TechnipFMC). Manifolds/SPS accessed via the SLB "
            "OneSubsea JV and Subsea Integration Alliance, not a standalone OEM."
        ),
        "MAX_WATER_DEPTH_M": 3000,
        "PRODUCT_LINES": [
            "SURF (umbilicals, risers, flowlines) EPCI",
            "Subsea structures, manifolds and templates (via OneSubsea JV)",
            "PLET / PLEM and pipeline end terminations",
            "Rigid and flexible risers, flowlines and tie-ins",
            "Pipeline installation (S-lay, J-lay, reel-lay)",
            "Life-of-field services, IRM and ROV operations",
        ],
        "NOTABLE_PROJECTS": [
            "ConocoPhillips Greater Ekofisk SURF EPCI, Norway (Dec 2025)",
            "Equinor Fram Sor FEED + EPCI option, Norway (2025)",
            "OKEA Bestla integrated SPS+SURF via OneSubsea (2024)",
            "Petrobras deepwater SURF awards, Brazil (>$1.25B)",
        ],
        "RECENT_DEVELOPMENTS": [
            "Oct 2023: OneSubsea JV closed (10% stake)",
            "Jul 2025: binding Saipem-Subsea7 merger agreement signed ('Saipem7')",
            "Jun 2026: merger pending regulatory clearance (UK CMA), target H2 2026",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.subsea7.com/en/investors/shareholder-centre/faqs.html",
            "https://investorcenter.slb.com/news-releases/news-release-details/slb-aker-solutions-and-subsea7-announce-closing-onesubsea-joint",
            "https://www.saipem.com/en/media/press-releases/2025-07-24/saipem-and-subsea7-announce-signing-merger-agreement",
            "https://www.gov.uk/cma-cases/subsea7-slash-saipem-merger-inquiry",
        ],
        "NOTES": (
            "Manifolds are an OEM offering only through the OneSubsea JV (10% "
            "stake) and Subsea Integration Alliance. 3,000 m is the cited "
            "pipeline/installation capability. Saipem7 merger NOT closed as of "
            "Jun 2026."
        ),
    },
    {
        "COMPANY": "McDermott International, Ltd",
        "TICKER": "private",
        "HQ_COUNTRY": "United States",
        "HQ_CITY": "Houston, Texas",
        "PARENT_OR_JV": "Privately owned by creditor consortium since 2024 restructuring (formerly NYSE:MDR)",
        "MANIFOLD_ROLE": "fabricator",
        "ROLE_TIER": "tier_1",
        "MARKET_POSITION": (
            "Tier-1 global offshore EPCI / SURF contractor and large-structure "
            "fabricator; manifolds delivered as part of integrated EPCI scope "
            "(structural fabrication + installation), not as an SPS OEM."
        ),
        "MAX_WATER_DEPTH_M": 2900,
        "PRODUCT_LINES": [
            "Subsea manifolds and structures (structural fabrication/integration)",
            "Subsea templates and PLET / PLEM structures",
            "SURF (umbilicals, risers, flowlines)",
            "Rigid and reel-lay pipelines (incl. pipe-in-pipe)",
            "Subsea field-development EPCI",
            "Floating facilities / topsides fabrication",
        ],
        "NOTABLE_PROJECTS": [
            "ADNOC Nasr Phase II EPCI incl. new manifold tower, UAE (Jan 2026)",
            "PTTEP Sabah Block H deepwater pipeline + SURF EPCI, Malaysia (2025)",
            "Chevron Gorgon Phase 2 subsea manifolds fabrication, Australia (2025)",
            "QatarEnergy North Field South offshore pipelines EPCI (2024)",
        ],
        "RECENT_DEVELOPMENTS": [
            "Jan 2026: ~$0.75-1B ADNOC Al Nasr EPCI incl. subsea manifold tower",
            "Sep 2025: PTTEP Block H deepwater pipeline + SURF EPCI (Malaysia)",
            "Dec 2024: completed CB&I storage divestment (~$475M)",
            "2024: out-of-court restructuring (~$2B debt reduction), went private",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.mcdermott.com/solutions/subsea-floating-facilities",
            "https://www.prnewswire.com/news-releases/mcdermott-awarded-deepwater-subsea-contract-by-pttep-in-malaysia-302549872.html",
            "https://worldoil.com/news/2026/1/22/mcdermott-wins-major-epci-contract-for-adnoc-s-al-nasr-offshore-expansion/",
            "https://www.mcdermott.com/mcdermott-difference/fabrication-facilities",
        ],
        "NOTES": (
            "Fabricates/installs manifolds, templates, PLET/PLEM at yards "
            "(Batam, Altamira, Dammam, Jebel Ali) but integrates third-party "
            "trees/valves/controls; NOT an SPS OEM. 2,900 m is stated deepest "
            "pipelay capability. McDermott is NOT part of the Saipem-Subsea7 deal."
        ),
    },
    {
        "COMPANY": "Dril-Quip (Innovex International, Inc.)",
        "TICKER": "NYSE:INVX",
        "HQ_COUNTRY": "United States",
        "HQ_CITY": "Houston, Texas",
        "PARENT_OR_JV": "Innovex International (Sept 2024 Dril-Quip + Innovex Downhole merger)",
        "MANIFOLD_ROLE": "OEM",
        "ROLE_TIER": "tier_2",
        "MARKET_POSITION": (
            "Tier-2 global OEM in subsea wellheads/connectors and deepwater "
            "drilling/production hardware (founded 1981). Smaller than the "
            "tier-1 SPS integrators; post-merger narrowed to core wellhead/"
            "connector lines (exited subsea trees in 2025)."
        ),
        "MAX_WATER_DEPTH_M": 4572,
        "PRODUCT_LINES": [
            "Subsea wellheads (SS-15 series, BigBore IIe, SS-15 RLDe)",
            "Mudline hanger systems",
            "Specialty/wellhead connectors (DXe connector)",
            "Subsea manifolds and flowline/connection systems",
            "Drilling and production riser systems",
            "Subsea control and tie-back systems",
        ],
        "NOTABLE_PROJECTS": [
            "Murphy Samurai/Khaleesi, Gulf of Mexico (first SS-15 RLDe, 2021)",
            "Premier Oil Catcher, Central North Sea (subsea trees, 2010s)",
            "Petrobras Brazil pre-salt wellhead equipment (~2023)",
            "Gulf of Mexico HP/HT deepwater wellhead programs",
        ],
        "RECENT_DEVELOPMENTS": [
            "Sept 2024: merger completed; renamed Innovex International (NYSE:INVX)",
            "Early 2025: ~$30M annualized merger cost synergies realized",
            "Jul 2025: divested subsea tree product line to Trendsetter Engineering",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.innovex-inc.com/dril-quip-and-innovex-complete-merger-to-form-innovex-international-inc/",
            "https://investors.innovex-inc.com/news/news-details/2025/Innovex-Completes-Divestment-of-Subsea-Tree-Product-Line/default.aspx",
            "https://www.offshore-energy.biz/newly-formed-houston-firm-sheds-subsea-tree-business-to-focus-on-core-product-lines/",
        ],
        "NOTES": (
            "Dril-Quip survives as a brand under Innovex International. "
            "MAX_WATER_DEPTH_M = 15,000 ft SS-15/DXe wellhead-connector rating. "
            "Manifolds always secondary to wellheads/connectors; subsea TREES "
            "(not manifolds) were sold to Trendsetter in 2025."
        ),
    },
    {
        "COMPANY": "Trendsetter Engineering, Inc.",
        "TICKER": "private",
        "HQ_COUNTRY": "United States",
        "HQ_CITY": "Houston, Texas",
        "PARENT_OR_JV": "Privately owned; affiliate Trendsetter Vulcan Offshore (HPHT intervention)",
        "MANIFOLD_ROLE": "OEM",
        "ROLE_TIER": "niche",
        "MARKET_POSITION": (
            "Independent / niche US subsea hardware specialist; competes with "
            "integrated majors by offering customized, fit-for-purpose, "
            "schedule-driven manifolds and connection systems. Recently expanded "
            "into subsea trees and HPHT well intervention."
        ),
        "MAX_WATER_DEPTH_M": 3048,
        "PRODUCT_LINES": [
            "Subsea production manifolds (production, gas-lift, SSIV)",
            "PLETs and PLEMs",
            "Connection systems (TCS connectors, Dual Bore, TC2 Collet)",
            "Jumper systems and pipework fabrication",
            "Mudmats and suction pile foundations",
            "Horizontal subsea trees (15K, via acquired Innovex line)",
            "Well intervention / capping and containment systems",
        ],
        "NOTABLE_PROJECTS": [
            "Woodside/Pemex Trion, offshore Mexico (manifolds + foundations, 2024)",
            "Trident Energy Bonito/Bicudo, Brazil (two 6-slot manifolds, 2024-25)",
            "Woodside Shenzi North, US Gulf of Mexico",
            "Leviathan production manifold (~450 tons)",
        ],
        "RECENT_DEVELOPMENTS": [
            "Jan 2024: awarded Woodside Trion manifolds/foundations/connectors",
            "Jun 2024: 'significant' Brazil contract (Trident Energy, 2 manifolds)",
            "Jul 2025: won four 15K horizontal trees + acquired Innovex tree line",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.trendsetterengineering.com/manifolds-plets-plems/",
            "https://www.trendsetterengineering.com/news/trendsetter-engineering-commences-work-on-woodsides-trion-project/",
            "https://worldoil.com/news/2024/6/13/trendsetter-engineering-secures-significant-subsea-contract-offshore-brazil/",
            "https://worldoil.com/news/2025/7/23/trendsetter-engineering-secures-subsea-tree-contract-for-u-s-gulf/",
        ],
        "NOTES": (
            "Privately owned Houston firm; in-house machine shop + FAT testing, "
            "ISO 9001. MAX_WATER_DEPTH_M = 10,000 ft (TVO intervention rating); "
            "manifold/tree pages do not publish explicit field depth ratings."
        ),
    },
    {
        "COMPANY": "ABB Ltd",
        "TICKER": "SIX:ABBN (also NYSE:ABB)",
        "HQ_COUNTRY": "Switzerland",
        "HQ_CITY": "Zurich",
        "PARENT_OR_JV": "Independent",
        "MANIFOLD_ROLE": "subsystem_supplier",
        "ROLE_TIER": "adjacency",
        "MARKET_POSITION": (
            "Not a subsea manifold/SPS OEM. Leading specialist supplier of "
            "subsea electrification — power distribution/conversion and "
            "automation — an enabling technology complementary to manifolds/SPS."
        ),
        "MAX_WATER_DEPTH_M": 3000,
        "PRODUCT_LINES": [
            "Subsea power distribution and conversion system (transformer, MV drives, switchgear)",
            "Subsea automation and control systems",
            "Subsea Power Distribution System (PDS) for seabed pumps/compressors",
            "ABB Ability System 800xA topside control",
            "Subsea variable speed drives for boosting/compression",
        ],
        "NOTABLE_PROJECTS": [
            "Subsea Power JIP with Equinor, TotalEnergies, Chevron (3,000-hr test, 2019)",
            "ABB-Equinor frame agreement for offshore electrical equipment",
        ],
        "RECENT_DEVELOPMENTS": [
            "Subsea power distribution positioned for long-distance step-outs (to 100 MW, 600 km, 3,000 m)",
            "Ongoing Equinor electrical-equipment framework agreements",
            "No 2024-2026 named manifold field award (activity is power/electrification)",
        ],
        "DATA_SOURCE_URLS": [
            "https://new.abb.com/oil-and-gas/sectors/offshore-oil-and-gas/subsea/subsea-power",
            "https://new.abb.com/news/detail/46714/abb-proves-world-first-subsea-power-technology-system-signaling-new-era-for-offshore-oil-and-gas",
            "https://www.offshore-mag.com/subsea/article/14168482/subsea-power-system-opens-way-to-longer-distance-deepwater-step-outs",
        ],
        "NOTES": (
            "Electrification/automation company, not a manifold manufacturer "
            "or EPC. Listed in some 'subsea manifold market' aggregator reports "
            "due to its adjacent subsea-power/controls role. MAX_WATER_DEPTH_M "
            "= 3,000 m stated PDS capability (validated in 2019 shallow test)."
        ),
    },
    {
        "COMPANY": "Halliburton Company",
        "TICKER": "NYSE:HAL",
        "HQ_COUNTRY": "United States",
        "HQ_CITY": "Houston, Texas",
        "PARENT_OR_JV": "Independent",
        "MANIFOLD_ROLE": "limited",
        "ROLE_TIER": "adjacency",
        "MARKET_POSITION": (
            "Tier-1 global oilfield services major but NOT a subsea manifold "
            "OEM. In subsea it competes in completions, well intervention, "
            "tubing-hanger controls and safety systems, not trees/manifolds/EPC."
        ),
        "MAX_WATER_DEPTH_M": 2578,
        "PRODUCT_LINES": [
            "Subsea completion systems (intelligent/multizone, FlexRite TAML)",
            "Subsea well intervention systems (SCILS, coiled tubing)",
            "Remote Operated Control/Completion Systems (ROCS, eROCS, umbilical-less)",
            "Optime Tubing Hanger Orientation System (OTHOS)",
            "Subsea safety systems (Veto, EcoStar eTRSV)",
            "Subsea controls (Dash electrohydraulic module, DynaLink telemetry)",
        ],
        "NOTABLE_PROJECTS": [
            "Aker BP first umbilical-less tubing hanger (eROCS + OTHOS), NCS (2025)",
            "Shell framework for umbilical-less tubing hanger install, GoM (2025)",
            "Deepwater record umbilical-less ROCS at 8,458 ft (~2,578 m), GoM",
        ],
        "RECENT_DEVELOPMENTS": [
            "Oct 2025: framework agreement with Shell for umbilical-less ROCS",
            "Oct 2025: first eROCS + OTHOS operation with Aker BP (NCS)",
            "2024-25: deepest umbilical-less tubing hanger op (~2,578 m)",
        ],
        "DATA_SOURCE_URLS": [
            "https://www.halliburton.com/en/completions/well-intervention-and-diagnostics/subsea-completion-interventions-systems",
            "https://www.halliburton.com/en/about-us/press-release/halliburton-signs-framework-agreement-umbilical-less-tubing-hanger-installations",
            "https://www.halliburton.com/en/resources/operator-sets-deepwater-record-with-umbilical-less-rocs-technology",
        ],
        "NOTES": (
            "Does NOT make subsea manifolds/trees/jumpers; footprint is "
            "completions, tubing-hanger/controls (umbilical-less ROCS/eROCS), "
            "safety valves and well intervention. MAX_WATER_DEPTH_M derived "
            "from the 8,458 ft umbilical-less record (intervention capability)."
        ),
    },
]


def _pack(value: object) -> object:
    """Pack list values into a delimited string for CSV storage."""
    if isinstance(value, (list, tuple)):
        return LIST_DELIMITER.join(str(v) for v in value)
    return value


def build() -> Path:
    rows = []
    for rec in RECORDS:
        rec = dict(rec)
        rec.setdefault("COLLECTION_DATE", COLLECTION_DATE)
        # Primary source URL = first of the list, for quick provenance.
        urls = rec.get("DATA_SOURCE_URLS") or []
        rec.setdefault("DATA_SOURCE_URL", urls[0] if urls else None)
        # Validate against the schema (raises on any bad row).
        model = ManifoldSupplierSchema(**rec)
        # Serialize back to a flat, CSV-friendly dict.
        flat = {k: _pack(v) for k, v in model.model_dump().items()}
        rows.append(flat)

    df = pd.DataFrame(rows)
    out_dir = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "modules"
        / "subsea"
        / "curated"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "manifold_suppliers.csv"
    parquet_path = out_dir / "manifold_suppliers.parquet"
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    print(f"Wrote {len(df)} validated supplier records:")
    print(f"  {csv_path}")
    print(f"  {parquet_path}")
    return csv_path


if __name__ == "__main__":
    build()
