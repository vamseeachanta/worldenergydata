#!/usr/bin/env python3
"""
ABOUTME: Retrieve production data for all FDAS V30 leases
ABOUTME: Generates four outputs: wells by lease, production by lease, by API, by field
"""

import os
import sys
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from worldenergydata.modules.bsee.data._from_bin.lease_data import LeaseData
from worldenergydata.modules.bsee.data._from_zip.production_data import GetProdDataFromZip


class FDASProductionRetriever:
    """Retrieve production data for FDAS V30 leases"""
    
    def __init__(self, leases_file: str, output_dir: str = None):
        """
        Initialize production retriever
        
        Args:
            leases_file: Path to leases.xlsx file
            output_dir: Output directory for results (default: ./results/fdas_production)
        """
        self.leases_file = Path(leases_file)
        self.output_dir = Path(output_dir) if output_dir else Path('./results/fdas_production')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load leases
        self.leases_df = pd.read_excel(self.leases_file)
        logger.info(f"Loaded {len(self.leases_df)} leases from {self.leases_file}")
        
        # Initialize data loaders
        self.production_loader = GetProdDataFromZip()
        
        # Storage for results
        self.wells_by_lease = {}
        self.production_by_api = {}
        self.production_raw = pd.DataFrame()
        
    def get_configuration(self) -> Dict:
        """
        Get configuration for data loading
        
        Returns:
            Configuration dictionary
        """
        # Get project root and data paths
        project_root = Path(__file__).parent.parent
        
        cfg = {
            'parameters': {
                'filepath': {
                    'production': {
                        'zip': str(project_root / 'data' / 'modules' / 'bsee' / 'zip' / 'historical_production_yearly'),
                        'bin': str(project_root / 'data' / 'modules' / 'bsee' / 'bin' / 'historical_production_yearly')
                    },
                    'bin_dir': str(project_root / 'data' / 'modules' / 'bsee' / 'bin')
                }
            },
            'Analysis': {
                'result_folder': str(self.output_dir / 'temp')
            }
        }
        
        # Create temp folder
        Path(cfg['Analysis']['result_folder']).mkdir(parents=True, exist_ok=True)
        Path(cfg['Analysis']['result_folder'], 'Data').mkdir(parents=True, exist_ok=True)
        
        return cfg
    
    def load_production_from_binary(self, cfg: Dict) -> pd.DataFrame:
        """
        Load all production data from binary files
        
        Args:
            cfg: Configuration dictionary
            
        Returns:
            DataFrame with all production data
        """
        logger.info("Loading production data from binary files...")
        
        folder_path_bin = cfg['parameters']['filepath']['production']['bin']
        
        if not os.path.exists(folder_path_bin):
            logger.error(f"Binary folder not found: {folder_path_bin}")
            logger.info("Please ensure production data is downloaded and converted to binary format")
            return pd.DataFrame()
        
        column_names = [
            'LEASE_NUMBER', 'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD', 
            'PRODUCT_CODE', 'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL', 
            'API_WELL_NUMBER', 'WELL_STAT_CD', 'AREA_CODE_BLOCK_NUM', 'OPERATOR_NUM', 
            'SORT_NAME', 'BOEM_FIELD', 'INJECTION_VOLUME', 'PROD_INTERVAL_CD', 
            'FIRST_PROD_DATE', 'UNIT_AGT_NUMBER', 'UNIT_ALOC_SUFFIX'
        ]
        
        all_production = []
        bin_files = list(Path(folder_path_bin).glob('*.bin'))
        
        logger.info(f"Found {len(bin_files)} binary files to process")
        
        for idx, file_path in enumerate(bin_files, 1):
            try:
                with open(file_path, 'rb') as file:
                    df = pickle.load(file)
                    
                    if column_names and len(df.columns) == len(column_names):
                        df.columns = column_names
                    
                    all_production.append(df)
                    
                if idx % 10 == 0:
                    logger.info(f"Processed {idx}/{len(bin_files)} files...")
                    
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                continue
        
        if all_production:
            production_df = pd.concat(all_production, ignore_index=True)
            logger.info(f"Loaded {len(production_df):,} production records")
            return production_df
        else:
            logger.warning("No production data loaded")
            return pd.DataFrame()
    
    def filter_production_by_leases(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter production data for FDAS leases
        
        Args:
            production_df: Full production DataFrame
            
        Returns:
            Filtered production DataFrame
        """
        # Get lease numbers (handle both G17001 and 17001 formats)
        lease_numbers = self.leases_df['LEASE_NUM'].tolist()
        
        # Create filter for both formats
        lease_filters = []
        for lease in lease_numbers:
            lease_str = str(lease).upper()
            if lease_str.startswith('G'):
                # Try both G17001 and 17001
                lease_filters.append(lease_str)
                lease_filters.append(lease_str[1:])  # Remove 'G'
            else:
                # Try both 17001 and G17001
                lease_filters.append(lease_str)
                lease_filters.append('G' + lease_str)
        
        logger.info(f"Filtering for {len(lease_numbers)} unique leases...")
        
        # Filter production data
        filtered_df = production_df[production_df['LEASE_NUMBER'].isin(lease_filters)].copy()
        
        logger.info(f"Found {len(filtered_df):,} production records for FDAS leases")
        
        return filtered_df
    
    def generate_wells_by_lease(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate output a: Wells by lease
        
        Args:
            production_df: Production DataFrame
            
        Returns:
            DataFrame with wells grouped by lease
        """
        logger.info("Generating wells by lease...")
        
        # Group wells by lease
        wells_by_lease = production_df.groupby('LEASE_NUMBER')['API_WELL_NUMBER'].apply(
            lambda x: sorted(x.unique())
        ).reset_index()
        
        wells_by_lease.columns = ['LEASE_NUMBER', 'API_WELLS']
        
        # Add well count
        wells_by_lease['WELL_COUNT'] = wells_by_lease['API_WELLS'].apply(len)
        
        # Merge with lease metadata
        lease_info = self.leases_df[['LEASE_NUM', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM']].copy()
        
        # Try matching with and without 'G' prefix
        wells_by_lease['LEASE_NUM_MATCH'] = wells_by_lease['LEASE_NUMBER'].apply(
            lambda x: 'G' + str(x) if not str(x).startswith('G') else str(x)
        )
        
        result = pd.merge(
            lease_info,
            wells_by_lease,
            left_on='LEASE_NUM',
            right_on='LEASE_NUM_MATCH',
            how='inner'
        )
        
        # Expand API wells into separate rows for easier viewing
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
        
        expanded_df = pd.DataFrame(expanded_rows)
        
        logger.info(f"Found {len(expanded_df)} wells across {result['LEASE_NUM'].nunique()} leases")
        
        return expanded_df
    
    def generate_production_by_lease(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate output b: Production aggregated by lease
        
        Args:
            production_df: Production DataFrame
            
        Returns:
            DataFrame with production aggregated by lease and month
        """
        logger.info("Generating production by lease...")
        
        # Aggregate production by lease and date
        lease_production = production_df.groupby(['LEASE_NUMBER', 'PRODUCTION_DATE']).agg({
            'MON_O_PROD_VOL': 'sum',
            'MON_G_PROD_VOL': 'sum',
            'MON_WTR_PROD_VOL': 'sum',
            'DAYS_ON_PROD': 'sum',
            'API_WELL_NUMBER': 'nunique'
        }).reset_index()
        
        lease_production.columns = [
            'LEASE_NUMBER', 'PRODUCTION_DATE', 
            'OIL_BBLS', 'GAS_MCF', 'WATER_BBLS',
            'TOTAL_DAYS_ON_PROD', 'ACTIVE_WELL_COUNT'
        ]
        
        # Calculate rates
        lease_production['OIL_RATE_BOPD'] = (
            lease_production['OIL_BBLS'] / lease_production['TOTAL_DAYS_ON_PROD']
        ).fillna(0)
        
        lease_production['GAS_RATE_MCFD'] = (
            lease_production['GAS_MCF'] / lease_production['TOTAL_DAYS_ON_PROD']
        ).fillna(0)
        
        # Calculate cumulative production by lease
        lease_production = lease_production.sort_values(['LEASE_NUMBER', 'PRODUCTION_DATE'])
        
        lease_production['CUMULATIVE_OIL_BBLS'] = lease_production.groupby('LEASE_NUMBER')['OIL_BBLS'].cumsum()
        lease_production['CUMULATIVE_GAS_MCF'] = lease_production.groupby('LEASE_NUMBER')['GAS_MCF'].cumsum()
        
        # Convert to MMBBL and BCF
        lease_production['CUMULATIVE_OIL_MMBBL'] = lease_production['CUMULATIVE_OIL_BBLS'] / 1_000_000
        lease_production['CUMULATIVE_GAS_BCF'] = lease_production['CUMULATIVE_GAS_MCF'] / 1_000_000
        
        # Add lease metadata
        lease_info = self.leases_df[['LEASE_NUM', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM']].copy()
        
        # Match lease numbers
        lease_production['LEASE_NUM_MATCH'] = lease_production['LEASE_NUMBER'].apply(
            lambda x: 'G' + str(x) if not str(x).startswith('G') else str(x)
        )
        
        result = pd.merge(
            lease_production,
            lease_info,
            left_on='LEASE_NUM_MATCH',
            right_on='LEASE_NUM',
            how='left'
        )
        
        # Reorder columns
        cols = [
            'LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM', 'PRODUCTION_DATE',
            'OIL_BBLS', 'GAS_MCF', 'WATER_BBLS', 'OIL_RATE_BOPD', 'GAS_RATE_MCFD',
            'CUMULATIVE_OIL_MMBBL', 'CUMULATIVE_GAS_BCF',
            'ACTIVE_WELL_COUNT', 'TOTAL_DAYS_ON_PROD'
        ]
        
        result = result[cols]
        
        logger.info(f"Generated {len(result):,} lease-month production records")
        
        return result
    
    def generate_production_by_api(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate output c: Production by API (individual wells)
        
        Args:
            production_df: Production DataFrame
            
        Returns:
            DataFrame with production by API12 well
        """
        logger.info("Generating production by API...")
        
        # Add calculated fields
        production_df = production_df.copy()
        
        # Calculate production rates
        production_df['OIL_RATE_BOPD'] = (
            production_df['MON_O_PROD_VOL'] / production_df['DAYS_ON_PROD']
        ).fillna(0)
        
        production_df['GAS_RATE_MCFD'] = (
            production_df['MON_G_PROD_VOL'] / production_df['DAYS_ON_PROD']
        ).fillna(0)
        
        production_df['WATER_RATE_BWD'] = (
            production_df['MON_WTR_PROD_VOL'] / production_df['DAYS_ON_PROD']
        ).fillna(0)
        
        # Calculate GOR and Water Cut
        production_df['GOR_MCF_BBL'] = (
            production_df['MON_G_PROD_VOL'] / production_df['MON_O_PROD_VOL']
        ).replace([float('inf'), -float('inf')], 0).fillna(0)
        
        total_liquid = production_df['MON_O_PROD_VOL'] + production_df['MON_WTR_PROD_VOL']
        production_df['WATER_CUT_PCT'] = (
            (production_df['MON_WTR_PROD_VOL'] / total_liquid) * 100
        ).fillna(0)
        
        # Sort by API and date
        production_df = production_df.sort_values(['API_WELL_NUMBER', 'PRODUCTION_DATE'])
        
        # Calculate cumulative production by well
        production_df['CUMULATIVE_OIL_BBLS'] = production_df.groupby('API_WELL_NUMBER')['MON_O_PROD_VOL'].cumsum()
        production_df['CUMULATIVE_GAS_MCF'] = production_df.groupby('API_WELL_NUMBER')['MON_G_PROD_VOL'].cumsum()
        
        # Convert to MMBBL and BCF
        production_df['CUMULATIVE_OIL_MMBBL'] = production_df['CUMULATIVE_OIL_BBLS'] / 1_000_000
        production_df['CUMULATIVE_GAS_BCF'] = production_df['CUMULATIVE_GAS_MCF'] / 1_000_000
        
        # Add lease metadata
        lease_info = self.leases_df[['LEASE_NUM', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM']].copy()
        
        production_df['LEASE_NUM_MATCH'] = production_df['LEASE_NUMBER'].apply(
            lambda x: 'G' + str(x) if not str(x).startswith('G') else str(x)
        )
        
        result = pd.merge(
            production_df,
            lease_info,
            left_on='LEASE_NUM_MATCH',
            right_on='LEASE_NUM',
            how='left'
        )
        
        # Select and reorder columns
        cols = [
            'API_WELL_NUMBER', 'LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM',
            'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD',
            'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL',
            'OIL_RATE_BOPD', 'GAS_RATE_MCFD', 'WATER_RATE_BWD',
            'GOR_MCF_BBL', 'WATER_CUT_PCT',
            'CUMULATIVE_OIL_MMBBL', 'CUMULATIVE_GAS_BCF',
            'BOEM_FIELD', 'AREA_CODE_BLOCK_NUM', 'OPERATOR_NUM', 'SORT_NAME'
        ]
        
        result = result[[col for col in cols if col in result.columns]]
        
        logger.info(f"Generated {len(result):,} API-month production records for {result['API_WELL_NUMBER'].nunique()} wells")
        
        return result
    
    def generate_production_by_field(self, production_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate output d: Production aggregated by field
        
        Args:
            production_df: Production DataFrame
            
        Returns:
            DataFrame with production aggregated by field and month
        """
        logger.info("Generating production by field...")
        
        # Add lease metadata first
        lease_info = self.leases_df[['LEASE_NUM', 'DEV_NAME', 'DEV_SYSTEM']].copy()
        
        production_with_dev = production_df.copy()
        production_with_dev['LEASE_NUM_MATCH'] = production_with_dev['LEASE_NUMBER'].apply(
            lambda x: 'G' + str(x) if not str(x).startswith('G') else str(x)
        )
        
        production_with_dev = pd.merge(
            production_with_dev,
            lease_info,
            left_on='LEASE_NUM_MATCH',
            right_on='LEASE_NUM',
            how='left'
        )
        
        # Aggregate by development/field and date
        field_production = production_with_dev.groupby(['DEV_NAME', 'DEV_SYSTEM', 'PRODUCTION_DATE']).agg({
            'MON_O_PROD_VOL': 'sum',
            'MON_G_PROD_VOL': 'sum',
            'MON_WTR_PROD_VOL': 'sum',
            'DAYS_ON_PROD': 'sum',
            'API_WELL_NUMBER': 'nunique',
            'LEASE_NUMBER': 'nunique'
        }).reset_index()
        
        field_production.columns = [
            'FIELD_NAME', 'DEV_SYSTEM', 'PRODUCTION_DATE',
            'OIL_BBLS', 'GAS_MCF', 'WATER_BBLS',
            'TOTAL_DAYS_ON_PROD', 'ACTIVE_WELL_COUNT', 'ACTIVE_LEASE_COUNT'
        ]
        
        # Calculate rates
        field_production['OIL_RATE_BOPD'] = (
            field_production['OIL_BBLS'] / field_production['TOTAL_DAYS_ON_PROD']
        ).fillna(0)
        
        field_production['GAS_RATE_MCFD'] = (
            field_production['GAS_MCF'] / field_production['TOTAL_DAYS_ON_PROD']
        ).fillna(0)
        
        # Calculate GOR
        field_production['GOR_MCF_BBL'] = (
            field_production['GAS_MCF'] / field_production['OIL_BBLS']
        ).replace([float('inf'), -float('inf')], 0).fillna(0)
        
        # Calculate cumulative production by field
        field_production = field_production.sort_values(['FIELD_NAME', 'PRODUCTION_DATE'])
        
        field_production['CUMULATIVE_OIL_BBLS'] = field_production.groupby('FIELD_NAME')['OIL_BBLS'].cumsum()
        field_production['CUMULATIVE_GAS_MCF'] = field_production.groupby('FIELD_NAME')['GAS_MCF'].cumsum()
        
        # Convert to MMBBL and BCF
        field_production['CUMULATIVE_OIL_MMBBL'] = field_production['CUMULATIVE_OIL_BBLS'] / 1_000_000
        field_production['CUMULATIVE_GAS_BCF'] = field_production['CUMULATIVE_GAS_MCF'] / 1_000_000
        
        # Reorder columns
        cols = [
            'FIELD_NAME', 'DEV_SYSTEM', 'PRODUCTION_DATE',
            'OIL_BBLS', 'GAS_MCF', 'WATER_BBLS',
            'OIL_RATE_BOPD', 'GAS_RATE_MCFD', 'GOR_MCF_BBL',
            'CUMULATIVE_OIL_MMBBL', 'CUMULATIVE_GAS_BCF',
            'ACTIVE_WELL_COUNT', 'ACTIVE_LEASE_COUNT', 'TOTAL_DAYS_ON_PROD'
        ]
        
        field_production = field_production[cols]
        
        logger.info(f"Generated {len(field_production):,} field-month production records for {field_production['FIELD_NAME'].nunique()} fields")
        
        return field_production
    
    def generate_summary_statistics(self, wells_df: pd.DataFrame, 
                                   lease_df: pd.DataFrame,
                                   api_df: pd.DataFrame,
                                   field_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate summary statistics across all outputs
        
        Returns:
            Summary statistics DataFrame
        """
        logger.info("Generating summary statistics...")
        
        summary_data = []
        
        # Overall statistics
        summary_data.append({
            'Category': 'Overall',
            'Metric': 'Total Leases',
            'Value': f"{wells_df['LEASE_NUMBER'].nunique()}"
        })
        
        summary_data.append({
            'Category': 'Overall',
            'Metric': 'Total Wells',
            'Value': f"{wells_df['API_WELL_NUMBER'].nunique()}"
        })
        
        summary_data.append({
            'Category': 'Overall',
            'Metric': 'Total Fields',
            'Value': f"{field_df['FIELD_NAME'].nunique()}"
        })
        
        # Production totals
        total_oil = api_df.groupby('API_WELL_NUMBER')['CUMULATIVE_OIL_MMBBL'].max().sum()
        total_gas = api_df.groupby('API_WELL_NUMBER')['CUMULATIVE_GAS_BCF'].max().sum()
        
        summary_data.append({
            'Category': 'Production',
            'Metric': 'Total Cumulative Oil (MMBBL)',
            'Value': f"{total_oil:.2f}"
        })
        
        summary_data.append({
            'Category': 'Production',
            'Metric': 'Total Cumulative Gas (BCF)',
            'Value': f"{total_gas:.2f}"
        })
        
        # By field
        field_summary = field_df.groupby('FIELD_NAME').agg({
            'CUMULATIVE_OIL_MMBBL': 'max',
            'CUMULATIVE_GAS_BCF': 'max',
            'ACTIVE_WELL_COUNT': 'max'
        }).reset_index()
        
        field_summary = field_summary.sort_values('CUMULATIVE_OIL_MMBBL', ascending=False)
        
        summary_data.append({
            'Category': 'Top Field',
            'Metric': f"{field_summary.iloc[0]['FIELD_NAME']}",
            'Value': f"{field_summary.iloc[0]['CUMULATIVE_OIL_MMBBL']:.2f} MMBBL"
        })
        
        summary_df = pd.DataFrame(summary_data)
        
        return summary_df
    
    def save_outputs(self, wells_df: pd.DataFrame, 
                    lease_df: pd.DataFrame,
                    api_df: pd.DataFrame,
                    field_df: pd.DataFrame,
                    summary_df: pd.DataFrame):
        """
        Save all outputs to files
        
        Args:
            wells_df: Wells by lease DataFrame
            lease_df: Production by lease DataFrame
            api_df: Production by API DataFrame
            field_df: Production by field DataFrame
            summary_df: Summary statistics DataFrame
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save CSV files
        output_files = {
            'a_wells_by_lease': wells_df,
            'b_production_by_lease': lease_df,
            'c_production_by_api': api_df,
            'd_production_by_field': field_df,
            'summary_statistics': summary_df
        }
        
        for name, df in output_files.items():
            csv_file = self.output_dir / f'{name}_{timestamp}.csv'
            df.to_csv(csv_file, index=False)
            logger.info(f"Saved {name}: {csv_file} ({len(df):,} rows)")
        
        # Save Excel workbook with all sheets
        excel_file = self.output_dir / f'fdas_production_complete_{timestamp}.xlsx'
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            wells_df.to_excel(writer, sheet_name='Wells_by_Lease', index=False)
            lease_df.to_excel(writer, sheet_name='Production_by_Lease', index=False)
            api_df.to_excel(writer, sheet_name='Production_by_API', index=False)
            field_df.to_excel(writer, sheet_name='Production_by_Field', index=False)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        logger.info(f"Saved Excel workbook: {excel_file}")
        
        # Generate summary report
        self.generate_summary_report(wells_df, lease_df, api_df, field_df, summary_df, timestamp)
    
    def generate_summary_report(self, wells_df, lease_df, api_df, field_df, summary_df, timestamp):
        """Generate a markdown summary report"""
        
        report_file = self.output_dir / f'PRODUCTION_SUMMARY_{timestamp}.md'
        
        with open(report_file, 'w') as f:
            f.write("# FDAS V30 Production Data Summary\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Source:** {self.leases_file}\n\n")
            f.write("---\n\n")
            
            f.write("## Summary Statistics\n\n")
            f.write(summary_df.to_markdown(index=False))
            f.write("\n\n---\n\n")
            
            f.write("## Leases and Wells\n\n")
            lease_summary = wells_df.groupby(['LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME']).size().reset_index(name='WELL_COUNT')
            f.write(lease_summary.to_markdown(index=False))
            f.write("\n\n---\n\n")
            
            f.write("## Field Production Summary\n\n")
            field_summary = field_df.groupby('FIELD_NAME').agg({
                'CUMULATIVE_OIL_MMBBL': 'max',
                'CUMULATIVE_GAS_BCF': 'max',
                'ACTIVE_WELL_COUNT': 'max'
            }).round(2).reset_index()
            field_summary = field_summary.sort_values('CUMULATIVE_OIL_MMBBL', ascending=False)
            f.write(field_summary.to_markdown(index=False))
            f.write("\n\n---\n\n")
            
            f.write("## Output Files\n\n")
            f.write("1. **a_wells_by_lease**: List of all API12 wells organized by lease\n")
            f.write("2. **b_production_by_lease**: Monthly production aggregated by lease\n")
            f.write("3. **c_production_by_api**: Individual well production with rates and cumulatives\n")
            f.write("4. **d_production_by_field**: Field-level production aggregation\n")
            f.write("5. **summary_statistics**: Overall statistics and summaries\n")
            f.write("6. **fdas_production_complete.xlsx**: All outputs in one Excel file\n\n")
        
        logger.info(f"Saved summary report: {report_file}")
    
    def run(self):
        """Execute the complete production retrieval workflow"""
        
        logger.info("=" * 80)
        logger.info("FDAS V30 Production Data Retrieval")
        logger.info("=" * 80)
        
        # Get configuration
        cfg = self.get_configuration()
        
        # Load all production data from binary
        logger.info("\nStep 1: Loading production data from binary files...")
        all_production = self.load_production_from_binary(cfg)
        
        if all_production.empty:
            logger.error("No production data loaded. Exiting.")
            return
        
        # Filter for FDAS leases
        logger.info("\nStep 2: Filtering production for FDAS leases...")
        fdas_production = self.filter_production_by_leases(all_production)
        
        if fdas_production.empty:
            logger.error("No production data found for FDAS leases. Exiting.")
            return
        
        # Generate all outputs
        logger.info("\nStep 3: Generating outputs...")
        
        logger.info("\n  a. Wells by lease...")
        wells_df = self.generate_wells_by_lease(fdas_production)
        
        logger.info("\n  b. Production by lease...")
        lease_df = self.generate_production_by_lease(fdas_production)
        
        logger.info("\n  c. Production by API...")
        api_df = self.generate_production_by_api(fdas_production)
        
        logger.info("\n  d. Production by field...")
        field_df = self.generate_production_by_field(fdas_production)
        
        logger.info("\nStep 4: Generating summary statistics...")
        summary_df = self.generate_summary_statistics(wells_df, lease_df, api_df, field_df)
        
        # Save all outputs
        logger.info("\nStep 5: Saving outputs...")
        self.save_outputs(wells_df, lease_df, api_df, field_df, summary_df)
        
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
    output_dir = project_root / 'results' / 'fdas_production'
    
    # Check if leases file exists
    if not leases_file.exists():
        logger.error(f"Leases file not found: {leases_file}")
        return 1
    
    # Create retriever and run
    try:
        retriever = FDASProductionRetriever(
            leases_file=str(leases_file),
            output_dir=str(output_dir)
        )
        
        retriever.run()
        
        return 0
        
    except Exception as e:
        logger.exception(f"Error during production retrieval: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
