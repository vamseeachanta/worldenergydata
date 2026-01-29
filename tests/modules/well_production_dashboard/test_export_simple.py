"""
Simple test to verify export manager is working
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from worldenergydata.modules.well_production_dashboard.export_manager import (
    ExportConfiguration,
    ExportResult,
    VerificationMetadata,
)


def test_export_configuration():
    """Test export configuration"""
    config = ExportConfiguration(formats=["pdf", "excel"], include_verification=True)
    assert config.formats == ["pdf", "excel"]
    assert config.include_verification == True
    print("✓ Export configuration test passed")


def test_verification_metadata():
    """Test verification metadata"""
    metadata = VerificationMetadata(quality_score=0.95, anomalies_detected=2)
    assert metadata.quality_score == 0.95
    assert metadata.anomalies_detected == 2

    data = metadata.to_dict()
    assert "quality_score" in data
    print("✓ Verification metadata test passed")


def test_export_result():
    """Test export result"""
    result = ExportResult(success=True, format="pdf", file_path="/path/to/file.pdf")
    assert result.success == True
    assert result.format == "pdf"
    print("✓ Export result test passed")


if __name__ == "__main__":
    test_export_configuration()
    test_verification_metadata()
    test_export_result()
    print("\nAll tests passed successfully!")
