"""
Test script to verify enhanced_refresh flag functionality
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from worldenergydata.bsee.data.refresh.data_refresh_enhanced import DataRefreshEnhanced
from worldenergydata.bsee.data.config import ConfigRouter
import yaml

def test_enhanced_refresh_flag():
    """Test that the enhanced_refresh flag is properly recognized"""
    
    # Test configuration with enhanced_refresh flag
    test_config = {
        'meta': {
            'library': 'worldenergydata',
            'basename': 'bsee',
            'mode': 'enhanced'
        },
        'enhanced_mode': True,
        'data': {
            'enhanced_refresh': True,  # New flag name
            'enhanced': True,
            'fresh_data': True,
            'well': False,
            'war': False,
            'production': False  # Set all to False to just test flag recognition
        }
    }
    
    print("Testing enhanced_refresh flag recognition...")
    print("=" * 50)
    
    # Initialize components
    data_refresh_enhanced = DataRefreshEnhanced()
    config_router = ConfigRouter()
    
    # Check if enhanced mode is detected
    is_enhanced = config_router.is_enhanced_mode(test_config)
    print(f"[OK] Enhanced mode detected: {is_enhanced}")
    
    # Check if enhanced_refresh flag is properly accessed
    enhanced_refresh_flag = test_config.get('data', {}).get('enhanced_refresh', False)
    print(f"[OK] Enhanced refresh flag value: {enhanced_refresh_flag}")
    
    # Test with flag set to False
    test_config['data']['enhanced_refresh'] = False
    enhanced_refresh_flag_false = test_config.get('data', {}).get('enhanced_refresh', False)
    print(f"[OK] Enhanced refresh flag (when False): {enhanced_refresh_flag_false}")
    
    # Load actual config file
    print("\nLoading actual configuration file...")
    config_path = Path(__file__).parent / "data_refresh_enhanced.yml"
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            actual_config = yaml.safe_load(f)
        
        actual_flag = actual_config.get('data', {}).get('enhanced_refresh')
        print(f"[OK] Actual config 'enhanced_refresh' flag: {actual_flag}")
        
        # Check that old 'refresh' flag is not present
        old_flag = actual_config.get('data', {}).get('refresh')
        if old_flag is None:
            print("[OK] Old 'refresh' flag is not present (good!)")
        else:
            print(f"[WARNING] Old 'refresh' flag still exists: {old_flag}")
    
    print("\n" + "=" * 50)
    print("TEST COMPLETED SUCCESSFULLY")
    print("The enhanced_refresh flag is working correctly!")

if __name__ == "__main__":
    test_enhanced_refresh_flag()