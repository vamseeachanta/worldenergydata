# ABOUTME: Selenium-based scraper for Mexico CNH SIH dashboard
# ABOUTME: Handles dashboard navigation, data export, and download management

"""
Mexico CNH SIH Dashboard Scraper

Selenium-based scraper for the Sistema de Informacion de Hidrocarburos (SIH)
dashboard operated by Mexico's Comision Nacional de Hidrocarburos.

This module provides automated data extraction from:
- Production dashboard (produccion.hidrocarburos.gob.mx)
- Main SIH portal (sih.hidrocarburos.gob.mx)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Graceful import handling for Selenium
try:
    from selenium import webdriver
    from selenium.common.exceptions import (
        ElementClickInterceptedException,
        ElementNotInteractableException,
        NoSuchElementException,
        StaleElementReferenceException,
        TimeoutException,
    )
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    # Define placeholder types for type hints when Selenium is not installed
    webdriver = None  # type: ignore
    Options = None  # type: ignore
    By = None  # type: ignore
    WebDriverWait = None  # type: ignore
    EC = None  # type: ignore

logger = logging.getLogger(__name__)


class SeleniumNotInstalledError(ImportError):
    """Raised when Selenium is required but not installed."""

    def __init__(self) -> None:
        super().__init__(
            "Selenium is required for SIH scraping. "
            "Install with: pip install selenium webdriver-manager"
        )


class SIHScraperError(Exception):
    """Base exception for SIH scraper errors."""

    pass


class NavigationError(SIHScraperError):
    """Raised when navigation to a page fails."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to navigate to {url}: {reason}")


class ExportError(SIHScraperError):
    """Raised when data export fails."""

    def __init__(self, export_type: str, reason: str) -> None:
        self.export_type = export_type
        self.reason = reason
        super().__init__(f"Failed to export {export_type}: {reason}")


class DownloadTimeoutError(SIHScraperError):
    """Raised when download does not complete within timeout."""

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout
        super().__init__(f"Download did not complete within {timeout} seconds")


