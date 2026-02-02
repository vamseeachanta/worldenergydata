# ABOUTME: BSEE raw data acquirer for incident investigations and INCs
# ABOUTME: Downloads ZIP archives from data.bsee.gov, extracts tab-delimited text files

"""
BSEE Raw Data Acquirer

Downloads BSEE enforcement and safety datasets from data.bsee.gov,
extracts ZIP archives, and saves tab-delimited text files to disk.

Datasets:
    - Incident Investigations: Accident investigation records (~1,984 records)
    - INCs: Incidents of Non-Compliance (~51K operator-level records)

Usage:
    # As module
    from worldenergydata.modules.hse.acquirers.bsee_acquirer import BSEEAcquirer

    acquirer = BSEEAcquirer()
    results = acquirer.download_all("data/modules/hse/raw/bsee")

    # CLI
    uv run python -m worldenergydata.modules.hse.acquirers.bsee_acquirer \\
        --output-dir data/modules/hse/raw/bsee --force
"""

import argparse
import io
import zipfile
from pathlib import Path
from typing import Dict, Optional

import httpx

from worldenergydata.common import get_logger

logger = get_logger(__name__)

# BSEE public data download URLs
BSEE_DATASETS: Dict[str, str] = {
    "incident_investigations": (
        "https://www.data.bsee.gov/Other/Files/IncInvRawData.zip"
    ),
    "incs": ("https://www.data.bsee.gov/Company/Files/INCSRawData.zip"),
}

# Expected extraction subdirectories (mirror the ZIP internal structure)
BSEE_EXTRACT_DIRS: Dict[str, str] = {
    "incident_investigations": "IncInvRawData",
    "incs": "INCSRawData",
}

# HTTP download settings
DOWNLOAD_TIMEOUT = 300  # seconds


