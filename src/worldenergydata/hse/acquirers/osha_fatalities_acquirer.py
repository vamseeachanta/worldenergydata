# ABOUTME: OSHA fatality and severe injury data acquirer for oil & gas
# ABOUTME: Downloads severe injury reports and fatality investigation data from OSHA

"""
OSHA Fatality and Severe Injury Data Acquirer

Downloads OSHA severe injury and fatality data from public endpoints.
The severe injury reporting dataset contains all reports filed under
OSHA's severe injury reporting rule (29 CFR 1904.39).

Datasets:
    - Severe Injury Reports: All reported amputations, hospitalizations, fatalities
    - Fatality Inspections: Extracted from main inspection dataset (type 'A')

Usage:
    from worldenergydata.hse.acquirers.osha_fatalities_acquirer import (
        OSHAFatalitiesAcquirer,
    )

    acquirer = OSHAFatalitiesAcquirer()
    results = acquirer.download_all("data/modules/hse/raw/osha/fatalities")

    # CLI
    uv run python -m worldenergydata.hse.acquirers.osha_fatalities_acquirer \\
        --output-dir data/modules/hse/raw/osha/fatalities --force
"""

import argparse
from pathlib import Path
from typing import Dict, Optional

import httpx
import pandas as pd

from worldenergydata.common import get_logger

logger = get_logger(__name__)

# OSHA severe injury report endpoint
SEVERE_INJURY_URL = "https://www.osha.gov/severeinjury/xml/severeinjury.csv"

# Oil & gas NAICS codes for filtering fatality/severe injury data
OIL_GAS_NAICS_PREFIXES = (
    "211",  # Oil and gas extraction
    "213111",  # Drilling oil and gas wells
    "213112",  # Support activities for oil and gas operations
)

# Additional keyword patterns for oil & gas establishment matching
OIL_GAS_KEYWORDS = (
    "oil",
    "gas",
    "petroleum",
    "drilling",
    "wellhead",
    "pipeline",
    "refin",
    "fracking",
    "hydraulic fracturing",
    "upstream",
    "midstream",
    "downstream",
    "oilfield",
)

# HTTP settings
DOWNLOAD_TIMEOUT = 120


