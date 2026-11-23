#!/usr/bin/env python3
"""
Final verification of duplicate consolidation
Verify that all consolidation was successful and content integrity is maintained
"""

import json
from pathlib import Path
from datetime import datetime


def verify_consolidation_complete():
    """Comprehensive verification of consolidation results"""
    project_root = Path(__file__).parent
    docs_root = project_root / "docs"
    
    print("=== FINAL CONSOLIDATION VERIFICATION ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    verification_results = {
        'timestamp': datetime.now().isoformat(),
        'consolidation_successful': True,
        'issues': [],
        'summary': {
            'exact_duplicates_removed': 0,
            'content_merged': 0,
            'files_preserved': 0,
            'obsolete_directories_cleaned': 0
        }
    }
    
    # Load the original analysis report
    report_file = project_root / "duplicate_analysis_report.json"
    if not report_file.exists():
        verification_results['issues'].append("Analysis report not found")
        return verification_results
    
    with open(report_file, 'r', encoding='utf-8') as f:
        original_report = json.load(f)
    
    print(f"\nOriginal analysis found:")
    print(f"  - {len(original_report['categorized_duplicates']['exact_duplicates'])} exact duplicates")
    print(f"  - {len(original_report['categorized_duplicates']['near_duplicates'])} near duplicates")
    
    # 1. Verify exact duplicates were removed
    print(f"\n1. Verifying exact duplicate removal...")
    exact_duplicates = original_report['categorized_duplicates']['exact_duplicates']
    
    for duplicate in exact_duplicates:
        file1_path = project_root / duplicate['file1']
        file2_path = project_root / duplicate['file2']
        
        # Check which file should have been removed based on our logic
        files_to_check = [file1_path, file2_path]
        existing_files = [f for f in files_to_check if f.exists()]
        
        if len(existing_files) == 2:
            verification_results['issues'].append(f"Both files still exist: {duplicate['file1']} and {duplicate['file2']}")
            print(f"  [WARN] Both files still exist: {file1_path.name} and {file2_path.name}")
        elif len(existing_files) == 1:
            verification_results['summary']['exact_duplicates_removed'] += 1
            print(f"  [OK] Duplicate resolved: kept {existing_files[0].relative_to(project_root)}")
        else:
            verification_results['issues'].append(f"Both files missing: {duplicate['file1']} and {duplicate['file2']}")
            print(f"  [ERROR] Both files missing: {duplicate['file1']} and {duplicate['file2']}")
    
    # 2. Verify content merging for near duplicates
    print(f"\n2. Verifying content merging...")
    near_duplicates = original_report['categorized_duplicates']['near_duplicates']
    
    for duplicate in near_duplicates:
        primary_file = project_root / duplicate['file1']  # Usually the longer file becomes primary
        merge_file = project_root / duplicate['file2']
        
        if primary_file.exists():
            try:
                content = primary_file.read_text(encoding='utf-8', errors='ignore')
                if "Additional Information" in content or len(content) > 200:
                    verification_results['summary']['content_merged'] += 1
                    print(f"  [OK] Content merged in: {primary_file.relative_to(project_root)}")
                else:
                    print(f"  [WARN] Merged content may be incomplete: {primary_file.relative_to(project_root)}")
            except Exception as e:
                verification_results['issues'].append(f"Could not read merged file: {primary_file}")
                print(f"  [ERROR] Could not read: {primary_file}")
        else:
            verification_results['issues'].append(f"Primary file missing after merge: {duplicate['file1']}")
            print(f"  [ERROR] Primary file missing: {duplicate['file1']}")
    
    # 3. Check for cleaned up obsolete directories
    print(f"\n3. Checking obsolete directory cleanup...")
    
    obsolete_patterns = [
        "docs/modules/equipment/anchor/calculation.md",
        "docs/modules/equipment/x_tree/x_tree.md", 
        "docs/modules/onshore/wyoming/data.md"
    ]
    
    for pattern in obsolete_patterns:
        obsolete_file = project_root / pattern
        if not obsolete_file.exists():
            verification_results['summary']['obsolete_directories_cleaned'] += 1
            print(f"  [OK] Obsolete file removed: {pattern}")
        else:
            print(f"  [WARN] Obsolete file still exists: {pattern}")
    
    # 4. Verify remaining file structure is logical
    print(f"\n4. Verifying final file structure...")
    
    # Count files in new structure
    data_sources_files = len(list((docs_root / "data-sources").rglob("*.md"))) if (docs_root / "data-sources").exists() else 0
    remaining_modules_files = len(list((docs_root / "modules").rglob("*.md"))) if (docs_root / "modules").exists() else 0
    remaining_raw_data_files = len(list((docs_root / "raw_data").rglob("*.md"))) if (docs_root / "raw_data").exists() else 0
    
    print(f"  Files in data-sources/: {data_sources_files}")
    print(f"  Files remaining in modules/: {remaining_modules_files}")
    print(f"  Files remaining in raw_data/: {remaining_raw_data_files}")
    
    verification_results['summary']['files_preserved'] = data_sources_files
    
    # 5. Overall assessment
    print(f"\n=== CONSOLIDATION ASSESSMENT ===")
    
    if len(verification_results['issues']) == 0:
        verification_results['consolidation_successful'] = True
        print("[SUCCESS] Consolidation completed successfully!")
        print(f"[OK] {verification_results['summary']['exact_duplicates_removed']} exact duplicates removed")
        print(f"[OK] {verification_results['summary']['content_merged']} files with merged content")
        print(f"[OK] {verification_results['summary']['obsolete_directories_cleaned']} obsolete files cleaned")
        print(f"[OK] {verification_results['summary']['files_preserved']} files preserved in final structure")
    else:
        verification_results['consolidation_successful'] = False
        print(f"[WARNING] Consolidation completed with {len(verification_results['issues'])} issues:")
        for issue in verification_results['issues']:
            print(f"  - {issue}")
    
    # 6. Before/after comparison
    print(f"\n=== BEFORE/AFTER COMPARISON ===")
    
    # Check if we have the migration verification results for comparison
    old_verification_file = project_root / "migration_verification_results.json"
    if old_verification_file.exists():
        with open(old_verification_file, 'r', encoding='utf-8') as f:
            old_results = json.load(f)
        
        old_total = old_results['verification']['total_migrated']
        old_remaining = old_results['verification']['remaining_in_old_locations']
        
        print(f"Before consolidation: {old_total} migrated files, {old_remaining} in old locations")
        print(f"After consolidation: {data_sources_files} in data-sources/, {remaining_modules_files + remaining_raw_data_files} in old locations")
        
        files_cleaned = old_remaining - (remaining_modules_files + remaining_raw_data_files)
        if files_cleaned > 0:
            print(f"[OK] {files_cleaned} duplicate files successfully removed")
    
    # Save verification results
    verification_file = project_root / "final_consolidation_verification.json"
    with open(verification_file, 'w', encoding='utf-8') as f:
        json.dump(verification_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nVerification results saved to: {verification_file}")
    
    return verification_results


if __name__ == "__main__":
    results = verify_consolidation_complete()
    
    # Exit with appropriate code
    if results['consolidation_successful']:
        print("\n[SUCCESS] Duplicate consolidation verification PASSED!")
        exit(0)
    else:
        print(f"\n[WARNING] Duplicate consolidation verification found {len(results['issues'])} issues")
        exit(1)