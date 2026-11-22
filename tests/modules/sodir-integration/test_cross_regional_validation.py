"""
Cross-regional data compatibility tests between SODIR and BSEE data.

Validates that Norwegian Continental Shelf data integrates seamlessly
with US Gulf of Mexico data for comparative analysis.
"""

import json
import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from worldenergydata.sodir.analysis import SodirAnalysis

# Import SODIR components
from worldenergydata.sodir.cross_regional import CrossRegionalAnalyzer
from worldenergydata.sodir.datasets import DatasetGenerator
from worldenergydata.sodir.processors.block_processor import BlockProcessor
from worldenergydata.sodir.processors.field_processor import FieldProcessor
from worldenergydata.sodir.processors.wellbore_processor import WellboreProcessor


class TestCrossRegionalValidation(unittest.TestCase):
    """Test cross-regional data compatibility between SODIR and BSEE."""

    def setUp(self):
        """Set up test data for both regions."""
        # SODIR (Norwegian) test data
        self.sodir_blocks = [
            {
                "blcNpdidBlock": "NOR_BLOCK_001",
                "blcName": "31/2",
                "quadrantId": 31,
                "status": "ACTIVE",
                "coordinates": {"utmZone": 31, "northing": 6500000, "easting": 500000},
                "waterDepth": 350,
                "region": "NORWEGIAN_CONTINENTAL_SHELF",
            }
        ]

        self.sodir_wellbores = [
            {
                "wlbNpdidWellbore": "NOR_WELL_001",
                "wlbName": "31/2-1",
                "blockId": "NOR_BLOCK_001",
                "wlbTotalDepth": 3500,  # meters
                "wlbWaterDepth": 350,  # meters
                "wlbStatus": "PRODUCING",
                "wlbDrillingOperator": "Operator A",
                "completionDate": "2020-06-15",
                "region": "NORWAY",
            }
        ]

        self.sodir_fields = [
            {
                "fldNpdidField": "NOR_FIELD_001",
                "fldName": "Field A",
                "blockId": "NOR_BLOCK_001",
                "fldOriginalReservesOil": 500,  # Million Sm³
                "fldOriginalReservesGas": 0.1,  # Billion Sm³
                "fldRemainingReservesOil": 400,
                "fldRemainingReservesGas": 0.08,
                "fldRecoverableOil": 500,
                "fldRecoverableGas": 0.1,
                "fldStatus": "PRODUCING",
                "fldDiscoveryYear": 2010,
                "fldWaterDepth": 350,
                "fldProductionStartYear": 2019,
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
                "operator": "Operator B",
                "completion_date": "2020-03-20",
                "region": "USA",
            }
        ]

        self.bsee_fields = [
            {
                "field_id": "US_FIELD_001",
                "field_name": "Field B",
                "block_id": "US_BLOCK_001",
                "oil_reserves_mmbbl": 3145,
                "gas_reserves_bcf": 3.53,
                "remaining_reserves_oil_mmbbl": 2500,
                "remaining_reserves_gas_bcf": 2.8,
                "water_depth_ft": 1150,
                "recovery_factor": 0.2,
                "status": "PRODUCING",
                "discovery_year": 2009,
                "production_start_year": 2019,
                "region": "USA",
            }
        ]

    def field_frame(self, source):
        """Provide the processed DataFrame accepted by the canonical analyzer."""
        if source == "BSEE":
            return pd.DataFrame(self.bsee_fields)
        return pd.DataFrame(FieldProcessor().process_batch(self.sodir_fields)).rename(
            columns={
                "recovery_factor_oil": "recovery_factor",
            }
        )

    def test_data_normalization(self):
        """Test that data from both regions can be normalized to common format."""
        analyzer = CrossRegionalAnalyzer()

        # Normalize SODIR data
        normalized_sodir_fields = analyzer.normalize_fields(
            self.field_frame("SODIR"), source="SODIR"
        )

        # Normalize BSEE data
        normalized_bsee_fields = analyzer.normalize_fields(
            self.field_frame("BSEE"), source="BSEE"
        )

        # Check common fields exist in both
        common_fields = [
            "field_id",
            "field_name",
            "oil_reserves_mmbbl",
            "gas_reserves_bcf",
            "remaining_reserves_oil_mmbbl",
            "remaining_reserves_gas_bcf",
            "water_depth_m",
            "total_boe_mmboe",
            "status",
            "discovery_year",
            "region",
        ]

        for field in common_fields:
            self.assertIn(field, normalized_sodir_fields.columns)
            self.assertIn(field, normalized_bsee_fields.columns)

        # Verify unit conversions
        # Fixture hand count: 500 million Sm³ at the processor's 6.29 gives 3145.
        self.assertAlmostEqual(
            normalized_sodir_fields.iloc[0]["oil_reserves_mmbbl"],
            3145.0,
            delta=0.01,
        )
        # Fixture hand count: 0.1 billion Sm³ at 35.3 gives 3.53 billion ft³.
        self.assertAlmostEqual(
            normalized_sodir_fields.iloc[0]["gas_reserves_bcf"], 3.53, delta=0.01
        )
        self.assertEqual(normalized_bsee_fields.iloc[0]["oil_reserves_mmbbl"], 3145.0)
        # Fixture hand calculation: 400 million Sm³ * 6.29 = 2516 million barrels.
        self.assertEqual(
            normalized_sodir_fields.iloc[0]["remaining_reserves_oil_mmbbl"], 2516.0
        )
        self.assertEqual(
            normalized_bsee_fields.iloc[0]["remaining_reserves_oil_mmbbl"], 2500.0
        )

    def test_wellbore_data_compatibility(self):
        """Test wellbore data compatibility between regions."""
        analyzer = CrossRegionalAnalyzer()

        # Normalize wellbores
        processed_sodir = pd.DataFrame(
            WellboreProcessor().process_batch(self.sodir_wellbores)
        )
        normalized_sodir = analyzer.normalize_data(
            {"wellbores": processed_sodir}, source="SODIR"
        )["wellbores"]
        normalized_bsee = analyzer.normalize_data(
            {"wellbores": pd.DataFrame(self.bsee_wellbores)}, source="BSEE"
        )["wellbores"]

        # Check depth conversions
        # SODIR: 3500 meters * 3.28084 = ~11483 feet
        self.assertAlmostEqual(
            normalized_sodir.iloc[0]["total_depth_ft"], 11482.94, delta=0.01
        )

        # Check water depth conversions
        # SODIR: 350 meters * 3.28084 = ~1148 feet
        self.assertAlmostEqual(
            normalized_sodir.iloc[0]["water_depth_ft"], 1148.29, delta=0.01
        )

        self.assertEqual(normalized_sodir.iloc[0]["status_normalized"], "PRODUCING")
        # The analyzer converts the BSEE depth to its canonical metre column.
        self.assertAlmostEqual(normalized_bsee.iloc[0]["depth_m"], 3505.2, delta=0.01)
        self.assertEqual(normalized_bsee.iloc[0]["region"], "BSEE")
        self.assertEqual(normalized_bsee.iloc[0]["status"], "ACTIVE")

    def test_block_data_compatibility(self):
        """Test block data compatibility with coordinate systems."""
        analyzer = CrossRegionalAnalyzer()

        # Process SODIR blocks (convert UTM to lat/lon)
        processor = BlockProcessor()
        processed_sodir_blocks = processor.process_batch(self.sodir_blocks)

        # Normalize both datasets
        normalized_sodir = analyzer.normalize_blocks(
            pd.DataFrame(processed_sodir_blocks).assign(water_depth_m=350),
            source="SODIR",
        )

        normalized_bsee = analyzer.normalize_blocks(
            pd.DataFrame(self.bsee_blocks).rename(
                columns={"water_depth_ft": "water_depth"}
            ),
            source="BSEE",
        )

        # Both should have lat/lon coordinates
        for blocks in (normalized_sodir, normalized_bsee):
            self.assertIn("lat", blocks.columns)
            self.assertIn("lon", blocks.columns)
            self.assertIn("water_depth", blocks.columns)
            self.assertTrue(blocks[["lat", "lon", "water_depth"]].notna().all().all())

        # Verify water depth conversions
        # BSEE: 1150 feet / 3.28084 = ~350 meters
        self.assertAlmostEqual(
            normalized_bsee.iloc[0]["water_depth"], 350.52, delta=0.01
        )

    def test_production_data_alignment(self):
        """Test that production data can be aligned for comparison."""
        analyzer = CrossRegionalAnalyzer()

        # Create production time series for both regions
        sodir_production = pd.DataFrame(
            {
                "date": pd.date_range("2020-01", periods=12, freq="ME"),
                "field_id": "NOR_FIELD_001",
                "oil_production_mmbbl": np.full(12, 1.0),
                "gas_production_bcf": np.full(12, 6.0),
            }
        )

        bsee_production = pd.DataFrame(
            {
                "date": pd.date_range("2020-01", periods=12, freq="ME"),
                "field_id": "US_FIELD_001",
                "oil_production_mmbbl": np.full(12, 2.0),
                "gas_production_bcf": np.full(12, 12.0),
            }
        )

        # Align production data
        aligned_sodir = analyzer.normalize_data(
            {"production": sodir_production}, source="SODIR"
        )["production"]
        aligned_bsee = analyzer.normalize_data(
            {"production": bsee_production}, source="BSEE"
        )["production"]

        # Both should have common units
        self.assertIn("oil_production_mmbbl", aligned_sodir.columns)
        self.assertIn("oil_production_mmbbl", aligned_bsee.columns)
        self.assertIn("gas_production_bcf", aligned_sodir.columns)
        self.assertIn("gas_production_bcf", aligned_bsee.columns)

        # Check date alignment
        self.assertTrue(aligned_sodir["date"].equals(aligned_bsee["date"]))
        # Fixture hand calculation: oil + gas/6 gives 2 and 4 million BOE.
        self.assertTrue((aligned_sodir["production_boe"] == 2.0).all())
        self.assertTrue((aligned_bsee["production_boe"] == 4.0).all())

    def test_cross_regional_metrics(self):
        """Test calculation of cross-regional comparison metrics."""
        analyzer = CrossRegionalAnalyzer()

        # Normalize both datasets
        normalized_sodir_fields = analyzer.normalize_fields(
            self.field_frame("SODIR"), source="SODIR"
        )

        normalized_bsee_fields = analyzer.normalize_fields(
            self.field_frame("BSEE"), source="BSEE"
        )

        # Calculate comparison metrics
        sodir_metrics = analyzer.calculate_metrics(
            {"fields": normalized_sodir_fields}, region="SODIR"
        )
        bsee_metrics = analyzer.calculate_metrics(
            {"fields": normalized_bsee_fields}, region="BSEE"
        )
        comparison = analyzer.compare_regions(sodir_metrics, bsee_metrics)

        # Verify metrics structure
        for metrics in (sodir_metrics, bsee_metrics):
            self.assertEqual(metrics.total_fields, 1)
            self.assertEqual(metrics.total_oil_reserves_mmbbl, 3145.0)
            self.assertAlmostEqual(metrics.total_gas_reserves_bcf, 3.53, delta=0.01)
        self.assertAlmostEqual(comparison.metrics_diff["recovery_factor_diff"], 0.0)
        self.assertAlmostEqual(comparison.metrics_diff["field_size_diff_mmboe"], 0.0)

    def test_discovery_timeline_compatibility(self):
        """Test that discovery timelines can be compared."""
        analyzer = CrossRegionalAnalyzer()

        # Create discovery data for both regions
        sodir_discoveries = [
            {
                "discovery_year": 2010,
                "field_name": "Field A",
                "recoverable_oil_sm3": 500000000,
            },
            {
                "discovery_year": 2011,
                "field_name": "Field C",
                "recoverable_oil_sm3": 100000000,
            },
            {
                "discovery_year": 2012,
                "field_name": "Field D",
                "recoverable_oil_sm3": 75000000,
            },
        ]

        bsee_discoveries = [
            {
                "discovery_year": 2009,
                "field_name": "Field B",
                "recoverable_oil_bbl": 3145000000,
            },
            {
                "discovery_year": 2010,
                "field_name": "Field E",
                "recoverable_oil_bbl": 300000000,
            },
            {
                "discovery_year": 2012,
                "field_name": "Field F",
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
        annual = aligned_timeline.set_index("year")
        self.assertEqual(annual.index.tolist(), [2009, 2010, 2011, 2012])
        self.assertEqual(annual["sodir_discoveries"].tolist(), [0, 1, 1, 1])
        self.assertEqual(annual["bsee_discoveries"].tolist(), [1, 1, 0, 1])
        # Hand calculations on the existing fixture basis: 500, 100 and 75
        # million Sm³ at 6.29 yield 3145, 629 and 471.75 million barrels.
        np.testing.assert_allclose(
            annual["sodir_volume_bbl"], [0, 3145000000, 629000000, 471750000]
        )
        self.assertEqual(
            annual["bsee_volume_bbl"].tolist(), [3145000000, 300000000, 0, 440000000]
        )

    def test_operator_mapping(self):
        """Test operator name mapping between regions."""
        analyzer = CrossRegionalAnalyzer()

        # Test operator normalization
        operator_map = {
            "Operator A": ["Operator A", "Operator A Legacy", "Operator A Historic"],
            "Operator B": ["Operator B", "Operator B Legacy", "Operator B Oil"],
            "Operator C": ["Operator C", "Operator C Legacy", "Operator C Regional"],
            "Operator D": ["Operator D", "Operator D Legacy", "Operator D Regional"],
        }

        # Normalize operator names
        sodir_operators = ["Operator A", "Operator A Legacy", "Operator D Legacy"]
        bsee_operators = ["Operator B Oil", "Operator C Regional", "Operator E"]

        normalized_sodir = analyzer.normalize_operator_names(
            sodir_operators, operator_map
        )

        normalized_bsee = analyzer.normalize_operator_names(
            bsee_operators, operator_map
        )

        # Check normalization
        self.assertIn("Operator A", normalized_sodir)
        self.assertIn("Operator B", normalized_bsee)
        self.assertIn("Operator C", normalized_bsee)
        self.assertEqual(normalized_sodir, ["Operator A", "Operator A", "Operator D"])
        self.assertEqual(normalized_bsee, ["Operator B", "Operator C", "Operator E"])

    def test_data_quality_validation(self):
        """Test data quality validation for cross-regional analysis."""
        analyzer = CrossRegionalAnalyzer()

        nullable_sodir_fields = {
            "operator",
            "owner_kind",
            "ownership_share",
            "cessation_year",
            "original_reserves_ngl_mmbbl",
            "original_reserves_condensate_mmbbl",
            "remaining_reserves_ngl_mmbbl",
            "remaining_reserves_condensate_mmbbl",
            "recoverable_ngl_mmbbl",
            "recoverable_condensate_mmbbl",
            "cumulative_oil_production_mmbbl",
            "cumulative_gas_production_bcf",
            "cumulative_ngl_production_mmbbl",
            "cumulative_condensate_production_mmbbl",
            "cumulative_water_injected_sm3",
            "main_supply_base",
            "main_area",
            "geometry",
            "date_updated",
            "oil_production_efficiency",
        }
        for source in ("SODIR", "BSEE"):
            frame = self.field_frame(source)
            nullable_fields = nullable_sodir_fields if source == "SODIR" else set()
            quality = analyzer.validate_data_quality(frame, data_type="fields")
            self.assertEqual(quality["total_records"], 1)
            self.assertEqual(
                quality["completeness"],
                {
                    column: 0.0 if column in nullable_fields else 100.0
                    for column in frame.columns
                },
            )
            self.assertEqual(
                quality["issues"],
                [
                    f"Column '{column}' has low completeness: 0.0%"
                    for column in frame.columns
                    if column in nullable_fields
                ],
            )
            expected_score = (
                100.0 * (len(frame.columns) - len(nullable_fields)) / len(frame.columns)
            )
            self.assertAlmostEqual(quality["quality_score"], expected_score)

    def test_cross_regional_aggregation(self):
        """Test aggregation of data across regions."""
        analyzer = CrossRegionalAnalyzer()

        # Combine and aggregate data
        all_fields = analyzer.aggregate_cross_regional(
            analyzer.normalize_fields(self.field_frame("SODIR"), source="SODIR"),
            analyzer.normalize_fields(self.field_frame("BSEE"), source="BSEE"),
        )

        # Verify aggregation
        self.assertEqual(len(all_fields), 2)
        self.assertIn("status", all_fields.columns)
        self.assertIn("discovery_year", all_fields.columns)

        # Check regional breakdown
        self.assertEqual(set(all_fields["region"]), {"SODIR", "BSEE"})

        # Check status breakdown
        self.assertTrue((all_fields["status"] == "PRODUCING").all())
        self.assertEqual(all_fields["oil_reserves"].sum(), 6290.0)
        self.assertEqual(
            all_fields.groupby("status").size().to_dict(), {"PRODUCING": 2}
        )
        self.assertEqual(
            all_fields.groupby("discovery_year").size().to_dict(), {2009: 1, 2010: 1}
        )

    def test_unit_conversion_accuracy(self):
        """Test accuracy of unit conversions between regions."""
        converted = FieldProcessor().process(
            {
                "fldName": "Field A",
                "fldOriginalReservesOil": 1,
                "fldOriginalReservesGas": 1,
            }
        )
        # Hand calculations using the existing processor fixture basis:
        # 1 million Sm³ oil * 6.29 = 6.29 million barrels;
        # 1 billion Sm³ gas * 35.3 = 35.3 billion ft³;
        # 1000 m * 3.28084 = 3280.84 ft.
        self.assertAlmostEqual(
            converted["original_reserves_oil_mmbbl"], 6.29, delta=0.0001
        )
        self.assertAlmostEqual(converted["original_reserves_gas_bcf"], 35.3, delta=0.01)
        self.assertAlmostEqual(
            WellboreProcessor().meters_to_feet(1000), 3280.84, delta=0.01
        )

    def test_statistical_comparison(self):
        """Test statistical comparison between regions."""
        analyzer = CrossRegionalAnalyzer()

        # Create sample data for statistical comparison
        sodir_recovery_factors = np.linspace(0.3, 0.6, 20)
        bsee_recovery_factors = np.linspace(0.25, 0.55, 25)

        # Perform statistical comparison
        comparison = analyzer.perform_statistical_tests(
            pd.DataFrame({"recovery_factor": sodir_recovery_factors}),
            pd.DataFrame({"recovery_factor": bsee_recovery_factors}),
            variables=["recovery_factor"],
        )["recovery_factor"]

        # Check statistical results
        self.assertIn("sodir_mean", comparison)
        self.assertIn("bsee_mean", comparison)
        self.assertIn("sodir_std", comparison)
        self.assertIn("bsee_std", comparison)
        self.assertIn("t_statistic", comparison)
        self.assertIn("t_test_p_value", comparison)
        self.assertGreaterEqual(comparison["t_test_p_value"], 0.0)
        self.assertLessEqual(comparison["t_test_p_value"], 1.0)

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
                "date": pd.date_range("2020-01", periods=12, freq="ME"),
                "production": np.random.uniform(100000, 150000, 12),
            }
        )

        bsee_quarterly = pd.DataFrame(
            {
                "date": pd.date_range("2020-01", periods=4, freq="QE"),
                "production": np.random.uniform(300000, 450000, 4),
            }
        )

        # Align to common frequency
        aligned_sodir, aligned_bsee = analyzer.align_temporal_data(
            sodir_monthly, bsee_quarterly, target_freq="QE"
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
        self.assertEqual(integrity_issues["checked_references"], 3)
        self.assertEqual(integrity_issues["orphaned_record_count"], 1)
        self.assertTrue(integrity_issues["applicable"])

    def test_duplicate_detection(self):
        """Test detection of duplicate entries across regions."""
        analyzer = CrossRegionalAnalyzer()

        # Create data with potential duplicates
        all_fields = [
            {"field_id": "F001", "field_name": "Field A", "region": "NORWAY"},
            {
                "field_id": "F002",
                "field_name": "Field A",
                "region": "NORWAY",
            },  # Duplicate name
            {"field_id": "F003", "field_name": "Field B", "region": "USA"},
        ]

        # Detect duplicates
        quality = analyzer.validate_data_quality(
            pd.DataFrame(all_fields), data_type="fields"
        )

        # Should identify duplicate
        self.assertEqual(quality["issues"], ["Found 1 duplicate records"])
        self.assertEqual(quality["quality_score"], 90.0)
        clean_quality = analyzer.validate_data_quality(
            pd.DataFrame([all_fields[0], all_fields[2]]), data_type="fields"
        )
        self.assertEqual(clean_quality["issues"], [])
        self.assertEqual(clean_quality["quality_score"], 100.0)

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
        self.assertEqual(consistency_issues["total_wells"], 10)
        self.assertEqual(consistency_issues["accounted_wells"], 14)


def _compatibility_time_frames():
    monthly = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-31", periods=6, freq="ME"),
            "production": [1, 2, 3, 4, 5, 6],
            "temperature": [5, 7, 9, 11, 13, 15],
        }
    )
    quarterly = pd.DataFrame(
        {
            "date": pd.date_range("2020-03-31", periods=2, freq="QE"),
            "production": [30, 60],
            "temperature": [4, 8],
        }
    )
    monthly.attrs = {"source_id": "synthetic-a", "units": {"production": "bbl"}}
    quarterly.attrs = {"source_id": "synthetic-b", "units": {"production": "bbl"}}
    return monthly, quarterly


