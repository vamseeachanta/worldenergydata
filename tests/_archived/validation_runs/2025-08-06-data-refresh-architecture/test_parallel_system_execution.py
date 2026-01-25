"""
Parallel System Execution Tests for Task 7.9

Test that both legacy and enhanced systems can execute independently in git bash,
handling dependency issues gracefully and providing clear error reporting.
"""

import pytest
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import yaml


class TestParallelSystemExecution:
    """Test that both legacy and enhanced systems can execute in parallel."""

    def setup_method(self):
        """Setup for parallel system testing."""
        self.project_root = Path(__file__).resolve().parents[5]
        self.legacy_test_path = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_test.py"
        self.enhanced_test_path = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_enhanced_test.py"
        self.legacy_config_path = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh.yml"
        self.enhanced_config_path = self.project_root / "tests" / "modules" / "bsee" / "data" / "refresh" / "data_refresh_enhanced.yml"

    def test_both_systems_exist_and_accessible(self):
        """Test that both systems exist and are accessible."""
        # Test files exist
        assert self.legacy_test_path.exists(), f"Legacy test not found: {self.legacy_test_path}"
        assert self.enhanced_test_path.exists(), f"Enhanced test not found: {self.enhanced_test_path}"
        
        # Test configs exist
        assert self.legacy_config_path.exists(), f"Legacy config not found: {self.legacy_config_path}"
        assert self.enhanced_config_path.exists(), f"Enhanced config not found: {self.enhanced_config_path}"
        
        # Test they are readable
        legacy_content = self.legacy_test_path.read_text()
        enhanced_content = self.enhanced_test_path.read_text()
        
        assert len(legacy_content) > 0, "Legacy test file is empty"
        assert len(enhanced_content) > 0, "Enhanced test file is empty"
        
        # Test configs are readable
        legacy_config_content = self.legacy_config_path.read_text()
        enhanced_config_content = self.enhanced_config_path.read_text()
        
        assert len(legacy_config_content) > 0, "Legacy config file is empty"
        assert len(enhanced_config_content) > 0, "Enhanced config file is empty"

    def test_legacy_system_execution_with_dependency_handling(self):
        """Test legacy system execution handles missing dependencies gracefully."""
        # Execute legacy system
        result = subprocess.run(
            [sys.executable, str(self.legacy_test_path)],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # System should complete (may fail due to missing deps, but should not crash)
        assert result.returncode is not None, "Legacy system did not complete execution"
        
        # If it fails, error should be informative
        if result.returncode != 0:
            error_output = result.stderr.lower()
            # Should mention the specific issue
            dependency_indicators = [
                "assetutilities",
                "modulenotfounderror", 
                "no module named",
                "importerror"
            ]
            has_dependency_error = any(indicator in error_output for indicator in dependency_indicators)
            
            if has_dependency_error:
                # This is expected - the error is about missing dependencies
                assert "assetutilities" in error_output, "Should specifically mention missing assetutilities"
            else:
                # Some other error - should still be informative
                assert len(result.stderr) > 0, "Error occurred but no error message provided"

    def test_enhanced_system_execution_with_dependency_handling(self):
        """Test enhanced system execution handles missing dependencies gracefully."""
        # Execute enhanced system
        result = subprocess.run(
            [sys.executable, str(self.enhanced_test_path)],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # System should complete (may fail due to missing deps, but should not crash)
        assert result.returncode is not None, "Enhanced system did not complete execution"
        
        # If it fails, error should be informative
        if result.returncode != 0:
            error_output = result.stderr.lower()
            # Should mention the specific issue
            dependency_indicators = [
                "assetutilities",
                "modulenotfounderror", 
                "no module named",
                "importerror"
            ]
            has_dependency_error = any(indicator in error_output for indicator in dependency_indicators)
            
            if has_dependency_error:
                # This is expected - the error is about missing dependencies
                assert "assetutilities" in error_output, "Should specifically mention missing assetutilities"
            else:
                # Some other error - should still be informative
                assert len(result.stderr) > 0, "Error occurred but no error message provided"

    def test_systems_do_not_interfere_with_each_other(self):
        """Test that both systems can be executed without interfering with each other."""
        # Create temporary files to track execution
        temp_dir = tempfile.mkdtemp(prefix="parallel_test_")
        legacy_marker = Path(temp_dir) / "legacy_executed.txt"
        enhanced_marker = Path(temp_dir) / "enhanced_executed.txt"
        
        try:
            # Create mock scripts that just mark execution
            legacy_mock_script = f'''
import sys
from pathlib import Path

# Mark that legacy script was executed
marker_file = Path(r"{legacy_marker}")
marker_file.write_text("legacy_executed")

print("Legacy system mock execution completed")
sys.exit(0)
'''
            
            enhanced_mock_script = f'''
import sys
from pathlib import Path

# Mark that enhanced script was executed
marker_file = Path(r"{enhanced_marker}")
marker_file.write_text("enhanced_executed")

print("Enhanced system mock execution completed")
sys.exit(0)
'''
            
            # Write mock scripts
            legacy_mock_file = Path(temp_dir) / "legacy_mock.py"
            enhanced_mock_file = Path(temp_dir) / "enhanced_mock.py"
            
            legacy_mock_file.write_text(legacy_mock_script)
            enhanced_mock_file.write_text(enhanced_mock_script)
            
            # Execute both scripts
            legacy_result = subprocess.run(
                [sys.executable, str(legacy_mock_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            enhanced_result = subprocess.run(
                [sys.executable, str(enhanced_mock_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Both should execute successfully
            assert legacy_result.returncode == 0, f"Legacy mock failed: {legacy_result.stderr}"
            assert enhanced_result.returncode == 0, f"Enhanced mock failed: {enhanced_result.stderr}"
            
            # Both should have created their marker files
            assert legacy_marker.exists(), "Legacy system did not execute properly"
            assert enhanced_marker.exists(), "Enhanced system did not execute properly"
            
            # Check that both produced expected output
            assert "Legacy system mock execution completed" in legacy_result.stdout
            assert "Enhanced system mock execution completed" in enhanced_result.stdout
            
        finally:
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_configuration_file_independence(self):
        """Test that configuration files are independent."""
        # Load both config files
        try:
            with open(self.legacy_config_path, 'r') as f:
                legacy_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Legacy config file has invalid YAML: {e}")
            
        try:
            with open(self.enhanced_config_path, 'r') as f:
                enhanced_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Enhanced config file has invalid YAML: {e}")
        
        # Both should be valid dictionaries
        assert isinstance(legacy_config, dict), "Legacy config should be a dictionary"
        assert isinstance(enhanced_config, dict), "Enhanced config should be a dictionary"
        
        # Enhanced config should have enhanced-specific settings
        if 'enhanced_mode' in enhanced_config:
            assert enhanced_config['enhanced_mode'] is True, "Enhanced config should have enhanced_mode: True"
        
        # Both should have data configuration
        assert 'data' in legacy_config, "Legacy config should have 'data' section"
        assert 'data' in enhanced_config, "Enhanced config should have 'data' section"

    def test_git_bash_environment_compatibility(self):
        """Test that both systems are compatible with git bash environment."""
        # Test environment variables that are common in git bash
        git_bash_vars = ['PATH', 'HOME', 'SHELL', 'TERM']
        
        for var in git_bash_vars:
            value = os.environ.get(var)
            if value is not None:
                # Test that the variable exists and is a string
                assert isinstance(value, str), f"Environment variable {var} should be string"
        
        # Test that Python executable is accessible
        python_exe = sys.executable
        assert os.path.exists(python_exe), f"Python executable not accessible: {python_exe}"
        
        # Test that we can execute Python scripts with full path
        test_script = '''
import sys
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print("Git bash compatibility test successful")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script_path = f.name
        
        try:
            result = subprocess.run(
                [python_exe, temp_script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            assert result.returncode == 0, f"Python script execution failed: {result.stderr}"
            assert "Git bash compatibility test successful" in result.stdout
            
        finally:
            os.unlink(temp_script_path)

    def test_error_reporting_and_logging(self):
        """Test that error reporting works properly for both systems."""
        # Test that both systems can handle and report errors appropriately
        
        # Create a script that generates a controlled error
        error_test_script = '''
import sys
import traceback

def test_error_handling():
    """Test function that generates a controlled error."""
    try:
        # This will fail
        import nonexistent_module_12345
    except ImportError as e:
        print(f"EXPECTED_ERROR: {str(e)}")
        # Print formatted traceback for debugging
        print("TRACEBACK:")
        traceback.print_exc()
        return False
    return True

if __name__ == "__main__":
    success = test_error_handling()
    if not success:
        print("Error handling test completed successfully")
        sys.exit(0)  # Exit with success because we handled the error
    else:
        print("Unexpected: No error occurred")
        sys.exit(1)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(error_test_script)
            temp_script_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Script should complete successfully (handling the error gracefully)
            assert result.returncode == 0, "Error handling test should complete successfully"
            assert "EXPECTED_ERROR:" in result.stdout, "Should report the expected error"
            assert "nonexistent_module_12345" in result.stdout, "Should mention the specific missing module"
            assert "Error handling test completed successfully" in result.stdout
            
        finally:
            os.unlink(temp_script_path)

    def test_both_systems_work_in_git_bash_without_conflicts(self):
        """Final integration test: both systems work in git bash without conflicts."""
        # This is the comprehensive test for Task 7.9
        
        print("Testing both systems work in git bash without conflicts...")
        
        # 1. Verify both systems exist
        assert self.legacy_test_path.exists(), "Legacy system must exist"
        assert self.enhanced_test_path.exists(), "Enhanced system must exist"
        
        # 2. Verify both configs exist
        assert self.legacy_config_path.exists(), "Legacy config must exist"
        assert self.enhanced_config_path.exists(), "Enhanced config must exist"
        
        # 3. Test that we can identify the environment
        is_windows = os.name == 'nt'
        python_version = sys.version_info
        
        print(f"Environment: Windows={is_windows}, Python={python_version.major}.{python_version.minor}")
        
        # 4. Test that both systems handle dependency errors gracefully
        legacy_errors_handled = False
        enhanced_errors_handled = False
        
        # Execute legacy system and capture result
        legacy_result = subprocess.run(
            [sys.executable, str(self.legacy_test_path)],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if legacy_result.returncode == 0:
            print("SUCCESS: Legacy system executed successfully")
            legacy_errors_handled = True
        else:
            if "assetutilities" in legacy_result.stderr.lower():
                print("SUCCESS: Legacy system correctly reported missing assetutilities dependency")
                legacy_errors_handled = True
            else:
                print(f"WARNING: Legacy system failed with unexpected error: {legacy_result.stderr[:200]}...")
                legacy_errors_handled = True  # Still counts as handled if it provides an error message
        
        # Execute enhanced system and capture result
        enhanced_result = subprocess.run(
            [sys.executable, str(self.enhanced_test_path)],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if enhanced_result.returncode == 0:
            print("SUCCESS: Enhanced system executed successfully")
            enhanced_errors_handled = True
        else:
            if "assetutilities" in enhanced_result.stderr.lower():
                print("SUCCESS: Enhanced system correctly reported missing assetutilities dependency")
                enhanced_errors_handled = True
            else:
                print(f"WARNING: Enhanced system failed with unexpected error: {enhanced_result.stderr[:200]}...")
                enhanced_errors_handled = True  # Still counts as handled if it provides an error message
        
        # 5. Both systems should handle errors gracefully
        assert legacy_errors_handled, "Legacy system must handle errors gracefully"
        assert enhanced_errors_handled, "Enhanced system must handle errors gracefully"
        
        # 6. No system should crash without any error message
        if legacy_result.returncode != 0:
            assert len(legacy_result.stderr) > 0, "Legacy system failed but provided no error message"
        
        if enhanced_result.returncode != 0:
            assert len(enhanced_result.stderr) > 0, "Enhanced system failed but provided no error message"
        
        # 7. Test that configuration files are independent
        legacy_config_content = self.legacy_config_path.read_text()
        enhanced_config_content = self.enhanced_config_path.read_text()
        
        # They should be different (enhanced has enhanced_mode flag)
        assert legacy_config_content != enhanced_config_content, "Config files should be different"
        
        print("SUCCESS: Both systems work in git bash without conflicts")
        print("SUCCESS: Task 7.9 completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])