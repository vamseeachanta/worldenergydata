"""Availability of offshore reference data withheld from public distribution."""

from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[3]
CURATED = ROOT / "data/modules/offshore_assets/curated"
WITHHELD_DATASETS = (
    "country_centroids.csv",
    "coverage_summary.csv",
    "drilling_rigs.csv",
    "fields.csv",
    "host_facilities.csv",
    "jackups.csv",
    "production_facilities.csv",
    "bsee_field_crosswalk.csv",
    "subseaiq_hosts.csv",
    "subseaiq_bsee_block_crosswalk.csv",
)
WITHHELD_REASON = "held privately pending redistribution-terms review"


class DatasetUnavailableError(RuntimeError):
    """A requested bundled dataset is withheld from public distribution."""


def load_withheld_dataset(name: str) -> NoReturn:
    """Explain why a withdrawn dataset cannot be loaded, including jackups."""
    if name not in WITHHELD_DATASETS:
        raise ValueError(f"Unknown withheld dataset: {name}")
    raise DatasetUnavailableError(
        f"The {name} data set is {WITHHELD_REASON}. "
        "No bundled data is available. Independently sourced inputs require "
        "their own provenance and redistribution clearance."
    )


def require_available_source(path: Path) -> Path:
    """Reject a bundled legacy path even if a stale copy has been restored.

    An explicit external input remains readable for private use or independently
    sourced collections. Its path does not establish redistribution permission.
    """
    path = Path(path)
    withheld = [(CURATED / name).resolve() for name in WITHHELD_DATASETS]
    withheld.extend(
        (ROOT / name).resolve()
        for name in (
            "reports/field-atlas/_roster.json",
            "reports/field-atlas/_atlas_feed.json",
            "reports/decommissioning/regional_liability.csv",
        )
    )
    if path.resolve() in withheld:
        raise DatasetUnavailableError(
            f"The {path.name} data set is {WITHHELD_REASON}. "
            "No bundled data is available; use independently sourced inputs."
        )
    return path
