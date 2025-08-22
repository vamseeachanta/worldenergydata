"""
Hierarchical data loader for BSEE integration
Loads and organizes data from BSEE sources into hierarchical structure
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator, Tuple
from datetime import date, datetime
import json
import pickle

from .models import (
    Well, Lease, Field, Block,
    WellSummary, ProductionMetrics
)

# Import BSEE analysis modules
from ...analysis import well_api10, well_api12, production_api10, production_api12


logger = logging.getLogger(__name__)


class HierarchicalDataLoader:
    """Loads BSEE data and organizes into hierarchical structure"""
    
    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize data loader
        
        Args:
            data_path: Path to BSEE data directory
        """
        self.data_path = data_path or Path("data/bsee")
        self.blocks = {}
        self.fields = {}
        self.leases = {}
        self.wells = {}
        self._cache = {}
        
    def load_hierarchy(self, block_number: Optional[str] = None,
                      field_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load complete hierarchy for specified block or field
        
        Args:
            block_number: Optional block number to filter
            field_name: Optional field name to filter
            
        Returns:
            Dictionary with hierarchical data structure
        """
        logger.info(f"Loading hierarchy for block={block_number}, field={field_name}")
        
        # Load raw data from BSEE sources
        raw_data = self._load_raw_data(block_number, field_name)
        
        # Build hierarchy
        hierarchy = self._build_hierarchy(raw_data)
        
        # Add production data
        self._add_production_data(hierarchy)
        
        return hierarchy
    
    def _load_raw_data(self, block_number: Optional[str] = None,
                      field_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load raw data from BSEE sources
        
        Args:
            block_number: Optional block filter
            field_name: Optional field filter
            
        Returns:
            Raw data dictionary
        """
        raw_data = {
            'blocks': [],
            'fields': [],
            'leases': [],
            'wells': [],
            'production': []
        }
        
        # Try to load from binary files first (faster)
        binary_path = self.data_path / "binary"
        if binary_path.exists():
            raw_data = self._load_from_binary(binary_path, block_number, field_name)
        else:
            # Fall back to CSV/API loading
            raw_data = self._load_from_csv(block_number, field_name)
        
        return raw_data
    
    def _load_from_binary(self, binary_path: Path, 
                         block_number: Optional[str] = None,
                         field_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load data from binary files (pickle format)
        
        Args:
            binary_path: Path to binary files
            block_number: Optional block filter
            field_name: Optional field filter
            
        Returns:
            Data dictionary
        """
        data = {
            'blocks': [],
            'fields': [],
            'leases': [],
            'wells': [],
            'production': []
        }
        
        # Load well data
        well_file = binary_path / "wells.bin"
        if well_file.exists():
            with open(well_file, 'rb') as f:
                wells_data = pickle.load(f)
                
                for well_record in wells_data:
                    # Filter by field if specified
                    if field_name and well_record.get('field_name') != field_name:
                        continue
                    
                    # Extract block from area/block designation
                    area_block = well_record.get('area_block', '')
                    if block_number and block_number not in area_block:
                        continue
                    
                    # Parse block, field, lease from well data
                    block_info = self._parse_block_info(area_block)
                    if block_info and block_info not in data['blocks']:
                        data['blocks'].append(block_info)
                    
                    field_info = {
                        'id': well_record.get('field_name', 'Unknown'),
                        'name': well_record.get('field_name', 'Unknown'),
                        'block_id': block_info['id'] if block_info else None
                    }
                    if field_info not in data['fields']:
                        data['fields'].append(field_info)
                    
                    lease_info = {
                        'id': well_record.get('lease_number', 'Unknown'),
                        'number': well_record.get('lease_number', 'Unknown'),
                        'field_id': field_info['id']
                    }
                    if lease_info not in data['leases']:
                        data['leases'].append(lease_info)
                    
                    well_info = {
                        'id': well_record.get('api_well_number', 'Unknown'),
                        'name': well_record.get('well_name', 'Unknown'),
                        'api_number': well_record.get('api_well_number'),
                        'lease_id': lease_info['id'],
                        'water_depth': well_record.get('water_depth'),
                        'total_depth': well_record.get('total_borehole_length'),
                        'spud_date': well_record.get('spud_date'),
                        'status': well_record.get('well_status', 'ACTIVE')
                    }
                    data['wells'].append(well_info)
        
        # Load production data
        prod_file = binary_path / "production.bin"
        if prod_file.exists():
            with open(prod_file, 'rb') as f:
                prod_data = pickle.load(f)
                data['production'] = prod_data
        
        return data
    
    def _load_from_csv(self, block_number: Optional[str] = None,
                      field_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load data from CSV files
        
        Args:
            block_number: Optional block filter
            field_name: Optional field filter
            
        Returns:
            Data dictionary
        """
        # This would integrate with existing BSEE CSV loaders
        # For now, return sample data for testing
        return self._create_sample_data(block_number, field_name)
    
    def _parse_block_info(self, area_block: str) -> Optional[Dict[str, str]]:
        """
        Parse block information from area/block string
        
        Args:
            area_block: Area block designation (e.g., "WR 759")
            
        Returns:
            Block info dictionary or None
        """
        if not area_block:
            return None
        
        parts = area_block.strip().split()
        if len(parts) >= 2:
            area = parts[0]
            number = parts[1]
            return {
                'id': f"{area}_{number}",
                'area': area,
                'number': number
            }
        return None
    
    def _build_hierarchy(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build hierarchical structure from raw data
        
        Args:
            raw_data: Raw data dictionary
            
        Returns:
            Hierarchical structure
        """
        hierarchy = {
            'blocks': {},
            'fields': {},
            'leases': {},
            'wells': {}
        }
        
        # Create blocks
        for block_data in raw_data.get('blocks', []):
            block = Block(
                id=block_data['id'],
                number=block_data['number'],
                area=block_data.get('area', '')
            )
            hierarchy['blocks'][block.id] = block
            self.blocks[block.id] = block
        
        # Create fields and link to blocks
        for field_data in raw_data.get('fields', []):
            field = Field(
                id=field_data['id'],
                name=field_data['name'],
                block_id=field_data.get('block_id')
            )
            hierarchy['fields'][field.id] = field
            self.fields[field.id] = field
            
            # Link to parent block
            if field_data.get('block_id') in hierarchy['blocks']:
                parent_block = hierarchy['blocks'][field_data['block_id']]
                parent_block.add_child(field)
        
        # Create leases and link to fields
        for lease_data in raw_data.get('leases', []):
            lease = Lease(
                id=lease_data['id'],
                number=lease_data['number'],
                field_id=lease_data.get('field_id')
            )
            hierarchy['leases'][lease.id] = lease
            self.leases[lease.id] = lease
            
            # Link to parent field
            if lease_data.get('field_id') in hierarchy['fields']:
                parent_field = hierarchy['fields'][lease_data['field_id']]
                parent_field.add_child(lease)
        
        # Create wells and link to leases
        for well_data in raw_data.get('wells', []):
            well = Well(
                id=well_data['id'],
                name=well_data['name'],
                api_number=well_data.get('api_number'),
                lease_id=well_data.get('lease_id'),
                water_depth_ft=well_data.get('water_depth'),
                total_depth_ft=well_data.get('total_depth'),
                spud_date=well_data.get('spud_date'),
                status=well_data.get('status', 'active')
            )
            hierarchy['wells'][well.id] = well
            self.wells[well.id] = well
            
            # Link to parent lease
            if well_data.get('lease_id') in hierarchy['leases']:
                parent_lease = hierarchy['leases'][well_data['lease_id']]
                parent_lease.add_child(well)
        
        return hierarchy
    
    def _add_production_data(self, hierarchy: Dict[str, Any]):
        """
        Add production data to wells
        
        Args:
            hierarchy: Hierarchical structure
        """
        # This would load actual production data
        # For now, add sample production data
        for well_id, well in hierarchy['wells'].items():
            # Sample production data
            production = {
                'oil_bbls': 50000 + (hash(well_id) % 100000),
                'gas_mcf': 25000 + (hash(well_id) % 50000),
                'water_bbls': 10000 + (hash(well_id) % 20000),
                'days_on': 365
            }
            well.set_production_data(production)
    
    def stream_large_dataset(self, chunk_size: int = 1000) -> Iterator[Dict[str, Any]]:
        """
        Stream large datasets in chunks
        
        Args:
            chunk_size: Number of wells per chunk
            
        Yields:
            Chunks of hierarchical data
        """
        # Load well list
        well_files = list(self.data_path.glob("wells_*.bin"))
        
        for well_file in well_files:
            with open(well_file, 'rb') as f:
                wells_chunk = pickle.load(f)
                
                # Process in chunks
                for i in range(0, len(wells_chunk), chunk_size):
                    chunk = wells_chunk[i:i + chunk_size]
                    
                    # Build hierarchy for this chunk
                    raw_data = self._process_chunk(chunk)
                    hierarchy = self._build_hierarchy(raw_data)
                    self._add_production_data(hierarchy)
                    
                    yield hierarchy
    
    def _process_chunk(self, wells_chunk: List[Dict]) -> Dict[str, Any]:
        """
        Process a chunk of wells into raw data format
        
        Args:
            wells_chunk: List of well records
            
        Returns:
            Raw data dictionary
        """
        data = {
            'blocks': [],
            'fields': [],
            'leases': [],
            'wells': [],
            'production': []
        }
        
        seen_blocks = set()
        seen_fields = set()
        seen_leases = set()
        
        for well_record in wells_chunk:
            # Extract unique blocks, fields, leases
            area_block = well_record.get('area_block', '')
            block_info = self._parse_block_info(area_block)
            
            if block_info and block_info['id'] not in seen_blocks:
                data['blocks'].append(block_info)
                seen_blocks.add(block_info['id'])
            
            field_name = well_record.get('field_name', 'Unknown')
            if field_name not in seen_fields:
                data['fields'].append({
                    'id': field_name,
                    'name': field_name,
                    'block_id': block_info['id'] if block_info else None
                })
                seen_fields.add(field_name)
            
            lease_number = well_record.get('lease_number', 'Unknown')
            if lease_number not in seen_leases:
                data['leases'].append({
                    'id': lease_number,
                    'number': lease_number,
                    'field_id': field_name
                })
                seen_leases.add(lease_number)
            
            # Add well
            data['wells'].append({
                'id': well_record.get('api_well_number', 'Unknown'),
                'name': well_record.get('well_name', 'Unknown'),
                'api_number': well_record.get('api_well_number'),
                'lease_id': lease_number,
                'water_depth': well_record.get('water_depth'),
                'total_depth': well_record.get('total_borehole_length'),
                'spud_date': well_record.get('spud_date'),
                'status': well_record.get('well_status', 'ACTIVE')
            })
        
        return data
    
    def _create_sample_data(self, block_number: Optional[str] = None,
                           field_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create sample data for testing
        
        Args:
            block_number: Optional block filter
            field_name: Optional field filter
            
        Returns:
            Sample data dictionary
        """
        # Sample data matching go-by reports structure
        data = {
            'blocks': [
                {'id': 'WR_759', 'area': 'WR', 'number': '759'}
            ],
            'fields': [
                {'id': 'Jack', 'name': 'Jack', 'block_id': 'WR_759'},
                {'id': 'St_Malo', 'name': 'St. Malo', 'block_id': 'WR_759'}
            ],
            'leases': [
                {'id': 'OCS-G-12345', 'number': 'OCS-G-12345', 'field_id': 'Jack'},
                {'id': 'OCS-G-12346', 'number': 'OCS-G-12346', 'field_id': 'Jack'},
                {'id': 'OCS-G-12347', 'number': 'OCS-G-12347', 'field_id': 'St_Malo'}
            ],
            'wells': [
                {
                    'id': 'API001',
                    'name': 'PS001',
                    'api_number': 'API001',
                    'lease_id': 'OCS-G-12345',
                    'water_depth': 7000,
                    'total_depth': 25000,
                    'spud_date': date(2020, 1, 15),
                    'status': 'active'
                },
                {
                    'id': 'API002',
                    'name': 'PS002',
                    'api_number': 'API002',
                    'lease_id': 'OCS-G-12345',
                    'water_depth': 7000,
                    'total_depth': 26000,
                    'spud_date': date(2020, 3, 20),
                    'status': 'active'
                },
                {
                    'id': 'API003',
                    'name': 'PS003',
                    'api_number': 'API003',
                    'lease_id': 'OCS-G-12346',
                    'water_depth': 7100,
                    'total_depth': 24500,
                    'spud_date': date(2020, 6, 10),
                    'status': 'active'
                }
            ],
            'production': []
        }
        
        # Apply filters
        if block_number and block_number != '759':
            return {'blocks': [], 'fields': [], 'leases': [], 'wells': [], 'production': []}
        
        if field_name:
            data['fields'] = [f for f in data['fields'] if f['name'] == field_name]
            field_ids = {f['id'] for f in data['fields']}
            data['leases'] = [l for l in data['leases'] if l['field_id'] in field_ids]
            lease_ids = {l['id'] for l in data['leases']}
            data['wells'] = [w for w in data['wells'] if w['lease_id'] in lease_ids]
        
        return data
    
    def get_hierarchy_stats(self) -> Dict[str, int]:
        """
        Get statistics about loaded hierarchy
        
        Returns:
            Dictionary with counts
        """
        return {
            'blocks': len(self.blocks),
            'fields': len(self.fields),
            'leases': len(self.leases),
            'wells': len(self.wells)
        }