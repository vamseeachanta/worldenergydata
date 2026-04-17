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
from generate_data_catalog import (
    _DOMAIN_MAP,
    _LFS_SIGNATURE,
    DataCatalogGenerator,
    load_source_registry,
)

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
            rows=[
                ["W001", "100", "200"],
                ["W002", "150", "300"],
                ["W003", "120", "240"],
            ],
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
        assert entry.is_lfs_stub is False
        assert entry.data_status == "real"


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
            header=["date", "oil"],
            rows=[["2024-01", "100"]],
        )
        _write_csv(
            mod_dir / "current" / "wells" / "headers.csv",
            header=["well_id", "name"],
            rows=[["W1", "Alpha"], ["W2", "Beta"]],
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
        _write_csv(
            mod_dir / "current" / "data.csv", header=["x", "y"], rows=[["1", "2"]]
        )
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
            header=["col1"],
            rows=[["val1"]],
        )
        _write_csv(
            root / "data" / "modules" / "mod_b" / "info.csv",
            header=["col2"],
            rows=[["val2"], ["val3"]],
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
            header=["a", "b"],
            rows=[["1", "2"]],
        )
        gen = DataCatalogGenerator(root)
        output_path, catalog = gen.generate(output_format="yaml")

        assert output_path.exists()
        assert output_path.suffix == ".yml"
        assert output_path.name == "data-catalog.yml"
        with open(output_path) as f:
            loaded = yaml.safe_load(f)
        assert loaded["version"] == "1.1.0"
        assert loaded["total_modules"] == 1
        assert "test_mod" in loaded["modules"]

    def test_generate_json_output(self, tmp_path: Path):
        """generate() with format='json' produces a .json file."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "test_mod" / "data.csv",
            header=["x"],
            rows=[["10"]],
        )
        gen = DataCatalogGenerator(root)
        output_path, catalog = gen.generate(output_format="json")

        assert output_path.exists()
        assert output_path.suffix == ".json"
        assert output_path.name == "data-catalog.json"
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded["version"] == "1.1.0"
        assert loaded["total_modules"] == 1
        assert "test_mod" in loaded["modules"]

    def test_generate_single_module(self, tmp_path: Path):
        """generate() with module_name scans only that module."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "mod_a" / "data.csv",
            header=["a"],
            rows=[["1"]],
        )
        _write_csv(
            root / "data" / "modules" / "mod_b" / "data.csv",
            header=["b"],
            rows=[["2"]],
        )
        gen = DataCatalogGenerator(root)
        output_path, catalog = gen.generate(module_name="mod_a", output_format="json")

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


# -- LFS stub detection -----------------------------------------------------


class TestLfsStubDetection:
    """Tests for Git LFS stub detection in scan_binary_file."""

    def test_scan_binary_lfs_stub(self, tmp_path: Path):
        """A file starting with the LFS signature is flagged as a stub."""
        root = _make_project(tmp_path)
        bin_path = root / "data" / "modules" / "test_mod" / "bin" / "stub.bin"
        bin_path.parent.mkdir(parents=True)
        lfs_content = (
            b"version https://git-lfs.github.com/spec/v1\n"
            b"oid sha256:abc123\nsize 12345\n"
        )
        bin_path.write_bytes(lfs_content)
        gen = DataCatalogGenerator(root)
        entry = gen.scan_binary_file(bin_path)

        assert entry.is_lfs_stub is True
        assert entry.data_status == "lfs_stub"

    def test_scan_binary_real_file(self, tmp_path: Path):
        """A file with pickle header is detected as real data."""
        root = _make_project(tmp_path)
        bin_path = root / "data" / "modules" / "test_mod" / "bin" / "real.bin"
        bin_path.parent.mkdir(parents=True)
        bin_path.write_bytes(b"\x80\x04\x95" + b"\x00" * 100)
        gen = DataCatalogGenerator(root)
        entry = gen.scan_binary_file(bin_path)

        assert entry.is_lfs_stub is False
        assert entry.data_status == "real"

    def test_scan_binary_empty_file(self, tmp_path: Path):
        """A zero-byte file gets data_status='empty'."""
        root = _make_project(tmp_path)
        bin_path = root / "data" / "modules" / "test_mod" / "bin" / "empty.bin"
        bin_path.parent.mkdir(parents=True)
        bin_path.write_bytes(b"")
        gen = DataCatalogGenerator(root)
        entry = gen.scan_binary_file(bin_path)

        assert entry.is_lfs_stub is False
        assert entry.data_status == "empty"
        assert entry.size_bytes == 0


# -- Source registry merge ---------------------------------------------------