class BSEEAcquirer:
    """
    Acquirer for BSEE raw data from data.bsee.gov.

    Downloads ZIP archives containing tab-delimited text files, extracts
    them to named subdirectories, and reports file sizes.

    Attributes:
        datasets: Dictionary mapping dataset names to download URLs.
    """

    def __init__(
        self,
        datasets: Optional[Dict[str, str]] = None,
        timeout: int = DOWNLOAD_TIMEOUT,
    ):
        """
        Initialize the BSEE acquirer.

        Args:
            datasets: Override default dataset URLs. Keys are dataset names,
                values are ZIP download URLs.
            timeout: HTTP request timeout in seconds.
        """
        self.datasets = datasets or BSEE_DATASETS
        self.timeout = timeout

    def download_all(
        self,
        output_dir: str,
        force: bool = False,
    ) -> Dict[str, Path]:
        """
        Download all BSEE datasets.

        Downloads each ZIP file, extracts contents to subdirectories, and
        saves the ZIP archive alongside. Skips existing directories unless
        force=True.

        Args:
            output_dir: Directory to save extracted data files.
            force: If True, re-download even if files exist.

        Returns:
            Dictionary mapping dataset names to extraction directory paths.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        results: Dict[str, Path] = {}

        for name, url in self.datasets.items():
            extract_dir_name = BSEE_EXTRACT_DIRS.get(name, name)
            extract_dir = out_path / extract_dir_name
            zip_path = out_path / f"{extract_dir_name}.zip"

            if extract_dir.exists() and not force:
                file_count = len(list(extract_dir.iterdir()))
                logger.info(
                    "Skipping %s (%s exists with %d files, use --force to re-download)",
                    name,
                    extract_dir,
                    file_count,
                )
                results[name] = extract_dir
                continue

            logger.info("Downloading %s from %s", name, url)
            try:
                extract_dir = self._download_and_extract(
                    url, zip_path, extract_dir, name
                )
                results[name] = extract_dir
                self._log_extracted_files(name, extract_dir)
            except Exception as exc:
                logger.error("Failed to download %s: %s", name, exc)

        return results

    def _download_and_extract(
        self,
        url: str,
        zip_path: Path,
        extract_dir: Path,
        dataset_name: str,
    ) -> Path:
        """
        Download a ZIP file and extract all contents.

        Args:
            url: URL to download the ZIP archive from.
            zip_path: Target path to save the ZIP archive.
            extract_dir: Directory to extract contents into.
            dataset_name: Name of the dataset (for logging).

        Returns:
            Path to the extraction directory.

        Raises:
            httpx.HTTPStatusError: If the download fails.
            zipfile.BadZipFile: If the archive is corrupt.
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

            # Save ZIP archive to disk
            zip_path.write_bytes(response.content)
            logger.info("Saved ZIP archive: %s", zip_path)

            # Extract all contents
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                members = zf.namelist()
                logger.info(
                    "Extracting %d files from %s archive",
                    len(members),
                    dataset_name,
                )

                for member in members:
                    # Flatten: extract files directly into extract_dir
                    # ZIP may contain subdirectory paths like "IncInvRawData/file.txt"
                    filename = Path(member).name
                    if not filename:
                        # Skip directory entries
                        continue

                    target = extract_dir / filename
                    with zf.open(member) as src:
                        target.write_bytes(src.read())

        return extract_dir

    def _log_extracted_files(
        self,
        dataset_name: str,
        extract_dir: Path,
    ) -> None:
        """
        Log extracted file names and sizes.

        Args:
            dataset_name: Name of the dataset (for logging).
            extract_dir: Directory containing extracted files.
        """
        for file_path in sorted(extract_dir.iterdir()):
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                logger.info(
                    "  %s / %s: %.2f MB",
                    dataset_name,
                    file_path.name,
                    size_mb,
                )

    def verify_data(self, output_dir: str) -> Dict[str, Dict]:
        """
        Verify downloaded data integrity.

        Checks that expected files exist and reports row counts for
        tab-delimited text files.

        Args:
            output_dir: Directory containing downloaded data.

        Returns:
            Dictionary with verification results per dataset.
        """
        out_path = Path(output_dir)
        results: Dict[str, Dict] = {}

        for name in self.datasets:
            extract_dir_name = BSEE_EXTRACT_DIRS.get(name, name)
            extract_dir = out_path / extract_dir_name

            if not extract_dir.exists():
                results[name] = {"status": "missing", "files": []}
                continue

            files_info = []
            for file_path in sorted(extract_dir.iterdir()):
                if file_path.is_file() and file_path.suffix == ".txt":
                    # Count lines (rows) in tab-delimited file
                    with open(file_path, encoding="latin-1") as f:
                        line_count = sum(1 for _ in f)
                    files_info.append(
                        {
                            "name": file_path.name,
                            "size_bytes": file_path.stat().st_size,
                            "rows": line_count - 1,  # Subtract header
                        }
                    )

            results[name] = {
                "status": "ok" if files_info else "empty",
                "files": files_info,
            }

        return results


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Download BSEE incident and INC raw data from data.bsee.gov",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save downloaded data files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force re-download even if files exist",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=False,
        help="Verify downloaded data after acquisition",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DOWNLOAD_TIMEOUT,
        help=f"HTTP download timeout in seconds (default: {DOWNLOAD_TIMEOUT})",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry point for BSEE data acquisition."""
    parser = build_parser()
    args = parser.parse_args(argv)

    acquirer = BSEEAcquirer(timeout=args.timeout)

    # Step 1: Download all datasets
    logger.info("Starting BSEE raw data download")
    results = acquirer.download_all(
        output_dir=args.output_dir,
        force=args.force,
    )

    logger.info(
        "Download complete: %d/%d datasets acquired",
        len(results),
        len(BSEE_DATASETS),
    )

    # Step 2: Optionally verify
    if args.verify:
        logger.info("Verifying downloaded data integrity")
        verification = acquirer.verify_data(args.output_dir)
        for name, info in verification.items():
            logger.info("  %s: %s", name, info["status"])
            for f in info.get("files", []):
                logger.info(
                    "    %s: %d rows, %.2f MB",
                    f["name"],
                    f["rows"],
                    f["size_bytes"] / (1024 * 1024),
                )

    logger.info("BSEE acquisition pipeline complete")


if __name__ == "__main__":
    main()