class TestCompatibilityGuards:
    @pytest.mark.parametrize(
        "column,value",
        [
            ("discovery_year", None),
            ("discovery_year", np.nan),
            ("discovery_year", np.inf),
            ("discovery_year", 2010.5),
            ("discovery_year", True),
            ("discovery_year", "2010"),
            ("discovery_year", 0),
            ("discovery_year", 10000),
            ("recoverable_oil_sm3", None),
            ("recoverable_oil_sm3", np.nan),
            ("recoverable_oil_sm3", np.inf),
            ("recoverable_oil_sm3", -1),
            ("recoverable_oil_sm3", True),
            ("recoverable_oil_sm3", "1,000"),
            ("recoverable_oil_sm3", 1j),
            ("recoverable_oil_sm3", np.finfo(float).max),
        ],
    )
    def test_discovery_rejects_invalid_values(self, column, value):
        record = {"discovery_year": 2010, "recoverable_oil_sm3": 10}
        record[column] = value
        other = [{"discovery_year": 2010, "recoverable_oil_bbl": 1}]
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_discovery_timelines([record], other)

    @pytest.mark.parametrize("records", [None, [], [None], [{"discovery_year": 2010}]])
    def test_discovery_rejects_missing_records_or_schema(self, records):
        other = [{"discovery_year": 2010, "recoverable_oil_bbl": 1}]
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_discovery_timelines(records, other)

    def test_discovery_preserves_zero_counts_and_inputs(self):
        source = [{"discovery_year": 2010, "recoverable_oil_sm3": 0}]
        other = [{"discovery_year": 2011, "recoverable_oil_bbl": 0}]
        before = deepcopy((source, other))
        result = CrossRegionalAnalyzer().align_discovery_timelines(source, other)
        assert result["year"].tolist() == [2010, 2011]
        assert result["sodir_discoveries"].tolist() == [1, 0]
        assert result["bsee_discoveries"].tolist() == [0, 1]
        assert result["sodir_volume_bbl"].tolist() == [0, 0]
        assert result["bsee_volume_bbl"].tolist() == [0, 0]
        basis = result.attrs["discovery_alignment"]
        assert basis["source_units"] == {"SODIR": "Sm3", "BSEE": "bbl"}
        assert basis["output_unit"] == "bbl"
        assert basis["conversion_basis"] == {
            "SODIR": "FieldProcessor.SM3_TO_BARRELS",
            "BSEE": "identity",
        }
        assert basis["supplied_observations_only"] is True
        assert basis["engineering_data_readiness_established"] is False
        assert (source, other) == before

    def test_discovery_rejects_aggregate_overflow(self):
        source = [{"discovery_year": 2010, "recoverable_oil_sm3": 0}]
        other = [
            {"discovery_year": 2010, "recoverable_oil_bbl": np.finfo(float).max}
        ] * 2
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_discovery_timelines(source, other)

    @pytest.mark.parametrize("names", [None, [], "Operator A", [None], [1], [" "]])
    def test_operator_rejects_invalid_labels(self, names):
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().normalize_operator_names(
                names, {"Operator A": ["Alias A"]}
            )

    @pytest.mark.parametrize(
        "mapping",
        [
            None,
            {},
            {None: ["Alias"]},
            {"Operator A": "Alias"},
            {"Operator A": [None]},
            {"Operator A": ["Alias"], "Operator B": [" alias "]},
        ],
    )
    def test_operator_rejects_malformed_or_ambiguous_aliases(self, mapping):
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().normalize_operator_names(["Alias"], mapping)

    def test_operator_preserves_order_unknown_labels_and_inputs(self):
        names = [" alias a ", "Operator Z", "Alias A"]
        mapping = {"Operator A": ["Alias A"]}
        before = deepcopy((names, mapping))
        result = CrossRegionalAnalyzer().normalize_operator_names(names, mapping)
        assert result == ["Operator A", "Operator Z", "Operator A"]
        assert (names, mapping) == before

    def test_temporal_aggregation_preserves_values_attrs_and_basis(self):
        monthly, quarterly = _compatibility_time_frames()
        before = deepcopy((monthly, quarterly))
        aligned = CrossRegionalAnalyzer().align_temporal_data(monthly, quarterly, "QE")
        assert aligned[0]["production"].tolist() == [6, 15]
        assert aligned[0]["temperature"].tolist() == [7, 13]
        assert aligned[1]["production"].tolist() == [30, 60]
        assert aligned[1]["temperature"].tolist() == [4, 8]
        for result, original in zip(aligned, before):
            assert result["date"].tolist() == quarterly["date"].tolist()
            for key, value in original.attrs.items():
                assert result.attrs[key] == value
            basis = result.attrs["temporal_alignment"]
            assert basis["aggregation_basis"] == {
                "production": "sum",
                "temperature": "mean",
            }
            assert basis["supplied_observations_only"] is True
            assert basis["calendar_completeness_established"] is False
        pd.testing.assert_frame_equal(monthly, before[0])
        pd.testing.assert_frame_equal(quarterly, before[1])
        assert monthly.attrs == before[0].attrs
        assert quarterly.attrs == before[1].attrs

    @pytest.mark.parametrize(
        "mutation",
        [
            lambda frame: frame.drop(columns="date"),
            lambda frame: frame.assign(date=pd.NaT),
            lambda frame: frame.assign(date="not-a-date"),
            lambda frame: frame.assign(
                date=frame["date"].astype(object).mask(frame.index == 0, "")
            ),
            lambda frame: frame.assign(date=1),
            lambda frame: frame.assign(date=frame["date"].iloc[0]),
            lambda frame: frame.assign(production=np.nan),
            lambda frame: frame.assign(production=np.inf),
            lambda frame: frame.assign(production=True),
            lambda frame: frame.assign(production="unknown"),
            lambda frame: frame.assign(production=1j),
            lambda frame: frame.rename(columns={"production": "volume"}),
            lambda frame: frame.rename(columns={"temperature": "production"}),
            lambda frame: frame.iloc[:0],
        ],
    )
    def test_temporal_rejects_invalid_inputs(self, mutation):
        monthly, quarterly = _compatibility_time_frames()
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_temporal_data(
                mutation(monthly), quarterly, "QE"
            )

    @pytest.mark.parametrize("frequency", [None, "", True, "not-a-frequency"])
    def test_temporal_rejects_invalid_frequency(self, frequency):
        monthly, quarterly = _compatibility_time_frames()
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_temporal_data(monthly, quarterly, frequency)

    def test_temporal_rejects_gaps_and_nonoverlap(self):
        monthly, quarterly = _compatibility_time_frames()
        shifted = quarterly.assign(date=quarterly["date"] + pd.DateOffset(years=1))
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_temporal_data(monthly, shifted, "QE")
        monthly["date"] = [
            *pd.date_range("2020-01-31", periods=3, freq="ME"),
            *pd.date_range("2020-07-31", periods=3, freq="ME"),
        ]
        quarterly = pd.DataFrame(
            {
                "date": pd.date_range("2020-03-31", periods=3, freq="QE"),
                "production": [1, 2, 3],
                "temperature": [1, 2, 3],
            }
        )
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_temporal_data(monthly, quarterly, "QE")

    def test_temporal_rejects_timezone_and_metadata_conflicts(self):
        monthly, quarterly = _compatibility_time_frames()
        monthly["date"] = monthly["date"].dt.tz_localize("UTC")
        quarterly["date"] = quarterly["date"].dt.tz_localize("Etc/GMT-1")
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_temporal_data(monthly, quarterly, "QE")
        monthly, quarterly = _compatibility_time_frames()
        monthly.attrs["temporal_alignment"] = {"previous": True}
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().align_temporal_data(monthly, quarterly, "QE")

    def test_relationship_counts_unique_orphans_and_preserves_inputs(self):
        parents = pd.DataFrame({"block_id": ["B1", "B2"]})
        children = pd.DataFrame({"block_id": ["B2", "B9", "B9"]})
        before = deepcopy((parents, children))
        result = CrossRegionalAnalyzer().check_referential_integrity(
            parents, children, "block_id"
        )
        assert result["orphaned_references"] == ["B9"]
        assert result["orphaned_record_count"] == 2
        assert result["checked_references"] == 3
        assert result["reference_records"] == 2
        assert result["applicable"] is True
        pd.testing.assert_frame_equal(parents, before[0])
        pd.testing.assert_frame_equal(children, before[1])

    @pytest.mark.parametrize("value", [None, np.nan, np.inf, True, 1.0, [], " ", " B1"])
    def test_relationship_rejects_invalid_identifiers(self, value):
        parents = pd.DataFrame({"block_id": [value]})
        children = pd.DataFrame({"block_id": ["B1"]})
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().check_referential_integrity(
                parents, children, "block_id"
            )

    def test_relationship_rejects_missing_schema_duplicates_and_mixed_types(self):
        valid = pd.DataFrame({"block_id": ["B1"]})
        invalid_frames = [
            None,
            pd.DataFrame(),
            pd.DataFrame({"block_id": ["B1", "B1"]}),
            pd.DataFrame({"block_id": [1]}),
        ]
        for invalid in invalid_frames:
            with pytest.raises(ValueError):
                CrossRegionalAnalyzer().check_referential_integrity(
                    invalid, valid, "block_id"
                )

    def test_relationship_empty_children_are_not_an_applicable_success(self):
        parents = pd.DataFrame({"block_id": ["B1"]})
        empty = pd.DataFrame(columns=["block_id"])
        result = CrossRegionalAnalyzer().check_referential_integrity(
            parents, empty, "block_id"
        )
        assert result["applicable"] is False
        assert result["checked_references"] == 0
        assert result["orphaned_record_count"] == 0
        assert result["reason"]
        for missing in (None, pd.DataFrame()):
            with pytest.raises(ValueError):
                CrossRegionalAnalyzer().check_referential_integrity(
                    parents, missing, "block_id"
                )

    @pytest.mark.parametrize(
        "field", ["total_wells", "producing_wells", "plugged_wells"]
    )
    @pytest.mark.parametrize("value", [None, np.nan, np.inf, True, -1, 0.5, "2", 1j])
    def test_count_consistency_rejects_invalid_values(self, field, value):
        counts = {"total_wells": 10, "producing_wells": 6, "plugged_wells": 2}
        counts[field] = value
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().check_consistency(counts)

    @pytest.mark.parametrize(
        "field", ["total_wells", "producing_wells", "plugged_wells"]
    )
    def test_count_consistency_rejects_missing_counts(self, field):
        counts = {"total_wells": 10, "producing_wells": 6, "plugged_wells": 2}
        counts.pop(field)
        with pytest.raises(ValueError):
            CrossRegionalAnalyzer().check_consistency(counts)

    @pytest.mark.parametrize(
        "counts,mismatch", [((0, 0, 0), False), ((10, 6, 2), False), ((10, 8, 4), True)]
    )
    def test_count_consistency_reports_explicit_counts(self, counts, mismatch):
        summary = dict(zip(("total_wells", "producing_wells", "plugged_wells"), counts))
        result = CrossRegionalAnalyzer().check_consistency(summary)
        assert result["well_count_mismatch"] is mismatch
        assert result["total_wells"] == counts[0]
        assert result["accounted_wells"] == counts[1] + counts[2]


if __name__ == "__main__":
    unittest.main()
