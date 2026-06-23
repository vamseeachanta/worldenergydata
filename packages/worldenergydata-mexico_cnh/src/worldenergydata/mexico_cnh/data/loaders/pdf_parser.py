# ABOUTME: PDF parser for Mexico CNH reports
# ABOUTME: Extracts tables and data from CNH PDF publications

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

logger = logging.getLogger(__name__)

# Try to import pdfplumber, which is optional
try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available. PDF parsing will be limited.")


class CNHPDFParser:
    """Parse CNH PDF reports.

    This parser extracts tables and data from PDF documents published
    by Mexico's CNH (Comision Nacional de Hidrocarburos). It uses
    pdfplumber for table extraction when available.
    """

    def __init__(
        self,
        table_settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the PDF parser.

        Args:
            table_settings: Custom settings for pdfplumber table extraction.

        Raises:
            ImportError: If pdfplumber is not available.
        """
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError(
                "pdfplumber is required for PDF parsing. "
                "Install it with: pip install pdfplumber"
            )

        # Default table extraction settings optimized for CNH reports
        self.table_settings = table_settings or {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 10,
            "min_words_vertical": 3,
            "min_words_horizontal": 1,
        }

    def extract_tables(
        self,
        file_path: Union[str, Path],
        pages: Optional[Union[int, List[int]]] = None,
    ) -> List[pd.DataFrame]:
        """Extract all tables from PDF.

        Args:
            file_path: Path to the PDF file.
            pages: Page number(s) to extract from (0-indexed).
                   If None, extracts from all pages.

        Returns:
            List of DataFrames, one per extracted table.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If no tables are found.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"Extracting tables from PDF: {file_path}")

        tables = []

        with pdfplumber.open(file_path) as pdf:
            # Determine which pages to process
            if pages is None:
                page_indices = range(len(pdf.pages))
            elif isinstance(pages, int):
                page_indices = [pages]
            else:
                page_indices = pages

            for page_idx in page_indices:
                if page_idx >= len(pdf.pages):
                    logger.warning(f"Page {page_idx} out of range, skipping")
                    continue

                page = pdf.pages[page_idx]
                page_tables = page.extract_tables(self.table_settings)

                for table_data in page_tables:
                    if table_data and len(table_data) > 1:
                        df = self._table_to_dataframe(table_data)
                        if df is not None and not df.empty:
                            tables.append(df)
                            logger.debug(
                                f"Extracted table from page {page_idx + 1}: "
                                f"{len(df)} rows, {len(df.columns)} columns"
                            )

        logger.info(f"Extracted {len(tables)} tables from {file_path.name}")
        return tables

    def _table_to_dataframe(
        self,
        table_data: List[List[Optional[str]]],
    ) -> Optional[pd.DataFrame]:
        """Convert extracted table data to DataFrame.

        Args:
            table_data: Raw table data from pdfplumber.

        Returns:
            DataFrame or None if conversion fails.
        """
        if not table_data or len(table_data) < 2:
            return None

        # First row is typically headers
        headers = table_data[0]
        rows = table_data[1:]

        # Clean headers
        headers = [
            self._clean_cell(h) if h else f"col_{i}" for i, h in enumerate(headers)
        ]

        # Clean data rows
        cleaned_rows = []
        for row in rows:
            if row and any(cell for cell in row):
                cleaned_row = [self._clean_cell(cell) for cell in row]
                cleaned_rows.append(cleaned_row)

        if not cleaned_rows:
            return None

        try:
            df = pd.DataFrame(cleaned_rows, columns=headers)
            return df
        except Exception as e:
            logger.warning(f"Failed to create DataFrame: {e}")
            return None

    def _clean_cell(self, cell: Optional[str]) -> str:
        """Clean a cell value.

        Args:
            cell: Raw cell value.

        Returns:
            Cleaned cell value.
        """
        if cell is None:
            return ""

        # Convert to string and clean
        text = str(cell).strip()

        # Replace multiple whitespace with single space
        text = re.sub(r"\s+", " ", text)

        # Remove common PDF artifacts
        text = text.replace("\n", " ").replace("\r", "")

        return text

    def extract_production_data(
        self,
        file_path: Union[str, Path],
        pages: Optional[Union[int, List[int]]] = None,
    ) -> pd.DataFrame:
        """Extract production data from monthly report.

        This method is specialized for CNH monthly production reports,
        which typically contain production statistics by field or operator.

        Args:
            file_path: Path to the production report PDF.
            pages: Page number(s) to extract from.

        Returns:
            DataFrame with consolidated production data.
        """
        tables = self.extract_tables(file_path, pages=pages)

        if not tables:
            raise ValueError(f"No tables found in {file_path}")

        # Find production-related tables by looking for common column names
        production_keywords = [
            "produccion",
            "production",
            "petroleo",
            "oil",
            "gas",
            "barriles",
            "barrels",
            "mmpcd",
            "bpd",
        ]

        production_tables = []
        for df in tables:
            columns_lower = [str(c).lower() for c in df.columns]
            if any(kw in " ".join(columns_lower) for kw in production_keywords):
                production_tables.append(df)

        if not production_tables:
            # If no obvious production tables, return the largest table
            logger.warning(
                "No production-specific tables found, returning largest table"
            )
            return max(tables, key=len)

        # Combine production tables if multiple
        if len(production_tables) == 1:
            result = production_tables[0]
        else:
            result = pd.concat(production_tables, ignore_index=True)

        # Try to convert numeric columns
        result = self._convert_numeric_columns(result)

        return result

    def _convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Attempt to convert columns to numeric types.

        Args:
            df: DataFrame to process.

        Returns:
            DataFrame with numeric conversions applied.
        """
        for col in df.columns:
            # Skip if column looks like an identifier
            if any(kw in col.lower() for kw in ["nombre", "name", "id", "clave"]):
                continue

            # Try numeric conversion
            try:
                # Handle Spanish number format (comma as decimal separator)
                numeric_values = df[col].str.replace(",", ".", regex=False)
                numeric_values = pd.to_numeric(numeric_values, errors="coerce")

                # Only apply if most values are numeric
                if numeric_values.notna().sum() > len(df) * 0.5:
                    df[col] = numeric_values
            except (AttributeError, TypeError):
                pass

        return df

    def extract_text(
        self,
        file_path: Union[str, Path],
        pages: Optional[Union[int, List[int]]] = None,
    ) -> str:
        """Extract all text from PDF.

        Args:
            file_path: Path to the PDF file.
            pages: Page number(s) to extract from.

        Returns:
            Extracted text as a single string.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        text_parts = []

        with pdfplumber.open(file_path) as pdf:
            if pages is None:
                page_indices = range(len(pdf.pages))
            elif isinstance(pages, int):
                page_indices = [pages]
            else:
                page_indices = pages

            for page_idx in page_indices:
                if page_idx >= len(pdf.pages):
                    continue

                page = pdf.pages[page_idx]
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    def get_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get PDF metadata.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dictionary with PDF metadata.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        with pdfplumber.open(file_path) as pdf:
            metadata = {
                "num_pages": len(pdf.pages),
                "metadata": pdf.metadata,
            }

            # Get page dimensions from first page
            if pdf.pages:
                first_page = pdf.pages[0]
                metadata["page_width"] = first_page.width
                metadata["page_height"] = first_page.height

        return metadata

    def find_tables_by_header(
        self,
        file_path: Union[str, Path],
        header_keywords: List[str],
    ) -> List[Tuple[int, pd.DataFrame]]:
        """Find tables containing specific header keywords.

        Args:
            file_path: Path to the PDF file.
            header_keywords: Keywords to search for in table headers.

        Returns:
            List of tuples (page_number, DataFrame) for matching tables.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        results = []
        keywords_lower = [kw.lower() for kw in header_keywords]

        with pdfplumber.open(file_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_tables = page.extract_tables(self.table_settings)

                for table_data in page_tables:
                    if not table_data or len(table_data) < 2:
                        continue

                    # Check headers
                    headers = table_data[0]
                    headers_text = " ".join(str(h).lower() for h in headers if h)

                    if any(kw in headers_text for kw in keywords_lower):
                        df = self._table_to_dataframe(table_data)
                        if df is not None and not df.empty:
                            results.append((page_idx + 1, df))

        return results
