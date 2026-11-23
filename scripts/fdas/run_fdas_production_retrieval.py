#!/usr/bin/env python3
"""
ABOUTME: Simplified FDAS V30 production retrieval working directly with ZIP files
ABOUTME: Generates four outputs: wells by lease, production by lease/API/field
"""

import os
import sys
import pandas as pd
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


class FDASProductionRetriever:
    """Retrieve production data for FDAS V30 leases from ZIP files"""
    
    def __init__(self, leases_file: str, production_zip_dir: str, output_dir: str = None):
        """
        Initialize production retriever
        
        Args:
            leases_file: Path to leases.xlsx file
            production_zip_dir: Directory containing production ZIP files
            output_dir: Output directory for results
        """
        self.leases_file = Path(leases_file)
        self.production_zip_dir = Path(production_zip_dir)
        self.output_dir = Path(output_dir) if output_dir else Path('./results/fdas_production')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load leases
        self.leases_df = pd.read_excel(self.leases_file)
        logger.info(f"Loaded {len(self.leases_df)} leases from {self.leases_file}")
        
        # Column names for BSEE production data
        self.column_names = [
            'LEASE_NUMBER', 'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD', 
            'PRODUCT_CODE', 'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL', 
            'API_WELL_NUMBER', 'WELL_STAT_CD', 'AREA_CODE_BLOCK_NUM', 'OPERATOR_NUM', 
            'SORT_NAME', 'BOEM_FIELD', 'INJECTION_VOLUME', 'PROD_INTERVAL_CD', 
            'FIRST_PROD_DATE', 'UNIT_AGT_NUMBER', 'UNIT_ALOC_SUFFIX'
        ]
    
    def load_production_from_zips(self) -> pd.DataFrame:
        """
        Load production data from ZIP files
        
        Returns:
            DataFrame with production data for FDAS leases
        """
        logger.info(f"Loading production data from ZIP files in {self.production_zip_dir}")
        
        zip_files = sorted(list(self.production_zip_dir.glob('*.zip')))
        logger.info(f"Found {len(zip_files)} ZIP files to process")
        
        if not zip_files:
            logger.error(f"No ZIP files found in {self.production_zip_dir}")
            return pd.DataFrame()
        
        # Get lease numbers to filter
        lease_numbers = set()
        for lease in self.leases_df['LEASE_NUM'].tolist():
            lease_str = str(lease).upper().strip()
            # Add both formats
            if lease_str.startswith('G'):
                lease_numbers.add(lease_str)
                lease_numbers.add(lease_str[1:].zfill(5))  # Remove G, pad to 5 digits
            else:
                lease_numbers.add(lease_str.zfill(5))
                lease_numbers.add('G' + lease_str)
        
        logger.info(f"Filtering for {len(self.leases_df)} unique leases")
        
        all_production = []
        
        for idx, zip_file in enumerate(zip_files, 1):
            try:
                logger.info(f"Processing {idx}/{len(zip_files)}: {zip_file.name}")
                
                with zipfile.ZipFile(zip_file, 'r') as z:
                    txt_file = z.namelist()[0]
                    
                    with z.open(txt_file) as f:
                        # Read production data
                        df = pd.read_csv(f, 
                                        delimiter=',',
                                        quotechar='"',
                                        names=self.column_names,
                                        dtype=str)
                        
                        # Strip whitespace from lease numbers
                        df['LEASE_NUMBER'] = df['LEASE_NUMBER'].str.strip()
                        
                        # Filter for FDAS leases
                        df_filtered = df[df['LEASE_NUMBER'].isin(lease_numbers)]
                        
                        if len(df_filtered) > 0:
                            logger.info(f"  Found {len(df_filtered):,} records for FDAS leases")
                            all_production.append(df_filtered)
                        
            except Exception as e:
                logger.error(f"Error processing {zip_file}: {e}")
                continue
        
        if all_production:
            production_df = pd.concat(all_production, ignore_index=True)
            logger.info(f"\nTotal production records: {len(production_df):,}")
            
            # Convert numeric columns
            numeric_cols = ['DAYS_ON_PROD', 'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL', 'INJECTION_VOLUME']
            for col in numeric_cols:
                production_df[col] = pd.to_numeric(production_df[col], errors='coerce').fillna(0)
            
            return production_df
        else:
            logger.warning("No production data found for FDAS leases")
            return pd.DataFrame()
    
    def generate_wells_by_lease(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """Generate output a: Wells by lease"""
        logger.info("Generating wells by lease...")
        
        wells_by_lease = production_df.groupby('LEASE_NUMBER')['API_WELL_NUMBER'].apply(
            lambda x: sorted(x.unique())
        ).reset_index()
        wells_by_lease.columns = ['LEASE_NUMBER', 'API_WELLS']
        wells_by_lease['WELL_COUNT'] = wells_by_lease['API_WELLS'].apply(len)
        
        # Merge with lease metadata
        lease_info = self.leases_df[['LEASE_NUM', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM']].copy()
        wells_by_lease['LEASE_NUM_MATCH'] = wells_by_lease['LEASE_NUMBER'].apply(
            lambda x: 'G' + str(x) if not str(x).startswith('G') else str(x)
        )
        
        result = pd.merge(lease_info, wells_by_lease, left_on='LEASE_NUM', right_on='LEASE_NUM_MATCH', how='inner')
        
        # Expand into rows
        expanded_rows = []
        for _, row in result.iterrows():
            for api in row['API_WELLS']:
                expanded_rows.append({
                    'LEASE_NUMBER': row['LEASE_NUM'],
                    'LEASE_NAME': row['LEASE_NAME'],
                    'DEV_NAME': row['DEV_NAME'],
                    'DEV_SYSTEM': row['DEV_SYSTEM'],
                    'API_WELL_NUMBER': api,
                    'WELL_COUNT': row['WELL_COUNT']
                })
        
        return pd.DataFrame(expanded_rows)
    
    def generate_production_by_lease(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """Generate output b: Production by lease"""
        logger.info("Generating production by lease...")
        
        lease_prod = production_df.groupby(['LEASE_NUMBER', 'PRODUCTION_DATE']).agg({
            'MON_O_PROD_VOL': 'sum',
            'MON_G_PROD_VOL': 'sum',
            'MON_WTR_PROD_VOL': 'sum',
            'DAYS_ON_PROD': 'sum',
            'API_WELL_NUMBER': 'nunique'
        }).reset_index()
        
        lease_prod.columns = ['LEASE_NUMBER', 'PRODUCTION_DATE', 'OIL_BBLS', 'GAS_MCF', 'WATER_BBLS', 'TOTAL_DAYS_ON_PROD', 'ACTIVE_WELL_COUNT']
        
        lease_prod['OIL_RATE_BOPD'] = (lease_prod['OIL_BBLS'] / lease_prod['TOTAL_DAYS_ON_PROD']).fillna(0)
        lease_prod['GAS_RATE_MCFD'] = (lease_prod['GAS_MCF'] / lease_prod['TOTAL_DAYS_ON_PROD']).fillna(0)
        
        lease_prod = lease_prod.sort_values(['LEASE_NUMBER', 'PRODUCTION_DATE'])
        lease_prod['CUMULATIVE_OIL_MMBBL'] = lease_prod.groupby('LEASE_NUMBER')['OIL_BBLS'].cumsum() / 1_000_000
        lease_prod['CUMULATIVE_GAS_BCF'] = lease_prod.groupby('LEASE_NUMBER')['GAS_MCF'].cumsum() / 1_000_000
        
        # Add metadata
        lease_info = self.leases_df[['LEASE_NUM', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM']].copy()
        lease_prod['LEASE_NUM_MATCH'] = lease_prod['LEASE_NUMBER'].apply(
            lambda x: 'G' + str(x) if not str(x).startswith('G') else str(x)
        )
        result = pd.merge(lease_prod, lease_info, left_on='LEASE_NUM_MATCH', right_on='LEASE_NUM', how='left')
        
        return result[['LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM', 'PRODUCTION_DATE',
                      'OIL_BBLS', 'GAS_MCF', 'WATER_BBLS', 'OIL_RATE_BOPD', 'GAS_RATE_MCFD',
                      'CUMULATIVE_OIL_MMBBL', 'CUMULATIVE_GAS_BCF', 'ACTIVE_WELL_COUNT']]
    
    def generate_production_by_api(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """Generate output c: Production by API"""
        logger.info("Generating production by API...")
        
        df = production_df.copy()
        df['OIL_RATE_BOPD'] = (df['MON_O_PROD_VOL'] / df['DAYS_ON_PROD']).fillna(0)
        df['GAS_RATE_MCFD'] = (df['MON_G_PROD_VOL'] / df['DAYS_ON_PROD']).fillna(0)
        df['GOR_MCF_BBL'] = (df['MON_G_PROD_VOL'] / df['MON_O_PROD_VOL']).replace([float('inf'), -float('inf')], 0).fillna(0)
        
        total_liquid = df['MON_O_PROD_VOL'] + df['MON_WTR_PROD_VOL']
        df['WATER_CUT_PCT'] = ((df['MON_WTR_PROD_VOL'] / total_liquid) * 100).fillna(0)
        
        df = df.sort_values(['API_WELL_NUMBER', 'PRODUCTION_DATE'])
        df['CUMULATIVE_OIL_MMBBL'] = df.groupby('API_WELL_NUMBER')['MON_O_PROD_VOL'].cumsum() / 1_000_000
        df['CUMULATIVE_GAS_BCF'] = df.groupby('API_WELL_NUMBER')['MON_G_PROD_VOL'].cumsum() / 1_000_000
        
        # Add metadata
        lease_info = self.leases_df[['LEASE_NUM', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM']].copy()
        df['LEASE_NUM_MATCH'] = df['LEASE_NUMBER'].apply(
            lambda x: 'G' + str(x) if not str(x).startswith('G') else str(x)
        )
        result = pd.merge(df, lease_info, left_on='LEASE_NUM_MATCH', right_on='LEASE_NUM', how='left')
        
        return result[['API_WELL_NUMBER', 'LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM',
                      'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD',
                      'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL',
                      'OIL_RATE_BOPD', 'GAS_RATE_MCFD', 'GOR_MCF_BBL', 'WATER_CUT_PCT',
                      'CUMULATIVE_OIL_MMBBL', 'CUMULATIVE_GAS_BCF', 'BOEM_FIELD', 'OPERATOR_NUM', 'SORT_NAME']]
    
    def generate_production_by_field(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """Generate output d: Production by field"""
        logger.info("Generating production by field...")
        
        # Add metadata
        lease_info = self.leases_df[['LEASE_NUM', 'DEV_NAME', 'DEV_SYSTEM']].copy()
        df = production_df.copy()
        df['LEASE_NUM_MATCH'] = df['LEASE_NUMBER'].apply(
            lambda x: 'G' + str(x) if not str(x).startswith('G') else str(x)
        )
        df = pd.merge(df, lease_info, left_on='LEASE_NUM_MATCH', right_on='LEASE_NUM', how='left')
        
        # Aggregate by field
        field_prod = df.groupby(['DEV_NAME', 'DEV_SYSTEM', 'PRODUCTION_DATE']).agg({
            'MON_O_PROD_VOL': 'sum',
            'MON_G_PROD_VOL': 'sum',
            'MON_WTR_PROD_VOL': 'sum',
            'DAYS_ON_PROD': 'sum',
            'API_WELL_NUMBER': 'nunique',
            'LEASE_NUMBER': 'nunique'
        }).reset_index()
        
        field_prod.columns = ['FIELD_NAME', 'DEV_SYSTEM', 'PRODUCTION_DATE', 'OIL_BBLS', 'GAS_MCF', 'WATER_BBLS',
                             'TOTAL_DAYS_ON_PROD', 'ACTIVE_WELL_COUNT', 'ACTIVE_LEASE_COUNT']
        
        field_prod['OIL_RATE_BOPD'] = (field_prod['OIL_BBLS'] / field_prod['TOTAL_DAYS_ON_PROD']).fillna(0)
        field_prod['GAS_RATE_MCFD'] = (field_prod['GAS_MCF'] / field_prod['TOTAL_DAYS_ON_PROD']).fillna(0)
        field_prod['GOR_MCF_BBL'] = (field_prod['GAS_MCF'] / field_prod['OIL_BBLS']).replace([float('inf'), -float('inf')], 0).fillna(0)
        
        field_prod = field_prod.sort_values(['FIELD_NAME', 'PRODUCTION_DATE'])
        field_prod['CUMULATIVE_OIL_MMBBL'] = field_prod.groupby('FIELD_NAME')['OIL_BBLS'].cumsum() / 1_000_000
        field_prod['CUMULATIVE_GAS_BCF'] = field_prod.groupby('FIELD_NAME')['GAS_MCF'].cumsum() / 1_000_000
        
        return field_prod
    
    def save_outputs(self, wells_df, lease_df, api_df, field_df):
        """Save all outputs"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        files = {
            'a_wells_by_lease': wells_df,
            'b_production_by_lease': lease_df,
            'c_production_by_api': api_df,
            'd_production_by_field': field_df
        }
        
        for name, df in files.items():
            csv_file = self.output_dir / f'{name}_{timestamp}.csv'
            df.to_csv(csv_file, index=False)
            logger.info(f"Saved {name}: {csv_file} ({len(df):,} rows)")
        
        # Excel workbook
        excel_file = self.output_dir / f'fdas_production_complete_{timestamp}.xlsx'
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            wells_df.to_excel(writer, sheet_name='Wells_by_Lease', index=False)
            lease_df.to_excel(writer, sheet_name='Production_by_Lease', index=False)
            api_df.to_excel(writer, sheet_name='Production_by_API', index=False)
            field_df.to_excel(writer, sheet_name='Production_by_Field', index=False)
        
        logger.info(f"Saved Excel workbook: {excel_file}")
    
    def run(self):
        """Execute the complete production retrieval workflow"""
        
        logger.info("=" * 80)
        logger.info("FDAS V30 Production Data Retrieval")
        logger.info("=" * 80)
        
        # Load production data
        logger.info("\nStep 1: Loading production data from ZIP files...")
        production_df = self.load_production_from_zips()
        
        if production_df.empty:
            logger.error("No production data loaded. Exiting.")
            return
        
        # Generate outputs
        logger.info("\nStep 2: Generating outputs...")
        
        logger.info("\n  a. Wells by lease...")
        wells_df = self.generate_wells_by_lease(production_df)
        
        logger.info("\n  b. Production by lease...")
        lease_df = self.generate_production_by_lease(production_df)
        
        logger.info("\n  c. Production by API...")
        api_df = self.generate_production_by_api(production_df)
        
        logger.info("\n  d. Production by field...")
        field_df = self.generate_production_by_field(production_df)
        
        # Save outputs
        logger.info("\nStep 3: Saving outputs...")
        self.save_outputs(wells_df, lease_df, api_df, field_df)
        
        logger.info("\n" + "=" * 80)
        logger.info("COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"\nResults saved to: {self.output_dir}")
        logger.info(f"\nTotal records generated:")
        logger.info(f"  - Wells by lease: {len(wells_df):,}")
        logger.info(f"  - Production by lease: {len(lease_df):,}")
        logger.info(f"  - Production by API: {len(api_df):,}")
        logger.info(f"  - Production by field: {len(field_df):,}")


def main():
    """Main entry point"""
    
    # Configure logger
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Set paths
    project_root = Path(__file__).parent.parent
    leases_file = project_root / 'docs' / 'modules' / 'bsee' / 'analysis' / 'production' / 'FDAS_V30' / 'leases.xlsx'
    production_zip_dir = project_root / 'data' / 'modules' / 'bsee' / 'zip' / 'historical_production_yearly'
    output_dir = project_root / 'results' / 'fdas_production'
    
    # Check paths
    if not leases_file.exists():
        logger.error(f"Leases file not found: {leases_file}")
        return 1
    
    if not production_zip_dir.exists():
        logger.error(f"Production ZIP directory not found: {production_zip_dir}")
        return 1
    
    # Create retriever and run
    try:
        retriever = FDASProductionRetriever(
            leases_file=str(leases_file),
            production_zip_dir=str(production_zip_dir),
            output_dir=str(output_dir)
        )
        
        retriever.run()
        
        return 0
        
    except Exception as e:
        logger.exception(f"Error during production retrieval: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
