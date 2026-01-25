"""
Unit tests for lease grouping functionality
Tests the grouping logic from SME V20 implementation
"""

import unittest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, date

from src.worldenergydata.modules.bsee.analysis.financial.lease_grouper import (
    LeaseGrouper,
    group_leases_by_development,
    aggregate_production_by_lease,
    map_wells_to_leases
)


class TestLeaseGrouper(unittest.TestCase):
    """Test suite for lease grouping operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.grouper = LeaseGrouper()
        
        # Sample lease data
        self.leases_df = pd.DataFrame({
            'LEASE_NUM': ['G12345', 'G23456', 'G34567', 'G45678'],
            'LEASE_NAME': ['Lease A', 'Lease B', 'Lease C', 'Lease D'],
            'DEV_NAME': ['DEV_1', 'DEV_1', 'DEV_2', 'DEV_2'],
            'DEV_TYPE_EFF': ['subsea', 'subsea', 'dry tree', 'dry tree'],
            'BLOCK': ['MC 100', 'MC 100', 'MC 200', 'MC 200']
        })
        
        # Sample well data
        self.wells_df = pd.DataFrame({
            'WELL_NAME': ['WELL_A1', 'WELL_A2', 'WELL_B1', 'WELL_C1'],
            'LEASE_NUM': ['G12345', 'G12345', 'G23456', 'G34567'],
            'API_WELL_NUMBER': ['608174001', '608174002', '608174003', '608174004'],
            'STATUS': ['ACTIVE', 'ACTIVE', 'PLUGGED', 'ACTIVE']
        })
        
        # Sample production data (matrix format)
        self.production_matrix = pd.DataFrame({
            'WELL_NAME': ['WELL_A1', 'WELL_A2', 'WELL_B1'],
            '2023-01': [1000, 800, 600],
            '2023-02': [950, 750, 550],
            '2023-03': [900, 700, 500],
            '2023-04': [850, 650, 450]
        })
        
        # Sample production data (timeseries format)
        dates = pd.date_range('2023-01-01', periods=4, freq='MS')
        self.production_timeseries = pd.DataFrame({
            'YearMonth': dates.tolist() * 3,
            'WELL_NAME': ['WELL_A1']*4 + ['WELL_A2']*4 + ['WELL_B1']*4,
            'OIL_BBL': [1000, 950, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450]
        })
    
    def test_initialization(self):
        """Test LeaseGrouper initialization"""
        self.assertIsInstance(self.grouper._groups, dict)
        self.assertIsInstance(self.grouper._well_lease_map, dict)
    
    def test_group_by_development(self):
        """Test grouping leases by development"""
        groups = self.grouper.group_by_development(self.leases_df)
        
        # Should have 2 development groups
        self.assertEqual(len(groups), 2)
        self.assertIn('DEV_1', groups)
        self.assertIn('DEV_2', groups)
        
        # Check group contents
        self.assertEqual(len(groups['DEV_1']), 2)
        self.assertEqual(len(groups['DEV_2']), 2)
        
        # Verify lease numbers in groups
        dev1_leases = groups['DEV_1']['LEASE_NUM'].tolist()
        self.assertIn('G12345', dev1_leases)
        self.assertIn('G23456', dev1_leases)
    
    def test_map_wells_to_leases(self):
        """Test mapping wells to leases"""
        well_map = self.grouper.map_wells_to_leases(self.wells_df, self.leases_df)
        
        # Check mapping structure
        self.assertIn('WELL_A1', well_map)
        self.assertIn('WELL_A2', well_map)
        
        # Verify correct lease mapping
        self.assertEqual(well_map['WELL_A1']['lease_num'], 'G12345')
        self.assertEqual(well_map['WELL_A2']['lease_num'], 'G12345')
        self.assertEqual(well_map['WELL_B1']['lease_num'], 'G23456')
        
        # Check additional info
        self.assertEqual(well_map['WELL_A1']['lease_name'], 'Lease A')
        self.assertEqual(well_map['WELL_A1']['dev_name'], 'DEV_1')
    
    def test_aggregate_production_by_lease(self):
        """Test aggregating production data by lease"""
        # Add lease mapping
        self.grouper._well_lease_map = {
            'WELL_A1': {'lease_num': 'G12345'},
            'WELL_A2': {'lease_num': 'G12345'},
            'WELL_B1': {'lease_num': 'G23456'}
        }
        
        result = self.grouper.aggregate_production_by_lease(
            self.production_timeseries,
            self.wells_df,
            self.leases_df
        )
        
        # Check structure
        self.assertIn('YearMonth', result.columns)
        self.assertIn('G12345', result.columns)
        self.assertIn('G23456', result.columns)
        
        # Verify aggregation (WELL_A1 + WELL_A2 for G12345)
        jan_2023 = result[result['YearMonth'] == '2023-01-01']
        self.assertEqual(jan_2023['G12345'].iloc[0], 1800)  # 1000 + 800
        self.assertEqual(jan_2023['G23456'].iloc[0], 600)
    
    def test_group_development_wells(self):
        """Test grouping wells by development"""
        dev_wells = self.grouper.group_development_wells(
            'DEV_1',
            self.wells_df,
            self.leases_df
        )
        
        # Should only include wells from DEV_1
        self.assertEqual(len(dev_wells), 3)  # WELL_A1, WELL_A2, WELL_B1
        self.assertIn('WELL_A1', dev_wells['WELL_NAME'].tolist())
        self.assertIn('WELL_B1', dev_wells['WELL_NAME'].tolist())
        self.assertNotIn('WELL_C1', dev_wells['WELL_NAME'].tolist())
    
    def test_create_lease_summary(self):
        """Test creating lease summary with production totals"""
        # Setup
        self.grouper._well_lease_map = {
            'WELL_A1': {'lease_num': 'G12345'},
            'WELL_A2': {'lease_num': 'G12345'},
            'WELL_B1': {'lease_num': 'G23456'}
        }
        
        summary = self.grouper.create_lease_summary(
            self.leases_df,
            self.wells_df,
            self.production_timeseries
        )
        
        # Check structure
        self.assertIn('LEASE_NUM', summary.columns)
        self.assertIn('LEASE_NAME', summary.columns)
        self.assertIn('WELL_COUNT', summary.columns)
        self.assertIn('TOTAL_PRODUCTION', summary.columns)
        self.assertIn('ACTIVE_WELLS', summary.columns)
        
        # Verify counts
        lease_a = summary[summary['LEASE_NUM'] == 'G12345']
        self.assertEqual(lease_a['WELL_COUNT'].iloc[0], 2)
        self.assertEqual(lease_a['ACTIVE_WELLS'].iloc[0], 2)
        
        # Verify production totals
        self.assertGreater(lease_a['TOTAL_PRODUCTION'].iloc[0], 0)
    
    def test_get_lease_time_range(self):
        """Test getting production time range for a lease"""
        # Setup production data with dates
        prod_data = self.production_timeseries.copy()
        
        # Map wells to lease
        self.grouper._well_lease_map = {
            'WELL_A1': {'lease_num': 'G12345'},
            'WELL_A2': {'lease_num': 'G12345'}
        }
        
        start_date, end_date = self.grouper.get_lease_time_range(
            'G12345',
            prod_data,
            self.wells_df
        )
        
        # Should return first and last production dates
        self.assertEqual(start_date, pd.Timestamp('2023-01-01'))
        self.assertEqual(end_date, pd.Timestamp('2023-04-01'))
    
    def test_filter_active_leases(self):
        """Test filtering for active leases only"""
        # Add production status
        leases_with_status = self.leases_df.copy()
        leases_with_status['PRODUCTION_STATUS'] = ['ACTIVE', 'ACTIVE', 'INACTIVE', 'PLUGGED']
        
        active_leases = self.grouper.filter_active_leases(leases_with_status)
        
        # Should only have active leases
        self.assertEqual(len(active_leases), 2)
        self.assertTrue(all(active_leases['PRODUCTION_STATUS'] == 'ACTIVE'))
    
    def test_empty_data_handling(self):
        """Test handling of empty dataframes"""
        empty_df = pd.DataFrame()
        
        # Should handle empty inputs gracefully
        groups = self.grouper.group_by_development(empty_df)
        self.assertEqual(len(groups), 0)
        
        well_map = self.grouper.map_wells_to_leases(empty_df, empty_df)
        self.assertEqual(len(well_map), 0)
    
    def test_missing_columns_handling(self):
        """Test handling of missing required columns"""
        bad_df = pd.DataFrame({'WRONG_COL': [1, 2, 3]})
        
        # Should raise or return empty based on implementation
        with self.assertRaises(KeyError):
            self.grouper.group_by_development(bad_df)


class TestLeaseGrouperAdvanced(unittest.TestCase):
    """Advanced tests for lease grouper functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.grouper = LeaseGrouper()
    
    def test_multi_block_lease_handling(self):
        """Test handling leases that span multiple blocks"""
        multi_block_leases = pd.DataFrame({
            'LEASE_NUM': ['G12345', 'G12345', 'G23456'],
            'BLOCK': ['MC 100', 'MC 101', 'MC 200'],
            'DEV_NAME': ['DEV_1', 'DEV_1', 'DEV_2']
        })
        
        groups = self.grouper.group_by_development(multi_block_leases)
        
        # Should handle duplicate lease numbers correctly
        dev1 = groups['DEV_1']
        # Implementation should either deduplicate or maintain all blocks
        self.assertIn('G12345', dev1['LEASE_NUM'].tolist())
    
    def test_production_gap_handling(self):
        """Test handling production data with gaps"""
        # Create production with gaps
        dates = pd.date_range('2023-01-01', periods=6, freq='MS')
        production_with_gaps = pd.DataFrame({
            'YearMonth': dates,
            'WELL_A1': [100, 0, 0, 50, 0, 75],  # Gaps in production
            'WELL_B1': [200, 150, 0, 0, 0, 100]
        })
        
        # Should handle zero production months
        result = self.grouper.process_production_gaps(production_with_gaps)
        self.assertIsNotNone(result)
    
    def test_normalize_lease_numbers_in_group(self):
        """Test normalization of lease numbers during grouping"""
        mixed_format_leases = pd.DataFrame({
            'LEASE_NUM': ['12345', 'G23456', ' 34567 ', 'g45678'],
            'DEV_NAME': ['DEV_1', 'DEV_1', 'DEV_2', 'DEV_2']
        })
        
        groups = self.grouper.group_by_development(mixed_format_leases, normalize=True)
        
        # All lease numbers should be normalized to G-prefix format
        for dev, group in groups.items():
            for lease_num in group['LEASE_NUM']:
                self.assertTrue(lease_num.startswith('G'))
                self.assertEqual(lease_num[0], 'G')
                self.assertTrue(lease_num[1:].isdigit())


if __name__ == '__main__':
    unittest.main()