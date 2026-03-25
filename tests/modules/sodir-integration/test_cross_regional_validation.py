"""
Cross-regional data compatibility tests between SODIR and BSEE data.

Validates that Norwegian Continental Shelf data integrates seamlessly
with US Gulf of Mexico data for comparative analysis.
"""

import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
from sodir_module.analysis import SodirAnalysis

# Import SODIR components
from sodir_module.cross_regional import CrossRegionalAnalyzer
from sodir_module.datasets import DatasetGenerator
from sodir_module.processors.block_processor import BlockProcessor
from sodir_module.processors.field_processor import FieldProcessor
from sodir_module.processors.wellbore_processor import WellboreProcessor


class TestCrossRegionalValidation(unittest.TestCase):
    """Test cross-regional data compatibility between SODIR and BSEE."""

    def setUp(self):
        """Set up test data for both regions."""
        # SODIR (Norwegian) test data
        self.sodir_blocks = [
            {
                "blockId": "NOR_BLOCK_001",
                "blockName": "Block 31/2",
                "quadrantId": 31,
                "status": "ACTIVE",
                "coordinates": {"utmZone": 31, "northing": 6500000, "easting": 500000},
                "waterDepth": 350,
                "region": "NORWEGIAN_CONTINENTAL_SHELF",
            }
        ]

        self.sodir_wellbores = [
            {
                "wellboreId": "NOR_WELL_001",
                "wellboreName": "31/2-1",
                "blockId": "NOR_BLOCK_001",
                "totalDepthMd": 3500,  # meters
                "waterDepth": 350,  # meters
                "status": "PRODUCING",
                "drillingOperator": "Equinor",
                "completionDate": "2020-06-15",
                "region": "NORWAY",
            }
        ]

        self.sodir_fields = [
            {
                "fieldId": "NOR_FIELD_001",
                "fieldName": "Johan Sverdrup",
                "blockId": "NOR_BLOCK_001",
                "originalOilInPlaceSm3": 500000000,  # Sm³
                "originalGasInPlaceSm3": 100000000,  # Sm³
                "remainingOilSm3": 400000000,
                "remainingGasSm3": 80000000,
                "status": "PRODUCING",
                "discoveryYear": 2010,
                "productionStartYear": 2019,
                "region": "NORWAY",
            }
        ]

        # BSEE (US Gulf of Mexico) test data - mock format
        self.bsee_blocks = [
            {
                "block_id": "US_BLOCK_001",
                "block_number": "MC 778",
                "area_code": "MC",
                "status": "ACTIVE",
                "latitude": 28.5,
                "longitude": -88.2,
                "water_depth_ft": 1150,  # feet
                "region": "GULF_OF_MEXICO",
            }
        ]

        self.bsee_wellbores = [
            {
                "well_id": "US_WELL_001",
                "well_name": "MC 778 #1",
                "block_id": "US_BLOCK_001",
                "total_depth_ft": 11500,  # feet
                "water_depth_ft": 1150,  # feet
                "status": "ACTIVE",
                "operator": "Shell",
                "completion_date": "2020-03-20",
                "region": "USA",
            }
        ]

        self.bsee_fields = [
            {
                "field_id": "US_FIELD_001",
                "field_name": "Appomattox",
                "block_id": "US_BLOCK_001",
                "original_oil_bbl": 3145000000,  # barrels
                "original_gas_mcf": 3530000000,  # MCF
                "remaining_oil_bbl": 2500000000,
                "remaining_gas_mcf": 2800000000,
                "status": "PRODUCING",
                "discovery_year": 2009,
                "production_start_year": 2019,
                "region": "USA",
            }
        ]

    def test_data_normalization(self):
        """Test that data from both regions can be normalized to common format."""
        analyzer = CrossRegionalAnalyzer()

        # Normalize SODIR data
        normalized_sodir_fields = analyzer.normalize_fields(
            self.sodir_fields, source="SODIR"
        )

        # Normalize BSEE data
        normalized_bsee_fields = analyzer.normalize_fields(
            self.bsee_fields, source="BSEE"
        )

        # Check common fields exist in both
        common_fields = [
            "field_id",
            "field_name",
            "original_oil_bbl",
            "original_gas_bcf",
            "remaining_oil_bbl",
            "remaining_gas_bcf",
            "status",
            "discovery_year",
            "region",
            "source",
        ]

        for field in common_fields:
            self.assertIn(field, normalized_sodir_fields[0])
            self.assertIn(field, normalized_bsee_fields[0])

        # Verify unit conversions
        # SODIR: 500M Sm³ * 6.29 = ~3145M barrels
        self.assertAlmostEqual(
            normalized_sodir_fields[0]["original_oil_bbl"],
            500000000 * 6.29,
            delta=1000000,
        )

        # BSEE: Already in barrels
        self.assertEqual(normalized_bsee_fields[0]["original_oil_bbl"], 3145000000)

    def test_wellbore_data_compatibility(self):
        """Test wellbore data compatibility between regions."""
        analyzer = CrossRegionalAnalyzer()

        # Normalize wellbores
        normalized_sodir = analyzer.normalize_wellbores(
            self.sodir_wellbores, source="SODIR"
        )

        normalized_bsee = analyzer.normalize_wellbores(
            self.bsee_wellbores, source="BSEE"
        )

        # Check depth conversions
        # SODIR: 3500 meters * 3.28084 = ~11483 feet
        self.assertAlmostEqual(
            normalized_sodir[0]["total_depth_ft"], 3500 * 3.28084, delta=1
        )

        # Check water depth conversions
        # SODIR: 350 meters * 3.28084 = ~1148 feet
        self.assertAlmostEqual(
            normalized_sodir[0]["water_depth_ft"], 350 * 3.28084, delta=1
        )

        # Both should have status normalized
        self.assertIn("status_normalized", normalized_sodir[0])
        self.assertIn("status_normalized", normalized_bsee[0])

    def test_block_data_compatibility(self):
        """Test block data compatibility with coordinate systems."""
        analyzer = CrossRegionalAnalyzer()

        # Process SODIR blocks (convert UTM to lat/lon)
        processor = BlockProcessor()
        processed_sodir_blocks = processor.process_batch(self.sodir_blocks)

        # Normalize both datasets
        normalized_sodir = analyzer.normalize_blocks(
            processed_sodir_blocks, source="SODIR"
        )

        normalized_bsee = analyzer.normalize_blocks(self.bsee_blocks, source="BSEE")

        # Both should have lat/lon coordinates
        for block in normalized_sodir + normalized_bsee:
            self.assertIn("latitude", block)
            self.assertIn("longitude", block)
            self.assertIn("water_depth_m", block)
            self.assertIn("water_depth_ft", block)

        # Verify water depth conversions
        # BSEE: 1150 feet / 3.28084 = ~350 meters
        self.assertAlmostEqual(
            normalized_bsee[0]["water_depth_m"], 1150 / 3.28084, delta=1
        )

    def test_production_data_alignment(self):
        """Test that production data can be aligned for comparison."""
        analyzer = CrossRegionalAnalyzer()

        # Create production time series for both regions
        sodir_production = pd.DataFrame(
            {
                "date": pd.date_range("2020-01", periods=12, freq="M"),
                "field_id": "NOR_FIELD_001",
                "oil_production_sm3": np.random.uniform(100000, 150000, 12),
                "gas_production_sm3": np.random.uniform(50000, 70000, 12),
            }
        )

        bsee_production = pd.DataFrame(
            {
                "date": pd.date_range("2020-01", periods=12, freq="M"),
                "field_id": "US_FIELD_001",
                "oil_production_bbl": np.random.uniform(630000, 945000, 12),
                "gas_production_mcf": np.random.uniform(177000, 248000, 12),
            }
        )

        # Align production data
        aligned_sodir = analyzer.align_production_data(sodir_production, source="SODIR")
        aligned_bsee = analyzer.align_production_data(bsee_production, source="BSEE")

        # Both should have common units
        self.assertIn("oil_production_bbl", aligned_sodir.columns)
        self.assertIn("oil_production_bbl", aligned_bsee.columns)
        self.assertIn("gas_production_bcf", aligned_sodir.columns)
        self.assertIn("gas_production_bcf", aligned_bsee.columns)

        # Check date alignment
        self.assertTrue(aligned_sodir["date"].equals(aligned_bsee["date"]))

    def test_cross_regional_metrics(self):
        """Test calculation of cross-regional comparison metrics."""
        analyzer = CrossRegionalAnalyzer()

        # Normalize both datasets
        normalized_sodir_fields = analyzer.normalize_fields(
            self.sodir_fields, source="SODIR"
        )

        normalized_bsee_fields = analyzer.normalize_fields(
            self.bsee_fields, source="BSEE"
        )

        # Calculate comparison metrics
        metrics = analyzer.calculate_comparison_metrics(
            normalized_sodir_fields, normalized_bsee_fields
        )

        # Verify metrics structure
        self.assertIn("sodir", metrics)
        self.assertIn("bsee", metrics)
        self.assertIn("comparison", metrics)

        # Check SODIR metrics
        self.assertIn("total_fields", metrics["sodir"])
        self.assertIn("total_original_oil_bbl", metrics["sodir"])
        self.assertIn("avg_field_size_bbl", metrics["sodir"])

        # Check BSEE metrics
        self.assertIn("total_fields", metrics["bsee"])
        self.assertIn("total_original_oil_bbl", metrics["bsee"])
        self.assertIn("avg_field_size_bbl", metrics["bsee"])

        # Check comparison metrics
        self.assertIn("oil_reserves_ratio", metrics["comparison"])
        self.assertIn("gas_reserves_ratio", metrics["comparison"])
        self.assertIn("avg_field_size_ratio", metrics["comparison"])

    def test_discovery_timeline_compatibility(self):
        """Test that discovery timelines can be compared."""
        analyzer = CrossRegionalAnalyzer()

        # Create discovery data for both regions
        sodir_discoveries = [
            {
                "discovery_year": 2010,
                "field_name": "Johan Sverdrup",
                "recoverable_oil_sm3": 500000000,
            },
            {
                "discovery_year": 2011,
                "field_name": "Johan Castberg",
                "recoverable_oil_sm3": 100000000,
            },
            {
                "discovery_year": 2012,
                "field_name": "Wisting",
                "recoverable_oil_sm3": 75000000,
            },
        ]

        bsee_discoveries = [
            {
                "discovery_year": 2009,
                "field_name": "Appomattox",
                "recoverable_oil_bbl": 3145000000,
            },
            {
                "discovery_year": 2010,
                "field_name": "Vito",
                "recoverable_oil_bbl": 300000000,
            },
            {
                "discovery_year": 2012,
                "field_name": "Anchor",
                "recoverable_oil_bbl": 440000000,
            },
        ]

        # Align discovery timelines
        aligned_timeline = analyzer.align_discovery_timelines(
            sodir_discoveries, bsee_discoveries
        )

        # Verify timeline structure
        self.assertIn("year", aligned_timeline.columns)
        self.assertIn("sodir_discoveries", aligned_timeline.columns)
        self.assertIn("bsee_discoveries", aligned_timeline.columns)
        self.assertIn("sodir_volume_bbl", aligned_timeline.columns)
        self.assertIn("bsee_volume_bbl", aligned_timeline.columns)

        # Check year range covers both datasets
        years = aligned_timeline["year"].values
        self.assertIn(2009, years)
        self.assertIn(2012, years)

    def test_operator_mapping(self):
        """Test operator name mapping between regions."""
        analyzer = CrossRegionalAnalyzer()

        # Test operator normalization
        operator_map = {
            "Equinor": ["Equinor", "Statoil", "StatoilHydro"],
            "Shell": ["Shell", "Royal Dutch Shell", "Shell Oil"],
            "BP": ["BP", "British Petroleum", "BP America"],
            "TotalEnergies": ["Total", "TotalEnergies", "Total E&P"],
        }

        # Normalize operator names
        sodir_operators = ["Equinor", "Statoil", "Total"]
        bsee_operators = ["Shell Oil", "BP America", "Chevron"]

        normalized_sodir = analyzer.normalize_operator_names(
            sodir_operators, operator_map
        )

        normalized_bsee = analyzer.normalize_operator_names(
            bsee_operators, operator_map
        )

        # Check normalization
        self.assertIn("Equinor", normalized_sodir)
        self.assertIn("Shell", normalized_bsee)
        self.assertIn("BP", normalized_bsee)

    def test_data_quality_validation(self):
        """Test data quality validation for cross-regional analysis."""
        analyzer = CrossRegionalAnalyzer()

        # Validate SODIR data quality
        sodir_quality = analyzer.validate_data_quality(
            self.sodir_fields, source="SODIR"
        )

        # Validate BSEE data quality
        bsee_quality = analyzer.validate_data_quality(self.bsee_fields, source="BSEE")

        # Check quality metrics
        for quality in [sodir_quality, bsee_quality]:
            self.assertIn("completeness", quality)
            self.assertIn("validity", quality)
            self.assertIn("consistency", quality)
            self.assertGreaterEqual(quality["completeness"], 0)
            self.assertLessEqual(quality["completeness"], 1)

    def test_cross_regional_aggregation(self):
        """Test aggregation of data across regions."""
        analyzer = CrossRegionalAnalyzer()

        # Combine and aggregate data
        all_fields = analyzer.aggregate_cross_regional(
            self.sodir_fields, self.bsee_fields
        )

        # Verify aggregation
        self.assertIn("total_fields", all_fields)
        self.assertIn("by_region", all_fields)
        self.assertIn("by_status", all_fields)
        self.assertIn("by_year", all_fields)

        # Check regional breakdown
        self.assertIn("NORWAY", all_fields["by_region"])
        self.assertIn("USA", all_fields["by_region"])

        # Check status breakdown
        self.assertIn("PRODUCING", all_fields["by_status"])

    def test_unit_conversion_accuracy(self):
        """Test accuracy of unit conversions between regions."""
        analyzer = CrossRegionalAnalyzer()

        # Test oil conversions
        oil_sm3 = 1000000  # 1 million Sm³
        oil_bbl = analyzer.convert_oil_to_barrels(oil_sm3, from_unit="sm3")
        expected_bbl = oil_sm3 * 6.29
        self.assertAlmostEqual(oil_bbl, expected_bbl, delta=100)

        # Test gas conversions
        gas_sm3 = 1000000000  # 1 billion Sm³
        gas_bcf = analyzer.convert_gas_to_bcf(gas_sm3, from_unit="sm3")
        expected_bcf = gas_sm3 / 1000000000 * 35.3
        self.assertAlmostEqual(gas_bcf, expected_bcf, delta=0.1)

        # Test depth conversions
        depth_m = 1000  # 1000 meters
        depth_ft = analyzer.convert_depth_to_feet(depth_m, from_unit="meters")
        expected_ft = depth_m * 3.28084
        self.assertAlmostEqual(depth_ft, expected_ft, delta=0.1)

    def test_statistical_comparison(self):
        """Test statistical comparison between regions."""
        analyzer = CrossRegionalAnalyzer()

        # Create sample data for statistical comparison
        sodir_recovery_factors = np.random.uniform(0.3, 0.6, 20)
        bsee_recovery_factors = np.random.uniform(0.25, 0.55, 25)

        # Perform statistical comparison
        comparison = analyzer.statistical_comparison(
            sodir_recovery_factors, bsee_recovery_factors, metric="recovery_factor"
        )

        # Check statistical results
        self.assertIn("sodir_mean", comparison)
        self.assertIn("bsee_mean", comparison)
        self.assertIn("sodir_std", comparison)
        self.assertIn("bsee_std", comparison)
        self.assertIn("t_statistic", comparison)
        self.assertIn("p_value", comparison)
        self.assertIn("significant_difference", comparison)

        # Verify statistical calculations
        self.assertAlmostEqual(
            comparison["sodir_mean"], np.mean(sodir_recovery_factors), delta=0.01
        )
        self.assertAlmostEqual(
            comparison["bsee_mean"], np.mean(bsee_recovery_factors), delta=0.01
        )

    def test_temporal_alignment(self):
        """Test temporal alignment of data from different regions."""
        analyzer = CrossRegionalAnalyzer()

        # Create time series with different frequencies
        sodir_monthly = pd.DataFrame(
            {
                "date": pd.date_range("2020-01", periods=12, freq="M"),
                "production": np.random.uniform(100000, 150000, 12),
            }
        )

        bsee_quarterly = pd.DataFrame(
            {
                "date": pd.date_range("2020-01", periods=4, freq="Q"),
                "production": np.random.uniform(300000, 450000, 4),
            }
        )

        # Align to common frequency
        aligned_sodir, aligned_bsee = analyzer.align_temporal_data(
            sodir_monthly, bsee_quarterly, target_freq="Q"
        )

        # Both should have same length and frequency
        self.assertEqual(len(aligned_sodir), len(aligned_bsee))
        self.assertEqual(len(aligned_sodir), 4)  # Quarterly

        # Check aggregation correctness
        # Monthly to quarterly should sum 3 months
        expected_q1 = sodir_monthly.iloc[0:3]["production"].sum()
        self.assertAlmostEqual(
            aligned_sodir.iloc[0]["production"], expected_q1, delta=1000
        )


