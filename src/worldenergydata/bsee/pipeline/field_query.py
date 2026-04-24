"""Unified query interface for BSEE field analysis pipeline.

Accepts a lease number, field name, or geological region and resolves
to a FieldContext that downstream pipeline stages consume.
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldContext:
    """Immutable context describing a resolved BSEE field.

    Attributes:
        field_code: BSEE field code (e.g. "001") or era name for era queries.
        field_name: Human-readable display name (e.g. "BUCKSKIN").
        leases: Lease numbers belonging to this field.
        area_code: OCS area code if available, else empty string.
        geological_era: Dominant geological era or "Unknown".
        well_count: Number of unique wells associated with the field.
        query_type: How the field was resolved ("lease", "field_name",
            "field_code", or "era").
    """

    field_code: str
    field_name: str
    leases: tuple[str, ...]
    area_code: str
    geological_era: str
    well_count: int
    query_type: str


class FieldQueryError(ValueError):
    """Raised when a query cannot be resolved to a known BSEE field."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_field(
    query: str,
    field_resolver,
    era_classifier,
    lease_field_map: pd.DataFrame | None = None,
) -> FieldContext:
    """Resolve a user query to a :class:`FieldContext`.

    Resolution order:
    1. Lease number lookup (if *lease_field_map* is provided).
    2. Direct field code match.
    3. Case-insensitive field name match.
    4. Geological era name match.

    Args:
        query: A lease number, field code, field name, or era name.
        field_resolver: A :class:`FieldNameResolver` (or compatible stub).
        era_classifier: A :class:`GeologicalEraClassifier` (or compatible stub).
        lease_field_map: Optional DataFrame with columns ``LEASE_NUMBER``,
            ``FIELD_NAME_CODE``, and optionally ``AREA_CODE``.

    Returns:
        A populated :class:`FieldContext`.

    Raises:
        FieldQueryError: If *query* cannot be matched to any field or era.
    """
    query = query.strip()
    all_fields = field_resolver.get_all_field_names()

    # 1. Lease number lookup
    ctx = _try_lease_lookup(
        query, lease_field_map, field_resolver, era_classifier, all_fields
    )
    if ctx is not None:
        return ctx

    # 2. Field code match
    ctx = _try_field_code(
        query, field_resolver, era_classifier, all_fields, lease_field_map
    )
    if ctx is not None:
        return ctx

    # 3. Field name match (case-insensitive)
    ctx = _try_field_name(
        query, field_resolver, era_classifier, all_fields, lease_field_map
    )
    if ctx is not None:
        return ctx

    # 4. Geological era match
    ctx = _try_era(query, era_classifier, lease_field_map)
    if ctx is not None:
        return ctx

    raise FieldQueryError(f"Cannot resolve query: {query}")


def build_lease_field_map(data_dir: Path) -> pd.DataFrame:
    """Build a lease-to-field mapping DataFrame from BSEE binary data.

    Loads ``deepqual/mv_deep_water_field_leases.bin`` and extracts the
    columns ``LEASE_NUMBER``, ``FIELD_NAME_CODE``, and ``AREA_CODE``
    (if present).

    Returns an empty :class:`~pandas.DataFrame` when the file is missing,
    is a Git LFS stub, or cannot be read.
    """
    file_path = data_dir / "deepqual" / "mv_deep_water_field_leases.bin"
    df = _load_pickle_safe(file_path)
    if df.empty:
        return pd.DataFrame()

    required = "LEASE_NUMBER", "FIELD_NAME_CODE"
    for col in required:
        if col not in df.columns:
            logger.warning(
                "Column %s not found in %s — returning empty map", col, file_path
            )
            return pd.DataFrame()

    cols = list(required)
    if "AREA_CODE" in df.columns:
        cols.append("AREA_CODE")

    return df[cols].drop_duplicates().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Resolution helpers (private)
# ---------------------------------------------------------------------------


def _try_lease_lookup(
    query: str,
    lease_field_map: pd.DataFrame | None,
    field_resolver,
    era_classifier,
    all_fields: dict[str, str],
) -> FieldContext | None:
    """Attempt to resolve *query* as a lease number."""
    if lease_field_map is None or lease_field_map.empty:
        return None

    if "LEASE_NUMBER" not in lease_field_map.columns:
        return None

    match = lease_field_map[lease_field_map["LEASE_NUMBER"] == query]
    if match.empty:
        return None

    field_code = str(match.iloc[0]["FIELD_NAME_CODE"]).strip()
    area_code = ""
    if "AREA_CODE" in match.columns:
        area_code = str(match.iloc[0]["AREA_CODE"]).strip()

    # Gather all leases for this field
    all_leases = _leases_for_field(field_code, lease_field_map)

    return FieldContext(
        field_code=field_code,
        field_name=field_resolver.resolve(field_code),
        leases=tuple(all_leases),
        area_code=area_code,
        geological_era="Unknown",
        well_count=0,
        query_type="lease",
    )


