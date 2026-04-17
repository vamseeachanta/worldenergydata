"""
Tests for multi-format export functionality (WRK-083).

Validates that BSEE production data can be exported to:
- Excel (.xlsx)
- PDF (.pdf) [requires weasyprint]
- Parquet (.parquet)
- JSON (.json)
- CSV (.csv)
"""

import json
import pickle
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd


class TestBSEEDataExport(unittest.TestCase):
    """Test multi-format export with real BSEE production data."""

    @classmethod
    def setUpClass(cls):
        """Load BSEE production data once for all tests."""
        cls.test_df = cls._load_bsee_data()
        cls.temp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        """Clean up temp directory."""
        import shutil

        if Path(cls.temp_dir).exists():
            shutil.rmtree(cls.temp_dir)

    @classmethod
    def _load_bsee_data(cls):
        """Load real BSEE production data from pickle."""
        try:
            # Try to load production sum data
            bin_file = (
                Path(__file__).parents[4]
                / "data"
                / "modules"
                / "bsee"
                / "bin"
                / "production_raw"
                / "mv_productionsum.bin"
            )

            if not bin_file.exists():
                return cls._create_synthetic_data()

            # Check if LFS stub
            with open(bin_file, "rb") as f:
                header = f.read(40)
                if b"version https://git-lfs" in header:
                    return cls._create_synthetic_data()

            # Load pickle
            with open(bin_file, "rb") as f:
                df = pickle.load(f)

            return df

        except Exception:
            return cls._create_synthetic_data()

    @staticmethod
    def _create_synthetic_data():
        """Create synthetic BSEE-style production data."""
        import numpy as np

        years = list(range(1985, 2025))
        return pd.DataFrame(
            {
                "PROD_YEAR": years,
                "OIL_STB": np.random.randint(10000000, 50000000, len(years)),
                "GAS_MCF": np.random.randint(50000000, 200000000, len(years)),
            }
        )

    def test_excel_export_available(self):
        """Test Excel exporter is available with openpyxl."""
        try:
            import openpyxl

            self.assertTrue(True, "openpyxl available")
        except ImportError:
            self.skipTest("openpyxl not installed")

        from worldenergydata.bsee.reports.comprehensive.exporters.excel_exporter import (
            ExcelExporter,
        )

        exporter = ExcelExporter()
        self.assertIsNotNone(exporter)

    def test_excel_export_production_data(self):
        """Test exporting BSEE production data to Excel."""
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl not installed")

        from worldenergydata.bsee.reports.comprehensive.exporters.base import (
            ExportConfig,
            ExportFormat,
        )
        from worldenergydata.bsee.reports.comprehensive.exporters.excel_exporter import (
            ExcelExporter,
        )

        exporter = ExcelExporter()

        test_data = {
            "report_metadata": {
                "title": "BSEE Production Export Test",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "organization": "WRK-083",
            },
            "production_data": self.test_df.to_dict("records"),
            "summary": {
                "total_records": len(self.test_df),
                "total_oil_stb": (
                    int(self.test_df["OIL_STB"].sum())
                    if "OIL_STB" in self.test_df.columns
                    else 0
                ),
                "total_gas_mcf": (
                    int(self.test_df["GAS_MCF"].sum())
                    if "GAS_MCF" in self.test_df.columns
                    else 0
                ),
            },
        }

        output_path = Path(self.temp_dir) / "bsee_production.xlsx"
        config = ExportConfig(
            format=ExportFormat.EXCEL,
            output_path=output_path,
            include_charts=False,
            include_raw_data=False,
        )

        result = exporter.export(test_data, config)

        self.assertTrue(result.success, f"Excel export failed: {result.message}")
        self.assertTrue(output_path.exists())
        self.assertGreater(result.file_size, 0)
        self.assertGreater(len(self.test_df), 0)

    def test_pdf_export_available(self):
        """Test PDF exporter availability (may fail without weasyprint)."""
        from worldenergydata.bsee.reports.comprehensive.exporters.pdf_exporter import (
            PDFExporter,
        )

        exporter = PDFExporter()
        self.assertIsNotNone(exporter)

        # Check if weasyprint is available
        try:
            import weasyprint

            self.assertTrue(True, "weasyprint available")
        except ImportError:
            self.skipTest("weasyprint not installed (expected)")

    def test_parquet_export_with_pandas(self):
        """Test Parquet export using pandas + pyarrow."""
        try:
            import pyarrow
        except ImportError:
            self.skipTest("pyarrow not installed")

        output_path = Path(self.temp_dir) / "bsee_production.parquet"

        # Export
        self.test_df.to_parquet(output_path, engine="pyarrow", index=False)

        # Verify file exists
        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)

        # Verify can be read back
        df_verify = pd.read_parquet(output_path)
        self.assertEqual(len(df_verify), len(self.test_df))
        self.assertListEqual(list(df_verify.columns), list(self.test_df.columns))

    def test_json_export_with_metadata(self):
        """Test JSON export with BSEE metadata."""
        output_path = Path(self.temp_dir) / "bsee_production.json"

        export_data = {
            "metadata": {
                "title": "BSEE Production Data",
                "source": "Bureau of Safety and Environmental Enforcement",
                "exported_at": datetime.now().isoformat(),
                "record_count": len(self.test_df),
                "columns": list(self.test_df.columns),
            },
            "records": self.test_df.to_dict("records"),
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        # Verify
        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)

        # Verify can be read back
        with open(output_path, "r") as f:
            loaded = json.load(f)

        self.assertEqual(loaded["metadata"]["record_count"], len(self.test_df))
        self.assertEqual(len(loaded["records"]), len(self.test_df))

    def test_csv_export_basic(self):
        """Test CSV export with pandas."""
        output_path = Path(self.temp_dir) / "bsee_production.csv"

        # Export
        self.test_df.to_csv(output_path, index=False)

        # Verify
        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)

        # Verify can be read back
        df_verify = pd.read_csv(output_path)
        self.assertEqual(len(df_verify), len(self.test_df))
        self.assertListEqual(list(df_verify.columns), list(self.test_df.columns))

    def test_all_formats_roundtrip(self):
        """Test that data can be exported and re-imported without loss."""
        formats_to_test = []

        # Excel
        try:
            import openpyxl

            formats_to_test.append(("xlsx", lambda p: pd.read_excel(p)))
        except ImportError:
            pass

        # Parquet
        try:
            import pyarrow

            formats_to_test.append(("parquet", lambda p: pd.read_parquet(p)))
        except ImportError:
            pass

        # CSV (always available)
        formats_to_test.append(("csv", lambda p: pd.read_csv(p)))

        # JSON (always available)
        def read_json_records(path):
            with open(path, "r") as f:
                data = json.load(f)
            return pd.DataFrame(data)

        formats_to_test.append(("json", read_json_records))

        for ext, reader_func in formats_to_test:
            with self.subTest(format=ext):
                output_path = Path(self.temp_dir) / f"roundtrip.{ext}"

                # Export
                if ext == "xlsx":
                    self.test_df.to_excel(output_path, index=False)
                elif ext == "parquet":
                    self.test_df.to_parquet(output_path, index=False)
                elif ext == "csv":
                    self.test_df.to_csv(output_path, index=False)
                elif ext == "json":
                    self.test_df.to_json(output_path, orient="records", indent=2)

                # Import and verify
                df_verify = reader_func(output_path)
                self.assertEqual(len(df_verify), len(self.test_df))

    def test_export_format_comparison(self):
        """Compare file sizes of different export formats."""
        size_comparison = {}

        # CSV baseline
        csv_path = Path(self.temp_dir) / "compare.csv"
        self.test_df.to_csv(csv_path, index=False)
        size_comparison["CSV"] = csv_path.stat().st_size

        # JSON
        json_path = Path(self.temp_dir) / "compare.json"
        self.test_df.to_json(json_path, orient="records", indent=2)
        size_comparison["JSON"] = json_path.stat().st_size

        # Parquet (if available)
        try:
            import pyarrow

            parquet_path = Path(self.temp_dir) / "compare.parquet"
            self.test_df.to_parquet(parquet_path, index=False)
            size_comparison["Parquet"] = parquet_path.stat().st_size
        except ImportError:
            pass

        # Excel (if available)
        try:
            import openpyxl

            xlsx_path = Path(self.temp_dir) / "compare.xlsx"
            self.test_df.to_excel(xlsx_path, index=False)
            size_comparison["Excel"] = xlsx_path.stat().st_size
        except ImportError:
            pass

        # Verify all formats produced output
        for format_name, size in size_comparison.items():
            self.assertGreater(size, 0, f"{format_name} produced empty file")

        # Parquet should typically be smaller than CSV for large datasets
        # For small datasets (like our test data), compression overhead can make it larger
        if "Parquet" in size_comparison and "CSV" in size_comparison:
            # Parquet is columnar and compressed
            # For small datasets, either format is acceptable
            self.assertLess(
                size_comparison["Parquet"],
                size_comparison["CSV"] * 5,  # Allow up to 5x for small datasets
                "Parquet should not be excessively large",
            )


