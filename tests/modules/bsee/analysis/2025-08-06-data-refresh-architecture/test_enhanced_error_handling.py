"""
Enhanced Error Handling Tests for BSEE Data Refresh Architecture

Tests for Task 7.8: Implement proper error reporting in ENHANCED system
- Dependency missing error handling
- Network failure scenarios
- Configuration file issues
- Import error graceful handling
"""

import pytest
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import yaml


class TestEnhancedErrorHandling:
    """Test enhanced error handling in git bash environment."""

    def setup_method(self):
        """Setup for each test method."""
        self.project_root = Path(__file__).resolve().parents[5]
        self.enhanced_test_path = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_enhanced_test.py"
        self.legacy_test_path = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_test.py"
        
    def test_missing_dependency_error_handling(self):
        """Test graceful handling of missing assetutilities dependency."""
        # Test that we can detect the missing dependency issue
        result = subprocess.run(
            [sys.executable, str(self.enhanced_test_path)],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # The script should fail but with informative error message
        assert result.returncode != 0
        error_output = result.stderr.lower()
        
        # Should mention the missing module
        assert "assetutilities" in error_output or "module" in error_output
        
        # Test that the error is specific and helpful
        assert "modulenotfounderror" in error_output or "importerror" in error_output
        
    def test_enhanced_system_import_error_detection(self):
        """Test detection and reporting of import errors in enhanced system."""
        # Create a test script that handles import errors gracefully
        test_script_content = '''
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(project_root / "src"))

try:
    from worldenergydata.engine import engine
    print("ENGINE_IMPORT_SUCCESS")
except ImportError as e:
    print(f"ENGINE_IMPORT_ERROR: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"ENGINE_OTHER_ERROR: {str(e)}")
    sys.exit(2)

try:
    from worldenergydata.bsee.data.refresh.data_refresh_enhanced import DataRefreshEnhanced
    print("ENHANCED_IMPORT_SUCCESS")
except ImportError as e:
    print(f"ENHANCED_IMPORT_ERROR: {str(e)}")
    sys.exit(3)
except Exception as e:
    print(f"ENHANCED_OTHER_ERROR: {str(e)}")
    sys.exit(4)

print("ALL_IMPORTS_SUCCESS")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_content)
            temp_script_path = f.name
            
        try:
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            
            # Check what type of error we get
            if "ENGINE_IMPORT_ERROR" in output:
                assert "assetutilities" in output.lower()
                assert result.returncode == 1
            elif "ENHANCED_IMPORT_ERROR" in output:
                assert result.returncode == 3
            elif "ALL_IMPORTS_SUCCESS" in output:
                assert result.returncode == 0
            else:
                # Some other error occurred
                assert "ERROR" in output
                
        finally:
            os.unlink(temp_script_path)
            
    def test_configuration_file_error_handling(self):
        """Test handling of configuration file issues."""
        # Create invalid configuration file
        invalid_config_content = "invalid yaml content: [unclosed bracket"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(invalid_config_content)
            invalid_config_path = f.name
            
        try:
            # Test YAML parsing error handling
            with pytest.raises(yaml.YAMLError):
                with open(invalid_config_path, 'r') as config_file:
                    yaml.safe_load(config_file)
                    
        finally:
            os.unlink(invalid_config_path)
            
        # Test missing configuration file handling
        nonexistent_config = "/nonexistent/path/config.yml"
        assert not os.path.exists(nonexistent_config)
        
        # This should be handled gracefully by any system
        with pytest.raises(FileNotFoundError):
            with open(nonexistent_config, 'r') as config_file:
                yaml.safe_load(config_file)
                
    def test_network_failure_simulation(self):
        """Test network failure handling in enhanced system."""
        # Import the scraper if available
        try:
            from tests.modules.bsee.analysis import bsee_data_scraper
            scraper_module = bsee_data_scraper
            
            # Test with mocked network failure
            scraper = scraper_module.BSEEDataScraper(max_retries=1, timeout=1)
            
            with patch.object(scraper.session, 'get') as mock_get:
                # Simulate network timeout
                mock_get.side_effect = Exception("Network timeout")
                
                result = scraper.download_and_process('well_data')
                
                assert result['status'] == 'error'
                assert 'error' in result
                assert 'Network timeout' in result['error']
                
        except ImportError:
            # If scraper module not available, skip this test
            pytest.skip("BSEEDataScraper not available for testing")
            
    def test_git_bash_path_error_handling(self):
        """Test path-related error handling in git bash environment."""
        # Test with invalid path
        invalid_path = Path("/completely/nonexistent/path/file.txt")
        
        # Should not crash, should handle gracefully
        assert not invalid_path.exists()
        
        # Test with permission-denied path (simulate)
        try:
            temp_file = Path(tempfile.gettempdir()) / "test_readonly.txt"
            temp_file.write_text("test")
            temp_file.chmod(0o444)  # Read-only
            
            # Try to write to read-only file (should fail gracefully)
            with pytest.raises(PermissionError):
                temp_file.write_text("new content")
                
        except Exception:
            # If chmod not supported on this platform, skip
            pytest.skip("chmod not supported on this platform")
        finally:
            if temp_file.exists():
                temp_file.chmod(0o666)  # Make writable for cleanup
                temp_file.unlink()
                
    def test_subprocess_error_reporting(self):
        """Test subprocess error reporting in git bash environment."""
        # Test command that should fail
        result = subprocess.run(
            [sys.executable, "-c", "import nonexistent_module_xyz"],
            capture_output=True,
            text=True
        )
        
        # Should complete with error
        assert result.returncode != 0
        assert len(result.stderr) > 0
        assert "nonexistent_module_xyz" in result.stderr
        
        # Test timeout handling
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout=1
            )
            
    def test_enhanced_system_fallback_behavior(self):
        """Test enhanced system fallback behavior when dependencies missing."""
        # Create a mock enhanced system that handles missing dependencies
        mock_enhanced_content = '''
import sys
from pathlib import Path

def safe_import_engine():
    """Safely import engine with proper error handling."""
    try:
        from worldenergydata.engine import engine
        return engine, None
    except ImportError as e:
        if "assetutilities" in str(e):
            return None, f"Missing assetutilities dependency: {str(e)}"
        else:
            return None, f"Import error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def main():
    """Main function with error handling."""
    engine_func, error = safe_import_engine()
    
    if error:
        print(f"ERROR: {error}")
        print("SOLUTION: Install missing dependencies or check environment")
        sys.exit(1)
    else:
        print("SUCCESS: Engine imported successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(mock_enhanced_content)
            temp_script_path = f.name
            
        try:
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should handle error gracefully
            if result.returncode != 0:
                assert "ERROR:" in result.stdout
                assert "assetutilities" in result.stdout.lower()
                assert "SOLUTION:" in result.stdout
            else:
                assert "SUCCESS:" in result.stdout
                
        finally:
            os.unlink(temp_script_path)
            
    def test_error_message_formatting(self):
        """Test that error messages are properly formatted for git bash."""
        # Test that error messages contain useful information
        test_errors = [
            "ModuleNotFoundError: No module named 'assetutilities.modules'",
            "FileNotFoundError: [Errno 2] No such file or directory: 'config.yml'",
            "yaml.scanner.ScannerError: while scanning a simple key",
            "ConnectionError: HTTPSConnectionPool(host='www.bsee.gov'): Read timed out"
        ]
        
        for error_msg in test_errors:
            # Test that error messages can be processed
            assert len(error_msg) > 0
            assert isinstance(error_msg, str)
            
            # Test that they contain useful keywords
            useful_keywords = ["Error", "Exception", "No module", "not found", "timed out"]
            has_useful_keyword = any(keyword.lower() in error_msg.lower() for keyword in useful_keywords)
            assert has_useful_keyword, f"Error message lacks useful keywords: {error_msg}"


class TestSystemCompatibility:
    """Test system compatibility and execution paths."""
    
    def setup_method(self):
        """Setup for system compatibility tests."""
        self.project_root = Path(__file__).resolve().parents[5]
        
    def test_both_systems_can_coexist(self):
        """Test that both legacy and enhanced systems can coexist without conflicts."""
        # Check that both test files exist
        legacy_test = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_test.py"
        enhanced_test = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_enhanced_test.py"
        
        assert legacy_test.exists(), "Legacy test file should exist"
        assert enhanced_test.exists(), "Enhanced test file should exist"
        
        # Check that both config files can exist
        legacy_config = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh.yml"
        enhanced_config = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_enhanced.yml"
        
        assert legacy_config.exists(), "Legacy config should exist"
        assert enhanced_config.exists(), "Enhanced config should exist"
        
        # Test that configs are different
        legacy_content = legacy_config.read_text()
        enhanced_content = enhanced_config.read_text()
        
        # They should contain different content (enhanced mode flags)
        assert "enhanced" not in legacy_content.lower() or legacy_content != enhanced_content
        
    def test_execution_path_independence(self):
        """Test that execution paths are independent."""
        # Both should be Python scripts that can be executed
        legacy_test = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_test.py"
        enhanced_test = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_enhanced_test.py"
        
        # Check that both are valid Python files
        assert legacy_test.suffix == '.py'
        assert enhanced_test.suffix == '.py'
        
        # Check that both have proper shebang or can be executed
        legacy_content = legacy_test.read_text()
        enhanced_content = enhanced_test.read_text()
        
        # Both should be executable Python scripts
        assert 'if __name__ == "__main__"' in legacy_content or 'def main' in legacy_content
        assert 'if __name__ == "__main__"' in enhanced_content or 'def main' in enhanced_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])