"""
Field-level data aggregator
Aggregates lease-level data up to field level
"""

from typing import Dict, Any, List, Optional
from datetime import date
import logging
import pandas as pd

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
    
    def fetch_field_leases(self, field_name: str, cfg: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Fetch all leases for a specific field
        
        Args:
            field_name: Name of the field
            cfg: Optional configuration dictionary
            
        Returns:
            DataFrame with lease data for the field
        """
        cache_key = f"field_{field_name}_leases"
        
        if cache_key in self._field_data_cache:
            logger.info(f"Using cached lease data for field: {field_name}")
            return self._field_data_cache[cache_key]
        
        try:
            # Get all lease data and filter by field
            all_leases = self.lease_files_loader.get_all_lease_data()
            
            if not all_leases.empty and 'Field Name' in all_leases.columns:
                field_leases = all_leases[all_leases['Field Name'] == field_name]
                self._field_data_cache[cache_key] = field_leases
                return field_leases
            else:
                logger.warning(f"No lease data found for field: {field_name}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error fetching field lease data: {e}")
            return pd.DataFrame()
    
    def fetch_field_production(self, field_name: str, cfg: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Fetch production data for a specific field
        
        Args:
            field_name: Name of the field
            cfg: Optional configuration dictionary
            
        Returns:
            DataFrame with production data for the field
        """
        cache_key = f"field_{field_name}_production"
        
        if cache_key in self._production_cache:
            logger.info(f"Using cached production data for field: {field_name}")
            return self._production_cache[cache_key]
        
        try:
            # Load production data for the field
            production_data = self.enhanced_loader._load_production_data(field_name=field_name)
            
            if production_data:
                production_df = pd.DataFrame(production_data)
                self._production_cache[cache_key] = production_df
                return production_df
            else:
                logger.warning(f"No production data found for field: {field_name}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error fetching field production data: {e}")
            return pd.DataFrame()
    
    def aggregate_with_fresh_data(self, field_names: List[str], 
                                  cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Aggregate data with fresh fetch from BSEE sources
        
        Args:
            field_names: List of field names to aggregate
            cfg: Optional configuration dictionary
            
        Returns:
            Aggregated field-level metrics
        """
        # Refresh data if needed
        if cfg:
            self.enhanced_loader.refresh_data_if_needed(cfg)
        
        aggregated = {
            'fields': {},
            'total_fields': len(field_names),
            'data_source': 'BSEE Binary Files',
            'fetch_timestamp': datetime.now().isoformat()
        }
        
        for field_name in field_names:
            # Fetch lease data for the field
            lease_df = self.fetch_field_leases(field_name, cfg)
            
            # Fetch production data
            production_df = self.fetch_field_production(field_name, cfg)
            
            field_metrics = {
                'lease_count': len(lease_df['Lease Number'].unique()) if 'Lease Number' in lease_df else 0,
                'has_production': not production_df.empty,
                'production_records': len(production_df) if not production_df.empty else 0
            }
            
            # Add production metrics if available
            if not production_df.empty:
                if 'Oil Volume' in production_df:
                    field_metrics['total_oil_bbls'] = production_df['Oil Volume'].sum()
                if 'Gas Volume' in production_df:
                    field_metrics['total_gas_mcf'] = production_df['Gas Volume'].sum()
            
            aggregated['fields'][field_name] = field_metrics
        
        return aggregated
    
    def get_field_summary(self, field_name: str) -> Dict[str, Any]:
        """Get comprehensive summary for a specific field
        
        Args:
            field_name: Name of the field
            
        Returns:
            Field summary metrics
        """
        try:
            # Get lease data
            lease_df = self.fetch_field_leases(field_name)
            
            # Get production data
            production_df = self.fetch_field_production(field_name)
            
            summary = {
                'field_name': field_name,
                'lease_count': len(lease_df['Lease Number'].unique()) if 'Lease Number' in lease_df and not lease_df.empty else 0,
                'area_codes': lease_df['Area Code'].unique().tolist() if 'Area Code' in lease_df and not lease_df.empty else [],
                'block_numbers': lease_df['Block Number'].unique().tolist() if 'Block Number' in lease_df and not lease_df.empty else [],
                'has_production_data': not production_df.empty,
                'data_points': len(lease_df) + len(production_df)
            }
            
            # Add production summary if available
            if not production_df.empty:
                summary['production'] = {
                    'record_count': len(production_df),
                    'total_oil_bbls': production_df['Oil Volume'].sum() if 'Oil Volume' in production_df else 0,
                    'total_gas_mcf': production_df['Gas Volume'].sum() if 'Gas Volume' in production_df else 0
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting field summary: {e}")
            return {'field_name': field_name, 'error': str(e)}
    
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