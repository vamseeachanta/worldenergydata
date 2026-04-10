# ABOUTME: Mexico CNH module for hydrocarbon data from Mexico's regulatory agency
# ABOUTME: Provides access to production, reserves, and field data via SIH dashboard

"""
Mexico CNH (Comision Nacional de Hidrocarburos) Integration Module for WorldEnergyData.

This module provides integration with Mexico's National Hydrocarbons Commission (CNH)
data sources, enabling collection and analysis of Mexican oil and gas data.

Key Features:
- SIH (Sistema de Informacion de Hidrocarburos) dashboard scraping via Selenium
- Production data access (monthly/annual reports)
- Well data collection (Clave del Pozo format)
- Field and block information
- Contract tracking (Round 1, Round 2, etc.)
- Data normalization and validation
- Selenium-based web scraping for dynamic content
- Rate limiting and error recovery

Example usage:
    from worldenergydata.mexico_cnh import MexicoCNH

    # Create module instance
    cnh = MexicoCNH()

    # Configure and route
    cfg = {
        "module": "mexico_cnh",
        "data_types": ["production", "wells"],
        "output": {"directory": "./data/mexico"},
    }
    result = cnh.router(cfg)

    # Or use the scraper directly
    from worldenergydata.mexico_cnh.scrapers import SIHScraper, SELENIUM_AVAILABLE

    if SELENIUM_AVAILABLE:
        with SIHScraper(headless=True) as scraper:
            scraper.navigate_to_production()
            path = scraper.export_production_data(field="CANTARELL")
            logger.info(f"Downloaded to: {path}")
"""

from .mexico_cnh import MexicoCNH
from .scrapers import SELENIUM_AVAILABLE, SIHScraper

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)

__version__ = "1.0.0"
__all__ = ["MexicoCNH", "SIHScraper", "SELENIUM_AVAILABLE"]
