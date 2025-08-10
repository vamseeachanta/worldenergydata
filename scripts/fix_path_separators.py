#!/usr/bin/env python3
"""
Quick fix for path separator issues in image links
"""

from pathlib import Path
import re


def fix_path_separators():
    """Fix mangled path separators in image links"""
    project_root = Path(__file__).parent
    docs_root = project_root / "docs"
    
    print("Fixing path separators in image links...")
    
    # Files that had path fixes applied
    files_to_fix = [
        "docs/data-sources/bsee/analysis/field/field_layout.md",
        "docs/data-sources/bsee/data/drilling_data_rev1.md", 
        "docs/data-sources/equipment/anchor/calculation.md",
        "docs/data-sources/equipment/x_tree/x_tree.md"
    ]
    
    fixes_applied = 0
    
    for file_path_str in files_to_fix:
        file_path = project_root / file_path_str
        
        if not file_path.exists():
            continue
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            original_content = content
            
            # Fix mangled paths like "modulesseenalysisield\image.png"
            # Should be "modules/bsee/analysis/field/image.png"
            content = re.sub(r'modulesseenalysisield\\', r'modules/bsee/analysis/field/', content)
            content = re.sub(r'modules\\equipment\\x_tree\\', r'modules/equipment/x_tree/', content)
            
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                fixes_applied += 1
                print(f"  [OK] Fixed paths in {file_path_str}")
                
        except Exception as e:
            print(f"  [ERROR] Failed to fix {file_path_str}: {e}")
    
    print(f"Path separator fixes applied: {fixes_applied}")


if __name__ == "__main__":
    fix_path_separators()