def _try_field_code(
    query: str,
    field_resolver,
    era_classifier,
    all_fields: dict[str, str],
    lease_field_map: pd.DataFrame | None,
) -> FieldContext | None:
    """Attempt to resolve *query* as a direct field code."""
    if query not in all_fields:
        return None

    leases = _leases_for_field(query, lease_field_map)
    area_code = _area_for_field(query, lease_field_map)

    # Note: well_count and geological_era are set to defaults here because
    # we cannot reliably determine field-specific wells from the era
    # classifier alone (it holds global well data).  The pipeline runner
    # derives accurate field-scoped stats from production data.
    return FieldContext(
        field_code=query,
        field_name=all_fields[query],
        leases=tuple(leases),
        area_code=area_code,
        geological_era="Unknown",
        well_count=0,
        query_type="field_code",
    )


def _try_field_name(
    query: str,
    field_resolver,
    era_classifier,
    all_fields: dict[str, str],
    lease_field_map: pd.DataFrame | None,
) -> FieldContext | None:
    """Attempt to resolve *query* as a case-insensitive field name."""
    query_upper = query.upper()
    for code, name in all_fields.items():
        if name.upper() == query_upper:
            leases = _leases_for_field(code, lease_field_map)
            area_code = _area_for_field(code, lease_field_map)

            return FieldContext(
                field_code=code,
                field_name=name,
                leases=tuple(leases),
                area_code=area_code,
                geological_era="Unknown",
                well_count=0,
                query_type="field_name",
            )
    return None


def _try_era(
    query: str,
    era_classifier,
    lease_field_map: pd.DataFrame | None,
) -> FieldContext | None:
    """Attempt to resolve *query* as a geological era name."""
    eras = getattr(era_classifier, "ERAS", [])
    era_upper_map = {e.upper(): e for e in eras}
    matched_era = era_upper_map.get(query.upper())
    if matched_era is None:
        return None

    # Gather wells in this era
    well_eras = era_classifier.get_well_eras()
    era_wells = [api for api, era in well_eras.items() if era == matched_era]

    # Gather leases associated with era wells (best effort)
    leases: list[str] = []
    # We cannot directly map wells to leases without additional data;
    # keep leases empty unless lease_field_map provides something richer.

    return FieldContext(
        field_code=matched_era,
        field_name=f"All {matched_era} fields",
        leases=tuple(leases),
        area_code="",
        geological_era=matched_era,
        well_count=len(era_wells),
        query_type="era",
    )


# ---------------------------------------------------------------------------
# Utility helpers (private)
# ---------------------------------------------------------------------------


def _leases_for_field(
    field_code: str, lease_field_map: pd.DataFrame | None
) -> list[str]:
    """Return all lease numbers for *field_code* from the map."""
    if lease_field_map is None or lease_field_map.empty:
        return []
    if "FIELD_NAME_CODE" not in lease_field_map.columns:
        return []
    matched = lease_field_map[lease_field_map["FIELD_NAME_CODE"] == field_code]
    return matched["LEASE_NUMBER"].tolist()


def _area_for_field(field_code: str, lease_field_map: pd.DataFrame | None) -> str:
    """Return the first area code for *field_code*, or empty string."""
    if lease_field_map is None or lease_field_map.empty:
        return ""
    if "AREA_CODE" not in lease_field_map.columns:
        return ""
    matched = lease_field_map[lease_field_map["FIELD_NAME_CODE"] == field_code]
    if matched.empty:
        return ""
    return str(matched.iloc[0]["AREA_CODE"]).strip()


def _dominant_era_for_wells(well_apis: list[str], era_classifier) -> str:
    """Return the dominant era across a set of well APIs."""
    return era_classifier.classify_field(well_apis)


def _load_pickle_safe(file_path: Path) -> pd.DataFrame:
    """Load a pickle file, returning empty DataFrame for LFS stubs or errors."""
    if not file_path.exists():
        logger.warning("File not found: %s", file_path)
        return pd.DataFrame()

    try:
        with open(file_path, "rb") as f:
            header = f.read(40)
        if b"version https://git-lfs" in header:
            logger.warning("LFS stub detected (not materialized): %s", file_path)
            return pd.DataFrame()

        with open(file_path, "rb") as f:
            obj = pickle.load(f)  # nosec B301

        if isinstance(obj, pd.DataFrame):
            return obj

        logger.warning("File does not contain a DataFrame: %s", file_path)
        return pd.DataFrame()

    except Exception as e:
        logger.error("Error loading %s: %s", file_path, e)
        return pd.DataFrame()