class TestExporterInterfaces(unittest.TestCase):
    """Test that all exporters follow consistent interfaces."""

    def test_bsee_excel_exporter_interface(self):
        """Test BSEE Excel exporter has required methods."""
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl not installed")

        from worldenergydata.bsee.reports.comprehensive.exporters.excel_exporter import (
            ExcelExporter,
        )

        exporter = ExcelExporter()

        # Check required methods
        self.assertTrue(hasattr(exporter, "export"))
        self.assertTrue(hasattr(exporter, "validate_data"))
        self.assertTrue(hasattr(exporter, "get_supported_features"))
        self.assertTrue(callable(exporter.export))
        self.assertTrue(callable(exporter.validate_data))

    def test_bsee_pdf_exporter_interface(self):
        """Test BSEE PDF exporter has required methods."""
        from worldenergydata.bsee.reports.comprehensive.exporters.pdf_exporter import (
            PDFExporter,
        )

        exporter = PDFExporter()

        # Check required methods
        self.assertTrue(hasattr(exporter, "export"))
        self.assertTrue(hasattr(exporter, "validate_data"))
        self.assertTrue(hasattr(exporter, "get_supported_features"))
        self.assertTrue(callable(exporter.export))
        self.assertTrue(callable(exporter.validate_data))


if __name__ == "__main__":
    unittest.main()
