#!/usr/bin/env python3
"""
Simple check of consolidation results
"""

from pathlib import Path


def main():
    project_root = Path(__file__).parent
    docs_root = project_root / "docs"
    
    print("=== SIMPLE CONSOLIDATION CHECK ===")
    
    # Check what files exist now
    print("\n1. Current file counts:")
    data_sources_files = list((docs_root / "data-sources").rglob("*.md")) if (docs_root / "data-sources").exists() else []
    modules_files = list((docs_root / "modules").rglob("*.md")) if (docs_root / "modules").exists() else []
    raw_data_files = list((docs_root / "raw_data").rglob("*.md")) if (docs_root / "raw_data").exists() else []
    root_files = list(project_root.glob("*.md"))
    
    print(f"  data-sources/: {len(data_sources_files)} files")
    print(f"  modules/: {len(modules_files)} files")
    print(f"  raw_data/: {len(raw_data_files)} files")
    print(f"  root directory: {len(root_files)} files")
    
    # Check specific files that were supposed to be consolidated
    print("\n2. Checking specific consolidation results:")
    
    # Check if exact duplicates were handled
    test_files = [
        ("docs/data-sources/equipment/anchor/calculation.md", "docs/modules/equipment/anchor/calculation.md"),
        ("docs/data-sources/equipment/x_tree/x_tree.md", "docs/modules/equipment/x_tree/x_tree.md"),
        ("docs/data-sources/onshore/wyoming/data.md", "docs/modules/onshore/wyoming/data.md"),
        ("docs/data-sources/sodir/sodir.md", "docs/raw_data/sodir/sodir.md")
    ]
    
    for file1_path, file2_path in test_files:
        file1 = project_root / file1_path
        file2 = project_root / file2_path
        
        exists1 = file1.exists()
        exists2 = file2.exists()
        
        print(f"  {file1_path}: {'EXISTS' if exists1 else 'REMOVED'}")
        print(f"  {file2_path}: {'EXISTS' if exists2 else 'REMOVED'}")
        
        if exists1 and exists2:
            print(f"    [WARN] Both files still exist - duplicate not resolved")
        elif exists1 or exists2:
            print(f"    [OK] Duplicate resolved - one file remains")
        else:
            print(f"    [ERROR] Both files missing")
        print()
    
    # Check the merged file
    print("3. Checking content merging:")
    normalization_file = project_root / "docs/data-sources/bsee/analysis/production/normalization_for_laterals.md"
    petrophysics_file = project_root / "petrophysics.md"
    
    if normalization_file.exists():
        content = normalization_file.read_text(encoding='utf-8', errors='ignore')
        has_additional_info = "Additional Information" in content
        content_length = len(content)
        print(f"  normalization_for_laterals.md: EXISTS ({content_length} chars)")
        print(f"  Contains merged content: {'YES' if has_additional_info else 'NO'}")
    else:
        print(f"  normalization_for_laterals.md: MISSING")
    
    if petrophysics_file.exists():
        print(f"  petrophysics.md: EXISTS (original still present)")
    else:
        print(f"  petrophysics.md: REMOVED")
    
    print("\n=== SUMMARY ===")
    print(f"Total files in new structure: {len(data_sources_files)}")
    print(f"Files remaining in old locations: {len(modules_files) + len(raw_data_files)}")
    print(f"Root markdown files: {len(root_files)}")
    
    # Simple assessment
    if len(modules_files) + len(raw_data_files) < 10:  # Expect reduction from original ~10
        print("[SUCCESS] Consolidation appears successful - old locations cleaned up")
    else:
        print("[WARN] Many files still in old locations")


if __name__ == "__main__":
    main()