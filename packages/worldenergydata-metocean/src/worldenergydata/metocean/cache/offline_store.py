# ABOUTME: Persistent offline storage for metocean data with compression.
# ABOUTME: Organizes data by source, station, and date for efficient retrieval.

"""
Offline Store for Metocean Data

Provides persistent storage for offline access to metocean data.
"""

import gzip
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import get_config
from ..constants import DataSource


class OfflineStore:
    """
    Stores metocean data for offline access.

    Features:
    - Compressed storage (gzip)
    - Organized by source, station, and date
    - Search by station and date range
    - Efficient retrieval of historical data
    """

    def __init__(self, store_dir: Optional[Path] = None) -> None:
        """
        Initialize the offline store.

        Args:
            store_dir: Directory for offline storage (default from config)
        """
        config = get_config().storage
        self.store_dir = store_dir or config.processed_path / "offline"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("metocean.offline_store")

        self.logger.info(f"Offline store initialized: {self.store_dir}")

    def store(
        self,
        source: DataSource,
        station_id: str,
        date: datetime,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Store data for a station and date.

        Args:
            source: Data source (NDBC, COOPS, etc.)
            station_id: Station identifier
            date: Date of the data
            data: List of observation records
            metadata: Optional metadata about the data

        Returns:
            Path to the stored file
        """
        # Create directory structure: source/station_id/YYYY/
        year_dir = self.store_dir / source.value / station_id / str(date.year)
        year_dir.mkdir(parents=True, exist_ok=True)

        # Filename: YYYYMMDD.json.gz
        filename = f"{date.strftime('%Y%m%d')}.json.gz"
        filepath = year_dir / filename

        store_data = {
            "source": source.value,
            "station_id": station_id,
            "date": date.isoformat(),
            "stored_at": datetime.utcnow().isoformat(),
            "record_count": len(data),
            "records": data,
        }

        if metadata:
            store_data["metadata"] = metadata

        with gzip.open(filepath, "wt", encoding="utf-8") as f:
            json.dump(store_data, f, default=str)

        self.logger.debug(
            f"Stored {len(data)} records to {filepath} "
            f"({filepath.stat().st_size / 1024:.1f} KB compressed)"
        )
        return filepath

    def retrieve(
        self,
        source: DataSource,
        station_id: str,
        date: datetime,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve data for a station and date.

        Args:
            source: Data source
            station_id: Station identifier
            date: Date of the data

        Returns:
            List of observation records, or None if not found
        """
        year_dir = self.store_dir / source.value / station_id / str(date.year)
        filename = f"{date.strftime('%Y%m%d')}.json.gz"
        filepath = year_dir / filename

        if not filepath.exists():
            self.logger.debug(f"No offline data found: {filepath}")
            return None

        try:
            with gzip.open(filepath, "rt", encoding="utf-8") as f:
                data = json.load(f)

            self.logger.debug(
                f"Retrieved {len(data.get('records', []))} records from {filepath}"
            )
            return data.get("records")
        except Exception as e:
            self.logger.error(f"Failed to retrieve offline data from {filepath}: {e}")
            return None

    def retrieve_with_metadata(
        self,
        source: DataSource,
        station_id: str,
        date: datetime,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve data with full metadata for a station and date.

        Args:
            source: Data source
            station_id: Station identifier
            date: Date of the data

        Returns:
            Full stored data including metadata, or None if not found
        """
        year_dir = self.store_dir / source.value / station_id / str(date.year)
        filename = f"{date.strftime('%Y%m%d')}.json.gz"
        filepath = year_dir / filename

        if not filepath.exists():
            return None

        try:
            with gzip.open(filepath, "rt", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to retrieve offline data from {filepath}: {e}")
            return None

    def retrieve_date_range(
        self,
        source: DataSource,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve data for a date range.

        Args:
            source: Data source
            station_id: Station identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Combined list of observation records
        """
        all_records = []
        current_date = start_date

        while current_date <= end_date:
            records = self.retrieve(source, station_id, current_date)
            if records:
                all_records.extend(records)
            current_date = datetime(
                current_date.year,
                current_date.month,
                current_date.day + 1 if current_date.day < 28 else 1,
            )
            # Handle month/year rollover properly
            from datetime import timedelta

            current_date = start_date + timedelta(
                days=(current_date - start_date).days + 1
            )
            if current_date > end_date:
                break

        self.logger.debug(
            f"Retrieved {len(all_records)} total records for "
            f"{station_id} from {start_date.date()} to {end_date.date()}"
        )
        return all_records

    def has_data(
        self,
        source: DataSource,
        station_id: str,
        date: datetime,
    ) -> bool:
        """
        Check if data exists for a station and date.

        Args:
            source: Data source
            station_id: Station identifier
            date: Date to check

        Returns:
            True if data exists, False otherwise
        """
        year_dir = self.store_dir / source.value / station_id / str(date.year)
        filename = f"{date.strftime('%Y%m%d')}.json.gz"
        return (year_dir / filename).exists()

    def list_available(
        self,
        source: Optional[DataSource] = None,
        station_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List available offline data.

        Args:
            source: Optional filter by data source
            station_id: Optional filter by station ID

        Returns:
            List of available data entries with metadata
        """
        available = []

        sources = [source] if source else list(DataSource)

        for src in sources:
            src_dir = self.store_dir / src.value
            if not src_dir.exists():
                continue

            for station_dir in src_dir.iterdir():
                if not station_dir.is_dir():
                    continue
                if station_id and station_dir.name != station_id:
                    continue

                for year_dir in station_dir.iterdir():
                    if not year_dir.is_dir():
                        continue

                    for file in year_dir.glob("*.json.gz"):
                        date_str = file.stem.replace(".json", "")
                        file_stat = file.stat()
                        available.append(
                            {
                                "source": src.value,
                                "station_id": station_dir.name,
                                "date": date_str,
                                "year": year_dir.name,
                                "path": str(file),
                                "size_bytes": file_stat.st_size,
                                "modified_at": datetime.fromtimestamp(
                                    file_stat.st_mtime
                                ).isoformat(),
                            }
                        )

        # Sort by date descending
        available.sort(key=lambda x: x["date"], reverse=True)
        return available

    def list_stations(
        self,
        source: Optional[DataSource] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all stations with offline data.

        Args:
            source: Optional filter by data source

        Returns:
            List of stations with data counts
        """
        stations = {}
        sources = [source] if source else list(DataSource)

        for src in sources:
            src_dir = self.store_dir / src.value
            if not src_dir.exists():
                continue

            for station_dir in src_dir.iterdir():
                if not station_dir.is_dir():
                    continue

                station_key = f"{src.value}:{station_dir.name}"
                if station_key not in stations:
                    stations[station_key] = {
                        "source": src.value,
                        "station_id": station_dir.name,
                        "file_count": 0,
                        "total_size_bytes": 0,
                        "years": set(),
                    }

                for year_dir in station_dir.iterdir():
                    if not year_dir.is_dir():
                        continue

                    stations[station_key]["years"].add(year_dir.name)

                    for file in year_dir.glob("*.json.gz"):
                        stations[station_key]["file_count"] += 1
                        stations[station_key]["total_size_bytes"] += file.stat().st_size

        # Convert sets to sorted lists
        result = []
        for station_data in stations.values():
            station_data["years"] = sorted(station_data["years"])
            station_data["total_size_mb"] = round(
                station_data["total_size_bytes"] / (1024 * 1024), 2
            )
            result.append(station_data)

        return sorted(result, key=lambda x: (x["source"], x["station_id"]))

    def delete(
        self,
        source: DataSource,
        station_id: str,
        date: datetime,
    ) -> bool:
        """
        Delete stored data for a station and date.

        Args:
            source: Data source
            station_id: Station identifier
            date: Date of the data

        Returns:
            True if data was deleted, False if not found
        """
        year_dir = self.store_dir / source.value / station_id / str(date.year)
        filename = f"{date.strftime('%Y%m%d')}.json.gz"
        filepath = year_dir / filename

        if not filepath.exists():
            return False

        try:
            filepath.unlink()
            self.logger.debug(f"Deleted offline data: {filepath}")

            # Clean up empty directories
            if not any(year_dir.iterdir()):
                year_dir.rmdir()
                station_dir = year_dir.parent
                if not any(station_dir.iterdir()):
                    station_dir.rmdir()

            return True
        except OSError as e:
            self.logger.error(f"Failed to delete offline data {filepath}: {e}")
            return False

    def delete_station(
        self,
        source: DataSource,
        station_id: str,
    ) -> int:
        """
        Delete all stored data for a station.

        Args:
            source: Data source
            station_id: Station identifier

        Returns:
            Number of files deleted
        """
        station_dir = self.store_dir / source.value / station_id
        if not station_dir.exists():
            return 0

        deleted = 0
        for year_dir in station_dir.iterdir():
            if not year_dir.is_dir():
                continue
            for file in year_dir.glob("*.json.gz"):
                try:
                    file.unlink()
                    deleted += 1
                except OSError as e:
                    self.logger.error(f"Failed to delete {file}: {e}")

        # Clean up empty directories
        try:
            import shutil

            shutil.rmtree(station_dir)
        except OSError:
            pass

        self.logger.info(f"Deleted {deleted} files for station {station_id}")
        return deleted

    def status(self) -> Dict[str, Any]:
        """
        Get offline store status.

        Returns:
            Dictionary with store statistics
        """
        total_files = 0
        total_size = 0
        sources_count: Dict[str, int] = {}
        stations_count: Dict[str, int] = {}

        for f in self.store_dir.rglob("*.json.gz"):
            total_files += 1
            total_size += f.stat().st_size

            # Parse path to get source and station
            parts = f.relative_to(self.store_dir).parts
            if len(parts) >= 2:
                source_name = parts[0]
                station_id = parts[1]
                sources_count[source_name] = sources_count.get(source_name, 0) + 1
                station_key = f"{source_name}:{station_id}"
                stations_count[station_key] = stations_count.get(station_key, 0) + 1

        return {
            "store_dir": str(self.store_dir),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "sources_count": sources_count,
            "unique_stations": len(stations_count),
        }

    def compact(self) -> Dict[str, Any]:
        """
        Compact the offline store by removing empty directories.

        Returns:
            Dictionary with compaction results
        """
        removed_dirs = 0

        # Walk through directory tree bottom-up
        for source_dir in self.store_dir.iterdir():
            if not source_dir.is_dir():
                continue

            for station_dir in source_dir.iterdir():
                if not station_dir.is_dir():
                    continue

                for year_dir in list(station_dir.iterdir()):
                    if year_dir.is_dir() and not any(year_dir.iterdir()):
                        year_dir.rmdir()
                        removed_dirs += 1

                if not any(station_dir.iterdir()):
                    station_dir.rmdir()
                    removed_dirs += 1

            if not any(source_dir.iterdir()):
                source_dir.rmdir()
                removed_dirs += 1

        self.logger.info(f"Compacted store: removed {removed_dirs} empty directories")
        return {"removed_directories": removed_dirs}
