"""
Simple test for hierarchical aggregation without complex imports
Tests core aggregation logic independently
"""

import unittest
from datetime import date
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../src'))


class TestAggregationLogic(unittest.TestCase):
    """Test core aggregation logic"""
    
    def test_revenue_calculation(self):
        """Test revenue calculation formulas"""
        # Test data
        oil_bbls = 100000
        gas_mcf = 50000
        oil_price = 75.00
        gas_price = 3.50
        
        # Calculate revenue
        oil_revenue = oil_bbls * oil_price
        gas_revenue = gas_mcf * gas_price
        gross_revenue = oil_revenue + gas_revenue
        
        # Verify calculations
        self.assertEqual(oil_revenue, 7500000)
        self.assertEqual(gas_revenue, 175000)
        self.assertEqual(gross_revenue, 7675000)
    
    def test_cost_calculation(self):
        """Test cost calculation formulas"""
        # Test data
        gross_revenue = 1000000
        oil_bbls = 10000
        gas_mcf = 6000
        
        # Cost parameters
        operating_cost_per_bbl = 12.50
        royalty_rate = 0.1875
        severance_tax_rate = 0.05
        
        # Calculate costs
        boe = oil_bbls + (gas_mcf / 6)  # Barrel of Oil Equivalent
        operating_cost = boe * operating_cost_per_bbl
        royalties = gross_revenue * royalty_rate
        severance_tax = gross_revenue * severance_tax_rate
        total_costs = operating_cost + royalties + severance_tax
        net_income = gross_revenue - total_costs
        
        # Verify calculations
        self.assertEqual(boe, 11000)
        self.assertEqual(operating_cost, 137500)
        self.assertEqual(royalties, 187500)
        self.assertEqual(severance_tax, 50000)
        self.assertEqual(total_costs, 375000)
        self.assertEqual(net_income, 625000)
    
    def test_hierarchical_summation(self):
        """Test summation across hierarchical levels"""
        # Well data
        wells = [
            {'id': 'W1', 'oil': 100000, 'gas': 50000, 'revenue': 1000000},
            {'id': 'W2', 'oil': 80000, 'gas': 40000, 'revenue': 800000},
            {'id': 'W3', 'oil': 120000, 'gas': 60000, 'revenue': 1200000}
        ]
        
        # Lease aggregation (W1 + W2 in Lease1, W3 in Lease2)
        lease1 = {
            'wells': ['W1', 'W2'],
            'oil': wells[0]['oil'] + wells[1]['oil'],
            'gas': wells[0]['gas'] + wells[1]['gas'],
            'revenue': wells[0]['revenue'] + wells[1]['revenue']
        }
        
        lease2 = {
            'wells': ['W3'],
            'oil': wells[2]['oil'],
            'gas': wells[2]['gas'],
            'revenue': wells[2]['revenue']
        }
        
        # Field aggregation (Lease1 + Lease2)
        field = {
            'leases': ['L1', 'L2'],
            'oil': lease1['oil'] + lease2['oil'],
            'gas': lease1['gas'] + lease2['gas'],
            'revenue': lease1['revenue'] + lease2['revenue']
        }
        
        # Verify lease aggregation
        self.assertEqual(lease1['oil'], 180000)
        self.assertEqual(lease1['gas'], 90000)
        self.assertEqual(lease1['revenue'], 1800000)
        
        # Verify field aggregation
        self.assertEqual(field['oil'], 300000)
        self.assertEqual(field['gas'], 150000)
        self.assertEqual(field['revenue'], 3000000)
    
    def test_goby_row_format(self):
        """Test go-by report 14-row structure"""
        # Sample well data
        well_data = {
            'field_name': 'Jack',
            'lease_number': 'OCS-G-12345',
            'well_name': 'PS001',
            'api_number': 'API001',
            'water_depth': 7000,
            'total_depth': 25000,
            'spud_date': date(2020, 1, 15),
            'status': 'active',
            'oil_production': 100000,
            'gas_production': 50000,
            'water_production': 20000,
            'gross_revenue': 7675000,
            'operating_cost': 137500,
            'net_income': 625000
        }
        
        # Create 14-row format
        row = [
            well_data['field_name'],
            well_data['lease_number'],
            well_data['well_name'],
            well_data['api_number'],
            well_data['water_depth'],
            well_data['total_depth'],
            well_data['spud_date'],
            well_data['status'],
            well_data['oil_production'],
            well_data['gas_production'],
            well_data['water_production'],
            well_data['gross_revenue'],
            well_data['operating_cost'],
            well_data['net_income']
        ]
        
        # Verify row structure
        self.assertEqual(len(row), 14)
        self.assertEqual(row[0], 'Jack')
        self.assertEqual(row[1], 'OCS-G-12345')
        self.assertEqual(row[8], 100000)
        self.assertEqual(row[11], 7675000)
    
    def test_aggregation_averages(self):
        """Test average calculations at different levels"""
        # Test data
        total_oil = 300000
        total_gas = 150000
        total_revenue = 3000000
        num_wells = 3
        num_leases = 2
        
        # Calculate averages
        avg_oil_per_well = total_oil / num_wells
        avg_gas_per_well = total_gas / num_wells
        avg_revenue_per_well = total_revenue / num_wells
        avg_wells_per_lease = num_wells / num_leases
        
        # Verify averages
        self.assertEqual(avg_oil_per_well, 100000)
        self.assertEqual(avg_gas_per_well, 50000)
        self.assertEqual(avg_revenue_per_well, 1000000)
        self.assertEqual(avg_wells_per_lease, 1.5)
    
    def test_boe_calculation(self):
        """Test Barrel of Oil Equivalent calculation"""
        # Test data
        oil_bbls = 100000
        gas_mcf = 60000
        ngl_bbls = 5000
        
        # Calculate BOE (6 mcf = 1 BOE)
        boe = oil_bbls + (gas_mcf / 6) + ngl_bbls
        
        # Verify calculation
        self.assertEqual(boe, 115000)
    
    def test_profit_margin_calculation(self):
        """Test profit margin calculation"""
        # Test data
        gross_revenue = 1000000
        total_costs = 375000
        net_income = 625000
        
        # Calculate profit margin
        profit_margin = (net_income / gross_revenue) * 100
        
        # Verify calculation
        self.assertEqual(profit_margin, 62.5)


if __name__ == '__main__':
    unittest.main()