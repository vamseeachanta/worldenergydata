"""Build the curated frontier-basin deepwater discovery database (issue #603).

Source of truth for the records is this module: each row was researched via a
web-search agent team (2026-06-26) from operator press releases (ExxonMobil,
Hess, TotalEnergies, APA/Apache, Petronas, Shell, Galp, Rhino Resources,
Staatsolie) and reputable trade press (Offshore Magazine, Oil & Gas Journal,
Reuters, Rigzone, Offshore-Energy). Every row carries a primary DATA_SOURCE_URL
and a CONFIDENCE_TIER (high = operator-confirmed, medium = reputable secondary,
low = analyst/in-place-only/commerciality-unconfirmed).

Running it validates every record against :class:`DiscoverySchema` and writes
the curated CSV to ``data/modules/frontier_basins/curated/``.

Usage:
    uv run python scripts/build_frontier_basins_db.py
"""

from __future__ import annotations

import csv
from pathlib import Path

try:  # normal package import (CI / clean install)
    from worldenergydata.canada.emerging_basins.discovery_schema import DiscoverySchema
except ImportError:  # pragma: no cover - dev fallback for split src/packages tree
    import importlib.util

    _schema_path = (
        Path(__file__).resolve().parents[1]
        / "packages"
        / "worldenergydata-canada"
        / "src"
        / "worldenergydata"
        / "canada"
        / "emerging_basins"
        / "discovery_schema.py"
    )
    import sys

    _spec = importlib.util.spec_from_file_location("_discovery_schema", _schema_path)
    assert _spec and _spec.loader
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["_discovery_schema"] = _mod
    _spec.loader.exec_module(_mod)
    DiscoverySchema = _mod.DiscoverySchema

# Stabroek equity historically ExxonMobil 45% (op) / Hess 30% / CNOOC 25%;
# the Hess 30% transferred to Chevron on 18 Jul 2025 (Chevron-Hess close).
_STABROEK = "ExxonMobil 45% (op) / Hess 30% (->Chevron Jul 2025) / CNOOC 25%"
_BLOCK58 = "TotalEnergies 50% (op) / APA 50% (Staatsolie up to 20% on GranMorgu dev)"
_PEL39 = "Shell 45% (op) / QatarEnergy 45% / NAMCOR 10%"
_PEL85 = "Rhino Resources 42.5% (op) / Azule Energy 42.5% / NAMCOR 10% / Korres 5%"

COLLECTION_DATE = "2026-06-26"

# Columns in write order.
FIELDNAMES = [
    "DISCOVERY_NAME",
    "BLOCK",
    "COUNTRY",
    "BASIN",
    "OPERATOR",
    "PARTNERS",
    "DISCOVERY_YEAR",
    "WATER_DEPTH_M",
    "RESOURCE_ESTIMATE",
    "RESOURCE_BASIS",
    "STATUS",
    "CONFIDENCE_TIER",
    "DATA_SOURCE_URL",
    "NOTES",
]

