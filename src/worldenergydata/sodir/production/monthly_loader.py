"""Monthly production loader for SODIR NCS fields.

Fetches and processes monthly production data per field from the SODIR API,
with unit conversions (Sm3 to bbl, MSm3 to Mcf) and local caching.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.common.units import OilUnits, GasUnits

logger = logging.getLogger(__name__)

# Backward-compatible module-level aliases (sourced from common.units)
SM3_TO_BBL = OilUnits.SM3_TO_BBL
MSM3_TO_MCF = GasUnits.MSM3_TO_MMSCF  # 1 million Sm3 = 35.3147 thousand cubic feet (Mcf)

# SODIR monthly production endpoint
PRODUCTION_ENDPOINT = "/field/production/monthly"


class MonthlyProductionLoader:
    """Load monthly production data from SODIR API.

    Supports fetching per-field or all-field production, parsing SODIR's
    raw JSON response format, and converting units.
    """

    def __init__(self, api_client=None):
        """Initialize loader.

        Args:
            api_client: SodirAPIClient instance (optional; for testing, pass a mock).
        """
        self.api_client = api_client
        self._cache: Dict[str, pd.DataFrame] = {}

    def load_field_production(self, field_name: str) -> pd.DataFrame:
        """Load monthly production for a specific field.

        Args:
            field_name: SODIR field name (e.g. "EDVARD GRIEG").

        Returns:
            DataFrame with columns: field_name, year, month, oil_sm3, gas_sm3,
            ngl_sm3, condensate_sm3, water_injected_sm3, oil_bbl, gas_mcf.
        """
        cache_key = self._cache_key(field_name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_data = self._fetch_production_data()
        field_records = [r for r in all_data if r.get("fldName") == field_name]

        if not field_records:
            return self._empty_dataframe()

        parsed = [self.parse_raw_record(r) for r in field_records]
        df = pd.DataFrame(parsed)
        df = self._add_converted_columns(df)

        self._cache[cache_key] = df
        return df

    def load_all_production(self) -> pd.DataFrame:
        """Load monthly production for all fields.

        Returns:
            DataFrame with all field production data.
        """
        all_data = self._fetch_production_data()
        if not all_data:
            return self._empty_dataframe()

        parsed = [self.parse_raw_record(r) for r in all_data]
        df = pd.DataFrame(parsed)
        df = self._add_converted_columns(df)
        return df

    def parse_raw_record(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single raw production record from SODIR API response.

        Args:
            raw: Raw dict from SODIR API JSON.

        Returns:
            Parsed record with standardized field names and Sm3 units.
        """
        oil_msm3 = self._safe_float(raw.get("prfPrdOilNetMillSm3", 0))
        gas_bsm3 = self._safe_float(raw.get("prfPrdGasNetBillSm3", 0))
        ngl_msm3 = self._safe_float(raw.get("prfPrdNGLNetMillSm3", 0))
        condensate_msm3 = self._safe_float(raw.get("prfPrdCondensateNetMillSm3", 0))
        water_msm3 = self._safe_float(raw.get("prfPrdProducedWaterInFieldMillSm3", 0))

        return {
            "field_name": raw.get("fldName", ""),
            "year": int(raw.get("prfYear", 0)),
            "month": int(raw.get("prfMonth", 0)),
            "oil_sm3": oil_msm3 * 1e6,
            "gas_sm3": gas_bsm3 * 1e9,
            "ngl_sm3": ngl_msm3 * 1e6,
            "condensate_sm3": condensate_msm3 * 1e6,
            "water_injected_sm3": water_msm3 * 1e6,
        }

    def convert_sm3_to_bbl(self, sm3: float) -> float:
        """Convert standard cubic meters to barrels.

        Args:
            sm3: Volume in Sm3.

        Returns:
            Volume in barrels.
        """
        return sm3 * SM3_TO_BBL

    def convert_msm3_to_mcf(self, msm3: float) -> float:
        """Convert million standard cubic meters to thousand cubic feet.

        Args:
            msm3: Volume in million Sm3.

        Returns:
            Volume in Mcf.
        """
        return msm3 * MSM3_TO_MCF

    def _fetch_production_data(self) -> List[Dict[str, Any]]:
        """Fetch raw production data from API."""
        if self.api_client is None:
            logger.warning("No API client configured; returning empty data")
            return []

        response = self.api_client.get(PRODUCTION_ENDPOINT)
        return response.get("data", []) if response else []

    def _add_converted_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add oil_bbl and gas_mcf columns derived from Sm3 values."""
        if df.empty:
            return df
        df["oil_bbl"] = df["oil_sm3"] * SM3_TO_BBL
        df["gas_mcf"] = (df["gas_sm3"] / 1e6) * MSM3_TO_MCF
        return df

    def _cache_key(self, field_name: str) -> str:
        """Generate a cache key for a field."""
        return f"monthly_production:{field_name}"

    def _empty_dataframe(self) -> pd.DataFrame:
        """Return an empty DataFrame with the expected schema."""
        return pd.DataFrame(
            columns=[
                "field_name", "year", "month", "oil_sm3", "gas_sm3",
                "ngl_sm3", "condensate_sm3", "water_injected_sm3",
                "oil_bbl", "gas_mcf",
            ]
        )

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert to float, defaulting to 0."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
