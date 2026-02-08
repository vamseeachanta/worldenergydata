"""
Tests for SME Financial Analysis Module
Tests module structure, configuration loading, and basic functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path
import yaml
import pandas as pd
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / 'src'))


class TestSMEFinancialModuleStructure(unittest.TestCase):
    """Test SME Financial module structure and imports"""
    
    def test_module_imports(self):
        """Test that all SME financial modules can be imported"""
        try:
            from worldenergydata.bsee.analysis import financial
            self.assertIsNotNone(financial)
        except ImportError as e:
            self.skipTest(f"SME Financial module not yet created: {e}")
    
    def test_submodule_imports(self):
        """Test that all submodules can be imported"""
        submodules = [
            'sme_analyzer',
            'sme_cli', 
            'sme_data_loader',
            'lease_grouper',
            'drilling_completion',
            'cash_flow_calculator',
            'report_generator',
            'config_loader'
        ]
        
        for submodule in submodules:
            try:
                module = __import__(
                    f'worldenergydata.bsee.analysis.financial.{submodule}',
                    fromlist=[submodule]
                )
                self.assertIsNotNone(module)
            except ImportError:
                self.skipTest(f"Submodule {submodule} not yet created")
    
    def test_comprehensive_imports(self):
        """Test that SME module can import from comprehensive reports"""
        try:
            from worldenergydata.bsee.reports.comprehensive.data_loader_enhanced import HierarchicalDataLoader
            from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import PriceDeck, CostStructure
            from worldenergydata.bsee.reports.comprehensive.exporters.excel_exporter import ExcelExporter
            
            self.assertIsNotNone(HierarchicalDataLoader)
            self.assertIsNotNone(PriceDeck)
            self.assertIsNotNone(CostStructure)
        except ImportError as e:
            self.skipTest(f"Comprehensive report imports not available: {e}")


class TestSMEConfiguration(unittest.TestCase):
    """Test SME Financial configuration loading"""
    
    def setUp(self):
        """Set up test configuration"""
        self.test_config = {
            'financial': {
                'lease_groups': {
                    'STONES': ['G03608', 'G04003'],
                    'CASCADE_CHINOOK': ['G25488', 'G25492'],
                    'JULIA': ['G24030', 'G24041'],
                    'ANCHOR': ['G34628', 'G34631']
                },
                'economic_parameters': {
                    'oil_price_usd': 50.00,
                    'gas_price_usd_mcf': 3.00,
                    'discount_rate': 0.10,
                    'tax_rate': 0.35,
                    'royalty_rate': 0.1875
                },
                'drilling_costs': {
                    'rig_rate_usd_per_day': 300000,
                    'completion_rate_usd_per_day': 400000
                }
            }
        }
    
    def test_config_structure(self):
        """Test configuration has required structure"""
        config = self.test_config['financial']
        
        # Check main sections exist
        self.assertIn('lease_groups', config)
        self.assertIn('economic_parameters', config)
        self.assertIn('drilling_costs', config)
        
        # Check lease groups
        self.assertIsInstance(config['lease_groups'], dict)
        self.assertGreater(len(config['lease_groups']), 0)
        
        # Check economic parameters
        params = config['economic_parameters']
        self.assertIn('oil_price_usd', params)
        self.assertIn('gas_price_usd_mcf', params)
        self.assertIn('discount_rate', params)
        self.assertIn('tax_rate', params)
        self.assertIn('royalty_rate', params)
        
        # Check drilling costs
        costs = config['drilling_costs']
        self.assertIn('rig_rate_usd_per_day', costs)
        self.assertIn('completion_rate_usd_per_day', costs)
    
    def test_config_loader(self):
        """Test configuration loader functionality"""
        try:
            from worldenergydata.bsee.analysis.financial.config_loader import SMEConfigLoader
            
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = yaml.dump(self.test_config)
                
                loader = SMEConfigLoader()
                config = loader.load_config('test_config.yaml')
                
                self.assertIsNotNone(config)
                self.assertIn('financial', config)
        except ImportError:
            self.skipTest("Config loader not yet created")
    
    def test_lease_group_mapping(self):
        """Test lease group mapping functionality"""
        config = self.test_config['financial']
        lease_groups = config['lease_groups']
        
        # Test that each group has leases
        for group_name, leases in lease_groups.items():
            self.assertIsInstance(leases, list)
            self.assertGreater(len(leases), 0)
            
            # Test lease format (should start with G)
            for lease in leases:
                self.assertTrue(lease.startswith('G'), f"Lease {lease} should start with 'G'")
    
    def test_economic_parameters_validation(self):
        """Test validation of economic parameters"""
        params = self.test_config['financial']['economic_parameters']
        
        # Test parameter ranges
        self.assertGreater(params['oil_price_usd'], 0)
        self.assertGreater(params['gas_price_usd_mcf'], 0)
        self.assertGreaterEqual(params['discount_rate'], 0)
        self.assertLessEqual(params['discount_rate'], 1)
        self.assertGreaterEqual(params['tax_rate'], 0)
        self.assertLessEqual(params['tax_rate'], 1)
        self.assertGreaterEqual(params['royalty_rate'], 0)
        self.assertLessEqual(params['royalty_rate'], 1)


class TestSMEDataLoader(unittest.TestCase):
    """Test SME Data Loader functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.test_production_data = pd.DataFrame({
            'YearMonth': pd.date_range('2020-01-01', periods=12, freq='MS'),
            'WELL_1': np.random.uniform(100, 1000, 12),
            'WELL_2': np.random.uniform(100, 1000, 12)
        })
    
    def test_data_loader_creation(self):
        """Test SME data loader can be created"""
        try:
            from worldenergydata.bsee.analysis.financial.sme_data_loader import SMEDataLoader
            loader = SMEDataLoader()
            self.assertIsNotNone(loader)
        except ImportError:
            self.skipTest("SME data loader not yet created")
    
    def test_comprehensive_loader_import(self):
        """Test that SME loader uses comprehensive data loader"""
        try:
            from worldenergydata.bsee.analysis.financial.sme_data_loader import SMEDataLoader
            from worldenergydata.bsee.reports.comprehensive.data_loader_enhanced import HierarchicalDataLoader
            
            loader = SMEDataLoader()
            # Should have a reference to comprehensive loader
            self.assertIsNotNone(loader.data_loader)
            self.assertIsInstance(loader.data_loader, HierarchicalDataLoader)
        except ImportError:
            self.skipTest("Loaders not yet created")
    
    @patch('pandas.read_excel')
    def test_matrix_production_loading(self, mock_read_excel):
        """Test loading matrix-style production data"""
        mock_read_excel.return_value = self.test_production_data
        
        try:
            from worldenergydata.bsee.analysis.financial.sme_data_loader import SMEDataLoader
            
            loader = SMEDataLoader()
            data = loader.load_matrix_production('test.xlsx')
            
            self.assertIsNotNone(data)
            self.assertIsInstance(data, pd.DataFrame)
            self.assertIn('YearMonth', data.columns)
        except ImportError:
            self.skipTest("SME data loader not yet created")