class SIHScraper:
    """
    Selenium scraper for CNH SIH dashboard.

    Provides automated interaction with Mexico's hydrocarbon information
    system for data extraction and export functionality.

    Attributes:
        SIH_URL: Main SIH portal URL
        PRODUCTION_URL: Production data dashboard URL

    Example:
        >>> with SIHScraper(headless=True) as scraper:
        ...     scraper.navigate_to_production()
        ...     path = scraper.export_production_data(field="CANTARELL")
        ...     print(f"Downloaded to: {path}")
    """

    SIH_URL = "https://sih.hidrocarburos.gob.mx/"
    PRODUCTION_URL = "https://produccion.hidrocarburos.gob.mx/"

    # Default element selectors (can be updated if dashboard changes)
    SELECTORS = {
        # Production dashboard selectors
        "export_button": "button.export-btn, [data-export], .btn-export",
        "export_excel": "[data-format='xlsx'], button:contains('Excel')",
        "date_from": "input[name='fecha_inicio'], #fecha_inicio, .date-from",
        "date_to": "input[name='fecha_fin'], #fecha_fin, .date-to",
        "field_select": "select[name='campo'], #campo, .field-select",
        "well_select": "select[name='pozo'], #pozo, .well-select",
        "search_button": "button[type='submit'], .btn-search, #buscar",
        "data_table": "table.data-table, .grid-container, #data-grid",
        "loading_spinner": ".loading, .spinner, [data-loading]",
        # Well data selectors
        "well_export_button": ".well-export, #export-wells",
        "well_data_tab": "[data-tab='wells'], .tab-wells",
    }

    # Rate limiting configuration
    MIN_ACTION_DELAY = 1.0  # Minimum seconds between actions
    PAGE_LOAD_DELAY = 2.0  # Additional delay after page loads

    def __init__(
        self,
        headless: bool = True,
        download_dir: Optional[Path] = None,
        implicit_wait: int = 10,
        page_load_timeout: int = 60,
        screenshot_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize the SIH scraper.

        Args:
            headless: Run browser in headless mode (no GUI)
            download_dir: Directory for downloaded files
            implicit_wait: Implicit wait timeout in seconds
            page_load_timeout: Page load timeout in seconds
            screenshot_dir: Directory for error screenshots

        Raises:
            SeleniumNotInstalledError: If Selenium is not installed
        """
        if not SELENIUM_AVAILABLE:
            raise SeleniumNotInstalledError()

        self.headless = headless
        self.download_dir = download_dir or Path("./data/mexico_cnh/downloads")
        self.screenshot_dir = screenshot_dir or Path("./data/mexico_cnh/screenshots")
        self.implicit_wait = implicit_wait
        self.page_load_timeout = page_load_timeout
        self.driver: Optional[webdriver.Chrome] = None
        self._last_action_time: float = 0

        # Ensure directories exist
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"SIHScraper initialized (headless={headless}, "
            f"download_dir={self.download_dir})"
        )

    def __enter__(self) -> "SIHScraper":
        """Context manager entry - starts the browser."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Context manager exit - stops the browser."""
        if exc_type is not None:
            # Take screenshot on error for debugging
            try:
                self.take_screenshot("error_on_exit")
            except Exception:
                pass
        self.stop()

    def _create_chrome_options(self) -> "Options":
        """
        Create Chrome options with proper configuration.

        Returns:
            Configured Chrome options
        """
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        # Standard Chrome arguments for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")

        # Language and locale for Mexican Spanish content
        options.add_argument("--lang=es-MX")
        options.add_experimental_option(
            "prefs",
            {
                "intl.accept_languages": "es-MX,es,en",
            },
        )

        # Download configuration
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(self.download_dir.absolute()),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "plugins.always_open_pdf_externally": True,
            },
        )

        # Disable automation detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        return options

    def start(self) -> None:
        """
        Initialize and start the Chrome WebDriver.

        Raises:
            WebDriverException: If browser fails to start
        """
        if self.driver is not None:
            logger.warning("Driver already started, stopping existing instance")
            self.stop()

        logger.info("Starting Chrome WebDriver...")
        options = self._create_chrome_options()

        try:
            # Try using webdriver-manager if available
            try:
                from webdriver_manager.chrome import ChromeDriverManager

                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except ImportError:
                # Fall back to system chromedriver
                self.driver = webdriver.Chrome(options=options)

            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.set_page_load_timeout(self.page_load_timeout)

            # Execute CDP commands to prevent detection
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
                },
            )

            logger.info("Chrome WebDriver started successfully")

        except Exception as e:
            logger.error(f"Failed to start Chrome WebDriver: {e}")
            raise

    def stop(self) -> None:
        """Close browser and cleanup resources."""
        if self.driver is not None:
            try:
                logger.info("Stopping Chrome WebDriver...")
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error while stopping WebDriver: {e}")
            finally:
                self.driver = None
                logger.info("Chrome WebDriver stopped")

    def _ensure_driver(self) -> None:
        """Ensure driver is initialized."""
        if self.driver is None:
            raise SIHScraperError("WebDriver not initialized. Call start() first.")

    def _rate_limit(self) -> None:
        """Enforce rate limiting between actions."""
        elapsed = time.time() - self._last_action_time
        if elapsed < self.MIN_ACTION_DELAY:
            sleep_time = self.MIN_ACTION_DELAY - elapsed
            time.sleep(sleep_time)
        self._last_action_time = time.time()

    def _wait_for_element(
        self,
        locator: tuple,
        timeout: int = 10,
        condition: str = "visible",
    ) -> Any:
        """
        Wait for an element with specified condition.

        Args:
            locator: Tuple of (By.*, selector)
            timeout: Wait timeout in seconds
            condition: One of 'visible', 'clickable', 'present'

        Returns:
            WebElement when found

        Raises:
            TimeoutException: If element not found within timeout
        """
        self._ensure_driver()
        wait = WebDriverWait(self.driver, timeout)

        conditions = {
            "visible": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable,
            "present": EC.presence_of_element_located,
        }

        ec_condition = conditions.get(condition, EC.visibility_of_element_located)
        return wait.until(ec_condition(locator))

    def _wait_for_page_load(self) -> None:
        """Wait for page to fully load."""
        self._ensure_driver()
        WebDriverWait(self.driver, self.page_load_timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(self.PAGE_LOAD_DELAY)

    def _wait_for_loading_complete(self, timeout: int = 30) -> None:
        """Wait for any loading indicators to disappear."""
        self._ensure_driver()
        try:
            # Wait for loading spinners to disappear
            for selector in [".loading", ".spinner", "[data-loading='true']"]:
                try:
                    WebDriverWait(self.driver, timeout).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                except TimeoutException:
                    pass
        except Exception as e:
            logger.debug(f"Loading check completed with: {e}")

    def _try_click(self, element: Any, retries: int = 3) -> bool:
        """
        Try to click an element with retry logic.

        Args:
            element: WebElement to click
            retries: Number of retry attempts

        Returns:
            True if click succeeded
        """
        for attempt in range(retries):
            try:
                self._rate_limit()
                element.click()
                return True
            except ElementClickInterceptedException:
                logger.debug(f"Click intercepted, attempt {attempt + 1}/{retries}")
                time.sleep(0.5)
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    pass
            except StaleElementReferenceException:
                logger.debug(f"Stale element, attempt {attempt + 1}/{retries}")
                time.sleep(0.5)
            except ElementNotInteractableException:
                logger.debug(
                    f"Element not interactable, attempt {attempt + 1}/{retries}"
                )
                time.sleep(0.5)
        return False

    def navigate_to_sih(self) -> None:
        """
        Navigate to main SIH dashboard.

        Raises:
            NavigationError: If navigation fails
        """
        self._ensure_driver()
        self._rate_limit()

        logger.info(f"Navigating to SIH dashboard: {self.SIH_URL}")

        try:
            self.driver.get(self.SIH_URL)
            self._wait_for_page_load()
            logger.info("Successfully navigated to SIH dashboard")
        except TimeoutException:
            self.take_screenshot("navigation_timeout_sih")
            raise NavigationError(self.SIH_URL, "Page load timeout")
        except Exception as e:
            self.take_screenshot("navigation_error_sih")
            raise NavigationError(self.SIH_URL, str(e))

    def navigate_to_production(self) -> None:
        """
        Navigate to production dashboard.

        Raises:
            NavigationError: If navigation fails
        """
        self._ensure_driver()
        self._rate_limit()

        logger.info(f"Navigating to production dashboard: {self.PRODUCTION_URL}")

        try:
            self.driver.get(self.PRODUCTION_URL)
            self._wait_for_page_load()
            logger.info("Successfully navigated to production dashboard")
        except TimeoutException:
            self.take_screenshot("navigation_timeout_production")
            raise NavigationError(self.PRODUCTION_URL, "Page load timeout")
        except Exception as e:
            self.take_screenshot("navigation_error_production")
            raise NavigationError(self.PRODUCTION_URL, str(e))

    def _set_date_filter(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> None:
        """
        Set date range filters on the dashboard.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        if not start_date and not end_date:
            return

        self._ensure_driver()

        # Try different date input selectors
        date_from_selectors = self.SELECTORS["date_from"].split(", ")
        date_to_selectors = self.SELECTORS["date_to"].split(", ")

        if start_date:
            for selector in date_from_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    element.clear()
                    element.send_keys(start_date)
                    logger.debug(f"Set start date to {start_date}")
                    break
                except NoSuchElementException:
                    continue

        if end_date:
            for selector in date_to_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    element.clear()
                    element.send_keys(end_date)
                    logger.debug(f"Set end date to {end_date}")
                    break
                except NoSuchElementException:
                    continue

    def _set_field_filter(self, field: Optional[str]) -> None:
        """
        Set field filter on the dashboard.

        Args:
            field: Field name to filter by
        """
        if not field:
            return

        self._ensure_driver()
        field_selectors = self.SELECTORS["field_select"].split(", ")

        for selector in field_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                select = Select(element)
                # Try exact match first, then partial match
                try:
                    select.select_by_visible_text(field)
                except NoSuchElementException:
                    # Try partial match
                    for option in select.options:
                        if field.upper() in option.text.upper():
                            select.select_by_visible_text(option.text)
                            break
                logger.debug(f"Set field filter to {field}")
                break
            except NoSuchElementException:
                continue

    def _click_export_button(self, export_format: str = "xlsx") -> None:
        """
        Click the export button to initiate download.

        Args:
            export_format: Export format ('xlsx', 'csv')

        Raises:
            ExportError: If export button not found or click fails
        """
        self._ensure_driver()

        # Try different export button selectors
        export_selectors = self.SELECTORS["export_button"].split(", ")

        for selector in export_selectors:
            try:
                element = self._wait_for_element(
                    (By.CSS_SELECTOR, selector),
                    timeout=10,
                    condition="clickable",
                )
                if self._try_click(element):
                    logger.info("Clicked export button")

                    # Wait for format selection if needed
                    time.sleep(0.5)

                    # Try to select format
                    if export_format == "xlsx":
                        excel_selectors = self.SELECTORS["export_excel"].split(", ")
                        for excel_sel in excel_selectors:
                            try:
                                format_elem = self.driver.find_element(
                                    By.CSS_SELECTOR, excel_sel
                                )
                                self._try_click(format_elem)
                                break
                            except NoSuchElementException:
                                continue

                    return
            except (TimeoutException, NoSuchElementException):
                continue

        self.take_screenshot("export_button_not_found")
        raise ExportError("production", "Export button not found")

    def export_production_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        field: Optional[str] = None,
    ) -> Path:
        """
        Export production data to Excel file.

        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            field: Field name to filter by

        Returns:
            Path to downloaded file

        Raises:
            ExportError: If export fails
            DownloadTimeoutError: If download times out
        """
        self._ensure_driver()
        logger.info(
            f"Exporting production data (start={start_date}, end={end_date}, field={field})"
        )

        try:
            # Navigate if not already on production page
            if self.PRODUCTION_URL not in (self.driver.current_url or ""):
                self.navigate_to_production()

            # Set filters
            self._set_date_filter(start_date, end_date)
            self._set_field_filter(field)

            # Click search if filters were set
            if start_date or end_date or field:
                search_selectors = self.SELECTORS["search_button"].split(", ")
                for selector in search_selectors:
                    try:
                        search_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if self._try_click(search_btn):
                            self._wait_for_loading_complete()
                            break
                    except NoSuchElementException:
                        continue

            # Click export
            self._click_export_button()

            # Wait for download
            return self.wait_for_download()

        except DownloadTimeoutError:
            raise
        except Exception as e:
            self.take_screenshot("export_production_error")
            raise ExportError("production", str(e))

    def export_well_data(self, field: Optional[str] = None) -> Path:
        """
        Export well data to file.

        Args:
            field: Field name to filter by

        Returns:
            Path to downloaded file

        Raises:
            ExportError: If export fails
            DownloadTimeoutError: If download times out
        """
        self._ensure_driver()
        logger.info(f"Exporting well data (field={field})")

        try:
            # Navigate to SIH if not there
            if self.SIH_URL not in (self.driver.current_url or ""):
                self.navigate_to_sih()

            # Click well data tab if available
            well_tab_selectors = self.SELECTORS["well_data_tab"].split(", ")
            for selector in well_tab_selectors:
                try:
                    tab = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if self._try_click(tab):
                        self._wait_for_loading_complete()
                        break
                except NoSuchElementException:
                    continue

            # Set field filter
            self._set_field_filter(field)

            # Click export
            well_export_selectors = self.SELECTORS["well_export_button"].split(", ")
            exported = False

            for selector in well_export_selectors:
                try:
                    export_btn = self._wait_for_element(
                        (By.CSS_SELECTOR, selector),
                        timeout=10,
                        condition="clickable",
                    )
                    if self._try_click(export_btn):
                        exported = True
                        break
                except (TimeoutException, NoSuchElementException):
                    continue

            if not exported:
                # Fall back to general export button
                self._click_export_button()

            # Wait for download
            return self.wait_for_download()

        except DownloadTimeoutError:
            raise
        except Exception as e:
            self.take_screenshot("export_well_error")
            raise ExportError("well", str(e))

    def wait_for_download(self, timeout: int = 60) -> Path:
        """
        Wait for download to complete.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            Path to the downloaded file

        Raises:
            DownloadTimeoutError: If download does not complete in time
        """
        logger.info(f"Waiting for download (timeout={timeout}s)...")

        start_time = time.time()
        download_complete = False
        downloaded_file: Optional[Path] = None

        # Get initial files in download directory
        initial_files = set(self.download_dir.glob("*"))

        while time.time() - start_time < timeout:
            current_files = set(self.download_dir.glob("*"))
            new_files = current_files - initial_files

            # Check for completed downloads (not .crdownload or .tmp)
            for file in new_files:
                if not file.suffix.lower() in [".crdownload", ".tmp", ".part"]:
                    # Verify file is not still being written
                    try:
                        initial_size = file.stat().st_size
                        time.sleep(0.5)
                        if file.stat().st_size == initial_size and initial_size > 0:
                            downloaded_file = file
                            download_complete = True
                            break
                    except FileNotFoundError:
                        continue

            if download_complete:
                break

            time.sleep(1)

        if not download_complete or downloaded_file is None:
            # Check for partial downloads
            partial_files = list(self.download_dir.glob("*.crdownload"))
            if partial_files:
                logger.warning(f"Download incomplete: {partial_files}")
            self.take_screenshot("download_timeout")
            raise DownloadTimeoutError(timeout)

        logger.info(f"Download complete: {downloaded_file}")
        return downloaded_file

    def take_screenshot(self, name: str) -> Optional[Path]:
        """
        Take screenshot for debugging.

        Args:
            name: Screenshot name (without extension)

        Returns:
            Path to screenshot file, or None if failed
        """
        if self.driver is None:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        try:
            self.driver.save_screenshot(str(filepath))
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None

    def get_page_info(self) -> Dict[str, Any]:
        """
        Get current page information for debugging.

        Returns:
            Dictionary with page URL, title, and available elements
        """
        self._ensure_driver()

        info = {
            "url": self.driver.current_url,
            "title": self.driver.title,
            "timestamp": datetime.now().isoformat(),
        }

        # Check for key elements
        for name, selector_str in self.SELECTORS.items():
            selectors = selector_str.split(", ")
            found = False
            for selector in selectors:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, selector)
                    found = True
                    break
                except NoSuchElementException:
                    continue
            info[f"has_{name}"] = found

        return info

    def get_available_fields(self) -> List[str]:
        """
        Get list of available fields from the dropdown.

        Returns:
            List of field names
        """
        self._ensure_driver()

        fields = []
        field_selectors = self.SELECTORS["field_select"].split(", ")

        for selector in field_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                select = Select(element)
                fields = [
                    option.text for option in select.options if option.text.strip()
                ]
                break
            except NoSuchElementException:
                continue

        logger.info(f"Found {len(fields)} available fields")
        return fields