class OSHAFatalitiesAcquirer:
    """
    Acquirer for OSHA fatality and severe injury data.

    Downloads the OSHA Severe Injury Reports CSV and optionally extracts
    fatality inspection records from the main OSHA inspection dataset.

    Attributes:
        severe_injury_url: URL for the severe injury reports CSV.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        severe_injury_url: str = SEVERE_INJURY_URL,
        timeout: int = DOWNLOAD_TIMEOUT,
    ):
        """
        Initialize the fatalities acquirer.

        Args:
            severe_injury_url: URL for the OSHA severe injury CSV.
            timeout: HTTP request timeout in seconds.
        """
        self.severe_injury_url = severe_injury_url
        self.timeout = timeout

    def download_all(
        self,
        output_dir: str,
        force: bool = False,
    ) -> Dict[str, Path]:
        """
        Download all fatality/severe injury datasets.

        Args:
            output_dir: Directory to save downloaded files.
            force: If True, re-download even if files exist.

        Returns:
            Dictionary mapping dataset names to file paths.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        results: Dict[str, Path] = {}

        # Download severe injury reports
        severe_path = out_path / "osha_severe_injury.csv"
        if severe_path.exists() and not force:
            logger.info("Skipping severe_injury (exists, use --force to re-download)")
            results["severe_injury"] = severe_path
        else:
            logger.info(
                "Downloading severe injury reports from %s",
                self.severe_injury_url,
            )
            try:
                self._download_csv(self.severe_injury_url, severe_path)
                results["severe_injury"] = severe_path
                logger.info("Saved severe_injury -> %s", severe_path)
            except Exception as exc:
                logger.error("Failed to download severe injury data: %s", exc)

        return results

    def _download_csv(self, url: str, output_path: Path) -> Path:
        """
        Download a CSV file directly (no ZIP extraction needed).

        Args:
            url: URL to download from.
            output_path: Target path for the CSV file.

        Returns:
            Path to the downloaded file.

        Raises:
            httpx.HTTPStatusError: If the download fails.
        """
        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            response.raise_for_status()

            output_path.write_bytes(response.content)

            size_mb = len(response.content) / (1024 * 1024)
            logger.info(
                "Downloaded %.1f MB -> %s",
                size_mb,
                output_path,
            )

        return output_path

    def extract_fatality_inspections(
        self,
        inspection_csv: str,
        output_path: str,
    ) -> int:
        """
        Extract fatality/catastrophe inspections from the main inspection CSV.

        Filters for inspection_type = 'A' (Accident/fatality/catastrophe)
        and optionally for oil & gas NAICS codes.

        Args:
            inspection_csv: Path to the full OSHA inspection CSV.
            output_path: Path for the filtered fatality inspection CSV.

        Returns:
            Number of fatality inspection records extracted.
        """
        in_path = Path(inspection_csv)
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        total = 0
        header_written = False

        for chunk in pd.read_csv(
            in_path,
            dtype=str,
            chunksize=100_000,
            low_memory=False,
            encoding="latin-1",
        ):
            col_map = {c: c.lower() for c in chunk.columns}
            df = chunk.rename(columns=col_map)

            # Filter for fatality/catastrophe inspections
            insp_type_col = None
            for candidate in ["insp_type", "inspection_type"]:
                if candidate in df.columns:
                    insp_type_col = candidate
                    break

            if insp_type_col is None:
                continue

            mask = df[insp_type_col].str.upper().fillna("") == "A"
            matched = chunk[mask]

            if len(matched) > 0:
                matched.to_csv(
                    out_path,
                    mode="a" if header_written else "w",
                    header=not header_written,
                    index=False,
                )
                header_written = True
                total += len(matched)

        logger.info(
            "Extracted %d fatality inspections -> %s",
            total,
            out_path,
        )
        return total

    def filter_oil_and_gas(
        self,
        input_path: str,
        output_path: str,
    ) -> int:
        """
        Filter severe injury/fatality CSV for oil & gas records.

        Uses NAICS codes and keyword matching on establishment names
        to identify oil & gas industry records.

        Args:
            input_path: Path to the source CSV file.
            output_path: Path for the filtered output CSV.

        Returns:
            Number of oil & gas records found.
        """
        in_path = Path(input_path)
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        total = 0
        header_written = False

        for chunk in pd.read_csv(
            in_path,
            dtype=str,
            chunksize=50_000,
            low_memory=False,
            encoding="latin-1",
        ):
            col_map = {c: c.lower() for c in chunk.columns}
            df = chunk.rename(columns=col_map)

            mask = pd.Series(False, index=df.index)

            # Check NAICS codes
            naics_col = self._find_column(df, ["naics", "naics_code", "primary_naics"])
            if naics_col is not None:
                naics_vals = df[naics_col].fillna("")
                for prefix in OIL_GAS_NAICS_PREFIXES:
                    mask = mask | naics_vals.str.startswith(prefix)

            # Keyword matching on establishment/employer name
            name_col = self._find_column(
                df, ["employer", "establishment_name", "estab_name", "company"]
            )
            if name_col is not None:
                name_vals = df[name_col].fillna("").str.lower()
                for keyword in OIL_GAS_KEYWORDS:
                    mask = mask | name_vals.str.contains(keyword, case=False, na=False)

            matched = chunk[mask]
            if len(matched) > 0:
                matched.to_csv(
                    out_path,
                    mode="a" if header_written else "w",
                    header=not header_written,
                    index=False,
                )
                header_written = True
                total += len(matched)

        logger.info(
            "Filtered %d oil & gas records -> %s",
            total,
            out_path,
        )
        return total

    @staticmethod
    def _find_column(
        df: pd.DataFrame,
        candidates: list,
    ) -> Optional[str]:
        """Find first matching column name from candidates."""
        for col in candidates:
            if col in df.columns:
                return col
        return None


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Download OSHA fatality and severe injury data " "for oil & gas analysis"
        ),
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save downloaded files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force re-download even if files exist",
    )
    parser.add_argument(
        "--inspection-csv",
        default=None,
        help=(
            "Path to full OSHA inspection CSV to extract fatality records. "
            "If not provided, only the severe injury dataset is downloaded."
        ),
    )
    parser.add_argument(
        "--filter-naics",
        action="store_true",
        default=False,
        help="Filter downloaded data for oil & gas records",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DOWNLOAD_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DOWNLOAD_TIMEOUT})",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry point for OSHA fatality data acquisition."""
    parser = build_parser()
    args = parser.parse_args(argv)

    acquirer = OSHAFatalitiesAcquirer(timeout=args.timeout)

    # Step 1: Download severe injury data
    logger.info("Starting OSHA fatality/severe injury data download")
    results = acquirer.download_all(
        output_dir=args.output_dir,
        force=args.force,
    )

    for name, path in results.items():
        size_mb = path.stat().st_size / (1024 * 1024)
        logger.info("  %s: %.1f MB -> %s", name, size_mb, path)

    # Step 2: Extract fatality inspections from main dataset if provided
    if args.inspection_csv:
        fatality_path = Path(args.output_dir) / "osha_fatality_inspections.csv"
        count = acquirer.extract_fatality_inspections(
            inspection_csv=args.inspection_csv,
            output_path=str(fatality_path),
        )
        if count > 0:
            results["fatality_inspections"] = fatality_path
        logger.info("  fatality_inspections: %d records", count)

    # Step 3: Optionally filter for oil & gas
    if args.filter_naics:
        logger.info("Filtering for oil & gas records")
        filtered_dir = Path(args.output_dir) / "filtered"
        filtered_dir.mkdir(parents=True, exist_ok=True)

        for name, path in results.items():
            filtered_path = filtered_dir / f"{path.stem}_oil_gas.csv"
            count = acquirer.filter_oil_and_gas(
                input_path=str(path),
                output_path=str(filtered_path),
            )
            logger.info("  %s: %d oil & gas records", name, count)

    logger.info("OSHA fatality acquisition complete")


if __name__ == "__main__":
    main()
