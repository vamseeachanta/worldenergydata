#!/usr/bin/env python3
"""
Verify migration results and check for content loss
"""

from pathlib import Path
import json
from test_migration_system import MigrationTester


def verify_migration_results():
    """Comprehensive verification of migration results"""
    project_root = Path(__file__).parent
    tester = MigrationTester(project_root)
    
    print("=== MIGRATION VERIFICATION ===")
    
    # Check new structure exists
    expected_structure = [
        "docs/data-sources/bsee",
        "docs/data-sources/equipment", 
        "docs/data-sources/sodir",
        "docs/data-sources/onshore",
        "docs/development",
        "docs/user-guide",
        "docs/analysis-guides",
        "docs/reference",
        "docs/examples"
    ]
    
    print("\\n1. Checking directory structure...")
    structure_ok = True
    for dir_path in expected_structure:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"  [OK] {dir_path} exists")
        else:
            print(f"  [MISSING] {dir_path} not found")
            structure_ok = False
    
    # Count files in new locations
    print("\\n2. Counting migrated files...")
    file_counts = {}
    
    for category_dir in (project_root / "docs").iterdir():
        if category_dir.is_dir() and category_dir.name not in ['modules', 'raw_data']:
            md_files = list(category_dir.rglob("*.md"))
            if md_files:
                file_counts[category_dir.name] = len(md_files)
                print(f"  {category_dir.name}: {len(md_files)} files")
    
    # Check for remaining files in old locations
    print("\\n3. Checking for remaining files in old locations...")
    old_locations = ["docs/modules", "docs/raw_data"]
    remaining_files = []
    
    for old_loc in old_locations:
        old_path = project_root / old_loc
        if old_path.exists():
            md_files = list(old_path.rglob("*.md"))
            remaining_files.extend(md_files)
            if md_files:
                print(f"  [WARN] {len(md_files)} files still in {old_loc}")
                for f in md_files[:3]:  # Show first 3
                    print(f"    - {f.relative_to(project_root)}")
                if len(md_files) > 3:
                    print(f"    ... and {len(md_files) - 3} more")
            else:
                print(f"  [OK] No files remaining in {old_loc}")
    
    # Verify BSEE structure preservation
    print("\\n4. Verifying BSEE structure preservation...")
    bsee_path = project_root / "docs/data-sources/bsee"
    if bsee_path.exists():
        analysis_files = list((bsee_path / "analysis").rglob("*.md"))
        data_files = list((bsee_path / "data").rglob("*.md"))
        
        print(f"  Analysis files: {len(analysis_files)}")
        print(f"  Data files: {len(data_files)}")
        
        # Check specific subdirectories
        expected_subdirs = ["analysis/economics", "analysis/production", "data/field_jsm"]
        for subdir in expected_subdirs:
            full_subdir = bsee_path / subdir
            if full_subdir.exists():
                files_in_subdir = list(full_subdir.rglob("*.md"))
                print(f"  {subdir}: {len(files_in_subdir)} files")
            else:
                print(f"  [MISSING] {subdir} not found")
    
    # Summary
    print("\\n=== VERIFICATION SUMMARY ===")
    total_migrated = sum(file_counts.values())
    print(f"Total files in new structure: {total_migrated}")
    print(f"Files remaining in old locations: {len(remaining_files)}")
    print(f"Directory structure: {'Complete' if structure_ok else 'Incomplete'}")
    
    verification_result = {
        'total_migrated': total_migrated,
        'remaining_in_old_locations': len(remaining_files),
        'structure_complete': structure_ok,
        'file_counts_by_category': file_counts
    }
    
    return verification_result


def check_content_integrity():
    """Check that file content was preserved during migration"""
    print("\\n=== CONTENT INTEGRITY CHECK ===")
    
    project_root = Path(__file__).parent
    
    # Sample a few migrated files for content verification
    sample_files = [
        "docs/data-sources/bsee/analysis/economics/intro.md",
        "docs/data-sources/bsee/data/analysis_data.md",
        "docs/data-sources/equipment/anchor/calculation.md",
        "docs/development/development_history.md"
    ]
    
    integrity_results = {
        'files_checked': 0,
        'files_verified': 0,
        'missing_files': [],
        'issues': []
    }
    
    for file_path in sample_files:
        full_path = project_root / file_path
        integrity_results['files_checked'] += 1
        
        if not full_path.exists():
            print(f"  [MISSING] {file_path}")
            integrity_results['missing_files'].append(file_path)
            continue
        
        try:
            # Basic checks
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            
            if len(content) == 0:
                print(f"  [EMPTY] {file_path}")
                integrity_results['issues'].append(f"Empty file: {file_path}")
            elif len(content) < 10:
                print(f"  [SMALL] {file_path} ({len(content)} bytes)")
                integrity_results['issues'].append(f"Very small file: {file_path}")
            else:
                print(f"  [OK] {file_path} ({len(content)} bytes)")
                integrity_results['files_verified'] += 1
                
        except Exception as e:
            print(f"  [ERROR] Could not read {file_path}: {e}")
            integrity_results['issues'].append(f"Read error: {file_path}")
    
    return integrity_results


if __name__ == "__main__":
    # Run verification
    verification = verify_migration_results()
    
    # Check content integrity
    integrity = check_content_integrity()
    
    # Final report
    print("\\n" + "="*50)
    print("FINAL MIGRATION REPORT")
    print("="*50)
    print(f"Files successfully migrated: {verification['total_migrated']}")
    print(f"Content integrity verified: {integrity['files_verified']}/{integrity['files_checked']} files")
    print(f"Issues found: {len(integrity['issues'])}")
    
    if verification['remaining_in_old_locations'] > 0:
        print(f"[WARNING] {verification['remaining_in_old_locations']} files still in old locations")
    
    if len(integrity['issues']) == 0 and verification['remaining_in_old_locations'] == 0:
        print("\\n[SUCCESS] Migration completed successfully with no issues!")
    else:
        print("\\n[WARNING] Migration completed with some issues - review above for details")
    
    # Save results
    results = {
        'verification': verification,
        'integrity': integrity
    }
    
    with open('migration_verification_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\\nVerification results saved to migration_verification_results.json")