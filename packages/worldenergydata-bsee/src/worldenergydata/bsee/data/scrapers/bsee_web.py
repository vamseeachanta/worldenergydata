"""
BSEE Web Scraper Module

This module handles downloading BSEE data files directly from their URLs
into memory, avoiding the need to store large zip files in the repository.
"""

import time
from typing import ByteString, Optional

import requests
from loguru import logger


class BSEEWebScraper:
    """
    Web scraper for BSEE data files.

    Downloads zip files directly into memory for processing without
    storing them on disk, solving the GitHub file size limit issue.
    """

    # BSEE data source URLs.
    #
    # The authoritative index of every bulk download is the "portal"
    # page (issue #9 / #12); when BSEE relocates a file the old URL
    # returns HTTP 200 with an HTML page instead of a 404, so callers
    # must classify payload content before zip parsing (issue #267,
    # see worldenergydata.bsee.data.refresh.payload).
    #
    # 2026-06-10 live-verified corrections (issue #267):
    #   deepwater_structure moved /Platform/Files/ -> /Other/Files/
    #   pipeline_location:  PipeLocAllRawData.zip -> PipeLocRawData.zip
    URLS = {
        "well": "https://www.data.bsee.gov/Well/Files/APDRawData.zip",
        "production": "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip",
        "war": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
        "portal": "https://www.data.bsee.gov/Main/RawData.aspx",
        "platform": "https://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip",
        "pipeline_permit": "https://www.data.bsee.gov/Pipeline/Files/PipePermRawData.zip",
        "deepwater_structure": "https://www.data.bsee.gov/Other/Files/PermStrucRawData.zip",
        "pipeline_location": "https://www.data.bsee.gov/Pipeline/Files/PipeLocRawData.zip",
        "deepqual": "https://www.data.bsee.gov/Other/Files/DeepQualRawData.zip",
    }

    # Request configuration
    # Dynamic timeouts based on expected file sizes
    TIMEOUTS = {
        "well": 600,  # 10 minutes for ~5-10 MB files
        "production": 1200,  # 20 minutes for ~15-50 MB files
        "war": 2400,  # 40 minutes for ~100+ MB files
        "default": 600,  # 10 minutes default
        "platform": 600,  # 10 minutes
        "pipeline_permit": 600,  # 10 minutes
        "deepwater_structure": 600,  # 10 minutes
        "pipeline_location": 900,  # 15 minutes (larger file)
        "deepqual": 600,  # 10 minutes (small file)
    }
    CHUNK_SIZE = 32768  # 32KB chunks for faster streaming
    MAX_RETRIES = 5  # Increased retries for large files
    RETRY_DELAY = 10  # Increased delay between retries
    PROGRESS_INTERVAL = 5 * 1024 * 1024  # Log progress every 5MB

    def __init__(self):
        """Initialize the web scraper with session management."""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "WorldEnergyData/1.0 (BSEE Data Refresh)",
                "Accept": "application/zip, application/octet-stream, */*",
            }
        )

    def download_zip_to_memory(
        self, url: str, max_retries: int = None, data_type: str = "default"
    ) -> Optional[ByteString]:
        """
        Download a zip file directly into memory with dynamic timeout handling.

        Args:
            url: URL of the zip file to download
            max_retries: Maximum number of retry attempts
            data_type: Type of data being downloaded (well, production, war) for timeout selection

        Returns:
            Bytes of the zip file content or None if failed
        """
        max_retries = max_retries or self.MAX_RETRIES
        timeout = self.TIMEOUTS.get(data_type, self.TIMEOUTS["default"])

        logger.info(
            f"Downloading {data_type} data with {timeout}s timeout and {max_retries} max retries"
        )

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Downloading from {url} (attempt {attempt + 1}/{max_retries})"
                )
                logger.info(f"Using timeout: {timeout} seconds for {data_type} data")

                # Use adaptive timeout - increase on retry
                adaptive_timeout = timeout * (
                    1 + attempt * 0.5
                )  # Increase timeout by 50% each retry
                logger.info(
                    f"Adaptive timeout for attempt {attempt + 1}: {adaptive_timeout} seconds"
                )

                # Stream the download to handle large files efficiently
                response = self.session.get(url, stream=True, timeout=adaptive_timeout)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if (
                    "zip" not in content_type.lower()
                    and "octet-stream" not in content_type.lower()
                ):
                    logger.warning(f"Unexpected content type: {content_type}")

                # Get file size if available
                file_size = int(response.headers.get("Content-Length", 0))
                if file_size > 0:
                    logger.info(f"File size: {file_size / (1024*1024):.2f} MB")

                # Download in chunks to memory
                chunks = []
                downloaded = 0
                last_progress_log = 0

                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    if chunk:
                        chunks.append(chunk)
                        downloaded += len(chunk)

                        # Progress logging for large files
                        if (
                            file_size > 0
                            and (downloaded - last_progress_log)
                            >= self.PROGRESS_INTERVAL
                        ):
                            progress = (downloaded / file_size) * 100
                            logger.info(
                                f"Download progress: {progress:.1f}%"
                                f" ({downloaded/(1024*1024):.1f} MB"
                                f" / {file_size/(1024*1024):.1f} MB)"
                            )
                            last_progress_log = downloaded

                # Combine all chunks
                data = b"".join(chunks)
                logger.info(f"Successfully downloaded {len(data) / (1024*1024):.2f} MB")

                return data

            except requests.exceptions.Timeout:
                logger.error(f"Timeout downloading from {url}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error downloading from {url}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)

            except Exception as e:
                logger.error(f"Unexpected error downloading from {url}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Failed to download from {url} after {max_retries} attempts")
        return None

    def download_well_data(self) -> Optional[ByteString]:
        """
        Download well APD data.

        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE well data (APD)")
        return self.download_zip_to_memory(self.URLS["well"], data_type="well")

    def download_production_data(self) -> Optional[ByteString]:
        """
        Download production data.

        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE production data")
        return self.download_zip_to_memory(
            self.URLS["production"], data_type="production"
        )

    def download_war_data(self) -> Optional[ByteString]:
        """
        Download WAR (Well Activity Report) data.

        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE WAR data")
        return self.download_zip_to_memory(self.URLS["war"], data_type="war")

    def download_platform_data(self) -> Optional[ByteString]:
        """
        Download platform structure data.

        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE platform structure data")
        return self.download_zip_to_memory(self.URLS["platform"], data_type="platform")

    def download_pipeline_permit_data(self) -> Optional[ByteString]:
        """
        Download pipeline permit data.

        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE pipeline permit data")
        return self.download_zip_to_memory(
            self.URLS["pipeline_permit"], data_type="pipeline_permit"
        )

    def download_deepwater_structure_data(self) -> Optional[ByteString]:
        """
        Download deepwater permanent structure data.

        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE deepwater structure data")
        return self.download_zip_to_memory(
            self.URLS["deepwater_structure"], data_type="deepwater_structure"
        )

    def download_pipeline_location_data(self) -> Optional[ByteString]:
        """
        Download pipeline location data.

        Returns:
            Bytes of the zip file or None if failed
        """
        logger.info("Downloading BSEE pipeline location data")
        return self.download_zip_to_memory(
            self.URLS["pipeline_location"], data_type="pipeline_location"
        )

    def verify_url_accessibility(self, url: str) -> bool:
        """
        Verify that a URL is accessible.

        Args:
            url: URL to check

        Returns:
            True if URL is accessible, False otherwise
        """
        try:
            response = self.session.head(url, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking URL {url}: {str(e)}")
            return False

    def verify_all_sources(self) -> dict:
        """
        Verify accessibility of all BSEE data sources.

        Returns:
            Dictionary with URL accessibility status
        """
        logger.info("Verifying BSEE data source accessibility")
        results = {}

        for name, url in self.URLS.items():
            accessible = self.verify_url_accessibility(url)
            results[name] = {"url": url, "accessible": accessible}
            logger.info(f"{name}: {'✓' if accessible else '✗'} {url}")

        return results

    def get_file_info(self, url: str) -> dict:
        """
        Get information about a file without downloading it.

        Args:
            url: URL of the file

        Returns:
            Dictionary with file information
        """
        try:
            response = self.session.head(url, timeout=30)
            response.raise_for_status()

            info = {
                "url": url,
                "content_type": response.headers.get("Content-Type", "unknown"),
                "content_length": int(response.headers.get("Content-Length", 0)),
                "last_modified": response.headers.get("Last-Modified", "unknown"),
                "etag": response.headers.get("ETag", "unknown"),
            }

            if info["content_length"] > 0:
                info["size_mb"] = info["content_length"] / (1024 * 1024)

            return info

        except Exception as e:
            logger.error(f"Error getting file info for {url}: {str(e)}")
            return {"url": url, "error": str(e)}

    def close(self):
        """Close the session."""
        self.session.close()