class TestSourceRegistryMerge:
    """Tests for _merge_source_registry."""

    def test_merge_applies_source_url(self, tmp_path: Path):
        """Registry URLs are applied to matching datasets."""
        root = _make_project(tmp_path)
        registry_dir = root / "data" / "catalog"
        registry_dir.mkdir(parents=True, exist_ok=True)
        (registry_dir / "source-registry.yml").write_text(
            "modules:\n"
            "  test_mod:\n"
            "    datasets:\n"
            "      data:\n"
            "        source_url: https://example.com/data.zip\n"
        )
        _write_csv(
            root / "data" / "modules" / "test_mod" / "data.csv",
            header=["a"],
            rows=[["1"]],
        )
        gen = DataCatalogGenerator(root)
        _, catalog = gen.generate(output_format="yaml")

        ds = catalog.modules["test_mod"].datasets[0]
        assert ds.source_url == "https://example.com/data.zip"

    def test_merge_applies_default_frequency(self, tmp_path: Path):
        """Module-level default_update_frequency flows to datasets."""
        root = _make_project(tmp_path)
        registry_dir = root / "data" / "catalog"
        registry_dir.mkdir(parents=True, exist_ok=True)
        (registry_dir / "source-registry.yml").write_text(
            "modules:\n" "  test_mod:\n" "    default_update_frequency: quarterly\n"
        )
        _write_csv(
            root / "data" / "modules" / "test_mod" / "data.csv",
            header=["a"],
            rows=[["1"]],
        )
        gen = DataCatalogGenerator(root)
        _, catalog = gen.generate(output_format="yaml")

        ds = catalog.modules["test_mod"].datasets[0]
        assert ds.update_frequency == "quarterly"

    def test_merge_no_registry_file(self, tmp_path: Path):
        """Missing registry file causes no crash; fields stay None."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "test_mod" / "data.csv",
            header=["a"],
            rows=[["1"]],
        )
        gen = DataCatalogGenerator(root)
        _, catalog = gen.generate(output_format="yaml")

        ds = catalog.modules["test_mod"].datasets[0]
        assert ds.source_url is None
        assert ds.update_frequency is None


# -- Staleness calculation ---------------------------------------------------


class TestStalenessCalculation:
    """Tests for _compute_staleness."""

    def test_stale_dataset(self, tmp_path: Path):
        """A dataset with old last_refreshed relative to frequency is marked stale."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "test_mod" / "data.csv",
            header=["a"],
            rows=[["1"]],
        )
        gen = DataCatalogGenerator(root)
        catalog = gen.scan_all_modules()

        ds = catalog.modules["test_mod"].datasets[0]
        ds.update_frequency = "daily"
        ds.last_refreshed = "2020-01-01T00:00:00+00:00"
        ds.data_status = "real"

        gen._compute_staleness(catalog)
        assert ds.data_status == "stale"

    def test_fresh_dataset(self, tmp_path: Path):
        """A recently refreshed dataset stays as 'real'."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "test_mod" / "data.csv",
            header=["a"],
            rows=[["1"]],
        )
        gen = DataCatalogGenerator(root)
        catalog = gen.scan_all_modules()

        ds = catalog.modules["test_mod"].datasets[0]
        from datetime import datetime, timezone

        ds.update_frequency = "annual"
        ds.last_refreshed = datetime.now(timezone.utc).isoformat()
        ds.data_status = "real"

        gen._compute_staleness(catalog)
        assert ds.data_status == "real"


# -- Freshness report -------------------------------------------------------


class TestFreshnessReport:
    """Tests for print_freshness_report."""

    def test_report_output(self, tmp_path: Path, capsys):
        """Report prints a table with correct counts."""
        root = _make_project(tmp_path)
        # Create a module with a real CSV and an LFS stub binary
        mod_dir = root / "data" / "modules" / "test_mod"
        _write_csv(mod_dir / "data.csv", header=["a"], rows=[["1"]])
        bin_path = mod_dir / "bin" / "stub.bin"
        bin_path.parent.mkdir(parents=True)
        lfs_content = (
            b"version https://git-lfs.github.com/spec/v1\n"
            b"oid sha256:abc123\nsize 12345\n"
        )
        bin_path.write_bytes(lfs_content)

        gen = DataCatalogGenerator(root)
        _, catalog = gen.generate(output_format="yaml")

        DataCatalogGenerator.print_freshness_report(catalog)
        captured = capsys.readouterr()

        assert "Data Freshness Report" in captured.out
        assert "test_mod" in captured.out
        assert "TOTAL" in captured.out


# -- External data root merging ---------------------------------------------


class TestExternalDataRoot:
    """Tests for external data root merging."""

    def test_external_root_adds_binary_directory(self, tmp_path: Path):
        """External root with bin/ subdirectories adds binary_stores entries."""
        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "bsee"
        _write_csv(mod_dir / "current" / "data.csv", header=["a"], rows=[["1"]])

        # Create external data with bin/ directory
        ext_root = tmp_path / "external" / "data"
        ext_bin = ext_root / "modules" / "bsee" / "bin" / "production_raw"
        ext_bin.mkdir(parents=True)
        (ext_bin / "file1.bin").write_bytes(b"\x00" * 100)
        (ext_bin / "file2.bin").write_bytes(b"\x00" * 200)

        gen = DataCatalogGenerator(root, external_data_root=ext_root)
        entry = gen.scan_module(mod_dir)

        assert len(entry.datasets) == 1  # the CSV
        assert len(entry.binary_stores) >= 1  # at least the bin directory
        # Total size should include external binary data
        assert entry.total_size_bytes > 300

    def test_external_root_adds_zip_files(self, tmp_path: Path):
        """External root with zip/ files adds binary_stores entries."""
        import zipfile as zf

        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "bsee"
        _write_csv(mod_dir / "current" / "data.csv", header=["a"], rows=[["1"]])

        # Create external zip
        ext_root = tmp_path / "external" / "data"
        ext_zip_dir = ext_root / "modules" / "bsee" / "zip" / "surveys"
        ext_zip_dir.mkdir(parents=True)
        zip_path = ext_zip_dir / "test.zip"
        with zf.ZipFile(zip_path, "w") as z:
            z.writestr("data.csv", "a,b\n1,2\n")

        gen = DataCatalogGenerator(root, external_data_root=ext_root)
        entry = gen.scan_module(mod_dir)

        zip_entries = [b for b in entry.binary_stores if b.format == "zip"]
        assert len(zip_entries) >= 1
        assert zip_entries[0].description
        assert "1 file(s)" in zip_entries[0].description

    def test_external_root_merges_csv_files(self, tmp_path: Path):
        """External root CSV files appear in the module's dataset list."""
        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "hse"
        mod_dir.mkdir(parents=True)

        # Create external OSHA CSV
        ext_root = tmp_path / "external" / "data"
        osha_dir = ext_root / "modules" / "hse" / "raw" / "osha"
        osha_dir.mkdir(parents=True)
        _write_csv(
            osha_dir / "osha_accident.csv",
            header=["summary_nr", "event_date"],
            rows=[["1001", "20240101"]],
        )

        gen = DataCatalogGenerator(root, external_data_root=ext_root)
        entry = gen.scan_module(mod_dir)

        csv_names = [d.name for d in entry.datasets if d.format == "csv"]
        assert "osha_accident" in csv_names

    def test_external_root_no_duplicates(self, tmp_path: Path):
        """Datasets present in both roots appear only once."""
        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "test_mod"
        _write_csv(mod_dir / "data.csv", header=["a"], rows=[["1"]])

        # External root with same file path
        ext_root = tmp_path / "external" / "data"
        ext_mod = ext_root / "modules" / "test_mod"
        _write_csv(ext_mod / "data.csv", header=["a"], rows=[["1"]])

        gen = DataCatalogGenerator(root, external_data_root=ext_root)
        entry = gen.scan_module(mod_dir)

        csv_ds = [d for d in entry.datasets if d.format == "csv"]
        assert len(csv_ds) == 1  # Not duplicated

    def test_no_external_root_still_works(self, tmp_path: Path):
        """Generator works correctly with no external root."""
        root = _make_project(tmp_path)
        mod_dir = root / "data" / "modules" / "test_mod"
        _write_csv(mod_dir / "data.csv", header=["a"], rows=[["1"]])

        gen = DataCatalogGenerator(root)  # No external root
        entry = gen.scan_module(mod_dir)

        assert len(entry.datasets) == 1
        assert entry.datasets[0].name == "data"

    def test_scan_all_discovers_external_only_modules(self, tmp_path: Path):
        """Modules that only exist in external root are discovered."""
        root = _make_project(tmp_path)
        _write_csv(
            root / "data" / "modules" / "mod_a" / "data.csv",
            header=["a"],
            rows=[["1"]],
        )

        ext_root = tmp_path / "external" / "data"
        ext_mod = ext_root / "modules" / "ext_only_mod"
        _write_csv(ext_mod / "data.csv", header=["b"], rows=[["2"]])

        gen = DataCatalogGenerator(root, external_data_root=ext_root)
        catalog = gen.scan_all_modules()

        assert "mod_a" in catalog.modules
        assert "ext_only_mod" in catalog.modules


