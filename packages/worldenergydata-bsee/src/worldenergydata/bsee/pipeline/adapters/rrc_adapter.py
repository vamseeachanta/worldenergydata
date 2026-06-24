# ABOUTME: Texas RRC adapter wiring existing Texas RRC module into the common adapter interface
# ABOUTME: Converts RRC well, permit, completion, and production data into SI-unit AdapterResult

"""Texas RRC adapter for the multi-source field analysis pipeline.

Normalises Texas Railroad Commission data into :class:`AdapterResult`.
Unit conversions (ft->m, BBL->m3, MCF->m3) applied on ingestion.
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
from worldenergydata.bsee.pipeline.adapters.data_availability import RRC_AVAILABILITY
from worldenergydata.bsee.pipeline.adapters.units import (
    barrels_to_m3,
    convert_column,
    feet_to_metres,
    mcf_to_m3,
)

logger = logging.getLogger(__name__)

_META = SourceMetadata(
    source_id="rrc",
    source_name="Railroad Commission of Texas",
    jurisdiction="Texas onshore and state waters",
    api_base_url="https://webapps2.rrc.texas.gov/EWA",
    update_cadence="monthly",
)

_KEEP_DRILL = [
    "permit_number",
    "permit_type",
    "approved_date",
    "total_depth",
    "horizontal_length",
    "is_horizontal",
    "well_purpose",
    "api_number",
]
_KEEP_COMP = [
    "api_number",
    "completion_date",
    "total_depth",
    "well_type",
    "is_horizontal",
]
_WORKOVER_TYPES = ["workover", "recompletion", "plug_back", "reenter"]


class RRCAdapter(AdapterInterface):
    """Adapter wiring Texas RRC into the common pipeline interface."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path("./data/texas_rrc")

    # -- public interface ---------------------------------------------------

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        field_name = query.strip().upper()
        district = kwargs.get("district")
        w: list[str] = []

        wells = self._load_wells(w)
        fw = self._filter_field(wells, field_name, district, w)
        leases = self._extract_leases(fw)

        w.append("Casing data unavailable from Texas RRC PDQ bulk downloads.")
        w.append(
            "Well path survey data (MD/inc/azi) not available from "
            "Texas RRC PDQ public dumps."
        )

        return AdapterResult(
            source=self.get_metadata(),
            field_code=field_name,
            field_name=field_name,
            leases=leases,
            area_code=str(district) if district else "",
            well_count=len(fw),
            query_type="field_name",
            wellbore_summary=self._wellbore_summary(fw, w),
            well_paths=pd.DataFrame(),
            casing_strings=pd.DataFrame(),
            drilling_activities=self._drilling(field_name, district, w),
            completion_activities=self._completions(fw, w),
            intervention_activities=self._interventions(field_name, district, fw, w),
            production=self._production(field_name, district, w),
            warnings=w,
        )

    def get_metadata(self) -> SourceMetadata:
        return _META

    def get_availability(self) -> DataAvailability:
        return RRC_AVAILABILITY

    # -- CSV loading --------------------------------------------------------

    def _load_csvs(self, pat: str, w: list[str], label: str) -> pd.DataFrame:
        try:
            files = sorted(self._data_dir.glob(pat))
            if not files:
                w.append(
                    f"No {label} files found matching " f"'{self._data_dir / pat}'."
                )
                return pd.DataFrame()
            frames = []
            for f in files:
                try:
                    frames.append(pd.read_csv(f, low_memory=False))
                except Exception as e:
                    w.append(f"Failed to read {f.name}: {e}")
            return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        except Exception as e:
            w.append(f"Error loading {label} data: {e}")
            return pd.DataFrame()

    def _load_wells(self, w: list[str]) -> pd.DataFrame:
        df = self._load_csvs("texas_rrc_og_well*.csv", w, "well")
        if df.empty:
            return df
        try:
            from worldenergydata.texas_rrc.processors.well_processor import (
                WellProcessor,
            )

            return WellProcessor().process(df, validate=False)
        except Exception as e:
            w.append(f"WellProcessor failed, using raw columns: {e}")
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            return df

    def _run_processor(self, df: pd.DataFrame, proc_cls: str, w: list[str]):
        """Import *proc_cls* by short name and process *df*."""
        mod_map = {
            "PermitProcessor": "worldenergydata.texas_rrc.processors.permit_processor",
            "ProductionProcessor": "worldenergydata.texas_rrc.processors.production_processor",
        }
        try:
            import importlib

            mod = importlib.import_module(mod_map[proc_cls])
            return getattr(mod, proc_cls)().process(df, validate=False)
        except Exception as e:
            w.append(f"{proc_cls} failed: {e}")
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            return df

    # -- district normalisation ---------------------------------------------

    @staticmethod
    def _norm_district(district: Any) -> str:
        d = str(district).strip().upper()
        return d.zfill(2) if d.isdigit() and len(d) == 1 else d

    def _field_district_filter(
        self,
        df: pd.DataFrame,
        field: str,
        district: Any,
    ) -> pd.DataFrame:
        if "field_name" in df.columns:
            df = df[df["field_name"].str.upper().str.strip() == field]
        if district is not None and "district" in df.columns:
            df = df[
                df["district"].astype(str).str.strip() == self._norm_district(district)
            ]
        return df.copy()

    # -- field / lease helpers -----------------------------------------------

    def _filter_field(
        self, wells: pd.DataFrame, field: str, district: Any, w: list[str]
    ) -> pd.DataFrame:
        if wells.empty:
            w.append(f"No well data available; cannot filter for field '{field}'.")
            return pd.DataFrame()
        mask = pd.Series(True, index=wells.index)
        if "field_name" in wells.columns:
            mask &= wells["field_name"].str.upper().str.strip() == field
        else:
            w.append("Well data missing 'field_name' column; returning all wells.")
        if district is not None:
            if "district" in wells.columns:
                mask &= wells["district"].astype(
                    str
                ).str.strip() == self._norm_district(district)
            else:
                w.append(
                    "Well data missing 'district' column; district filter ignored."
                )
        result = wells[mask].copy()
        if result.empty:
            suffix = f" in district {district}." if district else "."
            w.append(f"No wells matched field '{field}'" + suffix)
        return result

    @staticmethod
    def _extract_leases(fw: pd.DataFrame) -> tuple[str, ...]:
        if fw.empty or "lease_number" not in fw.columns:
            return ()
        return tuple(sorted(fw["lease_number"].dropna().unique().astype(str)))

    # -- domain builders ----------------------------------------------------

    def _wellbore_summary(self, fw: pd.DataFrame, w: list[str]) -> pd.DataFrame:
        if fw.empty:
            return pd.DataFrame()
        try:
            s = fw.get("well_status", pd.Series())
            avg_ft = fw.get("total_depth", pd.Series()).mean()
            return pd.DataFrame(
                [
                    {
                        "total_wells": len(fw),
                        "active_wells": int((s == "active").sum()),
                        "plugged_wells": int(
                            s.isin(["plugged", "plugged_and_abandoned"]).sum()
                        ),
                        "horizontal_wells": int(
                            fw.get("is_horizontal", pd.Series(dtype=bool)).sum()
                        ),
                        "avg_depth_m": (
                            feet_to_metres(avg_ft) if pd.notna(avg_ft) else None
                        ),
                    }
                ]
            )
        except Exception as e:
            w.append(f"Error building wellbore summary: {e}")
            return pd.DataFrame()

    def _drilling(self, field: str, district: Any, w: list[str]) -> pd.DataFrame:
        df = self._load_csvs("texas_rrc_drilling_permits*.csv", w, "drilling permit")
        if df.empty:
            return df
        df = self._run_processor(df, "PermitProcessor", w)
        df = self._field_district_filter(df, field, district)
        if df.empty:
            return df
        convert_column(df, "total_depth", feet_to_metres)
        convert_column(df, "horizontal_length", feet_to_metres)
        keep = [c for c in _KEEP_DRILL if c in df.columns]
        return df[keep].reset_index(drop=True) if keep else df.reset_index(drop=True)

    def _completions(self, fw: pd.DataFrame, w: list[str]) -> pd.DataFrame:
        comp = self._load_csvs("texas_rrc_og_completion*.csv", w, "completion")
        if not comp.empty:
            comp.columns = [c.lower().replace(" ", "_") for c in comp.columns]
            return comp.reset_index(drop=True)
        if fw.empty or "completion_date" not in fw.columns:
            return pd.DataFrame()
        done = fw[fw["completion_date"].notna()].copy()
        if done.empty:
            return pd.DataFrame()
        keep = [c for c in _KEEP_COMP if c in done.columns]
        result = done[keep].copy() if keep else done.copy()
        convert_column(result, "total_depth", feet_to_metres)
        return result.reset_index(drop=True)

    def _interventions(
        self, field: str, district: Any, fw: pd.DataFrame, w: list[str]
    ) -> pd.DataFrame:
        parts: list[pd.DataFrame] = []

        # Workover permits
        perm = self._load_csvs(
            "texas_rrc_drilling_permits*.csv", w, "permit (workover)"
        )
        if not perm.empty:
            perm = self._run_processor(perm, "PermitProcessor", w)
            perm = self._field_district_filter(perm, field, district)
            if "permit_type" in perm.columns:
                wo = perm[perm["permit_type"].isin(_WORKOVER_TYPES)].copy()
                if not wo.empty:
                    wo["intervention_type"] = wo["permit_type"]
                    convert_column(wo, "total_depth", feet_to_metres)
                    keep = [
                        c
                        for c in [
                            "api_number",
                            "approved_date",
                            "intervention_type",
                            "total_depth",
                        ]
                        if c in wo.columns
                    ]
                    parts.append(wo[keep])

        # Plug dates from well data
        if not fw.empty and "plug_date" in fw.columns:
            plugged = fw[fw["plug_date"].notna()].copy()
            if not plugged.empty:
                plugged["intervention_type"] = "plug_and_abandon"
                keep = [
                    c
                    for c in ["api_number", "plug_date", "intervention_type"]
                    if c in plugged.columns
                ]
                parts.append(
                    plugged[keep].rename(columns={"plug_date": "approved_date"})
                )

        if not parts:
            w.append(
                "Intervention data is partial: no workover job records "
                "or W-12 plugging reports available from RRC PDQ dumps."
            )
            return pd.DataFrame()
        return pd.concat(parts, ignore_index=True)

    def _production(self, field: str, district: Any, w: list[str]) -> pd.DataFrame:
        df = self._load_csvs("texas_rrc_og_production*.csv", w, "production")
        if df.empty:
            return df
        df = self._run_processor(df, "ProductionProcessor", w)
        df = self._field_district_filter(df, field, district)
        if df.empty:
            return pd.DataFrame()

        vol_cols = [
            "oil_production",
            "gas_production",
            "water_production",
            "condensate",
            "boe_total",
        ]
        agg = {c: "sum" for c in vol_cols if c in df.columns}
        if "production_date" in df.columns and agg:
            df = df.groupby("production_date", as_index=False).agg(agg)

        convert_column(df, "oil_production", barrels_to_m3)
        convert_column(df, "gas_production", mcf_to_m3)
        convert_column(df, "water_production", barrels_to_m3)
        convert_column(df, "condensate", barrels_to_m3)
        convert_column(df, "boe_total", barrels_to_m3)
        return df.reset_index(drop=True)


__all__ = ["RRCAdapter"]
