"""
Chunk-based Change Detection and Management for BSEE Data Refresh

This module implements an intelligent chunking mechanism that tracks data changes
and avoids re-downloading unchanged portions of BSEE datasets.
"""

import hashlib
import io
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, ByteString, Dict, List, Optional, Tuple

import pandas as pd
import requests
from loguru import logger


class ChunkMetadata:
    """Metadata for tracking data chunks and changes."""

    def __init__(
        self,
        chunk_id: str,
        checksum: str,
        timestamp: datetime,
        size_bytes: int,
        row_range: Optional[Tuple[int, int]] = None,
    ):
        """
        Initialize chunk metadata.

        Args:
            chunk_id: Unique identifier for the chunk
            checksum: Hash of the chunk content
            timestamp: Last update timestamp
            size_bytes: Size of the chunk in bytes
            row_range: Optional tuple of (start_row, end_row) for data chunks
        """
        self.chunk_id = chunk_id
        self.checksum = checksum
        self.timestamp = timestamp
        self.size_bytes = size_bytes
        self.row_range = row_range
        self.is_changed = False
        self.download_required = True

    def to_dict(self) -> Dict:
        """Convert metadata to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "checksum": self.checksum,
            "timestamp": self.timestamp.isoformat(),
            "size_bytes": self.size_bytes,
            "row_range": self.row_range,
            "is_changed": self.is_changed,
            "download_required": self.download_required,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChunkMetadata":
        """Create ChunkMetadata from dictionary."""
        metadata = cls(
            chunk_id=data["chunk_id"],
            checksum=data["checksum"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            size_bytes=data["size_bytes"],
            row_range=data.get("row_range"),
        )
        metadata.is_changed = data.get("is_changed", False)
        metadata.download_required = data.get("download_required", True)
        return metadata


class ChunkManager:
    """
    Manages chunk-based data refresh to minimize redundant downloads.

    This class implements:
    - HTTP HEAD requests to check file changes
    - ETag/Last-Modified tracking
    - Chunk-level checksums for change detection
    - Incremental data updates
    - Smart caching strategies
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the chunk manager.

        Args:
            cache_dir: Directory for storing chunk metadata and cache
        """
        if cache_dir is None:
            # Default cache location
            self.cache_dir = Path.home() / ".worldenergydata" / "cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "chunk_metadata.json"
        self.chunk_cache_dir = self.cache_dir / "chunks"
        self.chunk_cache_dir.mkdir(parents=True, exist_ok=True)

        # Load existing metadata
        self.metadata: Dict[str, Dict[str, ChunkMetadata]] = self._load_metadata()

        # Configuration
        self.chunk_size_mb = 10  # Size of each chunk in MB
        self.chunk_size_bytes = self.chunk_size_mb * 1024 * 1024
        self.row_chunk_size = 50000  # Rows per chunk for large CSV files
        self.ttl_hours = 24  # Time-to-live for cached chunks

        logger.info(f"ChunkManager initialized with cache at {self.cache_dir}")

    def check_remote_changes(self, url: str, data_type: str) -> Dict[str, Any]:
        """
        Check if remote file has changed using HTTP HEAD request.

        Args:
            url: URL of the remote file
            data_type: Type of data (well, production, war)

        Returns:
            Dictionary with change detection results
        """
        logger.info(f"Checking remote changes for {data_type} at {url}")

        try:
            # Send HEAD request to get metadata without downloading
            response = requests.head(url, timeout=30)
            response.raise_for_status()

            # Extract metadata
            remote_metadata = {
                "etag": response.headers.get("ETag", "").strip('"'),
                "last_modified": response.headers.get("Last-Modified", ""),
                "content_length": int(response.headers.get("Content-Length", 0)),
                "content_type": response.headers.get("Content-Type", ""),
            }

            # Get cached metadata
            cached = self.metadata.get(data_type, {})
            cached_metadata = cached.get("file_metadata", {}) if cached else {}

            # Check for changes
            has_changed = False
            change_reasons = []

            # Check ETag (most reliable)
            if remote_metadata["etag"] and cached_metadata.get("etag"):
                if remote_metadata["etag"] != cached_metadata["etag"]:
                    has_changed = True
                    change_reasons.append("ETag mismatch")

            # Check Last-Modified
            if remote_metadata["last_modified"] and cached_metadata.get(
                "last_modified"
            ):
                if remote_metadata["last_modified"] != cached_metadata["last_modified"]:
                    has_changed = True
                    change_reasons.append("Last-Modified changed")

            # Check file size
            if remote_metadata["content_length"] and cached_metadata.get(
                "content_length"
            ):
                if (
                    remote_metadata["content_length"]
                    != cached_metadata["content_length"]
                ):
                    has_changed = True
                    change_reasons.append("File size changed")

            # If no cached metadata, consider it changed
            if not cached_metadata:
                has_changed = True
                change_reasons.append("No cached metadata")

            result = {
                "has_changed": has_changed,
                "change_reasons": change_reasons,
                "remote_metadata": remote_metadata,
                "cached_metadata": cached_metadata,
                "requires_full_download": has_changed,
            }

            logger.info(
                f"{data_type}: {'Changed' if has_changed else 'Unchanged'} - {change_reasons}"
            )

            return result

        except requests.RequestException as e:
            logger.error(f"Error checking remote changes: {str(e)}")
            # On error, assume changed to ensure fresh data
            return {
                "has_changed": True,
                "change_reasons": ["HEAD request failed"],
                "requires_full_download": True,
            }

    def download_with_chunks(
        self, url: str, data_type: str, force_refresh: bool = False
    ) -> Optional[ByteString]:
        """
        Download data with intelligent chunk management.

        Args:
            url: URL to download from
            data_type: Type of data (well, production, war)
            force_refresh: Force full download even if unchanged

        Returns:
            Complete data bytes or None if failed
        """
        # Check for remote changes first
        if not force_refresh:
            change_info = self.check_remote_changes(url, data_type)

            if not change_info["has_changed"]:
                # Try to load from cache
                cached_data = self._load_from_cache(data_type)
                if cached_data:
                    logger.info(f"Using cached data for {data_type} (unchanged)")
                    return cached_data

        # Perform chunked download
        logger.info(f"Starting chunked download for {data_type}")

        try:
            # Use Range requests for chunked download
            response = requests.head(url, timeout=30)
            file_size = int(response.headers.get("Content-Length", 0))

            if file_size == 0:
                # Fallback to regular download if size unknown
                return self._download_full(url, data_type)

            # Check if server supports range requests
            accept_ranges = response.headers.get("Accept-Ranges", "none")
            if accept_ranges == "none":
                logger.info(
                    "Server doesn't support range requests, downloading full file"
                )
                return self._download_full(url, data_type)

            # Download in chunks
            chunks = []
            chunk_metadata = []
            num_chunks = (
                file_size + self.chunk_size_bytes - 1
            ) // self.chunk_size_bytes

            logger.info(
                f"File size: {file_size / (1024*1024):.2f} MB, downloading in {num_chunks} chunks"
            )

            for i in range(num_chunks):
                start_byte = i * self.chunk_size_bytes
                end_byte = min((i + 1) * self.chunk_size_bytes - 1, file_size - 1)

                # Check if chunk exists in cache
                chunk_id = f"{data_type}_chunk_{i}"
                cached_chunk = self._get_cached_chunk(chunk_id, data_type)

                if cached_chunk and not force_refresh:
                    logger.info(f"Using cached chunk {i+1}/{num_chunks}")
                    chunks.append(cached_chunk)
                else:
                    # Download chunk
                    logger.info(
                        f"Downloading chunk {i+1}/{num_chunks} ({start_byte}-{end_byte})"
                    )

                    headers = {"Range": f"bytes={start_byte}-{end_byte}"}
                    chunk_response = requests.get(url, headers=headers, timeout=300)
                    chunk_response.raise_for_status()

                    chunk_data = chunk_response.content
                    chunks.append(chunk_data)

                    # Cache the chunk
                    self._cache_chunk(chunk_id, chunk_data, data_type)

                    # Create metadata
                    checksum = hashlib.sha256(chunk_data).hexdigest()
                    meta = ChunkMetadata(
                        chunk_id=chunk_id,
                        checksum=checksum,
                        timestamp=datetime.now(),
                        size_bytes=len(chunk_data),
                    )
                    chunk_metadata.append(meta)

            # Combine chunks
            complete_data = b"".join(chunks)

            # Update metadata
            self._update_metadata(data_type, chunk_metadata, response.headers)

            # Cache complete file
            self._cache_complete_file(data_type, complete_data)

            logger.info(
                f"Successfully downloaded {len(complete_data) / (1024*1024):.2f} MB in chunks"
            )
            return complete_data

        except Exception as e:
            logger.error(f"Error in chunked download: {str(e)}")
            # Fallback to regular download
            return self._download_full(url, data_type)

    def _download_full(self, url: str, data_type: str) -> Optional[ByteString]:
        """
        Perform a full download without chunking.

        Args:
            url: URL to download from
            data_type: Type of data

        Returns:
            Complete data bytes or None if failed
        """
        logger.info(f"Performing full download for {data_type}")

        try:
            response = requests.get(url, timeout=1200, stream=True)
            response.raise_for_status()

            # Download with progress tracking
            chunks = []
            downloaded = 0
            file_size = int(response.headers.get("Content-Length", 0))

            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    chunks.append(chunk)
                    downloaded += len(chunk)

                    if file_size > 0 and downloaded % (5 * 1024 * 1024) == 0:
                        progress = (downloaded / file_size) * 100
                        logger.info(f"Download progress: {progress:.1f}%")

            complete_data = b"".join(chunks)

            # Cache the complete file
            self._cache_complete_file(data_type, complete_data)

            # Update metadata
            self._update_file_metadata(data_type, response.headers, complete_data)

            return complete_data

        except Exception as e:
            logger.error(f"Error in full download: {str(e)}")
            return None

    def process_incremental_changes(
        self,
        zip_data: ByteString,
        data_type: str,
        previous_data: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Process only changed portions of data.

        Args:
            zip_data: New zip file data
            data_type: Type of data
            previous_data: Previously processed DataFrame

        Returns:
            Updated DataFrame with incremental changes applied
        """
        logger.info(f"Processing incremental changes for {data_type}")

        try:
            # Extract new data
            new_data_dict = self._extract_zip_data(zip_data)

            if not new_data_dict:
                logger.error("No data extracted from zip")
                return previous_data if previous_data is not None else pd.DataFrame()

            # Get the main data file (usually the first/largest)
            main_file = list(new_data_dict.keys())[0]
            new_df = new_data_dict[main_file]

            if previous_data is None or previous_data.empty:
                logger.info("No previous data, using full new dataset")
                return new_df

            # Identify changes using checksums on chunks
            chunk_changes = self._identify_dataframe_changes(previous_data, new_df)

            if not chunk_changes["has_changes"]:
                logger.info("No changes detected in data")
                return previous_data

            # Apply incremental updates
            if chunk_changes["type"] == "append":
                # New rows added at the end
                logger.info(f"Appending {chunk_changes['new_rows']} new rows")
                updated_df = pd.concat(
                    [previous_data, new_df.iloc[chunk_changes["start_index"] :]],
                    ignore_index=True,
                )

            elif chunk_changes["type"] == "update":
                # Rows updated in place
                logger.info(f"Updating {len(chunk_changes['changed_indices'])} rows")
                updated_df = previous_data.copy()
                for idx in chunk_changes["changed_indices"]:
                    if idx < len(new_df):
                        updated_df.iloc[idx] = new_df.iloc[idx]

            else:
                # Full replacement needed
                logger.info("Full data replacement required")
                updated_df = new_df

            return updated_df

        except Exception as e:
            logger.error(f"Error processing incremental changes: {str(e)}")
            return new_df if "new_df" in locals() else pd.DataFrame()

    def _extract_zip_data(self, zip_data: ByteString) -> Dict[str, pd.DataFrame]:
        """Extract data from zip file."""
        data_dict = {}

        try:
            zip_buffer = io.BytesIO(zip_data)
            with zipfile.ZipFile(zip_buffer, "r") as zip_file:
                for filename in zip_file.namelist():
                    if filename.endswith(".txt") or filename.endswith(".csv"):
                        with zip_file.open(filename) as file:
                            df = pd.read_csv(file, low_memory=False)
                            data_dict[filename] = df
        except Exception as e:
            logger.error(f"Error extracting zip data: {str(e)}")

        return data_dict

    def _identify_dataframe_changes(
        self, old_df: pd.DataFrame, new_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Identify changes between two DataFrames.

        Returns:
            Dictionary with change information
        """
        changes = {
            "has_changes": False,
            "type": None,
            "changed_indices": [],
            "new_rows": 0,
            "start_index": 0,
        }

        # Quick checks
        if old_df.shape == new_df.shape:
            # Same size, check for updates
            if old_df.equals(new_df):
                return changes

            # Find changed rows
            changed_mask = ~(old_df == new_df).all(axis=1)
            changed_indices = changed_mask[changed_mask].index.tolist()

            changes["has_changes"] = True
            changes["type"] = "update"
            changes["changed_indices"] = changed_indices

        elif len(new_df) > len(old_df):
            # Check if it's an append operation
            if len(old_df) > 0 and old_df.equals(new_df.iloc[: len(old_df)]):
                changes["has_changes"] = True
                changes["type"] = "append"
                changes["new_rows"] = len(new_df) - len(old_df)
                changes["start_index"] = len(old_df)
            else:
                changes["has_changes"] = True
                changes["type"] = "full_replacement"
        else:
            changes["has_changes"] = True
            changes["type"] = "full_replacement"

        return changes

    def _load_metadata(self) -> Dict[str, Dict]:
        """Load chunk metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)

                # Convert to ChunkMetadata objects
                result = {}
                for data_type, type_data in data.items():
                    result[data_type] = {}
                    if "chunks" in type_data:
                        result[data_type]["chunks"] = {
                            chunk_id: ChunkMetadata.from_dict(chunk_data)
                            for chunk_id, chunk_data in type_data["chunks"].items()
                        }
                    if "file_metadata" in type_data:
                        result[data_type]["file_metadata"] = type_data["file_metadata"]

                return result
            except Exception as e:
                logger.error(f"Error loading metadata: {str(e)}")

        return {}

    def _save_metadata(self):
        """Save chunk metadata to disk."""
        try:
            # Convert to serializable format
            data = {}
            for data_type, type_data in self.metadata.items():
                data[data_type] = {}
                if "chunks" in type_data:
                    data[data_type]["chunks"] = {
                        chunk_id: chunk.to_dict()
                        for chunk_id, chunk in type_data["chunks"].items()
                    }
                if "file_metadata" in type_data:
                    data[data_type]["file_metadata"] = type_data["file_metadata"]

            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving metadata: {str(e)}")

    def _update_metadata(
        self, data_type: str, chunks: List[ChunkMetadata], headers: Dict
    ):
        """Update metadata for a data type."""
        if data_type not in self.metadata:
            self.metadata[data_type] = {}

        # Update chunks
        self.metadata[data_type]["chunks"] = {chunk.chunk_id: chunk for chunk in chunks}

        # Update file metadata
        self.metadata[data_type]["file_metadata"] = {
            "etag": headers.get("ETag", "").strip('"'),
            "last_modified": headers.get("Last-Modified", ""),
            "content_length": int(headers.get("Content-Length", 0)),
            "last_checked": datetime.now().isoformat(),
        }

        self._save_metadata()

    def _update_file_metadata(self, data_type: str, headers: Dict, data: ByteString):
        """Update file-level metadata."""
        if data_type not in self.metadata:
            self.metadata[data_type] = {}

        self.metadata[data_type]["file_metadata"] = {
            "etag": headers.get("ETag", "").strip('"'),
            "last_modified": headers.get("Last-Modified", ""),
            "content_length": len(data),
            "checksum": hashlib.sha256(data).hexdigest(),
            "last_checked": datetime.now().isoformat(),
        }

        self._save_metadata()

    def _cache_chunk(self, chunk_id: str, data: ByteString, data_type: str):
        """Cache a chunk to disk."""
        try:
            cache_file = self.chunk_cache_dir / f"{data_type}_{chunk_id}.cache"
            with open(cache_file, "wb") as f:
                f.write(data)
        except Exception as e:
            logger.error(f"Error caching chunk: {str(e)}")

    def _get_cached_chunk(self, chunk_id: str, data_type: str) -> Optional[ByteString]:
        """Get a cached chunk if available and not expired."""
        try:
            cache_file = self.chunk_cache_dir / f"{data_type}_{chunk_id}.cache"

            if not cache_file.exists():
                return None

            # Check age
            file_age = datetime.now() - datetime.fromtimestamp(
                cache_file.stat().st_mtime
            )
            if file_age > timedelta(hours=self.ttl_hours):
                logger.info(f"Cache expired for chunk {chunk_id}")
                return None

            with open(cache_file, "rb") as f:
                return f.read()

        except Exception as e:
            logger.error(f"Error reading cached chunk: {str(e)}")
            return None

    def _cache_complete_file(self, data_type: str, data: ByteString):
        """Cache complete file data."""
        try:
            cache_file = self.cache_dir / f"{data_type}_complete.cache"
            with open(cache_file, "wb") as f:
                f.write(data)
        except Exception as e:
            logger.error(f"Error caching complete file: {str(e)}")

    def _load_from_cache(self, data_type: str) -> Optional[ByteString]:
        """Load complete file from cache if available."""
        try:
            cache_file = self.cache_dir / f"{data_type}_complete.cache"

            if not cache_file.exists():
                return None

            # Check age
            file_age = datetime.now() - datetime.fromtimestamp(
                cache_file.stat().st_mtime
            )
            if file_age > timedelta(hours=self.ttl_hours):
                logger.info(f"Cache expired for {data_type}")
                return None

            with open(cache_file, "rb") as f:
                return f.read()

        except Exception as e:
            logger.error(f"Error loading from cache: {str(e)}")
            return None

    def clear_cache(self, data_type: Optional[str] = None):
        """
        Clear cached data.

        Args:
            data_type: Specific data type to clear, or None for all
        """
        if data_type:
            # Clear specific data type
            pattern = f"{data_type}_*"
            for cache_file in self.cache_dir.glob(pattern):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"Error removing {cache_file}: {str(e)}")

            # Clear metadata
            if data_type in self.metadata:
                del self.metadata[data_type]
                self._save_metadata()
        else:
            # Clear all cache
            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file():
                    try:
                        cache_file.unlink()
                    except Exception as e:
                        logger.error(f"Error removing {cache_file}: {str(e)}")

            # Clear all metadata
            self.metadata = {}
            self._save_metadata()

        logger.info(f"Cleared cache for {data_type if data_type else 'all data types'}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached data."""
        stats = {
            "cache_dir": str(self.cache_dir),
            "total_size_mb": 0,
            "data_types": {},
            "chunk_count": 0,
            "oldest_cache": None,
            "newest_cache": None,
        }

        oldest_time = None
        newest_time = None

        for cache_file in self.cache_dir.rglob("*.cache"):
            file_stat = cache_file.stat()
            size_mb = file_stat.st_size / (1024 * 1024)
            stats["total_size_mb"] += size_mb

            file_time = datetime.fromtimestamp(file_stat.st_mtime)
            if oldest_time is None or file_time < oldest_time:
                oldest_time = file_time
                stats["oldest_cache"] = file_time.isoformat()

            if newest_time is None or file_time > newest_time:
                newest_time = file_time
                stats["newest_cache"] = file_time.isoformat()

            # Count chunks
            if "_chunk_" in cache_file.name:
                stats["chunk_count"] += 1

        # Add metadata stats
        for data_type, type_data in self.metadata.items():
            stats["data_types"][data_type] = {
                "chunks": len(type_data.get("chunks", {})),
                "has_file_metadata": "file_metadata" in type_data,
            }

        return stats
