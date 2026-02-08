"""Tests for infrastructure data processing in MemoryProcessor."""

import io
import zipfile

import pandas as pd

from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor


def _create_test_zip(data: str, filename: str = "test_data.txt") -> bytes:
    """Create a test ZIP file with CSV data."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, data)
    return buf.getvalue()


class TestProcessPlatformData:
    def test_column_parsing(self):
        csv = (
            "AREA_CODE,BLOCK_NUMBER,WATER_DEPTH,INSTALL_DATE\nGC,237,1200.5,01/15/2005"
        )
        zip_data = _create_test_zip(csv)
        processor = MemoryProcessor(use_optimized=False)
        result = processor.process_platform_data(zip_data, {})
        assert len(result) == 1
        df = list(result.values())[0]["data"]
        assert "AREA_CODE" in df.columns
        assert "WATER_DEPTH" in df.columns

    def test_date_coercion(self):
        csv = "INSTALL_DATE,REMOVAL_DATE\n01/15/2005,"
        zip_data = _create_test_zip(csv)
        processor = MemoryProcessor(use_optimized=False)
        result = processor.process_platform_data(zip_data, {})
        df = list(result.values())[0]["data"]
        assert pd.api.types.is_datetime64_any_dtype(df["INSTALL_DATE"])

    def test_numeric_casting(self):
        csv = "WATER_DEPTH,LATITUDE,LONGITUDE\n1200.5,28.123,-89.456"
        zip_data = _create_test_zip(csv)
        processor = MemoryProcessor(use_optimized=False)
        result = processor.process_platform_data(zip_data, {})
        df = list(result.values())[0]["data"]
        assert df["WATER_DEPTH"].dtype in ["float64", "float32"]


class TestProcessPipelinePermitData:
    def test_column_parsing(self):
        csv = "SEGMENT_NUM,PPL_SIZE_CODE,MAOP_PRSS,STATUS_CODE\n12345,105,1480.0,ACT"
        zip_data = _create_test_zip(csv)
        processor = MemoryProcessor(use_optimized=False)
        result = processor.process_pipeline_permit_data(zip_data, {})
        assert len(result) == 1
        df = list(result.values())[0]["data"]
        assert "MAOP_PRSS" in df.columns

    def test_maop_numeric(self):
        csv = "MAOP_PRSS,SEG_LENGTH\n1480.0,12.5"
        zip_data = _create_test_zip(csv)
        processor = MemoryProcessor(use_optimized=False)
        result = processor.process_pipeline_permit_data(zip_data, {})
        df = list(result.values())[0]["data"]
        assert df["MAOP_PRSS"].iloc[0] == 1480.0


class TestProcessDeepwaterStructureData:
    def test_column_parsing(self):
        csv = "AREA_CODE,BLOCK_NUMBER,WATER_DEPTH,PERMIT_NUMBER\nMC,252,5000.0,P-1234"
        zip_data = _create_test_zip(csv)
        processor = MemoryProcessor(use_optimized=False)
        result = processor.process_deepwater_structure_data(zip_data, {})
        assert len(result) == 1


class TestProcessPipelineLocationData:
    def test_column_parsing(self):
        csv = "SEGMENT_NUM,POINT_NUM,LATITUDE,LONGITUDE,WATER_DEPTH\n12345,1,28.123,-89.456,500.0"
        zip_data = _create_test_zip(csv)
        processor = MemoryProcessor(use_optimized=False)
        result = processor.process_pipeline_location_data(zip_data, {})
        df = list(result.values())[0]["data"]
        assert "LATITUDE" in df.columns
        assert df["POINT_NUM"].iloc[0] == 1

    def test_numeric_casting(self):
        csv = "POINT_NUM,LATITUDE,LONGITUDE,WATER_DEPTH\n1,28.123,-89.456,500.0"
        zip_data = _create_test_zip(csv)
        processor = MemoryProcessor(use_optimized=False)
        result = processor.process_pipeline_location_data(zip_data, {})
        df = list(result.values())[0]["data"]
        assert df["WATER_DEPTH"].dtype in ["float64", "float32"]
