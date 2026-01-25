"""
BlockProcessor for handling Norwegian Continental Shelf block data from SODIR.

This processor handles block data including:
- Block names and identifiers
- Status (awarded, relinquished, etc.)
- Operator and licensee information
- Geographical boundaries and areas
- Stratigraphical information
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class BlockProcessor:
    """Process Norwegian Continental Shelf block data from SODIR API."""
    
    # Status normalization mapping
    STATUS_MAPPING = {
        'AWARDED': 'AWARDED',
        'awarded': 'AWARDED',
        'RELINQUISHED': 'RELINQUISHED',
        'relinquished': 'RELINQUISHED',
        'OPEN': 'OPEN',
        'open': 'OPEN',
        'APPLICATION': 'APPLICATION',
        'application': 'APPLICATION',
        '': 'UNKNOWN',
        None: 'UNKNOWN'
    }
    
    def __init__(self):
        """Initialize the BlockProcessor."""
        self.processed_count = 0
        self.error_count = 0
        
    def process(self, block_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single block record from SODIR.
        
        Args:
            block_data: Raw block data from SODIR API
            
        Returns:
            Processed block data with normalized fields
        """
        try:
            processed = {
                # Basic identifiers
                'block_name': block_data.get('blcName', ''),
                'block_id': block_data.get('blcNpdidBlock'),
                'status': self.normalize_status(block_data.get('blcStatus')),
                
                # Area information
                'area_km2': self._safe_float(block_data.get('blcAreaPolyArea')),
                'area_type': block_data.get('blcAreaPolyBlockName', ''),
                'stratigraphical': block_data.get('blcAreaPolyStratigraphical', ''),
                
                # Dates
                'valid_from': self._parse_date(block_data.get('blcAreaPolyDateValidFrom')),
                'valid_to': self._parse_date(block_data.get('blcAreaPolyDateValidTo')),
                
                # Operator and licensees
                'operator': block_data.get('blcOperatorName'),
                'licensees': self._process_licensees(block_data.get('blcLicensees', [])),
                
                # Geometry and coordinates
                'geometry': block_data.get('geometry'),
                'latitude': self._extract_latitude(block_data),
                'longitude': self._extract_longitude(block_data),
                
                # Reference information
                'vertical_reference': block_data.get('blcAreaPolyVerticalReference', 'MSL'),
                
                # Metadata
                'processed_timestamp': datetime.utcnow().isoformat(),
                'source': 'SODIR'
            }
            
            # Add additional fields if present
            if 'blcLicenseeName' in block_data:
                processed['license_name'] = block_data['blcLicenseeName']
                
            if 'blcDiscoveryWellbore' in block_data:
                processed['discovery_wellbore'] = block_data['blcDiscoveryWellbore']
                
            self.processed_count += 1
            return processed
            
        except Exception as e:
            logger.error(f"Error processing block {block_data.get('blcName', 'unknown')}: {str(e)}")
            self.error_count += 1
            return None
            
    def process_batch(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple block records.
        
        Args:
            blocks: List of raw block data from SODIR
            
        Returns:
            List of processed block data
        """
        processed_blocks = []
        
        for block in blocks:
            result = self.process(block)
            if result:
                processed_blocks.append(result)
                
        logger.info(f"Processed {len(processed_blocks)}/{len(blocks)} blocks successfully")
        return processed_blocks
        
    def validate(self, block_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate block data for required fields and data quality.
        
        Args:
            block_data: Block data to validate
            
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        # Check required fields
        required_fields = ['blcName']
        for field in required_fields:
            if not block_data.get(field):
                errors.append(f"Missing required field: {field}")
                
        # Validate block name format (e.g., "35/11")
        block_name = block_data.get('blcName', '')
        if block_name and not self._is_valid_block_name(block_name):
            errors.append(f"Invalid block name format: {block_name}")
            
        # Validate area if present
        if 'blcAreaPolyArea' in block_data:
            area = block_data['blcAreaPolyArea']
            if area is not None:
                try:
                    area_float = float(area)
                    if area_float < 0:
                        errors.append(f"Invalid area value (negative): {area}")
                    elif area_float > 10000:  # Sanity check - blocks shouldn't be huge
                        errors.append(f"Suspicious area value (too large): {area}")
                except (ValueError, TypeError):
                    errors.append(f"Invalid area value (not numeric): {area}")
                    
        # Validate dates if present
        for date_field in ['blcAreaPolyDateValidFrom', 'blcAreaPolyDateValidTo']:
            if date_field in block_data and block_data[date_field]:
                if not self._is_valid_date(block_data[date_field]):
                    errors.append(f"Invalid date format in {date_field}: {block_data[date_field]}")
                    
        # Validate geometry if present
        if 'geometry' in block_data and block_data['geometry']:
            if not self._is_valid_geometry(block_data['geometry']):
                errors.append("Invalid geometry structure")
                
        is_valid = len(errors) == 0
        return is_valid, errors
        
    def normalize_status(self, status: Optional[str]) -> str:
        """
        Normalize block status to standard values.
        
        Args:
            status: Raw status value
            
        Returns:
            Normalized status string
        """
        if status in self.STATUS_MAPPING:
            return self.STATUS_MAPPING[status]
        
        # Try to handle unexpected values
        if status:
            status_upper = status.upper()
            if status_upper in ['AWARDED', 'RELINQUISHED', 'OPEN', 'APPLICATION']:
                return status_upper
                
        return 'UNKNOWN'
        
    def _process_licensees(self, licensees: Any) -> List[str]:
        """
        Process licensees data which might be a list or a string.
        
        Args:
            licensees: Raw licensees data
            
        Returns:
            List of licensee names
        """
        if isinstance(licensees, list):
            return [str(l) for l in licensees if l]
        elif isinstance(licensees, str):
            # Handle comma-separated or semicolon-separated strings
            if ',' in licensees:
                return [l.strip() for l in licensees.split(',') if l.strip()]
            elif ';' in licensees:
                return [l.strip() for l in licensees.split(';') if l.strip()]
            else:
                return [licensees.strip()] if licensees.strip() else []
        else:
            return []
            
    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Safely convert a value to float.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None if conversion fails
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
            
    def _parse_date(self, date_str: Any) -> Optional[str]:
        """
        Parse and validate date string.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            ISO format date string or None
        """
        if not date_str:
            return None
            
        try:
            # Try to parse various date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y']:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
            return str(date_str)  # Return as-is if no format matches
        except Exception:
            return None
            
    def _extract_latitude(self, block_data: Dict[str, Any]) -> Optional[float]:
        """Extract latitude from block data."""
        # Try direct latitude field
        if 'latitude' in block_data:
            return self._safe_float(block_data['latitude'])
        
        # Try Norwegian coordinate fields
        if 'blcAreaPolyLatNorth' in block_data:
            return self._safe_float(block_data['blcAreaPolyLatNorth'])
            
        # Try UTM coordinates from mock data or SODIR format
        if 'coordinates' in block_data:
            coords = block_data['coordinates']
            if isinstance(coords, dict):
                northing = coords.get('northing')
                easting = coords.get('easting')
                zone = coords.get('utmZone', 31)
                
                if northing and easting:
                    # Convert UTM to WGS84 (simplified calculation)
                    # For Norwegian Continental Shelf, approximate conversion
                    # Zone 31-35 cover Norway, centered around 3-21 degrees E
                    lat = 58.0 + (northing - 6500000) / 111320.0  # Rough approximation
                    return lat
            
        # Try extracting from geometry centroid
        if 'geometry' in block_data and block_data['geometry']:
            geometry = block_data['geometry']
            if 'coordinates' in geometry and geometry['coordinates']:
                # For polygon, calculate centroid
                if geometry.get('type') == 'Polygon':
                    coords = geometry['coordinates'][0] if geometry['coordinates'] else []
                    if coords:
                        lats = [c[1] for c in coords if len(c) >= 2]
                        if lats:
                            return sum(lats) / len(lats)
        
        # Default latitude for Norwegian Continental Shelf if nothing else works
        return 62.0 if block_data else None
    
    def _extract_longitude(self, block_data: Dict[str, Any]) -> Optional[float]:
        """Extract longitude from block data."""
        # Try direct longitude field
        if 'longitude' in block_data:
            return self._safe_float(block_data['longitude'])
        
        # Try Norwegian coordinate fields
        if 'blcAreaPolyLonEast' in block_data:
            return self._safe_float(block_data['blcAreaPolyLonEast'])
            
        # Try UTM coordinates from mock data or SODIR format
        if 'coordinates' in block_data:
            coords = block_data['coordinates']
            if isinstance(coords, dict):
                northing = coords.get('northing')
                easting = coords.get('easting')
                zone = coords.get('utmZone', 31)
                
                if northing and easting:
                    # Convert UTM to WGS84 (simplified calculation)
                    # For Norwegian Continental Shelf, approximate conversion
                    # Zone 31-35 cover Norway, centered around 3-21 degrees E
                    lon = 3.0 + (zone - 31) * 6 + (easting - 500000) / 111320.0  # Rough approximation
                    return lon
            
        # Try extracting from geometry centroid
        if 'geometry' in block_data and block_data['geometry']:
            geometry = block_data['geometry']
            if 'coordinates' in geometry and geometry['coordinates']:
                # For polygon, calculate centroid
                if geometry.get('type') == 'Polygon':
                    coords = geometry['coordinates'][0] if geometry['coordinates'] else []
                    if coords:
                        lons = [c[0] for c in coords if len(c) >= 2]
                        if lons:
                            return sum(lons) / len(lons)
        
        # Default longitude for Norwegian Continental Shelf if nothing else works
        return 4.5 if block_data else None
    
    def _is_valid_block_name(self, block_name: str) -> bool:
        """
        Validate block name format (e.g., "35/11").
        
        Args:
            block_name: Block name to validate
            
        Returns:
            True if valid format
        """
        # Norwegian blocks typically follow pattern like "35/11" or "35/11-1"
        import re
        pattern = r'^\d{1,3}/\d{1,2}(-\d+)?$'
        return bool(re.match(pattern, block_name))
        
    def _is_valid_date(self, date_str: str) -> bool:
        """
        Check if date string is in valid format.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            True if valid date format
        """
        return self._parse_date(date_str) is not None
        
    def _is_valid_geometry(self, geometry: Dict[str, Any]) -> bool:
        """
        Validate geometry structure.
        
        Args:
            geometry: Geometry data to validate
            
        Returns:
            True if valid geometry
        """
        if not isinstance(geometry, dict):
            return False
            
        # Check for required GeoJSON fields
        if 'type' not in geometry or 'coordinates' not in geometry:
            return False
            
        # Validate geometry type
        valid_types = ['Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon']
        if geometry['type'] not in valid_types:
            return False
            
        # Basic coordinate validation
        if not isinstance(geometry['coordinates'], (list, tuple)):
            return False
            
        return True
        
    def get_statistics(self) -> Dict[str, int]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with processing counts
        """
        return {
            'processed': self.processed_count,
            'errors': self.error_count,
            'success_rate': self.processed_count / max(self.processed_count + self.error_count, 1)
        }