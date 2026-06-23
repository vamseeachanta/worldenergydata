# ABOUTME: Excel parser for Mexico CNH data exports
# ABOUTME: Handles Spanish column names and data normalization

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

# Spanish to English column mapping for CNH data
COLUMN_MAPPING: Dict[str, str] = {
    # Well identifiers
    "pozo": "well",
    "nombre_pozo": "well_name",
    "clave_pozo": "well_id",
    "numero_pozo": "well_number",
    # Field information
    "campo": "field",
    "nombre_campo": "field_name",
    "cuenca": "basin",
    # Operator information
    "operador": "operator",
    "contratista": "contractor",
    "asignatario": "assignee",
    # Production data
    "produccion_petroleo": "oil_production",
    "produccion_aceite": "oil_production",
    "produccion_gas": "gas_production",
    "produccion_agua": "water_production",
    "produccion_condensado": "condensate_production",
    "petroleo_acumulado": "cumulative_oil",
    "gas_acumulado": "cumulative_gas",
    # Units and rates
    "barriles_por_dia": "barrels_per_day",
    "miles_pies_cubicos": "mcf",
    "mmpcd": "mmcfd",
    "bpd": "bpd",
    # Dates
    "fecha": "date",
    "fecha_inicio": "start_date",
    "fecha_terminacion": "completion_date",
    "mes": "month",
    "ano": "year",
    "anio": "year",
    # Location
    "latitud": "latitude",
    "longitud": "longitude",
    "coordenada_x": "x_coordinate",
    "coordenada_y": "y_coordinate",
    "estado": "state",
    "municipio": "municipality",
    "entidad": "entity",
    # Well characteristics
    "profundidad": "depth",
    "profundidad_total": "total_depth",
    "profundidad_vertical": "vertical_depth",
    "clasificacion": "classification",
    "tipo": "type",
    "tipo_pozo": "well_type",
    "estatus": "status",
    "trayectoria": "trajectory",
    # Contract information
    "contrato": "contract",
    "tipo_contrato": "contract_type",
    "area_contractual": "contract_area",
    "bloque": "block",
    # Reservoir information
    "formacion": "formation",
    "yacimiento": "reservoir",
    "intervalo": "interval",
}

# Data type specifications for common columns
DTYPE_MAPPING: Dict[str, str] = {
    "well": "string",
    "well_name": "string",
    "well_id": "string",
    "field": "string",
    "field_name": "string",
    "operator": "string",
    "basin": "string",
    "state": "string",
    "status": "string",
    "well_type": "string",
    "contract": "string",
    "formation": "string",
}


