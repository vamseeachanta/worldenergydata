"""
ABOUTME: NTSB CAROL API loader for the incident taxonomy pipeline.
ABOUTME: Fetches NTSB marine accident data from the CAROL API and normalises to taxonomy schema.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
    IncidentDataFrameNormaliser,
    IncidentTaxonomyClassifier,
    TaxonomyRecord,
    NTSB_COLUMN_MAP,
)

logger = logging.getLogger(__name__)

# NTSB CAROL API endpoints
CAROL_BASE_URL = "https://data.ntsb.gov"
CAROL_SEARCH_URL = f"{CAROL_BASE_URL}/carol-main-public/api/Query/GetSearchResults"

# Pagination defaults
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 200
REQUEST_TIMEOUT = 60


class NTSBMarineLoader:
    """
    Loader for NTSB marine accident investigation data from the CAROL API.

    Fetches marine accident records from the NTSB CAROL (Case Analysis and
    Reporting Online) system and normalises them to the shared taxonomy schema.

    CAROL API documentation:
    https://data.ntsb.gov/carol-main-public/api/

    The loader filters responses to marine mode only and maps CAROL field names
    to the canonical taxonomy columns via NTSB_COLUMN_MAP.

    On API errors or empty responses the loader returns an empty DataFrame rather
    than raising, so callers can proceed with partial data sets.

    Usage::

        loader = NTSBMarineLoader()
        df = loader.fetch_marine_accidents(2020, 2023)
        records = loader.fetch_to_records(2020, 2023)
    """

    def __init__(
        self,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        timeout: int = REQUEST_TIMEOUT,
        session: Optional[Any] = None,
    ) -> None:
        """
        Initialise NTSBMarineLoader.

        Args:
            page_size: Number of records per API page.
            max_pages: Maximum pages to fetch (safety cap).
            timeout: HTTP request timeout in seconds.
            session: Optional pre-configured requests.Session (for testing).
        """
        self._page_size = page_size
        self._max_pages = max_pages
        self._timeout = timeout
        self._session = session
        self._normaliser = IncidentDataFrameNormaliser()

    def fetch_marine_accidents(
        self,
        year_start: int,
        year_end: int,
    ) -> pd.DataFrame:
        """
        Fetch marine accident records from NTSB CAROL and return a normalised DataFrame.

        Queries the CAROL GetSearchResults API for marine mode investigations
        within the specified year range. Returns an empty DataFrame with the
        canonical columns on any API failure, so callers receive a consistent
        schema regardless of connectivity.

        Args:
            year_start: First calendar year to include (inclusive).
            year_end: Last calendar year to include (inclusive).

        Returns:
            Normalised DataFrame with canonical taxonomy columns.
            Empty DataFrame (zero rows) on API failure.
        """
        raw_records = self._fetch_from_api(year_start, year_end)

        if not raw_records:
            logger.warning(
                "NTSB CAROL API returned no marine records for %d–%d; "
                "returning empty DataFrame",
                year_start,
                year_end,
            )
            return self._empty_dataframe()

        raw_df = pd.DataFrame(raw_records)
        logger.info(
            "Fetched %d raw NTSB marine records for %d–%d",
            len(raw_df),
            year_start,
            year_end,
        )
        return self._normaliser.normalise(raw_df, source="ntsb")

    def fetch_to_records(
        self,
        year_start: int,
        year_end: int,
        classifier: Optional[IncidentTaxonomyClassifier] = None,
    ) -> List[TaxonomyRecord]:
        """
        Fetch marine accident records and return classified TaxonomyRecord instances.

        Args:
            year_start: First calendar year to include (inclusive).
            year_end: Last calendar year to include (inclusive).
            classifier: Optional pre-built IncidentTaxonomyClassifier.

        Returns:
            List of TaxonomyRecord with root_cause populated.
            Empty list on API failure.
        """
        df = self.fetch_marine_accidents(year_start, year_end)
        if df.empty:
            return []
        records = self._normaliser.to_taxonomy_records(
            df, source="ntsb", classifier=classifier
        )
        logger.info("Produced %d taxonomy records from NTSB data", len(records))
        return records

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_session(self) -> Any:
        """Return the requests session, creating one if needed."""
        if self._session is not None:
            return self._session
        try:
            import requests

            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": (
                        "WorldEnergyData/1.0 (research; marine-safety-analysis)"
                    ),
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            )
            return session
        except ImportError as exc:
            raise RuntimeError(
                "requests library is required for NTSBMarineLoader live API calls"
            ) from exc

    def _fetch_from_api(
        self,
        year_start: int,
        year_end: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw records from the CAROL API across paginated results.

        Args:
            year_start: Start year.
            year_end: End year.

        Returns:
            List of raw record dicts; empty on failure.
        """
        start_date = f"{year_start}-01-01"
        end_date = f"{year_end}-12-31"

        payload: Dict[str, Any] = {
            "QueryGroups": [
                {
                    "QueryRules": [
                        {
                            "FieldName": "Mode",
                            "RuleOperator": "Equals",
                            "RuleValue": "Marine",
                        },
                        {
                            "FieldName": "EventDate",
                            "RuleOperator": "GreaterThanOrEqualTo",
                            "RuleValue": start_date,
                        },
                        {
                            "FieldName": "EventDate",
                            "RuleOperator": "LessThanOrEqualTo",
                            "RuleValue": end_date,
                        },
                    ],
                    "GroupOperator": "And",
                }
            ],
            "ResultSort": {"SortFieldName": "EventDate", "SortDescending": False},
            "ResultsPage": {"PageNumber": 1, "PageSize": self._page_size},
        }

        all_records: List[Dict[str, Any]] = []
        session = self._get_session()

        for page in range(1, self._max_pages + 1):
            payload["ResultsPage"]["PageNumber"] = page

            try:
                import requests

                response = session.post(
                    CAROL_SEARCH_URL,
                    json=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                data = response.json()

            except Exception as exc:
                logger.warning(
                    "NTSB CAROL API request failed on page %d: %s", page, exc
                )
                break

            results = _extract_results(data)
            if not results:
                break

            for raw in results:
                mapped = _map_carol_record(raw)
                if mapped:
                    all_records.append(mapped)

            logger.debug(
                "CAROL page %d: %d results (total so far: %d)",
                page,
                len(results),
                len(all_records),
            )

            total = _extract_total_count(data)
            if total is not None and len(all_records) >= total:
                break
            if len(results) < self._page_size:
                break

        return all_records

    def _empty_dataframe(self) -> pd.DataFrame:
        """Return an empty DataFrame with the canonical taxonomy columns."""
        canonical_cols = list(NTSB_COLUMN_MAP.values()) + ["source"]
        return pd.DataFrame(columns=canonical_cols)


# ---------------------------------------------------------------------------
# Module-level convenience functions (mirror uscg_client.py API)
# ---------------------------------------------------------------------------


def fetch_ntsb_marine(
    year_start: int,
    year_end: int,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: int = REQUEST_TIMEOUT,
) -> pd.DataFrame:
    """
    Fetch NTSB marine accident data from CAROL API as a normalised DataFrame.

    Returns an empty DataFrame on API failure.

    Args:
        year_start: First calendar year to include (inclusive).
        year_end: Last calendar year to include (inclusive).
        page_size: Records per API page.
        timeout: HTTP timeout in seconds.

    Returns:
        Normalised DataFrame with canonical taxonomy columns.
    """
    loader = NTSBMarineLoader(page_size=page_size, timeout=timeout)
    return loader.fetch_marine_accidents(year_start, year_end)


def load_dataframe_as_ntsb(
    df: pd.DataFrame,
    classifier: Optional[IncidentTaxonomyClassifier] = None,
) -> List[TaxonomyRecord]:
    """
    Treat an in-memory DataFrame as NTSB marine data and classify it.

    Useful for unit testing without live API access.

    Args:
        df: DataFrame with NTSB-style columns (raw or pre-renamed).
        classifier: Optional pre-built classifier.

    Returns:
        List of TaxonomyRecord instances.
    """
    normaliser = IncidentDataFrameNormaliser()
    normalised = normaliser.normalise(df, source="ntsb")
    return normaliser.to_taxonomy_records(
        normalised, source="ntsb", classifier=classifier
    )


# ---------------------------------------------------------------------------
# CAROL response parsing helpers
# ---------------------------------------------------------------------------


def _extract_results(data: Any) -> List[Dict[str, Any]]:
    """Extract result records from various CAROL API response formats."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in (
            "Results",
            "results",
            "Data",
            "data",
            "Items",
            "items",
            "Records",
            "records",
            "Investigations",
            "investigations",
        ):
            if key in data and isinstance(data[key], list):
                return data[key]

    return []


def _extract_total_count(data: Any) -> Optional[int]:
    """Extract total record count from CAROL API response envelope."""
    if not isinstance(data, dict):
        return None

    for key in (
        "TotalCount",
        "totalCount",
        "Total",
        "total",
        "TotalRecords",
        "totalRecords",
        "ResultCount",
        "resultCount",
    ):
        if key in data:
            try:
                return int(data[key])
            except (ValueError, TypeError):
                pass

    pagination = data.get("Pagination", data.get("pagination", {}))
    if isinstance(pagination, dict):
        for key in ("TotalRecords", "totalRecords", "Total", "total"):
            if key in pagination:
                try:
                    return int(pagination[key])
                except (ValueError, TypeError):
                    pass

    return None


def _map_carol_record(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Map a CAROL API record to NTSB_COLUMN_MAP canonical field names.

    Returns None if the record is missing a required identifier.
    """
    # CAROL uses camelCase field names; map to the CSV column names expected
    # by NTSB_COLUMN_MAP so the normaliser can rename them.
    mapped: Dict[str, Any] = {}

    # EventId / NTSB Number
    event_id = _first_value(
        raw,
        ["EventId", "NtsbNumber", "ntsb_number", "NTSB_NUMBER", "MKEY", "Id"],
    )
    if not event_id:
        return None
    mapped["EventId"] = event_id

    # EventDate
    event_date = _first_value(
        raw, ["EventDate", "event_date", "EVENT_DATE", "AccidentDate", "Date"]
    )
    if event_date:
        mapped["EventDate"] = event_date

    # Narrative fields
    mapped["AccidentTitle"] = _first_value(
        raw, ["AccidentTitle", "Title", "title", "TITLE"]
    )
    mapped["IncidentType"] = _first_value(
        raw, ["IncidentType", "EventType", "AccidentType", "Type", "type"]
    )
    mapped["ProbableCause"] = _first_value(
        raw, ["ProbableCause", "probable_cause", "Synopsis", "synopsis"]
    )
    mapped["Narrative"] = _first_value(raw, ["Narrative", "narrative", "Description"])

    # Vessel
    mapped["VesselName"] = _first_value(
        raw, ["VesselName", "vessel_name", "VESSEL_NAME", "Vessel"]
    )
    mapped["VesselType"] = _first_value(
        raw, ["VesselType", "vessel_type", "VESSEL_TYPE"]
    )

    # Location
    mapped["Latitude"] = _first_float(raw, ["Latitude", "latitude", "LAT", "Lat"])
    mapped["Longitude"] = _first_float(
        raw, ["Longitude", "longitude", "LON", "Lon", "Long"]
    )

    # Casualties
    mapped["FatalCount"] = _first_int(
        raw, ["FatalCount", "Fatalities", "fatalities", "Fatal"]
    )
    mapped["InjuryCount"] = _first_int(
        raw, ["InjuryCount", "Injuries", "injuries", "Injured"]
    )

    # Remove None values so the normaliser receives clean data
    return {k: v for k, v in mapped.items() if v is not None}


def _first_value(
    record: Dict[str, Any], keys: List[str]
) -> Optional[str]:
    """Return the first non-empty string value for any of the given keys."""
    for key in keys:
        val = record.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def _first_float(
    record: Dict[str, Any], keys: List[str]
) -> Optional[float]:
    """Return the first parseable float for any of the given keys."""
    for key in keys:
        val = record.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return None


def _first_int(
    record: Dict[str, Any], keys: List[str]
) -> Optional[int]:
    """Return the first parseable integer for any of the given keys."""
    for key in keys:
        val = record.get(key)
        if val is not None:
            try:
                return int(float(val))
            except (ValueError, TypeError):
                continue
    return None
