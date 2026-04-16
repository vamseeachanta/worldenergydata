"""
Machine-readable data catalog models for WorldEnergyData.

Provides dataclasses that describe datasets, modules, and the top-level
catalog. Supports serialization to YAML and JSON for downstream tooling,
dashboards, and CI/CD pipelines.

Classes:
    DatasetEntry: A single dataset (CSV, parquet, binary, etc.)
    ModuleCatalogEntry: A data module containing multiple datasets
    DataCatalog: Top-level catalog aggregating all modules

Example usage:
    from worldenergydata.common.catalog import (
        DataCatalog,
        DatasetEntry,
        ModuleCatalogEntry,
    )

    entry = DatasetEntry(
        name="production",
        path="data/production.csv",
        format="csv",
        domain="production",
        size_bytes=1024,
    )
    module = ModuleCatalogEntry(
        name="bsee",
        description="BSEE data module",
        path="src/worldenergydata/bsee",
        datasets=[entry],
    )
    catalog = DataCatalog()
    catalog.modules["bsee"] = module
    catalog.to_yaml(Path("catalog.yaml"))
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ColumnSchema:
    """Schema for a single column in a dataset.

    Attributes:
        name: Column name as it appears in the data file.
        type: Inferred data type (string, integer, float, datetime, boolean).
        description: Human-readable description (blank for auto-generated).
        unit: Physical or business unit (e.g. "feet", "barrels", "psi").
    """

    name: str
    type: str = "string"
    description: str = ""
    unit: str = ""


@dataclass
class DatasetEntry:
    """A single dataset (CSV, binary, parquet, etc.) in the catalog.

    Attributes:
        name: Human-readable dataset identifier.
        path: Relative path from repository root to the data file.
        format: File format (csv, parquet, pickle, json, zip, xlsx).
        domain: Business domain (drilling, production, safety, etc.).
        size_bytes: File size in bytes.
        row_count: Number of rows, if applicable.
        columns: Column names, if applicable.
        column_schemas: Typed column schemas with name, type, description,
            and unit for each column.
        update_frequency: How often the data is refreshed
            (daily, weekly, monthly, quarterly, annual, static).
        source_url: Upstream URL the data was fetched from.
        last_modified: ISO-8601 timestamp of last file modification.
        description: Free-text description of the dataset.
        last_refreshed: ISO-8601 timestamp of when data was last
            fetched from its upstream source (distinct from file mtime).
        is_lfs_stub: True if the file is a Git LFS pointer, not real data.
        data_status: Summary status — one of real, lfs_stub, empty,
            stale, or unknown.
    """

    name: str
    path: str
    format: str
    domain: str
    size_bytes: int
    row_count: Optional[int] = None
    columns: Optional[list[str]] = None
    column_schemas: Optional[list[ColumnSchema]] = None
    update_frequency: Optional[str] = None
    source_url: Optional[str] = None
    last_modified: Optional[str] = None
    description: Optional[str] = None
    last_refreshed: Optional[str] = None
    is_lfs_stub: bool = False
    data_status: str = "unknown"


@dataclass
class ModuleCatalogEntry:
    """A data module containing multiple datasets.

    Attributes:
        name: Module identifier (e.g. "bsee", "production").
        description: Human-readable description of the module.
        path: Relative path to the module source directory.
        domains: Business domains covered by this module.
        datasets: Regular data files (CSV, parquet, etc.).
        binary_stores: Large or binary data files (zip, pickle, etc.).
        documentation: Mapping of doc type to file path.
    """

    name: str
    description: str
    path: str
    domains: list[str] = field(default_factory=list)
    datasets: list[DatasetEntry] = field(default_factory=list)
    binary_stores: list[DatasetEntry] = field(default_factory=list)
    documentation: dict[str, str] = field(default_factory=dict)

    @property
    def total_size_bytes(self) -> int:
        """Sum of all dataset and binary store sizes."""
        return sum(d.size_bytes for d in self.datasets) + sum(
            b.size_bytes for b in self.binary_stores
        )

    @property
    def dataset_count(self) -> int:
        """Total number of datasets including binary stores."""
        return len(self.datasets) + len(self.binary_stores)


@dataclass
class DataCatalog:
    """Top-level data catalog for the entire repository.

    Attributes:
        version: Catalog schema version (semver).
        generated_at: ISO-8601 timestamp of catalog generation.
        modules: Mapping of module name to its catalog entry.
    """

    version: str = "1.1.0"
    generated_at: str = ""
    modules: dict[str, ModuleCatalogEntry] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def total_modules(self) -> int:
        """Number of registered modules."""
        return len(self.modules)

    @property
    def total_datasets(self) -> int:
        """Total datasets across all modules."""
        return sum(m.dataset_count for m in self.modules.values())

    @property
    def total_size_bytes(self) -> int:
        """Total size in bytes across all modules."""
        return sum(m.total_size_bytes for m in self.modules.values())

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert the catalog to a plain dictionary.

        Returns:
            Nested dictionary with summary statistics and all module data.
        """
        result: dict = {
            "version": self.version,
            "generated_at": self.generated_at,
            "total_modules": self.total_modules,
            "total_datasets": self.total_datasets,
            "total_size_bytes": self.total_size_bytes,
            "modules": {},
        }
        for name, module in self.modules.items():
            result["modules"][name] = asdict(module)
        return result

    def to_yaml(self, path: Path) -> None:
        """Serialize the catalog to a YAML file.

        Creates parent directories if they do not exist.

        Args:
            path: Destination file path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(
                self.to_dict(), f, default_flow_style=False, sort_keys=False
            )

    def to_json(self, path: Path) -> None:
        """Serialize the catalog to a JSON file.

        Creates parent directories if they do not exist.

        Args:
            path: Destination file path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# ---------------------------------------------------------------------------
# Auto-regeneration helper
# ---------------------------------------------------------------------------


def refresh_catalog(project_root: Path | None = None) -> bool:
    """Regenerate the data catalog after a data mutation.

    Call this from data loaders/importers after successfully fetching or
    modifying datasets.  Runs ``scripts/generate_data_catalog.py`` as a
    subprocess so it can be used from any context without circular imports.

    Args:
        project_root: Path to the worldenergydata project root.  If *None*,
            attempts to discover it from the ``catalog.py`` file location.

    Returns:
        ``True`` if the catalog was regenerated successfully, ``False`` on
        error (logged but not raised).
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent.parent
    script = project_root / "scripts" / "generate_data_catalog.py"
    if not script.exists():
        logger.warning("Catalog generator not found at %s", script)
        return False
    try:
        subprocess.run(
            ["python3", str(script), "--project-root", str(project_root)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        logger.info("Data catalog regenerated successfully")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.warning("Catalog regeneration failed: %s", exc)
        return False
