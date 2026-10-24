# ABOUTME: Excel parser for Mexico CNH data exports
# ABOUTME: Handles Spanish column names and data normalization

import logging
import unicodedata
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


def _header_key(value: str) -> str:
    """Fold accents before looking up Spanish headers (issue #1282).

    Python 3.11 unicodedata: NFKD decomposition and combining marks.
    https://docs.python.org/3.11/library/unicodedata.html
    """
    decomposed = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return text.lower().strip().replace(" ", "_").replace("-", "_")


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
        self.column_mapping = {
            _header_key(key): value
            for key, value in {**COLUMN_MAPPING, **(column_mapping or {})}.items()
        }
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
        required_columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Load Excel file and optionally normalize columns.

        Args:
            file_path: Path to the Excel file.
            sheet_name: Sheet name or index to read.
            skip_rows: Number of rows to skip at the start.
            normalize: Whether to normalize column names.
            required_columns: Required source headers or canonical target names.
                Each must map to a known target and be present. Requires normalize.

        Returns:
            DataFrame with loaded and optionally normalized data.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be parsed.
        """
        if required_columns and not normalize:
            raise ValueError("required_columns requires normalize=True")
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path.as_posix()}")

        logger.info(f"Loading Excel file: {file_path.as_posix()}")

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
            df = self.normalize_columns(df, required_columns=required_columns)
            df = self._convert_dtypes(df)

        return df

    def normalize_columns(
        self, df: pd.DataFrame, required_columns: list[str] | None = None
    ) -> pd.DataFrame:
        """Fold accents and map headers; reject missing/unmapped required columns.

        Required names may be source headers or canonical targets. Optional
        unknown columns remain normalized text for custom export metadata.
        """
        original_columns = list(df.columns)
        keys = [_header_key(col) for col in original_columns]
        targets = [self.column_mapping.get(key, key) for key in keys]
        known_targets = set(self.column_mapping.values())
        for required in required_columns or []:
            key = _header_key(required)
            target = self.column_mapping.get(key, key)
            if target not in known_targets or target not in targets:
                raise ValueError(f"Missing or unmapped required column: {required}")
        if len(set(targets)) != len(targets):
            raise ValueError(f"Duplicate normalized columns: {original_columns}")
        df = df.copy()
        df.columns = targets
        df.attrs["source_columns"] = original_columns
        return df

    @staticmethod
    def _require_recognized_columns(
        df: pd.DataFrame, candidates: list[str], report: str
    ) -> None:
        # Structural policy for #1282: a specialized parser must recognize
        # its data schema. Callers declare stricter requirements explicitly.
        if not any(col in df.columns for col in candidates):
            originals = df.attrs.get("source_columns", list(df.columns))
            raise ValueError(
                f"Missing or unmapped required {report} column; "
                f"expected one of {candidates}; source columns: {originals}"
            )

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
        required_columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Parse production data export.

        This method is specialized for CNH production reports, which
        typically contain monthly or daily production data by well or field.

        Args:
            file_path: Path to the production report Excel file.
            required_columns: Required source headers or canonical target names.
            sheet_name: Sheet name or index containing production data.

        Returns:
            DataFrame with normalized production data.
        """
        df = self.load(
            file_path, sheet_name=sheet_name, required_columns=required_columns
        )

        # Ensure numeric production columns
        production_cols = [
            "oil_production",
            "gas_production",
            "water_production",
            "condensate_production",
            "cumulative_oil",
            "cumulative_gas",
            "bpd",
            "barrels_per_day",
            "mmcfd",
            "mcf",
        ]

        self._require_recognized_columns(df, production_cols, "production")
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
        required_columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Parse well data export.

        This method is specialized for CNH well reports, which
        contain well metadata including location, depth, and status.

        Args:
            file_path: Path to the well report Excel file.
            required_columns: Required source headers or canonical target names.
            sheet_name: Sheet name or index containing well data.

        Returns:
            DataFrame with normalized well data.
        """
        df = self.load(
            file_path, sheet_name=sheet_name, required_columns=required_columns
        )

        self._require_recognized_columns(
            df,
            [
                "well",
                "well_name",
                "well_id",
                "well_number",
                "latitude",
                "longitude",
                "x_coordinate",
                "y_coordinate",
                "depth",
                "total_depth",
                "vertical_depth",
            ],
            "well",
        )
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
