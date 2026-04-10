"""
SME Data Loader for Financial Analysis
Imports and uses HierarchicalDataLoader from comprehensive reports
Implements SME V20 specific data loading logic
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from worldenergydata.common.data_resolver import get_module_data

from ...data.sources.bin.api_data import APIData
from ...data.sources.bin.block_data import BlockData
from ...data.sources.bin.lease_data import LeaseData

# Import from comprehensive reports module
from ...reports.comprehensive.data_loader_enhanced import HierarchicalDataLoader
from ...reports.comprehensive.hierarchical_aggregator import CostStructure, PriceDeck


def normalize_lease_number(val: Any) -> str:
    """
    Normalize lease number to standard format (G-prefix)

    Args:
        val: Lease number value

    Returns:
        Normalized lease number with G prefix
    """
    s = str(val).strip().upper()
    m = re.fullmatch(r"G?(\d+)", s)
    return "G" + m.group(1) if m else s


def std_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names by stripping whitespace

    Args:
        df: DataFrame to standardize

    Returns:
        DataFrame with standardized column names
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def pick_column(
    df: pd.DataFrame, keys: List[str], required: bool = False
) -> Optional[str]:
    """
    Find first matching column from list of candidates (case-insensitive)

    Args:
        df: DataFrame to search
        keys: List of candidate column names
        required: Raise error if not found

    Returns:
        First matching column name or None
    """
    colsU = [c.upper() for c in df.columns]
    for k in keys:
        if k.upper() in colsU:
            return df.columns[colsU.index(k.upper())]
    if required:
        raise KeyError(
            f"Missing required column; tried {keys}; have {list(df.columns)}"
        )
    return None


def validate_required_columns(df: pd.DataFrame, required_cols: List[str]) -> None:
    """
    Validate that required columns exist in dataframe

    Args:
        df: DataFrame to validate
        required_cols: List of required column names

    Raises:
        ValueError: If required columns are missing
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def validate_date_columns(df: pd.DataFrame, date_cols: List[str]) -> pd.DataFrame:
    """
    Validate and convert date columns to datetime

    Args:
        df: DataFrame with date columns
        date_cols: List of column names to convert

    Returns:
        DataFrame with converted date columns
    """
    result = df.copy()
    for col in date_cols:
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], errors="coerce")
    return result


