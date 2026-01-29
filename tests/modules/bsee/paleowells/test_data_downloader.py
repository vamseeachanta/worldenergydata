"""
Tests for the BSEE Data Downloader.
"""

import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from worldenergydata.modules.bsee.paleowells.data_downloader import BSEEDataDownloader


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def downloader(temp_dir):
    """Create a BSEEDataDownloader instance."""
    return BSEEDataDownloader(temp_dir)


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = Mock()
    response.status_code = 200
    response.headers = {
        "content-length": "1024",
        "last-modified": "Mon, 01 Jan 2024 00:00:00 GMT",
    }
    response.iter_content = Mock(return_value=[b"test data chunk"])
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def sample_zip_file(temp_dir):
    """Create a sample ZIP file for testing."""
    zip_path = temp_dir / "test.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test_file1.txt", "Test content 1")
        zf.writestr("test_file2.csv", "Test content 2")

    return zip_path


class TestBSEEDataDownloader:
    """Test suite for BSEEDataDownloader."""

    def test_initialization(self, downloader, temp_dir):
        """Test downloader initialization."""
        assert downloader.data_directory == temp_dir
        assert downloader.download_timeout == 300
        assert downloader.chunk_size == 8192
        assert temp_dir.exists()

    def test_data_sources_defined(self, downloader):
        """Test that data sources are properly defined."""
        assert "borehole" in downloader.DATA_SOURCES
        assert "company" in downloader.DATA_SOURCES
        assert "lease_owner" in downloader.DATA_SOURCES
        assert "production" in downloader.DATA_SOURCES
        assert "field" in downloader.DATA_SOURCES

        # Check structure of data sources
        for name, info in downloader.DATA_SOURCES.items():
            assert "url" in info
            assert "description" in info
            assert info["url"].startswith("https://")

    @patch("requests.get")
    def test_download_file_success(self, mock_get, downloader, temp_dir, mock_response):
        """Test successful file download."""
        mock_get.return_value = mock_response

        output_path = temp_dir / "test_download.zip"
        result = downloader.download_file("http://test.com/file.zip", output_path)

        assert result is True
        assert output_path.exists()
        mock_get.assert_called_once_with(
            "http://test.com/file.zip", stream=True, timeout=300
        )

    @patch("requests.get")
    def test_download_file_skip_existing(self, mock_get, downloader, temp_dir):
        """Test skipping download of existing file."""
        # Create existing file
        existing_file = temp_dir / "existing.zip"
        existing_file.write_text("existing content")

        result = downloader.download_file(
            "http://test.com/file.zip", existing_file, overwrite=False
        )

        assert result is True
        mock_get.assert_not_called()
        assert existing_file.read_text() == "existing content"

    @patch("requests.get")
    def test_download_file_overwrite(
        self, mock_get, downloader, temp_dir, mock_response
    ):
        """Test overwriting existing file."""
        mock_get.return_value = mock_response

        # Create existing file
        existing_file = temp_dir / "existing.zip"
        existing_file.write_text("old content")

        result = downloader.download_file(
            "http://test.com/file.zip", existing_file, overwrite=True
        )

        assert result is True
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_download_file_failure(self, mock_get, downloader, temp_dir):
        """Test handling download failure."""
        mock_get.side_effect = Exception("Network error")

        output_path = temp_dir / "failed_download.zip"
        result = downloader.download_file("http://test.com/file.zip", output_path)

        assert result is False
        assert not output_path.exists()

    def test_extract_zip_success(self, downloader, sample_zip_file, temp_dir):
        """Test successful ZIP extraction."""
        extract_dir = temp_dir / "extracted"
        result = downloader.extract_zip(sample_zip_file, extract_dir)

        assert result is True
        assert (extract_dir / "test_file1.txt").exists()
        assert (extract_dir / "test_file2.csv").exists()

    def test_extract_zip_skip_existing(self, downloader, sample_zip_file, temp_dir):
        """Test skipping extraction when files exist."""
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()

        # Create existing file
        (extract_dir / "test_file1.txt").write_text("existing")

        result = downloader.extract_zip(sample_zip_file, extract_dir, overwrite=False)

        assert result is True
        assert (extract_dir / "test_file1.txt").read_text() == "existing"

    def test_extract_zip_bad_file(self, downloader, temp_dir):
        """Test handling of invalid ZIP file."""
        bad_zip = temp_dir / "bad.zip"
        bad_zip.write_text("not a zip file")

        result = downloader.extract_zip(bad_zip)

        assert result is False

    @patch("zipfile.is_zipfile", return_value=True)
    @patch(
        "worldenergydata.modules.bsee.paleowells.data_downloader.BSEEDataDownloader.download_file"
    )
    @patch(
        "worldenergydata.modules.bsee.paleowells.data_downloader.BSEEDataDownloader.extract_zip"
    )
    def test_download_dataset(
        self, mock_extract, mock_download, mock_is_zip, downloader, temp_dir
    ):
        """Test downloading a specific dataset."""
        mock_download.return_value = True
        mock_extract.return_value = True

        result = downloader.download_dataset("borehole", extract=True, overwrite=False)

        assert result["dataset"] == "borehole"
        assert result["download_success"] is True
        assert result["extract_success"] is True
        assert "url" in result
        assert "description" in result

        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    def test_download_dataset_invalid(self, downloader):
        """Test downloading invalid dataset name."""
        with pytest.raises(ValueError) as exc_info:
            downloader.download_dataset("invalid_dataset")

        assert "Unknown dataset" in str(exc_info.value)

    @patch(
        "worldenergydata.modules.bsee.paleowells.data_downloader.BSEEDataDownloader.download_dataset"
    )
    @patch("time.sleep")  # Mock sleep to speed up test
    def test_download_all_datasets(self, mock_sleep, mock_download_dataset, downloader):
        """Test downloading multiple datasets."""
        mock_download_dataset.return_value = {
            "dataset": "test",
            "download_success": True,
            "extract_success": True,
            "extracted_files": [],
        }

        results = downloader.download_all_datasets(["borehole", "company"])

        assert len(results) == 2
        assert mock_download_dataset.call_count == 2

    @patch("requests.head")
    def test_get_latest_data_info(self, mock_head, downloader):
        """Test getting dataset information."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-length": "1048576",
            "last-modified": "Mon, 01 Jan 2024 00:00:00 GMT",
        }
        mock_head.return_value = mock_response

        info = downloader.get_latest_data_info()

        assert "borehole" in info
        assert info["borehole"]["available"] is True
        assert info["borehole"]["size"] == "1048576"
        assert "last_modified" in info["borehole"]

    @patch("requests.head")
    def test_get_latest_data_info_failure(self, mock_head, downloader):
        """Test handling failures when getting dataset info."""
        mock_head.side_effect = Exception("Network error")

        info = downloader.get_latest_data_info()

        assert "borehole" in info
        assert info["borehole"]["available"] is False
        assert "error" in info["borehole"]