class CNHExcelLoader:
    """Load and parse CNH Excel exports.

    This loader handles Excel files exported from Mexico's CNH
    (Comision Nacional de Hidrocarburos) data portal. It normalizes
    Spanish column names to English and handles common data formats.
    """

    def __init__(
        self,
        column_mapping: Optional[Dict[str, str]] = None,
        date_columns: Optional[List[str]] = None,
    ) -> None:
        """Initialize the Excel loader.

        Args:
            column_mapping: Custom column mapping to override defaults.
            date_columns: List of column names to parse as dates.
        """
        self.column_mapping = {**COLUMN_MAPPING, **(column_mapping or {})}
        self.date_columns = date_columns or [
            "fecha",
            "date",
            "fecha_inicio",
            "fecha_terminacion",
        ]

    def load(
        self,
        file_path: Union[str, Path],
        sheet_name: Union[str, int] = 0,
        skip_rows: int = 0,
        normalize: bool = True,
    ) -> pd.DataFrame:
        """Load Excel file and optionally normalize columns.

        Args:
            file_path: Path to the Excel file.
            sheet_name: Sheet name or index to read.
            skip_rows: Number of rows to skip at the start.
            normalize: Whether to normalize column names.

        Returns:
            DataFrame with loaded and optionally normalized data.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be parsed.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        logger.info(f"Loading Excel file: {file_path}")

        try:
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                skiprows=skip_rows,
                engine="openpyxl",
            )
        except Exception as e:
            raise ValueError(f"Failed to parse Excel file: {e}") from e

        logger.info(f"Loaded {len(df)} rows from {file_path.name}")

        if normalize:
            df = self.normalize_columns(df)
            df = self._convert_dtypes(df)

        return df

    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Translate Spanish columns to English.

        Args:
            df: DataFrame with Spanish column names.

        Returns:
            DataFrame with normalized English column names.
        """
        # Normalize column names: lowercase, strip whitespace, replace spaces
        df.columns = [
            str(col).lower().strip().replace(" ", "_").replace("-", "_")
            for col in df.columns
        ]

        # Apply mapping
        rename_map = {}
        for col in df.columns:
            if col in self.column_mapping:
                rename_map[col] = self.column_mapping[col]

        if rename_map:
            df = df.rename(columns=rename_map)
            logger.debug(f"Renamed columns: {rename_map}")

        return df

    def _convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to appropriate data types.

        Args:
            df: DataFrame to convert.

        Returns:
            DataFrame with converted data types.
        """
        # Parse date columns
        for col in df.columns:
            if col in self.date_columns or "date" in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except (ValueError, TypeError):
                    pass

        # Apply string types for known string columns
        for col, dtype in DTYPE_MAPPING.items():
            if col in df.columns and dtype == "string":
                df[col] = df[col].astype("string")

        return df

    def parse_production_report(
        self,
        file_path: Union[str, Path],
        sheet_name: Union[str, int] = 0,
    ) -> pd.DataFrame:
        """Parse production data export.

        This method is specialized for CNH production reports, which
        typically contain monthly or daily production data by well or field.

        Args:
            file_path: Path to the production report Excel file.
            sheet_name: Sheet name or index containing production data.

        Returns:
            DataFrame with normalized production data.
        """
        df = self.load(file_path, sheet_name=sheet_name)

        # Ensure numeric production columns
        production_cols = [
            "oil_production",
            "gas_production",
            "water_production",
            "condensate_production",
            "cumulative_oil",
            "cumulative_gas",
        ]

        for col in production_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Sort by date if available
        if "date" in df.columns:
            df = df.sort_values("date")

        return df

    def parse_well_report(
        self,
        file_path: Union[str, Path],
        sheet_name: Union[str, int] = 0,
    ) -> pd.DataFrame:
        """Parse well data export.

        This method is specialized for CNH well reports, which
        contain well metadata including location, depth, and status.

        Args:
            file_path: Path to the well report Excel file.
            sheet_name: Sheet name or index containing well data.

        Returns:
            DataFrame with normalized well data.
        """
        df = self.load(file_path, sheet_name=sheet_name)

        # Ensure numeric coordinate columns
        coord_cols = ["latitude", "longitude", "x_coordinate", "y_coordinate"]
        for col in coord_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Ensure numeric depth columns
        depth_cols = ["depth", "total_depth", "vertical_depth"]
        for col in depth_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def list_sheets(self, file_path: Union[str, Path]) -> List[str]:
        """List all sheet names in an Excel file.

        Args:
            file_path: Path to the Excel file.

        Returns:
            List of sheet names.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        xl = pd.ExcelFile(file_path, engine="openpyxl")
        return xl.sheet_names

    def load_all_sheets(
        self,
        file_path: Union[str, Path],
        normalize: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """Load all sheets from an Excel file.

        Args:
            file_path: Path to the Excel file.
            normalize: Whether to normalize column names.

        Returns:
            Dictionary mapping sheet names to DataFrames.
        """
        sheets = self.list_sheets(file_path)
        result = {}

        for sheet in sheets:
            try:
                result[sheet] = self.load(
                    file_path, sheet_name=sheet, normalize=normalize
                )
            except Exception as e:
                logger.warning(f"Failed to load sheet '{sheet}': {e}")

        return result
