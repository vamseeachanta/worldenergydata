"""
Marine Safety Module - Offshore Energy Industry Safety Incident Tracking

This module provides comprehensive tracking and analysis of marine safety incidents
in the offshore energy industry, including oil rigs, wind farms, and related vessels.

Data Sources:
    - USCG MISLE: US Coast Guard Marine Information for Safety and Law Enforcement
    - NTSB: National Transportation Safety Board marine accident investigations
    - BSEE: Bureau of Safety and Environmental Enforcement offshore incidents
    - MAIB: UK Marine Accident Investigation Branch
    - TSB: Canada Transportation Safety Board

Module Structure:
    scrapers/       Web scrapers for each data source
        uscg_scraper.py     USCG MISLE database scraper
        ntsb_scraper.py     NTSB marine accident scraper
        maib_scraper.py     UK MAIB report scraper
    database/       Database operations
        init_db.py          Schema initialization
        db_manager.py       Connection and session management
        models.py           SQLAlchemy models
    analysis/       Incident analysis
        cause_analyzer.py   Root cause analysis
        trend_analyzer.py   Trend detection
    importers/      Data importers
        maib_importer.py    MAIB data import
    processors/     Data processing
        normalizer.py       Data normalization
    utils/          Utility functions

Example usage:
    # Import submodules
    from worldenergydata.modules.marine_safety import (
        config,
        constants,
        exceptions,
        database,
        scrapers,
        utils,
    )

    # Use USCG scraper
    from worldenergydata.modules.marine_safety.scrapers.uscg_scraper import (
        USCGMarineCasualtyScraper
    )
    scraper = USCGMarineCasualtyScraper(start_year=2020)
    incidents = scraper.scrape()

    # Database operations
    from worldenergydata.modules.marine_safety.database.db_manager import get_db_manager
    db = get_db_manager()

CLI usage:
    worldenergydata marine-safety scrape uscg --start-year 2020
    worldenergydata marine-safety db init --dev-mode
    worldenergydata marine-safety stats --source all
    worldenergydata marine-safety export csv --output incidents.csv

Version: 1.0.0
Author: WorldEnergyData Team
License: MIT
"""

from typing import List

__version__ = "1.0.0"
__author__ = "WorldEnergyData Team"
__all__: List[str] = [
    "config",
    "constants",
    "exceptions",
    "database",
    "scrapers",
    "utils",
]

# Module-level exports
from worldenergydata.modules.marine_safety import config
from worldenergydata.modules.marine_safety import constants
from worldenergydata.modules.marine_safety import exceptions
from worldenergydata.modules.marine_safety import database
from worldenergydata.modules.marine_safety import scrapers
from worldenergydata.modules.marine_safety import utils
