# ABOUTME: USCG MISLE bulk data acquirer for periodic refresh.
# ABOUTME: Downloads, extracts, and verifies MISLE marine casualty data from USCG sources.

"""USCG MISLE bulk data acquirer for periodic refresh.

Downloads the USCG Marine Information for Safety and Law Enforcement (MISLE)
bulk dataset from USCG sources. The MISLE database contains marine casualty
and pollution data for commercial vessels in U.S. waters.

Primary source: USCG Office of Investigations and Casualty Analysis
Fallback source: Data Liberation Project (DLP) historical extracts

Usage:
    uv run python -m worldenergydata.marine_safety.acquirers.uscg_misle_acquirer \
        --output-dir data/modules/marine_safety/raw/uscg_misle [--force]
"""

import argparse
import hashlib
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from worldenergydata.common import get_logger
from worldenergydata.common.data_resolver import get_module_data_safe

logger = get_logger(__name__)

_MARINE_SAFETY_DATA = get_module_data_safe("marine_safety")

# Known USCG MISLE download URLs in order of preference
MISLE_URLS = [
    # Primary: USCG DCO portal bulk dataset
    "https://www.dco.uscg.mil/Portals/9/DCO%20Documents/5p/CG-INV/datasets/MISLE_DATA.zip",
    # Alternate: USCG Homeport attachment
    "https://homeport.uscg.mil/Lists/Content/Attachments/67/MISLE_DATA.zip",
    # Researcher page (may require navigation to find link)
    "https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/"
    "Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/"
    "Marine-Casualty-and-Pollution-Data-for-Researchers/",
]

# Expected file patterns in extracted MISLE data
EXPECTED_FILE_PATTERNS = [
    "*.csv",
    "*.mdb",
    "*.accdb",
    "*.txt",
]

