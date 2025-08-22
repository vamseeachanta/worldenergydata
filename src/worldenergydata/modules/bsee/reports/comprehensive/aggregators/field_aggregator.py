"""
Field-level data aggregator
Aggregates lease-level data up to field level
"""

from typing import Dict, Any, List, Optional
from datetime import date
import logging

from .base import DataAggregator
from ..models import (
    HierarchyLevel, ProductionMetrics, EconomicMetrics,
    Field, Lease, Well
)


logger = logging.getLogger(__name__)


class FieldAggregator(DataAggregator):
    """Aggregator for field-level data"""
    
    def __init__(self):
        """Initialize FieldAggregator"""
        super().__init__()
        self.hierarchy_level = HierarchyLevel.FIELD
    
    def get_hierarchy_level(self) -> HierarchyLevel:
        """Get hierarchy level"""
        return self.hierarchy_level
    
    def aggregate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate lease data to field level
        
        Args:
            data: Dictionary containing 'field' key with Field object
            
        Returns:
            Aggregated metrics for the field
        """
        if not self.validate(data):
            logger.error("Invalid data provided to FieldAggregator")
            return {}
        
        field = data.get('field')
        if not isinstance(field, Field):
            logger.error(f"Expected Field object, got {type(field)}")
            return {}
        
        # Initialize aggregation results
        result = {
            'oil_bbls': 0,
            'gas_mcf': 0,
            'water_bbls': 0,
            'lease_count': 0,
            'total_well_count': 0,
            'active_well_count': 0,
            'average_water_depth': 0,
            'leases': [],
            'peak_oil_rate': 0,
            'peak_gas_rate': 0
        }
        
        water_depths = []
        
        # Aggregate from leases
        for lease in field.children:
            if isinstance(lease, Lease):
                result['lease_count'] += 1
                
                # Get lease production
                if hasattr(lease, 'total_production') and lease.total_production:
                    prod_data = lease.total_production
                else:
                    # Trigger lease aggregation if needed
                    prod_data = lease.aggregate_production()
                
                # Sum production
                result['oil_bbls'] += prod_data.get('oil_bbls', 0)
                result['gas_mcf'] += prod_data.get('gas_mcf', 0)
                result['water_bbls'] += prod_data.get('water_bbls', 0)
                
                # Count wells
                well_count = lease.get_well_count()
                result['total_well_count'] += well_count
                
                # Count active wells and track water depth
                active_count = 0
                for well in lease.children:
                    if isinstance(well, Well):
                        if hasattr(well, 'status') and well.status == 'active':
                            active_count += 1
                        if hasattr(well, 'water_depth_ft') and well.water_depth_ft:
                            water_depths.append(well.water_depth_ft)
                
                result['active_well_count'] += active_count
                
                # Track lease info
                lease_info = {
                    'id': lease.id,
                    'number': lease.number,
                    'oil_bbls': prod_data.get('oil_bbls', 0),
                    'gas_mcf': prod_data.get('gas_mcf', 0),
                    'well_count': well_count,
                    'active_wells': active_count
                }
                result['leases'].append(lease_info)
        
        # Calculate average water depth
        if water_depths:
            result['average_water_depth'] = sum(water_depths) / len(water_depths)
        
        # Calculate peak rates (simplified - would need time series data in reality)
        if result['total_well_count'] > 0:
            result['peak_oil_rate'] = result['oil_bbls'] / (result['total_well_count'] * 365)
            result['peak_gas_rate'] = result['gas_mcf'] / (result['total_well_count'] * 365)
        
        # Store in field
        field.total_production = {
            'oil_bbls': result['oil_bbls'],
            'gas_mcf': result['gas_mcf'],
            'water_bbls': result['water_bbls']
        }
        
        # Cache results
        cache_key = f"field_{field.id}"
        self.cached_results[cache_key] = result
        
        return result
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate input data
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        self.clear_validation_errors()
        
        if not data:
            self.add_validation_error("Empty data provided")
            return False
        
        if 'field' not in data:
            self.add_validation_error("Missing 'field' key in data")
            return False
        
        field = data.get('field')
        if not isinstance(field, Field):
            self.add_validation_error(f"Invalid field type: {type(field)}")
            return False
        
        return True
    
    def calculate_metrics(self, data: Dict[str, Any]) -> ProductionMetrics:
        """
        Calculate production metrics for field
        
        Args:
            data: Field data
            
        Returns:
            ProductionMetrics object
        """
        field = data.get('field')
        if not field:
            return ProductionMetrics()
        
        # Get cached results or aggregate
        cache_key = f"field_{field.id}"
        if cache_key in self.cached_results:
            agg_data = self.cached_results[cache_key]
        else:
            agg_data = self.aggregate(data)
        
        metrics = ProductionMetrics(
            entity_id=field.id,
            entity_type="field",
            oil_production_bbls=agg_data.get('oil_bbls', 0),
            gas_production_mcf=agg_data.get('gas_mcf', 0),
            water_production_bbls=agg_data.get('water_bbls', 0),
            active_well_count=agg_data.get('active_well_count', 0)
        )
        
        # Sync volume aliases
        metrics.oil_volume_bbl = metrics.oil_production_bbls
        metrics.gas_volume_mcf = metrics.gas_production_mcf
        
        return metrics
    
    def aggregate_with_well_summation(self, field: Field) -> Dict[str, Any]:
        """
        Aggregate field with direct well summation (bypassing lease level)
        
        Args:
            field: Field to aggregate
            
        Returns:
            Aggregated data with well details
        """
        result = {
            'field_id': field.id,
            'field_name': field.name,
            'wells': [],
            'totals': {
                'oil_bbls': 0,
                'gas_mcf': 0,
                'water_bbls': 0,
                'well_count': 0,
                'active_wells': 0
            }
        }
        
        # Traverse all wells in field
        for lease in field.children:
            if isinstance(lease, Lease):
                for well in lease.children:
                    if isinstance(well, Well):
                        prod_data = well.get_production_data()
                        
                        well_info = {
                            'well_id': well.id,
                            'well_name': well.name,
                            'lease_number': lease.number,
                            'oil_bbls': prod_data.get('oil_bbls', 0),
                            'gas_mcf': prod_data.get('gas_mcf', 0),
                            'status': getattr(well, 'status', 'unknown')
                        }
                        
                        result['wells'].append(well_info)
                        result['totals']['oil_bbls'] += well_info['oil_bbls']
                        result['totals']['gas_mcf'] += well_info['gas_mcf']
                        result['totals']['well_count'] += 1
                        
                        if well_info['status'] == 'active':
                            result['totals']['active_wells'] += 1
        
        return result
    
    def calculate_field_economics(self, field: Field, 
                                 price_deck: Dict[str, float]) -> EconomicMetrics:
        """
        Calculate economic metrics for field
        
        Args:
            field: Field object
            price_deck: Pricing information
            
        Returns:
            EconomicMetrics object
        """
        # Get production data
        if hasattr(field, 'total_production') and field.total_production:
            prod_data = field.total_production
        else:
            agg_result = self.aggregate({'field': field})
            prod_data = {
                'oil_bbls': agg_result.get('oil_bbls', 0),
                'gas_mcf': agg_result.get('gas_mcf', 0)
            }
        
        # Calculate economics
        oil_revenue = prod_data['oil_bbls'] * price_deck.get('oil', 75.0)
        gas_revenue = prod_data['gas_mcf'] * price_deck.get('gas', 3.5)
        total_revenue = oil_revenue + gas_revenue
        
        operating_costs = prod_data['oil_bbls'] * price_deck.get('operating_cost_per_bbl', 12.5)
        royalties = total_revenue * price_deck.get('royalty_rate', 0.1875)
        
        metrics = EconomicMetrics(
            entity_id=field.id,
            entity_type="field",
            revenue=total_revenue,
            operating_costs=operating_costs,
            royalties=royalties,
            production_bbls=prod_data['oil_bbls']
        )
        metrics.calculate_net_income()
        
        return metrics