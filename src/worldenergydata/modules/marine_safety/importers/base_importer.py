"""
Base Data Importer

Abstract base class for bulk data importers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BaseImporter(ABC):
    """
    Abstract base class for data importers.

    All importers should inherit from this class and implement:
    - read_source()
    - parse_record()
    - map_to_model()
    """

    def __init__(self, source_path: Path, session: Session, batch_size: int = 100):
        """
        Initialize the importer.

        Args:
            source_path: Path to data source file
            session: SQLAlchemy session for database operations
            batch_size: Number of records to process in each batch
        """
        self.source_path = source_path
        self.session = session
        self.batch_size = batch_size

        self.stats = {
            'total_records': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'duplicates': 0
        }

        logger.info(f"Initialized {self.__class__.__name__}")
        logger.info(f"Source: {source_path}")
        logger.info(f"Batch size: {batch_size}")

    @abstractmethod
    def read_source(self) -> Generator[Dict[str, Any], None, None]:
        """
        Read records from source file.

        Yields:
            Raw record dictionaries

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement read_source()")

    @abstractmethod
    def parse_record(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw record into standardized format.

        Args:
            raw_record: Raw record from source

        Returns:
            Parsed record dictionary or None if invalid

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement parse_record()")

    @abstractmethod
    def map_to_model(self, parsed_record: Dict[str, Any]) -> Optional[Any]:
        """
        Map parsed record to database model.

        Args:
            parsed_record: Parsed record dictionary

        Returns:
            Database model instance or None if mapping fails

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement map_to_model()")

    def import_data(self, limit: Optional[int] = None, skip_duplicates: bool = True) -> Dict[str, int]:
        """
        Import data from source to database.

        Args:
            limit: Maximum number of records to import (None for all)
            skip_duplicates: Whether to skip duplicate records

        Returns:
            Statistics dictionary
        """
        logger.info(f"Starting import from {self.source_path}")

        batch = []
        records_processed = 0

        try:
            for raw_record in self.read_source():
                self.stats['total_records'] += 1
                records_processed += 1

                # Parse record
                parsed = self.parse_record(raw_record)
                if not parsed:
                    self.stats['skipped'] += 1
                    continue

                # Map to model
                model_instance = self.map_to_model(parsed)
                if not model_instance:
                    self.stats['errors'] += 1
                    continue

                # Check for duplicates
                if skip_duplicates and self.is_duplicate(model_instance):
                    self.stats['duplicates'] += 1
                    continue

                # Add to batch
                batch.append(model_instance)

                # Commit batch when full
                if len(batch) >= self.batch_size:
                    self._commit_batch(batch)
                    batch = []

                # Check limit
                if limit and records_processed >= limit:
                    logger.info(f"Reached limit of {limit} records")
                    break

                # Progress logging
                if self.stats['total_records'] % 1000 == 0:
                    logger.info(f"Processed {self.stats['total_records']} records...")

            # Commit remaining records
            if batch:
                self._commit_batch(batch)

        except Exception as e:
            logger.error(f"Import failed: {e}")
            self.session.rollback()
            raise

        logger.info(f"Import complete: {self.stats}")
        return self.stats

    def _commit_batch(self, batch: List[Any]):
        """
        Commit a batch of records to database.

        Args:
            batch: List of model instances
        """
        try:
            self.session.add_all(batch)
            self.session.commit()
            self.stats['imported'] += len(batch)
            logger.debug(f"Committed batch of {len(batch)} records")
        except Exception as e:
            logger.error(f"Batch commit failed: {e}")
            self.session.rollback()
            self.stats['errors'] += len(batch)

    def is_duplicate(self, model_instance: Any) -> bool:
        """
        Check if record already exists in database.

        Args:
            model_instance: Model instance to check

        Returns:
            True if duplicate, False otherwise
        """
        # Default implementation - override in subclass for specific logic
        return False

    def get_stats(self) -> Dict[str, int]:
        """
        Get import statistics.

        Returns:
            Dictionary of statistics
        """
        return self.stats.copy()

    def validate_source(self) -> bool:
        """
        Validate that source file exists and is readable.

        Returns:
            True if valid, False otherwise
        """
        if not self.source_path.exists():
            logger.error(f"Source file not found: {self.source_path}")
            return False

        if not self.source_path.is_file():
            logger.error(f"Source path is not a file: {self.source_path}")
            return False

        return True
