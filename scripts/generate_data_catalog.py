"""Generate machine-readable data catalog by scanning data directories.

Walks ``data/modules/`` and produces a YAML or JSON catalog describing
every CSV, parquet, Excel, and binary file it finds.  Metadata such as
column names, row counts, file sizes, and inferred business domains are
extracted without loading entire files into memory.

Usage:
    uv run python scripts/generate_data_catalog.py
    uv run python scripts/generate_data_catalog.py --module bsee
    uv run python scripts/generate_data_catalog.py --format json
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldenergydata.common.catalog import (
    DataCatalog,
    DatasetEntry,
    ModuleCatalogEntry,
)

# ---------------------------------------------------------------------------
# Domain inference mapping from directory names
# ---------------------------------------------------------------------------

_DOMAIN_MAP: dict[str, str] = {
    "wells": "drilling",
    "well_data": "drilling",
    "drilling": "drilling",
    "production": "production",
    "completions": "completions",
    "geology": "geology",
    "operations": "operations",
    "infrastructure": "infrastructure",
    "safety": "safety",
    "incidents": "safety",
    "environmental": "environmental",
    "wind": "renewable",
    "pricing": "economics",
    "oil_price": "economics",
}

# ---------------------------------------------------------------------------
# Module descriptions
# ---------------------------------------------------------------------------

_MODULE_DESCRIPTIONS: dict[str, str] = {
    "bsee": "US Gulf of Mexico offshore data from BSEE",
    "sodir_zip_data": "Norwegian Continental Shelf data from Sodir",
    "marine_safety": "Maritime casualty and safety incident data",
    "hse": "Health, Safety and Environment data",
    "vessel_hull_models": "Marine vessel hull geometry and specifications",
    "lngc": "LNG carrier fleet data",
    "pipeline_safety": "Pipeline safety incident data",
    "lng_terminals": "LNG terminal infrastructure data",
    "fdas": "Floating production data advisory system",
    "wind": "Wind energy resource and turbine data",
    "oil_price": "Historical oil price data",
    "metocean": "Meteorological and oceanographic data",
}


class DataCatalogGenerator:
    """Scan data directories and produce a structured catalog."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.data_root = project_root / "data" / "modules"

    # ------------------------------------------------------------------
    # File-level scanners
    # ------------------------------------------------------------------

    def scan_csv_file(self, path: Path) -> DatasetEntry:
        """Scan a CSV file for metadata without loading the entire file."""
        columns = None
        row_count = None
        try:
            with open(path, "r", newline="", errors="replace") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    columns = [c.strip() for c in header]
                row_count = sum(1 for _ in reader)
        except Exception:
            pass

        return DatasetEntry(
            name=path.stem,
            path=str(path.relative_to(self.project_root)),
            format="csv",
            domain=self.infer_domain(path),
            size_bytes=path.stat().st_size,
            row_count=row_count,
            columns=columns,
            last_modified=datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
        )

    def scan_binary_file(self, path: Path) -> DatasetEntry:
        """Scan a binary/pickle file for metadata."""
        return DatasetEntry(
            name=path.stem,
            path=str(path.relative_to(self.project_root)),
            format="pickle",
            domain=self.infer_domain(path),
            size_bytes=path.stat().st_size,
            last_modified=datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
        )

    def scan_excel_file(self, path: Path) -> DatasetEntry:
        """Scan an Excel file for basic metadata (size only, no parsing)."""
        return DatasetEntry(
            name=path.stem,
            path=str(path.relative_to(self.project_root)),
            format="xlsx" if path.suffix == ".xlsx" else "xls",
            domain=self.infer_domain(path),
            size_bytes=path.stat().st_size,
            last_modified=datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
        )

    # ------------------------------------------------------------------
    # Domain inference
    # ------------------------------------------------------------------

    def infer_domain(self, path: Path) -> str:
        """Infer business domain from directory structure."""
        parts = path.parts
        for part in reversed(parts):
            part_lower = part.lower()
            if part_lower in _DOMAIN_MAP:
                return _DOMAIN_MAP[part_lower]
        return "general"

    # ------------------------------------------------------------------
    # Module and catalog scanning
    # ------------------------------------------------------------------

    def scan_module(self, module_path: Path) -> ModuleCatalogEntry:
        """Scan a single data module directory."""
        module_name = module_path.name
        datasets: list[DatasetEntry] = []
        binary_stores: list[DatasetEntry] = []
        domains_seen: set[str] = set()
        documentation: dict[str, str] = {}

        # Check for README and DATA_DICTIONARY
        for doc_name in ("README.md", "DATA_DICTIONARY.md"):
            doc_path = module_path / doc_name
            if doc_path.exists():
                documentation[doc_name.lower().replace(".md", "")] = str(
                    doc_path.relative_to(self.project_root)
                )

        # Walk directory for data files
        for file_path in sorted(module_path.rglob("*")):
            if not file_path.is_file():
                continue
            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                entry = self.scan_csv_file(file_path)
                datasets.append(entry)
                domains_seen.add(entry.domain)
            elif suffix == ".bin":
                entry = self.scan_binary_file(file_path)
                binary_stores.append(entry)
                domains_seen.add(entry.domain)
            elif suffix in (".xlsx", ".xls"):
                entry = self.scan_excel_file(file_path)
                datasets.append(entry)
                domains_seen.add(entry.domain)
            elif suffix == ".parquet":
                entry = DatasetEntry(
                    name=file_path.stem,
                    path=str(file_path.relative_to(self.project_root)),
                    format="parquet",
                    domain=self.infer_domain(file_path),
                    size_bytes=file_path.stat().st_size,
                    last_modified=datetime.fromtimestamp(
                        file_path.stat().st_mtime, tz=timezone.utc
                    ).strftime("%Y-%m-%d"),
                )
                datasets.append(entry)
                domains_seen.add(entry.domain)

        return ModuleCatalogEntry(
            name=module_name,
            description=_MODULE_DESCRIPTIONS.get(
                module_name, f"{module_name} data module"
            ),
            path=str(module_path.relative_to(self.project_root)),
            domains=sorted(domains_seen),
            datasets=datasets,
            binary_stores=binary_stores,
            documentation=documentation,
        )

    def scan_all_modules(self) -> DataCatalog:
        """Scan all modules under data/modules/."""
        catalog = DataCatalog()
        if not self.data_root.exists():
            return catalog

        for module_path in sorted(self.data_root.iterdir()):
            if module_path.is_dir() and not module_path.name.startswith("."):
                entry = self.scan_module(module_path)
                if entry.dataset_count > 0:
                    catalog.modules[entry.name] = entry

        return catalog

    # ------------------------------------------------------------------
    # Generate and write
    # ------------------------------------------------------------------

    def generate(
        self,
        module_name: str | None = None,
        output_format: str = "yaml",
    ) -> Path:
        """Generate catalog and write to file.

        Args:
            module_name: If provided, scan only this module.
            output_format: ``"yaml"`` (default) or ``"json"``.

        Returns:
            Path to the generated catalog file.

        Raises:
            FileNotFoundError: If ``module_name`` does not exist on disk.
        """
        if module_name:
            module_path = self.data_root / module_name
            if not module_path.exists():
                raise FileNotFoundError(f"Module not found: {module_path}")
            catalog = DataCatalog()
            entry = self.scan_module(module_path)
            catalog.modules[entry.name] = entry
        else:
            catalog = self.scan_all_modules()

        output_dir = self.project_root / "data" / "catalog"
        if output_format == "json":
            output_path = output_dir / "data-catalog.json"
            catalog.to_json(output_path)
        else:
            output_path = output_dir / "data-catalog.yml"
            catalog.to_yaml(output_path)

        return output_path


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate data catalog")
    parser.add_argument("--module", help="Scan specific module only")
    parser.add_argument(
        "--format", choices=["yaml", "json"], default="yaml"
    )
    parser.add_argument(
        "--project-root", default=None, help="Project root path"
    )
    args = parser.parse_args()

    root = (
        Path(args.project_root)
        if args.project_root
        else Path(__file__).resolve().parent.parent
    )
    generator = DataCatalogGenerator(root)
    output_path = generator.generate(
        module_name=args.module, output_format=args.format
    )
    print(f"Catalog written to: {output_path}")


if __name__ == "__main__":
    main()
