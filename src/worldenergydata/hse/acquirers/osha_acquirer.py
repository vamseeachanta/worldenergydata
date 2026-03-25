# ABOUTME: OSHA enforcement data acquirer for oil & gas industry
# ABOUTME: Downloads inspection, violation, and accident data from DOL enforcement catalog

"""
OSHA Enforcement Data Acquirer

Downloads OSHA enforcement datasets from the Department of Labor data catalog,
extracts CSVs from ZIP archives, and optionally filters for oil & gas NAICS codes.

Datasets:
    - Inspections: Workplace inspection records
    - Violations: Cited violations from inspections
    - Accidents: Workplace accident/fatality reports
    - Accident Injuries: Individual injury details from accidents

Usage:
    # As module
    from worldenergydata.hse.acquirers.osha_acquirer import OSHAAcquirer

    acquirer = OSHAAcquirer()
    results = acquirer.download_all("data/modules/hse/raw/osha")

    # CLI
    uv run python -m worldenergydata.hse.acquirers.osha_acquirer \\
        --output-dir data/modules/hse/raw/osha --force --filter-naics
"""

import argparse
import io
import zipfile
from pathlib import Path
from typing import Dict, Optional

import httpx
import pandas as pd

from worldenergydata.common import get_logger

logger = get_logger(__name__)

# OSHA enforcement data catalog URLs (DOL public data)
OSHA_DATASETS: Dict[str, str] = {
    "inspection": (
        "https://enforcedata.dol.gov/views/data_catalogs/zip/" "osha_inspection.csv.zip"
    ),
    "violation": (
        "https://enforcedata.dol.gov/views/data_catalogs/zip/" "osha_violation.csv.zip"
    ),
    "accident": (
        "https://enforcedata.dol.gov/views/data_catalogs/zip/" "osha_accident.csv.zip"
    ),
    "accident_injury": (
        "https://enforcedata.dol.gov/views/data_catalogs/zip/"
        "osha_accident_injury.csv.zip"
    ),
}

# Oil & gas NAICS codes for filtering
OIL_GAS_NAICS_PREFIXES = (
    "211",  # Oil and gas extraction
    "213111",  # Drilling oil and gas wells
    "213112",  # Support activities for oil and gas operations
)

# SIC codes as fallback for older records
OIL_GAS_SIC_PREFIXES = (
    "1311",  # Crude petroleum and natural gas
    "1381",  # Drilling oil and gas wells
    "1382",  # Oil and gas field services
    "1389",  # Services to oil and gas extraction
)

# HTTP download settings
DOWNLOAD_TIMEOUT = 300  # seconds
CHUNK_SIZE = 8192


