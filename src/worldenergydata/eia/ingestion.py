"""Incremental JSONL ingestion for EIA weekly petroleum and gas feeds.

State tracking uses a JSON file that records the last successfully
fetched period date for each feed. On each run only data with a period
strictly after that date is written to JSONL output.

Output files:
  <output_dir>/eia_petroleum_weekly.jsonl
  <output_dir>/eia_gas_storage_weekly.jsonl

State file:
  <state_dir>/eia_ingestion_state.json
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from worldenergydata.eia.client import EIAFeedClient

logger = logging.getLogger(__name__)

JSONL_SCHEMA_VERSION: str = "1"

# Mapping of feed name to JSONL output filename
_FEED_FILENAMES: Dict[str, str] = {
    "petroleum_weekly": "eia_petroleum_weekly.jsonl",
    "gas_storage_weekly": "eia_gas_storage_weekly.jsonl",
}

_STATE_FILENAME: str = "eia_ingestion_state.json"


# ── Ingestion State ────────────────────────────────────────────────────────────


class EIAIngestionState:
    """Persistent state tracking for incremental EIA feed ingestion.

    The state is stored as a JSON file mapping feed names to their last
    successfully fetched period date (ISO string 'YYYY-MM-DD').

    Args:
        state_dir: Directory where the state file will be stored.
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir: Path = Path(state_dir)
        self._state_file: Path = self.state_dir / _STATE_FILENAME
        self._data: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load state from disk if the state file exists."""
        if self._state_file.exists():
            try:
                self._data = json.loads(self._state_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not load EIA ingestion state: %s", exc)
                self._data = {}

    def get_last_fetch(self, feed_name: str) -> Optional[str]:
        """Return the last fetched period date for a feed, or None if unknown.

        Args:
            feed_name: Feed identifier (e.g. 'petroleum_weekly').

        Returns:
            ISO date string 'YYYY-MM-DD', or None if never fetched.
        """
        return self._data.get(feed_name)

    def save_last_fetch(self, feed_name: str, period_date: str) -> None:
        """Persist the last successfully fetched period date for a feed.

        Args:
            feed_name: Feed identifier (e.g. 'petroleum_weekly').
            period_date: ISO date string 'YYYY-MM-DD' of the latest period.
        """
        self._data[feed_name] = period_date
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(
            json.dumps(self._data, indent=2), encoding="utf-8"
        )


# ── Ingestion Sync ────────────────────────────────────────────────────────────


class EIAIngestionSync:
    """Orchestrates incremental EIA feed ingestion to JSONL files.

    On each run:
    1. Reads state to find the last fetched period date per feed.
    2. Fetches only new data since that date.
    3. Filters out records on or before the last fetch date.
    4. Appends new records to the JSONL file, adding schema version.
    5. Updates state with the latest period seen.

    Args:
        api_key: EIA API key. Falls back to EIA_API_KEY env var.
        output_dir: Directory for JSONL output files.
        state_dir: Directory for the ingestion state file. Defaults to
                   output_dir if not specified.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        output_dir: Path = Path("./data/eia"),
        state_dir: Optional[Path] = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.state_dir = Path(state_dir) if state_dir else self.output_dir
        self.client = EIAFeedClient(api_key=api_key)
        self.state = EIAIngestionState(state_dir=self.state_dir)

    # ── JSONL writing ─────────────────────────────────────────────────────────

    def write_jsonl(self, feed_name: str, records: List[Dict[str, Any]]) -> None:
        """Append records to the JSONL file for a feed.

        Each record is written as a single JSON line. A '_schema_version'
        field is injected into every record before writing.

        Args:
            feed_name: Feed identifier determining the output filename.
            records: List of record dicts to append.
        """
        if not records:
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = _FEED_FILENAMES.get(feed_name, f"eia_{feed_name}.jsonl")
        output_path = self.output_dir / filename

        with output_path.open("a", encoding="utf-8") as fh:
            for record in records:
                enriched = dict(record)
                enriched["_schema_version"] = JSONL_SCHEMA_VERSION
                fh.write(json.dumps(enriched, default=str) + "\n")

        logger.info(
            "Wrote %d records to %s", len(records), output_path
        )

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _filter_new_records(
        self,
        records: List[Dict[str, Any]],
        last_fetch_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Return only records with a period strictly after last_fetch_date.

        Args:
            records: All fetched records for a feed.
            last_fetch_date: ISO date string 'YYYY-MM-DD', or None to allow all.

        Returns:
            Filtered list containing only truly new records.
        """
        if not last_fetch_date:
            return records

        new_records = [
            r for r in records
            if isinstance(r.get("period"), str) and r["period"] > last_fetch_date
        ]
        return new_records

    def _latest_period(self, records: List[Dict[str, Any]]) -> Optional[str]:
        """Return the maximum period date among a list of records.

        Args:
            records: List of record dicts with a 'period' key.

        Returns:
            Latest ISO date string, or None if records is empty.
        """
        periods = [
            r["period"] for r in records if isinstance(r.get("period"), str)
        ]
        return max(periods) if periods else None

    # ── Sync runners ──────────────────────────────────────────────────────────

    def run_petroleum_sync(self) -> Dict[str, Any]:
        """Fetch and ingest new weekly petroleum status records.

        Returns:
            Dict with keys:
              feed          — 'petroleum_weekly'
              records_written — count of new records written
              latest_period — latest period date written (or None)
        """
        feed = "petroleum_weekly"
        last_fetch = self.state.get_last_fetch(feed)

        logger.info(
            "Starting petroleum sync (last_fetch=%s)", last_fetch or "None"
        )

        start_date = last_fetch if last_fetch else None
        records = self.client.fetch_petroleum_weekly(start_date=start_date)
        new_records = self._filter_new_records(records, last_fetch)

        latest = self._latest_period(new_records)
        if new_records:
            self.write_jsonl(feed, new_records)
        if latest:
            self.state.save_last_fetch(feed, latest)

        logger.info(
            "Petroleum sync complete: %d new records, latest=%s",
            len(new_records),
            latest,
        )
        return {
            "feed": feed,
            "records_written": len(new_records),
            "latest_period": latest,
        }

    def run_gas_storage_sync(self) -> Dict[str, Any]:
        """Fetch and ingest new weekly natural gas storage records.

        Returns:
            Dict with keys:
              feed          — 'gas_storage_weekly'
              records_written — count of new records written
              latest_period — latest period date written (or None)
        """
        feed = "gas_storage_weekly"
        last_fetch = self.state.get_last_fetch(feed)

        logger.info(
            "Starting gas storage sync (last_fetch=%s)", last_fetch or "None"
        )

        start_date = last_fetch if last_fetch else None
        records = self.client.fetch_gas_storage_weekly(start_date=start_date)
        new_records = self._filter_new_records(records, last_fetch)

        latest = self._latest_period(new_records)
        if new_records:
            self.write_jsonl(feed, new_records)
        if latest:
            self.state.save_last_fetch(feed, latest)

        logger.info(
            "Gas storage sync complete: %d new records, latest=%s",
            len(new_records),
            latest,
        )
        return {
            "feed": feed,
            "records_written": len(new_records),
            "latest_period": latest,
        }

    def run_all(self) -> List[Dict[str, Any]]:
        """Run incremental sync for all EIA weekly feeds.

        Returns:
            List of result dicts from each feed sync.
        """
        results = []
        results.append(self.run_petroleum_sync())
        results.append(self.run_gas_storage_sync())
        return results
