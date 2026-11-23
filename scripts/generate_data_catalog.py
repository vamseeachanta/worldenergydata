"""Generate machine-readable data catalog by scanning data directories.

Walks ``data/modules/`` and produces a YAML or JSON catalog describing
every CSV, parquet, Excel, binary, and zip file it finds.  Metadata such
as column names, row counts, file sizes, and inferred business domains
are extracted without loading entire files into memory.

Supports external data roots (e.g. ``/mnt/ace/worldenergydata/data/``)
via the ``--external-data-root`` flag or the ``WED_DATA_ROOT`` env var.
When an external root is provided, its ``modules/`` subtree is merged
with the in-repo ``data/modules/`` so that large binary and raw data
hosted outside the repo appear in the catalog.

Usage:
    uv run python scripts/generate_data_catalog.py
    uv run python scripts/generate_data_catalog.py --module bsee
    uv run python scripts/generate_data_catalog.py --format json
    uv run python scripts/generate_data_catalog.py --external-data-root /mnt/ace/worldenergydata/data
    WED_DATA_ROOT=/mnt/ace/worldenergydata/data uv run python scripts/generate_data_catalog.py
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from worldenergydata.common.catalog import (
    ColumnSchema,
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


_LFS_SIGNATURE = b"version https://git-lfs"

_FREQUENCY_DAYS: dict[str, int] = {
    "daily": 2,
    "weekly": 10,
    "monthly": 45,
    "quarterly": 100,
    "annual": 400,
    "static": 99999,
}

# Skip directories during recursive scan
_SKIP_DIRS = {
    ".local",
    ".claude-flow",
    "__pycache__",
    "checkpoints",
    "cache",
    ".temp_downloads",
}


def load_source_registry(project_root: Path) -> dict[str, Any]:
    """Load source-registry.yml and return as nested dict."""
    registry_path = project_root / "data" / "catalog" / "source-registry.yml"
    if not registry_path.exists():
        return {}
    with open(registry_path) as f:
        return yaml.safe_load(f) or {}


def _load_osha_data_dictionary(dict_path: Path) -> dict[str, dict[str, dict[str, str]]]:
    """Load the OSHA data dictionary CSV and return a nested mapping.

    Returns:
        ``{table_name: {column_name: {"definition": ..., "display_name": ..., "datatype": ...}}}``
    """
    result: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    if not dict_path.exists():
        return result
    try:
        with open(dict_path, "r", newline="", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                table = row.get("table_name", "").strip().strip('"')
                col = row.get("column_name", "").strip().strip('"')
                if table and col:
                    result[table][col] = {
                        "definition": row.get("definition", "").strip().strip('"'),
                        "display_name": row.get("display_name", "").strip().strip('"'),
                        "datatype": row.get("column_datatype", "").strip().strip('"'),
                    }
    except Exception:
        pass
    return result


def _humanize_bytes(n: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


class DataCatalogGenerator:
    """Scan data directories and produce a structured catalog.

    Args:
        project_root: Path to the worldenergydata project root.
        external_data_root: Optional path to an external data directory
            (e.g. ``/mnt/ace/worldenergydata/data/``).  When provided,
            its ``modules/`` subtree is merged into the scan.
        follow_symlinks: Whether to follow symlinks during directory
            traversal (default ``True``).
    """

    def __init__(
        self,
        project_root: Path,
        external_data_root: Path | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        self.project_root = project_root
        self.data_root = project_root / "data" / "modules"
        self.external_data_root = external_data_root
        self.follow_symlinks = follow_symlinks
        self._osha_dict: dict[str, dict[str, dict[str, str]]] | None = None

    # ------------------------------------------------------------------
    # File-level scanners
    # ------------------------------------------------------------------

    def _relative_path(self, path: Path) -> str:
        """Return path relative to project root, or absolute if outside."""
        try:
            if path.is_relative_to(self.project_root):
                return str(path.relative_to(self.project_root))
        except (ValueError, TypeError):
            pass
        return str(path)

    def scan_csv_file(self, path: Path) -> DatasetEntry:
        """Scan a CSV file for metadata without loading the entire file.

        For very large CSV files (>100 MB), only counts a sample of rows
        and extrapolates to avoid long scan times.
        """
        columns = None
        row_count = None
        size = path.stat().st_size
        try:
            with open(path, "r", newline="", errors="replace") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    columns = [c.strip() for c in header]
                if size > 100_000_000:
                    # For very large files, estimate row count from sample
                    sample_rows = 0
                    sample_bytes = 0
                    for i, row in enumerate(reader):
                        sample_bytes += sum(len(c) for c in row) + len(row)
                        sample_rows += 1
                        if i >= 999:
                            break
                    if sample_rows > 0 and sample_bytes > 0:
                        row_count = int(sample_rows * (size / sample_bytes))
                else:
                    row_count = sum(1 for _ in reader)
        except Exception:
            pass

        return DatasetEntry(
            name=path.stem,
            path=self._relative_path(path),
            format="csv",
            domain=self.infer_domain(path),
            size_bytes=size,
            row_count=row_count,
            columns=columns,
            last_modified=datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
        )

    def scan_binary_file(self, path: Path) -> DatasetEntry:
        """Scan a binary/pickle file for metadata, detecting LFS stubs."""
        size = path.stat().st_size
        is_lfs = False
        if size == 0:
            data_status = "empty"
        else:
            try:
                with open(path, "rb") as f:
                    header = f.read(40)
                is_lfs = header.startswith(_LFS_SIGNATURE)
            except Exception:
                pass
            data_status = "lfs_stub" if is_lfs else "real"

        return DatasetEntry(
            name=path.stem,
            path=self._relative_path(path),
            format="pickle",
            domain=self.infer_domain(path),
            size_bytes=size,
            last_modified=datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
            is_lfs_stub=is_lfs,
            data_status=data_status,
        )

    def scan_excel_file(self, path: Path) -> DatasetEntry:
        """Scan an Excel file for basic metadata (size only, no parsing)."""
        return DatasetEntry(
            name=path.stem,
            path=self._relative_path(path),
            format="xlsx" if path.suffix == ".xlsx" else "xls",
            domain=self.infer_domain(path),
            size_bytes=path.stat().st_size,
            last_modified=datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
        )

    def scan_zip_file(self, path: Path) -> DatasetEntry:
        """Scan a zip archive for metadata: size, contained file listing."""
        contents: list[str] = []
        try:
            with zipfile.ZipFile(path, "r") as zf:
                contents = zf.namelist()
        except Exception:
            pass

        desc = f"ZIP archive with {len(contents)} file(s)"
        if contents:
            desc += f": {', '.join(contents[:5])}"
            if len(contents) > 5:
                desc += f" ... (+{len(contents) - 5} more)"

        return DatasetEntry(
            name=path.stem,
            path=(
                str(path.relative_to(self.project_root))
                if path.is_relative_to(self.project_root)
                else str(path)
            ),
            format="zip",
            domain=self.infer_domain(path),
            size_bytes=path.stat().st_size,
            description=desc,
            last_modified=datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
            data_status="real",
        )

    def scan_binary_directory(self, dir_path: Path) -> DatasetEntry:
        """Catalog a directory of binary files by extension, count, and size.

        Instead of reading individual binary files as CSVs, this produces
        a single summary entry for the directory.
        """
        ext_counts: dict[str, int] = defaultdict(int)
        ext_sizes: dict[str, int] = defaultdict(int)
        total_files = 0
        total_size = 0

        for fp in dir_path.rglob("*"):
            if not fp.is_file():
                continue
            parts = fp.relative_to(dir_path).parts
            if any(p in _SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
                continue
            ext = fp.suffix.lower() or "(no ext)"
            ext_counts[ext] += 1
            ext_sizes[ext] += fp.stat().st_size
            total_files += 1
            total_size += fp.stat().st_size

        ext_summary = ", ".join(
            f"{ext}: {count} files ({_humanize_bytes(ext_sizes[ext])})"
            for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1])
        )
        desc = (
            f"Binary data directory: {total_files} files, "
            f"{_humanize_bytes(total_size)} total. "
            f"Breakdown: {ext_summary}"
        )

        return DatasetEntry(
            name=dir_path.name,
            path=(
                str(dir_path.relative_to(self.project_root))
                if dir_path.is_relative_to(self.project_root)
                else str(dir_path)
            ),
            format="binary_directory",
            domain=self.infer_domain(dir_path),
            size_bytes=total_size,
            row_count=total_files,
            description=desc,
            last_modified=datetime.fromtimestamp(
                dir_path.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
            data_status="real",
        )

    def _get_osha_dict(self) -> dict[str, dict[str, dict[str, str]]]:
        """Lazy-load the OSHA data dictionary."""
        if self._osha_dict is None:
            candidates = [
                self.data_root / "hse" / "raw" / "osha" / "osha_data_dictionary.csv",
            ]
            if self.external_data_root:
                candidates.insert(
                    0,
                    self.external_data_root
                    / "modules"
                    / "hse"
                    / "raw"
                    / "osha"
                    / "osha_data_dictionary.csv",
                )
            for cand in candidates:
                if cand.exists():
                    self._osha_dict = _load_osha_data_dictionary(cand)
                    break
            if self._osha_dict is None:
                self._osha_dict = {}
        return self._osha_dict

    def _enrich_osha_columns(self, entry: DatasetEntry, file_path: Path) -> None:
        """Add column descriptions from the OSHA data dictionary."""
        osha_dict = self._get_osha_dict()
        if not osha_dict or not entry.columns:
            return

        # Derive table name from filename: osha_accident.csv -> osha_accident
        table_name = file_path.stem
        # Handle numbered splits: osha_violation3.csv -> osha_violation
        import re

        base_table = re.sub(r"\d+$", "", table_name)

        col_info = osha_dict.get(table_name) or osha_dict.get(base_table) or {}
        if not col_info:
            return

        schemas: list[ColumnSchema] = []
        for col_name in entry.columns:
            info = col_info.get(col_name, {})
            schemas.append(
                ColumnSchema(
                    name=col_name,
                    type=info.get("datatype", "string"),
                    description=info.get("definition", ""),
                    unit="",
                )
            )
        entry.column_schemas = schemas

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

    def _scan_directory_tree(
        self,
        module_path: Path,
        datasets: list[DatasetEntry],
        binary_stores: list[DatasetEntry],
        domains_seen: set[str],
        is_osha_dir: bool = False,
    ) -> None:
        """Scan a directory tree for data files, populating lists in place.

        For ``bin/`` directories containing many binary files, produces a
        single summary entry per subdirectory instead of per-file entries.
        For ``zip/`` directories, catalogs each zip archive.
        For CSV files in OSHA directories, enriches with data dictionary.
        """
        # Identify special subdirectories for bulk handling
        bin_dir = module_path / "bin"
        zip_dir = module_path / "zip"

        # Handle bin/ directory as bulk binary stores
        if bin_dir.is_dir():
            for sub in sorted(bin_dir.iterdir()):
                if sub.is_dir() and not sub.name.startswith("."):
                    entry = self.scan_binary_directory(sub)
                    binary_stores.append(entry)
                    domains_seen.add(entry.domain)
            # Also catalog any top-level files in bin/
            for fp in sorted(bin_dir.iterdir()):
                if fp.is_file() and not fp.name.startswith("."):
                    if fp.suffix.lower() == ".bin":
                        entry = self.scan_binary_file(fp)
                        binary_stores.append(entry)
                        domains_seen.add(entry.domain)

        # Handle zip/ directory
        if zip_dir.is_dir():
            for fp in sorted(zip_dir.rglob("*")):
                if fp.is_file() and fp.suffix.lower() == ".zip":
                    entry = self.scan_zip_file(fp)
                    binary_stores.append(entry)
                    domains_seen.add(entry.domain)

        # Walk remaining files (skip bin/ and zip/ already handled)
        for file_path in sorted(module_path.rglob("*")):
            if not file_path.is_file():
                continue
            # Skip files already handled in bin/ and zip/ directories
            try:
                rel = file_path.relative_to(module_path)
            except ValueError:
                continue
            parts = rel.parts
            if parts and parts[0] in ("bin", "zip"):
                continue
            # Skip hidden and cache directories
            if any(p in _SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
                continue

            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                entry = self.scan_csv_file(file_path)
                # Enrich OSHA CSVs with data dictionary
                if is_osha_dir or "osha" in file_path.name.lower():
                    self._enrich_osha_columns(entry, file_path)
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
                    path=(
                        str(file_path.relative_to(self.project_root))
                        if file_path.is_relative_to(self.project_root)
                        else str(file_path)
                    ),
                    format="parquet",
                    domain=self.infer_domain(file_path),
                    size_bytes=file_path.stat().st_size,
                    last_modified=datetime.fromtimestamp(
                        file_path.stat().st_mtime, tz=timezone.utc
                    ).strftime("%Y-%m-%d"),
                )
                datasets.append(entry)
                domains_seen.add(entry.domain)
            elif suffix == ".zip":
                entry = self.scan_zip_file(file_path)
                binary_stores.append(entry)
                domains_seen.add(entry.domain)

    def _get_external_module_path(self, module_name: str) -> Path | None:
        """Return the external data path for a module, if it exists."""
        if not self.external_data_root:
            return None
        ext = self.external_data_root / "modules" / module_name
        if ext.is_dir():
            return ext
        return None

    def scan_module(self, module_path: Path) -> ModuleCatalogEntry:
        """Scan a single data module directory.

        If an external data root is configured, merges files from the
        external ``modules/<name>/`` directory into the scan.
        """
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

        # Determine if this is an HSE module with OSHA data
        is_osha = module_name == "hse"

        # Scan the in-repo directory
        self._scan_directory_tree(
            module_path, datasets, binary_stores, domains_seen, is_osha_dir=is_osha
        )

        # Merge external data if available
        ext_path = self._get_external_module_path(module_name)
        if ext_path and ext_path.resolve() != module_path.resolve():
            # Track names already cataloged to avoid duplicates
            # (paths differ between in-repo and external so compare by name)
            seen_names = {d.name for d in datasets} | {b.name for b in binary_stores}

            ext_datasets: list[DatasetEntry] = []
            ext_binaries: list[DatasetEntry] = []
            self._scan_directory_tree(
                ext_path, ext_datasets, ext_binaries, domains_seen, is_osha_dir=is_osha
            )

            for d in ext_datasets:
                if d.name not in seen_names:
                    datasets.append(d)
                    seen_names.add(d.name)
            for b in ext_binaries:
                if b.name not in seen_names:
                    binary_stores.append(b)
                    seen_names.add(b.name)

        return ModuleCatalogEntry(
            name=module_name,
            description=_MODULE_DESCRIPTIONS.get(
                module_name, f"{module_name} data module"
            ),
            path=self._relative_path(module_path),
            domains=sorted(domains_seen),
            datasets=datasets,
            binary_stores=binary_stores,
            documentation=documentation,
        )

    # ------------------------------------------------------------------
    # Source registry merge and staleness
    # ------------------------------------------------------------------

    def _merge_source_registry(self, catalog: DataCatalog) -> None:
        """Populate source_url and update_frequency from source-registry.yml."""
        registry = load_source_registry(self.project_root)
        modules_reg = registry.get("modules", {})

        for mod_name, mod_entry in catalog.modules.items():
            mod_reg = modules_reg.get(mod_name, {})
            default_freq = mod_reg.get("default_update_frequency")
            default_url = mod_reg.get("source_base_url")
            datasets_reg = mod_reg.get("datasets", {}) or {}

            for ds in mod_entry.datasets + mod_entry.binary_stores:
                ds_reg = datasets_reg.get(ds.name, {}) or {}
                if not ds.source_url:
                    ds.source_url = ds_reg.get("source_url") or default_url
                if not ds.update_frequency:
                    ds.update_frequency = ds_reg.get("update_frequency") or default_freq

    def _compute_staleness(self, catalog: DataCatalog) -> None:
        """Mark datasets as stale when last_refreshed exceeds frequency."""
        now = datetime.now(timezone.utc)
        for mod in catalog.modules.values():
            for ds in mod.datasets + mod.binary_stores:
                if ds.data_status in ("lfs_stub", "empty"):
                    continue
                if ds.data_status == "unknown":
                    ds.data_status = "real"
                if ds.last_refreshed and ds.update_frequency:
                    refreshed = datetime.fromisoformat(ds.last_refreshed)
                    max_age = _FREQUENCY_DAYS.get(ds.update_frequency, 99999)
                    if (now - refreshed).days > max_age:
                        ds.data_status = "stale"

    # ------------------------------------------------------------------
    # Freshness report
    # ------------------------------------------------------------------

    @staticmethod
    def print_freshness_report(catalog: DataCatalog) -> None:
        """Print a summary table of data freshness per module."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines: list[str] = [
            f"Data Freshness Report ({today})",
            "=" * 72,
            "",
            f"{'Module':<20} {'Datasets':>8} {'Real':>6} {'Stubs':>6}"
            f" {'Stale':>6} {'Empty':>6}",
            "-" * 72,
        ]
        totals = {"datasets": 0, "real": 0, "stubs": 0, "stale": 0, "empty": 0}

        for mod_name in sorted(catalog.modules):
            mod = catalog.modules[mod_name]
            all_ds = mod.datasets + mod.binary_stores
            counts = {"real": 0, "stubs": 0, "stale": 0, "empty": 0}
            for ds in all_ds:
                if ds.data_status == "lfs_stub":
                    counts["stubs"] += 1
                elif ds.data_status == "stale":
                    counts["stale"] += 1
                elif ds.data_status == "empty":
                    counts["empty"] += 1
                else:
                    counts["real"] += 1
            n = len(all_ds)
            lines.append(
                f"{mod_name:<20} {n:>8} {counts['real']:>6}"
                f" {counts['stubs']:>6} {counts['stale']:>6}"
                f" {counts['empty']:>6}"
            )
            totals["datasets"] += n
            for k in counts:
                totals[k] += counts[k]

        lines.append("-" * 72)
        lines.append(
            f"{'TOTAL':<20} {totals['datasets']:>8}"
            f" {totals['real']:>6} {totals['stubs']:>6}"
            f" {totals['stale']:>6} {totals['empty']:>6}"
        )
        print("\n".join(lines))

    # ------------------------------------------------------------------
    # Multi-module scanning
    # ------------------------------------------------------------------

    def scan_all_modules(self) -> DataCatalog:
        """Scan all modules under data/modules/.

        If an external data root is configured, also discovers modules
        that exist only in the external root (not in the repo).
        """
        catalog = DataCatalog()
        if not self.data_root.exists() and not self.external_data_root:
            return catalog

        # Collect module names from both in-repo and external roots
        module_names: set[str] = set()
        if self.data_root.exists():
            for mp in self.data_root.iterdir():
                if mp.is_dir() and not mp.name.startswith("."):
                    module_names.add(mp.name)
        if self.external_data_root:
            ext_modules = self.external_data_root / "modules"
            if ext_modules.is_dir():
                for mp in ext_modules.iterdir():
                    if mp.is_dir() and not mp.name.startswith("."):
                        module_names.add(mp.name)

        for module_name in sorted(module_names):
            # Use in-repo path as primary; fall back to external
            module_path = self.data_root / module_name
            if not module_path.exists() and self.external_data_root:
                module_path = self.external_data_root / "modules" / module_name

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
    ) -> tuple[Path, DataCatalog]:
        """Generate catalog and write to file.

        Args:
            module_name: If provided, scan only this module.
            output_format: ``"yaml"`` (default) or ``"json"``.

        Returns:
            Tuple of (path to the generated catalog file, catalog object).

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

        self._merge_source_registry(catalog)
        self._compute_staleness(catalog)

        output_dir = self.project_root / "data" / "catalog"
        if output_format == "json":
            output_path = output_dir / "data-catalog.json"
            catalog.to_json(output_path)
        else:
            output_path = output_dir / "data-catalog.yml"
            catalog.to_yaml(output_path)

        return output_path, catalog


def _resolve_external_root(cli_value: str | None) -> Path | None:
    """Resolve external data root from CLI arg or WED_DATA_ROOT env var."""
    path_str = cli_value or os.environ.get("WED_DATA_ROOT")
    if not path_str:
        # Auto-detect common locations
        default = Path("/mnt/ace/worldenergydata/data")
        if default.is_dir():
            return default
        return None
    p = Path(path_str)
    if p.is_dir():
        return p
    print(f"WARNING: external data root not found: {p}", file=sys.stderr)
    return None


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate data catalog")
    parser.add_argument("--module", help="Scan specific module only")
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml")
    parser.add_argument("--project-root", default=None, help="Project root path")
    parser.add_argument(
        "--external-data-root",
        default=None,
        help="Path to external data directory (e.g. /mnt/ace/worldenergydata/data). "
        "Also reads WED_DATA_ROOT env var. Auto-detects /mnt/ace if present.",
    )
    parser.add_argument(
        "--follow-symlinks",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Follow symlinks when scanning directories (default: True). "
        "Use --no-follow-symlinks to disable.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print freshness summary table after generation",
    )
    args = parser.parse_args()

    root = (
        Path(args.project_root)
        if args.project_root
        else Path(__file__).resolve().parent.parent
    )
    ext_root = _resolve_external_root(args.external_data_root)
    if ext_root:
        print(f"External data root: {ext_root}")

    generator = DataCatalogGenerator(
        root,
        external_data_root=ext_root,
        follow_symlinks=args.follow_symlinks,
    )
    output_path, catalog = generator.generate(
        module_name=args.module, output_format=args.format
    )
    print(f"Catalog written to: {output_path}")
    print(
        f"  {catalog.total_modules} modules, "
        f"{catalog.total_datasets} datasets, "
        f"{_humanize_bytes(catalog.total_size_bytes)}"
    )
    if args.report:
        print()
        DataCatalogGenerator.print_freshness_report(catalog)


if __name__ == "__main__":
    main()