class TestDataIntegrityValidation(unittest.TestCase):
    """Test data integrity between SODIR and BSEE systems."""

    def test_referential_integrity(self):
        """Test referential integrity in cross-regional datasets."""
        # Create related datasets
        blocks = pd.DataFrame(
            {
                "block_id": ["B001", "B002", "B003"],
                "region": ["NORWAY", "NORWAY", "USA"],
            }
        )

        fields = pd.DataFrame(
            {
                "field_id": ["F001", "F002", "F003"],
                "block_id": ["B001", "B002", "B004"],  # B004 doesn't exist
                "region": ["NORWAY", "NORWAY", "USA"],
            }
        )

        analyzer = CrossRegionalAnalyzer()

        # Check referential integrity
        integrity_issues = analyzer.check_referential_integrity(
            blocks, fields, "block_id"
        )

        # Should identify orphaned reference
        self.assertIn("orphaned_references", integrity_issues)
        self.assertIn("B004", integrity_issues["orphaned_references"])

    def test_duplicate_detection(self):
        """Test detection of duplicate entries across regions."""
        analyzer = CrossRegionalAnalyzer()

        # Create data with potential duplicates
        all_fields = [
            {"field_id": "F001", "field_name": "Johan Sverdrup", "region": "NORWAY"},
            {
                "field_id": "F002",
                "field_name": "Johan Sverdrup",
                "region": "NORWAY",
            },  # Duplicate name
            {"field_id": "F003", "field_name": "Appomattox", "region": "USA"},
        ]

        # Detect duplicates
        duplicates = analyzer.detect_duplicates(all_fields, key="field_name")

        # Should identify duplicate
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["field_name"], "Johan Sverdrup")

    def test_data_consistency(self):
        """Test data consistency across regions."""
        analyzer = CrossRegionalAnalyzer()

        # Create inconsistent data
        field_summary = {
            "field_id": "F001",
            "total_wells": 10,
            "producing_wells": 12,  # Inconsistent: more producing than total
            "plugged_wells": 2,
        }

        # Check consistency
        consistency_issues = analyzer.check_consistency(field_summary)

        # Should identify inconsistency
        self.assertIn("well_count_mismatch", consistency_issues)
        self.assertTrue(consistency_issues["well_count_mismatch"])


if __name__ == "__main__":
    unittest.main()
