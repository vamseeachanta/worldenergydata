"""SODIR adapter -- wires the Norwegian sodir module into the common adapter interface.

Converts SODIR-native units (Sm3, million Sm3, billion Sm3) to SI (m3)
and maps processor output into the normalised AdapterResult contract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterInterface,
    AdapterResult,
    DataAvailability,
    SourceMetadata,
)
from worldenergydata.bsee.pipeline.adapters.data_availability import (
    SODIR_AVAILABILITY,
)
from worldenergydata.bsee.pipeline.adapters.units import BBL_TO_M3, BCF_TO_M3

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://factmaps.sodir.no/api/rest"

# FieldProcessor outputs reserves in mmbbl / bcf (already converted from Sm3).
# One more hop to SI m3.
_MMBBL_TO_M3 = 1e6 * BBL_TO_M3  # ~158 987 m3 per million bbl
_BCF_TO_M3 = BCF_TO_M3  # ~28 316 846 m3 per bcf

_PROD_COLS = [
    "cumulative_oil_m3",
    "cumulative_gas_m3",
    "cumulative_ngl_m3",
    "cumulative_condensate_m3",
    "recoverable_oil_m3",
    "recoverable_gas_m3",
]
_DRILL_COLS = [
    "wellbore_name",
    "spud_date",
    "completion_date",
    "duration_days",
    "operator",
    "total_depth_m",
    "water_depth_m",
]
_SUMM_COLS = ["purpose", "status", "count"]


class SodirAdapter(AdapterInterface):
    """Adapter bridging the SODIR module to the multi-source adapter interface.

    Args:
        api_client: Pre-configured SodirAPIClient (or duck-typed stub).
            If *None* a default client is created on first use.
        cache_dir: Optional local cache directory.
    """

    def __init__(
        self,
        api_client: Any | None = None,
        cache_dir: Path | str | None = None,
    ) -> None:
        self._api_client = api_client
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._field_proc: Any | None = None
        self._wb_proc: Any | None = None

    # -- lazy init -----------------------------------------------------------

    def _ensure_client(self) -> None:
        if self._api_client is not None:
            return
        from worldenergydata.sodir.api_client import SodirAPIClient

        self._api_client = SodirAPIClient(base_url=_DEFAULT_BASE_URL)

    def _ensure_processors(self) -> None:
        if self._field_proc is None:
            from worldenergydata.sodir.processors.field_processor import FieldProcessor

            self._field_proc = FieldProcessor()
        if self._wb_proc is None:
            from worldenergydata.sodir.processors.wellbore_processor import (
                WellboreProcessor,
            )

            self._wb_proc = WellboreProcessor()

    # -- public interface ----------------------------------------------------

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        """Resolve *query* (field name) against SODIR and return SI data.

        Never raises; failures become warnings with empty DataFrames.
        """
        self._ensure_client()
        self._ensure_processors()

        warnings: list[str] = []
        field_name = query.strip()

        # 1. Fetch and match field
        matched = self._fetch_field(field_name, warnings)
        canonical = matched.get("field_name", field_name) if matched else field_name
        fid = str(matched.get("field_id", "")) if matched else ""

        # 2. Fetch wellbores for this field
        wellbores = self._fetch_wellbores(canonical, warnings)

        # 3. Build domain DataFrames
        wb_summary = self._build_wellbore_summary(wellbores)
        drilling = self._build_drilling_activities(wellbores)
        production = self._build_production(matched, warnings)

        # 4. Unavailable domains
        for dom in ("casing", "intervention", "well_path"):
            warnings.append(f"{dom} data is unavailable from the SODIR source.")

        return AdapterResult(
            source=self.get_metadata(),
            field_code=fid,
            field_name=canonical,
            leases=(),
            area_code=matched.get("main_area", "") if matched else "",
            well_count=len(wellbores),
            query_type="field_name",
            wellbore_summary=wb_summary,
            well_paths=pd.DataFrame(),
            casing_strings=pd.DataFrame(),
            drilling_activities=drilling,
            completion_activities=pd.DataFrame(),
            intervention_activities=pd.DataFrame(),
            production=production,
            warnings=warnings,
        )

    def get_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            source_id="sodir",
            source_name="Sodir / NPD FactPages",
            jurisdiction="Norwegian Continental Shelf",
            api_base_url=_DEFAULT_BASE_URL,
            update_cadence="monthly",
        )

    def get_availability(self) -> DataAvailability:
        return SODIR_AVAILABILITY

    # -- internal fetchers ---------------------------------------------------

    def _fetch_field(
        self,
        field_name: str,
        warnings: list[str],
    ) -> Optional[dict[str, Any]]:
        """Fetch all fields and return the one matching *field_name*."""
        try:
            raw = self._api_client.get_fields()
            processed = self._field_proc.process_batch(raw)
            for f in processed:
                if f.get("field_name", "").lower() == field_name.lower():
                    return f
            warnings.append(
                f"Field '{field_name}' not found in SODIR data "
                f"({len(processed)} fields searched)."
            )
            return None
        except Exception as exc:
            warnings.append(f"Failed to fetch fields from SODIR: {exc}")
            return None

    def _fetch_wellbores(
        self,
        field_name: str,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        """Fetch wellbores and filter to those belonging to *field_name*."""
        try:
            raw = self._api_client.get_wellbores()
            processed = self._wb_proc.process_batch(raw)
            return [
                wb
                for wb in processed
                if (wb.get("field") or "").lower() == field_name.lower()
            ]
        except Exception as exc:
            warnings.append(f"Failed to fetch wellbores from SODIR: {exc}")
            return []

    # -- DataFrame builders --------------------------------------------------

    def _build_wellbore_summary(self, wellbores: list[dict[str, Any]]) -> pd.DataFrame:
        """Wellbore count grouped by purpose and status."""
        if not wellbores:
            return pd.DataFrame(columns=_SUMM_COLS)
        df = pd.DataFrame(wellbores)
        summary = (
            df.groupby(["purpose_normalized", "status_normalized"])
            .size()
            .reset_index(name="count")
        )
        summary.columns = _SUMM_COLS
        return summary

    def _build_drilling_activities(
        self, wellbores: list[dict[str, Any]]
    ) -> pd.DataFrame:
        """Spud date, duration, operator, depths (already in metres)."""
        if not wellbores:
            return pd.DataFrame(columns=_DRILL_COLS)
        rows = [
            {
                "wellbore_name": wb.get("wellbore_name", ""),
                "spud_date": wb.get("drilling_start_date"),
                "completion_date": wb.get("completion_date"),
                "duration_days": wb.get("drilling_duration_days"),
                "operator": wb.get("operator", ""),
                "total_depth_m": wb.get("total_depth_m"),
                "water_depth_m": wb.get("water_depth_m"),
            }
            for wb in wellbores
        ]
        return pd.DataFrame(rows)

    def _build_production(
        self,
        field_data: Optional[dict[str, Any]],
        warnings: list[str],
    ) -> pd.DataFrame:
        """Single-row field-level cumulative production in SI m3."""
        if field_data is None:
            return pd.DataFrame(columns=_PROD_COLS)

        def _to_m3_mmbbl(val: Any) -> float | None:
            try:
                return float(val) * _MMBBL_TO_M3 if val is not None else None
            except (TypeError, ValueError):
                return None

        def _to_m3_bcf(val: Any) -> float | None:
            try:
                return float(val) * _BCF_TO_M3 if val is not None else None
            except (TypeError, ValueError):
                return None

        row = {
            "cumulative_oil_m3": _to_m3_mmbbl(
                field_data.get("cumulative_oil_production_mmbbl")
            ),
            "cumulative_gas_m3": _to_m3_bcf(
                field_data.get("cumulative_gas_production_bcf")
            ),
            "cumulative_ngl_m3": _to_m3_mmbbl(
                field_data.get("cumulative_ngl_production_mmbbl")
            ),
            "cumulative_condensate_m3": _to_m3_mmbbl(
                field_data.get("cumulative_condensate_production_mmbbl")
            ),
            "recoverable_oil_m3": _to_m3_mmbbl(field_data.get("recoverable_oil_mmbbl")),
            "recoverable_gas_m3": _to_m3_bcf(field_data.get("recoverable_gas_bcf")),
        }
        warnings.append(
            "SODIR production is field-level cumulative only; "
            "monthly time-series and per-well allocation unavailable."
        )
        return pd.DataFrame([row])