# -- OSHA data dictionary enrichment ----------------------------------------


class TestOshaEnrichment:
    """Tests for OSHA data dictionary column enrichment."""

    def test_osha_columns_enriched(self, tmp_path: Path):
        """OSHA CSV columns get descriptions from the data dictionary."""
        root = _make_project(tmp_path)
        ext_root = tmp_path / "external" / "data"
        osha_dir = ext_root / "modules" / "hse" / "raw" / "osha"
        osha_dir.mkdir(parents=True)

        # Create data dictionary
        _write_csv(
            osha_dir / "osha_data_dictionary.csv",
            header=[
                "table_name",
                "column_name",
                "attribute_name",
                "definition",
                "column_datatype",
                "display_name",
            ],
            rows=[
                [
                    "osha_accident",
                    "summary_nr",
                    "Summary NR",
                    "Identifies the accident form",
                    "Numeric, Length=9",
                    "Summary NR",
                ],
                [
                    "osha_accident",
                    "event_date",
                    "Event Date",
                    "Date of accident",
                    "Numeric, Length=8",
                    "Event Date",
                ],
            ],
        )

        # Create OSHA accident CSV
        _write_csv(
            osha_dir / "osha_accident.csv",
            header=["summary_nr", "event_date", "event_desc"],
            rows=[["1001", "20240101", "test"]],
        )

        # Create in-repo hse module
        hse_dir = root / "data" / "modules" / "hse"
        hse_dir.mkdir(parents=True)

        gen = DataCatalogGenerator(root, external_data_root=ext_root)
        entry = gen.scan_module(hse_dir)

        osha_ds = [d for d in entry.datasets if d.name == "osha_accident"]
        assert len(osha_ds) == 1
        ds = osha_ds[0]
        assert ds.column_schemas is not None
        assert len(ds.column_schemas) == 3

        # Check enriched columns
        schema_map = {cs.name: cs for cs in ds.column_schemas}
        assert "Identifies the accident form" in schema_map["summary_nr"].description
        assert "Date of accident" in schema_map["event_date"].description

    def test_osha_numbered_splits_matched(self, tmp_path: Path):
        """Numbered OSHA files (osha_violation3.csv) match base table in dictionary."""
        root = _make_project(tmp_path)
        ext_root = tmp_path / "external" / "data"
        osha_dir = ext_root / "modules" / "hse" / "raw" / "osha"
        osha_dir.mkdir(parents=True)

        _write_csv(
            osha_dir / "osha_data_dictionary.csv",
            header=[
                "table_name",
                "column_name",
                "attribute_name",
                "definition",
                "column_datatype",
                "display_name",
            ],
            rows=[
                [
                    "osha_violation",
                    "activity_nr",
                    "Activity NR",
                    "Unique activity identifier",
                    "Numeric",
                    "Activity NR",
                ],
            ],
        )
        _write_csv(
            osha_dir / "osha_violation3.csv",
            header=["activity_nr", "other_col"],
            rows=[["1001", "x"]],
        )

        hse_dir = root / "data" / "modules" / "hse"
        hse_dir.mkdir(parents=True)

        gen = DataCatalogGenerator(root, external_data_root=ext_root)
        entry = gen.scan_module(hse_dir)

        viol_ds = [d for d in entry.datasets if d.name == "osha_violation3"]
        assert len(viol_ds) == 1
        assert viol_ds[0].column_schemas is not None
        schema_map = {cs.name: cs for cs in viol_ds[0].column_schemas}
        assert "Unique activity identifier" in schema_map["activity_nr"].description


