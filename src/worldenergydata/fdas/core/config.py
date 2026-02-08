"""
FDAS Configuration Management Module

Handles loading and validation of development system assumptions, price decks,
and other configuration parameters for field development economic analysis.

Author: WorldEnergyData Team
Date: 2025-10-03
Source: Ported from FDAS load_assumptions_fixed()
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from worldenergydata.common.exceptions import ConfigError


class ConfigurationError(ConfigError):
    """Raised when configuration loading or validation fails.

    Extends the common ConfigError for FDAS-specific configuration issues.
    """

    default_code = "FDAS_CONFIG_ERROR"


# Default assumptions for development systems
DEFAULT_ASSUMPTIONS = {
    "DEV_SYSTEM": ["dry", "subsea15", "subsea20", "default"],
    "HOST_CAPEX_MM": [0.0, 300.0, 450.0, 300.0],  # Million USD
    "SURF_PER_WELL_MM": [0.0, 8.0, 12.0, 8.0],
    "MODU_LOADED_DAYRATE_MM": [0.6, 0.8, 1.0, 0.8],
    "DRY_TREE_RIG_RATE_MM": [0.5, 0.5, 0.5, 0.5],
    "ROYALTY_RATE": [0.125, 0.188, 0.188, 0.188],
    "VARIABLE_OPEX_$/BBL": [8.0, 12.0, 15.0, 12.0],
    "FIXED_OPEX_MM_PER_YEAR": [10.0, 25.0, 40.0, 25.0],
    "DISCOUNT_RATE_ANNUAL": [0.10, 0.10, 0.10, 0.10],
    "WTI_BASE_$/BBL": [75.0, 75.0, 75.0, 75.0],
}


def normalize_dev_system(system_name: Optional[str]) -> str:
    """
    Normalize development system name to standard format.

    Args:
        system_name: Raw development system name

    Returns:
        Normalized system name (dry, subsea15, subsea20, or unknown)

    Examples:
        >>> normalize_dev_system('Subsea 15')
        'subsea15'
        >>> normalize_dev_system(None)
        'unknown'
        >>> normalize_dev_system('DRY TREE')
        'dry'
    """
    if pd.isna(system_name) or system_name is None:
        return "unknown"

    normalized = (
        str(system_name)
        .strip()
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )

    # Map common variants
    if "dry" in normalized or "tree" in normalized:
        return "dry"
    elif "20" in normalized or "ultra" in normalized:
        return "subsea20"
    elif "15" in normalized or "subsea" in normalized:
        return "subsea15"
    else:
        return normalized


def classify_dev_system_by_depth(
    water_depth: Optional[float], complex_name: Optional[str] = None
) -> str:
    """
    Classify development system based on water depth.

    Args:
        water_depth: Water depth in feet
        complex_name: Optional complex name for override logic

    Returns:
        Development system classification: dry, subsea15, or subsea20

    Examples:
        >>> classify_dev_system_by_depth(400)
        'dry'
        >>> classify_dev_system_by_depth(7500)
        'subsea20'
        >>> classify_dev_system_by_depth(5000)
        'subsea15'
    """
    if water_depth is None or pd.isna(water_depth):
        return "unknown"

    depth = float(water_depth)

    if depth < 500:
        return "dry"
    elif depth < 6000:
        return "subsea15"
    else:
        return "subsea20"


class AssumptionsManager:
    """
    Manages loading and lookup of development system assumptions.

    Provides Excel-compatible assumption lookup with fallback to default
    values, matching the behavior of FDAS Aget() function.
    """

    def __init__(self, assumptions_df: Optional[pd.DataFrame] = None):
        """
        Initialize assumptions manager.

        Args:
            assumptions_df: DataFrame with development system assumptions
                           If None, uses DEFAULT_ASSUMPTIONS
        """
        if assumptions_df is None:
            self.assumptions = pd.DataFrame(DEFAULT_ASSUMPTIONS)
        else:
            self.assumptions = assumptions_df.copy()

        # Normalize development system names
        if "DEV_SYSTEM" in self.assumptions.columns:
            self.assumptions["DEV_SYSTEM"] = self.assumptions["DEV_SYSTEM"].apply(
                normalize_dev_system
            )

    @classmethod
    def from_excel(
        cls, file_path: Union[str, Path], sheet_name: str = "assumptions"
    ) -> "AssumptionsManager":
        """
        Load assumptions from Excel file.

        Args:
            file_path: Path to Excel workbook
            sheet_name: Sheet name containing assumptions

        Returns:
            AssumptionsManager instance

        Raises:
            ConfigurationError: If file cannot be loaded
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            # Check if file is in transposed format (DEV_SYSTEM as first column with param names)
            if "DEV_SYSTEM" in df.columns and len(df.columns) > 2:
                # File is transposed - DEV_SYSTEM column contains parameter names
                # Columns are development systems
                dev_systems = [
                    col for col in df.columns if col not in ["DEV_SYSTEM", "Notes"]
                ]

                # Transpose: create rows for each dev system
                data_rows = []
                for dev_sys in dev_systems:
                    row_data = {"DEV_SYSTEM": dev_sys}
                    for idx, param_name in df["DEV_SYSTEM"].items():
                        # Clean parameter name to uppercase with underscores
                        clean_param = (
                            str(param_name).replace(" ", "_").replace("/", "_").upper()
                        )
                        value = df.loc[idx, dev_sys]
                        if pd.notna(value):
                            row_data[clean_param] = value
                    data_rows.append(row_data)

                df = pd.DataFrame(data_rows)

            return cls(df)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load assumptions from {file_path}: {e}"
            )

    @classmethod
    def from_dict(cls, assumptions_dict: Dict[str, Any]) -> "AssumptionsManager":
        """
        Create assumptions manager from dictionary.

        Args:
            assumptions_dict: Dictionary with assumption parameters

        Returns:
            AssumptionsManager instance
        """
        df = pd.DataFrame(assumptions_dict)
        return cls(df)

    def get(self, system_name: str, parameter: str, default: float = 0.0) -> float:
        """
        Get assumption value for development system and parameter.

        This replicates the FDAS Aget() function behavior with fallback
        to 'default' system if specific system not found.

        Args:
            system_name: Development system (dry, subsea15, subsea20)
            parameter: Parameter name (case-insensitive)
            default: Default value if not found

        Returns:
            Parameter value for system

        Examples:
            >>> mgr = AssumptionsManager()
            >>> mgr.get('subsea15', 'HOST_CAPEX_MM')
            300.0
            >>> mgr.get('subsea20', 'SURF_PER_WELL_MM')
            12.0
        """
        # Normalize inputs
        system = normalize_dev_system(system_name)
        param_upper = parameter.upper()

        # Try direct match first
        if param_upper in self.assumptions.columns:
            # Try exact system match
            mask = self.assumptions["DEV_SYSTEM"] == system

            # Fallback to default system if not found
            if not mask.any():
                mask = self.assumptions["DEV_SYSTEM"] == "default"

            # Return value if found
            if mask.any():
                value = self.assumptions.loc[mask, param_upper].iloc[0]
                return float(value) if pd.notna(value) else default

        # Try alternate formats (/ replaced with _ in cleaning)
        for alt_param in [
            param_upper.replace("/", "_"),
            param_upper.replace("$/", "$_"),
        ]:
            if alt_param in self.assumptions.columns:
                mask = self.assumptions["DEV_SYSTEM"] == system
                if not mask.any():
                    mask = self.assumptions["DEV_SYSTEM"] == "default"

                if mask.any():
                    value = self.assumptions.loc[mask, alt_param].iloc[0]
                    return float(value) if pd.notna(value) else default

        return default

    def get_all_for_system(self, system_name: str) -> Dict[str, float]:
        """
        Get all assumption parameters for a development system.

        Args:
            system_name: Development system name

        Returns:
            Dictionary of parameter name -> value
        """
        system = normalize_dev_system(system_name)
        mask = self.assumptions["DEV_SYSTEM"] == system

        if not mask.any():
            mask = self.assumptions["DEV_SYSTEM"] == "default"

        if not mask.any():
            return {}

        row = self.assumptions[mask].iloc[0]
        return {
            col: float(row[col])
            for col in self.assumptions.columns
            if col != "DEV_SYSTEM" and pd.notna(row[col])
        }

    def validate(self) -> Dict[str, Any]:
        """
        Validate assumptions configuration.

        Returns:
            Dictionary with validation results
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "systems_found": (
                list(self.assumptions["DEV_SYSTEM"].unique())
                if "DEV_SYSTEM" in self.assumptions.columns
                else []
            ),
            "parameters_found": [
                col for col in self.assumptions.columns if col != "DEV_SYSTEM"
            ],
        }

        # Check required systems
        required_systems = {"dry", "subsea15", "subsea20", "default"}
        found_systems = set(validation["systems_found"])
        missing_systems = required_systems - found_systems

        if missing_systems:
            validation["warnings"].append(
                f"Missing development systems: {missing_systems}"
            )

        # Check required parameters
        required_params = {
            "HOST_CAPEX_MM",
            "SURF_PER_WELL_MM",
            "ROYALTY_RATE",
            "VARIABLE_OPEX_$/BBL",
            "DISCOUNT_RATE_ANNUAL",
        }
        found_params = set(validation["parameters_found"])
        missing_params = required_params - found_params

        if missing_params:
            validation["errors"].append(
                f"Missing required parameters: {missing_params}"
            )
            validation["valid"] = False

        # Check for negative values where inappropriate
        for param in ["HOST_CAPEX_MM", "SURF_PER_WELL_MM", "DISCOUNT_RATE_ANNUAL"]:
            if param in self.assumptions.columns:
                if (self.assumptions[param] < 0).any():
                    validation["errors"].append(f"Negative values found in {param}")
                    validation["valid"] = False

        return validation


class PriceDeckManager:
    """
    Manages WTI and oil price deck loading and interpolation.
    """

    def __init__(self, wti_df: Optional[pd.DataFrame] = None):
        """
        Initialize price deck manager.

        Args:
            wti_df: DataFrame with columns: year_month, wti_price
        """
        self.wti_df = wti_df

    @classmethod
    def from_excel(
        cls, file_path: Union[str, Path], sheet_name: str = "WTI"
    ) -> "PriceDeckManager":
        """
        Load WTI price deck from Excel.

        Args:
            file_path: Path to Excel workbook
            sheet_name: Sheet name with WTI prices

        Returns:
            PriceDeckManager instance
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            return cls(df)
        except Exception as e:
            raise ConfigurationError(f"Failed to load WTI prices from {file_path}: {e}")

    def get_price(self, year_month: str, default: float = 75.0) -> float:
        """
        Get WTI price for a specific year-month.

        Args:
            year_month: Year-month string (e.g., '2024-01')
            default: Default price if not found

        Returns:
            WTI price in $/BBL
        """
        if self.wti_df is None:
            return default

        # Try exact match
        mask = self.wti_df["year_month"] == year_month
        if mask.any():
            price = self.wti_df.loc[mask, "wti_price"].iloc[0]
            return float(price) if pd.notna(price) else default

        return default


def load_configuration(config_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Load complete FDAS configuration from directory.

    Args:
        config_dir: Directory containing configuration files

    Returns:
        Dictionary with assumptions_manager and price_deck_manager

    Raises:
        ConfigurationError: If configuration cannot be loaded
    """
    config_path = Path(config_dir)

    if not config_path.exists():
        raise ConfigurationError(f"Configuration directory not found: {config_dir}")

    config = {}

    # Load assumptions
    assumptions_file = config_path / "default_assumptions.xlsx"
    if assumptions_file.exists():
        config["assumptions_manager"] = AssumptionsManager.from_excel(assumptions_file)
    else:
        # Use defaults
        config["assumptions_manager"] = AssumptionsManager()

    # Load WTI prices
    wti_file = config_path / "wti_monthly.xlsx"
    if wti_file.exists():
        config["price_deck_manager"] = PriceDeckManager.from_excel(wti_file)
    else:
        config["price_deck_manager"] = PriceDeckManager()

    return config
