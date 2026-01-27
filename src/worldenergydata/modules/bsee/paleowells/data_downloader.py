"""
BSEE/BOEM Data Downloader

Downloads and extracts data from BSEE and BOEM data portals.
"""

import logging
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class BSEEDataDownloader:
    """Download and manage BSEE/BOEM data files."""

    # Base URLs for data sources
    BSEE_BASE_URL = "https://www.data.bsee.gov"
    BOEM_BASE_URL = "https://www.data.boem.gov"

    # Common data endpoints
    DATA_SOURCES = {
        "borehole": {
            "url": f"{BSEE_BASE_URL}/Well/Files/BoreholeRawData.zip",
            "description": "Borehole raw data from BSEE",
        },
        "company": {
            "url": f"{BOEM_BASE_URL}/Company/Files/CompanyRawData.zip",
            "description": "Company information from BOEM",
        },
        "lease_owner": {
            "url": f"{BOEM_BASE_URL}/Leasing/Files/LeaseOwnerRawData.zip",
            "description": "Lease ownership data from BOEM",
        },
        "production": {
            "url": f"{BSEE_BASE_URL}/Production/Files/ProductionRawData.zip",
            "description": "Production data from BSEE",
        },
        "field": {
            "url": f"{BOEM_BASE_URL}/Field/Files/FieldRawData.zip",
            "description": "Field information from BOEM",
        },
    }

    def __init__(
        self,
        data_directory: Optional[Path] = None,
        download_timeout: int = 300,
        chunk_size: int = 8192,
    ):
        """
        Initialize the data downloader.

        Args:
            data_directory: Directory to store downloaded files
            download_timeout: Timeout for downloads in seconds
            chunk_size: Chunk size for streaming downloads
        """
        if data_directory is None:
            data_directory = (
                Path(__file__).parent.parent.parent.parent.parent.parent
                / "data"
                / "modules"
                / "bsee"
                / "downloads"
            )

        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.download_timeout = download_timeout
        self.chunk_size = chunk_size

    def download_file(
        self, url: str, output_path: Path, overwrite: bool = False
    ) -> bool:
        """
        Download a file from a URL.

        Args:
            url: URL to download from
            output_path: Path to save the file
            overwrite: Whether to overwrite existing files

        Returns:
            True if successful, False otherwise
        """
        if output_path.exists() and not overwrite:
            logger.info(f"File already exists: {output_path}")
            return True

        try:
            logger.info(f"Downloading from {url}")

            response = requests.get(url, stream=True, timeout=self.download_timeout)
            response.raise_for_status()

            # Get total file size if available
            total_size = int(response.headers.get("content-length", 0))

            # Download with progress tracking
            downloaded = 0
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if (
                                downloaded % (self.chunk_size * 100) == 0
                            ):  # Log every 100 chunks
                                logger.info(f"Download progress: {progress:.1f}%")

            logger.info(f"Successfully downloaded to {output_path}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading {url}: {e}")
            if output_path.exists():
                output_path.unlink()  # Remove partial download
            return False

        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            if output_path.exists():
                output_path.unlink()
            return False

    def extract_zip(
        self, zip_path: Path, extract_to: Optional[Path] = None, overwrite: bool = False
    ) -> bool:
        """
        Extract a ZIP file.

        Args:
            zip_path: Path to the ZIP file
            extract_to: Directory to extract to (defaults to same directory as ZIP)
            overwrite: Whether to overwrite existing files

        Returns:
            True if successful, False otherwise
        """
        if extract_to is None:
            extract_to = zip_path.parent

        extract_to = Path(extract_to)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Check if files already exist
                if not overwrite:
                    for member in zf.namelist():
                        if (extract_to / member).exists():
                            logger.info(
                                f"Extraction skipped - files already exist in {extract_to}"
                            )
                            return True

                # Extract all files
                zf.extractall(extract_to)
                logger.info(f"Extracted {len(zf.namelist())} files to {extract_to}")
                return True

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file {zip_path}: {e}")
            return False

        except Exception as e:
            logger.error(f"Error extracting {zip_path}: {e}")
            return False

    def download_dataset(
        self, dataset_name: str, extract: bool = True, overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Download a specific dataset from BSEE/BOEM.

        Args:
            dataset_name: Name of the dataset (from DATA_SOURCES keys)
            extract: Whether to extract ZIP files after download
            overwrite: Whether to overwrite existing files

        Returns:
            Dictionary with download status and file paths
        """
        if dataset_name not in self.DATA_SOURCES:
            raise ValueError(
                f"Unknown dataset: {dataset_name}. Available: {list(self.DATA_SOURCES.keys())}"
            )

        dataset_info = self.DATA_SOURCES[dataset_name]
        url = dataset_info["url"]

        # Create dataset-specific directory
        dataset_dir = self.data_directory / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # Download file
        filename = url.split("/")[-1]
        download_path = dataset_dir / filename

        result = {
            "dataset": dataset_name,
            "description": dataset_info["description"],
            "url": url,
            "download_path": str(download_path),
            "download_success": False,
            "extract_success": False,
            "extracted_files": [],
        }

        # Download
        if self.download_file(url, download_path, overwrite):
            result["download_success"] = True

            # Extract if requested
            if extract and zipfile.is_zipfile(download_path):
                if self.extract_zip(download_path, dataset_dir, overwrite):
                    result["extract_success"] = True

                    # List extracted files
                    extracted = [
                        f
                        for f in dataset_dir.iterdir()
                        if f.is_file() and f != download_path
                    ]
                    result["extracted_files"] = [str(f) for f in extracted]

        return result

    def download_all_datasets(
        self,
        datasets: Optional[List[str]] = None,
        extract: bool = True,
        overwrite: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Download multiple datasets.

        Args:
            datasets: List of dataset names to download. If None, downloads all.
            extract: Whether to extract ZIP files
            overwrite: Whether to overwrite existing files

        Returns:
            List of download results
        """
        if datasets is None:
            datasets = list(self.DATA_SOURCES.keys())

        results = []
        for dataset in datasets:
            logger.info(f"Processing dataset: {dataset}")
            result = self.download_dataset(dataset, extract, overwrite)
            results.append(result)

            # Small delay between downloads to be respectful
            time.sleep(1)

        # Summary
        successful = sum(1 for r in results if r["download_success"])
        logger.info(f"Downloaded {successful}/{len(results)} datasets successfully")

        return results

    def get_latest_data_info(self) -> Dict[str, Any]:
        """
        Get information about the latest available data without downloading.

        Returns:
            Dictionary with dataset information
        """
        info = {}

        for name, source in self.DATA_SOURCES.items():
            try:
                response = requests.head(source["url"], timeout=10)

                info[name] = {
                    "description": source["description"],
                    "url": source["url"],
                    "available": response.status_code == 200,
                    "size": response.headers.get("content-length", "Unknown"),
                    "last_modified": response.headers.get("last-modified", "Unknown"),
                }

            except Exception as e:
                info[name] = {
                    "description": source["description"],
                    "url": source["url"],
                    "available": False,
                    "error": str(e),
                }

        return info