# -- Zip file scanning -------------------------------------------------------


class TestZipScanning:
    """Tests for zip file scanning."""

    def test_scan_zip_file(self, tmp_path: Path):
        """scan_zip_file captures file listing from zip archive."""
        import zipfile as zf

        root = _make_project(tmp_path)
        zip_path = root / "data" / "modules" / "test_mod" / "archive.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zf.ZipFile(zip_path, "w") as z:
            z.writestr("data1.csv", "a\n1\n")
            z.writestr("data2.csv", "b\n2\n")

        gen = DataCatalogGenerator(root)
        entry = gen.scan_zip_file(zip_path)

        assert entry.name == "archive"
        assert entry.format == "zip"
        assert "2 file(s)" in entry.description
        assert entry.size_bytes > 0


# -- Binary directory scanning -----------------------------------------------


class TestBinaryDirectoryScanning:
    """Tests for binary directory scanning."""

    def test_scan_binary_directory(self, tmp_path: Path):
        """scan_binary_directory summarizes file counts and sizes."""
        root = _make_project(tmp_path)
        bin_dir = root / "data" / "modules" / "test_mod" / "bin" / "production"
        bin_dir.mkdir(parents=True)
        (bin_dir / "file1.bin").write_bytes(b"\x00" * 100)
        (bin_dir / "file2.bin").write_bytes(b"\x00" * 200)
        (bin_dir / ".gitkeep").write_bytes(b"")

        gen = DataCatalogGenerator(root)
        entry = gen.scan_binary_directory(bin_dir)

        assert entry.name == "production"
        assert entry.format == "binary_directory"
        assert entry.size_bytes == 300
        assert entry.row_count == 3  # file count including .gitkeep
        assert "Binary data directory" in entry.description
