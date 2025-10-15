"""
Scrapers Package for Marine Safety Module

Provides web scraping functionality for various data sources.
"""

from typing import List

__all__: List[str] = ["base_scraper"]

from worldenergydata.modules.marine_safety.scrapers import base_scraper
