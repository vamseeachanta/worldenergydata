# ABOUTME: Cross-database marine safety incident analysis combining MAIB, IMO, EMSA, TSB.
# ABOUTME: Unified query, correlation analysis, and trend identification across 4 authorities.

"""
Cross-database marine safety incident correlation analysis.

Provides a unified query interface and analytical layer across four major
marine safety investigation authorities: MAIB (UK), IMO (international),
EMSA (European), and TSB (Canada). Supports both live importer paths (when
configured with file paths) and synthetic fallback data.

Public API
----------
- CrossDatabaseQuery  — filter parameters
- CrossDatabaseResult — query output (data, counts, correlations)
- CrossDatabaseAnalyzer — query, correlations, trend_analysis, top_incident_types,
                          risk_hotspots
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from worldenergydata.marine_safety._cross_database_data import (
    SEVERITY_SCORES,
    SYNTHETIC_INCIDENTS,
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CrossDatabaseQuery:
    """Parameters for querying the cross-database incident store.

    All fields are optional; omitting them returns the full dataset.
    Multiple filters are combined with AND logic.
    """

    sources: list[str] = field(
        default_factory=lambda: ["maib", "imo", "emsa", "tsb"]
    )
    incident_types: Optional[list[str]] = None
    vessel_types: Optional[list[str]] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    regions: Optional[list[str]] = None


@dataclass
class CrossDatabaseResult:
    """Result of a cross-database query."""

    data: pd.DataFrame
    query: CrossDatabaseQuery
    total_incidents: int
    by_source: dict
    correlations: dict
    data_freshness: str = "synthetic"  # "live" | "synthetic"


# ---------------------------------------------------------------------------
# Helper normalizer functions
# ---------------------------------------------------------------------------

# Known incident types in the unified schema
_KNOWN_INCIDENT_TYPES = {
    "collision", "grounding", "fire", "flooding", "capsizing",
    "man_overboard", "machinery_failure", "structural", "explosion", "other",
}

# Map from importer-produced types to schema types
_INCIDENT_TYPE_MAP = {
    "collision": "collision",
    "contact": "collision",
    "grounding": "grounding",
    "stranding": "grounding",
    "fire": "fire",
    "fire on board": "fire",
    "explosion": "explosion",
    "flooding": "flooding",
    "sinking": "flooding",
    "foundering": "flooding",
    "capsizing": "capsizing",
    "capsize": "capsizing",
    "personnel_injury": "man_overboard",
    "fatality": "man_overboard",
    "man_overboard": "man_overboard",
    "person_overboard": "man_overboard",
    "equipment_failure": "machinery_failure",
    "loss_of_propulsion": "machinery_failure",
    "loss_of_control": "machinery_failure",
    "machinery_failure": "machinery_failure",
    "structural_failure": "structural",
    "structural": "structural",
    "weather_related": "other",
    "near_miss": "other",
    "pollution": "other",
    "environmental": "other",
    "other": "other",
}

# Known vessel types in unified schema
_VESSEL_TYPE_MAP = {
    "tanker": "tanker",
    "fishing": "fishing",
    "passenger": "passenger",
    "bulk_carrier": "bulk_carrier",
    "cargo": "general_cargo",
    "cargo_vessel": "general_cargo",
    "general_cargo": "general_cargo",
    "container": "container",
    "offshore": "offshore",
    "supply_vessel": "offshore",
    "anchor_handling": "offshore",
    "tug": "tug",
    "tugboat": "tug",
    "other": "other",
}

# Regions used in unified schema
_NORTH_SEA_STATES = {
    "united kingdom", "uk", "norway", "denmark", "netherlands", "germany",
    "belgium", "scotland", "england", "wales", "north sea",
}
_ATLANTIC_STATES = {
    "ireland", "france", "portugal", "spain", "bay of biscay", "atlantic",
    "newfoundland", "nova scotia", "maritime", "maritimes",
}
_MEDITERRANEAN_STATES = {
    "spain", "france", "italy", "greece", "turkey", "malta", "croatia",
    "mediterranean", "adriatic", "aegean",
}


def _normalize_incident_type(raw: str) -> str:
    """Map raw incident type string to unified schema type."""
    if not raw:
        return "other"
    key = raw.strip().lower().replace(" ", "_")
    # Direct lookup
    if key in _INCIDENT_TYPE_MAP:
        return _INCIDENT_TYPE_MAP[key]
    # Substring match
    for candidate, mapped in _INCIDENT_TYPE_MAP.items():
        if candidate in key or key in candidate:
            return mapped
    return "other"


def _normalize_vessel_type(raw: str) -> str:
    """Map raw vessel type string to unified schema type."""
    if not raw:
        return "other"
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    # Direct lookup
    if key in _VESSEL_TYPE_MAP:
        return _VESSEL_TYPE_MAP[key]
    # Substring match
    for candidate, mapped in _VESSEL_TYPE_MAP.items():
        if candidate in key:
            return mapped
    return "other"


def _normalize_region_maib(location: str) -> str:
    """Map MAIB coastal_state / national_location to unified region."""
    if not location:
        return "north_sea"  # Default for MAIB (UK authority)
    loc_lower = location.strip().lower()
    if any(s in loc_lower for s in _NORTH_SEA_STATES):
        return "north_sea"
    if any(s in loc_lower for s in _ATLANTIC_STATES):
        return "atlantic"
    if any(s in loc_lower for s in _MEDITERRANEAN_STATES):
        return "mediterranean"
    # MAIB data is predominantly UK/North Sea
    return "north_sea"


def _normalize_region_imo(location: str) -> str:
    """Map IMO location_description / area to unified region."""
    if not location:
        return "other"
    loc_lower = location.strip().lower()
    if "north sea" in loc_lower or "english channel" in loc_lower:
        return "north_sea"
    if "mediterranean" in loc_lower or "adriatic" in loc_lower or "aegean" in loc_lower:
        return "mediterranean"
    if "atlantic" in loc_lower or "biscay" in loc_lower:
        return "atlantic"
    if "pacific" in loc_lower:
        return "pacific"
    if "indian" in loc_lower or "malacca" in loc_lower:
        return "indian_ocean"
    if "gulf of mexico" in loc_lower or "caribbean" in loc_lower:
        return "gulf_of_mexico"
    if "arctic" in loc_lower:
        return "arctic"
    return "other"


def _normalize_region_tsb(province: str, region: str = "") -> str:
    """Map TSB province / region string to unified region."""
    combined = f"{province} {region}".strip().lower()
    if not combined:
        return "atlantic"  # Default for TSB (Canadian authority)
    if any(s in combined for s in ["british columbia", " bc", "(bc)", "pacific"]):
        return "pacific"
    if any(s in combined for s in ["nunavut", "northwest", "arctic", "(nu)", "(nt)"]):
        return "arctic"
    # Atlantic provinces
    if any(s in combined for s in [
        "nova scotia", "new brunswick", "newfoundland", "prince edward",
        "(ns)", "(nb)", "(nl)", "(pe)", "atlantic",
    ]):
        return "atlantic"
    if any(s in combined for s in ["quebec", "ontario", "(qc)", "(on)", "st. lawrence"]):
        return "atlantic"
    return "atlantic"


def _calc_severity(fatalities: int, injuries: int) -> str:
    """Calculate severity label from casualty counts."""
    fat = int(fatalities or 0)
    inj = int(injuries or 0)
    if fat >= 1:
        return "fatal"
    if inj >= 3:
        return "very_serious"
    if inj >= 1:
        return "serious"
    return "moderate"


# ---------------------------------------------------------------------------
# Per-source normalizers
# ---------------------------------------------------------------------------


def _normalize_maib(parsed: dict) -> dict:
    """Map MAIB parsed dict to SCHEMA_COLUMNS format."""
    vessel = parsed.get("vessel") or {}
    location = parsed.get("location") or {}
    fat = int(parsed.get("fatalities") or 0)
    inj = int(parsed.get("injuries") or 0)
    coastal_state = (
        location.get("coastal_state", "")
        or location.get("national_location_l1", "")
    )
    return {
        "source": "maib",
        "incident_id": str(parsed.get("source_incident_id", "")),
        "date": str(parsed.get("incident_date", ""))[:10],
        "incident_type": _normalize_incident_type(
            parsed.get("incident_type", "")
        ),
        "vessel_type": _normalize_vessel_type(
            vessel.get("ship_type_l1", "") or vessel.get("vessel_type", "")
        ),
        "region": _normalize_region_maib(coastal_state),
        "fatalities": fat,
        "injuries": inj,
        "severity": _calc_severity(fat, inj),
        "description": str(parsed.get("description", "")),
    }


def _normalize_imo(parsed: dict) -> dict:
    """Map IMO GISIS parsed dict to SCHEMA_COLUMNS format."""
    fat = int(parsed.get("fatalities") or 0)
    inj = int(parsed.get("injuries") or 0)
    location_desc = str(parsed.get("location_description", "") or "")
    return {
        "source": "imo",
        "incident_id": str(parsed.get("source_incident_id", "")),
        "date": str(parsed.get("incident_date", ""))[:10],
        "incident_type": _normalize_incident_type(
            str(parsed.get("incident_type", ""))
        ),
        "vessel_type": _normalize_vessel_type(
            str(parsed.get("vessel_type", ""))
        ),
        "region": _normalize_region_imo(location_desc),
        "fatalities": fat,
        "injuries": inj,
        "severity": _calc_severity(fat, inj),
        "description": str(parsed.get("description", "")),
    }


def _normalize_tsb(parsed: dict) -> dict:
    """Map TSB parsed dict to SCHEMA_COLUMNS format."""
    fat = int(parsed.get("fatalities") or 0)
    inj = int(parsed.get("injuries") or 0)
    location = parsed.get("location") or {}
    province = str(location.get("province", "") or "")
    region = str(location.get("region", "") or "")
    return {
        "source": "tsb",
        "incident_id": str(parsed.get("source_incident_id", "")),
        "date": str(parsed.get("incident_date", ""))[:10],
        "incident_type": _normalize_incident_type(
            parsed.get("incident_type", "")
        ),
        "vessel_type": _normalize_vessel_type(
            str((parsed.get("vessel") or {}).get("vessel_type", ""))
        ),
        "region": _normalize_region_tsb(province, region),
        "fatalities": fat,
        "injuries": inj,
        "severity": _calc_severity(fat, inj),
        "description": str(parsed.get("description", "")),
    }


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class CrossDatabaseAnalyzer:
    """
    Unified query and analysis layer over MAIB, IMO, EMSA, and TSB incident
    datasets.

    Supports live importer paths (configured via ``importer_config``) with
    graceful fallback to built-in synthetic data when importers fail or are
    not configured.

    Parameters
    ----------
    importer_config:
        Optional dict mapping source name to kwargs for the importer.
        Supported keys: ``"maib"``, ``"imo"``, ``"tsb"``.
        EMSA is always synthetic (access-restricted).

        Example::

            CrossDatabaseAnalyzer(importer_config={
                "maib": {"occurrences_file": Path("maib_occurrences.csv")},
                "tsb": {"occurrence_file": Path("occurrence.csv")},
            })
    """

    # Canonical column order for result DataFrames
    SCHEMA_COLUMNS: list[str] = [
        "source",
        "incident_id",
        "date",
        "incident_type",
        "vessel_type",
        "region",
        "fatalities",
        "injuries",
        "severity",
        "description",
    ]

    def __init__(
        self, importer_config: Optional[Dict[str, Any]] = None
    ) -> None:
        self.importer_config = importer_config or {}
        self._data: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Internal data-loading helpers
    # ------------------------------------------------------------------

    def _load_from_importer(self, source: str) -> pd.DataFrame:
        """
        Instantiate the appropriate importer and return a normalised DataFrame.

        Raises on any error (caller wraps in try/except and falls through to
        synthetic data).
        """
        cfg = self.importer_config[source]

        if source == "maib":
            from worldenergydata.marine_safety.importers.maib_importer import (
                MAIBImporter,
            )

            importer = MAIBImporter(
                occurrences_file=cfg["occurrences_file"],
                vessels_file=cfg.get("vessels_file"),
                persons_file=cfg.get("persons_file"),
                session=None,
            )
            normalizer = _normalize_maib

        elif source == "imo":
            from worldenergydata.marine_safety.importers.imo_importer import (
                IMOGISISImporter,
            )

            importer = IMOGISISImporter(
                source_path=cfg["source_path"],
                session=None,  # type: ignore[arg-type]
            )
            normalizer = _normalize_imo

        elif source == "tsb":
            from worldenergydata.marine_safety.importers.tsb_importer import (
                TSBImporter,
            )

            importer = TSBImporter(
                occurrence_file=cfg["occurrence_file"],
                vessels_file=cfg.get("vessels_file"),
                injuries_file=cfg.get("injuries_file"),
                session=None,
            )
            normalizer = _normalize_tsb

        else:
            raise ValueError(f"Unknown source for live import: {source!r}")

        rows: List[dict] = []
        for raw in importer.read_source():
            parsed = importer.parse_record(raw)
            if parsed is None:
                continue
            normalized = normalizer(parsed)
            if normalized.get("incident_id"):
                rows.append(normalized)

        if not rows:
            raise RuntimeError(f"No valid records parsed from {source} importer")

        return pd.DataFrame(rows)

    def _load_base(self) -> Tuple[pd.DataFrame, str]:
        """
        Load data from live importers if configured, else synthetic fallback.

        Returns
        -------
        (DataFrame, freshness_label)
            freshness_label is ``"live"`` if at least one live source loaded,
            else ``"synthetic"``.
        """
        frames: List[pd.DataFrame] = []
        freshness = "synthetic"

        # Try live importers for MAIB, IMO, TSB (EMSA always synthetic)
        for source in ["maib", "imo", "tsb"]:
            if source in self.importer_config:
                try:
                    df = self._load_from_importer(source)
                    frames.append(df)
                    freshness = "live"
                except Exception:
                    pass  # Fall through to synthetic for this source

        if frames:
            live_df = pd.concat(frames, ignore_index=True)
            # Fill in synthetic data for sources not loaded live
            live_sources = set(live_df["source"].unique())
            synthetic_df = pd.DataFrame(SYNTHETIC_INCIDENTS)
            missing_mask = ~synthetic_df["source"].isin(live_sources)
            missing_df = synthetic_df[missing_mask]
            if not missing_df.empty:
                combined = pd.concat([live_df, missing_df], ignore_index=True)
            else:
                combined = live_df
            combined = self._add_derived_columns(combined)
            return combined, freshness

        # Full synthetic fallback
        df = pd.DataFrame(SYNTHETIC_INCIDENTS)
        df = self._add_derived_columns(df)
        return df, "synthetic"

    def _add_derived_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add year and severity_score columns for internal use."""
        df = df.copy()
        df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year
        df["severity_score"] = df["severity"].map(SEVERITY_SCORES).fillna(0)
        return df

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(self, q: CrossDatabaseQuery) -> CrossDatabaseResult:
        """
        Execute a cross-database query with optional filters.

        Parameters
        ----------
        q:
            Query parameters.  Default ``CrossDatabaseQuery()`` returns all
            incidents from all four sources.

        Returns
        -------
        CrossDatabaseResult
            ``data`` contains only the canonical schema columns.
            ``by_source`` counts reflect the *filtered* dataset.
            ``data_freshness`` is ``"live"`` when at least one source was
            loaded from a real importer, else ``"synthetic"``.
        """
        df, freshness = self._load_base()

        if q.sources:
            df = df[df["source"].isin(q.sources)]
        if q.incident_types:
            df = df[df["incident_type"].isin(q.incident_types)]
        if q.vessel_types:
            df = df[df["vessel_type"].isin(q.vessel_types)]
        if q.start_year is not None:
            df = df[df["year"] >= q.start_year]
        if q.end_year is not None:
            df = df[df["year"] <= q.end_year]
        if q.regions:
            df = df[df["region"].isin(q.regions)]

        df = df.reset_index(drop=True)

        by_source: dict = {}
        for src in q.sources or df["source"].unique().tolist():
            by_source[src] = int((df["source"] == src).sum())

        # Only return columns that exist in the data
        available_cols = [c for c in self.SCHEMA_COLUMNS if c in df.columns]

        return CrossDatabaseResult(
            data=df[available_cols].copy(),
            query=q,
            total_incidents=len(df),
            by_source=by_source,
            correlations={},
            data_freshness=freshness,
        )

    def correlations(self, data: pd.DataFrame) -> dict:
        """
        Compute cross-source correlation metrics.

        Parameters
        ----------
        data:
            DataFrame in the unified schema (typically ``result.data``).

        Returns
        -------
        dict with keys:
          ``incident_type_severity``
              DataFrame — mean severity score (1–5) per incident type.
          ``vessel_type_region``
              DataFrame — vessel_type × region occurrence count matrix.
          ``source_overlap_rate``
              float — share of type/year/region groups reported by 2+ sources.
          ``trend_yoy``
              DataFrame — year-over-year totals by source.
        """
        df = data.copy()
        df["year"] = pd.to_datetime(df["date"]).dt.year
        df["severity_score"] = df["severity"].map(SEVERITY_SCORES)

        # Incident type vs mean severity score
        type_sev = (
            df.groupby("incident_type")["severity_score"]
            .mean()
            .reset_index()
            .rename(columns={"severity_score": "mean_severity_score"})
            .sort_values("mean_severity_score", ascending=False)
        )

        # Vessel type × region occurrence matrix
        vt_region = (
            df.groupby(["vessel_type", "region"])
            .size()
            .unstack(fill_value=0)
        )

        # Source overlap rate — groups where 2+ sources report the same
        # incident_type / year / region combination
        overlap_key = ["incident_type", "year", "region"]
        grouped = df.groupby(overlap_key)["source"].nunique()
        overlap_count = int((grouped >= 2).sum())
        total_groups = len(grouped)
        overlap_rate = (
            overlap_count / total_groups if total_groups > 0 else 0.0
        )

        # Year-over-year totals by source
        trend = (
            df.groupby(["year", "source"])
            .size()
            .reset_index(name="count")
            .sort_values(["year", "source"])
        )

        return {
            "incident_type_severity": type_sev,
            "vessel_type_region": vt_region,
            "source_overlap_rate": float(overlap_rate),
            "trend_yoy": trend,
        }

    def trend_analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Year-over-year incident counts by source and incident type.

        Returns
        -------
        DataFrame with columns: year, source, incident_type, count.
        """
        df = data.copy()
        df["year"] = pd.to_datetime(df["date"]).dt.year
        return (
            df.groupby(["year", "source", "incident_type"])
            .size()
            .reset_index(name="count")
            .sort_values(["year", "source", "incident_type"])
        )

    def top_incident_types(
        self, data: pd.DataFrame, n: int = 10
    ) -> pd.DataFrame:
        """
        Top-n incident types by total count across all sources.

        Returns
        -------
        DataFrame with columns: incident_type, count.
        Rows are sorted descending by count.
        """
        return (
            data.groupby("incident_type")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(n)
            .reset_index(drop=True)
        )

    def risk_hotspots(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Region × incident_type occurrence count matrix.

        Returns
        -------
        DataFrame indexed by region with incident_type columns.
        Cell values are incident counts (int, zero-filled).
        """
        return (
            data.groupby(["region", "incident_type"])
            .size()
            .unstack(fill_value=0)
        )