class TestLeaseGrouper(unittest.TestCase):
    """Test Lease Grouper functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.group_config = {
            'STONES': ['G03608', 'G04003'],
            'CASCADE_CHINOOK': ['G25488', 'G25492']
        }
        
        self.test_data = pd.DataFrame({
            'LEASE_NUMBER': ['G03608', 'G04003', 'G25488', 'G25492', 'G12345'],
            'PRODUCTION': [1000, 2000, 1500, 2500, 500]
        })
    
    def test_lease_grouper_creation(self):
        """Test lease grouper can be created"""
        try:
            from worldenergydata.bsee.analysis.financial.lease_grouper import LeaseGrouper
            grouper = LeaseGrouper(self.group_config)
            self.assertIsNotNone(grouper)
        except ImportError:
            self.skipTest("Lease grouper not yet created")
    
    def test_apply_grouping(self):
        """Test applying lease grouping to data"""
        try:
            from worldenergydata.bsee.analysis.financial.lease_grouper import LeaseGrouper
            
            grouper = LeaseGrouper(self.group_config)
            grouped_data = grouper.apply_lease_grouping(self.test_data)
            
            self.assertIsNotNone(grouped_data)
            # Should have group names
            self.assertIn('GROUP_NAME', grouped_data.columns)
        except ImportError:
            self.skipTest("Lease grouper not yet created")


class TestCashFlowCalculator(unittest.TestCase):
    """Test Cash Flow Calculator functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.production_data = pd.DataFrame({
            'YearMonth': pd.date_range('2020-01-01', periods=12, freq='MS'),
            'OIL_BBL': np.random.uniform(1000, 5000, 12),
            'GAS_MCF': np.random.uniform(5000, 20000, 12)
        })
        
        self.drilling_costs = pd.DataFrame({
            'YearMonth': pd.date_range('2019-10-01', periods=3, freq='MS'),
            'DRILLING_COST': [1000000, 1500000, 2000000]
        })
    
    def test_cash_flow_calculator_creation(self):
        """Test cash flow calculator can be created"""
        try:
            from worldenergydata.bsee.analysis.financial.cash_flow_calculator import CashFlowCalculator
            from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import PriceDeck, CostStructure
            
            calculator = CashFlowCalculator(PriceDeck(), CostStructure())
            self.assertIsNotNone(calculator)
        except ImportError:
            self.skipTest("Cash flow calculator not yet created")
    
    def test_monthly_cash_flow_calculation(self):
        """Test monthly cash flow calculation"""
        try:
            from worldenergydata.bsee.analysis.financial.cash_flow_calculator import CashFlowCalculator
            from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import PriceDeck, CostStructure
            
            calculator = CashFlowCalculator(PriceDeck(), CostStructure())
            cash_flow = calculator.calculate_monthly_cash_flow(
                self.production_data, 
                self.drilling_costs
            )
            
            self.assertIsNotNone(cash_flow)
            self.assertIn('YearMonth', cash_flow.columns)
            self.assertIn('NET_CASH_FLOW', cash_flow.columns)
        except ImportError:
            self.skipTest("Cash flow calculator not yet created")
    
    def test_npv_calculation(self):
        """Test NPV calculation"""
        try:
            from worldenergydata.bsee.analysis.financial.cash_flow_calculator import CashFlowCalculator
            from worldenergydata.bsee.reports.comprehensive.hierarchical_aggregator import PriceDeck, CostStructure
            
            calculator = CashFlowCalculator(PriceDeck(), CostStructure())
            
            # Create simple cash flow
            cash_flow = pd.DataFrame({
                'YearMonth': pd.date_range('2020-01-01', periods=12, freq='MS'),
                'NET_CASH_FLOW': [1000000] * 12
            })
            
            npv = calculator.calculate_npv(cash_flow, discount_rate=0.10)
            
            self.assertIsNotNone(npv)
            self.assertIsInstance(npv, (int, float))
            self.assertGreater(npv, 0)
        except ImportError:
            self.skipTest("Cash flow calculator not yet created")


if __name__ == '__main__':
    unittest.main()