# Request configuration
REQUEST_TIMEOUT = 300  # 5 minutes for large file
CHUNK_SIZE = 8192
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class USCGMISLEAcquirer:
    """Acquirer for USCG MISLE bulk marine casualty data.

    Downloads the MISLE dataset from USCG sources, extracts ZIP contents,
    and verifies the extracted files. Designed for periodic data refresh.

    The USCG may block automated downloads (HTTP 403). When all URLs fail,
    the acquirer documents the issue and provides manual download instructions.

    Attributes:
        output_dir: Directory where data files are stored.
        force: Whether to re-download even if files exist.
        manifest_path: Path to the acquisition manifest JSON.
    """

    def __init__(self, output_dir: Path, force: bool = False):
        """Initialize the MISLE acquirer.

        Args:
            output_dir: Directory to store downloaded and extracted files.
            force: If True, re-download even if files already exist.
        """
        self.output_dir = Path(output_dir)
        self.force = force
        self.manifest_path = self.output_dir / "acquisition_manifest.json"
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """Lazy-initialized HTTP session with browser-like headers."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                }
            )
        return self._session

    def acquire(self) -> Dict[str, Any]:
        """Run the full acquisition pipeline.

        Steps:
            1. Check if data already exists (skip if not --force)
            2. Attempt download from each known URL
            3. Extract ZIP if downloaded
            4. Verify extracted files
            5. Write acquisition manifest

        Returns:
            Acquisition result dictionary with status, file counts, etc.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "status": "pending",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self.output_dir),
            "urls_attempted": [],
            "download_url": None,
            "zip_path": None,
            "extracted_files": [],
            "file_count": 0,
            "total_size_bytes": 0,
            "errors": [],
        }

        # Check existing data
        if not self.force and self._has_existing_data():
            logger.info("MISLE data already exists. Use --force to re-download.")
            result["status"] = "skipped_existing"
            result["extracted_files"] = self._list_data_files()
            result["file_count"] = len(result["extracted_files"])
            return result

        # Attempt download from each URL
        zip_path = None
        for url in MISLE_URLS:
            result["urls_attempted"].append(url)
            logger.info(f"Attempting download from: {url}")

            try:
                zip_path = self._download(url)
                if zip_path and zip_path.exists() and zip_path.stat().st_size > 0:
                    result["download_url"] = url
                    result["zip_path"] = str(zip_path)
                    logger.info(
                        f"Download successful: {zip_path} "
                        f"({zip_path.stat().st_size:,} bytes)"
                    )
                    break
            except Exception as e:
                error_msg = f"Failed to download from {url}: {e}"
                logger.warning(error_msg)
                result["errors"].append(error_msg)

        if zip_path is None or not zip_path.exists():
            result["status"] = "download_failed"
            result["manual_instructions"] = self._get_manual_instructions()
            logger.error(
                "All download URLs failed. Manual download required. "
                "See acquisition_manifest.json for instructions."
            )
            self._write_manifest(result)
            return result

        # Extract ZIP
        try:
            extracted = self._extract_zip(zip_path)
            result["extracted_files"] = extracted
            result["file_count"] = len(extracted)
            result["total_size_bytes"] = sum(
                (self.output_dir / f).stat().st_size
                for f in extracted
                if (self.output_dir / f).exists()
            )
        except Exception as e:
            error_msg = f"ZIP extraction failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            result["status"] = "extraction_failed"
            self._write_manifest(result)
            return result

        # Verify extracted files
        verification = self._verify_extracted(extracted)
        result["verification"] = verification

        if verification["valid"]:
            result["status"] = "success"
            logger.info(
                f"Acquisition complete: {result['file_count']} files, "
                f"{result['total_size_bytes']:,} bytes total"
            )
        else:
            result["status"] = "verification_warning"
            logger.warning(
                f"Data extracted but verification has warnings: "
                f"{verification['warnings']}"
            )

        self._write_manifest(result)
        return result

    @retry(
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        reraise=True,
    )
    def _download(self, url: str) -> Optional[Path]:
        """Download a file from the given URL.

        Args:
            url: URL to download from.

        Returns:
            Path to the downloaded file, or None if not a downloadable file.

        Raises:
            requests.HTTPError: On non-recoverable HTTP errors.
        """
        response = self.session.get(
            url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        content_length = response.headers.get("Content-Length")

        # If we got an HTML page instead of a ZIP, try to discover download link
        if "text/html" in content_type:
            logger.info(f"Got HTML page from {url}, searching for download links...")
            download_url = self._discover_download_link(response.text, url)
            if download_url:
                logger.info(f"Discovered download link: {download_url}")
                return self._download(download_url)
            logger.warning(f"No download link found on page: {url}")
            return None

        # Determine output filename
        filename = "MISLE_DATA.zip"
        content_disp = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disp:
            filename = content_disp.split("filename=")[-1].strip("\"'")

        zip_path = self.output_dir / filename

        # Download with progress logging
        downloaded = 0
        total = int(content_length) if content_length else None
        last_log_time = time.time()

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Log progress every 10 seconds
                    now = time.time()
                    if now - last_log_time > 10:
                        if total:
                            pct = (downloaded / total) * 100
                            logger.info(
                                f"Download progress: {downloaded:,}/{total:,} "
                                f"bytes ({pct:.1f}%)"
                            )
                        else:
                            logger.info(f"Download progress: {downloaded:,} bytes")
                        last_log_time = now

        logger.info(f"Downloaded {downloaded:,} bytes to {zip_path}")
        return zip_path

    def _discover_download_link(
        self, html_content: str, base_url: str
    ) -> Optional[str]:
        """Search an HTML page for MISLE data download links.

        Args:
            html_content: HTML content of the page.
            base_url: Base URL for resolving relative links.

        Returns:
            Absolute URL to the download file, or None if not found.
        """
        try:
            from urllib.parse import urljoin

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")
            download_keywords = [
                "misle",
                "data",
                "download",
                "zip",
                "dataset",
                "casualty",
                "bulk",
            ]

            for link in soup.find_all("a", href=True):
                href = link["href"].lower()
                text = link.get_text(strip=True).lower()
                combined = f"{href} {text}"

                if any(kw in combined for kw in download_keywords) and href.endswith(
                    (".zip", ".csv", ".mdb", ".accdb")
                ):
                    return urljoin(base_url, link["href"])

            # Also check for direct file links anywhere on page
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.lower().endswith(".zip") and "misle" in href.lower():
                    return urljoin(base_url, href)

        except ImportError:
            logger.warning("beautifulsoup4 not installed; cannot parse HTML for links")
        except Exception as e:
            logger.warning(f"Error parsing HTML for download links: {e}")

        return None

    def _extract_zip(self, zip_path: Path) -> List[str]:
        """Extract a ZIP file to the output directory.

        Args:
            zip_path: Path to the ZIP file.

        Returns:
            List of extracted file names (relative to output_dir).

        Raises:
            zipfile.BadZipFile: If the file is not a valid ZIP.
        """
        logger.info(f"Extracting {zip_path}...")

        extracted_files = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Log ZIP contents
            for info in zf.infolist():
                logger.info(
                    f"  ZIP entry: {info.filename} " f"({info.file_size:,} bytes)"
                )

            zf.extractall(self.output_dir)

            for info in zf.infolist():
                if not info.is_dir():
                    extracted_files.append(info.filename)

        logger.info(f"Extracted {len(extracted_files)} files to {self.output_dir}")
        return extracted_files

    def _verify_extracted(self, extracted_files: List[str]) -> Dict[str, Any]:
        """Verify the extracted files meet expectations.

        Args:
            extracted_files: List of extracted file names.

        Returns:
            Verification result with valid flag and details.
        """
        verification: Dict[str, Any] = {
            "valid": True,
            "warnings": [],
            "file_details": [],
        }

        if not extracted_files:
            verification["valid"] = False
            verification["warnings"].append("No files were extracted")
            return verification

        for filename in extracted_files:
            filepath = self.output_dir / filename
            if not filepath.exists():
                verification["warnings"].append(f"File missing: {filename}")
                continue

            size = filepath.stat().st_size
            detail = {
                "filename": filename,
                "size_bytes": size,
                "extension": filepath.suffix.lower(),
            }

            # Check for CSV/TXT files and count lines
            if filepath.suffix.lower() in (".csv", ".txt"):
                try:
                    with open(filepath, "r", encoding="utf-8-sig") as f:
                        line_count = sum(1 for _ in f)
                    detail["line_count"] = line_count
                    if line_count < 2:
                        verification["warnings"].append(
                            f"{filename}: only {line_count} lines (may be empty)"
                        )
                except Exception as e:
                    detail["read_error"] = str(e)

            # Compute checksum
            detail["sha256"] = self._file_sha256(filepath)

            verification["file_details"].append(detail)

        if verification["warnings"]:
            verification["valid"] = len(verification["warnings"]) == 0

        return verification

    def _has_existing_data(self) -> bool:
        """Check if usable data files already exist in the output directory."""
        data_files = self._list_data_files()
        return len(data_files) > 0

    def _list_data_files(self) -> List[str]:
        """List data files (CSV, MDB, ACCDB, TXT) in the output directory."""
        if not self.output_dir.exists():
            return []

        data_extensions = {".csv", ".mdb", ".accdb", ".txt"}
        files = []
        for f in self.output_dir.iterdir():
            if f.is_file() and f.suffix.lower() in data_extensions:
                files.append(f.name)
        return sorted(files)

    @staticmethod
    def _file_sha256(filepath: Path) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _get_manual_instructions() -> Dict[str, Any]:
        """Return manual download instructions when automated download fails."""
        return {
            "reason": (
                "USCG blocks automated downloads (HTTP 403 Forbidden). "
                "Manual browser-based download is required."
            ),
            "option_1_browser": {
                "description": "Download via browser from USCG researcher page",
                "url": (
                    "https://www.dco.uscg.mil/Our-Organization/"
                    "Assistant-Commandant-for-Prevention-Policy-CG-5P/"
                    "Inspections-Compliance-CG-5PC-/"
                    "Office-of-Investigations-Casualty-Analysis/"
                    "Marine-Casualty-and-Pollution-Data-for-Researchers/"
                ),
                "steps": [
                    "Visit the URL above in a web browser",
                    "Look for a download link for MISLE data",
                    "Complete any required researcher forms",
                    "Download the ZIP file",
                    "Extract to the output directory",
                ],
            },
            "option_2_foia": {
                "description": "Submit a FOIA request",
                "email": "cgfoia@uscg.mil",
                "request_text": (
                    "MISLE database records for marine casualties "
                    "(all available years)"
                ),
                "estimated_response": "20-60 days",
            },
            "option_3_data_gov": {
                "description": "Check federal open data portals",
                "urls": [
                    "https://catalog.data.gov/dataset?q=coast+guard+marine+casualty",
                    "https://catalog.data.gov/dataset?q=MISLE",
                ],
            },
            "alternative_data": {
                "description": (
                    "Data Liberation Project historical extracts (1995-2012) "
                    "are available in the dlp_historical directory"
                ),
                "path": str(_MARINE_SAFETY_DATA / "raw" / "dlp_historical") + "/",
                "files": [
                    "Accidents_1995-2012.csv",
                    "Vessels_1995-2012.csv",
                    "Injuries_1995-2012.csv",
                    "Deaths_1995-2012.csv",
                ],
            },
        }

    def _write_manifest(self, result: Dict[str, Any]) -> None:
        """Write acquisition manifest to disk.

        Args:
            result: Acquisition result dictionary.
        """
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Manifest written to {self.manifest_path}")


def main() -> None:
    """CLI entry point for USCG MISLE data acquisition."""
    parser = argparse.ArgumentParser(
        description="Acquire USCG MISLE bulk marine casualty data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Download MISLE data\n"
            "  uv run python -m worldenergydata.marine_safety."
            "acquirers.uscg_misle_acquirer \\\n"
            "    --output-dir data/modules/marine_safety/raw/uscg_misle\n\n"
            "  # Force re-download\n"
            "  uv run python -m worldenergydata.marine_safety."
            "acquirers.uscg_misle_acquirer \\\n"
            "    --output-dir data/modules/marine_safety/raw/uscg_misle "
            "--force\n"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to store downloaded MISLE data files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Re-download even if data files already exist",
    )

    args = parser.parse_args()

    acquirer = USCGMISLEAcquirer(
        output_dir=args.output_dir,
        force=args.force,
    )

    logger.info("=" * 60)
    logger.info("USCG MISLE Data Acquirer")
    logger.info("=" * 60)
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Force re-download: {args.force}")
    logger.info()

    result = acquirer.acquire()

    logger.info()
    logger.info("=" * 60)
    logger.info(f"Status: {result['status']}")
    logger.info(f"Files: {result['file_count']}")
    if result.get("total_size_bytes"):
        size_mb = result["total_size_bytes"] / (1024 * 1024)
        logger.info(f"Total size: {size_mb:.1f} MB")
    if result.get("errors"):
        logger.error(f"Errors: {len(result['errors'])}")
        for err in result["errors"]:
            logger.info(f"  - {err}")
    if result.get("manual_instructions"):
        logger.info()
        logger.info("MANUAL DOWNLOAD REQUIRED")
        logger.info("-" * 40)
        instructions = result["manual_instructions"]
        logger.info(f"Reason: {instructions['reason']}")
        logger.info()
        logger.info("Option 1: Browser download")
        logger.info(f"  URL: {instructions['option_1_browser']['url']}")
        logger.info()
        logger.info("Option 2: FOIA request")
        logger.info(f"  Email: {instructions['option_2_foia']['email']}")
        logger.info()
        logger.info("Alternative: DLP historical data (1995-2012)")
        logger.info(f"  Path: {instructions['alternative_data']['path']}")
    logger.info("=" * 60)

    # Exit with non-zero if download failed
    if result["status"] in ("download_failed", "extraction_failed"):
        sys.exit(1)


if __name__ == "__main__":
    main()
