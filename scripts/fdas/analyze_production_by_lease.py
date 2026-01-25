#!/usr/bin/env python3
"""
ABOUTME: Analyze production by lease data
ABOUTME: Generate lease-level statistics, rankings, and visualizations
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

def analyze_lease_production(input_file: str):
    """
    Analyze production by lease data
    
    Args:
        input_file: Path to production by lease CSV file
    """
    print("=" * 80)
    print("PRODUCTION BY LEASE - DETAILED ANALYSIS")
    print("=" * 80)
    
    # Load data
    df = pd.read_csv(input_file)
    print(f"\n✓ Loaded {len(df):,} records from {input_file}")
    
    # Convert production date
    df['PRODUCTION_DATE'] = pd.to_datetime(df['PRODUCTION_DATE'], format='%Y%m')
    
    # Basic statistics
    print(f"\n📊 OVERVIEW")
    print(f"  Date Range: {df['PRODUCTION_DATE'].min().strftime('%b %Y')} to {df['PRODUCTION_DATE'].max().strftime('%b %Y')}")
    print(f"  Unique Leases: {df['LEASE_NUMBER'].nunique()}")
    print(f"  Total Lease-Months: {len(df):,}")
    
    # Lease-level summary
    print(f"\n📈 LEASE-LEVEL SUMMARY")
    print("-" * 80)
    
    lease_summary = df.groupby(['LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM']).agg({
        'OIL_BBLS': 'sum',
        'GAS_MCF': 'sum',
        'CUMULATIVE_OIL_MMBBL': 'max',
        'CUMULATIVE_GAS_BCF': 'max',
        'ACTIVE_WELL_COUNT': 'max',
        'PRODUCTION_DATE': ['min', 'max', 'count']
    }).reset_index()
    
    lease_summary.columns = ['LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM',
                              'TOTAL_OIL_BBLS', 'TOTAL_GAS_MCF',
                              'CUM_OIL_MMBBL', 'CUM_GAS_BCF', 'MAX_WELLS',
                              'FIRST_PROD', 'LAST_PROD', 'MONTHS']
    
    # Calculate production life
    lease_summary['PROD_YEARS'] = ((lease_summary['LAST_PROD'] - lease_summary['FIRST_PROD']).dt.days / 365.25).round(1)
    
    # Calculate GOR
    lease_summary['AVG_GOR'] = (lease_summary['TOTAL_GAS_MCF'] / lease_summary['TOTAL_OIL_BBLS']).round(1)
    
    # Sort by cumulative oil
    lease_summary = lease_summary.sort_values('CUM_OIL_MMBBL', ascending=False)
    
    # Display summary
    print(f"\n{'Rank':<5} {'Lease':<8} {'Name':<15} {'Development':<15} {'Cum Oil':<12} {'Cum Gas':<12} {'Wells':<7} {'Years':<7}")
    print("-" * 90)
    
    for i, row in lease_summary.head(15).iterrows():
        print(f"{i+1:<5} {row['LEASE_NUMBER']:<8} {str(row['LEASE_NAME'])[:15]:<15} "
              f"{str(row['DEV_NAME'])[:15]:<15} {row['CUM_OIL_MMBBL']:>10.2f} M {row['CUM_GAS_BCF']:>10.2f} B "
              f"{row['MAX_WELLS']:>5} {row['PROD_YEARS']:>6.1f}")
    
    # Development-level summary
    print(f"\n🏗️  DEVELOPMENT-LEVEL SUMMARY")
    print("-" * 80)
    
    dev_summary = df.groupby(['DEV_NAME', 'DEV_SYSTEM']).agg({
        'CUMULATIVE_OIL_MMBBL': 'max',
        'CUMULATIVE_GAS_BCF': 'max',
        'ACTIVE_WELL_COUNT': 'max',
        'LEASE_NUMBER': 'nunique'
    }).reset_index()
    
    dev_summary.columns = ['DEVELOPMENT', 'SYSTEM', 'CUM_OIL_MMBBL', 'CUM_GAS_BCF', 'MAX_WELLS', 'LEASE_COUNT']
    dev_summary = dev_summary.sort_values('CUM_OIL_MMBBL', ascending=False)
    
    print(f"\n{'Development':<20} {'System':<12} {'Leases':<8} {'Cum Oil (MMBBL)':<16} {'Cum Gas (BCF)':<16} {'Max Wells':<10}")
    print("-" * 85)
    
    for _, row in dev_summary.iterrows():
        print(f"{row['DEVELOPMENT']:<20} {row['SYSTEM']:<12} {row['LEASE_COUNT']:>6} "
              f"{row['CUM_OIL_MMBBL']:>14.2f} {row['CUM_GAS_BCF']:>14.2f} {row['MAX_WELLS']:>9}")
    
    # Production trends
    print(f"\n📅 PRODUCTION TRENDS")
    print("-" * 80)
    
    # Group by year
    df['YEAR'] = df['PRODUCTION_DATE'].dt.year
    
    yearly = df.groupby('YEAR').agg({
        'OIL_BBLS': 'sum',
        'GAS_MCF': 'sum',
        'LEASE_NUMBER': 'nunique',
        'ACTIVE_WELL_COUNT': 'max'
    }).reset_index()
    
    yearly.columns = ['YEAR', 'ANNUAL_OIL_BBLS', 'ANNUAL_GAS_MCF', 'ACTIVE_LEASES', 'MAX_WELLS']
    yearly['ANNUAL_OIL_MMBBL'] = yearly['ANNUAL_OIL_BBLS'] / 1_000_000
    
    print(f"\n{'Year':<6} {'Oil (MMBBL)':<14} {'Gas (BCF)':<14} {'Active Leases':<15} {'Max Wells':<10}")
    print("-" * 60)
    
    for _, row in yearly.tail(10).iterrows():
        annual_gas_bcf = row['ANNUAL_GAS_MCF'] / 1_000_000
        print(f"{int(row['YEAR']):<6} {row['ANNUAL_OIL_MMBBL']:>12.2f} {annual_gas_bcf:>12.2f} "
              f"{row['ACTIVE_LEASES']:>13} {row['MAX_WELLS']:>10}")
    
    # Key statistics
    print(f"\n📊 KEY STATISTICS")
    print("-" * 80)
    
    total_oil = lease_summary['CUM_OIL_MMBBL'].sum()
    total_gas = lease_summary['CUM_GAS_BCF'].sum()
    
    print(f"\nTotal Portfolio Cumulative Production:")
    print(f"  Oil:  {total_oil:>10.2f} MMBBL")
    print(f"  Gas:  {total_gas:>10.2f} BCF")
    
    print(f"\nTop 3 Producing Leases (Oil):")
    for i, row in lease_summary.head(3).iterrows():
        pct = (row['CUM_OIL_MMBBL'] / total_oil) * 100
        print(f"  {i+1}. {row['LEASE_NUMBER']} ({row['LEASE_NAME']}): {row['CUM_OIL_MMBBL']:.2f} MMBBL ({pct:.1f}%)")
    
    print(f"\nDevelopment System Distribution:")
    system_dist = lease_summary.groupby('DEV_SYSTEM')['CUM_OIL_MMBBL'].sum().sort_values(ascending=False)
    for system, oil in system_dist.items():
        pct = (oil / total_oil) * 100
        count = len(lease_summary[lease_summary['DEV_SYSTEM'] == system])
        print(f"  {system:<12}: {oil:>8.2f} MMBBL ({pct:>5.1f}%) - {count} leases")
    
    # Recent production analysis (last 12 months)
    print(f"\n📅 RECENT PRODUCTION (Last 12 Months)")
    print("-" * 80)
    
    recent_date = df['PRODUCTION_DATE'].max() - pd.DateOffset(months=12)
    recent = df[df['PRODUCTION_DATE'] >= recent_date]
    
    recent_summary = recent.groupby(['LEASE_NUMBER', 'LEASE_NAME']).agg({
        'OIL_BBLS': 'sum',
        'GAS_MCF': 'sum'
    }).reset_index()
    
    recent_summary.columns = ['LEASE_NUMBER', 'LEASE_NAME', 'OIL_12M_BBLS', 'GAS_12M_MCF']
    recent_summary['OIL_12M_MMBBL'] = recent_summary['OIL_12M_BBLS'] / 1_000_000
    recent_summary = recent_summary.sort_values('OIL_12M_BBLS', ascending=False)
    
    print(f"\nTop 10 Leases by Last 12 Months Production:")
    print(f"{'Lease':<10} {'Name':<15} {'Oil (MMBBL)':<14} {'Avg BOPD':<12}")
    print("-" * 52)
    
    for _, row in recent_summary.head(10).iterrows():
        avg_bopd = row['OIL_12M_BBLS'] / 365
        print(f"{row['LEASE_NUMBER']:<10} {str(row['LEASE_NAME'])[:15]:<15} {row['OIL_12M_MMBBL']:>12.3f} {avg_bopd:>10,.0f}")
    
    print(f"\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    return lease_summary, dev_summary


def main():
    """Main entry point"""
    
    # Find the most recent production by lease file
    project_root = Path(__file__).parent.parent
    results_dir = project_root / 'results' / 'fdas_production'
    
    # Find latest file
    lease_files = list(results_dir.glob('b_production_by_lease_*.csv'))
    
    if not lease_files:
        print("Error: No production by lease files found")
        print(f"Expected location: {results_dir}")
        return 1
    
    # Get most recent
    latest_file = max(lease_files, key=lambda p: p.stat().st_mtime)
    
    print(f"Analyzing: {latest_file.name}\n")
    
    # Analyze
    try:
        lease_summary, dev_summary = analyze_lease_production(str(latest_file))
        
        # Save summaries
        output_dir = results_dir
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        lease_summary_file = output_dir / f'lease_summary_{timestamp}.csv'
        dev_summary_file = output_dir / f'development_summary_{timestamp}.csv'
        
        lease_summary.to_csv(lease_summary_file, index=False)
        dev_summary.to_csv(dev_summary_file, index=False)
        
        print(f"\n✓ Saved lease summary: {lease_summary_file.name}")
        print(f"✓ Saved development summary: {dev_summary_file.name}")
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