RECORDS: list[dict] = [
    # ===================================================================
    # GUYANA — Stabroek block (ExxonMobil-operated)
    # Per-discovery recoverable volumes are NOT published by ExxonMobil;
    # only a block-level aggregate (~11 billion boe, Apr 2022) is stated.
    # ===================================================================
    {
        "DISCOVERY_NAME": "Liza",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2015,
        "WATER_DEPTH_M": 1743,
        "RESOURCE_ESTIMATE": "Liza field >1 Bboe (range ~0.8-1.4 Bboe)",
        "RESOURCE_BASIS": "recoverable",
        "STATUS": "producing",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.nsenergybusiness.com/news/newsexxonmobil-discovers-significant-oil-in-liza-1-well-offshore-guyana-210515-4582361/",
        "NOTES": "First Stabroek discovery; produced via Liza Destiny (2019) + Liza Unity (2022) FPSOs. Stabroek block aggregate ~11 Bboe (ExxonMobil, Apr 2022).",
    },
    {
        "DISCOVERY_NAME": "Liza Deep",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2017,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "~100-150 MMboe (deeper interval)",
        "RESOURCE_BASIS": "recoverable",
        "STATUS": "producing",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2017/0112_exxonmobil-announces-new-oil-discoveries-offshore-guyana",
        "NOTES": "Liza-3; water depth not disclosed.",
    },
    {
        "DISCOVERY_NAME": "Payara",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2017,
        "WATER_DEPTH_M": 2030,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "producing",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2017/0112_exxonmobil-announces-new-oil-discoveries-offshore-guyana",
        "NOTES": "Produced via Prosperity FPSO (first oil Nov 2023, ~220k bopd).",
    },
    {
        "DISCOVERY_NAME": "Snoek",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2017,
        "WATER_DEPTH_M": 1563,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2017/0330_exxonmobil-announces-new-oil-discovery-offshore-guyana",
        "NOTES": "Southern Liza area.",
    },
    {
        "DISCOVERY_NAME": "Turbot",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2017,
        "WATER_DEPTH_M": 1802,
        "RESOURCE_ESTIMATE": "Turbot+Longtail combined >500 MMboe",
        "RESOURCE_BASIS": "recoverable",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2017/1005_exxonmobil-announces-fifth-discovery-offshore-guyana",
        "NOTES": "Combined Turbot+Longtail figure is the only disclosed area volume.",
    },
    {
        "DISCOVERY_NAME": "Ranger",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2018,
        "WATER_DEPTH_M": 2735,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2018/0105_exxonmobil-announces-sixth-oil-discovery-offshore-guyana",
        "NOTES": "Opened a new carbonate play; deepest Stabroek water depth catalogued here.",
    },
    {
        "DISCOVERY_NAME": "Pacora",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2018,
        "WATER_DEPTH_M": 2067,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "sanctioned",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/newsroom/news-releases/2018/0228_exxonmobil-announces-seventh-oil-discovery-offshore-guyana",
        "NOTES": "Co-developed within the Payara project.",
    },
    {
        "DISCOVERY_NAME": "Longtail",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2018,
        "WATER_DEPTH_M": 1940,
        "RESOURCE_ESTIMATE": "Turbot+Longtail combined >500 MMboe",
        "RESOURCE_BASIS": "recoverable",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2018/0620_exxonmobil-announces-eighth-discovery-offshore-guyana",
        "NOTES": "Yellowtail/Whiptail area.",
    },
    {
        "DISCOVERY_NAME": "Hammerhead",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2018,
        "WATER_DEPTH_M": 1150,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "sanctioned",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2025/0922_exxonmobil-guyana-expands-capacity-with-seventh-offshore-development",
        "NOTES": "7th Stabroek project, sanctioned Sep 2025 (~150k bopd, first oil ~2029).",
    },
    {
        "DISCOVERY_NAME": "Pluma",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2018,
        "WATER_DEPTH_M": 1018,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://dpi.gov.gy/exxonmobil-makes-10th-oil-discovery-offshore-guyana/",
        "NOTES": "10th Stabroek discovery.",
    },
    {
        "DISCOVERY_NAME": "Tilapia",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2019,
        "WATER_DEPTH_M": 1783,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "appraisal",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2019/0206_exxonmobil-announces-two-new-discoveries-offshore-guyana",
        "NOTES": "",
    },
    {
        "DISCOVERY_NAME": "Haimara",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2019,
        "WATER_DEPTH_M": 1399,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "appraisal",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2019/0206_exxonmobil-announces-two-new-discoveries-offshore-guyana",
        "NOTES": "Gas-condensate discovery.",
    },
    {
        "DISCOVERY_NAME": "Yellowtail",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2019,
        "WATER_DEPTH_M": 1843,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "producing",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2019/0418_exxonmobil-announces-13th-discovery-offshore-guyana",
        "NOTES": "Produced via ONE GUYANA FPSO (first oil Aug 2025, ~250k bopd).",
    },
    {
        "DISCOVERY_NAME": "Tripletail",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2019,
        "WATER_DEPTH_M": 2003,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://www.worldoil.com/news/2019/9/16/exxonmobil-finds-more-oil-offshore-guyana-at-tripletail",
        "NOTES": "Turbot area.",
    },
    {
        "DISCOVERY_NAME": "Mako",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2019,
        "WATER_DEPTH_M": 1620,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "appraisal",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2019/1223_exxonmobil-discovers-oil-offshore-guyana-at-mako-1-well",
        "NOTES": "",
    },
    {
        "DISCOVERY_NAME": "Uaru",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2020,
        "WATER_DEPTH_M": 1933,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "sanctioned",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2023/0426_exxonmobil-guyana-advances-fifth-offshore-guyana-development",
        "NOTES": "5th Stabroek project (FID Apr 2023); Errea Wittu FPSO, ~250k bopd.",
    },
    {
        "DISCOVERY_NAME": "Pinktail",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2021,
        "WATER_DEPTH_M": 1810,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2021/0909_exxonmobil-announces-discovery-at-pinktail-offshore-guyana",
        "NOTES": "",
    },
    {
        "DISCOVERY_NAME": "Cataback",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2021,
        "WATER_DEPTH_M": 1807,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2021/1007_exxonmobil-increases-stabroek-resource-estimate-to-approximately-10-billion-barrels",
        "NOTES": "Announced alongside the ~10 Bboe block resource update.",
    },
    {
        "DISCOVERY_NAME": "Whiptail",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2021,
        "WATER_DEPTH_M": 1795,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "sanctioned",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2024/0412_guyana-offshore-development-whiptail",
        "NOTES": "6th Stabroek project (FID Apr 2024); FPSO Jaguar, ~250k bopd, first oil ~2027.",
    },
    {
        "DISCOVERY_NAME": "Fangtooth",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 1838,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "appraisal",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2022/0105_exxonmobil-makes-two-discoveries-offshore-guyana",
        "NOTES": "Fangtooth-1; a separate Fangtooth SE well followed in 2023.",
    },
    {
        "DISCOVERY_NAME": "Lau Lau",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 1461,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "appraisal",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2022/0105_exxonmobil-makes-two-discoveries-offshore-guyana",
        "NOTES": "Appraisal drilling began Jun 2024.",
    },
    {
        "DISCOVERY_NAME": "Sailfin",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 1407,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2022/1026_exxonmobil-announces-two-new-guyana-discoveries",
        "NOTES": "Southeast Stabroek.",
    },
    {
        "DISCOVERY_NAME": "Yarrow",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 1085,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/news/news-releases/2022/1026_exxonmobil-announces-two-new-guyana-discoveries",
        "NOTES": "Announced with Sailfin.",
    },
    {
        "DISCOVERY_NAME": "Lancetfish",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2023,
        "WATER_DEPTH_M": 1780,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/locations/guyana/news-releases/0426_exxonmobil-guyana-makes-discovery-at-lancetfish-1",
        "NOTES": "",
    },
    {
        "DISCOVERY_NAME": "Bluefin",
        "BLOCK": "Stabroek",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": _STABROEK,
        "DISCOVERY_YEAR": 2024,
        "WATER_DEPTH_M": 1294,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://corporate.exxonmobil.com/locations/guyana/news-releases/03152024_exxonmobil-guyana-announces-new-discovery",
        "NOTES": "Southeast Stabroek; first 2024 discovery.",
    },
    # ----- Guyana adjacent blocks -----
    {
        "DISCOVERY_NAME": "Tanager-1",
        "BLOCK": "Kaieteur",
        "OPERATOR": "ExxonMobil",
        "PARTNERS": "ExxonMobil 35% (op) / Cataleya 25% / Ratio 25% / Hess 15%",
        "DISCOVERY_YEAR": 2020,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "non_commercial",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.offshore-energy.biz/exxonmobil-makes-non-commercial-discovery-at-tanager-1-well-off-guyana/",
        "NOTES": "Ultra-deepwater; sub-commercial heavy oil. ExxonMobil/Hess later exited Kaieteur.",
    },
    {
        "DISCOVERY_NAME": "Jethro-1",
        "BLOCK": "Orinduik",
        "OPERATOR": "Tullow Oil",
        "PARTNERS": "Tullow 60% (op) / TotalEnergies 25% / Eco Atlantic 15%",
        "DISCOVERY_YEAR": 2019,
        "WATER_DEPTH_M": 1350,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "non_commercial",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://www.offshore-energy.biz/tullow-makes-first-oil-discovery-on-orinduik-license-offshore-guyana/",
        "NOTES": "Heavy, high-sulphur oil; sub-commercial as found.",
    },
    {
        "DISCOVERY_NAME": "Joe-1",
        "BLOCK": "Orinduik",
        "OPERATOR": "Tullow Oil",
        "PARTNERS": "Tullow 60% (op) / TotalEnergies 25% / Eco Atlantic 15%",
        "DISCOVERY_YEAR": 2019,
        "WATER_DEPTH_M": 780,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "non_commercial",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://www.oedigital.com/news/470736-tullow-makes-second-discovery-offshore-guyana",
        "NOTES": "Heavy oil; sub-commercial as found.",
    },
    {
        "DISCOVERY_NAME": "Kawa-1",
        "BLOCK": "Corentyne",
        "OPERATOR": "CGX Energy",
        "PARTNERS": "CGX Energy 32% (op) / Frontera Energy 68%",
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 355,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.prnewswire.com/news-releases/cgx-and-frontera-announce-light-oil-and-gas-condensate-discovery-at-the-kawa-1-exploration-well-offshore-guyana-301542642.html",
        "NOTES": "Light oil + gas condensate; de-risked the later Wei-1 well.",
    },
    {
        "DISCOVERY_NAME": "Wei-1",
        "BLOCK": "Corentyne",
        "OPERATOR": "CGX Energy",
        "PARTNERS": "CGX Energy 32% (op) / Frontera Energy 68%",
        "DISCOVERY_YEAR": 2023,
        "WATER_DEPTH_M": 583,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.worldoil.com/news/2023/6/28/cgx-frontera-make-major-oil-discovery-offshore-guyana/",
        "NOTES": "Light/medium crude; ~210 ft hydrocarbon-bearing sands; commerciality under evaluation.",
    },
    # ===================================================================
    # SURINAME — Block 58 (TotalEnergies-operated) + adjacent blocks
    # ===================================================================
    {
        "DISCOVERY_NAME": "Maka Central-1",
        "BLOCK": "Block 58",
        "OPERATOR": "TotalEnergies",
        "PARTNERS": _BLOCK58,
        "DISCOVERY_YEAR": 2020,
        "WATER_DEPTH_M": 1000,
        "RESOURCE_ESTIMATE": ">123 m net pay (light oil + gas-condensate)",
        "RESOURCE_BASIS": "net_pay",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.ogj.com/exploration-development/discoveries/article/14074323/maka-central-discovery-offshore-suriname-extends-guyana-cretaceous-oil-play",
        "NOTES": "First Block 58 discovery (operator Apache at time of drilling).",
    },
    {
        "DISCOVERY_NAME": "Sapakara West-1",
        "BLOCK": "Block 58",
        "OPERATOR": "TotalEnergies",
        "PARTNERS": _BLOCK58,
        "DISCOVERY_YEAR": 2020,
        "WATER_DEPTH_M": 1000,
        "RESOURCE_ESTIMATE": "79 m net oil + gas-condensate pay",
        "RESOURCE_BASIS": "net_pay",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.globenewswire.com/news-release/2020/04/02/2010828/0/en/Apache-Corporation-Announces-Significant-Oil-Discovery-Offshore-Suriname-at-Sapakara-West-1.html",
        "NOTES": "",
    },
    {
        "DISCOVERY_NAME": "Kwaskwasi-1",
        "BLOCK": "Block 58",
        "OPERATOR": "TotalEnergies",
        "PARTNERS": _BLOCK58,
        "DISCOVERY_YEAR": 2020,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "278 m net oil/volatile-oil/gas-condensate pay",
        "RESOURCE_BASIS": "net_pay",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://investor.apacorp.com/news-releases/news-release-details/apache-corporation-announces-major-oil-discovery-block-58",
        "NOTES": "Largest net pay on Block 58; water depth not disclosed.",
    },
    {
        "DISCOVERY_NAME": "Keskesi East-1",
        "BLOCK": "Block 58",
        "OPERATOR": "TotalEnergies",
        "PARTNERS": _BLOCK58,
        "DISCOVERY_YEAR": 2021,
        "WATER_DEPTH_M": 725,
        "RESOURCE_ESTIMATE": "63 m total net pay",
        "RESOURCE_BASIS": "net_pay",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://totalenergies.com/news/news/total-announces-third-significant-discovery-block-58-offshore-suriname",
        "NOTES": "TotalEnergies took over as operator around this well.",
    },
    {
        "DISCOVERY_NAME": "Sapakara South",
        "BLOCK": "Block 58",
        "OPERATOR": "TotalEnergies",
        "PARTNERS": _BLOCK58,
        "DISCOVERY_YEAR": 2021,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "GranMorgu (Sapakara South + Krabdagu) >750 MMbbl recoverable",
        "RESOURCE_BASIS": "recoverable",
        "STATUS": "sanctioned",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://totalenergies.com/news/press-releases/suriname-totalenergies-announces-final-investment-decision-granmorgu",
        "NOTES": "One of two GranMorgu development fields (FID 1 Oct 2024, ~$10.5B, FPSO 220k bopd, first oil 2028). The >750 MMbbl figure is the combined GranMorgu volume.",
    },
    {
        "DISCOVERY_NAME": "Krabdagu-1",
        "BLOCK": "Block 58",
        "OPERATOR": "TotalEnergies",
        "PARTNERS": _BLOCK58,
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 780,
        "RESOURCE_ESTIMATE": "GranMorgu (Sapakara South + Krabdagu) >750 MMbbl recoverable; up to 90 m net oil pay",
        "RESOURCE_BASIS": "recoverable",
        "STATUS": "sanctioned",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.globenewswire.com/news-release/2022/02/21/2388780/0/en/APA-Corporation-Announces-Oil-Discovery-at-Krabdagu-Exploration-Well-Offshore-Suriname.html",
        "NOTES": "Second GranMorgu development field.",
    },
    {
        "DISCOVERY_NAME": "Bonboni-1",
        "BLOCK": "Block 58",
        "OPERATOR": "TotalEnergies",
        "PARTNERS": _BLOCK58,
        "DISCOVERY_YEAR": 2021,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "16 m net pay, ~25 API black oil",
        "RESOURCE_BASIS": "net_pay",
        "STATUS": "non_commercial",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://www.nsenergybusiness.com/projects/block-58-development-offshore-suriname/",
        "NOTES": "~45 km north of the Maka-Keskesi trend; pay extent insufficient for standalone development.",
    },
    {
        "DISCOVERY_NAME": "Sloanea-1",
        "BLOCK": "Block 52",
        "OPERATOR": "Petronas",
        "PARTNERS": "Petronas 50% (op) / ExxonMobil 50% (Staatsolie back-in option)",
        "DISCOVERY_YEAR": 2020,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "appraisal",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.staatsolie.com/en/news/petronas-confirms-oil-discovery-in-block-52-offshore-suriname/",
        "NOTES": "Campanian sandstones; later framed as a potential gas/FLNG development.",
    },
    {
        "DISCOVERY_NAME": "Roystonea-1",
        "BLOCK": "Block 52",
        "OPERATOR": "Petronas",
        "PARTNERS": "Petronas 50% (op) / ExxonMobil 50% (Staatsolie back-in option)",
        "DISCOVERY_YEAR": 2023,
        "WATER_DEPTH_M": 904,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.rigzone.com/news/petronas_exxonmobil_make_third_discovery_in_surinames_block_52-16-may-2024-176761-article/",
        "NOTES": "Oil-bearing Campanian sandstones (TD 5,315 m).",
    },
    {
        "DISCOVERY_NAME": "Fusaea-1",
        "BLOCK": "Block 52",
        "OPERATOR": "Petronas",
        "PARTNERS": "Petronas 50% (op) / ExxonMobil 50% (Staatsolie back-in option)",
        "DISCOVERY_YEAR": 2024,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.rigzone.com/news/petronas_exxonmobil_make_third_discovery_in_surinames_block_52-16-may-2024-176761-article/",
        "NOTES": "Oil & gas-bearing Campanian sandstones (TD 5,227 m).",
    },
    {
        "DISCOVERY_NAME": "Baja-1",
        "BLOCK": "Block 53",
        "OPERATOR": "APA Corporation",
        "PARTNERS": "APA 45% (op) / Petronas 30% / CEPSA 25% (TotalEnergies acquired 25% Jun 2025)",
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 1140,
        "RESOURCE_ESTIMATE": "34 m net oil pay",
        "RESOURCE_BASIS": "net_pay",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.ogj.com/exploration-development/discoveries/article/14281658/apa-makes-first-discovery-in-block-53-offshore-suriname",
        "NOTES": "First discovery on Block 53.",
    },
    # ===================================================================
    # NAMIBIA — Orange Basin
    # ===================================================================
    {
        "DISCOVERY_NAME": "Graff-1",
        "BLOCK": "PEL 39 / Block 2913A",
        "OPERATOR": "Shell",
        "PARTNERS": _PEL39,
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 2000,
        "RESOURCE_ESTIMATE": "Graff+La Rona+Jonker combined ~1.7 Bboe [unverified, secondary; mixed in-place/EUR]",
        "RESOURCE_BASIS": "recoverable",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://www.oedigital.com/news/494051-shell-s-partners-confirm-oil-discovery-at-graff-1-well-offshore-namibia",
        "NOTES": "Shell took a ~$400M PEL 39 write-down in 2025 citing commerciality/reservoir difficulties.",
    },
    {
        "DISCOVERY_NAME": "La Rona-1",
        "BLOCK": "PEL 39 / Block 2913A",
        "OPERATOR": "Shell",
        "PARTNERS": _PEL39,
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "low",
        "DATA_SOURCE_URL": "https://www.offshore-technology.com/news/shell-finds-hydrocarbons-offshore-namibia/",
        "NOTES": "Commerciality uncertain (PEL 39 2025 write-down).",
    },
    {
        "DISCOVERY_NAME": "Jonker-1X",
        "BLOCK": "PEL 39 / Block 2913A",
        "OPERATOR": "Shell",
        "PARTNERS": _PEL39,
        "DISCOVERY_YEAR": 2023,
        "WATER_DEPTH_M": 2210,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "low",
        "DATA_SOURCE_URL": "https://www.offshore-technology.com/news/shell-finds-hydrocarbons-offshore-namibia/",
        "NOTES": "TD 6,168 m; commerciality uncertain (PEL 39 2025 write-down).",
    },
    {
        "DISCOVERY_NAME": "Cullinan-1X",
        "BLOCK": "PEL 39 / Block 2913A",
        "OPERATOR": "Shell",
        "PARTNERS": _PEL39,
        "DISCOVERY_YEAR": 2023,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "low",
        "DATA_SOURCE_URL": "https://www.offshore-technology.com/news/shell-finds-hydrocarbons-offshore-namibia/",
        "NOTES": "Hydrocarbons encountered; commerciality uncertain (PEL 39 2025 write-down).",
    },
    {
        "DISCOVERY_NAME": "Lesedi-1X",
        "BLOCK": "PEL 39 / Block 2913A",
        "OPERATOR": "Shell",
        "PARTNERS": _PEL39,
        "DISCOVERY_YEAR": 2023,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "low",
        "DATA_SOURCE_URL": "https://www.offshore-technology.com/news/shell-finds-hydrocarbons-offshore-namibia/",
        "NOTES": "Hydrocarbons confirmed; commerciality uncertain (PEL 39 2025 write-down).",
    },
    {
        "DISCOVERY_NAME": "Venus-1X",
        "BLOCK": "PEL 56 / Block 2913B",
        "OPERATOR": "TotalEnergies",
        "PARTNERS": "TotalEnergies 45.25% (op) / QatarEnergy 30% / Impact Oil & Gas 9.5% / NAMCOR 10%",
        "DISCOVERY_YEAR": 2022,
        "WATER_DEPTH_M": 3000,
        "RESOURCE_ESTIMATE": "~750 MMbbl recoverable (Phase 1, operator concept); 84 m net oil pay",
        "RESOURCE_BASIS": "recoverable",
        "STATUS": "pre_fid",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.offshore-energy.biz/totalenergies-750-million-barrel-project-offshore-namibia-targets-first-oil-in-2030/",
        "NOTES": "FID targeted end-2026, first oil ~2030. Analyst ~2 Bbbl recoverable / larger in-place figures are [unverified by operator].",
    },
    {
        "DISCOVERY_NAME": "Mopane",
        "BLOCK": "PEL 83 / Block 2813A",
        "OPERATOR": "Galp Energia",
        "PARTNERS": "Galp 80% (op) / NAMCOR 10% / Custos 10% (TotalEnergies farming in as operator, 40%)",
        "DISCOVERY_YEAR": 2024,
        "WATER_DEPTH_M": 1680,
        "RESOURCE_ESTIMATE": "up to 10 Bboe IN-PLACE (Galp estimate; NOT recoverable)",
        "RESOURCE_BASIS": "in_place",
        "STATUS": "appraisal",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://www.offshore-technology.com/news/mopane-field-oil-reserves-estimate/",
        "NOTES": "Multiple stacked intervals (AVO-1/-2/-3/-10/-13). The 10 Bboe headline is in-place and partly analyst-amplified; recoverable not disclosed.",
    },
    {
        "DISCOVERY_NAME": "Capricornus 1-X",
        "BLOCK": "PEL 85 / Block 2914",
        "OPERATOR": "Rhino Resources",
        "PARTNERS": _PEL85,
        "DISCOVERY_YEAR": 2025,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "38 m net pay, ~37 API light oil; tested >11,000 stb/d",
        "RESOURCE_BASIS": "net_pay",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "high",
        "DATA_SOURCE_URL": "https://www.rhinorsc.com/capricornus-1-x-light-oil-discovery/",
        "NOTES": "Flow-tested light oil, <2% CO2, no H2S.",
    },
    {
        "DISCOVERY_NAME": "Sagittarius 1-X",
        "BLOCK": "PEL 85 / Block 2914",
        "OPERATOR": "Rhino Resources",
        "PARTNERS": _PEL85,
        "DISCOVERY_YEAR": 2025,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://www.rhinorsc.com/rhino-resources-completes-drilling-of-first-exploration-well-on-pel-85-offshore-namibia/",
        "NOTES": "Hydrocarbon reservoir with no water contact; fluid analysis pending at announcement.",
    },
    {
        "DISCOVERY_NAME": "Volans-1X",
        "BLOCK": "PEL 85 / Block 2914",
        "OPERATOR": "Rhino Resources",
        "PARTNERS": _PEL85,
        "DISCOVERY_YEAR": 2025,
        "WATER_DEPTH_M": None,
        "RESOURCE_ESTIMATE": "",
        "RESOURCE_BASIS": "not_disclosed",
        "STATUS": "discovery",
        "CONFIDENCE_TIER": "medium",
        "DATA_SOURCE_URL": "https://www.oedigital.com/news/530653-rhino-resources-makes-high-liquid-yield-gas-discovery-off-namibia",
        "NOTES": "High-yield gas-condensate discovery.",
    },
]


