"""
DiscoveryProcessor for handling exploration discovery data from SODIR.

This processor handles discovery data including:
- Discovery names and years
- Hydrocarbon types (oil, gas, condensate)
- Resource estimates
- Discovery size classification
- Associated wellbores
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscoveryProcessor:
    """Process exploration discovery data from SODIR API."""
    
    # Discovery size classification (based on oil equivalent)
    SIZE_CLASSES = {
        'SMALL': (0, 10),        # < 10 million barrels oil equivalent
        'MEDIUM': (10, 50),      # 10-50 million barrels
        'LARGE': (50, 200),      # 50-200 million barrels
        'GIANT': (200, float('inf'))  # > 200 million barrels
    }
    
    # Hydrocarbon type normalization
    HC_TYPE_MAPPING = {
        'OIL': 'OIL',
        'GAS': 'GAS',
        'GAS/CONDENSATE': 'GAS_CONDENSATE',
        'GAS CONDENSATE': 'GAS_CONDENSATE',
        'CONDENSATE': 'CONDENSATE',
        'OIL/GAS': 'OIL_GAS',
        'OIL GAS': 'OIL_GAS',
        '': 'UNKNOWN',
        None: 'UNKNOWN'
    }
    
    # Conversion factors
    SM3_TO_BARRELS = 6.29
    BILLION_SM3_TO_BCF = 35.3
    # Gas to oil equivalent: 1000 Sm3 gas = 1 Sm3 oil equivalent
    GAS_TO_OIL_EQUIVALENT = 1000
    
    def __init__(self):
        """Initialize the DiscoveryProcessor."""
        self.processed_count = 0
        self.error_count = 0
        
    def process(self, discovery_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single discovery record from SODIR.
        
        Args:
            discovery_data: Raw discovery data from SODIR API
            
        Returns:
            Processed discovery data with normalized fields and calculations
        """
        try:
            processed = {
                # Basic identifiers
                'discovery_name': discovery_data.get('dscName', ''),
                'discovery_id': discovery_data.get('dscNpdidDiscovery'),
                'discovery_year': self._safe_int(discovery_data.get('dscDiscoveryYear')),
                
                # Classification
                'hydrocarbon_type': self.normalize_hc_type(discovery_data.get('dscHcType')),
                'included_in_field': discovery_data.get('dscResInclInDiscoveryName'),
                'field_name': discovery_data.get('dscFieldName'),
                
                # Associated wellbore
                'wellbore_name': discovery_data.get('dscWellboreName'),
                'wellbore_id': discovery_data.get('dscNpdidWellbore'),
                
                # Resource estimates (converted to standard units)
                'recoverable_oil_mmbbl': self._convert_to_mmbbl(discovery_data.get('dscRecoverableOil')),
                'recoverable_gas_bcf': self._convert_to_bcf(discovery_data.get('dscRecoverableGas')),
                'recoverable_ngl_mmbbl': self._convert_to_mmbbl(discovery_data.get('dscRecoverableNGL')),
                'recoverable_condensate_mmbbl': self._convert_to_mmbbl(discovery_data.get('dscRecoverableCondensate')),
                
                # Resource estimates in original units (million Sm3)
                'recoverable_oil_msm3': self._safe_float(discovery_data.get('dscRecoverableOil')),
                'recoverable_gas_bsm3': self._safe_float(discovery_data.get('dscRecoverableGas')),
                'recoverable_ngl_msm3': self._safe_float(discovery_data.get('dscRecoverableNGL')),
                'recoverable_condensate_msm3': self._safe_float(discovery_data.get('dscRecoverableCondensate')),
                
                # Operator and license
                'operator': discovery_data.get('dscOperatorName'),
                'production_license': discovery_data.get('dscProductionLicense'),
                
                # Status and dates
                'discovery_status': discovery_data.get('dscStatus'),
                'date_updated': self._parse_date(discovery_data.get('dscDateUpdated')),
                
                # Geometry if available
                'geometry': discovery_data.get('geometry'),
                
                # Metadata
                'processed_timestamp': datetime.utcnow().isoformat(),
                'source': 'SODIR'
            }
            
            # Calculate oil equivalent
            oil_eq = self._calculate_oil_equivalent(
                processed['recoverable_oil_msm3'],
                processed['recoverable_gas_bsm3'],
                processed['recoverable_ngl_msm3'],
                processed['recoverable_condensate_msm3']
            )
            processed['oil_equivalent_mmbbl'] = oil_eq
            
            # Classify discovery size
            if oil_eq is not None:
                processed['discovery_size_class'] = self.classify_discovery_size(oil_eq)
            else:
                processed['discovery_size_class'] = 'UNKNOWN'
                
            # Calculate discovery age
            if processed['discovery_year']:
                processed['discovery_age_years'] = datetime.now().year - processed['discovery_year']
                
            # Determine if discovery is commercial
            processed['is_commercial'] = self._assess_commerciality(processed)
            
            self.processed_count += 1
            return processed
            
        except Exception as e:
            logger.error(f"Error processing discovery {discovery_data.get('dscName', 'unknown')}: {str(e)}")
            self.error_count += 1
            return None
            
    def process_batch(self, discoveries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple discovery records.
        
        Args:
            discoveries: List of raw discovery data from SODIR
            
        Returns:
            List of processed discovery data
        """
        processed_discoveries = []
        
        for discovery in discoveries:
            result = self.process(discovery)
            if result:
                processed_discoveries.append(result)
                
        logger.info(f"Processed {len(processed_discoveries)}/{len(discoveries)} discoveries successfully")
        return processed_discoveries
        
    def normalize_hc_type(self, hc_type: Optional[str]) -> str:
        """
        Normalize hydrocarbon type to standard values.
        
        Args:
            hc_type: Raw hydrocarbon type
            
        Returns:
            Normalized HC type string
        """
        if hc_type in self.HC_TYPE_MAPPING:
            return self.HC_TYPE_MAPPING[hc_type]
            
        if hc_type:
            hc_upper = hc_type.upper().strip()
            if hc_upper in self.HC_TYPE_MAPPING:
                return self.HC_TYPE_MAPPING[hc_upper]
                
            # Handle variations
            if 'OIL' in hc_upper and 'GAS' in hc_upper:
                return 'OIL_GAS'
            elif 'CONDENSATE' in hc_upper:
                return 'GAS_CONDENSATE' if 'GAS' in hc_upper else 'CONDENSATE'
            elif 'OIL' in hc_upper:
                return 'OIL'
            elif 'GAS' in hc_upper:
                return 'GAS'
                
        return 'UNKNOWN'
        
    def classify_discovery_size(self, oil_equivalent_mmbbl: float) -> str:
        """
        Classify discovery size based on oil equivalent.
        
        Args:
            oil_equivalent_mmbbl: Oil equivalent in million barrels
            
        Returns:
            Size classification string
        """
        for size_class, (min_val, max_val) in self.SIZE_CLASSES.items():
            if min_val <= oil_equivalent_mmbbl < max_val:
                return size_class
        return 'UNKNOWN'
        
    def validate(self, discovery_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate discovery data for required fields and data quality.
        
        Args:
            discovery_data: Discovery data to validate
            
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        # Check required fields
        required_fields = ['dscName']
        for field in required_fields:
            if not discovery_data.get(field):
                errors.append(f"Missing required field: {field}")
                
        # Validate discovery year
        if 'dscDiscoveryYear' in discovery_data and discovery_data['dscDiscoveryYear']:
            try:
                year = int(discovery_data['dscDiscoveryYear'])
                current_year = datetime.now().year
                if year < 1960 or year > current_year:
                    errors.append(f"Invalid discovery year: {year}")
            except (ValueError, TypeError):
                errors.append(f"Invalid year value: {discovery_data['dscDiscoveryYear']}")
                
        # Validate resource estimates
        resource_fields = ['dscRecoverableOil', 'dscRecoverableGas', 'dscRecoverableNGL', 'dscRecoverableCondensate']
        
        for field in resource_fields:
            if field in discovery_data and discovery_data[field] is not None:
                try:
                    value = float(discovery_data[field])
                    if value < 0:
                        errors.append(f"Negative resource value in {field}: {value}")
                except (ValueError, TypeError):
                    errors.append(f"Invalid numeric value in {field}: {discovery_data[field]}")
                    
        # Check that at least one resource type has a value
        has_resources = any(
            discovery_data.get(field) is not None and 
            self._safe_float(discovery_data.get(field)) > 0
            for field in resource_fields
        )
        
        if not has_resources:
            errors.append("Discovery has no resource estimates")
            
        is_valid = len(errors) == 0
        return is_valid, errors
        
    def _calculate_oil_equivalent(
        self, 
        oil_msm3: Optional[float],
        gas_bsm3: Optional[float],
        ngl_msm3: Optional[float],
        condensate_msm3: Optional[float]
    ) -> Optional[float]:
        """
        Calculate total oil equivalent in million barrels.
        
        Args:
            oil_msm3: Oil in million Sm3
            gas_bsm3: Gas in billion Sm3
            ngl_msm3: NGL in million Sm3
            condensate_msm3: Condensate in million Sm3
            
        Returns:
            Oil equivalent in million barrels
        """
        try:
            total_msm3 = 0
            
            # Add oil directly
            if oil_msm3:
                total_msm3 += oil_msm3
                
            # Convert gas to oil equivalent (billion Sm3 to million Sm3 oil equivalent)
            if gas_bsm3:
                # 1 billion Sm3 gas = 1000 million Sm3 gas = 1 million Sm3 oil equivalent
                total_msm3 += gas_bsm3
                
            # Add NGL and condensate directly
            if ngl_msm3:
                total_msm3 += ngl_msm3
            if condensate_msm3:
                total_msm3 += condensate_msm3
                
            # Convert to million barrels
            if total_msm3 > 0:
                return round(total_msm3 * self.SM3_TO_BARRELS, 2)
            return 0.0
            
        except (ValueError, TypeError):
            return None
            
    def _assess_commerciality(self, processed_data: Dict[str, Any]) -> bool:
        """
        Assess if a discovery is likely commercial based on size and other factors.
        
        Args:
            processed_data: Processed discovery data
            
        Returns:
            True if likely commercial, False otherwise
        """
        # If included in a field, it's commercial
        if processed_data.get('field_name'):
            return True
            
        # If oil equivalent is significant (>10 mmbbl), likely commercial
        oil_eq = processed_data.get('oil_equivalent_mmbbl')
        if oil_eq and oil_eq > 10:
            return True
            
        # If status indicates development
        status = processed_data.get('discovery_status', '').upper()
        if status and any(term in status for term in ['DEVELOP', 'PRODUC', 'COMMERCIAL']):
            return True
            
        return False
        
    def _convert_to_mmbbl(self, value: Any) -> Optional[float]:
        """
        Convert value to million barrels (from million Sm3).
        
        Args:
            value: Value in million Sm3
            
        Returns:
            Value in million barrels or None
        """
        if value is None:
            return None
        try:
            msm3 = float(value)
            mmbbl = msm3 * self.SM3_TO_BARRELS
            return round(mmbbl, 2)
        except (ValueError, TypeError):
            return None
            
    def _convert_to_bcf(self, value: Any) -> Optional[float]:
        """
        Convert value to billion cubic feet (from billion Sm3).
        
        Args:
            value: Value in billion Sm3
            
        Returns:
            Value in billion cubic feet or None
        """
        if value is None:
            return None
        try:
            bsm3 = float(value)
            bcf = bsm3 * self.BILLION_SM3_TO_BCF
            return round(bcf, 2)
        except (ValueError, TypeError):
            return None
            
    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Safely convert a value to float.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
            
    def _safe_int(self, value: Any) -> Optional[int]:
        """
        Safely convert a value to int.
        
        Args:
            value: Value to convert
            
        Returns:
            Int value or None
        """
        if value is None:
            return None
        try:
            return int(value)
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
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y', '%Y%m%d']:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
            return str(date_str)
        except Exception:
            return None
            
    def get_statistics(self) -> Dict[str, Any]:
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