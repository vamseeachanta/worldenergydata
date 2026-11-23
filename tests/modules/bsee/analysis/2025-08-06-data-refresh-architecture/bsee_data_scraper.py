#!/usr/bin/env python3
"""
BSEE Data Scraper Implementation

This module implements the BSEEDataScraper class for downloading and processing
BSEE data files in-memory without storing large ZIP files locally, addressing
GitHub file size constraints while providing fresh data access.

Key Features:
- In-memory processing of 100+ MB ZIP files
- Direct access to confirmed stable BSEE URLs
- Maintains compatibility with existing binary format
- Respects update schedules (daily/bi-monthly)
- Comprehensive error handling and retry logic
- Memory-efficient streaming download

Based on Task 1 research findings, this implementation uses the web scraping
fallback approach with direct file downloads.
"""

import gc
import hashlib
import io
import logging
import os
import pickle
import tempfile
import time
import warnings
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

import pandas as pd
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BSEEDataSource:
    """Configuration for a BSEE data source."""

    name: str
    url: str
    display_name: str
    update_frequency: str  # 'daily' or 'bi-monthly'
    data_type: str  # 'well', 'production', 'war'
    expected_size_mb: int
    file_encoding: str = "utf-8"
    delimiter: str = "|"  # Common BSEE delimiter