class OSHAAcquirer:
    """
    Acquirer for OSHA enforcement data from DOL public data catalog.

    Downloads ZIP archives containing CSV datasets, extracts them,
    and optionally filters for oil & gas industry NAICS codes.

    Attributes:
        datasets: Dictionary mapping dataset names to download URLs.
    """

    def __init__(
        self,
        datasets: Optional[Dict[str, str]] = None,
        timeout: int = DOWNLOAD_TIMEOUT,
    ):
        """
        Initialize the OSHA acquirer.

        Args:
            datasets: Override default dataset URLs. Keys are dataset names,
                values are ZIP download URLs.
            timeout: HTTP request timeout in seconds.
        """
        self.datasets = datasets or OSHA_DATASETS
        self.timeout = timeout

    def download_all(
        self,
        output_dir: str,
        force: bool = False,
    ) -> Dict[str, Path]:
        """
        Download all OSHA enforcement datasets.

        Downloads each ZIP file, extracts the CSV contents, and saves
        to the output directory. Skips existing files unless force=True.

        Args:
            output_dir: Directory to save extracted CSV files.
            force: If True, re-download even if files exist.

        Returns:
            Dictionary mapping dataset names to extracted CSV file paths.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        results: Dict[str, Path] = {}

        for name, url in self.datasets.items():
            csv_path = out_path / f"osha_{name}.csv"

            if csv_path.exists() and not force:
                logger.info(
                    "Skipping %s (exists, use --force to re-download)",
                    name,
                )
                results[name] = csv_path
                continue

            logger.info("Downloading %s from %s", name, url)
            try:
                csv_path = self._download_and_extract(url, csv_path, name)
                results[name] = csv_path
                logger.info("Saved %s -> %s", name, csv_path)
            except Exception as exc:
                logger.error("Failed to download %s: %s", name, exc)

        return results

    def _download_and_extract(
        self,
        url: str,
        csv_path: Path,
        dataset_name: str,
    ) -> Path:
        """
        Download a ZIP file and extract the CSV contents.

        Args:
            url: URL to download the ZIP archive from.
            csv_path: Target path for the extracted CSV.
            dataset_name: Name of the dataset (for logging).

        Returns:
            Path to the extracted CSV file.

        Raises:
            httpx.HTTPStatusError: If the download fails.
            zipfile.BadZipFile: If the archive is corrupt.
            ValueError: If no CSV found in the archive.
        """
        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            response.raise_for_status()

            content_length = len(response.content)
            logger.info(
                "Downloaded %s: %.1f MB",
                dataset_name,
                content_length / (1024 * 1024),
            )

            # Extract CSV from ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                csv_files = [f for f in zf.namelist() if f.lower().endswith(".csv")]

                if not csv_files:
                    raise ValueError(f"No CSV files found in {dataset_name} archive")

                # Use the first CSV file found
                source_name = csv_files[0]
                logger.info(
                    "Extracting %s from archive",
                    source_name,
                )

                with zf.open(source_name) as src:
                    csv_path.write_bytes(src.read())

        return csv_path

    def filter_oil_and_gas(
        self,
        input_path: str,
        output_path: str,
        chunk_size: int = 100_000,
    ) -> int:
        """
        Filter a CSV file for oil & gas industry records.

        Looks for NAICS codes starting with oil & gas prefixes (211, 213111,
        213112) and SIC codes (1311, 1381, 1382, 1389) as fallback.

        Handles column name variations: naics_code, NAICS_CODE, sic_code,
        SIC_CODE.

        Args:
            input_path: Path to the source CSV file.
            output_path: Path for the filtered output CSV.
            chunk_size: Number of rows to process per chunk (memory management).

        Returns:
            Number of records matching oil & gas industry codes.
        """
        in_path = Path(input_path)
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        total_matches = 0
        header_written = False

        for chunk in pd.read_csv(
            in_path,
            dtype=str,
            chunksize=chunk_size,
            low_memory=False,
            encoding="latin-1",
        ):
            # Normalize column names to lowercase for matching
            col_map = {c: c.lower() for c in chunk.columns}
            chunk_lower = chunk.rename(columns=col_map)

            mask = pd.Series(False, index=chunk_lower.index)

            # Check NAICS code columns
            naics_col = self._find_column(chunk_lower, ["naics_code", "naics_cd"])
            if naics_col is not None:
                naics_vals = chunk_lower[naics_col].fillna("")
                for prefix in OIL_GAS_NAICS_PREFIXES:
                    mask = mask | naics_vals.str.startswith(prefix)

            # Check SIC code columns as fallback
            sic_col = self._find_column(chunk_lower, ["sic_code", "sic_cd", "sic"])
            if sic_col is not None:
                sic_vals = chunk_lower[sic_col].fillna("")
                for prefix in OIL_GAS_SIC_PREFIXES:
                    mask = mask | sic_vals.str.startswith(prefix)

            matched = chunk[mask]
            if len(matched) > 0:
                matched.to_csv(
                    out_path,
                    mode="a" if header_written else "w",
                    header=not header_written,
                    index=False,
                )
                header_written = True
                total_matches += len(matched)

        logger.info(
            "Filtered %s -> %s: %d oil & gas records",
            in_path.name,
            out_path.name,
            total_matches,
        )
        return total_matches

    @staticmethod
    def _find_column(
        df: pd.DataFrame,
        candidates: list,
    ) -> Optional[str]:
        """
        Find first matching column name from candidates.

        Args:
            df: DataFrame to search columns in.
            candidates: List of potential column names (lowercase).

        Returns:
            First matching column name, or None if not found.
        """
        for col in candidates:
            if col in df.columns:
                return col
        return None


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Download OSHA enforcement data for oil & gas analysis",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save downloaded CSV files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force re-download even if files exist",
    )
    parser.add_argument(
        "--filter-naics",
        action="store_true",
        default=False,
        help="Filter downloaded data for oil & gas NAICS codes",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DOWNLOAD_TIMEOUT,
        help=f"HTTP download timeout in seconds (default: {DOWNLOAD_TIMEOUT})",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry point for OSHA data acquisition."""
    parser = build_parser()
    args = parser.parse_args(argv)

    acquirer = OSHAAcquirer(timeout=args.timeout)

    # Step 1: Download all datasets
    logger.info("Starting OSHA enforcement data download")
    results = acquirer.download_all(
        output_dir=args.output_dir,
        force=args.force,
    )

    logger.info(
        "Download complete: %d/%d datasets acquired",
        len(results),
        len(OSHA_DATASETS),
    )

    for name, path in results.items():
        size_mb = path.stat().st_size / (1024 * 1024)
        logger.info("  %s: %.1f MB -> %s", name, size_mb, path)

    # Step 2: Optionally filter for oil & gas
    if args.filter_naics:
        logger.info("Filtering datasets for oil & gas NAICS codes")
        filtered_dir = Path(args.output_dir) / "filtered"
        filtered_dir.mkdir(parents=True, exist_ok=True)

        for name, path in results.items():
            filtered_path = filtered_dir / f"osha_{name}_oil_gas.csv"
            count = acquirer.filter_oil_and_gas(
                input_path=str(path),
                output_path=str(filtered_path),
            )
            logger.info(
                "  %s: %d oil & gas records -> %s",
                name,
                count,
                filtered_path,
            )

    logger.info("OSHA acquisition pipeline complete")


if __name__ == "__main__":
    main()
