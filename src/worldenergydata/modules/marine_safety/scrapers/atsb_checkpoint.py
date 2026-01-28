# ABOUTME: Checkpoint management for ATSB marine investigation scraper.
# ABOUTME: Handles saving and loading of scraping progress for resumable operations.

"""
ATSB Checkpoint Manager

Manages checkpointing for resumable ATSB scraping operations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

from worldenergydata.modules.marine_safety.utils.logger import get_logger

logger = get_logger(__name__)


class ATSBCheckpointManager:
    """
    Manages checkpoint state for ATSB scraper.

    Enables resumable scraping by tracking processed investigation IDs
    and saving progress to disk.
    """

    def __init__(self, checkpoint_dir: Path) -> None:
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self._checkpoint_file = self.checkpoint_dir / "atsb_scraper_checkpoint.json"
        self._processed_ids: Set[str] = set()
        self._last_checkpoint_time: Optional[datetime] = None

    @property
    def processed_ids(self) -> Set[str]:
        """Get the set of processed investigation IDs."""
        return self._processed_ids

    @property
    def last_checkpoint_time(self) -> Optional[datetime]:
        """Get the timestamp of the last checkpoint save."""
        return self._last_checkpoint_time

    def add_processed_id(self, atsb_id: str) -> None:
        """
        Add an investigation ID to the processed set.

        Args:
            atsb_id: ATSB investigation ID
        """
        self._processed_ids.add(atsb_id)

    def is_processed(self, atsb_id: str) -> bool:
        """
        Check if an investigation ID has been processed.

        Args:
            atsb_id: ATSB investigation ID

        Returns:
            True if already processed
        """
        return atsb_id in self._processed_ids

    def load(self) -> None:
        """Load checkpoint data from disk if available."""
        if not self._checkpoint_file.exists():
            logger.debug("No checkpoint file found")
            return

        try:
            with open(self._checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

            self._processed_ids = set(checkpoint.get("processed_ids", []))
            last_time = checkpoint.get("last_checkpoint_time")
            if last_time:
                self._last_checkpoint_time = datetime.fromisoformat(last_time)

            logger.info(
                f"Loaded checkpoint: {len(self._processed_ids)} processed IDs, "
                f"last checkpoint: {self._last_checkpoint_time}"
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load checkpoint: {e}")

    def save(self, force: bool = False) -> None:
        """
        Save checkpoint data to disk.

        Args:
            force: If True, save regardless of time since last checkpoint.
                Otherwise, saves at most once per minute.
        """
        now = datetime.utcnow()
        if (
            not force
            and self._last_checkpoint_time
            and (now - self._last_checkpoint_time).total_seconds() < 60
        ):
            return

        checkpoint = {
            "processed_ids": list(self._processed_ids),
            "last_checkpoint_time": now.isoformat(),
            "total_processed": len(self._processed_ids),
        }

        try:
            with open(self._checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2)

            self._last_checkpoint_time = now
            logger.debug(f"Checkpoint saved: {len(self._processed_ids)} processed IDs")

        except IOError as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def clear(self) -> None:
        """Clear checkpoint data to start fresh."""
        self._processed_ids.clear()
        self._last_checkpoint_time = None

        if self._checkpoint_file.exists():
            self._checkpoint_file.unlink()
            logger.info("Checkpoint cleared")

    def get_statistics(self) -> dict:
        """
        Get checkpoint statistics.

        Returns:
            Dictionary with checkpoint statistics
        """
        return {
            "total_processed_ids": len(self._processed_ids),
            "last_checkpoint": (
                self._last_checkpoint_time.isoformat()
                if self._last_checkpoint_time
                else None
            ),
            "checkpoint_file": str(self._checkpoint_file),
        }
