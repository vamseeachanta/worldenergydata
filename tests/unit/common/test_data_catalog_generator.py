"""Tests for the data catalog generation script.

Covers CSV/binary/Excel scanning, domain inference, module scanning,
multi-module scanning, and YAML/JSON catalog generation.  Each test
creates its own filesystem structure in tmp_path.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest
import yaml

# Ensure src is on the path for script imports
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from worldenergydata.common.catalog import DataCatalog, DatasetEntry, ModuleCatalogEntry

# Import the generator under test from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from generate_data_catalog import DataCatalogGenerator, _DOMAIN_MAP


# -- Helpers -----------------------------------------------------------------

def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project structure and return the project root."""
    root = tmp_path / "project"
    (root / "data" / "modules").mkdir(parents=True)
    return root


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write a CSV with the given header and rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


# -- CSV scanning ------------------------------------------------------------

class TestScanCsvFile:
    """Tests for DataCatalogGenerator.scan_csv_file."""

    def test_scan_csv_file_extracts_columns(self, tmp_path: Path):
        """Scanning a CSV extracts column names and row count."""
        root = _make_project(tmp_path)
        csv_path = root / "data" / "modules" / "test_mod" / "current" / "data.csv"
        _write_csv(
            csv_path,
            header=["well_id", "oil_bbl", "gas_mcf"],
            rows=[["W001", "100", "200"], ["W002", "150", "300"], ["W003", "120", "240"]],
        )
        gen = DataCatalogGenerator(root)
        entry = gen.scan_csv_file(csv_path)

        assert entry.name == "data"
        assert entry.format == "csv"
        assert entry.columns == ["well_id", "oil_bbl", "gas_mcf"]
        assert entry.row_count == 3
        assert entry.size_bytes > 0
        assert entry.last_modified is not None
        assert entry.path == "data/modules/test_mod/current/data.csv"

    def test_scan_csv_file_empty(self, tmp_path: Path):
        """A CSV with only a header row has row_count=0."""
        root = _make_project(tmp_path)
        csv_path = root / "data" / "modules" / "test_mod" / "empty.csv"
        _write_csv(csv_path, header=["col_a", "col_b"], rows=[])
        gen = DataCatalogGenerator(root)
        entry = gen.scan_csv_file(csv_path)

        assert entry.columns == ["col_a", "col_b"]
        assert entry.row_count == 0


# -- Binary file scanning ----------------------------------------------------

class TestScanBinaryFile:
    """Tests for DataCatalogGenerator.scan_binary_file."""

    def test_scan_binary_file(self, tmp_path: Path):
        """Binary file scanning produces format='pickle' and captures size."""
        root = _make_project(tmp_path)
        bin_path = root / "data" / "modules" / "test_mod" / "bin" / "model.bin"
        bin_path.parent.mkdir(parents=True)
        bin_path.write_bytes(b"\x80\x04\x95" + b"\x00" * 100)
        gen = DataCatalogGenerator(root)
        entry = gen.scan_binary_file(bin_path)

        assert entry.name == "model"
        assert entry.format == "pickle"
        assert entry.size_bytes == 103
        assert entry.last_modified is not None
        assert entry.path == "data/modules/test_mod/bin/model.bin"


# -- Excel file scanning -----------------------------------------------------

class TestScanExcelFile:
    """Tests for DataCatalogGenerator.scan_excel_file."""

    def test_scan_excel_file_xlsx(self, tmp_path: Path):
        """An .xlsx file is reported with format='xlsx'."""
        root = _make_project(tmp_path)
        xlsx_path = root / "data" / "modules" / "test_mod" / "report.xlsx"
        xlsx_path.parent.mkdir(parents=True, exist_ok=True)
        xlsx_path.write_bytes(b"PK\x03\x04" + b"\x00" * 50)
        gen = DataCatalogGenerator(root)
        entry = gen.scan_excel_file(xlsx_path)

        assert entry.name == "report"
        assert entry.format == "xlsx"
        assert entry.size_bytes == 54

    def test_scan_excel_file_xls(self, tmp_path: Path):
        """An .xls file is reported with format='xls'."""
        root = _make_project(tmp_path)
        xls_path = root / "data" / "modules" / "test_mod" / "legacy.xls"
        xls_path.parent.mkdir(parents=True, exist_ok=True)
        xls_path.write_bytes(b"\xd0\xcf\x11\xe0" + b"\x00" * 40)
        gen = DataCatalogGenerator(root)
        entry = gen.scan_excel_file(xls_path)

        assert entry.name == "legacy"
        assert entry.format == "xls"
        assert entry.size_bytes == 44