class SMEDataLoader:
    """
    SME-specific data loader that uses HierarchicalDataLoader from comprehensive reports
    Implements V20 data processing logic while reusing existing infrastructure
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize SME data loader

        Args:
            data_path: Path to BSEE data directory
        """
        self.data_path = data_path or get_module_data("bsee")

        # Initialize HierarchicalDataLoader from comprehensive reports
        self.hierarchical_loader = HierarchicalDataLoader(data_path=self.data_path)

        # Initialize individual data fetchers (reusing from comprehensive)
        self.block_data_fetcher = BlockData()
        self.lease_data_fetcher = LeaseData()
        self.api_data_fetcher = APIData()

        # Cache for processed data
        self._cache = {}

    def load_leases_data(self, excel_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load lease data from Excel or binary files

        Args:
            excel_path: Optional path to Excel file

        Returns:
            DataFrame with lease information
        """
        if excel_path and Path(excel_path).exists():
            # Load from Excel if provided
            df = pd.read_excel(excel_path)
        else:
            # Use hierarchical loader to get lease data
            df = self.lease_data_fetcher.get_lease_data()

        df = std_columns(df)

        # Normalize lease numbers
        if "LEASE_NUM" in df.columns:
            df["LEASE_NUM"] = df["LEASE_NUM"].map(normalize_lease_number)

        return df

    def load_production_data(self, dev_name: Optional[str] = None) -> pd.DataFrame:
        """
        Load production data for a development

        Args:
            dev_name: Development name to filter

        Returns:
            DataFrame with production data
        """
        # Use the API data fetcher to get production data
        prod_data = self.api_data_fetcher.get_production_data()

        if dev_name:
            # Filter by development if specified
            prod_data = self.filter_by_development(prod_data, dev_name)

        return prod_data

    def load_drilling_completion_data(
        self, excel_path: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load drilling and completion data from Excel
        Returns both monthly and totals dataframes

        Args:
            excel_path: Path to D&C Excel file

        Returns:
            Tuple of (monthly_df, totals_df)
        """
        xls = pd.ExcelFile(excel_path)
        monthly_frames = []
        totals_frames = []

        for sheet in xls.sheet_names:
            df = std_columns(xls.parse(sheet))
            if df.empty:
                continue

            # Rename columns to standard names
            rename_map = {
                "DRILL DAYS": "DRILL_DAYS",
                "DRILLING_DAYS": "DRILL_DAYS",
                "DRILLING DAYS": "DRILL_DAYS",
                "COMP DAYS": "COMP_DAYS",
                "COMPLETION_DAYS": "COMP_DAYS",
                "COMPLETION DAYS": "COMP_DAYS",
                "TOTAL_DEPTH": "TOTAL_DEPTH_DATE",
                "TD_DATE": "TOTAL_DEPTH_DATE",
            }

            for old, new in rename_map.items():
                if old in df.columns and new not in df.columns:
                    df = df.rename(columns={old: new})

            # Find well column
            well_col = pick_column(df, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"])
            month_col = pick_column(df, ["YEARMONTH", "MONTH", "DATE"])

            # Process monthly data
            if (
                well_col
                and month_col
                and "DRILL_DAYS" in df.columns
                and "COMP_DAYS" in df.columns
            ):
                df[month_col] = pd.to_datetime(df[month_col], errors="coerce")
                df = df.rename(columns={month_col: "YearMonth"})
                df["YearMonth"] = df["YearMonth"].dt.to_period("M").dt.to_timestamp()

                keep_cols = [
                    c
                    for c in [
                        "YearMonth",
                        well_col,
                        "DRILL_DAYS",
                        "COMP_DAYS",
                        "LEASE_NUM",
                        "LEASE_NAME",
                        "DEV_NAME",
                        "WELL_SPUD_DATE",
                        "TOTAL_DEPTH_DATE",
                    ]
                    if c in df.columns
                ]
                monthly_frames.append(df[keep_cols].copy())

            # Process totals data
            if (
                well_col
                and "WELL_SPUD_DATE" in df.columns
                and "TOTAL_DEPTH_DATE" in df.columns
                and "DRILL_DAYS" in df.columns
            ):

                keep_cols = [
                    c
                    for c in [
                        well_col,
                        "WELL_SPUD_DATE",
                        "TOTAL_DEPTH_DATE",
                        "DRILL_DAYS",
                        "COMP_DAYS",
                        "LEASE_NUM",
                        "LEASE_NAME",
                        "DEV_NAME",
                    ]
                    if c in df.columns
                ]
                totals_frames.append(df[keep_cols].copy())

        monthly = (
            pd.concat(monthly_frames, ignore_index=True)
            if monthly_frames
            else pd.DataFrame()
        )
        totals = (
            pd.concat(totals_frames, ignore_index=True)
            if totals_frames
            else pd.DataFrame()
        )

        # Normalize lease numbers
        for df in (monthly, totals):
            if not df.empty and "LEASE_NUM" in df.columns:
                df["LEASE_NUM"] = df["LEASE_NUM"].map(normalize_lease_number)

        return monthly, totals

    def filter_by_development(
        self, df: pd.DataFrame, dev_name: str, leases_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Filter dataframe by development name

        Args:
            df: DataFrame to filter
            dev_name: Development name
            leases_df: Optional lease DataFrame for joining

        Returns:
            Filtered DataFrame
        """
        if df is None or df.empty:
            return df

        result = df.copy()
        result.columns = [c.upper() for c in result.columns]

        # If DEV_NAME not in columns, try to join with leases
        if "DEV_NAME" not in result.columns and leases_df is not None:
            leases = leases_df.copy()
            leases.columns = [c.upper() for c in leases.columns]

            if "LEASE_NUM" in result.columns and "LEASE_NUM" in leases.columns:
                result = result.merge(
                    leases[["LEASE_NUM", "DEV_NAME"]], on="LEASE_NUM", how="left"
                )
            elif "LEASE_NAME" in result.columns and "LEASE_NAME" in leases.columns:
                result = result.merge(
                    leases[["LEASE_NAME", "DEV_NAME"]], on="LEASE_NAME", how="left"
                )

        # Filter by development name
        if "DEV_NAME" in result.columns:
            result = result[
                result["DEV_NAME"].astype(str).str.strip().str.upper()
                == str(dev_name).strip().upper()
            ]

        return result

    def _matrix_to_timeseries(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert matrix-style production data to timeseries format

        Args:
            df: Matrix-style DataFrame with well columns and month rows

        Returns:
            Timeseries DataFrame with YearMonth and well production
        """
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]

        # Identify ID columns and month columns
        id_cols = [
            c for c in df.columns if c.upper() in ("WELL_NAME", "API_WELL_NUMBER")
        ]
        month_cols = [c for c in df.columns if re.fullmatch(r"\d{4}-\d{2}", str(c))]

        if not id_cols:
            raise ValueError("Cannot identify well name column in matrix-style sheet")

        well_key = id_cols[0]

        # Melt to long format
        long = df.melt(
            id_vars=[well_key],
            value_vars=month_cols,
            var_name="YearMonth",
            value_name="BBLS_PER_DAY",
        )

        # Convert types
        long["YearMonth"] = pd.to_datetime(
            long["YearMonth"], format="%Y-%m", errors="coerce"
        )
        long["BBLS_PER_DAY"] = pd.to_numeric(
            long["BBLS_PER_DAY"], errors="coerce"
        ).fillna(0.0)

        # Calculate monthly production from daily rate
        days_in_month = long["YearMonth"].dt.days_in_month
        long["OIL_BBL"] = (long["BBLS_PER_DAY"] * days_in_month).astype(float)

        # Rename well column to WELL_NAME for consistency
        long = long.rename(columns={well_key: "WELL_NAME"})

        return long[["YearMonth", "WELL_NAME", "OIL_BBL"]]

    def build_development_day_maps(
        self,
        dev_name: str,
        leases_df: pd.DataFrame,
        production_df: pd.DataFrame,
        dc_totals: pd.DataFrame,
    ) -> Tuple[Dict, Dict, set]:
        """
        Build drilling and completion day maps for a development

        Args:
            dev_name: Development name
            leases_df: Lease data
            production_df: Production data
            dc_totals: D&C totals data

        Returns:
            Tuple of (drill_map, comp_map, all_wells)
        """
        # Filter D&C data for development
        dc_dev = self.filter_by_development(dc_totals, dev_name, leases_df)

        drill_map = {}
        comp_map = {}
        all_wells = set()

        if not dc_dev.empty:
            well_col = pick_column(
                dc_dev, ["WELL_NAME", "WELL", "API_WELL_NUMBER", "API"]
            )

            if well_col:
                for _, row in dc_dev.iterrows():
                    well = str(row[well_col]).strip()
                    if well:
                        all_wells.add(well)

                        # Add to drill map if has drill days
                        if (
                            "DRILL_DAYS" in row
                            and pd.notna(row["DRILL_DAYS"])
                            and row["DRILL_DAYS"] > 0
                        ):
                            spud_date = pd.to_datetime(
                                row.get("WELL_SPUD_DATE"), errors="coerce"
                            )
                            if pd.notna(spud_date):
                                month_key = spud_date.strftime("%Y-%m")
                                if month_key not in drill_map:
                                    drill_map[month_key] = {}
                                drill_map[month_key][well] = float(row["DRILL_DAYS"])

                        # Add to comp map if has comp days
                        if (
                            "COMP_DAYS" in row
                            and pd.notna(row["COMP_DAYS"])
                            and row["COMP_DAYS"] > 0
                        ):
                            td_date = pd.to_datetime(
                                row.get("TOTAL_DEPTH_DATE"), errors="coerce"
                            )
                            if pd.notna(td_date):
                                month_key = td_date.strftime("%Y-%m")
                                if month_key not in comp_map:
                                    comp_map[month_key] = {}
                                comp_map[month_key][well] = float(row["COMP_DAYS"])

        return drill_map, comp_map, all_wells

    def load_wti_price_deck(
        self, excel_path: Optional[str] = None, flat_price: float = 80.0
    ) -> PriceDeck:
        """
        Load WTI price deck using comprehensive report's PriceDeck class

        Args:
            excel_path: Optional path to WTI price Excel
            flat_price: Flat price if no Excel provided

        Returns:
            PriceDeck instance
        """
        if excel_path and Path(excel_path).exists():
            # Load monthly WTI prices
            df = pd.read_excel(excel_path)
            df = std_columns(df)

            # Find date and price columns
            date_col = pick_column(df, ["Date", "Month", "YearMonth", "Period"])
            price_col = pick_column(df, ["WTI", "Price", "Oil Price", "$/bbl"])

            if date_col and price_col:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                prices = dict(zip(df[date_col], df[price_col]))
            else:
                prices = {}
        else:
            prices = {}

        # Create PriceDeck instance from comprehensive reports
        return PriceDeck(oil_price=flat_price, wti_monthly=prices)

    def load_cost_structure(self, assumptions: Dict[str, Any]) -> CostStructure:
        """
        Load cost structure using comprehensive report's CostStructure class

        Args:
            assumptions: Dictionary of cost assumptions

        Returns:
            CostStructure instance
        """
        # Map SME assumptions to CostStructure parameters
        return CostStructure(
            drill_cost_per_day=assumptions.get("Drilling_Cost_Per_Day_USD", 100000),
            comp_cost_per_day=assumptions.get("Completion_Cost_Per_Day_USD", 75000),
            opex_per_bbl=assumptions.get("OPEX_Per_Barrel", 25.0),
            tax_rate=assumptions.get("Tax_Rate", 0.35),
        )

    def get_cached_data(self, key: str, loader_func: callable) -> Any:
        """
        Get data from cache or load if not cached

        Args:
            key: Cache key
            loader_func: Function to load data if not cached

        Returns:
            Cached or loaded data
        """
        if key not in self._cache:
            self._cache[key] = loader_func()
        return self._cache[key]

    def load_block_data(self, block_name: str) -> pd.DataFrame:
        """
        Load block data using hierarchical loader

        Args:
            block_name: Block name to load

        Returns:
            Block data DataFrame
        """
        return self.hierarchical_loader.load_block(block_name)

    def load_field_data(self, field_name: str) -> pd.DataFrame:
        """
        Load field data using hierarchical loader

        Args:
            field_name: Field name to load

        Returns:
            Field data DataFrame
        """
        return self.hierarchical_loader.load_field(field_name)

    def _load_from_source(self, source_func: callable) -> Any:
        """
        Helper to load from source function

        Args:
            source_func: Function that loads data

        Returns:
            Loaded data
        """
        return source_func()
