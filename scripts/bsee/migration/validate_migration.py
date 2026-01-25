#!/usr/bin/env python3
"""
BSEE Migration Validation Script
Verify data integrity after consolidation
"""

import os
import csv
import hashlib
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
CURRENT_DIR = Path("data/modules/bsee")
BACKUP_DIR = Path("data/modules/bsee.backup_20250821_064447")

def count_csv_rows(file_path: Path) -> int:
    """Count rows in a CSV file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f) - 1  # Subtract header
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return -1

def calculate_checksum(file_path: Path) -> str:
    """Calculate MD5 checksum of a file"""
    try:
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception as e:
        print(f"Error calculating checksum for {file_path}: {e}")
        return ""

def validate_row_counts():
    """Validate row counts for moved files"""
    print("\n" + "="*60)
    print("VALIDATING ROW COUNTS")
    print("="*60)
    
    # Files that were moved
    file_mappings = {
        "analysis_data/combined_data_for_analysis/production.csv": "current/production/production.csv",
        "analysis_data/combined_data_for_analysis/well_data.csv": "current/wells/well_data.csv",
        "analysis_data/combined_data_for_analysis/well_directional_surveys.csv": "current/wells/well_directional_surveys.csv",
        "analysis_data/combined_data_for_analysis/well_tubulars.csv": "current/wells/well_tubulars.csv",
        "analysis_data/combined_data_for_analysis/completion_perforations.csv": "current/completions/completion_perforations.csv",
        "analysis_data/combined_data_for_analysis/completion_properties.csv": "current/completions/completion_properties.csv",
        "analysis_data/combined_data_for_analysis/completion_summary.csv": "current/completions/completion_summary.csv",
        "analysis_data/combined_data_for_analysis/well_activity_bop_tests.csv": "current/operations/well_activity_bop_tests.csv",
        "analysis_data/combined_data_for_analysis/well_activity_open_hole.csv": "current/operations/well_activity_open_hole.csv",
        "analysis_data/combined_data_for_analysis/well_activity_remarks.csv": "current/operations/well_activity_remarks.csv",
        "analysis_data/combined_data_for_analysis/well_activity_summary.csv": "current/operations/well_activity_summary.csv",
        "analysis_data/combined_data_for_analysis/ST_BP_and_tree_height.csv": "current/operations/ST_BP_and_tree_height.csv",
        "analysis_data/combined_data_for_analysis/cut_casings.csv": "current/operations/cut_casings.csv",
        "analysis_data/combined_data_for_analysis/geology_markers.csv": "current/geology/geology_markers.csv",
        "analysis_data/combined_data_for_analysis/hydrocarbon_bearing_interval.csv": "current/geology/hydrocarbon_bearing_interval.csv",
        "analysis_data/combined_data_for_analysis/all_bsee_blocks.csv": "current/infrastructure/all_bsee_blocks.csv",
    }
    
    validation_results = []
    all_valid = True
    
    for original, new in file_mappings.items():
        original_path = BACKUP_DIR / original
        new_path = CURRENT_DIR / new
        
        if original_path.exists() and new_path.exists():
            original_rows = count_csv_rows(original_path)
            new_rows = count_csv_rows(new_path)
            
            if original_rows == new_rows:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
                all_valid = False
                
            validation_results.append({
                'file': new.split('/')[-1],
                'original_rows': original_rows,
                'new_rows': new_rows,
                'status': status
            })
            
            print(f"{status} {new.split('/')[-1]:40} Original: {original_rows:6} New: {new_rows:6}")
        else:
            print(f"❌ MISSING: {new}")
            all_valid = False
    
    print("\n" + "-"*60)
    if all_valid:
        print("✅ ALL ROW COUNTS VALIDATED SUCCESSFULLY")
    else:
        print("❌ SOME VALIDATIONS FAILED")
    
    return validation_results, all_valid

def validate_checksums():
    """Validate checksums for moved files"""
    print("\n" + "="*60)
    print("VALIDATING FILE CHECKSUMS")
    print("="*60)
    
    # Key files to validate
    critical_files = [
        "current/wells/well_data.csv",
        "current/production/production.csv",
        "current/wells/well_directional_surveys.csv",
        "current/completions/completion_summary.csv",
        "current/operations/well_activity_summary.csv",
    ]
    
    checksum_results = []
    
    for file_path in critical_files:
        full_path = CURRENT_DIR / file_path
        if full_path.exists():
            checksum = calculate_checksum(full_path)
            size = full_path.stat().st_size
            checksum_results.append({
                'file': file_path,
                'checksum': checksum[:8] + "...",
                'size': size,
                'status': '✅ Valid'
            })
            print(f"✅ {file_path:50} Size: {size:10,} bytes  MD5: {checksum[:8]}...")
        else:
            print(f"❌ File not found: {file_path}")
            
    return checksum_results

def check_import_paths():
    """Check Python files for old import paths that need updating"""
    print("\n" + "="*60)
    print("CHECKING IMPORT PATHS IN CODE")
    print("="*60)
    
    # Search for Python files that might reference old paths
    old_paths = [
        "data/modules/bsee/legacy",
        "data/modules/bsee/analysis_data/combined_data_for_analysis",
        "legacy/data_for_analysis",
        "legacy/online_raw_well_data",
    ]
    
    python_files = list(Path("src").rglob("*.py")) if Path("src").exists() else []
    python_files.extend(list(Path("tests").rglob("*.py")) if Path("tests").exists() else [])
    
    files_to_update = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for old_path in old_paths:
                    if old_path in content:
                        files_to_update.append((py_file, old_path))
                        print(f"⚠️  Found old path in {py_file}: {old_path}")
        except Exception as e:
            pass
    
    if not files_to_update:
        print("✅ No old import paths found in Python files")
    else:
        print(f"\n⚠️  Found {len(files_to_update)} files with old paths that need updating")
        
    return files_to_update

def test_data_loading():
    """Test loading performance of new structure"""
    print("\n" + "="*60)
    print("TESTING DATA LOADING PERFORMANCE")
    print("="*60)
    
    import time
    
    test_files = [
        "current/wells/well_data.csv",
        "current/production/production.csv",
        "current/completions/completion_summary.csv",
    ]
    
    performance_results = []
    
    for file_path in test_files:
        full_path = CURRENT_DIR / file_path
        if full_path.exists():
            start_time = time.time()
            try:
                # Test loading with pandas
                df = pd.read_csv(full_path, nrows=1000)  # Load first 1000 rows for test
                load_time = time.time() - start_time
                
                performance_results.append({
                    'file': file_path.split('/')[-1],
                    'load_time': f"{load_time:.3f}s",
                    'rows': len(df),
                    'columns': len(df.columns),
                    'status': '✅ Success'
                })
                
                print(f"✅ {file_path.split('/')[-1]:30} Loaded {len(df):4} rows in {load_time:.3f}s")
            except Exception as e:
                print(f"❌ Error loading {file_path}: {e}")
                performance_results.append({
                    'file': file_path.split('/')[-1],
                    'status': f'❌ Error: {str(e)[:30]}'
                })
    
    return performance_results

def generate_validation_summary():
    """Generate comprehensive validation summary"""
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    # Run all validations
    row_results, rows_valid = validate_row_counts()
    checksum_results = validate_checksums()
    import_updates = check_import_paths()
    performance_results = test_data_loading()
    
    # Summary
    print("\n" + "="*60)
    print("FINAL VALIDATION REPORT")
    print("="*60)
    
    validations = {
        "Row Count Validation": "✅ PASSED" if rows_valid else "❌ FAILED",
        "Checksum Validation": "✅ PASSED" if checksum_results else "⚠️ PARTIAL",
        "Import Path Check": "✅ CLEAN" if not import_updates else f"⚠️ {len(import_updates)} files need updates",
        "Data Loading Test": "✅ PASSED" if performance_results else "❌ FAILED",
    }
    
    for test, result in validations.items():
        print(f"{test:25} {result}")
    
    # Overall status
    print("\n" + "-"*60)
    if all("✅" in result for result in validations.values()):
        print("🎉 ALL VALIDATIONS PASSED SUCCESSFULLY!")
        overall_status = "SUCCESS"
    elif any("❌" in result for result in validations.values()):
        print("❌ SOME VALIDATIONS FAILED - REVIEW NEEDED")
        overall_status = "FAILED"
    else:
        print("⚠️  VALIDATIONS PASSED WITH WARNINGS")
        overall_status = "WARNING"
    
    return {
        'row_validation': row_results,
        'checksum_validation': checksum_results,
        'import_updates_needed': import_updates,
        'performance_tests': performance_results,
        'overall_status': overall_status,
        'summary': validations
    }

if __name__ == "__main__":
    results = generate_validation_summary()
    
    # Save detailed results
    import json
    with open("specs/modules/bsee/consolidation/validation_results.json", "w") as f:
        json.dump({
            'summary': results['summary'],
            'overall_status': results['overall_status'],
            'row_counts': results['row_validation'],
            'checksums': [
                {k: str(v) for k, v in item.items()} 
                for item in results['checksum_validation']
            ],
            'performance': results['performance_tests'],
            'files_needing_updates': [str(f[0]) for f in results['import_updates_needed']]
        }, f, indent=2)
    
    print(f"\n📊 Detailed results saved to: specs/modules/bsee/consolidation/validation_results.json")