"""
Block-level data aggregator
Aggregates field-level data up to block level
"""

from typing import Dict, Any, List, Optional
from datetime import date
import logging

from .base import DataAggregator
from ..models import (
    HierarchyLevel, ProductionMetrics, EconomicMetrics,
    Block, Field
)


logger = logging.getLogger(__name__)


class BlockAggregator(DataAggregator):
    """Aggregator for block-level data"""
    
    def __init__(self):
        """Initialize BlockAggregator"""
        super().__init__()
        self.hierarchy_level = HierarchyLevel.BLOCK
    
    def get_hierarchy_level(self) -> HierarchyLevel:
        """Get hierarchy level"""
        return self.hierarchy_level
    
    def aggregate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate field data to block level
        
        Args:
            data: Dictionary containing 'block' key with Block object
            
        Returns:
            Aggregated metrics for the block
        """
        if not self.validate(data):
            logger.error("Invalid data provided to BlockAggregator")
            return {}
        
        block = data.get('block')
        if not isinstance(block, Block):
            logger.error(f"Expected Block object, got {type(block)}")
            return {}
        
        # Initialize aggregation results
        result = {
            'oil_bbls': 0,
            'gas_mcf': 0,
            'water_bbls': 0,
            'field_count': 0,
            'total_lease_count': 0,
            'total_well_count': 0,
            'active_well_count': 0,
            'revenue': 0,
            'operating_cost': 0,
            'fields': []
        }
        
        # Aggregate from fields
        for field in block.children:
            if isinstance(field, Field):
                result['field_count'] += 1
                
                # Get field production (either from total_production or by aggregating)
                if hasattr(field, 'total_production') and field.total_production:
                    prod_data = field.total_production
                else:
                    # Trigger field aggregation if needed
                    prod_data = field.aggregate_production()
                
                # Sum production
                result['oil_bbls'] += prod_data.get('oil_bbls', 0)
                result['gas_mcf'] += prod_data.get('gas_mcf', 0)
                result['water_bbls'] += prod_data.get('water_bbls', 0)
                
                # Count leases and wells
                result['total_lease_count'] += field.get_lease_count()
                
                # Count wells in field
                well_count = 0
                active_well_count = 0
                for lease in field.children:
                    if hasattr(lease, 'children'):
                        for well in lease.children:
                            well_count += 1
                            if hasattr(well, 'status') and well.status == 'active':
                                active_well_count += 1
                
                result['total_well_count'] += well_count
                result['active_well_count'] += active_well_count
                
                # Store field info
                field_info = {
                    'id': field.id,
                    'name': field.name,
                    'oil_bbls': prod_data.get('oil_bbls', 0),
                    'gas_mcf': prod_data.get('gas_mcf', 0),
                    'lease_count': field.get_lease_count()
                }
                result['fields'].append(field_info)
        
        # Calculate revenue if price deck provided
        if 'price_deck' in data:
            revenue_costs = self.aggregate_revenue_costs(block, data['price_deck'])
            result.update(revenue_costs)
        
        # Store in block
        block.total_production = {
            'oil_bbls': result['oil_bbls'],
            'gas_mcf': result['gas_mcf'],
            'water_bbls': result['water_bbls']
        }
        
        # Cache results
        cache_key = f"block_{block.id}"
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
        
        if 'block' not in data:
            self.add_validation_error("Missing 'block' key in data")
            return False
        
        block = data.get('block')
        if not isinstance(block, Block):
            self.add_validation_error(f"Invalid block type: {type(block)}")
            return False
        
        return True
    
    def calculate_metrics(self, data: Dict[str, Any]) -> ProductionMetrics:
        """
        Calculate production metrics for block
        
        Args:
            data: Block data
            
        Returns:
            ProductionMetrics object
        """
        block = data.get('block')
        if not block:
            return ProductionMetrics()
        
        # Get cached results or aggregate
        cache_key = f"block_{block.id}"
        if cache_key in self.cached_results:
            agg_data = self.cached_results[cache_key]
        else:
            agg_data = self.aggregate(data)
        
        metrics = ProductionMetrics(
            entity_id=block.id,
            entity_type="block",
            oil_production_bbls=agg_data.get('oil_bbls', 0),
            gas_production_mcf=agg_data.get('gas_mcf', 0),
            water_production_bbls=agg_data.get('water_bbls', 0),
            active_well_count=agg_data.get('active_well_count', 0)
        )
        
        # Sync volume aliases
        metrics.oil_volume_bbl = metrics.oil_production_bbls
        metrics.gas_volume_mcf = metrics.gas_production_mcf
        
        return metrics
    
    def aggregate_fields_with_rollup(self, block: Block, 
                                    include_economics: bool = True) -> Dict[str, Any]:
        """
        Aggregate fields with detailed rollup information
        
        Args:
            block: Block to aggregate
            include_economics: Whether to include economic calculations
            
        Returns:
            Detailed aggregation with rollup info
        """
        rollup = {
            'block_id': block.id,
            'block_name': block.name,
            'fields': [],
            'totals': {
                'oil_bbls': 0,
                'gas_mcf': 0,
                'water_bbls': 0,
                'revenue': 0,
                'operating_cost': 0,
                'net_income': 0
            }
        }
        
        for field in block.children:
            if isinstance(field, Field):
                field_data = {
                    'field_id': field.id,
                    'field_name': field.name,
                    'production': field.aggregate_production(),
                    'lease_count': field.get_lease_count()
                }
                
                # Add to totals
                for key in ['oil_bbls', 'gas_mcf', 'water_bbls']:
                    rollup['totals'][key] += field_data['production'].get(key, 0)
                
                # Calculate field economics if requested
                if include_economics:
                    oil_revenue = field_data['production'].get('oil_bbls', 0) * 75.0
                    gas_revenue = field_data['production'].get('gas_mcf', 0) * 3.5
                    field_data['revenue'] = oil_revenue + gas_revenue
                    field_data['operating_cost'] = field_data['production'].get('oil_bbls', 0) * 12.5
                    field_data['net_income'] = field_data['revenue'] - field_data['operating_cost']
                    
                    rollup['totals']['revenue'] += field_data['revenue']
                    rollup['totals']['operating_cost'] += field_data['operating_cost']
                    rollup['totals']['net_income'] += field_data['net_income']
                
                rollup['fields'].append(field_data)
        
        return rollup