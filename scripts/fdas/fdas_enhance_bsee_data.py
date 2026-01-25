#!/usr/bin/env python
"""
BSEE Data Enhancement Script for FDAS Integration

Adds required columns and files to BSEE data for FDAS compatibility:
1. Adds DEV_SYSTEM column to well_data.csv
2. Creates lease_mapping.csv
3. Enhances production.csv with DEV_NAME and LEASE_NAME

Author: WorldEnergyData Team
Date: 2025-10-03
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.worldenergydata.modules.fdas.core.config import classify_dev_system_by_depth


def enhance_well_data(bsee_data_dir: Path, output_dir: Path) -> pd.DataFrame:
    """
    Add DEV_SYSTEM column to well_data.csv based on water depth.

    Args:
        bsee_data_dir: Path to BSEE data directory
        output_dir: Path for output files

    Returns:
        Enhanced well data DataFrame
    """
    well_data_path = bsee_data_dir / 'wells' / 'well_data.csv'

    if not well_data_path.exists():
        raise FileNotFoundError(f"well_data.csv not found at {well_data_path}")

    print(f"Loading well data from {well_data_path}...")
    well_data = pd.read_csv(well_data_path)

    # Add DEV_SYSTEM column
    print("Adding DEV_SYSTEM classification...")
    well_data['DEV_SYSTEM'] = well_data['WATER_DEPTH'].apply(
        classify_dev_system_by_depth
    )

    # Summary
    dev_system_counts = well_data['DEV_SYSTEM'].value_counts()
    print("\nDevelopment System Distribution:")
    for system, count in dev_system_counts.items():
        print(f"  {system:12}: {count:6} wells")

    # Save enhanced file
    output_path = output_dir / 'wells' / 'well_data_enhanced.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    well_data.to_csv(output_path, index=False)
    print(f"\n✓ Enhanced well data saved to {output_path}")

    return well_data


def create_lease_mapping(well_data: pd.DataFrame,
                         bsee_data_dir: Path,
                         output_dir: Path) -> pd.DataFrame:
    """
    Create lease_mapping.csv from production data with well enrichment.

    Args:
        well_data: Enhanced well data with DEV_SYSTEM
        bsee_data_dir: Path to BSEE data directory
        output_dir: Path for output files

    Returns:
        Lease mapping DataFrame
    """
    print("\nCreating lease mapping...")

    # Load production data to get lease information
    prod_path = bsee_data_dir / 'production' / 'production.csv'

    if not prod_path.exists():
        print(f"\nWarning: production.csv not found at {prod_path}")
        print("Creating simplified mapping from well data only")

        # Fallback: create minimal mapping from well data
        # Use field name as grouping key
        if 'BOTM_FLD_NAME_CD' in well_data.columns:
            lease_mapping = well_data.groupby('BOTM_FLD_NAME_CD').agg({
                'WATER_DEPTH': 'mean',
                'DEV_SYSTEM': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'unknown',
                'API_WELL_NUMBER': 'count'
            }).reset_index()

            lease_mapping = lease_mapping.rename(columns={
                'BOTM_FLD_NAME_CD': 'DEV_NAME',
                'WATER_DEPTH': 'AVG_WATER_DEPTH',
                'API_WELL_NUMBER': 'WELL_COUNT'
            })

            # Add placeholder columns
            lease_mapping['LEASE_NUMBER'] = lease_mapping.index
            lease_mapping['LEASE_NAME'] = lease_mapping.apply(
                lambda row: f"Lease {row['LEASE_NUMBER']}", axis=1
            )
        else:
            return None
    else:
        # Load production data
        print(f"Loading production data from {prod_path}...")
        production = pd.read_csv(prod_path, low_memory=False)

        # Get unique lease/development combinations
        lease_cols = []
        for col in ['LEASE_NUMBER', 'MMS_LEASE_NUM', 'LEASE_NUM']:
            if col in production.columns:
                lease_cols.append(col)
                break

        dev_cols = []
        for col in ['DEV_NAME', 'FIELD_NAME', 'COMPLEX_NAME']:
            if col in production.columns:
                dev_cols.append(col)
                break

        if not lease_cols or not dev_cols:
            print("\nWarning: Required columns not found in production data")
            return None

        lease_col = lease_cols[0]
        dev_col = dev_cols[0]

        # Aggregate production by lease
        lease_mapping = production.groupby(lease_col).agg({
            dev_col: 'first',
            'API_WELL_NUMBER': 'nunique' if 'API_WELL_NUMBER' in production.columns else 'count'
        }).reset_index()

        lease_mapping = lease_mapping.rename(columns={
            lease_col: 'LEASE_NUMBER',
            dev_col: 'DEV_NAME',
            'API_WELL_NUMBER': 'WELL_COUNT'
        })

        # Join with well data for water depth and dev system
        well_summary = well_data.groupby('API_WELL_NUMBER').agg({
            'WATER_DEPTH': 'first',
            'DEV_SYSTEM': 'first'
        }).reset_index()

        # Add placeholder columns
        lease_mapping['LEASE_NAME'] = lease_mapping.apply(
            lambda row: f"Lease {row['LEASE_NUMBER']}", axis=1
        )
        lease_mapping['AVG_WATER_DEPTH'] = 0.0  # Would need well-to-lease mapping
        lease_mapping['DEV_SYSTEM'] = 'unknown'  # Would need well-to-lease mapping

    # Reorder columns
    lease_mapping = lease_mapping[[
        'LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME', 'DEV_SYSTEM',
        'AVG_WATER_DEPTH', 'WELL_COUNT'
    ]]

    # Summary
    print(f"Created mapping for {len(lease_mapping)} leases")
    print(f"\nTop 10 leases by well count:")
    top_leases = lease_mapping.nlargest(10, 'WELL_COUNT')
    for _, row in top_leases.iterrows():
        lease_num = str(row['LEASE_NUMBER'])[:10]
        dev_name = str(row['DEV_NAME'])[:20]
        print(f"  {lease_num:10} {dev_name:20} "
              f"{row['DEV_SYSTEM']:12} {row['WELL_COUNT']:3} wells")

    # Save
    output_path = output_dir / 'leases' / 'lease_mapping.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lease_mapping.to_csv(output_path, index=False)
    print(f"\n✓ Lease mapping saved to {output_path}")

    return lease_mapping


def enhance_production_data(bsee_data_dir: Path,
                            lease_mapping: pd.DataFrame,
                            output_dir: Path) -> pd.DataFrame:
    """
    Enhance production.csv with DEV_NAME and LEASE_NAME.

    Args:
        bsee_data_dir: Path to BSEE data directory
        lease_mapping: Lease mapping DataFrame (can be None)
        output_dir: Path for output files

    Returns:
        Enhanced production DataFrame
    """
    prod_path = bsee_data_dir / 'production' / 'production.csv'

    if not prod_path.exists():
        print(f"\nWarning: production.csv not found at {prod_path}")
        print("Skipping production enhancement")
        return None

    if lease_mapping is None:
        print(f"\nWarning: No lease mapping available")
        print("Skipping production enhancement - BSEE data structure doesn't match FDAS requirements")
        print("\nManual steps needed:")
        print("1. Map API_WELL_NUMBER to development names")
        print("2. Add DEV_NAME and LEASE_NAME columns")
        print("3. Ensure production.csv has required columns for FDAS")
        return None

    print(f"\nLoading production data from {prod_path}...")
    production = pd.read_csv(prod_path, low_memory=False)

    # Create lookup dictionary
    lease_lookup = lease_mapping.set_index('LEASE_NUMBER').to_dict('index')

    # Add columns
    print("Adding DEV_NAME and LEASE_NAME...")

    def add_lease_info(row):
        lease_num = row.get('LEASE_NUMBER')
        if lease_num in lease_lookup:
            info = lease_lookup[lease_num]
            return pd.Series({
                'DEV_NAME': info['DEV_NAME'],
                'LEASE_NAME': info['LEASE_NAME'],
                'DEV_SYSTEM': info['DEV_SYSTEM']
            })
        return pd.Series({
            'DEV_NAME': None,
            'LEASE_NAME': None,
            'DEV_SYSTEM': 'unknown'
        })

    enhanced = production.join(production.apply(add_lease_info, axis=1))

    # Summary
    dev_prod = enhanced.groupby('DEV_NAME')['OIL_VOLUME'].sum().nlargest(10)
    print(f"\nTop 10 developments by oil production:")
    for dev_name, volume in dev_prod.items():
        print(f"  {str(dev_name)[:30]:30} {volume:15,.0f} BBL")

    # Save
    output_path = output_dir / 'production' / 'production_enhanced.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    enhanced.to_csv(output_path, index=False)
    print(f"\n✓ Enhanced production data saved to {output_path}")

    return enhanced


def main():
    """Main enhancement workflow."""
    print("="*80)
    print("BSEE Data Enhancement for FDAS Integration")
    print("="*80)

    # Paths
    bsee_data_dir = Path('data/modules/bsee/current')
    output_dir = Path('data/modules/fdas/enhanced')

    if not bsee_data_dir.exists():
        print(f"\nError: BSEE data directory not found: {bsee_data_dir}")
        print("Please ensure BSEE data is available")
        return 1

    try:
        # Step 1: Enhance well data
        print("\nStep 1: Enhancing well data with DEV_SYSTEM...")
        well_data = enhance_well_data(bsee_data_dir, output_dir)

        # Step 2: Create lease mapping
        print("\nStep 2: Creating lease mapping...")
        lease_mapping = create_lease_mapping(well_data, bsee_data_dir, output_dir)

        # Step 3: Enhance production data
        if lease_mapping is not None:
            print("\nStep 3: Enhancing production data...")
            production = enhance_production_data(bsee_data_dir, lease_mapping, output_dir)
        else:
            print("\nStep 3: Skipping production enhancement (no lease mapping)")

        print("\n" + "="*80)
        print("✓ BSEE Data Enhancement Complete!")
        print("="*80)
        print(f"\nEnhanced files created in: {output_dir}")
        print("\nFiles created:")
        print("  - well_data_enhanced.csv (with DEV_SYSTEM classification)")
        if lease_mapping is not None:
            print("  - lease_mapping.csv")
        print("\nNote: BSEE data structure differs from FDAS expectations.")
        print("      Well data enhancement is complete and ready to use.")
        print("\nNext steps:")
        print("1. Review enhanced well data")
        print("2. For full FDAS integration, production data needs:")
        print("   - DEV_NAME (development/field name)")
        print("   - LEASE_NAME (lease identifier)")
        print("   - Oil/gas/water volumes with proper column names")
        print("3. See examples/fdas_complete_workflow.py for usage")

        return 0

    except Exception as e:
        print(f"\n✗ Error during enhancement: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