class BSEEDataScraper:
    """
    BSEE Data Scraper for in-memory processing of offshore energy data.

    This class downloads and processes BSEE data files without storing
    large ZIP files locally, addressing GitHub constraints while providing
    access to fresh data that eliminates analysis variance from stale files.
    """

    def __init__(self, max_retries: int = 3, timeout: int = 300):
        """
        Initialize BSEE Data Scraper.

        Args:
            max_retries: Maximum retry attempts for failed downloads
            timeout: Request timeout in seconds (5 minutes default for large files)
        """
        self.max_retries = max_retries
        self.timeout = timeout

        # Data source configurations based on Task 1 research
        self.data_sources = {
            "well_data": BSEEDataSource(
                name="well_data",
                url="https://www.data.bsee.gov/Well/Files/APDRawData.zip",
                display_name="Application for Permit to Drill",
                update_frequency="daily",
                data_type="well",
                expected_size_mb=50,
            ),
            "production_data": BSEEDataSource(
                name="production_data",
                url="https://www.data.bsee.gov/Production/Files/ProductionRawData.zip",
                display_name="Production Data",
                update_frequency="bi-monthly",
                data_type="production",
                expected_size_mb=100,
            ),
            "war_data": BSEEDataSource(
                name="war_data",
                url="https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
                display_name="eWell Submissions WAR",
                update_frequency="daily",
                data_type="war",
                expected_size_mb=75,
            ),
        }

        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "BSEE-Data-Scraper/1.0 (WorldEnergyData)"}
        )

        # Processing statistics
        self.stats = {
            "downloads_attempted": 0,
            "downloads_successful": 0,
            "total_bytes_downloaded": 0,
            "total_processing_time": 0,
            "last_download_times": {},
        }

        # Memory management
        self.max_memory_mb = 500  # Maximum memory usage for single file processing

    def download_and_process(
        self, data_source: str, force_refresh: bool = False
    ) -> Dict:
        """
        Download and process a BSEE data source in memory.

        Args:
            data_source: Key for data source ('well_data', 'production_data', 'war_data')
            force_refresh: Force download even if recently downloaded

        Returns:
            Dictionary containing processed data and metadata
        """
        if data_source not in self.data_sources:
            raise ValueError(
                f"Unknown data source: {data_source}. Available: {list(self.data_sources.keys())}"
            )

        source = self.data_sources[data_source]

        # Check if we need to refresh based on update frequency
        if not force_refresh and not self._needs_refresh(data_source):
            logger.info(f"Skipping {source.display_name} - recently downloaded")
            return {"status": "skipped", "reason": "recently_downloaded"}

        logger.info(f"Starting download and processing: {source.display_name}")
        start_time = time.time()

        try:
            # Download file in memory
            zip_data = self._download_file_to_memory(source)

            # Process ZIP file in memory
            processed_data = self._process_zip_in_memory(zip_data, source)

            # Update statistics
            processing_time = time.time() - start_time
            self.stats["downloads_successful"] += 1
            self.stats["total_processing_time"] += processing_time
            self.stats["last_download_times"][data_source] = datetime.now()

            logger.info(
                f"Successfully processed {source.display_name} in {processing_time:.1f}s"
            )

            # Force garbage collection to free memory
            del zip_data
            gc.collect()

            result = {
                "status": "success",
                "data_source": data_source,
                "display_name": source.display_name,
                "processing_time": processing_time,
                "data": processed_data,
                "download_timestamp": datetime.now().isoformat(),
                "file_count": len(processed_data.get("files", {})),
                "total_records": sum(
                    len(df)
                    for df in processed_data.get("dataframes", {}).values()
                    if df is not None
                ),
            }

            return result

        except Exception as e:
            self.stats["downloads_attempted"] += 1
            error_msg = str(e)
            logger.error(f"Failed to process {source.display_name}: {error_msg}")

            # Enhanced error reporting for better git bash compatibility
            error_context = {
                "status": "error",
                "data_source": data_source,
                "display_name": source.display_name,
                "error": error_msg,
                "error_type": type(e).__name__,
                "download_timestamp": datetime.now().isoformat(),
            }

            # Add environment context for debugging in git bash
            import platform

            error_context["environment"] = {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "cwd": os.getcwd(),
            }

            return error_context

    def _download_file_to_memory(self, source: BSEEDataSource) -> BinaryIO:
        """
        Download file to memory with retry logic and progress monitoring.

        Returns:
            BytesIO object containing the downloaded file data
        """
        self.stats["downloads_attempted"] += 1

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(
                    f"Downloading {source.display_name} (attempt {attempt + 1}/{self.max_retries + 1})"
                )

                # Stream download to handle large files efficiently
                response = self.session.get(
                    source.url, stream=True, timeout=self.timeout
                )
                response.raise_for_status()

                # Check content length
                content_length = response.headers.get("content-length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    logger.info(f"Downloading {size_mb:.1f}MB file...")

                    # Memory usage check
                    if size_mb > self.max_memory_mb:
                        warnings.warn(
                            f"File size ({size_mb:.1f}MB) exceeds memory limit ({self.max_memory_mb}MB)"
                        )

                # Download in chunks to memory
                zip_buffer = io.BytesIO()
                chunk_size = 8192  # 8KB chunks
                downloaded = 0

                for chunk in response.iter_content(chunk=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        zip_buffer.write(chunk)
                        downloaded += len(chunk)

                        # Progress logging for large files
                        if downloaded % (1024 * 1024) == 0:  # Every MB
                            mb_downloaded = downloaded / (1024 * 1024)
                            if content_length:
                                percent = (downloaded / int(content_length)) * 100
                                logger.debug(
                                    f"Downloaded {mb_downloaded:.1f}MB ({percent:.1f}%)"
                                )

                # Verify download
                zip_buffer.seek(0)
                total_mb = downloaded / (1024 * 1024)
                self.stats["total_bytes_downloaded"] += downloaded

                logger.info(f"Download complete: {total_mb:.1f}MB")

                # Verify it's a valid ZIP file
                if not self._verify_zip_header(zip_buffer):
                    raise ValueError("Downloaded file is not a valid ZIP archive")

                zip_buffer.seek(0)
                return zip_buffer

            except (Timeout, ConnectionError) as e:
                if attempt < self.max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Download failed (attempt {attempt + 1}): {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise RequestException(
                        f"Failed to download after {self.max_retries + 1} attempts: {e}"
                    )

            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Download error (attempt {attempt + 1}): {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise

    def _verify_zip_header(self, zip_buffer: BinaryIO) -> bool:
        """Verify the buffer contains a valid ZIP file."""
        zip_buffer.seek(0)
        header = zip_buffer.read(4)
        zip_buffer.seek(0)

        # Check for ZIP file magic bytes
        return header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06")

    def _process_zip_in_memory(
        self, zip_buffer: BinaryIO, source: BSEEDataSource
    ) -> Dict:
        """
        Process ZIP file contents in memory without extracting to disk.

        Returns:
            Dictionary containing processed data and metadata
        """
        logger.info(f"Processing ZIP contents for {source.display_name}")

        processed_data = {
            "source": source.name,
            "files": {},
            "dataframes": {},
            "metadata": {
                "processing_timestamp": datetime.now().isoformat(),
                "total_files": 0,
                "data_files_found": 0,
                "file_types": set(),
            },
        }

        try:
            with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
                file_list = zip_ref.namelist()
                processed_data["metadata"]["total_files"] = len(file_list)

                logger.info(f"Found {len(file_list)} files in ZIP archive")

                # Process each file in the ZIP
                for file_name in file_list:
                    if file_name.endswith("/"):  # Skip directories
                        continue

                    file_ext = Path(file_name).suffix.lower()
                    processed_data["metadata"]["file_types"].add(file_ext)

                    # Process data files (common BSEE formats)
                    if file_ext in [".txt", ".csv", ".dat", ".tsv"]:
                        try:
                            file_data = self._process_data_file(
                                zip_ref, file_name, source
                            )
                            if file_data is not None:
                                processed_data["files"][file_name] = file_data
                                processed_data["metadata"]["data_files_found"] += 1

                                # Create DataFrame if it's structured data
                                if file_data.get("is_structured", False):
                                    df = self._create_dataframe_from_file(
                                        file_data, source
                                    )
                                    if df is not None:
                                        processed_data["dataframes"][file_name] = df

                        except Exception as e:
                            logger.warning(f"Failed to process file {file_name}: {e}")
                            continue
                    else:
                        # Store metadata for non-data files
                        try:
                            file_info = zip_ref.getinfo(file_name)
                            processed_data["files"][file_name] = {
                                "size": file_info.file_size,
                                "compressed_size": file_info.compress_size,
                                "file_type": file_ext,
                                "is_structured": False,
                            }
                        except Exception:
                            continue

                # Convert set to list for JSON serialization
                processed_data["metadata"]["file_types"] = list(
                    processed_data["metadata"]["file_types"]
                )

                logger.info(
                    f"Processed {processed_data['metadata']['data_files_found']} data files"
                )
                return processed_data

        except zipfile.BadZipFile as e:
            raise ValueError(f"Invalid ZIP file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error processing ZIP file: {e}")

    def _process_data_file(
        self, zip_ref: zipfile.ZipFile, file_name: str, source: BSEEDataSource
    ) -> Optional[Dict]:
        """
        Process individual data file from ZIP archive.

        Returns:
            Dictionary containing file data and metadata, or None if processing fails
        """
        try:
            with zip_ref.open(file_name, "r") as file_handle:
                # Read file content
                content = file_handle.read()

                # Decode content
                try:
                    text_content = content.decode(source.file_encoding)
                except UnicodeDecodeError:
                    # Try common fallback encodings
                    for encoding in ["latin-1", "cp1252", "utf-8-sig"]:
                        try:
                            text_content = content.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        logger.warning(f"Could not decode file {file_name}")
                        return None

                # Analyze file structure
                lines = text_content.split("\n")
                non_empty_lines = [line.strip() for line in lines if line.strip()]

                if not non_empty_lines:
                    return None

                # Check if it's structured data (has consistent delimiters)
                is_structured = self._is_structured_data(
                    non_empty_lines, source.delimiter
                )

                file_data = {
                    "file_name": file_name,
                    "size": len(content),
                    "encoding": source.file_encoding,
                    "line_count": len(non_empty_lines),
                    "is_structured": is_structured,
                    "sample_lines": non_empty_lines[:5],  # First 5 lines for inspection
                    "delimiter": source.delimiter if is_structured else None,
                }

                # For structured data, store the full content for DataFrame creation
                if is_structured and len(non_empty_lines) > 1:  # Has header + data
                    file_data["content"] = text_content
                    file_data["estimated_columns"] = len(
                        non_empty_lines[0].split(source.delimiter)
                    )

                return file_data

        except Exception as e:
            logger.warning(f"Error processing data file {file_name}: {e}")
            return None

    def _is_structured_data(self, lines: List[str], delimiter: str) -> bool:
        """
        Determine if the file contains structured (delimited) data.

        Returns:
            True if the file appears to be structured data with consistent delimiters
        """
        if len(lines) < 2:  # Need at least header + one data row
            return False

        # Check if delimiter is present in multiple lines
        delimiter_counts = [
            line.count(delimiter) for line in lines[:10]
        ]  # Check first 10 lines

        if not any(count > 0 for count in delimiter_counts):
            return False

        # Check for consistency in delimiter count (allowing some variation)
        non_zero_counts = [count for count in delimiter_counts if count > 0]
        if len(non_zero_counts) < 2:
            return False

        # Most lines should have similar delimiter counts
        avg_count = sum(non_zero_counts) / len(non_zero_counts)
        consistent_lines = sum(
            1 for count in non_zero_counts if abs(count - avg_count) <= 2
        )

        return (
            consistent_lines / len(non_zero_counts) >= 0.7
        )  # 70% consistency threshold

    def _create_dataframe_from_file(
        self, file_data: Dict, source: BSEEDataSource
    ) -> Optional[pd.DataFrame]:
        """
        Create a pandas DataFrame from structured file data.

        Returns:
            DataFrame containing the file data, or None if creation fails
        """
        try:
            if not file_data.get("is_structured", False) or "content" not in file_data:
                return None

            # Use StringIO to read content into DataFrame
            content_io = io.StringIO(file_data["content"])

            # Try to read as delimited file
            df = pd.read_csv(
                content_io,
                delimiter=source.delimiter,
                low_memory=False,
                encoding_errors="replace",
                on_bad_lines="warn",  # Skip bad lines with warning
            )

            # Basic validation
            if df.empty:
                return None

            logger.debug(
                f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns"
            )
            return df

        except Exception as e:
            logger.warning(
                f"Could not create DataFrame from {file_data['file_name']}: {e}"
            )
            return None

    def _needs_refresh(self, data_source: str) -> bool:
        """
        Check if data source needs refresh based on update frequency.

        Returns:
            True if data should be refreshed, False if recently downloaded
        """
        if data_source not in self.stats["last_download_times"]:
            return True  # Never downloaded

        last_download = self.stats["last_download_times"][data_source]
        source = self.data_sources[data_source]

        # Calculate refresh interval based on update frequency
        if source.update_frequency == "daily":
            refresh_interval = timedelta(
                hours=6
            )  # Refresh every 6 hours for daily updates
        elif source.update_frequency == "bi-monthly":
            refresh_interval = timedelta(
                days=7
            )  # Refresh weekly for bi-monthly updates
        else:
            refresh_interval = timedelta(hours=12)  # Default: 12 hours

        return datetime.now() - last_download > refresh_interval

    def save_processed_data(
        self, processed_data: Dict, output_dir: str, legacy_compatible: bool = True
    ) -> List[str]:
        """
        Save processed data to binary files compatible with existing architecture.

        Args:
            processed_data: Output from download_and_process()
            output_dir: Directory to save binary files (typically data/modules/bsee/bin/)
            legacy_compatible: If True, saves individual DataFrames as separate .bin files
                              like the legacy system. If False, saves entire structure.

        Returns:
            List of paths to saved binary files
        """
        if processed_data["status"] != "success":
            raise ValueError(
                f"Cannot save failed processing result: {processed_data.get('error', 'Unknown error')}"
            )

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        saved_files = []
        data_source = processed_data["data_source"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if legacy_compatible:
            # Legacy-compatible mode: Save individual DataFrames as separate .bin files
            # This matches the behavior of well_data.py and production_data.py

            processed_data_dict = processed_data["data"]
            dataframes = processed_data_dict.get("dataframes", {})

            if not dataframes:
                logger.warning(
                    f"No DataFrames found in processed data for {data_source}"
                )
                # Create a consolidated DataFrame if individual files aren't available
                all_data = []
                for file_name, file_data in processed_data_dict.get(
                    "files", {}
                ).items():
                    if file_data.get("is_structured", False) and "content" in file_data:
                        try:
                            # Parse the content into DataFrame
                            df = self._create_dataframe_from_file(
                                file_data,
                                (
                                    self.data_sources[data_source]
                                    if data_source in self.data_sources
                                    else None
                                ),
                            )
                            if df is not None:
                                all_data.append(df)
                        except Exception as e:
                            logger.warning(
                                f"Failed to create DataFrame from {file_name}: {e}"
                            )

                if all_data:
                    # Concatenate all DataFrames
                    consolidated_df = pd.concat(all_data, ignore_index=True)
                    file_name = f"{data_source}_{timestamp}.bin"
                    file_path = os.path.join(output_dir, file_name)

                    with open(file_path, "wb") as f:
                        pickle.dump(consolidated_df, f)

                    saved_files.append(file_path)
                    logger.info(f"Saved consolidated DataFrame to {file_path}")
            else:
                # Save each DataFrame as a separate .bin file (legacy format)
                for file_label, df in dataframes.items():
                    if df is not None and len(df) > 0:
                        # Generate file name similar to legacy system
                        # Remove file extensions and add timestamp
                        clean_label = Path(file_label).stem
                        file_name = f"{clean_label}_{timestamp}.bin"
                        file_path = os.path.join(output_dir, file_name)

                        # Save DataFrame directly (exact legacy format)
                        with open(file_path, "wb") as f:
                            pickle.dump(df, f)

                        saved_files.append(file_path)
                        logger.info(f"Saved DataFrame ({len(df)} rows) to {file_path}")
        else:
            # Enhanced mode: Save entire processed data structure
            binary_filename = f"{data_source}_{timestamp}_enhanced.bin"
            binary_path = os.path.join(output_dir, binary_filename)

            with open(binary_path, "wb") as f:
                pickle.dump(processed_data["data"], f)

            saved_files.append(binary_path)
            logger.info(f"Saved enhanced data structure to {binary_path}")

        return saved_files

    def save_processed_data_legacy_format(
        self, processed_data: Dict, output_dir: str
    ) -> List[str]:
        """
        Save processed data in exact legacy format for maximum compatibility.

        This method specifically mimics the behavior of:
        - well_data.py: save_eWellAPMRawData_to_binary()
        - production_data.py: save_zip_data_to_binary()

        Args:
            processed_data: Output from download_and_process()
            output_dir: Directory to save binary files

        Returns:
            List of paths to saved binary files
        """
        if processed_data["status"] != "success":
            raise ValueError(
                f"Cannot save failed processing result: {processed_data.get('error', 'Unknown error')}"
            )

        os.makedirs(output_dir, exist_ok=True)
        saved_files = []

        processed_data_dict = processed_data["data"]
        dataframes = processed_data_dict.get("dataframes", {})

        # Process each DataFrame exactly like legacy system
        for file_name, df in dataframes.items():
            if df is not None and len(df) > 0:
                # Create file label exactly like legacy system
                file_label = Path(file_name).stem  # Remove extension
                binary_filename = f"{file_label}.bin"  # Simple .bin extension
                binary_path = os.path.join(output_dir, binary_filename)

                # Save DataFrame directly using pickle (exact legacy method)
                with open(binary_path, "wb") as f:
                    pickle.dump(df, f)

                saved_files.append(binary_path)
                logger.info(f"Saved legacy-format DataFrame to {binary_path}")

        return saved_files

    def get_statistics(self) -> Dict:
        """Get scraper statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats["downloads_successful"]
                / max(self.stats["downloads_attempted"], 1)
            )
            * 100,
            "average_processing_time": self.stats["total_processing_time"]
            / max(self.stats["downloads_successful"], 1),
            "total_data_mb": self.stats["total_bytes_downloaded"] / (1024 * 1024),
        }

    def close(self):
        """Clean up resources."""
        if hasattr(self, "session") and self.session is not None:
            try:
                self.session.close()
            except Exception:
                pass  # Ignore errors during cleanup

        # Force garbage collection
        gc.collect()

    def __del__(self):
        """Ensure cleanup on object destruction."""
        try:
            self.close()
        except Exception:
            pass  # Avoid errors during garbage collection


# Convenience function for quick data access
def download_bsee_data(data_source: str, force_refresh: bool = False) -> Dict:
    """
    Convenience function to download and process BSEE data.

    Args:
        data_source: 'well_data', 'production_data', or 'war_data'
        force_refresh: Force download even if recently downloaded

    Returns:
        Dictionary containing processed data and metadata
    """
    scraper = BSEEDataScraper()
    try:
        result = scraper.download_and_process(data_source, force_refresh)
        return result
    finally:
        scraper.close()


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Test download of well data
    print("Testing BSEE Data Scraper...")
    result = download_bsee_data("well_data", force_refresh=True)

    if result["status"] == "success":
        print(f"Successfully processed {result['display_name']}")
        print(f"Processing time: {result['processing_time']:.1f}s")
        print(f"Files found: {result['file_count']}")
        print(f"Total records: {result['total_records']}")
    else:
        print(f"Processing failed: {result['error']}")
