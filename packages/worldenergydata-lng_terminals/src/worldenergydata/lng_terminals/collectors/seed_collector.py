"""Seed collector providing a curated baseline of well-known global LNG terminals.

This collector embeds a hardcoded dataset of ~90 major LNG facilities
worldwide.  It requires no network access and serves as the foundation
layer that later collectors (FERC, GIE, GIIGNL, web scrapers) enrich
and deduplicate against.

Data sourced from publicly available industry references including IEA,
IGU World LNG Report, GIIGNL Annual Report, and operator disclosures.
Capacities reflect nameplate / design values in MTPA.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..constants import (
    RefreshMode,
    Region,
    SourceReliability,
    TerminalFunction,
    TerminalStatus,
    TerminalType,
)
from ..models.terminal import LNGTerminal
from .base_collector import BaseCollector

# ---------------------------------------------------------------------------
# Seed dataset
# ---------------------------------------------------------------------------

_SEED_TERMINALS: list[dict[str, Any]] = [
    # -----------------------------------------------------------------------
    # UNITED STATES -- Export terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Sabine Pass LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 30.0,
        "operator": "Cheniere Energy",
        "year_commissioned": 2016,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Cameron LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 13.5,
        "operator": "Sempra Energy",
        "year_commissioned": 2019,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Corpus Christi LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 25.0,
        "operator": "Cheniere Energy",
        "year_commissioned": 2018,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Freeport LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 15.0,
        "operator": "Freeport LNG Development",
        "year_commissioned": 2019,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Cove Point LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.25,
        "operator": "Berkshire Hathaway Energy",
        "year_commissioned": 2018,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Elba Island LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 2.5,
        "operator": "Southern LNG Company",
        "year_commissioned": 2019,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Golden Pass LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 18.0,
        "operator": "Golden Pass Products",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Plaquemines LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 20.0,
        "operator": "Venture Global LNG",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Rio Grande LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 17.6,
        "operator": "NextDecade",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Port Arthur LNG",
        "country": "USA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 13.5,
        "operator": "Sempra Energy",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Delfin FLNG",
        "country": "USA",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "capacity_mtpa": 4.4,
        "operator": "Delfin Midstream",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Delfin FLNG Vessel 2",
        "country": "USA",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "capacity_mtpa": 4.4,
        "operator": "Delfin Midstream",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Delfin FLNG Vessel 3",
        "country": "USA",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PROPOSED,
        "capacity_mtpa": 4.4,
        "operator": "Delfin Midstream",
        "region": Region.NORTH_AMERICA,
    },
    # -----------------------------------------------------------------------
    # QATAR
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Ras Laffan LNG (Qatargas)",
        "country": "QAT",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 77.0,
        "operator": "QatarEnergy",
        "year_commissioned": 1997,
        "region": Region.MIDDLE_EAST,
    },
    {
        "terminal_name": "North Field East LNG",
        "country": "QAT",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 32.0,
        "operator": "QatarEnergy",
        "region": Region.MIDDLE_EAST,
    },
    # -----------------------------------------------------------------------
    # AUSTRALIA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "North West Shelf LNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 16.9,
        "operator": "Woodside Energy",
        "year_commissioned": 1989,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Gorgon LNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 15.6,
        "operator": "Chevron Australia",
        "year_commissioned": 2016,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Wheatstone LNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.9,
        "operator": "Chevron Australia",
        "year_commissioned": 2017,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Gladstone GLNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.8,
        "operator": "Santos",
        "year_commissioned": 2015,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Queensland Curtis QCLNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.5,
        "operator": "Shell",
        "year_commissioned": 2014,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Australia Pacific APLNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 9.0,
        "operator": "ConocoPhillips",
        "year_commissioned": 2015,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Ichthys LNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.9,
        "operator": "INPEX",
        "year_commissioned": 2018,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Darwin LNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.7,
        "operator": "Santos",
        "year_commissioned": 2006,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Prelude FLNG",
        "country": "AUS",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.6,
        "operator": "Shell",
        "year_commissioned": 2018,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Pluto LNG",
        "country": "AUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 4.9,
        "operator": "Woodside Energy",
        "year_commissioned": 2012,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # RUSSIA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Sakhalin-2 LNG",
        "country": "RUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 10.8,
        "operator": "Sakhalin Energy",
        "year_commissioned": 2009,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Yamal LNG",
        "country": "RUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 17.4,
        "operator": "Novatek",
        "year_commissioned": 2017,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Arctic LNG 2",
        "country": "RUS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 19.8,
        "operator": "Novatek",
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # MALAYSIA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "MLNG Bintulu",
        "country": "MYS",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 30.0,
        "operator": "PETRONAS",
        "year_commissioned": 1983,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "PFLNG Satu",
        "country": "MYS",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 1.2,
        "operator": "PETRONAS",
        "year_commissioned": 2016,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "PFLNG Dua",
        "country": "MYS",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 1.5,
        "operator": "PETRONAS",
        "year_commissioned": 2021,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "PFLNG Tiga",
        "country": "MYS",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 2.0,
        "operator": "PETRONAS",
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # NIGERIA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Nigeria LNG Bonny Island",
        "country": "NGA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 22.0,
        "operator": "Nigeria LNG Limited",
        "year_commissioned": 1999,
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "UTM FLNG",
        "country": "NGA",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "capacity_mtpa": 1.5,
        "operator": "UTM Offshore",
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "Ace Gas FLNG",
        "country": "NGA",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "capacity_mtpa": 3.0,
        "operator": "Ace Gas",
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "Transoceanic FLNG",
        "country": "NGA",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PROPOSED,
        "capacity_mtpa": 3.0,
        "operator": "Transoceanic Gas and Power",
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # INDONESIA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Bontang LNG",
        "country": "IDN",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 22.5,
        "operator": "Pertamina",
        "year_commissioned": 1977,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Tangguh LNG",
        "country": "IDN",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.6,
        "operator": "BP",
        "year_commissioned": 2009,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Donggi Senoro LNG",
        "country": "IDN",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 2.0,
        "operator": "PT Donggi Senoro LNG",
        "year_commissioned": 2015,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Genting FLNG",
        "country": "IDN",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 1.2,
        "operator": "Genting",
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # TRINIDAD AND TOBAGO
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Atlantic LNG",
        "country": "TTO",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 15.0,
        "operator": "Atlantic LNG Company",
        "year_commissioned": 1999,
        "region": Region.SOUTH_AMERICA,
    },
    # -----------------------------------------------------------------------
    # ALGERIA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Arzew GL1Z LNG",
        "country": "DZA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.0,
        "operator": "Sonatrach",
        "year_commissioned": 1978,
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "Arzew GL2Z LNG",
        "country": "DZA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.2,
        "operator": "Sonatrach",
        "year_commissioned": 1981,
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "Arzew GL3Z LNG",
        "country": "DZA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 4.7,
        "operator": "Sonatrach",
        "year_commissioned": 2014,
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "Skikda LNG",
        "country": "DZA",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.1,
        "operator": "Sonatrach",
        "year_commissioned": 2013,
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # EGYPT
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Idku LNG",
        "country": "EGY",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.2,
        "operator": "Egyptian LNG",
        "year_commissioned": 2005,
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "Damietta LNG",
        "country": "EGY",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "SEGAS",
        "year_commissioned": 2005,
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # OMAN
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Oman LNG Qalhat",
        "country": "OMN",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 10.4,
        "operator": "Oman LNG",
        "year_commissioned": 2000,
        "region": Region.MIDDLE_EAST,
    },
    # -----------------------------------------------------------------------
    # UAE
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Das Island ADGAS LNG",
        "country": "ARE",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.6,
        "operator": "ADNOC LNG",
        "year_commissioned": 1977,
        "region": Region.MIDDLE_EAST,
    },
    # -----------------------------------------------------------------------
    # NORWAY
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Hammerfest Snohvit LNG",
        "country": "NOR",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 4.3,
        "operator": "Equinor",
        "year_commissioned": 2007,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # EQUATORIAL GUINEA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Bioko Island LNG (EG LNG)",
        "country": "GNQ",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.4,
        "operator": "Marathon Oil",
        "year_commissioned": 2007,
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # CAMEROON
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Kribi FLNG (Hilli Episeyo)",
        "country": "CMR",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 2.4,
        "operator": "Golar LNG",
        "year_commissioned": 2018,
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # MAURITANIA -- FLNG
    # -----------------------------------------------------------------------
    {
        "terminal_name": "FLNG Gimi",
        "country": "MRT",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 2.5,
        "operator": "Golar LNG",
        "year_commissioned": 2025,
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "GTA Phase 2 FLNG",
        "country": "MRT",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "capacity_mtpa": 2.5,
        "operator": "BP",
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # MOZAMBIQUE
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Coral Sul FLNG",
        "country": "MOZ",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.4,
        "operator": "Eni",
        "year_commissioned": 2022,
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "Coral Norte FLNG",
        "country": "MOZ",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 3.6,
        "operator": "Eni",
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # CONGO
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Tango FLNG",
        "country": "COG",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 0.6,
        "operator": "Eni",
        "year_commissioned": 2023,
        "region": Region.AFRICA,
    },
    {
        "terminal_name": "Nguya FLNG",
        "country": "COG",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 2.4,
        "operator": "Eni",
        "year_commissioned": 2025,
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # GABON -- FLNG
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Cap Lopez FLNG",
        "country": "GAB",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 0.7,
        "operator": "Perenco",
        "region": Region.AFRICA,
    },
    # -----------------------------------------------------------------------
    # PAPUA NEW GUINEA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "PNG LNG",
        "country": "PNG",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.3,
        "operator": "ExxonMobil",
        "year_commissioned": 2014,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Kumul FLNG",
        "country": "PNG",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "capacity_mtpa": 1.5,
        "operator": "Kumul Petroleum",
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # CANADA
    # -----------------------------------------------------------------------
    {
        "terminal_name": "LNG Canada",
        "country": "CAN",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 14.0,
        "operator": "Shell Canada",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Woodfibre LNG",
        "country": "CAN",
        "terminal_type": TerminalType.ONSHORE_EXPORT,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 2.1,
        "operator": "Pacific Energy",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Cedar LNG",
        "country": "CAN",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 3.3,
        "operator": "Pembina Pipeline",
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Ksi Lisims LNG",
        "country": "CAN",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "capacity_mtpa": 12.0,
        "operator": "Western LNG",
        "region": Region.NORTH_AMERICA,
    },
    # -----------------------------------------------------------------------
    # MEXICO
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Altamira LNG FSRU",
        "country": "MEX",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "Iberdrola",
        "year_commissioned": 2006,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Energia Costa Azul LNG",
        "country": "MEX",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.BIDIRECTIONAL,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.3,
        "operator": "Sempra Energy",
        "year_commissioned": 2008,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Fast LNG Altamira",
        "country": "MEX",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 1.4,
        "operator": "New Fortress Energy",
        "year_commissioned": 2024,
        "region": Region.NORTH_AMERICA,
    },
    {
        "terminal_name": "Fast LNG Altamira Train 2",
        "country": "MEX",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 1.4,
        "operator": "New Fortress Energy",
        "region": Region.NORTH_AMERICA,
    },
    # -----------------------------------------------------------------------
    # JAPAN -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Sodegaura LNG",
        "country": "JPN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 12.0,
        "operator": "TEPCO / Tokyo Gas",
        "year_commissioned": 1973,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Negishi LNG",
        "country": "JPN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.5,
        "operator": "Tokyo Gas",
        "year_commissioned": 1969,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Futtsu LNG",
        "country": "JPN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 10.0,
        "operator": "TEPCO",
        "year_commissioned": 1985,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Himeji LNG",
        "country": "JPN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.0,
        "operator": "Kansai Electric / Osaka Gas",
        "year_commissioned": 1979,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Sakai LNG",
        "country": "JPN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "Osaka Gas",
        "year_commissioned": 1972,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # SOUTH KOREA -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Incheon LNG",
        "country": "KOR",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 28.0,
        "operator": "KOGAS",
        "year_commissioned": 1983,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Pyeongtaek LNG",
        "country": "KOR",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 25.0,
        "operator": "KOGAS",
        "year_commissioned": 1986,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Tongyeong LNG",
        "country": "KOR",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 14.0,
        "operator": "KOGAS",
        "year_commissioned": 2002,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Samcheok LNG",
        "country": "KOR",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 10.0,
        "operator": "KOGAS",
        "year_commissioned": 2014,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # CHINA -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Dapeng LNG",
        "country": "CHN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.0,
        "operator": "CNOOC",
        "year_commissioned": 2006,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Rudong LNG",
        "country": "CHN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 6.5,
        "operator": "PetroChina",
        "year_commissioned": 2011,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Fujian Putian LNG",
        "country": "CHN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 6.3,
        "operator": "CNOOC",
        "year_commissioned": 2009,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Shanghai Yangshan LNG",
        "country": "CHN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.0,
        "operator": "Shenergy",
        "year_commissioned": 2009,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # INDIA -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Dahej LNG",
        "country": "IND",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 17.5,
        "operator": "Petronet LNG",
        "year_commissioned": 2004,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Dabhol LNG",
        "country": "IND",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "GAIL / NTPC",
        "year_commissioned": 2013,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Kochi LNG",
        "country": "IND",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "Petronet LNG",
        "year_commissioned": 2013,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # UNITED KINGDOM -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "South Hook LNG",
        "country": "GBR",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 15.6,
        "operator": "Qatar Terminal Limited",
        "year_commissioned": 2009,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Dragon LNG",
        "country": "GBR",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.6,
        "operator": "Shell / Ancala Partners",
        "year_commissioned": 2009,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Isle of Grain LNG",
        "country": "GBR",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 14.8,
        "operator": "National Grid",
        "year_commissioned": 2005,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # SPAIN -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Barcelona LNG",
        "country": "ESP",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 17.1,
        "operator": "Enagas",
        "year_commissioned": 1969,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Huelva LNG",
        "country": "ESP",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 11.8,
        "operator": "Enagas",
        "year_commissioned": 1988,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Cartagena LNG",
        "country": "ESP",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 11.8,
        "operator": "Enagas",
        "year_commissioned": 1989,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # TURKEY -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Aliaga LNG (EgeGaz)",
        "country": "TUR",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 6.0,
        "operator": "EgeGaz",
        "year_commissioned": 2006,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # BRAZIL -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Guanabara Bay FSRU",
        "country": "BRA",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.7,
        "operator": "Petrobras",
        "year_commissioned": 2009,
        "region": Region.SOUTH_AMERICA,
    },
    {
        "terminal_name": "Bahia FSRU",
        "country": "BRA",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.5,
        "operator": "Petrobras",
        "year_commissioned": 2014,
        "region": Region.SOUTH_AMERICA,
    },
    # -----------------------------------------------------------------------
    # TAIWAN -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Yung An LNG",
        "country": "TWN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 10.5,
        "operator": "CPC Corporation",
        "year_commissioned": 1990,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Taichung LNG",
        "country": "TWN",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 6.0,
        "operator": "CPC Corporation",
        "year_commissioned": 2009,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # SINGAPORE -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Singapore LNG (SLNG)",
        "country": "SGP",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 11.0,
        "operator": "Singapore LNG Corporation",
        "year_commissioned": 2013,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # ITALY -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Panigaglia LNG",
        "country": "ITA",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.5,
        "operator": "Snam",
        "year_commissioned": 1971,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Adriatic LNG (Rovigo)",
        "country": "ITA",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.0,
        "operator": "Adriatic LNG",
        "year_commissioned": 2009,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Piombino FSRU Golar Tundra",
        "country": "ITA",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "Snam",
        "year_commissioned": 2023,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # FRANCE -- Import terminals
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Montoir-de-Bretagne LNG",
        "country": "FRA",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 10.0,
        "operator": "Elengy",
        "year_commissioned": 1980,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Fos Tonkin LNG",
        "country": "FRA",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.0,
        "operator": "Elengy",
        "year_commissioned": 1972,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Dunkerque LNG",
        "country": "FRA",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 13.0,
        "operator": "Dunkerque LNG",
        "year_commissioned": 2016,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # FSRUs -- Key floating import units
    # -----------------------------------------------------------------------
    {
        "terminal_name": "BW Singapore FSRU",
        "country": "SGP",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.0,
        "operator": "BW LNG",
        "year_commissioned": 2015,
        "region": Region.ASIA_PACIFIC,
    },
    {
        "terminal_name": "Hoegh Giant FSRU",
        "country": "BRA",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 6.0,
        "operator": "Hoegh LNG",
        "year_commissioned": 2017,
        "region": Region.SOUTH_AMERICA,
    },
    {
        "terminal_name": "Independence FSRU",
        "country": "LTU",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 4.0,
        "operator": "Klaipedos Nafta",
        "year_commissioned": 2014,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Eemshaven LNG FSRU",
        "country": "NLD",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 8.0,
        "operator": "Gasunie",
        "year_commissioned": 2022,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Wilhelmshaven FSRU",
        "country": "DEU",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "Uniper",
        "year_commissioned": 2022,
        "region": Region.EUROPE,
    },
    {
        "terminal_name": "Brunsbüttel FSRU",
        "country": "DEU",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "RWE",
        "year_commissioned": 2023,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # BELGIUM -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Zeebrugge LNG",
        "country": "BEL",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 9.0,
        "operator": "Fluxys",
        "year_commissioned": 1987,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # PORTUGAL -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Sines LNG",
        "country": "PRT",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.6,
        "operator": "REN Atlantico",
        "year_commissioned": 2003,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # GREECE -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Revithoussa LNG",
        "country": "GRC",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 7.0,
        "operator": "DESFA",
        "year_commissioned": 2000,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # POLAND -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Swinoujscie LNG",
        "country": "POL",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 6.2,
        "operator": "Polskie LNG",
        "year_commissioned": 2015,
        "region": Region.EUROPE,
    },
    # -----------------------------------------------------------------------
    # ARGENTINA -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Escobar FSRU",
        "country": "ARG",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.0,
        "operator": "YPF",
        "year_commissioned": 2011,
        "region": Region.SOUTH_AMERICA,
    },
    {
        "terminal_name": "Golar MK II FLNG",
        "country": "ARG",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.UNDER_CONSTRUCTION,
        "capacity_mtpa": 3.5,
        "operator": "Southern Energy",
        "region": Region.SOUTH_AMERICA,
    },
    {
        "terminal_name": "Argentina LNG Phase 2",
        "country": "ARG",
        "terminal_type": TerminalType.FLNG,
        "function": TerminalFunction.EXPORT,
        "status": TerminalStatus.PLANNED,
        "capacity_mtpa": 12.0,
        "operator": "YPF",
        "region": Region.SOUTH_AMERICA,
    },
    # -----------------------------------------------------------------------
    # PAKISTAN -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Port Qasim FSRU",
        "country": "PAK",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 5.7,
        "operator": "Pakistan GasPort",
        "year_commissioned": 2015,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # BANGLADESH -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Moheshkhali FSRU (Excellence)",
        "country": "BGD",
        "terminal_type": TerminalType.FSRU,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 3.75,
        "operator": "Excelerate Energy",
        "year_commissioned": 2018,
        "region": Region.ASIA_PACIFIC,
    },
    # -----------------------------------------------------------------------
    # THAILAND -- Import terminal
    # -----------------------------------------------------------------------
    {
        "terminal_name": "Map Ta Phut LNG",
        "country": "THA",
        "terminal_type": TerminalType.ONSHORE_IMPORT,
        "function": TerminalFunction.IMPORT,
        "status": TerminalStatus.OPERATIONAL,
        "capacity_mtpa": 11.5,
        "operator": "PTT LNG",
        "year_commissioned": 2011,
        "region": Region.ASIA_PACIFIC,
    },
]

# Sanity check at import time
assert (
    len(_SEED_TERMINALS) >= 80
), f"Seed dataset must contain >= 80 terminals, got {len(_SEED_TERMINALS)}"

# ---------------------------------------------------------------------------
# Fields that every seed record provides (used for source citations)
# ---------------------------------------------------------------------------
_ALWAYS_SOURCED_FIELDS: list[str] = [
    "terminal_name",
    "country",
    "terminal_type",
    "function",
    "status",
]


# ---------------------------------------------------------------------------
# Collector implementation
# ---------------------------------------------------------------------------


class SeedCollector(BaseCollector):
    """Provides a hardcoded baseline of well-known global LNG terminals.

    This collector returns an embedded dataset of ~90 major terminals and
    does not perform any network I/O.  The data is curated from publicly
    available industry reports (IGU, GIIGNL, operator disclosures).
    """

    source_name: str = "seed_dataset"
    source_reliability: SourceReliability = SourceReliability.MEDIUM

    def __init__(self, refresh_mode: RefreshMode | None = None) -> None:
        super().__init__(source_name="seed_dataset", refresh_mode=refresh_mode)

    def fetch_data(self) -> list[dict[str, Any]]:
        """Return the embedded seed terminal list.

        No network access required -- the data is compiled into this module.
        """
        self.logger.info("Returning %d seed terminal records", len(_SEED_TERMINALS))
        return _SEED_TERMINALS

    def parse_records(self, raw_data: list[dict[str, Any]]) -> list[LNGTerminal]:
        """Convert seed dicts into validated LNGTerminal instances."""
        terminals: list[LNGTerminal] = []
        now = datetime.utcnow()

        for record in raw_data:
            try:
                # Build the list of fields this record actually provides
                sourced_fields = list(_ALWAYS_SOURCED_FIELDS)
                for optional_key in (
                    "capacity_mtpa",
                    "operator",
                    "year_commissioned",
                    "region",
                ):
                    if record.get(optional_key) is not None:
                        sourced_fields.append(optional_key)

                terminal = LNGTerminal(
                    terminal_name=record["terminal_name"],
                    country=record["country"],
                    terminal_type=record["terminal_type"],
                    function=record["function"],
                    status=record["status"],
                    capacity_mtpa=record.get("capacity_mtpa"),
                    operator=record.get("operator"),
                    year_commissioned=record.get("year_commissioned"),
                    region=record.get("region"),
                    last_updated=now,
                    sources=[self._create_citation(sourced_fields)],
                )
                terminals.append(terminal)
            except Exception as exc:
                self.logger.warning(
                    "Failed to parse seed record '%s': %s",
                    record.get("terminal_name", "unknown"),
                    exc,
                )

        self.logger.info(
            "Parsed %d / %d seed records successfully",
            len(terminals),
            len(raw_data),
        )
        return terminals
