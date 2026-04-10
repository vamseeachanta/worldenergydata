"""
BSEE Data Format Converter for Test Data Generation.

This module provides utilities to convert generic test data into BSEE-specific formats
required by the WorldEnergyData modules.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import random


class BSEEDataConverter:
    """Convert generic test data to BSEE-specific formats."""
    
    # BSEE Production Data Columns
    PRODUCTION_COLUMNS = {
        'PRODUCTION_DATE': 'YYYYMM format date',
        'API_WELL_NUMBER': '12-digit API number',
        'MON_O_PROD_VOL': 'Monthly oil production volume (BBL)',
        'MON_G_PROD_VOL': 'Monthly gas production volume (MCF)',
        'MON_W_PROD_VOL': 'Monthly water production volume (BBL)',
        'DAYS_ON_PROD': 'Days on production',
        'WELL_NAME': 'Well name identifier',
        'LEASE_NUMBER': 'OCS lease number',
        'PROD_FIELD_CODE': 'Production field code',
        'BSEE_COMPANY_CODE': 'Company code',
        'AVG_CHOKE_SIZE': 'Average choke size',
        'AVG_OIL_RATE': 'Average oil rate (BBL/day)',
        'AVG_GAS_RATE': 'Average gas rate (MCF/day)',
        'AVG_WTR_RATE': 'Average water rate (BBL/day)'
    }
    
    # BSEE Well Data Columns
    WELL_COLUMNS = {
        'API_WELL_NUMBER': '12-digit API number',
        'WELL_NAME': 'Well name',
        'SURFACE_AREA_CODE': 'Surface area/block',
        'SURFACE_BLOCK_NUMBER': 'Block number',
        'SURFACE_LEASE_NUMBER': 'Surface lease number',
        'BOREHOLE_STAT_CODE': 'Borehole status code',
        'WATER_DEPTH': 'Water depth (feet)',
        'WELL_SPUD_DATE': 'Spud date YYYYMMDD',
        'WELL_COMPLETION_DATE': 'Completion date YYYYMMDD',
        'TOTAL_DEPTH': 'Total depth (feet)',
        'MEASURED_DEPTH': 'Measured depth (feet)',
        'TRUE_VERTICAL_DEPTH': 'True vertical depth (feet)',
        'SURFACE_LATITUDE': 'Surface latitude',
        'SURFACE_LONGITUDE': 'Surface longitude',
        'STATUS_DATE': 'Status date YYYYMMDD'
    }
    
    # BSEE Lease Data Columns
    LEASE_COLUMNS = {
        'LEASE_NUMBER': 'OCS lease number',
        'LEASE_AREA_CODE': 'Area code',
        'LEASE_BLOCK_NUMBER': 'Block number',
        'LEASE_EFF_DATE': 'Effective date YYYYMMDD',
        'LEASE_EXPIR_DATE': 'Expiration date YYYYMMDD',
        'LEASE_AREA_SIZE': 'Area size (acres)',
        'WATER_DEPTH_MIN': 'Minimum water depth',
        'WATER_DEPTH_MAX': 'Maximum water depth',
        'LEASE_HOLDER': 'Lease holder name',
        'LEASE_STATUS': 'Lease status'
    }
    
    # BSEE Completion Data Columns
    COMPLETION_COLUMNS = {
        'API_WELL_NUMBER': '12-digit API number',
        'COMPLETION_NAME': 'Completion name',
        'COMPLETION_DATE': 'Completion date YYYYMMDD',
        'PERF_TOP_MD': 'Perforation top MD',
        'PERF_BOTTOM_MD': 'Perforation bottom MD',
        'PERF_TOP_TVD': 'Perforation top TVD',
        'PERF_BOTTOM_TVD': 'Perforation bottom TVD',
        'COMPLETION_TYPE': 'Completion type',
        'SAND_CONTROL': 'Sand control method',
        'RESERVOIR_NAME': 'Reservoir name'
    }
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the converter.
        
        Args:
            seed: Random seed for reproducible test data
        """
        if seed:
            random.seed(seed)
            np.random.seed(seed)
    
    def generate_api_number(self, state_code: str = "177", county_code: str = "104") -> str:
        """
        Generate a valid 12-digit API well number.
        
        Args:
            state_code: 2-3 digit state code (177 for federal OCS)
            county_code: 3 digit county/area code
            
        Returns:
            12-digit API number string
        """
        unique_well = str(random.randint(10000, 99999))
        sidetrack = str(random.randint(0, 9)).zfill(2)
        return f"{state_code}{county_code}{unique_well}{sidetrack}"
    
    def generate_production_data(
        self,
        num_wells: int = 5,
        num_months: int = 24,
        start_date: Optional[datetime] = None,
        field_name: str = "TEST_FIELD"
    ) -> pd.DataFrame:
        """
        Generate BSEE-formatted production data.
        
        Args:
            num_wells: Number of wells to generate
            num_months: Number of production months per well
            start_date: Production start date
            field_name: Field name for the data
            
        Returns:
            DataFrame with BSEE production format
        """
        if start_date is None:
            start_date = datetime(2020, 1, 1)
        
        data = []
        
        for well_idx in range(num_wells):
            api_number = self.generate_api_number()
            well_name = f"WELL_{well_idx+1:03d}"
            lease_number = f"OCS-G-{random.randint(30000, 40000)}"
            
            # Generate declining production profile
            initial_oil = random.uniform(1000, 5000)
            initial_gas = random.uniform(2000, 10000)
            decline_rate = random.uniform(0.02, 0.08)
            
            for month_idx in range(num_months):
                prod_date = start_date + timedelta(days=30 * month_idx)
                
                # Calculate production with exponential decline
                oil_prod = initial_oil * np.exp(-decline_rate * month_idx)
                gas_prod = initial_gas * np.exp(-decline_rate * month_idx)
                water_prod = random.uniform(50, 200) * (1 + month_idx * 0.1)
                
                # Random production days (accounting for downtime)
                days_on = random.randint(20, 30)
                
                row = {
                    'PRODUCTION_DATE': prod_date.strftime('%Y%m'),
                    'API_WELL_NUMBER': api_number,
                    'MON_O_PROD_VOL': round(oil_prod * days_on, 0),
                    'MON_G_PROD_VOL': round(gas_prod * days_on, 0),
                    'MON_W_PROD_VOL': round(water_prod * days_on, 0),
                    'DAYS_ON_PROD': days_on,
                    'WELL_NAME': well_name,
                    'LEASE_NUMBER': lease_number,
                    'PROD_FIELD_CODE': field_name,
                    'BSEE_COMPANY_CODE': f"CO{random.randint(100, 999)}",
                    'AVG_CHOKE_SIZE': round(random.uniform(20, 64), 1),
                    'AVG_OIL_RATE': round(oil_prod, 1),
                    'AVG_GAS_RATE': round(gas_prod, 1),
                    'AVG_WTR_RATE': round(water_prod, 1)
                }
                data.append(row)
        
        return pd.DataFrame(data)
    
    def generate_well_data(
        self,
        num_wells: int = 5,
        water_depth_range: tuple = (1000, 7000)
    ) -> pd.DataFrame:
        """
        Generate BSEE-formatted well data.
        
        Args:
            num_wells: Number of wells to generate
            water_depth_range: Range of water depths in feet
            
        Returns:
            DataFrame with BSEE well format
        """
        data = []
        base_date = datetime(2015, 1, 1)
        
        for well_idx in range(num_wells):
            api_number = self.generate_api_number()
            
            # Generate well dates
            spud_date = base_date + timedelta(days=random.randint(0, 1825))
            completion_date = spud_date + timedelta(days=random.randint(30, 180))
            
            # Generate depths
            water_depth = random.randint(*water_depth_range)
            total_depth = water_depth + random.randint(8000, 20000)
            tvd = total_depth - random.randint(0, 2000)
            
            row = {
                'API_WELL_NUMBER': api_number,
                'WELL_NAME': f"WELL_{well_idx+1:03d}",
                'SURFACE_AREA_CODE': 'GC',
                'SURFACE_BLOCK_NUMBER': str(random.randint(100, 999)),
                'SURFACE_LEASE_NUMBER': f"OCS-G-{random.randint(30000, 40000)}",
                'BOREHOLE_STAT_CODE': random.choice(['PA', 'TA', 'DA', 'SI']),
                'WATER_DEPTH': water_depth,
                'WELL_SPUD_DATE': spud_date.strftime('%Y%m%d'),
                'WELL_COMPLETION_DATE': completion_date.strftime('%Y%m%d'),
                'TOTAL_DEPTH': total_depth,
                'MEASURED_DEPTH': total_depth + random.randint(0, 5000),
                'TRUE_VERTICAL_DEPTH': tvd,
                'SURFACE_LATITUDE': round(random.uniform(27.0, 29.0), 6),
                'SURFACE_LONGITUDE': round(random.uniform(-94.0, -88.0), 6),
                'STATUS_DATE': completion_date.strftime('%Y%m%d')
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def generate_lease_data(self, num_leases: int = 3) -> pd.DataFrame:
        """
        Generate BSEE-formatted lease data.
        
        Args:
            num_leases: Number of leases to generate
            
        Returns:
            DataFrame with BSEE lease format
        """
        data = []
        base_date = datetime(2010, 1, 1)
        
        for lease_idx in range(num_leases):
            eff_date = base_date + timedelta(days=random.randint(0, 3650))
            expir_date = eff_date + timedelta(days=random.randint(1825, 3650))
            
            row = {
                'LEASE_NUMBER': f"OCS-G-{random.randint(30000, 40000)}",
                'LEASE_AREA_CODE': random.choice(['GC', 'MC', 'WR', 'AT']),
                'LEASE_BLOCK_NUMBER': str(random.randint(100, 999)),
                'LEASE_EFF_DATE': eff_date.strftime('%Y%m%d'),
                'LEASE_EXPIR_DATE': expir_date.strftime('%Y%m%d'),
                'LEASE_AREA_SIZE': random.randint(2000, 5760),
                'WATER_DEPTH_MIN': random.randint(500, 3000),
                'WATER_DEPTH_MAX': random.randint(3000, 8000),
                'LEASE_HOLDER': f"Test Company {lease_idx+1}",
                'LEASE_STATUS': random.choice(['ACTIVE', 'EXPIRED', 'RELINQUISHED'])
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def generate_completion_data(
        self,
        api_numbers: Optional[List[str]] = None,
        num_completions: int = 5
    ) -> pd.DataFrame:
        """
        Generate BSEE-formatted completion data.
        
        Args:
            api_numbers: List of API numbers to use
            num_completions: Number of completions if no API numbers provided
            
        Returns:
            DataFrame with BSEE completion format
        """
        if api_numbers is None:
            api_numbers = [self.generate_api_number() for _ in range(num_completions)]
        
        data = []
        base_date = datetime(2018, 1, 1)
        
        for idx, api_number in enumerate(api_numbers):
            completion_date = base_date + timedelta(days=random.randint(0, 1095))
            
            # Generate perforation depths
            top_md = random.randint(10000, 18000)
            bottom_md = top_md + random.randint(50, 500)
            top_tvd = top_md - random.randint(0, 1000)
            bottom_tvd = bottom_md - random.randint(0, 1000)
            
            row = {
                'API_WELL_NUMBER': api_number,
                'COMPLETION_NAME': f"COMP_{idx+1:03d}",
                'COMPLETION_DATE': completion_date.strftime('%Y%m%d'),
                'PERF_TOP_MD': top_md,
                'PERF_BOTTOM_MD': bottom_md,
                'PERF_TOP_TVD': top_tvd,
                'PERF_BOTTOM_TVD': bottom_tvd,
                'COMPLETION_TYPE': random.choice(['CASED_HOLE', 'OPEN_HOLE', 'GRAVEL_PACK']),
                'SAND_CONTROL': random.choice(['NONE', 'SCREEN', 'GRAVEL_PACK', 'FRAC_PACK']),
                'RESERVOIR_NAME': f"RESERVOIR_{chr(65 + idx % 26)}"
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def save_test_data(
        self,
        output_dir: Union[str, Path],
        prefix: str = "test"
    ) -> Dict[str, Path]:
        """
        Generate and save complete set of BSEE test data.
        
        Args:
            output_dir: Directory to save test data
            prefix: Prefix for file names
            
        Returns:
            Dictionary of data type to file path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        files = {}
        
        # Generate production data
        prod_df = self.generate_production_data()
        prod_file = output_dir / f"{prefix}_production.csv"
        prod_df.to_csv(prod_file, index=False)
        files['production'] = prod_file
        
        # Generate well data
        well_df = self.generate_well_data()
        well_file = output_dir / f"{prefix}_wells.csv"
        well_df.to_csv(well_file, index=False)
        files['wells'] = well_file
        
        # Generate lease data
        lease_df = self.generate_lease_data()
        lease_file = output_dir / f"{prefix}_leases.csv"
        lease_df.to_csv(lease_file, index=False)
        files['leases'] = lease_file
        
        # Generate completion data using well API numbers
        api_numbers = well_df['API_WELL_NUMBER'].tolist()
        comp_df = self.generate_completion_data(api_numbers)
        comp_file = output_dir / f"{prefix}_completions.csv"
        comp_df.to_csv(comp_file, index=False)
        files['completions'] = comp_file
        
        # Create documentation
        doc_file = output_dir / f"{prefix}_README.md"
        with open(doc_file, 'w') as f:
            f.write(self._generate_documentation())
        files['documentation'] = doc_file
        
        return files
    
    def _generate_documentation(self) -> str:
        """Generate documentation for the test data."""
        return """# BSEE Test Data Documentation

## Overview
This directory contains BSEE-formatted test data for WorldEnergyData testing.

## File Descriptions

### Production Data (test_production.csv)
- Monthly production volumes for oil, gas, and water
- Production dates in YYYYMM format
- API well numbers (12-digit format)
- Days on production and average rates

### Well Data (test_wells.csv)
- Well identification and location information
- Spud and completion dates in YYYYMMDD format
- Depth measurements (MD, TVD)
- Surface coordinates

### Lease Data (test_leases.csv)
- OCS lease numbers and block information
- Lease effective and expiration dates
- Water depth ranges
- Lease holder information

### Completion Data (test_completions.csv)
- Completion information linked to wells
- Perforation depths (MD and TVD)
- Completion types and sand control methods
- Reservoir names

## Column Specifications

All files follow official BSEE data formats:
- Dates: YYYYMM (monthly) or YYYYMMDD (daily)
- API Numbers: 12-digit format (state + county + well + sidetrack)
- Volumes: Integer values in BBL (oil/water) or MCF (gas)
- Depths: Integer values in feet

## Usage

```python
import pandas as pd

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)

# Load production data
production = pd.read_csv('test_production.csv')

# Convert date column to datetime
production['PRODUCTION_DATE'] = pd.to_datetime(
    production['PRODUCTION_DATE'], 
    format='%Y%m'
)
```

## Data Quality Notes

- All data is synthetic and for testing purposes only
- Production profiles follow realistic decline curves
- Well locations are within Gulf of Mexico OCS blocks
- Dates are internally consistent (spud < completion)
"""


def create_sample_bsee_data():
    """Create sample BSEE data files for testing."""
    converter = BSEEDataConverter(seed=42)
    
    # Create test data directory
    test_data_dir = Path("tests/data/bsee_test_data")
    
    # Generate and save all test data
    files = converter.save_test_data(test_data_dir, prefix="sample")
    
    logger.info("Created BSEE test data files:")
    for data_type, file_path in files.items():
        logger.info(f"  {data_type}: {file_path}")
    
    return files


if __name__ == "__main__":
    # Generate sample data when run directly
    create_sample_bsee_data()