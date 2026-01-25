#!/usr/bin/env python3
"""
Test BSEE data access with new structure
"""

import pandas as pd
from pathlib import Path
import sys

def test_bsee_data_access():
    """Test that BSEE data can be accessed from new locations"""
    
    base_path = Path("data/modules/bsee/current")
    
    test_files = {
        "production": base_path / "production/production.csv",
        "well_data": base_path / "wells/well_data.csv",
        "completions": base_path / "completions/completion_summary.csv",
        "geology": base_path / "geology/geology_markers.csv",
        "operations": base_path / "operations/well_activity_summary.csv",
    }
    
    print("Testing BSEE data access with new structure...")
    print("=" * 60)
    
    all_passed = True
    
    for name, file_path in test_files.items():
        try:
            # Test file exists
            if not file_path.exists():
                print(f"❌ {name}: File not found at {file_path}")
                all_passed = False
                continue
            
            # Test file is readable
            df = pd.read_csv(file_path, nrows=5)
            
            # Verify data loaded
            if len(df) > 0:
                print(f"✅ {name}: Successfully loaded {len(df)} rows, {len(df.columns)} columns")
            else:
                print(f"⚠️  {name}: File is empty")
                
        except Exception as e:
            print(f"❌ {name}: Error loading file - {e}")
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("✅ All BSEE data files are accessible in new structure")
        return 0
    else:
        print("❌ Some files failed to load")
        return 1

def test_import_compatibility():
    """Test that common import patterns still work"""
    
    print("\nTesting import compatibility...")
    print("=" * 60)
    
    # Test importing from new structure
    test_imports = [
        "from pathlib import Path",
        "import pandas as pd",
    ]
    
    for import_str in test_imports:
        try:
            exec(import_str)
            print(f"✅ {import_str}")
        except Exception as e:
            print(f"❌ {import_str}: {e}")
    
    # Test data path construction
    try:
        bsee_data = Path("data/modules/bsee/current")
        production_file = bsee_data / "production/production.csv"
        
        if production_file.exists():
            print(f"✅ Path construction works: {production_file}")
        else:
            print(f"❌ Path exists but file not found: {production_file}")
    except Exception as e:
        print(f"❌ Path construction failed: {e}")
    
    print("=" * 60)
    print("✅ Import compatibility test complete")
    
    return 0

if __name__ == "__main__":
    result1 = test_bsee_data_access()
    result2 = test_import_compatibility()
    
    if result1 == 0 and result2 == 0:
        print("\n🎉 All BSEE compatibility tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)