def build() -> Path:
    """Validate every record and write the curated CSV. Returns the CSV path."""
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "data" / "modules" / "frontier_basins" / "curated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "frontier_discoveries.csv"

    validated: list[dict] = []
    for rec in RECORDS:
        country = _country_for(rec["BLOCK"])
        basin = _basin_for(country)
        full = {**rec, "COUNTRY": country, "BASIN": basin}
        model = DiscoverySchema(**full)
        row = {f: full.get(f, "") for f in FIELDNAMES}
        # Normalise None -> "" for clean CSV cells.
        for k, v in row.items():
            if v is None:
                row[k] = ""
        # Sanity: ensure model validated.
        assert model.DISCOVERY_NAME == rec["DISCOVERY_NAME"]
        validated.append(row)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(validated)

    print(f"Wrote {len(validated)} discoveries to {out_csv}")
    return out_csv


_GUYANA_BLOCKS = {"Stabroek", "Kaieteur", "Orinduik", "Corentyne"}
_SURINAME_BLOCKS = {"Block 58", "Block 52", "Block 53"}


def _country_for(block: str) -> str:
    if block in _GUYANA_BLOCKS:
        return "Guyana"
    if block in _SURINAME_BLOCKS:
        return "Suriname"
    if block.startswith("PEL"):
        return "Namibia"
    raise ValueError(f"Cannot map block {block!r} to a country")


def _basin_for(country: str) -> str:
    return "Orange" if country == "Namibia" else "Guyana-Suriname"


if __name__ == "__main__":
    build()
