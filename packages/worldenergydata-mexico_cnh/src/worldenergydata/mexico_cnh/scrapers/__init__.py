# ABOUTME: Web scrapers for Mexico CNH module
# ABOUTME: Handles Selenium-based scraping of SIH dashboard and other portals

"""
Mexico CNH Web Scrapers.

Provides Selenium-based web scraping capabilities for extracting data
from Mexico CNH web portals that require JavaScript rendering.
"""

from .sih_scraper import (
    SELENIUM_AVAILABLE,
    DownloadTimeoutError,
    ExportError,
    NavigationError,
    SIHScraper,
    SIHScraperError,
)

__all__ = [
    "SELENIUM_AVAILABLE",
    "SIHScraper",
    "SIHScraperError",
    "NavigationError",
    "ExportError",
    "DownloadTimeoutError",
]