# -- Domain inference --------------------------------------------------------

class TestInferDomain:
    """Tests for DataCatalogGenerator.infer_domain."""

    def test_infer_domain_production(self, tmp_path: Path):
        """A path containing 'production' infers domain 'production'."""
        root = _make_project(tmp_path)
        gen = DataCatalogGenerator(root)
        path = root / "data" / "modules" / "bsee" / "production" / "monthly.csv"
        assert gen.infer_domain(path) == "production"

    def test_infer_domain_wells(self, tmp_path: Path):
        """A path containing 'wells' infers domain 'drilling'."""
        root = _make_project(tmp_path)
        gen = DataCatalogGenerator(root)
        path = root / "data" / "modules" / "bsee" / "wells" / "headers.csv"
        assert gen.infer_domain(path) == "drilling"

    def test_infer_domain_unknown(self, tmp_path: Path):
        """An unrecognized directory name falls back to 'general'."""
        root = _make_project(tmp_path)
        gen = DataCatalogGenerator(root)
        path = root / "data" / "modules" / "bsee" / "misc" / "stuff.csv"
        assert gen.infer_domain(path) == "general"


# -- Module scanning ---------------------------------------------------------

class TestScanModule:
    """Tests for DataCatalogGenerator.scan_module."""

    def test_scan_module_finds_csvs(self, tmp_path: Path):
        """scan_module discovers CSV files and populates datasets."""
        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "test_mod"
        _write_csv(
            mod_dir / "current" / "production" / "data.csv",
            header=["date", "oil"], rows=[["2024-01", "100"]],
        )
        _write_csv(
            mod_dir / "current" / "wells" / "headers.csv",
            header=["well_id", "name"], rows=[["W1", "Alpha"], ["W2", "Beta"]],
        )
        gen = DataCatalogGenerator(root)
        entry = gen.scan_module(mod_dir)

        assert entry.name == "test_mod"
        assert len(entry.datasets) == 2
        assert entry.dataset_count == 2
        assert entry.total_size_bytes > 0
        assert "production" in entry.domains
        assert "drilling" in entry.domains

    def test_scan_module_empty_dir(self, tmp_path: Path):
        """An empty module directory returns 0 datasets."""
        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "empty_mod"
        mod_dir.mkdir(parents=True)
        gen = DataCatalogGenerator(root)
        entry = gen.scan_module(mod_dir)

        assert entry.name == "empty_mod"
        assert entry.dataset_count == 0
        assert entry.datasets == []
        assert entry.binary_stores == []
        assert entry.total_size_bytes == 0

    def test_scan_module_with_binary_and_csv(self, tmp_path: Path):
        """Module with both CSV and .bin files separates them correctly."""
        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "mixed_mod"
        _write_csv(mod_dir / "current" / "data.csv", header=["x", "y"], rows=[["1", "2"]])
        bin_path = mod_dir / "bin" / "store.bin"
        bin_path.parent.mkdir(parents=True)
        bin_path.write_bytes(b"\x00" * 50)
        gen = DataCatalogGenerator(root)
        entry = gen.scan_module(mod_dir)

        assert len(entry.datasets) == 1
        assert len(entry.binary_stores) == 1
        assert entry.dataset_count == 2

    def test_scan_module_finds_documentation(self, tmp_path: Path):
        """scan_module picks up README.md and DATA_DICTIONARY.md."""
        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "doc_mod"
        mod_dir.mkdir(parents=True)
        _write_csv(mod_dir / "data.csv", header=["a"], rows=[["1"]])
        (mod_dir / "README.md").write_text("# Module docs")
        (mod_dir / "DATA_DICTIONARY.md").write_text("# Data dictionary")
        gen = DataCatalogGenerator(root)
        entry = gen.scan_module(mod_dir)

        assert "readme" in entry.documentation
        assert "data_dictionary" in entry.documentation


