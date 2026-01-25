"""
Data validation utilities for SODIR data processing.

Provides validation for:
- Required fields
- Data types
- Value ranges
- Logical relationships
- Coordinate bounds
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataValidator:
    """Validate SODIR data for quality and consistency."""
    
    # Norwegian Continental Shelf coordinate bounds
    NORWAY_LAT_MIN = 56.0
    NORWAY_LAT_MAX = 72.0
    NORWAY_LON_MIN = -5.0
    NORWAY_LON_MAX = 35.0
    
    # Valid UTM zones for Norwegian Continental Shelf
    NORWAY_UTM_ZONES = [31, 32, 33, 34, 35]
    
    def __init__(self):
        """Initialize the DataValidator."""
        self.validation_count = 0
        self.error_count = 0
        
    def validate_schema(
        self, 
        data: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate data against a schema definition.
        
        Args:
            data: Data to validate
            schema: Schema definition with 'required' and 'optional' fields
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required fields
        if 'required' in schema:
            for field in schema['required']:
                if field not in data or data[field] is None or data[field] == '':
                    errors.append(f"Missing required field: {field}")
                    
        # Check for unexpected fields (optional)
        if 'strict' in schema and schema['strict']:
            allowed_fields = set(schema.get('required', [])) | set(schema.get('optional', []))
            for field in data:
                if field not in allowed_fields:
                    errors.append(f"Unexpected field: {field}")
                    
        self.validation_count += 1
        if errors:
            self.error_count += 1
            
        return len(errors) == 0, errors
        
    def validate_types(
        self, 
        data: Dict[str, Any], 
        type_schema: Dict[str, type]
    ) -> bool:
        """
        Validate data types for fields.
        
        Args:
            data: Data to validate
            type_schema: Dictionary mapping field names to expected types
            
        Returns:
            True if all types are valid
        """
        for field, expected_type in type_schema.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    try:
                        # Try to convert
                        expected_type(data[field])
                    except (ValueError, TypeError):
                        logger.error(f"Type validation failed for {field}: expected {expected_type}, got {type(data[field])}")
                        return False
        return True
        
    def validate_norwegian_coordinates(
        self, 
        latitude: Optional[float], 
        longitude: Optional[float]
    ) -> bool:
        """
        Validate if coordinates are within Norwegian Continental Shelf bounds.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            
        Returns:
            True if coordinates are valid for Norwegian waters
        """
        if latitude is None or longitude is None:
            return False
            
        try:
            lat = float(latitude)
            lon = float(longitude)
            
            if lat < self.NORWAY_LAT_MIN or lat > self.NORWAY_LAT_MAX:
                return False
                
            if lon < self.NORWAY_LON_MIN or lon > self.NORWAY_LON_MAX:
                return False
                
            return True
            
        except (ValueError, TypeError):
            return False
            
    def validate_utm_zone(self, zone: Optional[int]) -> bool:
        """
        Validate if UTM zone is valid for Norwegian Continental Shelf.
        
        Args:
            zone: UTM zone number
            
        Returns:
            True if zone is valid for Norwegian waters
        """
        if zone is None:
            return False
            
        try:
            zone_int = int(zone)
            return zone_int in self.NORWAY_UTM_ZONES
        except (ValueError, TypeError):
            return False
            
    def validate_date_range(
        self, 
        date_str: Optional[str], 
        min_year: int = 1960,
        max_year: Optional[int] = None
    ) -> bool:
        """
        Validate if date is within reasonable range.
        
        Args:
            date_str: Date string in ISO format
            min_year: Minimum valid year
            max_year: Maximum valid year (current year + 10 if None)
            
        Returns:
            True if date is within valid range
        """
        if not date_str:
            return False
            
        try:
            # Parse ISO date
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(date_str)
                
            year = dt.year
            
            if max_year is None:
                max_year = datetime.now().year + 10
                
            return min_year <= year <= max_year
            
        except (ValueError, TypeError):
            return False
            
    def validate_numeric_range(
        self,
        value: Any,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        allow_zero: bool = True,
        allow_negative: bool = False
    ) -> bool:
        """
        Validate if numeric value is within specified range.
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            allow_zero: Whether zero is allowed
            allow_negative: Whether negative values are allowed
            
        Returns:
            True if value is within valid range
        """
        if value is None:
            return True  # None is considered valid (optional field)
            
        try:
            num_val = float(value)
            
            if not allow_negative and num_val < 0:
                return False
                
            if not allow_zero and num_val == 0:
                return False
                
            if min_val is not None and num_val < min_val:
                return False
                
            if max_val is not None and num_val > max_val:
                return False
                
            return True
            
        except (ValueError, TypeError):
            return False
            
    def validate_block_name(self, block_name: str) -> bool:
        """
        Validate Norwegian block name format (e.g., "35/11").
        
        Args:
            block_name: Block name to validate
            
        Returns:
            True if valid block name format
        """
        if not block_name:
            return False
            
        import re
        # Norwegian blocks: "35/11" or with suffix "35/11-1"
        pattern = r'^\d{1,3}/\d{1,2}(-\d+)?$'
        return bool(re.match(pattern, block_name))
        
    def validate_wellbore_name(self, wellbore_name: str) -> bool:
        """
        Validate Norwegian wellbore name format (e.g., "35/11-1").
        
        Args:
            wellbore_name: Wellbore name to validate
            
        Returns:
            True if valid wellbore name format
        """
        if not wellbore_name:
            return False
            
        import re
        # Norwegian wellbores: "35/11-1" or with suffix "35/11-1 S"
        pattern = r'^\d{1,3}/\d{1,2}-\d+(\s+[A-Z]+)?$'
        return bool(re.match(pattern, wellbore_name))
        
    def validate_field_data(self, field_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for field data.
        
        Args:
            field_data: Field data to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Required fields
        if not field_data.get('fldName'):
            errors.append("Missing field name")
            
        # Validate reserves logic
        original_oil = field_data.get('fldOriginalReservesOil')
        remaining_oil = field_data.get('fldRemainingReservesOil')
        
        if original_oil is not None and remaining_oil is not None:
            try:
                if float(remaining_oil) > float(original_oil):
                    errors.append(f"Remaining reserves ({remaining_oil}) exceed original reserves ({original_oil})")
            except (ValueError, TypeError):
                pass
                
        # Validate timeline
        discovery = field_data.get('fldDiscoveryYear')
        prod_start = field_data.get('fldProductionStartYear')
        cessation = field_data.get('fldCessationYear')
        
        if discovery and prod_start:
            try:
                if int(prod_start) < int(discovery):
                    errors.append(f"Production start ({prod_start}) before discovery ({discovery})")
            except (ValueError, TypeError):
                pass
                
        if prod_start and cessation:
            try:
                if int(cessation) < int(prod_start):
                    errors.append(f"Cessation ({cessation}) before production start ({prod_start})")
            except (ValueError, TypeError):
                pass
                
        return len(errors) == 0, errors
        
    def validate_discovery_data(self, discovery_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for discovery data.
        
        Args:
            discovery_data: Discovery data to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Required fields
        if not discovery_data.get('dscName'):
            errors.append("Missing discovery name")
            
        # Validate discovery year
        discovery_year = discovery_data.get('dscDiscoveryYear')
        if discovery_year:
            if not self.validate_date_range(f"{discovery_year}-01-01"):
                errors.append(f"Invalid discovery year: {discovery_year}")
                
        # Validate resources (at least one should be present)
        resource_fields = ['dscRecoverableOil', 'dscRecoverableGas', 'dscRecoverableNGL', 'dscRecoverableCondensate']
        has_resources = any(discovery_data.get(field) for field in resource_fields)
        
        if not has_resources:
            errors.append("No resource estimates provided")
            
        # Validate resource values are non-negative
        for field in resource_fields:
            value = discovery_data.get(field)
            if value is not None:
                if not self.validate_numeric_range(value, min_val=0):
                    errors.append(f"Invalid resource value in {field}: {value}")
                    
        return len(errors) == 0, errors
        
    def validate_survey_data(self, survey_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation for survey data.
        
        Args:
            survey_data: Survey data to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Required fields
        if not survey_data.get('srvName'):
            errors.append("Missing survey name")
            
        # Validate dates
        start_date = survey_data.get('srvAcquisitionStartDate')
        end_date = survey_data.get('srvAcquisitionEndDate')
        
        if start_date and not self.validate_date_range(start_date):
            errors.append(f"Invalid acquisition start date: {start_date}")
            
        if end_date and not self.validate_date_range(end_date):
            errors.append(f"Invalid acquisition end date: {end_date}")
            
        if start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
                if end < start:
                    errors.append(f"End date ({end_date}) before start date ({start_date})")
            except Exception:
                pass
                
        # Validate area
        area = survey_data.get('srvAreaKm2')
        if area is not None:
            if not self.validate_numeric_range(area, min_val=0, max_val=100000):
                errors.append(f"Invalid survey area: {area} km2")
                
        # Validate technical parameters
        streamer_count = survey_data.get('srvStreamerCount')
        if streamer_count is not None:
            if not self.validate_numeric_range(streamer_count, min_val=0, max_val=50):
                errors.append(f"Invalid streamer count: {streamer_count}")
                
        return len(errors) == 0, errors
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics.
        
        Returns:
            Dictionary with validation counts
        """
        return {
            'validations': self.validation_count,
            'errors': self.error_count,
            'success_rate': (self.validation_count - self.error_count) / max(self.validation_count, 1)
        }