# -- Multi-module scanning ---------------------------------------------------

class TestScanAllModules:
    """Tests for DataCatalogGenerator.scan_all_modules."""

    def test_scan_all_modules(self, tmp_path: Path):
        """scan_all_modules discovers all module directories."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "mod_a" / "data.csv",
            header=["col1"], rows=[["val1"]],
        )
        _write_csv(
            root / "data" / "modules" / "mod_b" / "info.csv",
            header=["col2"], rows=[["val2"], ["val3"]],
        )
        (root / "data" / "modules" / "mod_c").mkdir(parents=True)  # empty
        gen = DataCatalogGenerator(root)
        catalog = gen.scan_all_modules()

        assert isinstance(catalog, DataCatalog)
        assert catalog.total_modules == 2
        assert "mod_a" in catalog.modules
        assert "mod_b" in catalog.modules
        assert "mod_c" not in catalog.modules  # empty modules excluded

    def test_scan_all_modules_no_data_dir(self, tmp_path: Path):
        """If data/modules/ does not exist, return empty catalog."""
        root = tmp_path / "project_empty"
        root.mkdir()
        gen = DataCatalogGenerator(root)
        catalog = gen.scan_all_modules()

        assert catalog.total_modules == 0
        assert catalog.modules == {}


# -- Catalog generation (output files) ---------------------------------------

class TestGenerate:
    """Tests for DataCatalogGenerator.generate."""

    def test_generate_yaml_output(self, tmp_path: Path):
        """generate() with default format produces a .yml file."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "test_mod" / "data.csv",
            header=["a", "b"], rows=[["1", "2"]],
        )
        gen = DataCatalogGenerator(root)
        output_path = gen.generate(output_format="yaml")

        assert output_path.exists()
        assert output_path.suffix == ".yml"
        assert output_path.name == "data-catalog.yml"
        with open(output_path) as f:
            loaded = yaml.safe_load(f)
        assert loaded["version"] == "1.0.0"
        assert loaded["total_modules"] == 1
        assert "test_mod" in loaded["modules"]

    def test_generate_json_output(self, tmp_path: Path):
        """generate() with format='json' produces a .json file."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "test_mod" / "data.csv",
            header=["x"], rows=[["10"]],
        )
        gen = DataCatalogGenerator(root)
        output_path = gen.generate(output_format="json")

        assert output_path.exists()
        assert output_path.suffix == ".json"
        assert output_path.name == "data-catalog.json"
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded["version"] == "1.0.0"
        assert loaded["total_modules"] == 1
        assert "test_mod" in loaded["modules"]

    def test_generate_single_module(self, tmp_path: Path):
        """generate() with module_name scans only that module."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "mod_a" / "data.csv",
            header=["a"], rows=[["1"]],
        )
        _write_csv(
            root / "data" / "modules" / "mod_b" / "data.csv",
            header=["b"], rows=[["2"]],
        )
        gen = DataCatalogGenerator(root)
        output_path = gen.generate(module_name="mod_a", output_format="json")

        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded["total_modules"] == 1
        assert "mod_a" in loaded["modules"]
        assert "mod_b" not in loaded["modules"]

    def test_generate_missing_module_raises(self, tmp_path: Path):
        """generate() with a non-existent module_name raises FileNotFoundError."""
        root = _make_project(tmp_path)
        gen = DataCatalogGenerator(root)
        with pytest.raises(FileNotFoundError, match="Module not found"):
            gen.generate(module_name="nonexistent")
